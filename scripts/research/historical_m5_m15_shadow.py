"""Exploratory M5-entry/M15-context replay, deliberately separate from M1 study.

No historical macro vintages, no commission/slippage and no SL/TP path.
Never authorizes live trading or replaces the original 0.15 M1 spread gate.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
from statistics import mean
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.intelligence.perception.screening import features
from katarina.intelligence.perception.technical_regime import classify_market_regime
from katarina.intelligence.shadow.shadow_hypotheses import propose
from historical_shadow_ticks import bars, intact, first_quote, snapshot_hash

UTC=timezone.utc
HORIZON=900
WINDOW=90
FAMILY="trend_impulse_break_m5_m15_v1"


def scan_symbol(mt5,symbol,start,end,limit):
    info=mt5.symbol_info(symbol)
    if info is None:
        return dict(symbol=symbol,reason="symbol_unknown")
    if info.trade_mode not in (1,2,4):
        return dict(symbol=symbol,reason="broker_trade_mode_denied")
    if not mt5.symbol_select(symbol,True):
        return dict(symbol=symbol,reason="symbol_subscription_failed")
    warmup=start-timedelta(days=6)
    raw5=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M5,warmup,end)
    raw15=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M15,warmup,end)
    if raw5 is None or raw15 is None:
        return dict(symbol=symbol,reason="bar_history_unavailable",
                    broker_error=mt5.last_error())
    m5,m15=bars(raw5),bars(raw15)
    closes15=[int(b["time"]+900) for b in m15]
    counters=Counter()
    signals=[]
    start_ts,end_ts=start.timestamp(),end.timestamp()
    last_until=float("-inf")
    allowed={1:["BUY"],2:["SELL"],4:["BUY","SELL"]}[info.trade_mode]
    for i in range(119,len(m5)):
        current=m5[i]
        stamp=current["time"]+300
        if stamp<start_ts or stamp>=end_ts:
            continue
        counters["m5_closed_checked"]+=1
        if stamp < last_until:
            counters["overlap_skipped"]+=1
            continue
        if i < 21: continue
        baseline=mean(float(b["tick_volume"]) for b in m5[i-20:i])
        if baseline <= 0 or current["tick_volume"] < baseline*1.25:
            continue
        width=current["high"]-current["low"]
        if width<=0 or abs(current["close"]-current["open"]) < .6*width:
            continue
        if not (current["close"]>max(b["high"] for b in m5[i-6:i])
                or current["close"]<min(b["low"] for b in m5[i-6:i])):
            continue
        counters["quick_prefilter_pass"]+=1
        j=bisect_right(closes15,stamp)-1
        if j<119:
            counters["insufficient_m15_warmup"]+=1
            continue
        five=m5[i-119:i+1]
        fifteen=m15[j-119:j+1]
        if not intact(five,300) or not intact(fifteen,900):
            counters["bar_gap"]+=1
            continue
        now=datetime.fromtimestamp(stamp,UTC)
        try:
            signal_features=features(five,300,now)
            context_features=features(fifteen,900,now)
        except ValueError:
            counters["features_invalid"]+=1
            continue
        if context_features["close_age_seconds"]>1800:
            counters["stale_context"]+=1
            continue
        regime=classify_market_regime(context_features)
        # Reuse fixed directional breakout logic by adapting the two closed
        # frames. The original helper's +60 timestamp is NOT used as M5 time.
        hypothesis=propose(dict(m1=signal_features,m5=context_features,
                        m1_bars=five,regime_detail=regime,allowed_sides=allowed))
        if not hypothesis:
            counters["hypothesis_rejected"]+=1
            continue
        counters["hypothesis_pass"]+=1
        if len(signals)>=limit:
            counters["cap_reached"]+=1
            break
        entry,reason=first_quote(mt5,symbol,stamp,WINDOW)
        if reason:
            counters["entry_"+reason]+=1
            continue
        spread_atr=(entry["ask"]-entry["bid"])/signal_features["atr"]
        cost_pass=spread_atr<=.15
        counters["cost_pass" if cost_pass else "cost_rejected"]+=1
        last_until=entry["time"]+HORIZON
        exit_quote,reason=first_quote(mt5,symbol,last_until,WINDOW)
        if reason:
            counters["exit_"+reason]+=1
            continue
        side=hypothesis[0]["side"]
        midpoint=(entry["bid"]+entry["ask"])/2
        delta=(exit_quote["bid"]-entry["ask"] if side=="BUY"
               else entry["bid"]-exit_quote["ask"])
        exit_mid=(exit_quote["bid"]+exit_quote["ask"])/2
        midpoint_move=(exit_mid-midpoint)*(1 if side=="BUY" else -1)
        signals.append(dict(symbol=symbol,family=FAMILY,side=side,regime=regime,
          signal_bar_close_utc=now.isoformat(),
          context_bar_close_utc=context_features["last_closed_utc"],
          signal_atr=signal_features["atr"],
          entry_tick_utc=datetime.fromtimestamp(entry["time"],UTC).isoformat(),
          exit_tick_utc=datetime.fromtimestamp(exit_quote["time"],UTC).isoformat(),
          entry_bid=entry["bid"],entry_ask=entry["ask"],
          exit_bid=exit_quote["bid"],exit_ask=exit_quote["ask"],
          entry_spread_atr=spread_atr,cost_screen_pass=cost_pass,
          quoted_markout_bps=delta/midpoint*10000,
          midpoint_markout_bps=midpoint_move/midpoint*10000,
          m5_evidence_sha256=snapshot_hash(five),
          m15_evidence_sha256=snapshot_hash(fifteen),
          historical_macro_context="UNAVAILABLE_POINT_IN_TIME",
          is_realized_pnl=False,live_risk_authorized=False))
        counters["quotes_measured"]+=1
    return dict(symbol=symbol,current_trade_mode=int(info.trade_mode),
      m5_bars_available=len(m5),m15_bars_available=len(m15),
      counts=dict(counters),signals=signals)


def main():
    import MetaTrader5 as mt5
    p=argparse.ArgumentParser()
    p.add_argument("--terminal",default=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe")
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    p.add_argument("--symbols",default="XAUUSD,EURUSD,GBPUSD,USDJPY,XAGUSD,US30,NAS100")
    p.add_argument("--max-signals-per-symbol",type=int,default=200)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    start=datetime.fromisoformat(a.start).replace(tzinfo=UTC)
    end=datetime.fromisoformat(a.end).replace(tzinfo=UTC)
    if end<=start or end>datetime.now(UTC):
        p.error("invalid_historical_window")
    if not 1<=a.max_signals_per_symbol<=500:p.error("invalid_cap")
    out=Path(a.output)
    if out.exists():raise FileExistsError("immutable output exists")
    if not mt5.initialize(a.terminal,timeout=20000):
        raise RuntimeError("research_terminal_unavailable")
    try:
        catalog=[s.name for s in (mt5.symbols_get() or ())]
        names=(sorted(catalog) if a.symbols=="all" else
               [next((s for s in catalog if s.upper().startswith(x.strip().upper())),None)
                for x in a.symbols.split(",")])
        records=[]
        for name in names:
            if not name: continue
            try:
                item=scan_symbol(mt5,name,start,end,a.max_signals_per_symbol)
            except Exception as exc:
                item=dict(symbol=name,reason="scan_exception",
                          error_type=type(exc).__name__)
            records.append(item)
            print(json.dumps(dict(symbol=name,signals=len(item.get("signals",[])),
                    m5=item.get("m5_bars_available",0),
                    reason=item.get("reason"))),flush=True)
    finally:
        mt5.shutdown()
    samples=[s for item in records for s in item.get("signals",[])]
    groups={}
    for side in ("BUY","SELL"):
        for costpass in (True,False):
            subset=[s["quoted_markout_bps"] for s in samples
                    if s["side"]==side and s["cost_screen_pass"]==costpass]
            groups[side+("_pass" if costpass else "_reject")]=dict(
                n=len(subset),mean_bps=mean(subset) if subset else None,
                positive_fraction=sum(x>0 for x in subset)/len(subset) if subset else None)
    result=dict(report_version="historical_m5_m15_shadow_v1",
        family=FAMILY,period=dict(start=a.start,end_exclusive=a.end),
        signal_timeframe="M5",context_timeframe="M15",horizon_seconds=HORIZON,
        quote_source="MT5_actual_historical_bid_ask",
        original_m1_strategy_unchanged=True,
        spread_to_m5_atr_limit=.15,
        research_scope="EXPLORATORY_REUSED_HISTORY_NOT_PROSPECTIVE",
        historical_macro_context="UNAVAILABLE_POINT_IN_TIME",
        commission_included=False,slippage_included=False,
        stop_loss_take_profit_paths_tested=False,
        model_promotion_allowed=False,live_execution_enabled=False,
        symbols_scanned=len(records),signals_observed=len(samples),
        summary=groups,symbols=records)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("RESULT "+json.dumps(dict(signals=len(samples),summary=groups)),flush=True)
    print("REPORT "+str(out),flush=True)

if __name__=="__main__":
    main()
