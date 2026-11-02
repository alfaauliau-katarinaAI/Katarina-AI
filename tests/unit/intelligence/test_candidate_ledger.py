import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path

from katarina.intelligence.operations import candidate_ledger


class CandidateLedgerTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_setup_creates_table_with_unique_constraint(self):
        candidate_ledger.setup(self.db)
        cur = self.db.cursor()
        cur.execute("PRAGMA table_info(research_candidates)")
        cols = {row[1]: row[2] for row in cur.fetchall()}
        self.assertIn("cycle_id", cols)
        self.assertIn("symbol", cols)
        self.assertIn("closed_m5_utc", cols)
        self.assertIn("observed_utc", cols)
        self.assertIn("market_state", cols)
        self.assertIn("direction_bias", cols)
        self.assertIn("selected_method", cols)
        self.assertIn("technical_setup", cols)
        self.assertIn("technical_evidence_score", cols)
        self.assertIn("conditional_side", cols)
        self.assertIn("conditional_invalidation", cols)
        self.assertIn("conditional_target", cols)
        self.assertIn("after_spread_rr_geometry", cols)
        self.assertIn("spread", cols)
        self.assertIn("bid", cols)
        self.assertIn("ask", cols)
        self.assertIn("tick_epoch", cols)
        self.assertIn("blockers_json", cols)

    def test_record_records_wait_and_actionable_cards_idempotently(self):
        cycle_id = "c-20261102T120000.000Z"
        cards = {
            "EURUSD": {
                "observed_vps_timestamp_utc": "2026-11-02T12:00:00Z",
                "closed_bar_times_utc": {"M5": "2026-11-02T11:55:00Z"},
                "market_state": "TREND_UP",
                "direction_bias": "BUY",
                "selected_method": "PULLBACK",
                "technical_setup": "M5_PULLBACK",
                "action": "WAIT",
                "conditional_side": "WAIT",
                "technical_evidence_score": 0.45,
                "conditional_invalidation": None,
                "conditional_target": None,
                "after_spread_rr_geometry": None,
                "blocking_reasons": ["insufficient_technical_evidence"],
            },
            "USDJPY": {
                "analyzed_at_utc": "2026-11-02T12:00:00Z",
                "market_state": "BREAKOUT_DOWN",
                "direction_bias": "SELL",
                "selected_method": "BREAKOUT",
                "technical_setup": "M5_BREAKOUT",
                "action": "PAPER_OBSERVATION_ONLY",
                "conditional_side": "SELL",
                "technical_evidence_score": 0.82,
                "conditional_invalidation": 154.20,
                "conditional_target": 152.80,
                "after_spread_rr_geometry": 2.1,
                "blocking_reasons": [],
            },
        }
        quotes = {
            "EURUSD": (1.08500, 1.08512, 1790000000.0),
            "USDJPY": (153.500, 153.515, 1790000001.0),
        }

        # First recording
        recorded = candidate_ledger.record(self.db, cycle_id=cycle_id, cards=cards, quotes=quotes)
        self.assertEqual(recorded, 2)

        cur = self.db.cursor()
        cur.execute("SELECT symbol, conditional_side, spread, blockers_json FROM research_candidates ORDER BY symbol")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "EURUSD")
        self.assertEqual(rows[0][1], "WAIT")
        self.assertAlmostEqual(rows[0][2], 0.00012, places=6)
        self.assertIn("insufficient_technical_evidence", rows[0][3])

        self.assertEqual(rows[1][0], "USDJPY")
        self.assertEqual(rows[1][1], "SELL")
        self.assertAlmostEqual(rows[1][2], 0.015, places=6)

        # Duplicate recording for the same cycle_id and symbols must be ignored without error
        recorded_again = candidate_ledger.record(self.db, cycle_id=cycle_id, cards=cards, quotes=quotes)
        self.assertEqual(recorded_again, 2)
        cur.execute("SELECT count(*) FROM research_candidates")
        self.assertEqual(cur.fetchone()[0], 2)

    def test_observer_non_interference_when_candidate_ledger_fails(self):
        """Simulate candidate_ledger failure during observer cycle: decisions/action must remain intact."""
        from types import SimpleNamespace

        store = SimpleNamespace(db=self.db)
        report = {
            "symbols": {
                "EURUSD": {
                    "action": "WAIT",
                    "conditional_side": "WAIT",
                    "market_state": "SIDEWAYS",
                }
            }
        }
        latest_quotes = {"EURUSD": (1.08500, 1.08510, 1790000000.0)}

        with patch("katarina.intelligence.operations.candidate_ledger.record", side_effect=RuntimeError("disk_full")):
            try:
                candidate_ledger.record(store.db, cycle_id="c-test", cards=report["symbols"], quotes=latest_quotes)
                report["research_candidates"] = {"status": "RECORDED"}
            except Exception as ex:
                report["research_candidates"] = {"status": "FAILED", "error": type(ex).__name__}

        self.assertEqual(report["research_candidates"], {"status": "FAILED", "error": "RuntimeError"})
        self.assertEqual(report["symbols"]["EURUSD"]["action"], "WAIT")


if __name__ == "__main__":
    unittest.main()
