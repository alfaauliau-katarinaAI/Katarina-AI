"""Read-only snapshot status of the scheduled market-regime observer."""
import json
from collections import Counter
from pathlib import Path
p=Path(r"C:\KatarinaDev\artifacts\multi-market-brain\latest.json")
obj=json.loads(p.read_text(encoding="utf-8"))
print("as_of_utc",obj.get("as_of_utc"))
print("symbols_scanned",obj.get("symbols_scanned"))
print("decision",obj.get("decision"))
print("live_execution_enabled",obj.get("live_execution_enabled"))
registered=[e for e in obj.get("symbols",[]) if "market_regime_v1" in e]
print("regime_registry_count",len(registered))
print("regimes",dict(Counter(e["market_regime_v1"]["regime"] for e in registered)))
print("by_symbol",[(e["symbol"],e["market_regime_v1"]["regime"],
  e["market_regime_v1"].get("reason_codes",[]))
  for e in registered])
