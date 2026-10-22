"""WP11: one normal brain-owned observer cycle despite stale clock snapshots."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from tests.integration.test_brain_owned_workflow import SyntheticBroker


class PartiallyClosedBroker(SyntheticBroker):
    SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "NAS100")

    def symbols_get(self):
        return [SimpleNamespace(name=s, trade_mode=4) for s in self.SYMBOLS]

    def symbol_info_tick(self, symbol):
        # The clock snapshot is old for two markets. Causal historical
        # prices remain available here so ledger behavior can be tested.
        age = 3800 if symbol in ("XAUUSD", "NAS100") else 2
        return SimpleNamespace(time=self.now + 10800 - age,
                               bid=2000., ask=2000.1)


class PartialClockCycleTests(unittest.TestCase):
    def test_three_fresh_two_stale_snapshots_do_not_fail_whole_cycle(self):
        broker = PartiallyClosedBroker()
        with tempfile.TemporaryDirectory() as root:
            result = UnifiedKatarinaBrain.observe_once(Path(root),
                                                        broker=broker,
                                                        fetch_news=False)
            self.assertEqual(result["observed_symbols"], 5)
            self.assertEqual(result["received_market_data_symbols"], 5)
            report = json.loads((Path(root) / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(report["observation_ledger"]["status"], "RECORDED")
            self.assertEqual(report["broker_clock_confirming_symbols"], 3)
            self.assertEqual(report["orders_submitted"], 0)
            with closing(sqlite3.connect(Path(root) / "context.sqlite3")) as db:
                quotes = db.execute(
                    "SELECT symbol,status FROM observer_quotes ORDER BY symbol"
                ).fetchall()
            self.assertEqual(len(quotes), 5)
            self.assertTrue(all(status == "OK" for _, status in quotes))
            self.assertFalse(any("sensor_reason" in report["symbols"][s]
                                 for s in ("XAUUSD", "NAS100")))
        self.assertEqual(broker.orders, 0)
        self.assertEqual(broker.shutdowns, 1)


if __name__ == "__main__":
    unittest.main()
