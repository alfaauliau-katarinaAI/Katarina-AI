import json
import sqlite3
import unittest

from katarina.intelligence.demo.forward_outcomes import ForwardOutcomes
from katarina.intelligence.shadow.shadow_research_evaluation import (
    FAMILY, HORIZON, evaluate,
)

START = 1791244800


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        ForwardOutcomes(self.db)

    def tearDown(self):
        self.db.close()

    def insert(self, oid, entry, side="BUY", status="OBSERVED",
               net=3., ready=True, signal_side="BUY", shadow=True):
        context = dict(context={"ready":ready},regime_detail="TREND_UP",
            shadow_hypotheses=([dict(family=FAMILY,side=signal_side,
                   research_only=True,live_risk_authorized=False)]
                   if shadow else []))
        with self.db:
            self.db.execute("""INSERT INTO forward_markouts
                (observation_id,symbol,side,horizon,entry_time,due_time,
                 entry_bid,entry_ask,entry_atr,context,status,
                 markout_bps,midpoint_bps)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (oid,"TEST",side,HORIZON,entry,entry+HORIZON,100.,101.,
                  2.,json.dumps(context),status,
                  net if status=="OBSERVED" else None,
                  (net+10) if status=="OBSERVED" else None))

    def populated(self, count=36, net=3., days=12):
        for i in range(count):
            entry = START+(i%days)*86400+(i//days)*HORIZON
            self.insert(i+1,entry,net=net)

    def test_sufficient_observations_still_not_trading_approval(self):
        self.populated()
        data = evaluate(self.db)
        self.assertEqual(len(data["groups"]),1)
        group = data["groups"][0]
        self.assertEqual(group["observed"],36)
        self.assertEqual(group["distinct_utc_days"],12)
        self.assertEqual(group["evidence_status"],"DESCRIPTIVE_SUFFICIENT")
        self.assertTrue(group["indicative_positive_quoted_markout"])
        self.assertAlmostEqual(group["mean_markout_bps"],3.)
        self.assertFalse(group["promotion_allowed"])
        self.assertFalse(data["model_promotion_allowed"])
        self.assertFalse(data["is_realized_strategy_pnl"])

    def test_pending_samples_do_not_block_matured_evidence(self):
        self.populated()
        self.insert(200,START+13*86400,status="PENDING")
        result = evaluate(self.db)["groups"][0]
        self.assertEqual(result["pending"],1)
        self.assertEqual(result["evidence_status"],"DESCRIPTIVE_SUFFICIENT")

    def test_insufficient_days_and_negative_returns(self):
        self.populated(count=36,net=-2.,days=5)
        group = evaluate(self.db)["groups"][0]
        self.assertEqual(group["evidence_status"],"INSUFFICIENT_FORWARD_EVIDENCE")
        self.assertFalse(group["indicative_positive_quoted_markout"])

    def test_missing_exit_ratio_blocks_diagnostic_threshold(self):
        self.populated()
        for i in range(15):
            self.insert(100+i,START+(i%12)*86400+3*HORIZON,
                        status="MISSING_EXIT")
        group = evaluate(self.db)["groups"][0]
        self.assertGreater(group["missing_exit"],0)
        self.assertEqual(group["evidence_status"],"INSUFFICIENT_FORWARD_EVIDENCE")

    def test_overlaps_excluded_not_counted_as_trades(self):
        self.insert(1,START)
        self.insert(2,START+120)
        group = evaluate(self.db)["groups"][0]
        self.assertEqual(group["nonoverlap_observations"],1)
        self.assertEqual(group["overlap_excluded"],1)
        self.assertEqual(group["observed"],1)

    def test_opposite_direction_and_no_signal_are_baseline(self):
        self.insert(1,START,side="SELL",signal_side="BUY")
        self.insert(2,START+HORIZON,side="BUY",shadow=False)
        self.assertEqual(evaluate(self.db)["groups"],[])

    def test_news_readiness_is_not_retroactively_filtered(self):
        self.insert(1,START,ready=True)
        self.insert(2,START+HORIZON,ready=False)
        groups = evaluate(self.db)["groups"]
        self.assertEqual(len(groups),2)
        self.assertEqual({g["entry_context_ready"] for g in groups},{True,False})

    def test_invalid_outcome_rejected(self):
        self.insert(1,START)
        self.db.execute("""UPDATE forward_markouts
            SET markout_bps=NULL WHERE observation_id=1""")
        with self.assertRaises(ValueError):
            evaluate(self.db)


if __name__=="__main__":
    unittest.main()
