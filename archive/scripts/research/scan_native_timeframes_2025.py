"""MT5 native 21 timeframe coverage, sample years (read-only)."""
import MetaTrader5 as mt5
from datetime import datetime,timezone,timedelta
import json
pairs=["M1","M2","M3","M4","M5","M6","M10","M12","M15","M20","M30","H1","H2","H3","H4","H6","H8","H12","D1","W1","MN1"]
out=[]
if not mt5.initialize(path=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe",timeout=15000):raise SystemExit(str(mt5.last_error()))
try:
 for sym in ["XAUUSD.vx","NAS100.vx","EURUSD.vx"]:
  for tf in pairs:
   t=getattr(mt5,"TIMEFRAME_"+tf)
   one=mt5.copy_rates_range(sym,t,datetime(2025,7,14,tzinfo=timezone.utc),datetime(2025,7,21,tzinfo=timezone.utc))
   two=mt5.copy_rates_range(sym,t,datetime(2026,9,14,tzinfo=timezone.utc),datetime(2026,9,21,tzinfo=timezone.utc))
   out.append({"symbol":sym,"timeframe":tf,"2025_count":-1 if one is None else len(one),
    "2026_count":-1 if two is None else len(two)})
finally:mt5.shutdown()
p=r"C:\KatarinaDev\artifacts\historical-brain\mt5_native_21_timeframes_2025_2026.json"
open(p,"w",encoding="utf-8").write(json.dumps(out,indent=2))
for sym in ["XAUUSD.vx","NAS100.vx","EURUSD.vx"]:
 print(sym,[(x["timeframe"],x["2025_count"],x["2026_count"]) for x in out if x["symbol"]==sym])
