"""KATARINA event-driven intraday hypothesis test, research only.

Predeclared three price-action families × two fixed UTC sessions, two
holding periods and R ratios. Uses closed M5/H1/H4, next M5 open, actual
historical MT5 bar spread; adverse tick slippage and assumed 0.03R fee.
No MT5 trade_send, no live changes. Chronological years shown separately.
2026 is previously inspected, NOT a fresh untouched holdout.
"""
from __future__ import annotations
import json,sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/"scripts"/"research"))
from backtest_brain_v2_from_2025 import load_bars, aggregate,build_frames,frame_last,getframe,MT5PATH,AUDIT
import MetaTrader5 as mt5

SYMBOLS=("XAUUSD.vx","NAS100.vx","US30.vx","JPN225.vx","EURUSD.vx","GBPUSD.vx","USDJPY.vx")
WINDOWS=(6,12)                # fixed UTC opening-range anchors; not exchange DST corrected
MODES=("OR_TREND_BREAK","OR_FAILED_BREAK","H1_H4_PULLBACK")
RRS=(1.25,2.,3.)
HOLD_BARS=(36,72)             # 3h/6h, intraday
STOP_H1ATR=.55                # one fixed, not tuned to inspected data
def is_trading_contiguous(bars,lo,hi):
    return all(0<bars[i].time-bars[i-1].time<=600 for i in range(lo+1,hi+1))
def sim(bars,j,side,h1atr,point,tick,rr,hold):
    if j<1 or j>=len(bars):return None
    b=bars[j]
    if b.spread<=0 or b.time-bars[j-1].time>600:return None
    spr=b.spread*point
    risk=h1atr*STOP_H1ATR
    if risk<=2.5*spr or risk<=4*tick:return None
    entry=b.o+(spr+tick if side==1 else -tick)
    sl=entry-side*risk
    tp=entry+side*risk*rr
    final=None;last=j
    for k in range(j,min(j+hold,len(bars))):
        x=bars[k]
        if k>j and x.time-bars[k-1].time>600:break
        final=(x.c if side==1 else x.c+x.spread*point)-side*tick
        last=k
        slhit=(x.l<=sl if side==1 else x.h+x.spread*point>=sl)
        tphit=(x.h>=tp if side==1 else x.l+x.spread*point<=tp)
        if slhit:return (-1.-tick/risk-.03,k,"SL")
        if tphit:return (rr-tick/risk-.03,k,"TP")
    if final is None:return None
    return ((final-entry)*side/risk-.03,last,"TIME")
def stats(trades):
    v=[x["R"] for x in trades];n=len(v)
    if not n:return {"n":0,"mean_R":None,"PF":None,"weekly_pos_pct":None,"weeks":0,"max_dd_R":None}
    gain=sum(x for x in v if x>0);loss=-sum(x for x in v if x<0)
    peak=cur=dd=0.
    byweek=defaultdict(float)
    for x in trades:
       val=x["R"];cur+=val;peak=max(peak,cur);dd=max(dd,peak-cur)
       byweek[x["iso_week"]]+=val
    weeks=len(byweek)
    return {"n":n,"mean_R":round(sum(v)/n,5),
        "PF":round(gain/loss,3) if loss>0 else None,
        "weeks":weeks,"weekly_pos_pct":round(100*sum(x>0 for x in byweek.values())/weeks,2),
        "max_dd_R":round(dd,2),"sum_R":round(sum(v),2)}
def candidates(bars, index_h1,index_h4):
    # One independent session candidate per mode each day; no intrabar lookahead.
    days=defaultdict(list)
    for i,b in enumerate(bars):
      u=datetime.fromtimestamp(b.time,tz=timezone.utc)
      days[u.strftime("%Y-%m-%d")].append(i)
    done=[]
    for day,ii in days.items():
       for hh in WINDOWS:
         anchor=int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())+hh*3600
         opening=[i for i in ii if anchor<=bars[i].time<anchor+3600]
         if len(opening)!=12 or bars[opening[0]].time!=anchor or not is_trading_contiguous(bars,opening[0],opening[-1]):
            continue
         hi=max(bars[i].h for i in opening)
         lo=min(bars[i].l for i in opening)
         # inspect only bars AFTER opening range has already closed
         inspect=[i for i in ii if anchor+3600<=bars[i].time<anchor+3*3600]
         chosen=set()
         for i in inspect:
            if len(chosen)==len(MODES):break
            if i<60 or i+1>=len(bars) or not is_trading_contiguous(bars,i-20,i):continue
            b=bars[i]
            t=b.time+300
            h1=getframe(index_h1,t)
            h4=getframe(index_h4,t)
            if h1 is None or h4 is None or h1.atr<=0:continue
            if h1.closed_at_utc.timestamp()>t or h4.closed_at_utc.timestamp()>t:raise RuntimeError("future frame")
            body=abs(b.c-b.o)
            # trend only when H1+H4 both agree and H4 trend is not very weak
            aligned=h1.direction if h1.direction==h4.direction and h1.direction!=0 and h4.efficiency>=.22 else 0
            # opening-range breakout confirmed on CLOSE with minimal distance
            side=1 if b.c>hi+.03*h1.atr else -1 if b.c<lo-.03*h1.atr else 0
            if ("OR_TREND_BREAK" not in chosen and side!=0 and side==aligned):
                chosen.add("OR_TREND_BREAK");done.append((i+1,side,"OR_TREND_BREAK",hh,h1.atr))
            # failed excursion with wick and close back into known opening range
            upwick=b.h-max(b.o,b.c);lowwick=min(b.o,b.c)-b.l
            if "OR_FAILED_BREAK" not in chosen:
                if b.h>hi+.025*h1.atr and b.c<hi and upwick>=max(.05*h1.atr,body):
                   chosen.add("OR_FAILED_BREAK");done.append((i+1,-1,"OR_FAILED_BREAK",hh,h1.atr))
                elif b.l<lo-.025*h1.atr and b.c>lo and lowwick>=max(.05*h1.atr,body):
                   chosen.add("OR_FAILED_BREAK");done.append((i+1,1,"OR_FAILED_BREAK",hh,h1.atr))
            if "H1_H4_PULLBACK" not in chosen and aligned!=0:
                past=bars[i-20:i]
                mean=sum(x.c for x in past)/20
                prior=bars[i-1]
                if aligned==1 and prior.l<mean and b.c>mean and b.c>b.o:
                  chosen.add("H1_H4_PULLBACK");done.append((i+1,1,"H1_H4_PULLBACK",hh,h1.atr))
                elif aligned==-1 and prior.h>mean and b.c<mean and b.c<b.o:
                  chosen.add("H1_H4_PULLBACK");done.append((i+1,-1,"H1_H4_PULLBACK",hh,h1.atr))
    return done
def run(sym):
    si=mt5.symbol_info(sym)
    bars,source=load_bars(sym)
    idx1=frame_last(build_frames(aggregate(bars,3600),3600))
    idx4=frame_last(build_frames(aggregate(bars,14400),14400))
    signals=candidates(bars,idx1,idx4)
    print("SYMBOL",sym,"bars",len(bars),"session_signals",len(signals),flush=True)
    bycfg=defaultdict(list)
    point=float(si.point);tick=float(si.trade_tick_size or si.point)
    for j,side,mode,hh,at in signals:
       yr=datetime.fromtimestamp(bars[j].time,tz=timezone.utc).year
       if yr not in (2025,2026):continue
       for rr in RRS:
         for hold in HOLD_BARS:
           v=sim(bars,j,side,at,point,tick,rr,hold)
           if v is None:continue
           r,end,why=v
           t=datetime.fromtimestamp(bars[j].time,tz=timezone.utc)
           y=str(t.year)
           bycfg[(mode,hh,rr,hold,y)].append({"time":bars[j].time,"end":bars[end].time,
             "R":r,"result":why,"iso_week":str(t.isocalendar().year)+"-W"+f"{t.isocalendar().week:02d}"})
    candidates_report=[]
    for mode in MODES:
      for hh in WINDOWS:
       for rr in RRS:
        for hold in HOLD_BARS:
          train=bycfg.get((mode,hh,rr,hold,"2025"),[])
          eval_=bycfg.get((mode,hh,rr,hold,"2026"),[])
          a=stats(train);b=stats(eval_)
          # Training selection no more than one market attempt/session/day; high sample/frequency requirement.
          passdev=a["n"]>=60 and a["weeks"]>=16 and a["mean_R"]>=.08 and a["PF"]>=1.18
          candidates_report.append({"mode":mode,"utc_start":hh,"rr":rr,"hold_minutes":hold*5,
            "2025":a,"2026":b,"dev_pass":passdev})
    passing=[x for x in candidates_report if x["dev_pass"]]
    return {"symbol":sym,"source":source,"total_closed_M5":len(bars),
     "signal_events":len(signals),"tested":len(candidates_report),
     "2025_pass_count":len(passing),
     "2026_positive_among_2025_pass":sum(x["2026"]["mean_R"] is not None and x["2026"]["mean_R"]>0 for x in passing),
     "best_2025_eligible":max(passing,key=lambda x:x["2025"]["mean_R"]) if passing else None,
     "all":candidates_report}
def main():
    report={"kind":"KATARINA_INDEPENDENT_INTRADAY_EVENT_STUDY_2025_2026",
      "2025_development_only":True,"2026_historically_reused":True,
      "sessions_utc":WINDOWS,"RRS":RRS,"hold_bars":HOLD_BARS,"stops_h1_atr":STOP_H1ATR,
      "notes":["Independent event hypotheses, not same signal list as prior scalp",
       "M5 OHLC stop-first execution proxy: NOT real tick fill simulation",
       "0.03R fee ASSUMED; one adverse tick per side",
       "Session hours UTC do not adjust for UK/US DST",
       "No full portfolio equity/margin or account cash modelling",
       "Research only, risk governor unchanged"],
      "live_execution_enabled":False,"model_promotion_allowed":False,"symbols":[]}
    if not mt5.initialize(path=MT5PATH,timeout=15000):raise RuntimeError(mt5.last_error())
    try:
       for sym in SYMBOLS:
          try:x=run(sym)
          except Exception as ex:
             import traceback
             x={"symbol":sym,"error":str(ex),"trace":traceback.format_exc()[-2000:]}
          report["symbols"].append(x)
          print("RESULT",sym,"2025_pass",x.get("2025_pass_count"),"2026_positive",x.get("2026_positive_among_2025_pass"),flush=True)
    finally:mt5.shutdown()
    out=AUDIT/"katarina_intraday_session_2025_2026.json"
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("FILE",str(out),flush=True)
if __name__=="__main__":main()
