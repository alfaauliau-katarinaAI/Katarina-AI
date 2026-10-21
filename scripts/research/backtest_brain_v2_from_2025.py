"""KATARINA V2 historical test 2025-01 to 2026-10.
Causal M5/M15/H1, 2025 research and 2026 chronological validation.
M5 high/low cannot resolve exact intrabar stop/target -> stop-first.
No trading; no alteration of the existing Risk Governor or live settings.
"""
from __future__ import annotations
import csv,json,sys
from bisect import bisect_right
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from dataclasses import dataclass

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.intelligence.adaptive_regime import AdaptiveRegimeEngine, ClosedFrame
from katarina.intelligence.closed_swing_structure import ClosedSwingStructure, ClosedBar
from katarina.engines.adaptive_scalper import AdaptiveScalpRouter,ClosedPriceContext,ScalpSide
import MetaTrader5 as mt5

AUDIT=Path(r"C:\KatarinaDev\artifacts\historical-brain")
BEGIN=datetime(2025,1,1,tzinfo=timezone.utc)
END=datetime(2026,10,10,tzinfo=timezone.utc)
SYMBOLS=["XAUUSD.vx","NAS100.vx","US30.vx","JPN225.vx","EURUSD.vx","GBPUSD.vx","USDJPY.vx"]
MT5PATH=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe"

@dataclass(frozen=True)
class Bar:
  time:int; o:float; h:float; l:float; c:float; spread:int; volume:int
def load_bars(symbol):
  # MT5 chart max-bars cap: the full span returns None/empty on this VPS.
  # Request per calendar month instead; never assume an empty full-range
  # response means a symbol lacks history.
  bars=[]
  for year in (2025,2026):
    for month in range(1,13):
      start=datetime(year,month,1,tzinfo=timezone.utc)
      if start>=END:break
      stop=datetime(year+1,1,1,tzinfo=timezone.utc) if month==12 else datetime(year,month+1,1,tzinfo=timezone.utc)
      stop=min(stop,END)
      r=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M5,start,stop-timedelta(seconds=1))
      if r is None:continue
      bars.extend(Bar(int(v["time"]),float(v["open"]),float(v["high"]),float(v["low"]),float(v["close"]),
              int(v["spread"]),int(v["tick_volume"])) for v in r)
  src="MT5_M5"
  if symbol=="XAUUSD.vx":
    f=AUDIT/"xauusd_vx_m5_reconstructed_2025_jan_apr.csv"
    if f.exists():
      with f.open(encoding="utf-8",newline="") as h:
       reader=csv.DictReader(h)
       old=[Bar(int(x["time"]),float(x["open"]),float(x["high"]),float(x["low"]),
            float(x["close"]),int(x["spread"]),int(x["tick_volume"])) for x in reader]
      bars=old+[b for b in bars if b.time>=int(datetime(2025,5,1,tzinfo=timezone.utc).timestamp())]
      src="TICK_TO_M5_2025_JAN_APR_AND_MT5_M5_REST"
  # eliminate ghost monthly singleton bars in missing historical periods
  bars.sort(key=lambda b:b.time)
  dedup={x.time:x for x in bars if x.c>0 and x.h>=x.l and x.o>0}
  bars=sorted(dedup.values(),key=lambda x:x.time)
  return bars,src
def aggregate(bars,seconds):
  agg={}
  for b in bars:
    key=b.time//seconds*seconds
    if key not in agg: agg[key]=[b.time,b.o,b.h,b.l,b.c,b.spread,b.volume,1]
    else:
      z=agg[key]
      z[2]=max(z[2],b.h);z[3]=min(z[3],b.l);z[4]=b.c;z[5]=b.spread;z[6]+=b.volume;z[7]+=1
  expected=seconds//300
  complete=[]
  for start,v in sorted(agg.items()):
    if v[7]==expected and v[0]==start:
      complete.append(Bar(start,v[1],v[2],v[3],v[4],v[5],v[6]))
  return complete
def build_frames(bars, seconds):
  """Compute causal features from completed OHLC bars, Wilder 14 ADX smoothing."""
  frames={}
  if not bars:return frames
  n=14; pre_tr=pre_pd=pre_md=0.
  dxs=[]; atr=sm_p=sm_m=adx=None
  close_hist=[]
  for i,b in enumerate(bars):
    if i>0:
      prev=bars[i-1]
      tr=max(b.h-b.l,abs(b.h-prev.c),abs(b.l-prev.c))
      up=b.h-prev.h;down=prev.l-b.l
      pd=up if up>down and up>0 else 0.
      md=down if down>up and down>0 else 0.
      if i<=n:
        pre_tr+=tr;pre_pd+=pd;pre_md+=md
        if i==n: atr=pre_tr/n;sm_p=pre_pd/n;sm_m=pre_md/n
      else:
        atr=(atr*(n-1)+tr)/n
        sm_p=(sm_p*(n-1)+pd)/n
        sm_m=(sm_m*(n-1)+md)/n
      if atr is not None and atr>0:
        pdi=100*sm_p/atr;mdi=100*sm_m/atr
        dx=100*abs(pdi-mdi)/(pdi+mdi) if pdi+mdi>0 else 0.
        dxs.append(dx)
        if len(dxs)==n: adx=sum(dxs)/n
        elif len(dxs)>n: adx=(adx*(n-1)+dx)/n
    close_hist.append(b.c)
    if adx is None or atr is None or atr<=0 or i<34:continue
    # Past 12 CLOSED observations for direction and efficiency.
    recent=close_hist[-13:]
    diffs=[recent[j]-recent[j-1] for j in range(1,len(recent))]
    path=sum(abs(x) for x in diffs)
    eff=abs(recent[-1]-recent[0])/path if path>0 else 0.
    direction=1 if recent[-1]-recent[-4]>.12*atr else (
             -1 if recent[-1]-recent[-4]<-.12*atr else 0)
    close_time=b.time+seconds
    frames[close_time]=ClosedFrame(direction,float(adx),float(eff),float(atr),
                                  datetime.fromtimestamp(close_time,tz=timezone.utc))
  return frames
def frame_last(frames):
   times=sorted(frames)
   values=[frames[x] for x in times]
   return times,values
def getframe(idx,t):
   times,values=idx
   i=bisect_right(times,t)-1
   return values[i] if i>=0 else None
def evaluate_trade(bars,entry_idx,side,atr,point,tick,mode,commission_r=.03):
  """Entry next M5 open, spread from next bar, adverse 1 tick both directions.
  Stop-first on ambiguous same-bar; max hold in bars; commission scenario, not measured.
  """
  target_rr={ "TREND_PULLBACK":1.5,"RANGE_FADE":1.0,"BREAKOUT_RETEST":1.5,"REVERSAL_RECLAIM":1.3}
  stop_mult={ "TREND_PULLBACK":1.2,"RANGE_FADE":.9,"BREAKOUT_RETEST":1.1,"REVERSAL_RECLAIM":1.1}
  hold_max={"TREND_PULLBACK":12,"RANGE_FADE":12,"BREAKOUT_RETEST":8,"REVERSAL_RECLAIM":12}
  if mode not in target_rr:return None
  nxt=bars[entry_idx]
  spr=nxt.spread*point
  if nxt.spread<=0:return None
  if nxt.time-bars[entry_idx-1].time>900:return None
  entry=(nxt.o+spr+tick if side==1 else nxt.o-tick)
  risk=atr*stop_mult[mode]
  if risk<=4*tick or risk<=2*spr:return None
  sl=entry-side*risk;tp=entry+side*risk*target_rr[mode]
  exitprice=None;kind="TIME"
  for j in range(entry_idx,min(len(bars),entry_idx+hold_max[mode])):
    b=bars[j]
    if j>entry_idx and b.time-bars[j-1].time>900:break
    exit_spr=max(b.spread,0)*point
    if side==1:
      sl_hit=b.l<=sl;tp_hit=b.h>=tp
    else:
      sl_hit=b.h+exit_spr>=sl;tp_hit=b.l+exit_spr<=tp
    if sl_hit or tp_hit:
      exitprice=sl-tick*side if sl_hit else tp-tick*side
      kind="SL" if sl_hit else "TP"
      break
    close_px=b.c if side==1 else b.c+exit_spr
    exitprice=close_px-tick*side
  if exitprice is None:return None
  gross=(exitprice-entry)*side/risk
  net=gross-commission_r
  return {"R":net,"gross_R":gross,"exit":kind,
          "exit_idx":j,"spread_entry_to_ATR":spr/atr,
          "period":"2025" if nxt.time<1767225600 else "2026"}
def report_stats(trades):
   if not trades:return {"n":0,"mean_R":None,"PF":None,"max_DD_R":None,"win_rate":None}
   profits=[x["R"] for x in trades]
   pos=sum(x for x in profits if x>0);neg=-sum(x for x in profits if x<0)
   eq=top=dd=0.
   for r in profits:
     eq+=r;top=max(top,eq);dd=max(dd,top-eq)
   return {"n":len(trades),"mean_R":round(sum(profits)/len(profits),5),
       "profit_factor":round(pos/neg,4) if neg>0 else None,
       "max_DD_R":round(dd,3),"win_rate":round(sum(r>0 for r in profits)/len(profits),4),
       "sum_R":round(sum(profits),4),
       "cost_model":"historical_M5_spread + 1_tick_slip_each_way + ASSUMED 0.03R commission"}

def run_symbol(symbol):
  si=mt5.symbol_info(symbol)
  if si is None: return {"symbol":symbol,"error":"symbol_missing"}
  bars,source=load_bars(symbol)
  print("READ",symbol,len(bars),source,flush=True)
  if len(bars)<120: return {"symbol":symbol,"bars":len(bars),"error":"too_few_bars"}
  tf5=build_frames(bars,300)
  tf15=build_frames(aggregate(bars,900),900)
  tf60=build_frames(aggregate(bars,3600),3600)
  idx5=frame_last(tf5);idx15=frame_last(tf15);idx60=frame_last(tf60)
  engine=AdaptiveRegimeEngine();swing=ClosedSwingStructure();scalper=AdaptiveScalpRouter()
  state_counts=defaultdict(Counter)
  candidate_counts=defaultdict(Counter)
  trades=[]
  next_free=50
  point=float(si.point);tick=float(si.trade_tick_size or si.point)
  for i in range(50,len(bars)-13):
    b=bars[i];t=b.time+300
    if i%3!=2: continue    # one 15-min sampling point: reducing correlated duplicate signals
    period="2025" if t<1767225600 else "2026"
    f5=getframe(idx5,t);f15=getframe(idx15,t);f60=getframe(idx60,t)
    if None in (f5,f15,f60):continue
    now=datetime.fromtimestamp(t,tz=timezone.utc)
    f={"M5":f5,"M15":f15,"H1":f60}
    sub=bars[i-44:i+1]
    if any(sub[z].time-sub[z-1].time>600 for z in range(1,len(sub))):
      # no gap-bridging swing, session opens need fresh history
      continue
    history=[ClosedBar(datetime.fromtimestamp(x.time+300,tz=timezone.utc),
         x.o,x.h,x.l,x.c) for x in sub]
    try: structure=swing.extract(history,as_of_utc=now,spread=b.spread*point)
    except ValueError:continue
    read=engine.assess(frames=f,as_of_utc=now,structure=structure)
    state_counts[period][read.state.value]+=1
    if i<next_free:continue
    if b.spread<=0:continue
    candle=ClosedPriceContext(b.o,b.h,b.l,b.c,bars[i-1].c,
            max(x.h for x in bars[i-20:i]),min(x.l for x in bars[i-20:i]),
            f5.atr,structure.spread_to_atr,True,True,False)
    proposal=scalper.plan(symbol,read,candle)
    if not proposal.ready_for_research:
      candidate_counts[period]["WAIT"]+=1
      continue
    candidate_counts[period][proposal.strategy.value]+=1
    side=1 if proposal.side==ScalpSide.BUY else -1
    trade=evaluate_trade(bars,i+1,side,f5.atr,point,tick,proposal.strategy.value)
    if trade is None:continue
    trade["setup"]=proposal.strategy.value
    trade["state"]=read.state.value
    trade["time"]=b.time
    trade["month"]=datetime.fromtimestamp(b.time,tz=timezone.utc).strftime("%Y-%m")
    trades.append(trade)
    next_free=trade["exit_idx"]+1
  byperiod={}
  for period in ["2025","2026"]:
    selected=[tr for tr in trades if tr["period"]==period]
    byperiod[period]={"stats":report_stats(selected),
                     "states":dict(state_counts[period]),
                     "signals":dict(candidate_counts[period]),
                     "strategy":{key:report_stats([tr for tr in selected if tr["setup"]==key]) for key in
                      ["TREND_PULLBACK","RANGE_FADE","BREAKOUT_RETEST","REVERSAL_RECLAIM"]},
                     "monthly":{k:report_stats([tr for tr in selected if tr["month"]==k])
                       for k in sorted(set(tr["month"] for tr in selected))}}
  return {"symbol":symbol,"bars":len(bars),"source":source,
          "first_bar_utc":datetime.fromtimestamp(bars[0].time,tz=timezone.utc).isoformat(),
          "last_bar_utc":datetime.fromtimestamp(bars[-1].time,tz=timezone.utc).isoformat(),
          "timeframes":{"M5":len(tf5),"M15":len(tf15),"H1":len(tf60)},
          "periods":byperiod,"trades":[{k:v for k,v in tr.items() if k!="exit_idx"} for tr in trades]}

def main():
  if not mt5.initialize(path=MT5PATH,timeout=15000):
     raise RuntimeError("MT5 initialization failed: "+str(mt5.last_error()))
  report={"kind":"KATARINA_adaptive_brain_v2_retrospective_bar_execution_estimate",
        "symbol_results":[],"window":"2025-01-01 to 2026-10-09 UTC",
        "validation_window":"2026 compared against fixed research rules; not previously untouched external holdout",
        "warnings":["2025 early missing rates for many symbols; XAU Jan-Apr reconstructed from cached broker Bid/Ask tick records",
                    "M5 stop-first high-low approximation not full intra-bar actual execution",
                    "Historical bar spreads provided by MT5; commission 0.03R assumed, actual broker commission UNVERIFIED",
                    "Real-market forward fills, rejection, swaps, leverage and liquidity not modeled",
                    "Thresholds not tuned to 2025 or 2026 results; this is a diagnostic no promotion",
                    "MT5 terminal max chart bars limit may truncate older history"],
        "model_promotion_allowed":False,"live_execution_enabled":False}
  try:
    ai=mt5.account_info()
    report["source_broker"]=ai.server if ai else None
    for sym in SYMBOLS:
      try:r=run_symbol(sym)
      except Exception as e:
        import traceback
        r={"symbol":sym,"exception":repr(e),"traceback":traceback.format_exc()[-1200:]}
      report["symbol_results"].append(r)
      if "periods" in r:
        print("FINISHED",sym,{p:r["periods"][p]["stats"] for p in ["2025","2026"]},flush=True)
      else: print("FAILED",sym,r,flush=True)
  finally:
    mt5.shutdown()
  out=AUDIT/"backtest_adaptive_brain_v2_from_2025.json"
  out.write_text(json.dumps(report,indent=2),encoding="utf-8")
  for x in report["symbol_results"]:
    x.pop("trades",None)
  (AUDIT/"backtest_adaptive_brain_v2_from_2025_summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
  print("REPORT",str(out),flush=True)
if __name__=="__main__":main()
