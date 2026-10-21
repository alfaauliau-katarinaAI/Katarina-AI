"""Independent index and FX intraday playbooks, chronological broker M5 research.

INDEX: US cash opening drive retest/failed extension (UTC 13:30/14:30 approximations).
FX: Asian range liquidity sweep and London continuation/retest.
Predefined two variants per asset family; RR2, SL 0.8x H1 ATR, 3h hold,
closed M5 signals and completed H1/H4/D1 only. Research, not execution.
"""
from __future__ import annotations
import sys,json
from datetime import datetime,timezone
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_brain_v2_from_2025 import load_bars,aggregate,build_frames,frame_last,getframe,MT5PATH,AUDIT
from intraday_tool_method_matrix_2025 import replay,metrics
import MetaTrader5 as mt5
INDEX=("NAS100.vx","US30.vx","JPN225.vx")
FX=("EURUSD.vx","GBPUSD.vx","USDJPY.vx")
RR=2.
STOP_MULT=.8
HOLD_BARS=36

def contiguous(bars,indexes):
 return bool(indexes) and all(bars[b].time-bars[a].time==300 for a,b in zip(indexes,indexes[1:]))

def add_event(events,bars,j,side,typ,atr):
 if j>=len(bars) or side==0 or atr<=0:return
 if bars[j].time-bars[j-1].time!=300:return
 events.append((j,side,typ,atr))

def indices(bars,h1,h4):
 byday=defaultdict(list)
 for i,b in enumerate(bars):
  dt=datetime.fromtimestamp(b.time,tz=timezone.utc)
  byday[dt.date().isoformat()].append(i)
 events=[]
 for day,rows in byday.items():
  start=int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
  for anchor_hour in (13.5,14.5):
   anchor=start+int(anchor_hour*3600)
   initial=[i for i in rows if anchor<=bars[i].time<anchor+1800]
   if len(initial)!=6 or not contiguous(bars,initial):continue
   hi=max(bars[i].h for i in initial);lo=min(bars[i].l for i in initial)
   break_side=0;break_idx=None;used=set()
   later=[i for i in rows if anchor+1800<=bars[i].time<anchor+3*3600]
   for i in later:
    if i<=initial[-1] or i+1>=len(bars) or bars[i].time-bars[i-1].time!=300:continue
    b=bars[i];t=b.time+300
    f1=getframe(h1,t);f4=getframe(h4,t)
    if f1 is None or f4 is None or f1.atr<=0:continue
    direction=f1.direction if f1.direction==f4.direction and f1.direction else 0
    if b.c>hi+.04*f1.atr:now_side=1
    elif b.c<lo-.04*f1.atr:now_side=-1
    else:now_side=0
    if break_idx is None and now_side!=0:
      break_idx=i;break_side=now_side
    if ("OPEN_RETEST" not in used and break_idx is not None and
        i>break_idx and direction==break_side and f1.adx>=18):
      mid=hi if break_side>0 else lo
      tol=.14*f1.atr
      near=(b.l<=mid+tol and b.c>mid if break_side>0
            else b.h>=mid-tol and b.c<mid)
      body=(b.c>b.o if break_side>0 else b.c<b.o)
      if near and body:
       add_event(events,bars,i+1,break_side,f"OPEN_RETEST_{int(anchor_hour*60)}",f1.atr)
       used.add("OPEN_RETEST")
    if ("OPEN_FAILED" not in used and f1.adx<=24):
      wick_hi=b.h-max(b.o,b.c);wick_lo=min(b.o,b.c)-b.l
      body=abs(b.c-b.o)
      if b.h>hi+.06*f1.atr and b.c<hi and wick_hi>=body:
       add_event(events,bars,i+1,-1,f"OPEN_FAILED_{int(anchor_hour*60)}",f1.atr)
       used.add("OPEN_FAILED")
      elif b.l<lo-.06*f1.atr and b.c>lo and wick_lo>=body:
       add_event(events,bars,i+1,1,f"OPEN_FAILED_{int(anchor_hour*60)}",f1.atr)
       used.add("OPEN_FAILED")
 return events
def forex(bars,h1,h4):
 byday=defaultdict(list)
 for i,b in enumerate(bars):
  dt=datetime.fromtimestamp(b.time,tz=timezone.utc)
  byday[dt.date().isoformat()].append(i)
 events=[]
 for day,rows in byday.items():
  midnight=int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
  asian=[i for i in rows if midnight<=bars[i].time<midnight+6*3600]
  if len(asian)!=72 or not contiguous(bars,asian):continue
  hi=max(bars[i].h for i in asian)
  lo=min(bars[i].l for i in asian)
  used=set()
  for i in rows:
   if not(midnight+6*3600<=bars[i].time<midnight+11*3600):continue
   if i<1 or i+1>=len(bars) or bars[i].time-bars[i-1].time!=300:continue
   b=bars[i]; t=b.time+300
   f1=getframe(h1,t);f4=getframe(h4,t)
   if f1 is None or f4 is None or f1.atr<=0:continue
   body=abs(b.c-b.o)
   upwick=b.h-max(b.o,b.c);lowwick=min(b.o,b.c)-b.l
   if "ASIA_SWEEP" not in used and t<midnight+10*3600 and f1.adx<=24:
    if b.h>hi+.03*f1.atr and b.c<hi and upwick>=body:
     add_event(events,bars,i+1,-1,"ASIA_SWEEP",f1.atr)
     used.add("ASIA_SWEEP")
    elif b.l<lo-.03*f1.atr and b.c>lo and lowwick>=body:
     add_event(events,bars,i+1,1,"ASIA_SWEEP",f1.atr)
     used.add("ASIA_SWEEP")
   if "LONDON_CONTINUATION" not in used and t<midnight+11*3600:
    direction=f1.direction if f1.direction==f4.direction and f1.direction else 0
    if f1.adx>=20 and direction:
     # Confirm candle closed outside Asian range and current M5 body aligns.
     if direction>0 and b.c>hi+.05*f1.atr and b.c>b.o:
      add_event(events,bars,i+1,1,"LONDON_CONTINUATION",f1.atr)
      used.add("LONDON_CONTINUATION")
     elif direction<0 and b.c<lo-.05*f1.atr and b.c<b.o:
      add_event(events,bars,i+1,-1,"LONDON_CONTINUATION",f1.atr)
      used.add("LONDON_CONTINUATION")
 return events

def screen(sym):
 si=mt5.symbol_info(sym)
 bars,source=load_bars(sym)
 f1=frame_last(build_frames(aggregate(bars,3600),3600))
 f4=frame_last(build_frames(aggregate(bars,14400),14400))
 events=indices(bars,f1,f4) if sym in INDEX else forex(bars,f1,f4)
 outcomes=defaultdict(list)
 for j,side,method,atr in events:
  yr=str(datetime.fromtimestamp(bars[j].time,tz=timezone.utc).year)
  if yr not in ("2025","2026"):continue
  found=replay(bars,j,side,atr,STOP_MULT,RR,HOLD_BARS,float(si.point),
      float(si.trade_tick_size or si.point))
  if found is None:continue
  val,end=found
  outcomes[(method,yr)].append({"R":val,"time":bars[j].time,
      "entry_time":bars[j].time,"exit_time":bars[end].time,
      "side":side})
 # One side / one at-a-time per playbook; no overlap within same symbol/method.
 results=[]
 for method in sorted(set(x[0] for x in outcomes)):
  byyear={}
  for yr in ("2025","2026"):
   vals=sorted(outcomes[(method,yr)],key=lambda x:x["time"])
   clean=[];last_end=0
   for entry in vals:
    if entry["entry_time"]<=last_end:continue
    clean.append(entry);last_end=entry["exit_time"]
   byyear[yr]=clean
  a=metrics(byyear["2025"]);b=metrics(byyear["2026"])
  dev=a["n"]>=40 and a["months"]>=7 and a["active_weeks"]>=20 and a["mean_R"]>.10 and a["PF"]>1.2 and a["top5_excluded_sum_R"]>0
  diag=b["n"]>=30 and b["mean_R"]>.05 and b["PF"]>1.1 and b["top5_excluded_sum_R"]>0
  results.append({"method":method,"2025":a,"2026":b,
      "development_gate_pass":dev,"2026_reused_diagnostic_positive":diag,
      "yearly_trades":byyear})
 return {"symbol":sym,"source":source,"bar_count":len(bars),
  "event_count":len(events),"playbooks":results}
def main():
 report={"kind":"KATARINA_FROZEN_ASSET_CLASS_INTRADAY_HYPOTHESES",
   "training_period":"2025","reused_not_clean_diagnostic":"2026_through_Oct_09",
   "index_models":"13:30/14:30 UTC 30min US open range retest or failed extension",
   "forex_models":"00-06 UTC Asia sweep fade or 06-11 UTC continuation",
   "RR":RR,"stop_h1_atr":STOP_MULT,"hold_m5_bars":HOLD_BARS,
   "price_path":"M5 OHLC stop-first, observed bar spread, 1 adverse tick each side, assumed fee 0.03R",
   "timezone_warning":"US open anchors deliberately fixed UTC; daylight saving not yet normalized",
   "references_are_hypotheses_not_proof":True,"live_trading":False,
   "symbol_results":[]}
 if not mt5.initialize(path=MT5PATH,timeout=15000):
  raise RuntimeError(mt5.last_error())
 try:
  for sym in INDEX+FX:
   try:
    info=screen(sym)
   except Exception as ex:
    import traceback
    info={"symbol":sym,"error":str(ex),"trace":traceback.format_exc()[-1800:]}
   report["symbol_results"].append(info)
   print("MARKET",sym,"events",info.get("event_count"),
     "playbooks",[(p["method"],p["2025"]["n"],p["2025"]["mean_R"],
     p["2026"]["n"],p["2026"]["mean_R"],p["development_gate_pass"],
     p["2026_reused_diagnostic_positive"]) for p in info.get("playbooks",[])],flush=True)
   out=AUDIT/"katarina_distinct_index_fx_intraday_2025_2026.json"
   out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
 finally:mt5.shutdown()
 print("FILE",str(AUDIT/"katarina_distinct_index_fx_intraday_2025_2026.json"),flush=True)
if __name__=="__main__":main()
