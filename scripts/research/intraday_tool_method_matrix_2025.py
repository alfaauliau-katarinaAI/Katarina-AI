"""Predeclared KATARINA intraday method matrix, causal 2025-2026 research.

Market hypothesis components (not optimizable after outcome):
- H1/H4 structure and regime, ORB/failed breakout/pullback
- M5 tick quote-volume proxy, NOT centralized traded volume or footprint
- Fibonacci location in 8h prior closed-channel
- ADX/trend quality, candle body conviction
- 2 stop ATR scales, RR2/RR3, 3h/6h hold.
Select by 2025 only; 2026 is REUSED diagnostics (not virgin OOS).
M5 OHLC stop-first execution approximation. No broker orders.
"""
from __future__ import annotations
import sys,json,statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_brain_v2_from_2025 import load_bars,aggregate,build_frames,frame_last,getframe,MT5PATH,AUDIT
from intraday_session_2025 import candidates
import MetaTrader5 as mt5

SYMS=("XAUUSD.vx","NAS100.vx","US30.vx","JPN225.vx","EURUSD.vx","GBPUSD.vx","USDJPY.vx")
MODES=("OR_TREND_BREAK","OR_FAILED_BREAK","H1_H4_PULLBACK")
FILTERS=("RAW","ADX20","ADX25","TICK_VOLUME_1P2","TICK_VOLUME_1P5",
         "FIBO_618","BODY_STRONG","ADX20_FIBO","VOL_BODY","DAILY_CONFIRM")
STOPS=(.55,.8)  # H1 ATR; fixed in advance
RRS=(2.,3.)
HOLDS=(36,72)    # M5 -> 3/6h

def features(bars,signal_index,side,h1,h4,daily):
  idx=signal_index
  b=bars[idx]
  if idx<100 or not all(x>0 for x in (h1.atr,h4.atr)):return None
  if bars[idx].time-bars[idx-1].time!=300:return None
  past=bars[idx-96:idx]
  if len(past)<96:return None
  # all calculations from current/previous CLOSED bars, never entry candle
  hi=max(x.h for x in past);lo=min(x.l for x in past)
  pos=(b.c-lo)/(hi-lo) if hi>lo else .5
  vol_hist=[x.volume for x in bars[idx-24:idx] if x.volume>0]
  if not vol_hist:return None
  vol_base=statistics.median(vol_hist)
  tickratio=b.volume/vol_base if vol_base>0 else 0
  spreadratio=b.spread if b.spread>0 else 0
  candle_range=b.h-b.l
  bodyratio=abs(b.c-b.o)/candle_range if candle_range>0 else 0
  direction=1 if b.c>b.o else -1 if b.c<b.o else 0
  atr_rel_or=None
  return {"adx":h1.adx,"h4_eff":h4.efficiency,
     "volume_relative":tickratio,"fibo_pos":pos,"body":bodyratio,
     "signal_dir":direction,"side":side,
     "D1_bias":0 if daily is None else daily.direction,
     "spread_points":spreadratio}

def meets(f,x):
  side=x["side"];pos=x["fibo_pos"]
  fib=(pos>=.618 if side>0 else pos<=.382)
  if f=="RAW":return True
  if f=="ADX20":return x["adx"]>=20
  if f=="ADX25":return x["adx"]>=25
  if f=="TICK_VOLUME_1P2":return x["volume_relative"]>=1.2
  if f=="TICK_VOLUME_1P5":return x["volume_relative"]>=1.5
  if f=="FIBO_618":return fib
  if f=="BODY_STRONG":return x["body"]>=.55 and x["signal_dir"]==side
  if f=="ADX20_FIBO":return x["adx"]>=20 and fib
  if f=="VOL_BODY":return x["volume_relative"]>=1.2 and x["body"]>=.55 and x["signal_dir"]==side
  if f=="DAILY_CONFIRM":return x["D1_bias"]==side
  raise ValueError(f)
def replay(bars,entry_idx,side,atr,stop_mult,rr,hold,point,tick):
  if entry_idx<1 or entry_idx>=len(bars):return None
  b=bars[entry_idx]
  if b.spread<=0 or b.time-bars[entry_idx-1].time>600:return None
  distance=atr*stop_mult
  spread=b.spread*point
  if distance<2.5*spread or distance<4*tick:return None
  entry=b.o+(spread+tick if side>0 else -tick)
  sl=entry-side*distance;tp=entry+side*distance*rr
  value=None
  for j in range(entry_idx,min(entry_idx+hold,len(bars))):
    z=bars[j]
    if j>entry_idx and z.time-bars[j-1].time>600:break
    exit_spread=z.spread*point
    stop_hit=(z.l<=sl if side>0 else z.h+exit_spread>=sl)
    target_hit=(z.h>=tp if side>0 else z.l+exit_spread<=tp)
    if stop_hit:return (-1-tick/distance-.03,j)
    if target_hit:return (rr-tick/distance-.03,j)
    closing=z.c if side>0 else z.c+exit_spread
    value=side*(closing-side*tick-entry)/distance-.03
  return (value,j) if value is not None else None
def metrics(vals):
  if not vals:return {"n":0,"mean_R":None,"PF":None,"win_rate":None,"months":0,"active_weeks":0,"positive_weeks":0,"dd_R":None}
  pnl=[v["R"] for v in vals]
  pos=sum(v for v in pnl if v>0);neg=-sum(v for v in pnl if v<0)
  weeks=defaultdict(float); months=defaultdict(float);peak=cur=dd=0.
  for row in vals:
    dt=datetime.fromtimestamp(row["time"],tz=timezone.utc)
    weeks[(dt.isocalendar().year,dt.isocalendar().week)]+=row["R"]
    months[dt.strftime("%Y-%m")]+=row["R"]
    cur+=row["R"];peak=max(peak,cur);dd=max(dd,peak-cur)
  return {"n":len(vals),"mean_R":round(sum(pnl)/len(pnl),5),
   "PF":round(pos/neg,4) if neg else None,
   "win_rate":round(sum(v>0 for v in pnl)/len(pnl),4),
   "months":len(months),"active_weeks":len(weeks),
   "positive_weeks":sum(v>0 for v in weeks.values()),
   "dd_R":round(dd,3),
   "top5_excluded_sum_R":round(sum(pnl)-sum(sorted(pnl,reverse=True)[:5]),3),
   "total_R":round(sum(pnl),3)}
def screen_symbol(sym):
  info=mt5.symbol_info(sym)
  bars,source=load_bars(sym)
  f1=frame_last(build_frames(aggregate(bars,3600),3600))
  f4=frame_last(build_frames(aggregate(bars,14400),14400))
  fd=frame_last(build_frames(aggregate(bars,86400),86400))
  events=candidates(bars,f1,f4)
  pre=[]
  for j,side,mode,hour,atr in events:
    if j>=len(bars) or j<102:continue
    i=j-1;t=bars[i].time+300
    h1=getframe(f1,t);h4=getframe(f4,t);d1=getframe(fd,t)
    if h1 is None or h4 is None:continue
    x=features(bars,i,side,h1,h4,d1)
    if x is None:continue
    pre.append((j,side,mode,hour,atr,x))
  point=float(info.point);tick=float(info.trade_tick_size or info.point)
  combos=[]
  for mode in MODES:
   for hour in (6,12):
    subset=[e for e in pre if e[2]==mode and e[3]==hour]
    for fname in FILTERS:
     filtered=[e for e in subset if meets(fname,e[5])]
     if not filtered:continue
     for sl in STOPS:
      for rr in RRS:
       for hold in HOLDS:
        observations={"2025":[],"2026":[]}
        last={"2025":-1,"2026":-1}
        for entry,side,_,_,atr,x in filtered:
          year=str(datetime.fromtimestamp(bars[entry].time,tz=timezone.utc).year)
          if year not in last or entry<=last[year]:continue
          sim=replay(bars,entry,side,atr,sl,rr,hold,point,tick)
          if sim is None:continue
          value,end=sim;last[year]=end
          observations[year].append({"time":bars[entry].time,"exit_time":bars[end].time,
              "R":value,"side":side,"mode":mode,"hour":hour,
              "stopATR":sl,"rr":rr,"hold":hold,"filter":fname})
        a=metrics(observations["2025"]);b=metrics(observations["2026"])
        devpass=(a["n"]>=40 and a["months"]>=7 and a["active_weeks"]>=25
                and a["mean_R"]>=.12 and a["PF"]>=1.25
                and a["top5_excluded_sum_R"]>0)
        diagpass=(b["n"]>=35 and b["mean_R"]>=.05 and b["PF"]>=1.1 and
                  b["top5_excluded_sum_R"]>0)
        combos.append({"mode":mode,"session_utc":hour,"filter":fname,
              "stop_h1_atr":sl,"rr":rr,"hold_hours":hold/12,
              "2025":a,"2026":b,"passes_2025_gate":bool(devpass),
              "positive_2026_diagnostic":bool(diagpass)})
  qualified=[x for x in combos if x["passes_2025_gate"]]
  qualified_both=[x for x in qualified if x["positive_2026_diagnostic"]]
  # Ranking is 2025 ONLY; never optimize on 2026 diagnostics
  ranked=sorted(qualified,key=lambda x:(
       x["2025"]["mean_R"], x["2025"]["active_weeks"]),reverse=True)
  result={"symbol":sym,"source":source,"M5_bars":len(bars),
     "first":datetime.fromtimestamp(bars[0].time,tz=timezone.utc).isoformat(),
     "2025_2026_candidates":len(pre),"configurations_evaluated":len(combos),
     "2025_qualified":len(qualified),"2026_diagnostic_positive_among_qualified":len(qualified_both),
     "best_ranked_2025_only":ranked[:5],
     "qualified_2026_diagnostic":qualified_both[:30],
     "all":combos}
  print("SYMBOL",sym,"signals",len(pre),"configs",len(combos),"pass2025",len(qualified),
        "positive2026diag",len(qualified_both),flush=True)
  return result
def main():
 r={"kind":"KATARINA_INTRADAY_TOOL_METHOD_MATRIX_V1_2025_2026",
   "features":["H1/H4","closed M5 quote tick volume","8h Fibonacci position",
      "H1 ADX","candle conviction","D1 trend"],
   "params":{"modes":MODES,"filters":FILTERS,"stops_h1_atr":STOPS,
             "rr":RRS,"hold_m5_bars":HOLDS,"sessions_utc":[6,12]},
   "2025_development":True,"2026_reused_diagnostic_NOT_clean_holdout":True,
   "slippage_ticks":1,"commission_R_assumed":.03,
   "execution_proxy":"broker M5 OHLC, stop-first for ambiguous bar",
   "no_live_trades":True,"risk_governor_unchanged":True,"symbols":[]}
 if not mt5.initialize(path=MT5PATH,timeout=15000):raise RuntimeError(mt5.last_error())
 try:
  for sym in SYMS:
    try:x=screen_symbol(sym)
    except Exception as e:
     import traceback
     x={"symbol":sym,"error":str(e),"trace":traceback.format_exc()}
    r["symbols"].append(x)
    out=AUDIT/"katarina_intraday_tool_matrix_2025_2026.json"
    out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
 finally:mt5.shutdown()
 print("COMPLETE",str(AUDIT/"katarina_intraday_tool_matrix_2025_2026.json"),flush=True)
if __name__=="__main__":main()
