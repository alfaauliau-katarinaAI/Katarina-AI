"""KATARINA fixed-signal historical RR/SL/time-horizon grid, research only.

The old V2 signals are deliberately FROZEN. Experiments vary exit geometry
only (stop ATR, target:stop, max holding M5 bars). Signal samples were already
selected by earlier V2 exit lockout: results are CONDITIONAL on those signals,
not a fully independent alternative strategy backtest.

Chronological selection uses 2025. 2026 diagnostic is REUSED/INSPECTED, not
an untouched future holdout. No broker orders or changes to Risk Governor.
"""
from __future__ import annotations
import json,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_brain_v2_from_2025 import load_bars,MT5PATH,AUDIT
import MetaTrader5 as mt5

SLS=(.75,1.0,1.25,1.75)
RRS=(1.,1.5,2.,3.,5.,7.,10.)
HOLDS=(12,24,48)
def atr_array(bars,n=14):
  out=[None]*len(bars)
  if len(bars)<n+2:return out
  v=0.
  for i in range(1,len(bars)):
    b=bars[i];p=bars[i-1]
    tr=max(b.h-b.l,abs(b.h-p.c),abs(b.l-p.c))
    if i<=n:
      v+=tr
      if i==n:out[i]=v/n
    else:
      v=(v*(n-1)+tr)/n;out[i]=v
  return out
def side_of(tr, bars, i):
   st=tr["state"]
   if st.endswith("_UP"):return 1
   if st.endswith("_DOWN"):return -1
   if st!="SIDEWAYS":return 0
   b=bars[i];before=bars[max(0,i-20):i]
   if len(before)!=20:return 0
   lo=min(x.l for x in before);hi=max(x.h for x in before)
   if hi<=lo:return 0
   where=(b.c-lo)/(hi-lo)
   cdir=1 if b.c>b.o else -1 if b.c<b.o else 0
   pdir=1 if b.c>bars[i-1].c else -1 if b.c<bars[i-1].c else 0
   lower=b.l<lo and b.c>b.l
   upper=b.h>hi and b.c<b.h
   if where<=.3 and (cdir>0 or lower or pdir>0):return 1
   if where>=.7 and (cdir<0 or upper or pdir<0):return -1
   return 0
def trade_result(bars,j,side,atr,point,tick,slmult,rr,hold):
  if j<=0 or j>=len(bars):return None
  b=bars[j];spr=b.spread*point
  if b.spread<=0 or b.time-bars[j-1].time>900:return None
  stop=atr*slmult
  if stop<=2*spr or stop<4*tick:return None
  entry=b.o+(spr+tick if side==1 else -tick)
  sl=entry-side*stop;tp=entry+side*stop*rr
  for k in range(j,min(j+hold,len(bars))):
     x=bars[k]
     if k>j and x.time-bars[k-1].time>900:break
     xspr=max(x.spread,0)*point
     if side==1:
        stop_hit=x.l<=sl
        take_hit=x.h>=tp
     else:
        stop_hit=x.h+xspr>=sl
        take_hit=x.l+xspr<=tp
     if stop_hit:return (-1.0-tick/stop-.03,k,"STOP")
     if take_hit:return (rr-tick/stop-.03,k,"TARGET")
     final=(x.c if side==1 else x.c+xspr)-tick*side
     pnl=side*(final-entry)/stop-.03
  return (pnl,k,"TIME")
def stats(xs):
  if not xs:return {"n":0,"mean_R":None,"pf":None}
  n=len(xs);gross_pos=sum(x for x in xs if x>0);gross_neg=-sum(x for x in xs if x<0)
  return {"n":n,"mean_R":round(sum(xs)/n,6),"pf":round(gross_pos/gross_neg,4) if gross_neg else None,
          "win_rate":round(sum(x>0 for x in xs)/n,4)}
def screen_symbol(src):
  sym=src["symbol"];si=mt5.symbol_info(sym)
  if si is None:return {"symbol":sym,"error":"missing symbol"}
  bars,bar_source=load_bars(sym)
  atr=atr_array(bars)
  ix={x.time:i for i,x in enumerate(bars)}
  split=defaultdict(list)
  skip=Counter()
  for raw in src["trades"]:
     i=ix.get(raw["time"])
     if i is None or i+1>=len(bars) or atr[i] is None:skip["missing_source_or_atr"]+=1;continue
     side=side_of(raw,bars,i)
     if side==0:skip["unrecoverable_side"]+=1;continue
     split[raw["setup"]].append((i+1,side,float(atr[i]),raw["period"]))
  combos=[]
  price_point=float(si.point);tick=float(si.trade_tick_size or si.point)
  for mode,signals in sorted(split.items()):
    if len(signals)<30:continue
    for slmult in SLS:
     for rr in RRS:
      for hold in HOLDS:
       outcomes={"2025":[],"2026":[]}
       ends={"2025":-1,"2026":-1}
       months={"2025":set(),"2026":set()}
       for j,side,at,yr in signals:
          if j<=ends[yr]:continue
          rrtrade=trade_result(bars,j,side,at,price_point,tick,slmult,rr,hold)
          if rrtrade is None:continue
          pnl,end,reason=rrtrade
          outcomes[yr].append(pnl)
          ends[yr]=end
          months[yr].add(datetime.fromtimestamp(bars[j].time,tz=timezone.utc).strftime("%Y-%m"))
       train=stats(outcomes["2025"]);test=stats(outcomes["2026"])
       combos.append({"mode":mode,"sl_atr":slmult,"rr":rr,"hold_bars":hold,
           "2025":train,"2026":test,"months_2025":len(months["2025"]),
           "pass_2025":train["n"]>=80 and train["mean_R"]>=.05 and train["pf"] is not None and train["pf"]>=1.12 and len(months["2025"])>=5})
  passed=[x for x in combos if x["pass_2025"]]
  # train-only selection, 2026 is locked for reporting, not tuning
  winner= max(passed,key=lambda x:(x["2025"]["mean_R"],x["2025"]["n"])) if passed else None
  per_mode={}
  for mode in sorted(split):
     ls=[x for x in combos if x["mode"]==mode and x["2025"]["n"]>=80]
     if ls:
       best=max(ls,key=lambda x:x["2025"]["mean_R"])
       per_mode[mode]={"best_2025_train":best,"passed_2025":sum(x["pass_2025"] for x in ls),
         "trials":len(ls),"positive_2025":sum(x["2025"]["mean_R"]>0 for x in ls),
         "positive_2026":sum(x["2026"]["mean_R"] is not None and x["2026"]["mean_R"]>0 for x in ls)}
  print("FINISHED",sym,"source",bar_source,"signals",{k:len(v) for k,v in split.items()},
    "trials",len(combos),"passed",len(passed),
    "winner",winner,flush=True)
  return {"symbol":sym,"source":bar_source,
          "source_signal_count":len(src["trades"]), "used_by_mode":{k:len(v) for k,v in split.items()},
          "skips":dict(skip),"tested_configurations":len(combos),
          "2025_passing_count":len(passed),"best_2025":winner,"per_mode":per_mode,
          "all_candidates":combos}
def main():
  p=AUDIT/"backtest_adaptive_brain_v2_from_2025.json"
  src=json.loads(p.read_text(encoding="utf-8"))
  report={"kind":"KATARINA_RR_GRID_2025_2026","date":"2026-10-11",
     "source_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
     "definition":{"stop_atr":SLS,"target_to_stop":RRS,
       "max_hold_M5_bars":HOLDS,"signal_source":"previous V2 signals only",
       "timeframe":"M5 entries + M15 H1 regime from previous model",
       "entry_next_M5_open":True, "intrabar_ambiguous_SL_first":True,
       "cost_model":"historical MT5 bar spread + one tick adverse per side + ASSUMED 0.03R fees",
       "2025_selection_only":True,"2026_already_inspected":True,
       "note":"Reuses baseline signals filtered by previously chosen exit timing: conditional test, not fair fully independent variant portfolio",
       "no_real_fill_proof":True},
     "live_execution_enabled":False,"model_promotion_allowed":False,"symbols":[]}
  if not mt5.initialize(path=MT5PATH,timeout=15000):raise RuntimeError(mt5.last_error())
  try:
    for x in src["symbol_results"]:
      try:out=screen_symbol(x)
      except Exception as e:
        import traceback
        out={"symbol":x["symbol"],"error":str(e),"traceback":traceback.format_exc()[-1000:]}
      report["symbols"].append(out)
  finally:mt5.shutdown()
  path=AUDIT/"katarina_rr_grid_from_2025_2026.json"
  path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
  print("REPORT",str(path),flush=True)
if __name__=="__main__": main()
