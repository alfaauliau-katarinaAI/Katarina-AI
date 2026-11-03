"""WP4 observer isolation: a failing candidate ledger never changes the decision.

Adopted from the Jules WP4 test idea (PR #261, observer non-interference) and run
against the canonical observer with the synthetic broker. No orders, no network.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from tests.integration.test_brain_owned_workflow import SyntheticBroker
from tests.synthetic_clock_fixture import ModuleClockFixture


def _observe(root, broker):
    return UnifiedKatarinaBrain.observe_once(root, broker=broker, max_symbols=3, fetch_news=False)


def _decisions(report):
    return {symbol: (card["action"], card.get("conditional_side"), tuple(card["blocking_reasons"]))
            for symbol, card in report["symbols"].items()}


class CandidateLedgerIsolationTests(unittest.TestCase):
    def test_observer_records_candidates_for_every_symbol(self):
        broker = SyntheticBroker()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = _observe(root, broker)
            report = json.loads((root / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(report["research_candidates"], {"status": "RECORDED", "rows": 3})
            with closing(sqlite3.connect(root / "context.sqlite3")) as db:
                rows = db.execute("SELECT symbol FROM research_candidates WHERE cycle_id=?",
                                  (result["ledger_cycle_id"],)).fetchall()
            self.assertEqual(len(rows), 3)
            self.assertEqual(result["orders_submitted"], 0)
            self.assertEqual(broker.orders, 0)

    def test_candidate_ledger_failure_does_not_change_decision_or_ledger(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            _observe(Path(first), SyntheticBroker())
            baseline = json.loads((Path(first) / "latest.json").read_text(encoding="utf-8"))
            broker = SyntheticBroker()
            with patch("katarina.intelligence.operations.candidate_ledger.record",
                       side_effect=RuntimeError("disk full")):
                result = _observe(Path(second), broker)
            report = json.loads((Path(second) / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(report["research_candidates"], {"status": "FAILED", "error": "RuntimeError"})
            self.assertEqual(report["observation_ledger"]["status"], "RECORDED")
            self.assertEqual(_decisions(report), _decisions(baseline))
            self.assertEqual(result["orders_submitted"], 0)
            self.assertEqual(broker.orders, 0)


_clock_fixture = ModuleClockFixture()


def setUpModule():
    _clock_fixture.start()


def tearDownModule():
    _clock_fixture.stop()


if __name__ == "__main__":
    unittest.main()
