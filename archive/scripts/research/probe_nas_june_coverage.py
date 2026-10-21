from datetime import datetime,timezone
import MetaTrader5 as mt5,json
terminal=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe"
assert mt5.initialize(terminal,timeout=15000)
out={}
try:
    symbol="NAS100.vx"
    for name,tf in (("M1",mt5.TIMEFRAME_M1),("M5",mt5.TIMEFRAME_M5)):
        x=mt5.copy_rates_range(symbol,tf,datetime(2026,5,28,tzinfo=timezone.utc),
                              datetime(2026,7,1,tzinfo=timezone.utc))
        out[name]=dict(bars=None if x is None else len(x),
                       error=mt5.last_error(),
                       first=(datetime.fromtimestamp(int(x[0]["time"]),timezone.utc).isoformat()
                              if x is not None and len(x) else None),
                       last=(datetime.fromtimestamp(int(x[-1]["time"]),timezone.utc).isoformat()
                             if x is not None and len(x) else None))
finally:
    mt5.shutdown()
print(json.dumps(out))
