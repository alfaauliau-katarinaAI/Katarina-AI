"""One-hour XAUUSD micro-scalp RR screen from true tick-derived 2025/2026 M1 bars.

M1/M2/M3/M4 reconstruction avoids MT5 100k chart-bar truncation. Each
higher bar requires EVERY component M1 minute; gaps are never filled.
2026 is a reused research window, not untouched holdout. No trade orders.
"""
from __future__ import annotations
import csv,json,hashlib
from collections import OrderedDict
from pathlib import Path
import MetaTrader5 as mt5
import kfei_native_tf_2025 as k
AUDIT=Path(r"C:\KatarinaDev\artifacts\historical-brain")
src=AUDIT/"xauusd_vx_m1_tick_2025_2026.csv"
bars1=[]
with src.open(encoding="utf-8",newline="") as f:
 for row in csv.DictReader(f):
  bars1.append((int(row["time"]),float(row["open"]),float(row["high"]),
          float(row["low"]),float(row["close"]),int(row["spread"]),int(row["tick_volume"])))
print("M1_LOADED",len(bars1),flush=True)
def get_tf(n):
 if n==1:return bars1
 out=[]
 current=None
 acc=[]
 def emit():
  if len(acc)!=n:return
  if acc[0][0]!=current or acc[-1][0] != current+60*(n-1):return
  if any(acc[j][0]-acc[j-1][0]!=60 for j in range(1,n)):return
  b0=acc[0];b1=acc[-1]
  out.append((current,b0[1],max(x[2] for x in acc),min(x[3] for x in acc),
              b1[4],b1[5],sum(x[6] for x in acc)))
 for b in bars1:
  key=b[0]//(n*60)*(n*60)
  if key!=current:
   if current is not None:emit()
   current=key;acc=[b]
  else:acc.append(b)
 if current is not None:emit()
 return out
def main():
 p=AUDIT/"xauusd_m1_tick_2025_2026_audit.json"
 audit=json.loads(p.read_text(encoding="utf-8"))
 cache={}
 report={"kind":"KATARINA_XAUUSD_M1_M2_M3_M4_TICK_BAR_RR",
         "source_audit_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
         "source_csv_sha256":audit["csv_sha256"],"M1_available":len(bars1),
         "method":"Causal KFEI closed prices, next chart bar, stop-first, time exit",
         "holding_max_minutes":60,"fee_assumption_R":.03,
         "risk_governor_changed":False,"live_execution_enabled":False,
         "untouched_future_holdout":False,"results":[]}
 k.HOLD_MINUTES=60
 k.ENTRY_TF=["M1","M2","M3","M4"]
 if not mt5.initialize(path=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe",timeout=15000):
  raise RuntimeError(mt5.last_error())
 try:
  si=mt5.symbol_info("XAUUSD.vx")
  assert si is not None
  for minutes in (1,2,3,4):
    tf="M"+str(minutes)
    cache[tf]=get_tf(minutes)
    print("TF_LOADED",tf,len(cache[tf]),flush=True)
    k.native_history=lambda sym,tf:cache[tf]
    out=k.scan_one("XAUUSD.vx",tf,float(si.point),float(si.trade_tick_size or si.point))
    report["results"].append(out)
    cache.pop(tf,None)
    path=AUDIT/"katarina_xau_tick_m1_m4_rr_from_2025.json"
    path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
 finally:mt5.shutdown()
 print("RESULT",json.dumps({"candidate_runs":sum(x.get("configurations",0) for x in report["results"]),
          "2025_passing":sum(x.get("2025_passing",0) for x in report["results"]),
          "2026_positive":sum(x.get("2026_positive_among_passed",0) for x in report["results"]),
          "path":str(AUDIT/"katarina_xau_tick_m1_m4_rr_from_2025.json")}),flush=True)
if __name__=="__main__":main()
