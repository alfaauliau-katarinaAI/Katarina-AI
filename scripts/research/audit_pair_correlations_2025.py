"""KATARINA multi-pair portfolio correlation evidence from broker M5 daily closes.

No orders, no rebalancing, no Risk Governor changes. Pearson on overlapping
UTC trading-day log returns 2025/2026 (not session-local; holidays missing).
"""
from __future__ import annotations
import sys, json, math, statistics
from datetime import datetime, timezone
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/"scripts"/"research"))
from backtest_brain_v2_from_2025 import load_bars,AUDIT,MT5PATH
import MetaTrader5 as mt5
SYMS=["XAUUSD.vx","NAS100.vx","US30.vx","JPN225.vx","EURUSD.vx","GBPUSD.vx","USDJPY.vx"]
def correlation(a,b):
  keys=sorted(set(a)&set(b));n=len(keys)
  if n<40:return {"n":n,"pearson":None}
  x=[a[k] for k in keys];y=[b[k] for k in keys]
  mx=statistics.mean(x);my=statistics.mean(y)
  x2=sum((z-mx)**2 for z in x)
  y2=sum((z-my)**2 for z in y)
  if x2<=0 or y2<=0:return {"n":n,"pearson":None}
  return {"n":n,"pearson":round(sum((xi-mx)*(yi-my) for xi,yi in zip(x,y))/math.sqrt(x2*y2),4)}
def main():
  if not mt5.initialize(path=MT5PATH,timeout=15000):raise RuntimeError(mt5.last_error())
  try:
   maps={}
   for sym in SYMS:
    bars,_=load_bars(sym)
    daily={}
    for z in bars:
     day=datetime.fromtimestamp(z.time,tz=timezone.utc).strftime("%Y-%m-%d")
     daily[day]=z.c
    ds=sorted(daily)
    vals={}
    for i in range(1,len(ds)):
      now=datetime.fromisoformat(ds[i])
      # Reject multi-day holidays/weekends with too long a stale previous close? Weekend allowed.
      if (now-datetime.fromisoformat(ds[i-1])).days>4:continue
      if daily[ds[i-1]]<=0:continue
      vals[ds[i]]=math.log(daily[ds[i]]/daily[ds[i-1]])
    maps[sym]=vals
   results=[]
   for i,a in enumerate(SYMS):
    for b in SYMS[i+1:]:
     x=correlation(maps[a],maps[b])
     results.append({"a":a,"b":b,**x,"same_side_exposure_warning":abs(x["pearson"])>=.65 if x["pearson"] is not None else False})
   report={"kind":"KATARINA_MULTI_PAIR_DAILY_CLOSE_CORRELATION_DIAGNOSTIC",
    "method":"daily UTC last bid close log-returns, shared days, historical M5 bars",
    "not_timevarying_or_causal_relationship":True,"no_risk_settings_changed":True,
    "correlation_of_returns_not_strategy_PnL":True,"pairs":results}
   out=AUDIT/"multi_pair_daily_correlations_2025_2026.json"
   out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
   print(json.dumps(sorted(results,key=lambda r:abs(r["pearson"] or 0),reverse=True)[:16],indent=2))
  finally:mt5.shutdown()
if __name__=="__main__":main()
