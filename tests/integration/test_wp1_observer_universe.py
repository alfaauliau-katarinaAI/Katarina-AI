"""WP1 integration: explicit Stage-0 core, missing-symbol ledger, LIVE OFF."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from katarina.adapters.automatic_connection import BoundLocalBroker
from katarina.intelligence.broker.observer_universe import ObserverUniverse
from katarina.intelligence.cognition.continuous_observation import run_continuous
from tests.integration.test_automatic_connection import AccountBroker, config


class ExplicitUniverseObserverIntegrationTests(unittest.TestCase):
    @staticmethod
    def observe(universe=None, *, max_symbols=3):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            native = AccountBroker()
            options = {} if universe is None else {"universe": universe}
            result = run_continuous(
                root, config=config(priority=("local",), attempts=1),
                factories={"local": lambda c: BoundLocalBroker(native, c)},
                max_symbols=max_symbols, max_cycles=1, fetch_news=False,
                **options,
            )
            if not (root / "latest.json").exists():
                self_fail_status = (root / "continuous-status.json").read_text(encoding="utf-8")
                with closing(sqlite3.connect(root / "context.sqlite3")) as db:
                    faults = db.execute("SELECT status, reason FROM observer_cycles").fetchall()
                raise AssertionError(f"observer_not_published: {result}; {self_fail_status}; {faults}")
            report = json.loads((root / "latest.json").read_text(
                encoding="utf-8"))
            with closing(sqlite3.connect(root / "context.sqlite3")) as db:
                rows = db.execute(
                    "SELECT symbol, status, reason FROM observer_quotes "
                    "ORDER BY symbol").fetchall()
            return result, report, rows, native.orders

    def test_universe_preserves_core_order_and_ignores_budget_2(self):
        result, report, rows, orders = self.observe(
            ObserverUniverse(("XAUUSD", "EURUSD", "GBPUSD")), max_symbols=2)
        self.assertEqual(list(report["symbols"]), ["XAUUSD", "EURUSD", "GBPUSD"])
        self.assertEqual([x[0] for x in rows], ["EURUSD", "GBPUSD", "XAUUSD"])
        self.assertTrue(all(x[1] == "OK" for x in rows))
        self.assertEqual(result["orders_submitted"], 0)
        self.assertFalse(result["live_execution_authorized"])
        self.assertEqual(orders, 0)

    def test_missing_core_is_wait_with_failed_quote_ledger_reason(self):
        result, report, rows, orders = self.observe(
            ObserverUniverse(("XAUUSD", "EURUSD", "GBPUSD", "UNLISTED")), max_symbols=2)
        self.assertEqual(report["unavailable_symbols"], ["UNLISTED"])
        self.assertEqual(report["symbols"]["UNLISTED"]["action"], "WAIT")
        self.assertEqual(report["symbols"]["UNLISTED"]["sensor_reason"],
                         "CORE_SYMBOL_UNAVAILABLE")
        self.assertIn(("UNLISTED", "FAILED", "CORE_SYMBOL_UNAVAILABLE"), rows)
        self.assertEqual(orders, 0)
        self.assertEqual(result["orders_submitted"], 0)

    def test_explicit_universe_rejects_worker_mode_before_host_lock(self):
        import os
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"KATARINA_ALL_MARKET_RESEARCH": "1"}):
                with self.assertRaisesRegex(
                        ValueError, "universe_and_all_market_research_exclusive"):
                    run_continuous(
                        Path(tmp), config=config(priority=("local",), attempts=1),
                        universe=ObserverUniverse(("XAUUSD", "EURUSD")),
                        max_cycles=1, fetch_news=False,
                    )
            self.assertFalse((Path(tmp) / "brain.lock").exists())

    def test_old_path_still_selects_three_symbols_without_universe(self):
        _, report, rows, orders = self.observe()
        self.assertEqual(len(report["symbols"]), 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(orders, 0)


if __name__ == "__main__":
    unittest.main()
