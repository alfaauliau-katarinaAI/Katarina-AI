"""Self-evolution must reject repeated causal events and truncated cohorts."""
from datetime import datetime, timedelta, timezone
import sqlite3
import unittest
from unittest.mock import patch

from katarina.intelligence.cognition.self_evolution_lab import (
    _read, evaluate_shadow_self_evolution, derive_shadow_research_policy,
)
from katarina.intelligence.cognition.unified_cognitive_cycle import run_unified_cognitive_cycle

CLOCK=datetime(2026,10,14,12,0,tzinfo=timezone.utc)


class StrictShadowIndependenceTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("""CREATE TABLE prospective_shadow (
            id INTEGER PRIMARY KEY,
            symbol TEXT, method TEXT, side TEXT, regime TEXT,
            observed_at REAL, exit_at REAL, state TEXT,
            virtual_net_r REAL, evidence_score REAL,
            official_news_verified INTEGER
        )""")

    def tearDown(self):
        self.db.close()

    def insert(self, index, *, at=None, side="BUY", method="SWEEP",
               symbol="XAUUSD", regime="TREND_UP"):
        obs=(CLOCK-timedelta(days=5,hours=index)).timestamp() if at is None else at
        self.db.execute(
            "INSERT INTO prospective_shadow (id,symbol,method,side,regime,"
            "observed_at,exit_at,state,virtual_net_r,evidence_score,"
            "official_news_verified) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (index+1,symbol,method,side,regime,obs,obs+60,
             "VIRTUAL_QUOTED",.8,.8,0))
        self.db.commit()

    def test_duplicate_causal_outcome_aborts_all_research_instead_of_double_counting(self):
        t=(CLOCK-timedelta(days=2)).timestamp()
        self.insert(0,at=t)
        self.insert(1,at=t)
        rows,issue=_read(self.db,CLOCK.timestamp())
        self.assertEqual(rows,[])
        self.assertEqual(issue,"duplicate_causal_shadow_observation")
        report=evaluate_shadow_self_evolution(self.db,as_of_utc=CLOCK)
        self.assertEqual(report["data_integrity"],"INVALID")
        self.assertFalse(report["promotion_allowed"])
        self.assertEqual(report["decision"],"WAIT_FOR_VERIFIED_EVIDENCE")
        self.assertFalse(derive_shadow_research_policy(report).integrity_ok)

    def test_different_buy_sell_at_same_time_remain_distinct(self):
        t=(CLOCK-timedelta(days=2)).timestamp()
        self.insert(0,at=t,side="BUY")
        self.insert(1,at=t,side="SELL")
        rows,issue=_read(self.db,CLOCK.timestamp())
        self.assertIsNone(issue)
        self.assertEqual(len(rows),2)
        self.assertEqual({x["side"] for x in rows},{"BUY","SELL"})

    def test_different_strategy_same_instant_is_not_wrongly_equated(self):
        t=(CLOCK-timedelta(days=2)).timestamp()
        self.insert(0,at=t,method="SWEEP")
        self.insert(1,at=t,method="RANGE_FADE")
        rows,issue=_read(self.db,CLOCK.timestamp())
        self.assertIsNone(issue)
        self.assertEqual(len(rows),2)

    def test_old_history_cannot_silently_drop_at_maximum_capacity(self):
        self.insert(0)
        self.insert(1)
        self.insert(2)
        with patch("katarina.intelligence.cognition.self_evolution_lab.MAX_ROWS",2):
            rows,issue=_read(self.db,CLOCK.timestamp())
            self.assertEqual(rows,[])
            self.assertEqual(issue,"shadow_observation_window_truncated")
            report=evaluate_shadow_self_evolution(self.db,as_of_utc=CLOCK)
            self.assertEqual(report["data_integrity"],"INVALID")
            self.assertEqual(report["cohorts"],[])
            self.assertFalse(derive_shadow_research_policy(report).integrity_ok)

    def test_exact_capacity_still_permits_research_only_preview(self):
        self.insert(0)
        self.insert(1)
        with patch("katarina.intelligence.cognition.self_evolution_lab.MAX_ROWS",2):
            rows,issue=_read(self.db,CLOCK.timestamp())
            self.assertIsNone(issue)
            self.assertEqual(len(rows),2)
            report=evaluate_shadow_self_evolution(self.db,as_of_utc=CLOCK)
            self.assertEqual(report["data_integrity"],"VALID")
            self.assertFalse(report["promotion_allowed"])
            self.assertFalse(report["order_submission_authorized"])

    def test_future_snapshot_is_not_leaked_into_past_evaluation(self):
        self.insert(0)
        self.insert(1,at=(CLOCK+timedelta(days=1)).timestamp())
        rows,issue=_read(self.db,CLOCK.timestamp())
        self.assertIsNone(issue)
        self.assertEqual(len(rows),1)
        self.assertTrue(all(row["observed"]<=CLOCK.timestamp() for row in rows))

    def test_corrupt_duplicate_blocks_persistent_cognitive_checkpoint_creation(self):
        at=(CLOCK-timedelta(days=2)).timestamp()
        self.insert(0,at=at)
        self.insert(1,at=at)
        with self.assertRaisesRegex(ValueError,"duplicate_causal_shadow_observation"):
            run_unified_cognitive_cycle(self.db,as_of_utc=CLOCK)
        self.assertIsNone(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name='katarina_cognitive_ledger'"
        ).fetchone())


if __name__=="__main__":
    unittest.main()
