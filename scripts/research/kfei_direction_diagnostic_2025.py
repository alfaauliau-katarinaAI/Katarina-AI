"""KATARINA KFEI next-closed-candle direction diagnostic by timeframe.

Only price direction, NOT trading profits; no position opens.
Test predeclared drive class without optimizing its numeric thresholds.
2026 has previously been inspected, so not untouched OOS.
"""
from __future__ import annotations
import json,sys
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
DIR=Path(r"C:\KatarinaDev\artifacts\historical-brain")
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kfei_native_tf_2025 import native_history,xau_recon,labels_and_signal,FRAME_MINUTES
import MetaTrader5 as mt5
def main():
 result={"kind":"KATARINA_KFEI_drive_next_candle_direction_diagnostic",
         "not_cash_returns":True,"not_independent_new_data":True,
         "no_live_orders":True,"symbols":[]}
 if not mt5.initialize(path=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe",timeout=15000):
  raise RuntimeError(mt5.last_error())
 try:
  for symbol in ("XAUUSD.vx","NAS100.vx","EURUSD.vx"):
   report={"symbol":symbol,"timeframes":[]}
   for tf in FRAME_MINUTES:
     bars=native_history(symbol,tf)
     if symbol=="XAUUSD.vx" and tf=="M5":bars=xau_recon(bars)
     if len(bars)<100:continue
     sig=labels_and_signal(bars,FRAME_MINUTES[tf])
     buckets=defaultdict(list)
     latest_idx={"2025":-5,"2026":-5}
     for index,side,atr,mode,drive in sig:
      if mode!="DRIVE_CONTINUATION" or index+1>=len(bars):continue
      period=str(datetime.fromtimestamp(bars[index][0],tz=timezone.utc).year)
      if period not in ("2025","2026"):continue
      if index-latest_idx[period]<3:continue
      # Price move from closed setup candle to next candle close, no costs.
      current=bars[index-1][4];next_close=bars[index][4]
      if abs(next_close-current)<1e-9:continue
      signed=side*(next_close-current)/max(1e-12,atr)
      buckets[period].append((1 if signed>0 else 0,signed))
      latest_idx[period]=index
     rec={"tf":tf}
     for year in ("2025","2026"):
      xs=buckets[year]
      n=len(xs)
      rec[year]={"n":n,"continuation_frac":round(sum(z[0] for z in xs)/n,5) if n else None,
              "mean_directional_move_ATR":round(sum(z[1] for z in xs)/n,5) if n else None}
     report["timeframes"].append(rec)
   result["symbols"].append(report)
   print("DONE",symbol,[(r["tf"],r["2025"]["n"],r["2025"]["continuation_frac"],
        r["2026"]["n"],r["2026"]["continuation_frac"]) for r in report["timeframes"]
        if r["2025"]["n"]>=60 and r["2026"]["n"]>=60][:19],flush=True)
 finally:mt5.shutdown()
 (DIR/"katarina_kfei_direction_by_timeframe.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
