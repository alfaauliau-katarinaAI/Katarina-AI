"""KATARINA read-only robustness audit for selected 2025 XAU intraday idea.

Chosen from 2025 only: opening-range H1/H4-aligned break, UTC06, RR 2 and
3, hold six hours. 2026 has been inspected before; not virgin OOS. M5
stop-first fill proxy, broker spread, adverse ticks; no live order calls.
"""
from __future__ import annotations
import sys, json, random, statistics
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_brain_v2_from_2025 import load_bars,aggregate,build_frames,frame_last,MT5PATH,AUDIT
from intraday_session_2025 import candidates,STOP_H1ATR
import MetaTrader5 as mt5

def replay(bars,idx,side,atr,point,tick,rr=2.,hold=72,spread_multiplier=1.,slip_ticks=1,fee_r=.03):
  if idx<1 or idx>=len(bars):return None
  b=bars[idx]
  if b.spread<=0 or b.time-bars[idx-1].time>600:return None
  sp=b.spread*point*spread_multiplier
  stop=atr*STOP_H1ATR
  if stop<=2.5*sp or stop<=4*tick:return None
  entry=b.o+(sp+tick*slip_ticks if side==1 else -tick*slip_ticks)
  sl=entry-side*stop;tp=entry+side*stop*rr
  close=None
  for j in range(idx,min(idx+hold,len(bars))):
    x=bars[j]
    if j>idx and x.time-bars[j-1].time>600:break
    xs=x.spread*point*spread_multiplier
    if (x.l<=sl if side==1 else x.h+xs>=sl):
      return (-1-slip_ticks*tick/stop-fee_r,j,"SL")
    if (x.h>=tp if side==1 else x.l+xs<=tp):
      return (rr-slip_ticks*tick/stop-fee_r,j,"TP")
    last=(x.c if side==1 else x.c+xs)-side*slip_ticks*tick
    close=side*(last-entry)/stop-fee_r
  return (close,j,"TIME") if close is not None else None

def weeks_ci(trades,iterations=10000,seed=2049):
  if not trades:return None
  grouped=defaultdict(list)
  for x in trades:grouped[x["week"]].append(x["R"])
  arr=list(grouped.values());rng=random.Random(seed)
  means=[]
  for _ in range(iterations):
    sampled=[arr[rng.randrange(len(arr))] for _ in arr]
    tot=sum(sum(z) for z in sampled)
    n=sum(len(z) for z in sampled)
    means.append(tot/n)
  means.sort()
  return {"lo95":round(means[int(.025*iterations)],4),
          "hi95":round(means[int(.975*iterations)],4),
          "n_weeks":len(grouped)}
def metrics(xs):
  if not xs:return {"n":0}
  rs=[x["R"] for x in xs]
  weeks=defaultdict(float);months=defaultdict(float)
  for x in xs:
    weeks[x["week"]]+=x["R"];months[x["month"]]+=x["R"]
  pos=sum(z for z in rs if z>0);neg=-sum(z for z in rs if z<0)
  peak=eq=dd=0.
  for z in rs:
    eq+=z;peak=max(eq,peak);dd=max(dd,peak-eq)
  top=sorted(rs,reverse=True)
  trimmed=sum(rs)-sum(top[:min(5,len(top))])
  return {"n":len(rs),"avg_R":round(statistics.mean(rs),5),
          "PF":round(pos/neg,4) if neg else None,
          "active_weeks":len(weeks),"positive_active_weeks":sum(v>0 for v in weeks.values()),
          "positive_week_fraction":round(sum(v>0 for v in weeks.values())/len(weeks),4),
          "active_months":len(months),"positive_active_months":sum(v>0 for v in months.values()),
          "sum_R":round(sum(rs),4),"sum_R_excluding_top_5":round(trimmed,4),
          "max_drawdown_R":round(dd,4),"weekblock_bootstrap_ci95":weeks_ci(xs),
          "monthly_R":{k:round(v,4) for k,v in sorted(months.items())}}
def main():
  if not mt5.initialize(path=MT5PATH,timeout=15000):raise RuntimeError(mt5.last_error())
  try:
    sym="XAUUSD.vx";si=mt5.symbol_info(sym)
    point=float(si.point);tick=float(si.trade_tick_size or si.point)
    bars,_=load_bars(sym)
    a=frame_last(build_frames(aggregate(bars,3600),3600))
    b=frame_last(build_frames(aggregate(bars,14400),14400))
    signals=[x for x in candidates(bars,a,b) if x[2]=="OR_TREND_BREAK" and x[3]==6]
    print("OR_TREND_BREAK UTC06",len(signals),"signals",flush=True)
    records=[]
    for idx,side,mode,hour,atr in signals:
       if idx>=len(bars):continue
       dt=datetime.fromtimestamp(bars[idx].time,tz=timezone.utc)
       if dt.year not in (2025,2026):continue
       week=f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
       for rr in (2.,3.):
        for stress,spread_mult,slip,fee in (("BASE",1.,1,.03),
              ("SPLIT_1P5_SLIP3",1.5,3,.05),
              ("DOUBLE_SPREAD_SLIP5",2.,5,.08)):
         out=replay(bars,idx,side,atr,point,tick,rr,72,spread_mult,slip,fee)
         if out is None:continue
         val,finish,reason=out
         records.append({"year":str(dt.year),"R":val,"week":week,
          "month":dt.strftime("%Y-%m"),"date":dt.strftime("%Y-%m-%d"),
          "time":bars[idx].time,"end":bars[finish].time,"side":side,
          "rr":rr,"stress":stress,"exit":reason})
    results=[]
    for rr in (2.,3.):
      for stress in ("BASE","SPLIT_1P5_SLIP3","DOUBLE_SPREAD_SLIP5"):
        group={"2025":metrics([z for z in records if z["year"]=="2025" and z["rr"]==rr and z["stress"]==stress]),
               "2026":metrics([z for z in records if z["year"]=="2026" and z["rr"]==rr and z["stress"]==stress])}
        results.append({"RR":rr,"cost_stress":stress,"periods":group})
        print("RESULT",rr,stress,{p:(group[p]["n"],group[p]["avg_R"],
            group[p]["PF"],group[p]["weekblock_bootstrap_ci95"]) for p in ("2025","2026")},flush=True)
    # same directional trade delayed 30 minutes, as a limited timing control.
    placebo=[]
    for idx,side,mode,hour,atr in signals:
      if idx+6>=len(bars):continue
      if bars[idx+6].time-bars[idx].time!=1800:continue
      year=str(datetime.fromtimestamp(bars[idx].time,tz=timezone.utc).year)
      if year not in ("2025","2026"):continue
      start=bars[idx]
      delay=bars[idx+6]
      base=replay(bars,idx,side,atr,point,tick,2.,72)
      late=replay(bars,idx+6,side,atr,point,tick,2.,72)
      if base is None or late is None:continue
      placebo.append({"year":year,"difference_R":base[0]-late[0],"early_R":base[0],
                      "late_R":late[0]})
    test={}
    for yr in ("2025","2026"):
      r=[x for x in placebo if x["year"]==yr]
      test[yr]={"n":len(r),"avg_R_early":round(statistics.mean(x["early_R"] for x in r),5) if r else None,
          "avg_R_delayed":round(statistics.mean(x["late_R"] for x in r),5) if r else None,
          "avg_R_advantage_early":round(statistics.mean(x["difference_R"] for x in r),5) if r else None}
    report={"kind":"KATARINA_XAU_SESSION_TREND_BREAK_ROBUSTNESS_2025_2026",
      "not_true_oos":True,"selected_after_initial_screen":True,
      "cost_scenarios":{"BASE":"broker M5 spread + one tick slip per side + assumed 0.03R fee",
          "SPLIT_1P5_SLIP3":"1.5 times spread + 3 tick slips + assumed 0.05R fee",
          "DOUBLE_SPREAD_SLIP5":"2x spread + 5 tick slips + assumed 0.08R fee"},
      "yearly_metrics":results,"delayed_entry_control":test,
      "limitations":["not true real tick stops/fills","one correlated instrument",
          "2026 was previously inspected","short run around 65 trades per year",
          "not reliable weekly profit promise","news filter unverified",
          "no broker portfolio commission/funding funding"],
      "live_execution_authorized":False,"risk_governor_modified":False}
    out=AUDIT/"xau_intraday_session_robustness_2025_2026.json"
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("FILE",str(out),flush=True)
  finally:mt5.shutdown()
if __name__=="__main__":main()
