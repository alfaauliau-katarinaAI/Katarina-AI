"""Point-in-time M5/M15/H1 market-regime evidence by broker symbol.

Labels observable regimes on CLOSED history only, then looks at later
M5 closes for descriptive diagnostic evaluation. No order/PNL backtest.
No thresholds selected on outcomes, no broker actual fills, no promotion.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from bisect import bisect_right
from datetime import datetime,timedelta,timezone
from pathlib import Path
from statistics import mean
from math import isfinite
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.intelligence.market_regime_intelligence import (
    classify_regime,PROFILES,FRAME_SECONDS,STATES)
from historical_shadow_ticks import bars
UTC=timezone.utc
PERIODS=(("august","2026-08-16","2026-09-01"),
         ("september","2026-09-15","2026-10-01"),
         ("october_diagnostic","2026-10-01","2026-10-10"))
EVAL_HOURS=(1,4)

def select(ohlc,close_times,epoch,n=120):
    j=bisect_right(close_times,epoch)-1
    return ohlc[j-n+1:j+1] if j>=n-1 else []

def direction_for(label):
    return 1 if label.endswith("_UP") else -1 if label.endswith("_DOWN") else 0

def classify_symbol_period(mt5,symbol,phase,start,end):
    since=datetime.fromisoformat(start).replace(tzinfo=UTC)
    until=datetime.fromisoformat(end).replace(tzinfo=UTC)
    history={}
    complete={}
    metrics=Counter()
    for label,tf in (("M5",mt5.TIMEFRAME_M5),
                     ("M15",mt5.TIMEFRAME_M15),
                     ("H1",mt5.TIMEFRAME_H1)):
        raw=mt5.copy_rates_range(symbol,tf,since-timedelta(days=17),until)
        if raw is None or len(raw)<120:
            return [],dict(reason="insufficient_"+label+"_broker_history",
                           mt5_error=str(mt5.last_error()[0]))
        arr=bars(raw)
        history[label]=arr
        complete[label]=[r["time"]+FRAME_SECONDS[label] for r in arr]
    five=history["M5"]
    ftime=complete["M5"]
    rows=[]
    last_bar=-float("inf")
    for i in range(119,len(five)):
        entry=ftime[i]
        if not since.timestamp()<=entry<until.timestamp():
            continue
        # 30-minute observations at actual M5 close stamps. This is
        # not necessarily a market entry and not a trading signal.
        if int(entry)%1800!=0:
            continue
        metrics["inspection_points"]+=1
        view5=five[i-119:i+1]
        view15=select(history["M15"],complete["M15"],entry)
        viewh1=select(history["H1"],complete["H1"],entry)
        now=datetime.fromtimestamp(entry,UTC)
        info=classify_regime(symbol,view5,view15,viewh1,now)
        label=info["regime"]
        metrics[label]+=1
        # Descriptive forward close displacement relative to pre-label
        # ATR, not executable net quote PNL or win probability.
        future={}
        ref=float(five[i]["close"])
        atr=info["frames"].get("M5",{}).get("atr")
        for hours in EVAL_HOURS:
            target=entry+hours*3600
            idx=bisect_right(ftime,target)-1
            if idx<=i or idx>=len(five) or target>=until.timestamp():
                future[str(hours)+"h"]=None
                continue
            observed=ftime[idx]
            if target-observed>300 or observed-entry<hours*3600-300:
                future[str(hours)+"h"]=None
                continue
            if atr is None or not isfinite(atr) or atr<=0:
                future[str(hours)+"h"]=None
                continue
            outcome=(float(five[idx]["close"])-ref)/atr
            future[str(hours)+"h"]=dict(
                signed_directional_displacement_ATR=outcome,
                absolute_displacement_ATR=abs(outcome),
                aligned_with_state=(
                    outcome*direction_for(label)>0
                    if direction_for(label)!=0 else None),
                close_time_utc=datetime.fromtimestamp(observed,UTC).isoformat(),
                is_transaction_profit=False)
        rows.append(dict(symbol=symbol,study_period=phase,
            close_time_utc=now.isoformat(),regime=label,
            direction=info["direction"],reason_codes=info["reason_codes"],
            evidence_score_0_100=info["evidence_score_0_100"],
            evidence_is_profit_probability=False,
            frames=info["frames"],
            future_close_displacement=future,
            promoted_to_live=False))
    return rows,dict(metrics)

def groups(events):
    groups=[]
    for (symbol,window,label),rows in sorted(
        ((k,[e for e in events if (e["symbol"],e["study_period"],e["regime"])==k])
        for k in {(x["symbol"],x["study_period"],x["regime"]) for x in events}),
        key=lambda x:x[0]):
        aligned={};med={}
        for hours in EVAL_HOURS:
            result=[e["future_close_displacement"][str(hours)+"h"] for e in rows]
            values=[p for p in result if p is not None]
            side=[p["aligned_with_state"] for p in values
                  if p["aligned_with_state"] is not None]
            aligned[str(hours)+"h"]=dict(
                measured=len(values),
                mean_abs_close_displacement_ATR=(
                    mean(p["absolute_displacement_ATR"] for p in values)
                    if values else None),
                mean_signed_close_displacement_ATR=(
                    mean(p["signed_directional_displacement_ATR"] for p in values)
                    if values else None),
                directional_consistency=(sum(side)/len(side) if side else None),
                no_execution_costs_included=True)
        groups.append(dict(symbol=symbol,period=window,regime=label,
            n_observations=len(rows),
            distinct_UTC_days=len({e["close_time_utc"][:10] for e in rows}),
            future_close_diagnostics=aligned,
            model_validated=False,live_execution_enabled=False))
    return groups

def main():
    import MetaTrader5 as mt5
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",default=",".join(PROFILES))
    p.add_argument("--output",required=True)
    p.add_argument("--terminal",default=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe")
    p.add_argument("--which-periods",choices=("all","october"),default="all")
    a=p.parse_args()
    file=Path(a.output)
    if file.exists():raise FileExistsError("immutable_report_exists")
    symbols=a.symbols.split(",")
    if len(symbols)!=len(set(symbols)) or any(s not in PROFILES for s in symbols):
        p.error("unknown_or_duplicate_symbol")
    periods=PERIODS if a.which_periods=="all" else PERIODS[-1:]
    if not mt5.initialize(a.terminal,timeout=20000):
        raise RuntimeError("broker_research_terminal_unavailable")
    try:
        trials=[];diagnostics={}
        for symbol in symbols:
            if not mt5.symbol_select(symbol,True):
                diagnostics[symbol]=dict(reason="symbol_subscribe_failed")
                continue
            for period in periods:
                rows,counts=classify_symbol_period(mt5,symbol,*period)
                trials.extend(rows)
                diagnostics[symbol+"|"+period[0]]=counts
                print(json.dumps(dict(symbol=symbol,window=period[0],
                    observations=len(rows),counts=counts)),flush=True)
    finally:
        mt5.shutdown()
    document=dict(kind="causal_mtf_market_regime_diagnostics_v1",
       engine_version="market_regime_v1",
       distinct_instruments=list(symbols),
       periods_utc=periods,
       sample_every_minutes=30,
       regime_states=list(STATES),
       fixed_symbol_profiles=PROFILES,
       purpose="DESCRIPTIVE_REGIME_CLASSIFICATION_AND_FUTURE_CLOSED_M5_DISPLACEMENT",
       historical_market_data_not_prospective_holdout=True,
       evidence_scores_are_not_probabilities=True,
       no_actual_fills_no_bidask_PNL=True,
       not_a_regime_based_strategy_backtest=True,
       model_promotion_allowed=False,live_execution_enabled=False,
       decision="NO_TRADE",diagnostics=diagnostics,
       trials_count=len(trials),by_symbol_regime_period=groups(trials),
       classified_observations=trials)
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(json.dumps(document,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("REPORT",file,flush=True)
if __name__=="__main__":
    main()
