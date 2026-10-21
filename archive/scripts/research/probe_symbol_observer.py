"""Single read-only smoke test of registered per-symbol live observer routing."""
from datetime import datetime,timezone
import json
import MetaTrader5 as mt5
from katarina.intelligence.multi_market_brain import collect,screen
from katarina.intelligence.symbol_playbooks import SYMBOLS

class ClearContext:
    def assess(self,currencies,now):
        return dict(ready=True,reasons=[])

terminal=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe"
data=collect(mt5,terminal)
observation=screen(data,ClearContext(),datetime.now(timezone.utc))
nonregistered=[(r["symbol"],len(r.get("shadow_hypotheses",[])))
    for r in observation["symbols"]
    if r["symbol"] not in SYMBOLS and r.get("shadow_hypotheses")]
if nonregistered:
    raise RuntimeError("nonregistered_market_received_playbook")
if observation["live_execution_enabled"] is not False or observation["decision"]!="NO_TRADE":
    raise RuntimeError("real_trading_not_blocked")
print(json.dumps(dict(kind="symbol_specific_observer_smoke",
  symbols_scanned=observation["symbols_scanned"],
  registered_markets=len(SYMBOLS),
  shadow_candidate_count=observation["shadow_candidate_count"],
  unknown_market_signals=nonregistered,
  live_execution_enabled=observation["live_execution_enabled"],
  decision=observation["decision"],
  any_broker_error=sum(bool(r.get("errors")) for r in observation["symbols"]))))
