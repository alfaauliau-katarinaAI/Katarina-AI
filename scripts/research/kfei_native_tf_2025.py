"""KATARINA KFEI research: MT5 native TF support and 2025/2026 RR test.

Causal closed-candle decisions, next-bar fills, intrabar stop-first, broker bar
spread + 1tick each side + assumed 0.03R commission. No live trading.
KFEI is descriptive directional efficiency/energy, NOT a win probability.
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime,timezone,timedelta
import MetaTrader5 as mt5
DIR=Path(r"C:\KatarinaDev\artifacts\historical-brain")
BEGIN=datetime(2025,1,1,tzinfo=timezone.utc)
END=datetime(2026,10,10,tzinfo=timezone.utc)
SYMBOLS=["XAUUSD.vx","NAS100.vx","US30.vx","JPN225.vx","EURUSD.vx","GBPUSD.vx","USDJPY.vx"]
FRAME_MINUTES={"M1":1,"M2":2,"M3":3,"M4":4,"M5":5,"M6":6,"M10":10,"M12":12,
 "M15":15,"M20":20,"M30":30,"H1":60,"H2":120,"H3":180,"H4":240,
 "H6":360,"H8":480,"H12":720,"D1":1440,"W1":10080,"MN1":43200}
# Higher TFs can provide structural context but are NOT scalper entry frames
ENTRY_TF=["M5","M6","M10","M12","M15","M20","M30","H1","H2"]
RRS=(1.,1.5,2.,3.,5.,7.,10.)
STOPS=(.8,1.2,1.6)
HOLD_MINUTES=180  # Default intraday horizon; alternate short-scalp audits may set 60.
MODES=("DRIVE_CONTINUATION","SWEEP_REVERSAL","RANGE_REJECTION","CLOSED_BREAK")
def iso(t):return datetime.fromtimestamp(int(t),tz=timezone.utc).isoformat()
def native_history(sym,tf):
   tf_enum=getattr(mt5,"TIMEFRAME_"+tf)
   dedup={}
   for year in (2025,2026):
    for month in range(1,13):
     a=datetime(year,month,1,tzinfo=timezone.utc)
     if a>=END:break
     e=(datetime(year+1,1,1,tzinfo=timezone.utc) if month==12 else
        datetime(year,month+1,1,tzinfo=timezone.utc))
     e=min(e,END)
     arr=mt5.copy_rates_range(sym,tf_enum,a,e-timedelta(seconds=1))
     if arr is None:continue
     for z in arr:
      sec=int(z["time"])
      if a.timestamp()<=sec<e.timestamp():
       dedup[sec]=(sec,float(z["open"]),float(z["high"]),float(z["low"]),
           float(z["close"]),int(z["spread"]),int(z["tick_volume"]))
   return sorted(dedup.values())
def xau_recon(bars):
  import csv
  p=DIR/"xauusd_vx_m5_reconstructed_2025_jan_apr.csv"
  if p.exists():
   with p.open(encoding="utf-8",newline="") as f:
    old=[(int(z["time"]),float(z["open"]),float(z["high"]),float(z["low"]),
         float(z["close"]),int(z["spread"]),int(z["tick_volume"])) for z in csv.DictReader(f)]
   cut=int(datetime(2025,5,1,tzinfo=timezone.utc).timestamp())
   return sorted({x[0]:x for x in old if x[0]<cut}.values())+[b for b in bars if b[0]>=cut]
  return bars
def labels_and_signal(bars,tfminutes):
   """Output point-in-time setup candidates with named KFEI score."""
   out=[]
   if len(bars)<100:return out
   tr=[];atr=[];closes=[]
   s=None
   for i,b in enumerate(bars):
     closes.append(b[4])
     if i==0:tr.append(b[2]-b[3]);atr.append(b[2]-b[3]);continue
     pc=bars[i-1][4]
     trval=max(b[2]-b[3],abs(b[2]-pc),abs(b[3]-pc))
     tr.append(trval)
     prev=atr[-1] if i>1 else trval
     newatr=(prev*13+trval)/14
     atr.append(newatr)
     if i<64:continue
     # Gap veto: no fabricated bars between closed signal lookback.
     sec=tfminutes*60
     if b[0]-bars[i-1][0]!=sec:continue
     a=bars[i-20:i]
     if any(a[j][0]-a[j-1][0]!=sec for j in range(1,len(a))):continue
     ap=atr[i]
     if ap<=0 or b[5]<=0:continue
     path=sum(abs(closes[q]-closes[q-1]) for q in range(i-11,i+1))
     displacement=b[4]-closes[i-12]
     er=abs(displacement)/path if path>1e-12 else 0.
     atr_base=sorted(atr[i-50:i])
     typical=atr_base[len(atr_base)//2] if atr_base else ap
     expansion=ap/typical if typical>0 else 1.
     drive=(1 if displacement>0 else -1 if displacement<0 else 0)*er*min(3.,abs(displacement)/ap)*min(2.,expansion)
     hi=max(x[2] for x in a);lo=min(x[3] for x in a);width=hi-lo
     if width<=0:continue
     body=abs(b[4]-b[1]);low_wick=min(b[1],b[4])-b[3];top_wick=b[2]-max(b[1],b[4])
     cdir=1 if b[4]>b[1] else -1 if b[4]<b[1] else 0
     side=0;mode=None
     if b[3]<lo and b[4]>lo and low_wick>=max(.20*ap,1.2*body):
       side=1;mode="SWEEP_REVERSAL"
     elif b[2]>hi and b[4]<hi and top_wick>=max(.20*ap,1.2*body):
       side=-1;mode="SWEEP_REVERSAL"
     elif b[4]>hi+.04*ap and cdir==1 and er>.24:
       side=1;mode="CLOSED_BREAK"
     elif b[4]<lo-.04*ap and cdir==-1 and er>.24:
       side=-1;mode="CLOSED_BREAK"
     elif abs(drive)>.60 and cdir==(1 if drive>0 else -1):
       side=cdir;mode="DRIVE_CONTINUATION"
     elif er<.22 and (b[4]-lo)/width<.25 and cdir==1:
       side=1;mode="RANGE_REJECTION"
     elif er<.22 and (b[4]-lo)/width>.75 and cdir==-1:
       side=-1;mode="RANGE_REJECTION"
     if mode is None:continue
     # Descriptive score for future diagnostics, NOT entry authorization.
     out.append((i+1,side,ap,mode,drive))
   return out
def simulate(bars,signal,rr,stopmult,hold,point,tick):
  i,side,atr,mode,drive=signal
  if i>=len(bars):return None
  b=bars[i]
  if b[5]<=0 or i==0:return None
  if b[0]-bars[i-1][0]>2*(bars[i-1][0]-bars[i-2][0]):return None
  spread=b[5]*point
  distance=atr*stopmult
  if distance<max(2*spread,4*tick):return None
  entry=b[1]+(spread+tick if side>0 else -tick)
  sl=entry-side*distance;tp=entry+side*distance*rr
  pnl=None
  for j in range(i,min(i+hold,len(bars))):
   x=bars[j]
   if j>i and x[0]-bars[j-1][0]>2*(b[0]-bars[i-1][0]):break
   xspr=x[5]*point
   stop_hit=(x[3]<=sl if side>0 else x[2]+xspr>=sl)
   profit_hit=(x[2]>=tp if side>0 else x[3]+xspr<=tp)
   if stop_hit:return (-1-tick/distance-.03,j)
   if profit_hit:return (rr-tick/distance-.03,j)
   closing=x[4] if side>0 else x[4]+xspr
   pnl=side*(closing-side*tick-entry)/distance-.03
  return (pnl,j) if pnl is not None else None
def stats(xs):
  n=len(xs)
  if not n:return {"n":0,"mean_R":None,"pf":None}
  a=sum(v for v in xs if v>0); b=-sum(v for v in xs if v<0)
  return {"n":n,"mean_R":round(sum(xs)/n,5),"pf":round(a/b,3) if b>0 else None,
          "win":round(sum(v>0 for v in xs)/n,4)}
def scan_one(sym,tf,point,tick):
  frame=FRAME_MINUTES[tf]
  bars=native_history(sym,tf)
  if sym=="XAUUSD.vx" and tf=="M5":bars=xau_recon(bars)
  counts={"2025":sum(datetime.fromtimestamp(x[0],tz=timezone.utc).year==2025 for x in bars),
          "2026":sum(datetime.fromtimestamp(x[0],tz=timezone.utc).year==2026 for x in bars)}
  info={"tf":tf,"native_monthly_count":counts,"first":iso(bars[0][0]) if bars else None,
        "last":iso(bars[-1][0]) if bars else None,"role":"ENTRY" if tf in ENTRY_TF else "CONTEXT",
        "configurations":0,"2025_passing":0}
  if tf not in ENTRY_TF or counts["2025"]<1000 or counts["2026"]<1000:return info
  signals=labels_and_signal(bars,frame)
  bymode=defaultdict(list)
  for x in signals:
    if x[0]>=len(bars):continue
    y=datetime.fromtimestamp(bars[x[0]][0],tz=timezone.utc).year
    if y not in (2025,2026):continue
    bymode[x[3]].append(x)
  info["signals"]={k:len(v) for k,v in bymode.items()}
  candidates=[]
  hold=max(1,int(HOLD_MINUTES/frame))
  for mode,sg in sorted(bymode.items()):
   for mult in STOPS:
    for rr in RRS:
     outcomes={"2025":[],"2026":[]};lastend={"2025":-1,"2026":-1};months={"2025":set(),"2026":set()}
     for x in sg:
      idx=x[0]
      y=str(datetime.fromtimestamp(bars[idx][0],tz=timezone.utc).year)
      if idx<=lastend[y]:continue
      executed=simulate(bars,x,rr,mult,hold,point,tick)
      if executed is None:continue
      val,exitidx=executed
      outcomes[y].append(val);lastend[y]=exitidx
      months[y].add(datetime.fromtimestamp(bars[idx][0],tz=timezone.utc).strftime("%Y-%m"))
     s25=stats(outcomes["2025"]);s26=stats(outcomes["2026"])
     passing=(s25["n"]>=70 and len(months["2025"])>=5 and s25["mean_R"]>=.08 and s25["pf"]>=1.15)
     candidates.append({"mode":mode,"sl_atr":mult,"rr":rr,"holding_minutes":hold*frame,
         "train_2025":s25,"diagnostic_2026":s26,"train_months":len(months["2025"]),
         "passed_dev":passing})
  info["configurations"]=len(candidates)
  winners=[r for r in candidates if r["passed_dev"]]
  info["2025_passing"]=len(winners)
  info["2026_positive_among_passed"]=sum(r["diagnostic_2026"]["mean_R"] is not None and r["diagnostic_2026"]["mean_R"]>0 for r in winners)
  info["top_train"]=sorted(candidates,key=lambda r:(r["train_2025"]["mean_R"] if r["train_2025"]["mean_R"] is not None else -999),reverse=True)[:3]
  info["best_passing"]=max(winners,key=lambda r:r["train_2025"]["mean_R"]) if winners else None
  info["positive_both_sample_sufficient"]=[r for r in winners if r["diagnostic_2026"]["n"]>=70 and r["diagnostic_2026"]["mean_R"]>0 and r["diagnostic_2026"]["pf"]>1.0]
  print("TF",sym,tf,"rows",counts,"signals",len(signals),"devpass",len(winners),
    "positive_both",len(info["positive_both_sample_sufficient"]),flush=True)
  return info
def main():
  report={"kind":"KATARINA_KFEI_NATIVE_TF_RR_SCREEN_2025_2026",
    "dates":["2025-01-01","2026-10-10 (exclusive)"],"timeframes":FRAME_MINUTES,
    "tested_sides":"both BUY SELL per strategy as signaled",
    "indicator":"KFEI = sign(close-close_12) * ER12 * clip(abs(displacement)/ATR14,0,3) * clip(ATR14/median(ATR14_last50),0,2)",
    "policy":{"only_chart_entries":ENTRY_TF,"higher_timeframes_are_context":True,
      "RRs":RRS,"stop_ATR_mult":STOPS,"holding_max_minutes":180,
      "broker_bar_spread":True,"assumed_slippage_ticks_per_side":1,
      "assumed_fee_R":.03,"M5_ambiguity_stop_first":True,
      "data_inspected_and_reused_2026":True,"multiple_comparisons_not_corrected":True,
      "MT5_strategy_tester_real_ticks":False,
      "no_portfolio_cash_sim":True,"live_orders":False,
      "risk_governor_modified":False,"promotion_allowed":False},
    "symbols":[]}
  if not mt5.initialize(path=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe",timeout=15000):raise RuntimeError(mt5.last_error())
  try:
   for sym in SYMBOLS:
    si=mt5.symbol_info(sym)
    if si is None:continue
    rec={"symbol":sym,"results":[]}
    for tf in FRAME_MINUTES:
     try:rec["results"].append(scan_one(sym,tf,float(si.point),
                               float(si.trade_tick_size or si.point)))
     except Exception as e:
      rec["results"].append({"tf":tf,"error":str(e)})
    report["symbols"].append(rec)
    print("SYMBOL_DONE",sym,flush=True)
    dest=DIR/"katarina_kfei_tf_rr_2025_2026.json"
    dest.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
  finally:mt5.shutdown()
  print("REPORT",str(DIR/"katarina_kfei_tf_rr_2025_2026.json"),flush=True)
if __name__=="__main__":main()
