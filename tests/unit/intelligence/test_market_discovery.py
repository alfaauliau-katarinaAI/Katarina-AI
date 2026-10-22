"""Stage-0 broker discovery never invents a signal or an order."""
from datetime import datetime, timezone
import sqlite3
from types import SimpleNamespace
import unittest

from katarina.intelligence.broker.market_discovery import discover_quote_batch

NOW = datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc)


class FakeBroker:
    TIMEFRAME_M1 = 1

    def __init__(self, names, *, stale=(), unavailable=()):
        self.names = tuple(names)
        self.stale = set(stale)
        self.unavailable = set(unavailable)
        self.orders = 0
        self.calls = []

    def symbol_select(self, name, enabled):
        self.calls.append(name)
        return enabled and name not in self.unavailable

    def symbol_info_tick(self, name):
        epoch = NOW.timestamp() + 3 * 3600
        if name in self.stale:
            epoch -= 400
        return SimpleNamespace(bid=1.0, ask=1.002,
                               time_msc=int(epoch * 1000))

    def copy_rates_from_pos(self, name, frame, start, count):
        if start != 1 or frame != self.TIMEFRAME_M1:
            raise AssertionError("not using closed M1 bars")
        return [{"high": 1.2, "low": 1.1} for _ in range(count)]


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")

    def tearDown(self):
        self.db.close()

    @staticmethod
    def catalog(*symbols):
        return [SimpleNamespace(name=name, trade_mode=mode)
                for name, mode in symbols]

    def test_round_robin_covers_full_eligible_broker_catalog(self):
        names = ["PAIR%02d.vx" % i for i in range(10)]
        catalog = self.catalog(*[(n, 4) for n in names],
                               ("DISABLED", 0), ("CLOSE_ONLY", 3))
        broker = FakeBroker(names)
        scanned = set()
        for _ in range(4):
            result = discover_quote_batch(broker, self.db, catalog, NOW,
                                          clock_shift_hours=3, budget=3,
                                          deep_symbols=("EURUSD.vx",))
            self.assertEqual(result["status"], "EXPLORATORY_NO_TRADING_AUTHORITY")
            self.assertEqual(result["universe_size"], 10)
            self.assertEqual(result["observed_symbols"], ["EURUSD.vx"])
            self.assertEqual(result["entries_authorized"], 0)
            self.assertEqual(result["orders_submitted"], 0)
            self.assertLessEqual(result["surveyed"], 3)
            scanned.update(row["symbol"] for row in result["sampled"])
        self.assertEqual(scanned, set(names))
        self.assertEqual(broker.orders, 0)

    def test_stale_quote_and_failed_subscription_cannot_be_prioritized(self):
        catalog = self.catalog(("AAA", 4), ("BBB", 4), ("CCC", 4))
        broker = FakeBroker(("AAA", "BBB", "CCC"),
                            stale=("BBB",), unavailable=("CCC",))
        result = discover_quote_batch(broker, self.db, catalog, NOW,
                                      clock_shift_hours=3, budget=3)
        self.assertEqual(result["research_priority"], ["AAA"])
        by_symbol = {r["symbol"]: r for r in result["sampled"]}
        self.assertIn("stale_or_future_broker_quote", by_symbol["BBB"]["reasons"])
        self.assertIn("broker_symbol_select_failed", by_symbol["CCC"]["reasons"])
        self.assertTrue(all(r["state"] == "WAIT" for r in result["sampled"]))
        self.assertEqual(broker.orders, 0)

    def test_missing_bars_never_become_strategy_evidence(self):
        class MissingHistory(FakeBroker):
            def copy_rates_from_pos(self, *args):
                return None
        result = discover_quote_batch(
            MissingHistory(("XAUUSD.vx",)), self.db,
            self.catalog(("XAUUSD.vx", 4)), NOW,
            clock_shift_hours=3)
        self.assertEqual(result["research_priority"], [])
        self.assertIn("closed_m1_bars_unavailable",
                      result["sampled"][0]["reasons"])
        self.assertEqual(result["orders_submitted"], 0)

    def test_invalid_inputs_fail_closed_and_empty_catalog_is_safe(self):
        catalog = self.catalog(("AAA", 0), ("BBB", 3))
        b = FakeBroker(())
        result = discover_quote_batch(b, self.db, catalog, NOW,
                                      clock_shift_hours=3)
        self.assertEqual(result["status"], "NO_TRADE_ENABLED_MARKETS")
        self.assertEqual(result["surveyed"], 0)
        with self.assertRaises(ValueError):
            discover_quote_batch(b, self.db, [], NOW,
                                 clock_shift_hours=3, budget=0)
        with self.assertRaises(ValueError):
            discover_quote_batch(b, self.db, None, NOW,
                                 clock_shift_hours=3)

    def test_cost_metric_is_descriptive_not_a_trading_decision(self):
        broker = FakeBroker(("XAUUSD.vx",))
        result = discover_quote_batch(
            broker, self.db, self.catalog(("XAUUSD.vx", 4)), NOW,
            clock_shift_hours=3)
        row = result["sampled"][0]
        self.assertAlmostEqual(row["spread_to_m1_range"], 0.02)
        self.assertEqual(row["state"], "WAIT")
        self.assertIn("NOT_SETUP_SCORE", result["priority_basis"])
        self.assertEqual(broker.orders, 0)


if __name__ == "__main__":
    unittest.main()
