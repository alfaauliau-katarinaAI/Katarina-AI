"""WP9b synthetic broker acceptance: active and counterfactual, no orders."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from tests.integration.test_brain_owned_workflow import SyntheticBroker


class DecisionShadowAcceptanceTests(unittest.TestCase):
    @staticmethod
    def _observe(root, broker, config=None):
        return UnifiedKatarinaBrain.observe_once(
            root, broker=broker, max_symbols=1, fetch_news=False,
            **({"decision_inputs": str(config)} if config is not None else {}),
        )

    def test_legacy_active_decision_and_measured_shadow_have_no_order(self):
        broker = SyntheticBroker()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = self._observe(root, broker)
            report = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(result["orders_submitted"], 0)
            self.assertFalse(report["live_execution_authorized"])
            self.assertEqual(report["decision_shadow_ledger"]["status"], "RECORDED")
            symbol = next(iter(report["symbols"]))
            card = report["symbols"][symbol]
            self.assertIn("system_unhealthy", card["blocking_reasons"])
            self.assertEqual(card["action"], "WAIT")
            self.assertEqual(broker.orders, 0)
            with closing(sqlite3.connect(root / "context.sqlite3")) as db:
                rows = db.execute(
                    "SELECT symbol,mode,action,conditional_side,blockers_json "
                    "FROM decision_shadow WHERE cycle_id=?",
                    (result["ledger_cycle_id"],),
                ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0:3], (symbol, "measured_inputs", "WAIT"))
            self.assertIn("system_unhealthy", json.loads(rows[0][4]))
            self.assertEqual(broker.orders, 0)

    def test_measured_active_fails_without_previous_then_uses_recorded_history(self):
        broker = SyntheticBroker()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "decision_inputs.json"
            config.write_text(
                json.dumps({"schema_version": 1, "mode": "measured_inputs"}),
                encoding="utf-8",
            )
            first = self._observe(root, broker, config)
            initial = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            card1 = next(iter(initial["symbols"].values()))
            self.assertIn("system_unhealthy", card1["blocking_reasons"])
            second = self._observe(root, broker, config)
            report = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            card2 = next(iter(report["symbols"].values()))
            self.assertNotIn("system_unhealthy", card2["blocking_reasons"])
            self.assertIn("no_verified_relevant_news", card2["blocking_reasons"])
            self.assertEqual(report["decision_shadow_ledger"]["rows"], 1)
            self.assertEqual(second["orders_submitted"], 0)
            with closing(sqlite3.connect(root / "context.sqlite3")) as db:
                row = db.execute(
                    "SELECT mode,blockers_json FROM decision_shadow WHERE cycle_id=?",
                    (second["ledger_cycle_id"],),
                ).fetchone()
                self.assertEqual(row[0], "legacy_fail_closed")
                self.assertIn("system_unhealthy", json.loads(row[1]))
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM decision_shadow "
                        "WHERE cycle_id IN (?,?)",
                        (first["ledger_cycle_id"], second["ledger_cycle_id"]),
                    ).fetchone()[0],
                    2,
                )
            self.assertEqual(broker.orders, 0)


if __name__ == "__main__":
    unittest.main()
