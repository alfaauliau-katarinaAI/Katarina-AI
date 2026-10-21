"""Auditable evidence checker for KATARINA multi-market V2 test from 2025."""
from __future__ import annotations
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
DIR=Path(r"C:\KatarinaDev\artifacts\historical-brain")
source=DIR/"backtest_adaptive_brain_v2_from_2025.json"
payload=source.read_bytes()
result=json.loads(payload)
assert result["live_execution_enabled"] is False
assert result["model_promotion_allowed"] is False
assert len(result["symbol_results"])==7
stats={}
for item in result["symbol_results"]:
 assert not item.get("error"),item.get("error")
 symbol=item["symbol"]
 entries=item["trades"]
 assert len(entries)==sum(item["periods"][p]["stats"]["n"] for p in ("2025","2026"))
 # Each trade entry is a different 15-minute signal, ordered, no lookahead timestamps.
 assert all(entries[i]["time"]<=entries[i+1]["time"] for i in range(len(entries)-1))
 assert len({e["time"] for e in entries})==len(entries)
 assert all(e["period"] in ("2025","2026") for e in entries)
 for yr in (2025,2026):
  arr=[e for e in entries if e["period"]==str(yr)]
  assert all(datetime.fromtimestamp(e["time"],tz=timezone.utc).year==yr for e in arr)
  stored=item["periods"][str(yr)]["stats"]
  assert stored["n"]==len(arr)
  assert abs(sum(float(x["R"]) for x in arr)-stored["sum_R"])<.002
  assert all(x["exit"] in ("SL","TP","TIME") for x in arr)
 stats[symbol]={"2025_n":item["periods"]["2025"]["stats"]["n"],
                "2026_n":item["periods"]["2026"]["stats"]["n"],
                "first_bar":item["first_bar_utc"],
                "last_bar":item["last_bar_utc"]}
audit={"audit":"KATARINA_2025_2026_BACKTEST_INTEGRITY",
 "source_sha256":hashlib.sha256(payload).hexdigest(),
 "symbols_verified":len(stats),"trades_2025":sum(x["2025_n"] for x in stats.values()),
 "trades_2026":sum(x["2026_n"] for x in stats.values()),
 "checks":["no live execution","no promotion","entry time monotonic","no repeated signal times",
  "per year trade period consistency","per year sums and counts match individual trades",
  "trade exit category is recognized"],
 "sources":stats,"passed":True}
dest=DIR/"backtest_2025_2026_integrity_audit.json"
dest.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
print(json.dumps(audit,indent=2))
