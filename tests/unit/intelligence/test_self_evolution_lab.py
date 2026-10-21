"""Deterministic, no-LLM/MT5, retrospective held-out shadow evolution tests."""
from datetime import datetime, timedelta, timezone
import sqlite3
import unittest

from katarina.intelligence.cognition.self_evolution_lab import (
    evaluate_shadow_self_evolution,derive_shadow_research_policy, VERSION,
)
from katarina.intelligence.shadow.prospective_shadow_book import (
    ProspectiveShadowBook,ResearchHypothesis,
)

START = datetime(2026, 7, 1, tzinfo=timezone.utc)
AT = START + timedelta(days=40)


def mkdb():
    db = sqlite3.connect(":memory:")
    db.execute("""CREATE TABLE prospective_shadow(
        id INTEGER PRIMARY KEY, symbol TEXT, method TEXT, side TEXT,
        regime TEXT, observed_at REAL, exit_at REAL, state TEXT,
        virtual_net_r REAL, evidence_score REAL, official_news_verified INTEGER)""")
    return db


def sample(db, days=30, high=2.0, low=-1.0, pending=0):
    identity=0
    for day in range(days):
        for j in range(8):
            identity+=1
            when=(START + timedelta(days=day,hours=j+1)).timestamp()
            high_score=j%2==0
            value=high if high_score else low
            db.execute("""INSERT INTO prospective_shadow VALUES
                    (?,?,?,?,?,?,?,?,?,?,?)""",(
                identity,"XAUUSD.vx","SWEEP","SELL","TREND_DOWN",
                when,when+3600,"VIRTUAL_QUOTED",
                value,.85 if high_score else .64,1))
    for j in range(pending):
        identity+=1
        when=(START+timedelta(days=days,hours=j)).timestamp()
        db.execute("INSERT INTO prospective_shadow VALUES(?,?,?,?,?,?,?,?,?,?,?)",(
            identity,"XAUUSD.vx","SWEEP","SELL","TREND_DOWN",
            when,None,"OPEN",None,.85,0))
    db.commit()


class SelfEvolutionLabTests(unittest.TestCase):
    def setUp(self):
        # sqlite3 context managers commit/rollback but DO NOT close connections.
        # Track every in-memory DB so resource-bound test runs do not leak handles.
        self._owned_dbs = []

    def tearDown(self):
        for db in reversed(self._owned_dbs):
            db.close()

    def _own(self, db):
        self._owned_dbs.append(db)
        return db

    def _mkdb(self):
        return self._own(mkdb())

    def test_no_table_no_signal(self):
        x=evaluate_shadow_self_evolution(self._own(sqlite3.connect(":memory:")),as_of_utc=AT)
        self.assertEqual(x["data_integrity"],"INVALID")
        self.assertEqual(x["decision"],"WAIT_FOR_VERIFIED_EVIDENCE")
        self.assertFalse(x["promotion_allowed"])

    def test_negative_series_no_promotion(self):
        db=self._mkdb()
        sample(db,high=-.3,low=-.9)
        r=evaluate_shadow_self_evolution(db,as_of_utc=AT)
        self.assertEqual(r["cohorts"][0]["status"],"UNSTABLE_OR_NEGATIVE_QUOTE_EDGE")
        self.assertEqual(r["decision"],"WAIT_FOR_VERIFIED_EVIDENCE")

    def test_witnesses_real_train_holdout_learning_not_llm(self):
        db=self._mkdb();sample(db)
        r=evaluate_shadow_self_evolution(db,as_of_utc=AT)
        self.assertEqual(r["data_integrity"],"VALID")
        self.assertEqual(r["cohorts"][0]["proposed_min_evidence_score"],.70)
        self.assertEqual(r["cohorts"][0]["status"],"RESEARCH_CANDIDATE_REVIEW_REQUIRED")
        self.assertEqual(r["cohorts"][0]["holdout"]["observations"],36)
        self.assertGreater(r["cohorts"][0]["holdout"]["daily_cluster_lower_r"],0)
        self.assertEqual(r["decision"],"RESEARCH_PROPOSAL_ONLY")
        self.assertEqual(r["external_models_invoked"],0)
        self.assertFalse(r["promotion_allowed"])
        self.assertFalse(r["order_submission_authorized"])
        self.assertFalse(r["self_code_mutation_authorized"])
        self.assertEqual(r["live_risk_authorized_fraction"],0)
        self.assertEqual([v["pass"] for v in r["reviewers"]],
                         [True,True,False,False])
        self.assertEqual(r["version"],VERSION)

    def test_determinism_and_freshness_fingerprint(self):
        db=self._mkdb();sample(db)
        a=evaluate_shadow_self_evolution(db,as_of_utc=AT)
        b=evaluate_shadow_self_evolution(db,as_of_utc=AT)
        self.assertEqual(a,b)
        when=(START + timedelta(days=31)).timestamp()
        db.execute("INSERT INTO prospective_shadow VALUES(?,?,?,?,?,?,?,?,?,?,?)",(
            777,"XAUUSD.vx","SWEEP","SELL","TREND_DOWN",when,
            when+3600,"VIRTUAL_QUOTED",-.5,.9,1))
        c=evaluate_shadow_self_evolution(db,as_of_utc=AT)
        self.assertNotEqual(a["source_digest_sha256"],c["source_digest_sha256"])
        self.assertNotEqual(a["review_receipt_sha256"],c["review_receipt_sha256"])

    def test_time_leak_blocks(self):
        db=self._mkdb();sample(db)
        db.execute("UPDATE prospective_shadow SET exit_at=? WHERE id=1",
                   ((AT+timedelta(hours=1)).timestamp(),))
        x=evaluate_shadow_self_evolution(db,as_of_utc=AT)
        self.assertEqual(x["data_integrity"],"INVALID")
        self.assertFalse(x["promotion_allowed"])

    def test_gap_coverage_blocks_cherrypicking(self):
        db=self._mkdb();sample(db)
        # Mark 70% quote paths as uncertain without claiming loss or victory
        db.execute("""UPDATE prospective_shadow SET state='UNCERTAIN_GAP',
                   virtual_net_r=NULL WHERE id % 4 != 0""")
        x=evaluate_shadow_self_evolution(db,as_of_utc=AT)
        self.assertEqual(x["cohorts"][0]["status"],"INSUFFICIENT_EVIDENCE")
        self.assertLess(x["cohorts"][0]["coverage"],.8)

    def test_unknown_or_corrupt_record_fails_closed(self):
        db=self._mkdb();sample(db)
        db.execute("UPDATE prospective_shadow SET evidence_score=2.0 WHERE id=1")
        self.assertEqual(evaluate_shadow_self_evolution(
            db,as_of_utc=AT)["data_integrity"],"INVALID")

    def test_pending_never_treated_as_loss_or_win(self):
        db=self._mkdb();sample(db,days=5,pending=2)
        x=evaluate_shadow_self_evolution(db,as_of_utc=AT)
        self.assertEqual(x["cohorts"][0]["pending"],2)
        self.assertEqual(x["cohorts"][0]["status"],"INSUFFICIENT_EVIDENCE")

    def _candidate(self, score, *, side="SELL", now=AT):
        return ResearchHypothesis(
            symbol="XAUUSD.vx",method="SWEEP",regime="TREND_DOWN",
            side=side,closed_bar_at=now-timedelta(minutes=5),
            observed_at=now,bid=100,ask=100.1,tick_at=now.timestamp(),
            stop=101.3 if side=="SELL" else 99.,
            target=97 if side=="SELL" else 103.,
            evidence_score=score,blockers=("unverified_news",),
            official_news_verified=False,spread_atr=.05,
        )

    def test_positive_shadow_learning_changes_next_virtual_sample(self):
        past=self._mkdb()
        sample(past,days=30,high=2.,low=-1.)
        report=evaluate_shadow_self_evolution(past,as_of_utc=AT)
        learned=derive_shadow_research_policy(report)
        self.assertTrue(learned.integrity_ok)
        self.assertEqual(learned.score_floor("XAUUSD.vx","SWEEP","SELL",
                                             "TREND_DOWN"),.70)
        self.assertEqual(learned.score_floor("XAUUSD.vx","SWEEP","BUY",
                                             "TREND_DOWN"),.62)
        self.assertFalse(learned.live_execution_authorized)
        self.assertEqual(learned.to_dict()["may_change_production_model"],False)
        research_db=self._own(sqlite3.connect(":memory:"))
        book=ProspectiveShadowBook(research_db)
        rejected=book.propose([self._candidate(.64)],AT,research_policy=learned)
        self.assertFalse(rejected["accepted"])
        self.assertEqual(book.summary()["counts"],{})
        accepted=book.propose([self._candidate(.85)],AT,research_policy=learned)
        self.assertTrue(accepted["accepted"])
        self.assertEqual(book.summary()["counts"],{"OPEN":1})
        self.assertEqual(accepted["mode"],"NO_REAL_ORDERS")

    def test_negative_cohort_is_quarantined_but_buy_learns_separately(self):
        past=self._mkdb()
        sample(past,high=-.3,low=-.9)
        policy=derive_shadow_research_policy(
            evaluate_shadow_self_evolution(past,as_of_utc=AT))
        self.assertEqual(policy.score_floor("XAUUSD.vx","SWEEP","SELL",
                                             "TREND_DOWN"),.78)
        self.assertEqual(policy.score_floor("XAUUSD.vx","SWEEP","BUY",
                                             "TREND_DOWN"),.62)
        db=self._own(sqlite3.connect(":memory:"))
        book=ProspectiveShadowBook(db)
        self.assertFalse(book.propose(
            [self._candidate(.7)],AT,research_policy=policy)["accepted"])
        self.assertTrue(book.propose(
            [self._candidate(.81)],AT,research_policy=policy)["accepted"])

    def test_corrupt_shadow_learning_blocks_new_virtual_hypothesis(self):
        past=self._mkdb()
        sample(past)
        past.execute("UPDATE prospective_shadow SET evidence_score=2 WHERE id=1")
        report=evaluate_shadow_self_evolution(past,as_of_utc=AT)
        policy=derive_shadow_research_policy(report)
        self.assertFalse(policy.integrity_ok)
        db=self._own(sqlite3.connect(":memory:"))
        book=ProspectiveShadowBook(db)
        result=book.propose([self._candidate(.85)],AT,research_policy=policy)
        self.assertEqual(result["reason"],"SHADOW_LEARNING_INVALID_FAIL_CLOSED")
        self.assertEqual(book.summary()["counts"],{})

    def test_policy_from_future_is_never_applied(self):
        past=self._mkdb()
        sample(past)
        report=evaluate_shadow_self_evolution(past,as_of_utc=AT)
        policy=derive_shadow_research_policy(report)
        db=self._own(sqlite3.connect(":memory:"))
        book=ProspectiveShadowBook(db)
        with self.assertRaisesRegex(ValueError,"invalid_or_future_shadow_learning"):
            book.propose([self._candidate(.85,now=AT-timedelta(days=1))],
                         AT-timedelta(days=1),research_policy=policy)
        self.assertEqual(book.summary()["counts"],{})

    def test_asof_must_be_aware(self):
        with self.assertRaises(ValueError):
            evaluate_shadow_self_evolution(self._mkdb(),as_of_utc=datetime(2026,10,13))

if __name__=="__main__":
    unittest.main()
