"""WP4 research-candidate ledger regression: WAIT, idempotence, and causality.

No MT5, no orders and no live observer process.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sqlite3
import unittest

from katarina.intelligence.operations import candidate_ledger
from katarina.intelligence.operations import observation_ledger

NOW = datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc)


def card(**updates):
    result = {
        "action": "WAIT",
        "market_state": "UPTREND",
        "direction_bias": "BUY",
        "selected_method": "pullback",
        "technical_setup": "M5_RETEST",
        "technical_evidence_score": 0.57,
        "conditional_side": "BUY",
        "conditional_invalidation": 100.0,
        "conditional_target": 105.0,
        "after_spread_rr_geometry": 2.4,
        "broker_spread_price": 0.2,
        "blocking_reasons": ["forward_experience_not_verified"],
        "closed_bar_times_utc": {"M5": (NOW - timedelta(minutes=5)).isoformat()},
    }
    result.update(updates)
    return result


class CandidateLedgerTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.cards = {"XAUUSD.vx": card()}
        self.quotes = {"XAUUSD.vx": (102.0, 102.2, NOW.timestamp() - 1)}
        self.cid = observation_ledger.record_snapshot(
            self.db, observed_utc=NOW, clock_shift_hours=0,
            cards=self.cards, quotes=self.quotes
        )

    def count(self):
        return self.db.execute("SELECT COUNT(*) FROM research_candidates").fetchone()[0]

    def test_records_wait_with_candidate_side_and_zero_orders(self):
        before = json.loads(json.dumps(self.cards))
        self.assertEqual(candidate_ledger.record(
            self.db, cycle_id=self.cid, cards=self.cards, quotes=self.quotes), 1)
        row = self.db.execute(
            "SELECT market_state, conditional_side, selected_method, blockers_json, spread, "
            "closed_m5_utc FROM research_candidates"
        ).fetchone()
        self.assertEqual(row[:3], ("UPTREND", "BUY", "pullback"))
        self.assertEqual(json.loads(row[3]), ["forward_experience_not_verified"])
        self.assertAlmostEqual(row[4], .2)
        self.assertEqual(row[5], (NOW - timedelta(minutes=5)).isoformat())
        self.assertEqual(self.cards, before)
        self.assertEqual(self.cards["XAUUSD.vx"]["action"], "WAIT")
        orders = self.db.execute(
            "SELECT orders_submitted FROM observer_cycles WHERE cycle_id=?", (self.cid,)
        ).fetchone()
        self.assertEqual(orders[0], 0)

    def test_idempotent_no_overwrite_on_duplicate_cycle(self):
        candidate_ledger.record(self.db, cycle_id=self.cid, cards=self.cards, quotes=self.quotes)
        self.assertEqual(self.count(), 1)
        modified = {"XAUUSD.vx": card(selected_method="fibonacci")}
        candidate_ledger.record(self.db, cycle_id=self.cid, cards=modified, quotes=self.quotes)
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.db.execute(
            "SELECT selected_method FROM research_candidates").fetchone()[0], "pullback")

    def test_missing_sensor_quote_still_has_wait_row(self):
        self.cards = {"XAUUSD.vx": {
            "action": "WAIT", "conditional_side": "WAIT",
            "market_state": "UNKNOWN", "blocking_reasons": ["sensor_unavailable"],
        }}
        self.assertEqual(candidate_ledger.record(
            self.db, cycle_id=self.cid, cards=self.cards, quotes={}), 1)
        row = self.db.execute(
            "SELECT bid,ask,tick_epoch,blockers_json FROM research_candidates").fetchone()
        self.assertEqual(row[:3], (None, None, None))
        self.assertEqual(json.loads(row[3]), ["sensor_unavailable"])

    def test_future_closed_bar_cannot_be_recorded(self):
        before = self.db.execute("SELECT COUNT(*) FROM observer_quotes").fetchone()[0]
        with self.assertRaisesRegex(ValueError, "LOOKAHEAD"):
            candidate_ledger.record(
                self.db, cycle_id=self.cid,
                cards={"XAUUSD.vx": card(closed_bar_times_utc={
                    "M5": (NOW + timedelta(minutes=5)).isoformat()
                })}, quotes=self.quotes)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM observer_quotes").fetchone()[0], before)
        self.assertIsNone(self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='research_candidates'").fetchone())

    def test_invalid_second_symbol_does_not_half_insert(self):
        cards = {"A.vx": card(), "B.vx": card(conditional_side="OPEN_LIVE")}
        with self.assertRaisesRegex(ValueError, "SIDE_INVALID"):
            candidate_ledger.record(
                self.db, cycle_id=self.cid,
                cards=cards, quotes={"A.vx": (100.0, 100.2, NOW.timestamp())})
        self.assertIsNone(self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='research_candidates'").fetchone())

    def test_nonexistent_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError, "CYCLE_MISSING"):
            candidate_ledger.record(
                self.db, cycle_id="nonexistent", cards=self.cards, quotes=self.quotes)


if __name__ == "__main__":
    unittest.main()
