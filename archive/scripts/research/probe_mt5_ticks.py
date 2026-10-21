from __future__ import annotations
from datetime import datetime, timezone
import json, subprocess, sys

TERMINALS=[
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe",
]
SYMBOLS=["XAUUSD.vx","XAUUSDc","XAUUSD"]

def worker(terminal:str)->int:
    import MetaTrader5 as mt5
    item={"terminal":terminal,"initialized":False,"last_error":None,"symbols":[]}
    try:
        ok=mt5.initialize(path=terminal,timeout=10000)
        item["initialized"]=bool(ok)
        if not ok:
            item["last_error"]=mt5.last_error()
            print(json.dumps(item,sort_keys=True));return 0
        ti=mt5.terminal_info()
        item["terminal_build"]=None if ti is None else getattr(ti,"build",None)
        item["connected"]=None if ti is None else bool(getattr(ti,"connected",False))
        for symbol in SYMBOLS:
            si=mt5.symbol_info(symbol)
            if si is None:continue
            mt5.symbol_select(symbol,True)
            start=datetime(2026,9,1,0,0,tzinfo=timezone.utc)
            end=datetime(2026,9,1,1,0,tzinfo=timezone.utc)
            ticks=mt5.copy_ticks_range(symbol,start,end,mt5.COPY_TICKS_ALL)
            rec={
                "symbol":symbol,
                "digits":getattr(si,"digits",None),
                "tick_size":getattr(si,"trade_tick_size",None),
                "tick_value_loss":getattr(si,"trade_tick_value_loss",None),
                "count":0 if ticks is None else int(len(ticks)),
                "copy_error":None if ticks is not None else mt5.last_error(),
            }
            if ticks is not None and len(ticks):
                rec.update({
                    "first_time_msc":int(ticks[0]["time_msc"]),
                    "last_time_msc":int(ticks[-1]["time_msc"]),
                    "first_bid":float(ticks[0]["bid"]),
                    "first_ask":float(ticks[0]["ask"]),
                    "last_bid":float(ticks[-1]["bid"]),
                    "last_ask":float(ticks[-1]["ask"]),
                })
            item["symbols"].append(rec)
        print(json.dumps(item,sort_keys=True))
        return 0
    except Exception as exc:
        item["exception"]=str(exc)
        print(json.dumps(item,sort_keys=True))
        return 0
    finally:
        try:mt5.shutdown()
        except Exception:pass

def main()->int:
    if len(sys.argv)>=3 and sys.argv[1]=="--worker":
        return worker(sys.argv[2])
    results=[]
    for terminal in TERMINALS:
        try:
            p=subprocess.run([sys.executable,__file__,"--worker",terminal],capture_output=True,text=True,timeout=25)
            lines=[x for x in p.stdout.splitlines() if x.strip()]
            if lines:
                try:results.append(json.loads(lines[-1]))
                except Exception:results.append({"terminal":terminal,"parse_error":lines[-1]})
            else:
                results.append({"terminal":terminal,"worker_exit_code":p.returncode,"stderr":p.stderr[-1000:]})
        except subprocess.TimeoutExpired:
            results.append({"terminal":terminal,"initialized":False,"hard_timeout":True})
    print(json.dumps({"proof_type":"KATARINA_MT5_PYTHON_TICK_PROBE","results":results},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
