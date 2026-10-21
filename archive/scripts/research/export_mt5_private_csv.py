"""Export read-only M15 bid bars from locally authorized MT5 to PRIVATE workspace.
No order_send, account details, credentials, raw tick redistribution or Github publishing.
"""
import csv,json,sys
from datetime import datetime,timezone
from pathlib import Path
import MetaTrader5 as mt5

OUT=Path(r"C:\KatarinaDev\private-market-data\mt5_20261012_m15.csv")
OUT.parent.mkdir(parents=True,exist_ok=True)
if not mt5.initialize():
    raise RuntimeError(f"MT5 unavailable: {mt5.last_error()}")
term=mt5.terminal_info()
print("connected",term.connected,"trade_allowed",term.trade_allowed,flush=True)
all_symbols=[x for x in (mt5.symbols_get() or []) if x.trade_mode!=mt5.SYMBOL_TRADE_MODE_DISABLED]
rows_written=0;coverage={}
with OUT.open("w",newline="",encoding="utf-8") as fd:
    writer=csv.writer(fd)
    writer.writerow(["symbol","time","open","high","low","close","spread","point","volume"])
    for i,s in enumerate(all_symbols,1):
        if not mt5.symbol_select(s.name,True):
            coverage[s.name]={"error":"selection failed"};continue
        arr=mt5.copy_rates_from_pos(s.name,mt5.TIMEFRAME_M15,1,5000)
        if arr is None or len(arr)<250:
            coverage[s.name]={"error":"insufficient bars","bars":0 if arr is None else len(arr)};continue
        arr=sorted(arr,key=lambda x:x["time"]);point=float(s.point)
        for r in arr:
            writer.writerow([s.name,int(r["time"]),float(r["open"]),float(r["high"]),
                float(r["low"]),float(r["close"]),int(r["spread"]),point,int(r["tick_volume"])])
        coverage[s.name]={"bars":len(arr),"first":datetime.fromtimestamp(int(arr[0]["time"]),timezone.utc).isoformat(),
            "last":datetime.fromtimestamp(int(arr[-1]["time"]),timezone.utc).isoformat()}
        rows_written+=len(arr)
        print("EXPORT",i,"/",len(all_symbols),s.name,len(arr),flush=True)
mt5.shutdown()
(OUT.parent/"export_coverage.json").write_text(json.dumps({"symbols":coverage,"bars":rows_written,"source":"MT5 M15 bid history; READ ONLY","public_git_upload":False},indent=2),encoding="utf-8")
print("EXPORT_DONE",len(all_symbols),"SYMBOLS",rows_written,"BARS",OUT.stat().st_size,"BYTES",flush=True)