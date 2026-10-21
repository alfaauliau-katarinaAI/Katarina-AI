"""Run existing MarketDecisionBrain V3 on historical MT5 CLOSED bars, read-only.

Reuses adaptive_walkforward for outcome-delayed experience. Entry/exit
labels use M5 BID OHLC with ASSUMED spread, not broker tick fills,
and do NOT constitute fresh OOS. No historical news assumed. No orders.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
from math import ceil
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))

from katarina.intelligence.broker_clock_alignment import infer_clock_shift
from katarina.intelligence.market_decision_pipeline import SensorCandle
from katarina.intelligence.causal_market_replay import (
    replay_native_brain,purged_chronological_splits
)
from katarina.intelligence.adaptive_walkforward import PaperEvent
from katarina.intelligence.replay_cost_diagnostics import describe_candidates
from katarina.intelligence.closed_bar_failure_forensics import (
    diagnose_frozen_replay,
)

# Dynamically verify the 17 broker-supported canonical names, not hardcode five.
from katarina.intelligence.broker_scan_universe import resolve_broker_symbols


def requested_history_depth(now_utc,window_end_utc,max_cuts):
    """Bound the MT5 bar request; retain M15/H1 warmup on older windows."""
    if now_utc.tzinfo is None or window_end_utc.tzinfo is None:
        raise ValueError("timezone_aware_utc_broker_history_required")
    delta=(now_utc-window_end_utc).total_seconds()
    if delta<0 or delta>80*86400:
        raise ValueError("historical_window_must_be_past_within_80_days")
    if not 120<=max_cuts<=2300:
        raise ValueError("historical_window_unbounded_cuts")
    depths={
        "M5":(max(1500,max_cuts+250+ceil(delta/300)+80),300),
        "M15":(max(900,(max_cuts+250)//3+150+ceil(delta/900)+40),900),
        "H1":(max(280,(max_cuts+250)//12+80+ceil(delta/3600)+25),3600),
    }
    if depths["M5"][0]>25000 or depths["M15"][0]>9000 or depths["H1"][0]>3000:
        raise ValueError("historical_window_exceeds_bounded_MT5_bar_memory")
    return depths


def load_from_live_terminal(symbols,*,max_cuts,include_spreads=False,
                            window_end_utc=None):
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("MT5_TERMINAL_NOT_AVAILABLE")
    try:
        terminal=mt5.terminal_info()
        if terminal is None or terminal.trade_allowed:
            raise RuntimeError("HISTORICAL_REPLAY_REQUIRES_DISABLED_TRADE_PERMISSION")
        now=datetime.now(timezone.utc)
        cutoff=window_end_utc or now
        counts=requested_history_depth(now,cutoff,max_cuts)
        readings={s:mt5.symbol_info_tick(s) for s in symbols}
        shift=infer_clock_shift(
            {s:int(t.time) for s,t in readings.items()
                if t is not None and t.bid>0 and t.ask>=t.bid},
            now.timestamp(),min_symbols=3)
        if not shift.suitable_for_readonly_snapshot:
            raise RuntimeError("CURRENT_BROKER_CLOCK_CONSENSUS_NOT_VERIFIED")
        frames={}
        status={}
        market_spreads={}
        offset=shift.observed_hours_shift
        req={
            "M5":(mt5.TIMEFRAME_M5,*counts["M5"]),
            "M15":(mt5.TIMEFRAME_M15,*counts["M15"]),
            "H1":(mt5.TIMEFRAME_H1,*counts["H1"]),
        }
        for symbol in symbols:
            bars={}
            spreads={}
            broker_spec=mt5.symbol_info(symbol)
            point=float(getattr(broker_spec,"point",0) or 0)
            for tf,(period,count,length) in req.items():
                rates=mt5.copy_rates_from_pos(symbol,period,1,count)
                if rates is None or len(rates)<60:
                    status[symbol]={"result":"NOT_ENOUGH_BROKER_BARS","timeframe":tf,
                                    "observed":0 if rates is None else len(rates)}
                    bars={}
                    break
                rows=[]
                for r in rates:
                    closed=datetime.fromtimestamp(int(r["time"])-offset*3600+length,
                                                  timezone.utc)
                    if closed>cutoff:continue
                    if tf=="M5" and include_spreads:
                        raw_spread=int(r["spread"])
                        if (point>0 and 0<raw_spread<100000):
                            spreads[int(closed.timestamp())]=point*raw_spread
                    rows.append(SensorCandle(
                        closed,float(r["open"]),float(r["high"]),
                        float(r["low"]),float(r["close"]),
                        float(r["tick_volume"])))
                bars[tf]=tuple(rows)
            if bars and all(len(v)>=60 for v in bars.values()):
                frames[symbol]=bars
                if include_spreads:
                    market_spreads[symbol]=spreads
                status[symbol]={"result":"AVAILABLE",
                                "counts":{k:len(v) for k,v in bars.items()},
                                "range_m5":[bars["M5"][0].closed_at_utc.isoformat(),
                                            bars["M5"][-1].closed_at_utc.isoformat()]}
        return (frames,status,offset,market_spreads) if include_spreads else (frames,status,offset)
    finally:
        mt5.shutdown()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols",default="XAUUSD.vx,EURUSD.vx,NAS100.vx")
    p.add_argument("--max-cuts",type=int,default=700)
    p.add_argument("--spread-to-atr",type=float,default=.04)
    p.add_argument("--extra-cost-r",type=float,default=.15)
    p.add_argument("--window-end-utc",default=None,
                   help="Past UTC time; closed bars after this instant are hidden from Brain")
    p.add_argument("--private-report",required=True)
    a=p.parse_args()
    symbols=[s.strip() for s in a.symbols.split(",") if s.strip()]
    if len(symbols)<3 or len(symbols)>5 or len(set(symbols))!=len(symbols):
        p.error("3-5 unique symbols per VPS memory-capped batch required")
    import MetaTrader5 as mt5
    if not mt5.initialize():raise RuntimeError("BROKER_CATALOG_UNAVAILABLE")
    try:
        approved=set(resolve_broker_symbols(mt5.symbols_get()).symbols)
    finally:
        mt5.shutdown()
    if any(s not in approved for s in symbols):
        p.error("unknown or noncanonical broker research symbol")
    if not 120<=a.max_cuts<=2300:
        p.error("120-2300 retrospective M5 cuts per symbol")
    window_end=(datetime.fromisoformat(a.window_end_utc.replace("Z","+00:00"))
                if a.window_end_utc else None)
    if window_end is not None and window_end.tzinfo is None:
        p.error("window-end-utc must contain UTC offset")
    frames,status,offset,spreads=load_from_live_terminal(
        symbols,max_cuts=a.max_cuts,include_spreads=True,
        window_end_utc=window_end)
    if not frames:raise RuntimeError("NO_HISTORICAL_MARKET_BARS")
    result=replay_native_brain(
        frames,assumed_spread_to_m15_atr=a.spread_to_atr,
        additional_cost_r=a.extra_cost_r,
        max_m5_cuts_per_symbol=a.max_cuts,
        historical_m5_spread_by_symbol=spreads)
    events=[PaperEvent(x["symbol"],x["method"],x["side"],
                       x["signal_at"],x["label_known_at"],
                       x["proxy_gross_r"],x["technical_score"],
                       x.get("spread_to_m15_atr",a.spread_to_atr),
                       market_regime=x["regime"])
            for x in result["signals"]]
    splits=purged_chronological_splits(events)
    summary=result["adaptive_summary"]
    cost_review=describe_candidates(result["signals"],splits)
    forensic=diagnose_frozen_replay(result,frames)
    info={
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "historical_window_end_utc":(window_end.isoformat() if window_end
                                     else "CURRENT_OBSERVED_PAST"),
        "broker_replay_window_for_research_not_unseen_holdout":True,
        "purpose":"CLOSED_BAR_REAL_MT5_HISTORICAL_SIGNAL_REPLAY",
        "read_only":True,"orders_sent":0,
        "broker_current_clock_offset_hours":offset,
        "broker_historical_clock_dst_verified":False,
        "historical_m5_signal_close_spread_snapshot_available":True,
        "actual_historical_entry_bidask_verified":False,
        "next_bar_entry_spread_assumed_equal_signal_close":True,
        "actual_historical_spread_verified":False,
        "historical_news_contents_available":False,
        "retrospective_data_already_inspected_not_independent_holdout":True,
        "market_brain_reused":result["market_brain_reused"],
        "memory_engine_reused":result["memory_engine_reused"],
        "symbols_requested":symbols,
        "broker_data_availability":status,
        "counters":result["counters"],
        "assumed_spread_to_m15_atr_FALLBACK_NOT_USED":a.spread_to_atr,
        "spread_source":"BROKER_M5_CLOSED_BAR_SPREAD_POINTS",
        "additional_cost_r":a.extra_cost_r,
        "purged_calendar_split_counts":{
            "train":len(splits["train"]),
            "validation":len(splits["validation"]),
            "test":len(splits["test"]),
            "purged_or_embargoed":splits["purged"],
            "embargo_seconds":splits.get("embargo_sec"),
        },
        "adapted_replay":{
            "status":summary.get("status"),
            "adaptive":summary.get("adaptive"),
            "v6_conditional_benchmark":summary.get("v6_conditional_benchmark"),
            "replay_conditions":summary.get("replay_conditions"),
        },
        "candidate_methods":dict(Counter(x["method"] for x in result["signals"])),
        "unlabeled_technical_proposals":len(result["all_technical_proposals"]),
        "by_method_and_side":dict(Counter(
            x["method"]+":"+x["side"] for x in result["all_technical_proposals"])),
        "full_cost_sensitivity":cost_review,
        "entry_failure_diagnostics":forensic,
        "no_qualified_live_strategy":True,
        "live_execution_authorized":False,
    }
    dest=Path(a.private_report)
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(info,indent=2,allow_nan=False,ensure_ascii=False)+"\n",
                   encoding="utf-8")
    tmp.replace(dest)
    print("NATIVE_CAUSAL_BROKER_REPLAY",json.dumps({
        "symbols":list(frames),"cuts":result["counters"]["evaluated"],
        "paper_labels":result["counters"]["proxy_completed"],
        "train_val_test":info["purged_calendar_split_counts"],
        "candidate_methods":info["candidate_methods"],
        "failure_causes":{k:forensic["totals"][k] for k in (
            "exit_causes","loss_exit_causes",
            "ambiguous_intrabar_stop_vs_target_count",
            "early_stop_within_15m_count","censored_or_gap_proxy_labels",
            "mean_net_proxy_r")},
        "adaptive_research":summary.get("adaptive",{}),
        "orders":0,"live":False},allow_nan=False))


if __name__=="__main__":
    main()
