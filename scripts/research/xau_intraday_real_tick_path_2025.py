"""Exact broker Bid/Ask tick path replay for KATARINA XAU OR opening-range breakout.

Research-only read access, NO mt5.order_send and no risk or trading config changes.
Stops use observed price, conservative gap handling; TP at price not positive gaps.
Fills still simulated and fee hypothetical, NOT authenticated deal statements.
"""
from __future__ import annotations
import sys,json
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_brain_v2_from_2025 import load_bars,aggregate,build_frames,frame_last,MT5PATH,AUDIT
from intraday_session_2025 import candidates,STOP_H1ATR
from audit_xau_intraday_robustness_2025 import metrics
import MetaTrader5 as mt5

def replay_ticks(sym, ticks, start_ms, end_ms, side, atr, ticksize, rr, adverse_ticks, fee_r):
    if ticks is None or not len(ticks):return None,"missing_tick_history"
    ticks=ticks[(ticks["time_msc"]>=start_ms)&(ticks["time_msc"]<end_ms)&
                (ticks["bid"]>0)&(ticks["ask"]>=ticks["bid"])]
    if len(ticks)<3:return None,"insufficient_good_ticks"
    if ticks[0]["time_msc"]-start_ms>120000:return None,"entry_tick_late_2m"
    risk=atr*STOP_H1ATR
    entry_spread=float(ticks[0]["ask"]-ticks[0]["bid"])
    if risk<=2.5*entry_spread or risk<=4*ticksize:return None,"risk_less_than_spread"
    entry=float(ticks[0]["ask"])+adverse_ticks*ticksize if side==1 else float(ticks[0]["bid"])-adverse_ticks*ticksize
    sl=entry-side*risk;tp=entry+side*rr*risk
    reason="TIME";exit_px=None;final_tick=ticks[-1]
    for t in ticks:
        bid=float(t["bid"]);ask=float(t["ask"])
        if side==1:
            if bid<=sl:
                exit_px=min(sl,bid)-adverse_ticks*ticksize
                reason="SL";final_tick=t;break
            if bid>=tp:
                exit_px=tp-adverse_ticks*ticksize
                reason="TP";final_tick=t;break
        else:
            if ask>=sl:
                exit_px=max(sl,ask)+adverse_ticks*ticksize
                reason="SL";final_tick=t;break
            if ask<=tp:
                exit_px=tp+adverse_ticks*ticksize
                reason="TP";final_tick=t;break
    if exit_px is None:
        # If the market stops printing ticks too early, simulation cannot value exit at 6h.
        if end_ms-int(ticks[-1]["time_msc"])>120000:return None,"stale_time_exit"
        exit_px=float(ticks[-1]["bid"])-adverse_ticks*ticksize if side==1 else (
                 float(ticks[-1]["ask"])+adverse_ticks*ticksize)
    value=side*(exit_px-entry)/risk-fee_r
    return {"R":float(value),"reason":reason,
       "time_msc":int(final_tick["time_msc"]),"tick_count":int(len(ticks)),
       "entry_spread":entry_spread},None

def main():
  symbol="XAUUSD.vx"
  if not mt5.initialize(path=MT5PATH,timeout=15000):raise RuntimeError(mt5.last_error())
  records=[];invalid=defaultdict(int)
  try:
   si=mt5.symbol_info(symbol);tick=float(si.trade_tick_size or si.point)
   bars,_=load_bars(symbol)
   framesH1=frame_last(build_frames(aggregate(bars,3600),3600))
   framesH4=frame_last(build_frames(aggregate(bars,14400),14400))
   events=[x for x in candidates(bars,framesH1,framesH4) if x[2]=="OR_TREND_BREAK" and x[3]==6]
   print("EVENTS",len(events),flush=True)
   for ix,(j,side,mode,hour,atr) in enumerate(events):
     start=datetime.fromtimestamp(bars[j].time,tz=timezone.utc)
     stop=start+timedelta(hours=6)
     ticks=mt5.copy_ticks_range(symbol,start,stop,mt5.COPY_TICKS_ALL)
     startms=int(start.timestamp()*1000);endms=int(stop.timestamp()*1000)
     if ticks is None:
       invalid["mt5_copy_ticks_none"]+=1
       continue
     for rr in (2.,3.):
       for costmode,ticks_slip,fees in (("1_tick",1,.03),("3_tick",3,.05)):
         res,err=replay_ticks(symbol,ticks,startms,endms,side,atr,tick,rr,ticks_slip,fees)
         if err:
           invalid[err]+=1;continue
         week=f"{start.isocalendar().year}-W{start.isocalendar().week:02d}"
         records.append({"year":str(start.year),"week":week,"month":start.strftime("%Y-%m"),
             "R":res["R"],"rr":rr,"cost":costmode,"time":bars[j].time,
             "side":side,"exit":res["reason"],"tick_count":res["tick_count"],
             "entry_spread":res["entry_spread"]})
     if ix%22==0:print("PROGRESS",ix,"/",len(events),"evaluated",len(records),"invalid",dict(invalid),flush=True)
  finally:mt5.shutdown()
  result={"kind":"KATARINA_XAU_OR_TREND_BREAK_BROKER_REAL_TICK_PATH_REPLAY",
      "strategy":"UTC06 first hour range; 07-09 UTC H1/H4 aligned breakout; closed M5 decision",
      "stop_in_H1_ATR":STOP_H1ATR,"holding_hours":6,
      "notes":["tick Bid/Ask observed path, next-M5-first-tick simulated entries",
        "1/3 tick adverse each side, fee 0.03/0.05R ASSUMED",
        "2026 previously inspected NOT clean new holdout",
        "no broker fill confirmations, order queue, swap or portfolio cash modeling"],
      "live_orders":False,"risk_governor_unchanged":True,"invalid_events":dict(invalid),"summary":[]}
  for rr in (2.,3.):
    for cost in ("1_tick","3_tick"):
      byyear={}
      for yr in ("2025","2026"):
        v=[x for x in records if x["rr"]==rr and x["cost"]==cost and x["year"]==yr]
        byyear[yr]=metrics(v)
      result["summary"].append({"RR":rr,"cost":cost,"periods":byyear})
      print("RESULT",rr,cost,[(yr,byyear[yr].get("n"),byyear[yr].get("avg_R"),
                byyear[yr].get("PF"),byyear[yr].get("weekblock_bootstrap_ci95"))
                   for yr in ("2025","2026")],flush=True)
  out=AUDIT/"xau_intraday_real_tick_path_2025_2026.json"
  out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
  print("FILE",str(out),"TICK_SCORES",len(records),flush=True)
if __name__=="__main__":main()
