"""Bounded REAL broker tick validation of the EXISTING native brain replay.

ONE-TIME VPS read-only script; never a scheduled observer. Native signals
are frozen from historical closed bars BEFORE querying outcome quotes.
For each signal, verify its NEXT M5 BID OHLC exactly against real tick
BID open/high/low/close; price BUY at ask/bid and SELL at bid/ask.
If clocks, ticks, spreads or exit path fail, print UNKNOWN, never invent R.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))

from run_native_brain_causal_broker_replay import load_from_live_terminal
from katarina.intelligence.causal_market_replay import replay_native_brain
from katarina.intelligence.causal_tick_reconciliation import (
    tick_reconcile,summarize_tick_reconciliation,
)


def preselect(signals,max_per_symbol):
    """Signal-time-only balanced deterministic audit selection.

    Never look at modeled R, exit reason or known future market path
    when choosing which historical signals to audit.
    """
    by_symbol={}
    for s in signals:
        by_symbol.setdefault(s["symbol"],[]).append(s)
    out=[]
    for symbol in sorted(by_symbol):
        rows=sorted(by_symbol[symbol],
                    key=lambda x:(x["signal_at"],x["method"],x["side"]))
        if len(rows)<=max_per_symbol:
            out.extend(rows)
            continue
        # Exactly N spread across historical dates, determined before
        # querying any tick data or inspecting the proxy outcome.
        chosen=[rows[i*(len(rows)-1)//(max_per_symbol-1)]
                for i in range(max_per_symbol)]
        out.extend(chosen)
    return sorted(out,key=lambda x:(x["signal_at"],x["symbol"]))


def run(args):
    import MetaTrader5 as mt5
    names=[s.strip() for s in args.symbols.split(",") if s.strip()]
    if len(names)<3 or len(names)>5 or len(set(names))!=len(names):
        raise ValueError("three_to_five_unique_symbols_required")
    frames,availability,offset=load_from_live_terminal(
        names,max_cuts=args.max_cuts)
    if len(frames)<3:
        raise RuntimeError("insufficient_broker_histories_for_clock_vote")
    retrospective=replay_native_brain(
        frames,assumed_spread_to_m15_atr=args.assumed_spread_atr,
        additional_cost_r=args.extra_cost_r,
        max_m5_cuts_per_symbol=args.max_cuts)
    selected=preselect(retrospective["all_technical_proposals"],args.max_per_symbol)
    if not mt5.initialize():
        raise RuntimeError("MT5_TICKS_UNAVAILABLE")
    try:
        terminal=mt5.terminal_info()
        if terminal is None or terminal.trade_allowed:
            raise RuntimeError("READ_ONLY_TRADE_DISABLED_REQUIRED")
        bars={}
        for sym in frames:
            a=mt5.copy_rates_from_pos(sym,mt5.TIMEFRAME_M5,1,
                max(1500,args.max_cuts+300))
            if a is None:bars[sym]={};continue
            bars[sym]={int(x["time"]):{
                "time":int(x["time"]),"open":float(x["open"]),
                "high":float(x["high"]),"low":float(x["low"]),
                "close":float(x["close"])} for x in a}
        records=[]
        for index,s in enumerate(selected,1):
            raw_epoch=int(s["signal_at"])+offset*3600
            bar=bars.get(s["symbol"],{}).get(raw_epoch)
            if bar is None:
                outcome={"status":"RAW_M5_BAR_MISSING"}
            else:
                info=mt5.symbol_info(s["symbol"])
                ticksize=float(info.trade_tick_size or info.point) if info else 0
                arr=mt5.copy_ticks_range(
                    s["symbol"],
                    datetime.fromtimestamp(raw_epoch,timezone.utc),
                    datetime.fromtimestamp(raw_epoch+7200+90,timezone.utc),
                    mt5.COPY_TICKS_INFO)
                if arr is None:
                    outcome={"status":"BROKER_TICK_API_ERROR"}
                else:
                    outcome=tick_reconcile(s,arr,bar,raw_offset_hours=offset,
                         tick_size=ticksize,extra_cost_r=args.extra_cost_r)
            records.append({"signal":{k:s[k] for k in (
                "symbol","method","side","regime","signal_at",
                "technical_score")},
                "outcome":outcome})
            if index%10==0:
                print("TICK_RESEARCH_PROGRESS",json.dumps({
                    "checked":index,"planned":len(selected),
                    "quote_closed":sum(r["outcome"]["status"]==
                     "CLOSED_QUOTE_SIMULATION_ONLY" for r in records)}),flush=True)
    finally:
        mt5.shutdown()
    report=summarize_tick_reconciliation(records)
    report.update({
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "source":"actual broker tick BID/ASK history with next M5 BID validation",
        "reused_market_decision_engine":"MarketDecisionBrain.evaluate",
        "source_replay_candidates_total":len(retrospective["all_technical_proposals"]),
        "source_proxy_labeled_count":len(retrospective["signals"]),
        "sample_selection":"BALANCED_CHRONOLOGICAL_BY_SYMBOL_NO_OUTCOME_RANK",
        "sample_source":"ALL_PRE_OUTCOME_NATIVE_BRAIN_TECHNICAL_PROPOSALS",
        "max_per_symbol":args.max_per_symbol,
        "broker_clock_offset_now_hours":offset,
        "historical_DST_multi_months_verified":False,
        "original_signal_spread_was_assumed":True,
        "entry_sl_tp_FIXED_FROM_PRIOR_NATIVE_BRAIN_CARD":True,
        "last_month_broker_history_not_independent_unseen_OOS":True,
        "cost_stress_r_assumed":args.extra_cost_r,
        "forward_broker_fills_verified":False,
        "live_execution_authorized":False,"orders_sent":0,
        "availability":availability,
        "records":records,
    })
    path=Path(args.private_report)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
                    encoding="utf-8")
    temp.replace(path)
    print("BROKER_TICK_RECONCILIATION",json.dumps({
        "sampled":report["n_sampled"],
        "quote_completed":report["quote_completed"],
        "statuses":report["reason_counts"],
        "source_candidates":report["source_replay_candidates_total"],
        "groups":len(report["cohorts"]),
        "orders":0,"live":False
    }),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols",default="XAUUSD.vx,EURUSD.vx,NAS100.vx,GBPUSD.vx,USDJPY.vx")
    p.add_argument("--max-cuts",type=int,default=1200)
    p.add_argument("--max-per-symbol",type=int,default=10)
    p.add_argument("--assumed-spread-atr",type=float,default=.04)
    p.add_argument("--extra-cost-r",type=float,default=.15)
    p.add_argument("--private-report",required=True)
    a=p.parse_args()
    if not 150<=a.max_cuts<=1400 or not 2<=a.max_per_symbol<=24:
        p.error("bounded replay max cuts [150,1400], max per symbol [2,24]")
    run(a)


if __name__=="__main__":
    main()
