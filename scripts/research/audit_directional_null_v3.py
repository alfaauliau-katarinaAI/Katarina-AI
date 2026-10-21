"""KATARINA root-cause audit: identical-time counterfactual reverse-side controls.

This is a matched comparison of *historical previously sampled* technical
signals. It uses precisely the baseline historical fill function, not a new
optimizer. Because 2025/2026 history has been viewed, results are diagnostics,
not independent statistical evidence of a profitable strategy.
"""
from __future__ import annotations
import json,sys,collections,statistics,math
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import OUT,get_bars,true_range_at,hypothetic_fill,stats,split
SYMBOLS=("XAUUSD.vx","EURUSD.vx","US30.vx")
TARGET=OUT/"root_cause_v3"
TARGET.mkdir(parents=True,exist_ok=True)
def output(report):
  path=TARGET/"ROOT_CAUSE_DIAGNOSTIC.json"
  path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
  print("AUDIT_FINAL",json.dumps(report,ensure_ascii=False),flush=True)
def main():
  if not mt5.initialize():raise RuntimeError("MT5 unavailable")
  t=mt5.terminal_info()
  if t is None or t.trade_allowed:raise RuntimeError("Broker trading not disabled; do not proceed")
  result={};all_actual=[];all_reverse=[];all_pairs=[];issues=[]
  for sym in SYMBOLS:
    mt5.symbol_select(sym,True)
    point=float(mt5.symbol_info(sym).point)
    arr=get_bars(sym,mt5.TIMEFRAME_M5,90000)
    if arr is None:raise RuntimeError("No M5 "+sym)
    times=arr["time"].astype(np.int64)
    source=json.loads((OUT/(sym.replace(".","_")+".json")).read_text(encoding="utf-8"))
    samples=source["events"];observed=[];reverse=[];matched=[];audit=collections.Counter()
    for row in samples:
      idx=int(np.searchsorted(times,int(row["entry_time"]),side="left"))-1
      if idx<35 or idx>=len(times)-25 or int(times[idx])+300!=int(row["entry_time"]):
        audit["missing_next_open"]+=1;continue
      atr=true_range_at(arr,idx)
      if not atr or not math.isfinite(atr):
        audit["invalid_atr"]+=1;continue
      side=1 if row["side"]=="BUY" else -1
      old=hypothetic_fill(arr,idx,side,point,atr)
      opp=hypothetic_fill(arr,idx,-side,point,atr)
      if old is None or opp is None:
        audit["fill_rejected"]+=1;continue
      if abs(old["R"]-row["R"])>0.0001:
        audit["replication_mismatch"]+=1
      actual=dict(row,R=float(old["R"]))
      control=dict(row,R=float(opp["R"]))
      observed.append(actual);reverse.append(control)
      matched.append({"entry_time":int(row["entry_time"]),"side":row["side"],
          "playbook":row["playbook"],"market_state":row["regime"],
          "original_R":float(old["R"]),"opposite_R":float(opp["R"]),
          "edge_at_matched_time_R":float(old["R"]-opp["R"])})
    all_actual.extend(observed);all_reverse.extend(reverse);all_pairs.extend(matched)
    deltas=[x["edge_at_matched_time_R"] for x in matched]
    result[sym]={"baseline":stats(observed),"same_time_reverse_side":stats(reverse),
      "paired_delta_R":round(statistics.mean(deltas),6) if deltas else None,
      "median_paired_delta_R":round(statistics.median(deltas),6) if deltas else None,
      "matched":len(matched),"audit":dict(audit),
      "by_playbook":{p:{"original":stats([x for x in observed if x["playbook"]==p]),
                        "reverse":stats([x for x in reverse if x["playbook"]==p])}
                     for p in sorted({x["playbook"] for x in observed})}}
    print("PAIR",sym,"matched",len(matched),"original",result[sym]["baseline"]["avg_R"],
          "opposite",result[sym]["same_time_reverse_side"]["avg_R"],
          "direction_delta",result[sym]["paired_delta_R"],"audit",dict(audit),flush=True)
  mt5.shutdown()
  all_actual.sort(key=lambda x:x["exit_time"])
  all_reverse.sort(key=lambda x:x["exit_time"])
  rep=dict(symbols=SYMBOLS,matched=len(all_pairs),
     original=stats(all_actual),counterfactual_reverse=stats(all_reverse),
     per_pair=result,
     by_period={p:{
          "original":stats([x for x in all_actual if split(x["entry_time"])==p]),
          "counterfactual_reverse":stats([x for x in all_reverse if split(x["entry_time"])==p])}
          for p in ("2025_available","2026_Jan_May","2026_Jun_Oct")},
     assumptions=[
       "Same original decision times, same M5 spread/ATR SL/TP and 24-bar maximum hold",
       "Reverse-direction model is a diagnostic negative control; not a tradable inverse strategy",
       "Historical news was not verified, market server UTC/DST not reconciled",
       "Results may be selected/overfit: 2025/2026 data already inspected",
       "Profit R per trade is not account growth, and sampled 1/36 M5 bars",
       "Trade terminal read-only; no brokerage order submitted",
     ],live_execution_authorized=False)
  output(rep)
if __name__=="__main__":main()