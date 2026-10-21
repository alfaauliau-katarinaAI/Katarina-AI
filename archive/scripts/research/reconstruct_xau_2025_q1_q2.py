"""Rebuild missing 2025 Jan-Apr XAUUSD.vx M5 bars from genuine Valetax Bid/Ask ticks.

Historical research only. One day at a time, neither account orders nor
terminal settings modified. Each generated bar uses a completed 5m bucket.
"""
from __future__ import annotations
import csv, json, sys, time
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5

SYMBOL="XAUUSD.vx"
START=datetime(2025,1,1,tzinfo=timezone.utc)
END=datetime(2025,5,1,tzinfo=timezone.utc)
OUT=Path(r"C:\KatarinaDev\artifacts\historical-brain")
def main():
  ok=mt5.initialize(path=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe",timeout=15000)
  if not ok: raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
  summary={"symbol":SYMBOL,"start":START.isoformat(),"end_exclusive":END.isoformat(),"days":[],"total_ticks":0,"total_bars":0}
  rows=[]
  try:
    si=mt5.symbol_info(SYMBOL)
    point=float(si.point)
    day=START
    while day<END:
      tick=mt5.copy_ticks_range(SYMBOL,day,day+timedelta(days=1)-timedelta(milliseconds=1),mt5.COPY_TICKS_ALL)
      stat={"utc_day":day.strftime("%Y-%m-%d"),"tick_count":0 if tick is None else int(len(tick)),"bars":0}
      if tick is None: stat["error"]=str(mt5.last_error())
      elif len(tick):
        sel=(tick["bid"]>0)&(tick["ask"]>=tick["bid"])
        t=tick[sel]
        # no timezones on numeric Unix milliseconds; always UTC by contract
        sec5=t["time_msc"]//300000*300
        unique,starts,counts=np.unique(sec5,return_index=True,return_counts=True)
        for u,st,n in zip(unique,starts,counts):
          e=st+n
          b=t["bid"][st:e]
          a=t["ask"][st:e]
          spr=np.maximum(0,(a-b)/point)
          rows.append((int(u),float(b[0]),float(np.max(b)),float(np.min(b)),float(b[-1]),
                       int(round(float(np.median(spr)))),int(n),
                       float(a[0]),float(a[-1])))
          stat["bars"]+=1
        summary["total_ticks"]+=int(len(t))
        summary["total_bars"]+=stat["bars"]
      summary["days"].append(stat)
      if day.day==1 or day.day==15:
         print("PROGRESS",day.date(),"ticks",summary["total_ticks"],"bars",summary["total_bars"],flush=True)
      day+=timedelta(days=1)
  finally: mt5.shutdown()
  target=OUT/"xauusd_vx_m5_reconstructed_2025_jan_apr.csv"
  with target.open("w",newline="",encoding="utf-8") as h:
     writer=csv.writer(h)
     writer.writerow(("time","open","high","low","close","spread","tick_volume","ask_open","ask_close"))
     writer.writerows(sorted(rows))
  summary["missing_weekdays"]=[x["utc_day"] for x in summary["days"] if x["tick_count"]==0 and datetime.fromisoformat(x["utc_day"]).weekday()<5]
  summary["file"]=str(target)
  (OUT/"xau_reconstruction_2025_audit.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
  print("RESULT",json.dumps({"total_ticks":summary["total_ticks"],"total_bars":summary["total_bars"],"missing_weekdays":summary["missing_weekdays"],"file":str(target)}),flush=True)
if __name__=="__main__": main()
