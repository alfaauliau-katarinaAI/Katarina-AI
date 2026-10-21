"""Unified offline cognitive/curiosity/Adaptive Entry/Exit synthesis guards."""
import sqlite3
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from katarina.engines.adaptive_scalper import ResearchEntryPlan, ScalpSide
from katarina.intelligence.perception.adaptive_regime import MarketRead, MarketState, Playbook
from katarina.intelligence.cognition.adaptive_observation import BrainV2Observation
from katarina.intelligence.shadow.prospective_shadow_book import ProspectiveShadowBook
from katarina.intelligence.cognition.unified_cognitive_cycle import (
    run_unified_cognitive_cycle, rollback_cognitive_research,
    verify_cognitive_history,
)
from katarina.intelligence.perception.structure_exit_plan import StructuralExitPlan
from katarina.intelligence.cognition.unified_adaptive_research_cycle import (
    synthesize_offline_research,
)

CLOCK = datetime(2026, 10, 14, 13, 30, tzinfo=timezone.utc)
SOURCE = "a" * 64
METHOD = "TREND_PULLBACK"


def brain(side=ScalpSide.BUY, ready=True):
    regime = MarketRead(
        MarketState.TREND_UP, Playbook.TREND_PULLBACK,
        1, 0.7, "NORMAL", ("causal_closed_bar",))
    proposal = ResearchEntryPlan(
        "XAUUSD", regime.state, regime.playbook, side, ready,
        ("causal_closed_bar",), 0.0)
    return BrainV2Observation(regime, proposal, None)


def exit_plan(side="BUY", stop=1990., target=2030.):
    return StructuralExitPlan(
        side, True, stop, target, 10., 3., "closed_swing", "structure",
        ())


def mock_report(status="RESEARCH_CANDIDATE_REVIEW_REQUIRED", method=METHOD,
                gaps=0, side="BUY", duplicate=False):
    cohort = {
        "symbol": "XAUUSD", "method": method, "side": side,
        "regime": "TREND_UP", "status": status,
        "gapped": gaps, "completed": 100,
    }
    question = {
        "symbol": "XAUUSD", "method": method, "side": side,
        "regime": "TREND_UP", "status": status,
        "broker_costs_verified": False,
        "scientific_experiment": "PRECOMMIT_NEW_UNSEEN_QUOTE_SAMPLE",
    }
    return {
        "ledger_status": "READ_ONLY_PREVIEW",
        "observation_sha256": "b" * 64,
        "matured_observations": 100,
        "semantic_memory": [cohort, dict(cohort)] if duplicate else [cohort],
        "curiosity_hypotheses": [question],
        "real_execution_authorized": False,
        "production_mutation_authorized": False,
        "orders_submitted": 0,
    }


class UnifiedAdaptiveResearchCycleTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        ProspectiveShadowBook(self.db)
        self.args = dict(
            brain=brain(), exit_plan=exit_plan(), symbol="XAUUSD",
            expected_entry=2000., research_method=METHOD,
            as_of_utc=CLOCK, source_digest=SOURCE, hand_id="research-hand-1",
        )

    def tearDown(self):
        self.db.close()

    def synthesize(self, **overrides):
        return synthesize_offline_research(
            self.db, **dict(self.args, **overrides))

    def test_real_empty_shadow_cannot_be_promoted_as_alpha(self):
        before = self.db.execute(
            "SELECT COUNT(*) FROM prospective_shadow").fetchone()[0]
        r = self.synthesize()
        self.assertEqual(r.action, "WAIT")
        self.assertIn("NO_CAUSALLY_MATCHED_SHADOW_COHORT",
                      r.quarantine_reasons)
        self.assertIn("REAL_BROKER_FORWARD_EVIDENCE_MISSING",
                      r.quarantine_reasons)
        self.assertEqual(r.matured_observations, 0)
        self.assertFalse(r.live_execution_authorized)
        self.assertFalse(r.may_promote_strategy)
        self.assertEqual(r.orders_submitted, 0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM prospective_shadow").fetchone()[0], before)
        self.assertIsNone(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name='katarina_cognitive_ledger'"
        ).fetchone())

    def test_matching_favorable_virtual_cohort_only_allows_research_review(self):
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle",
                   return_value=mock_report()) as read:
            r = self.synthesize()
        read.assert_called_once_with(self.db, as_of_utc=CLOCK, persist=False)
        self.assertEqual(r.action, "VIRTUAL_EXPERIMENT_REVIEW_ONLY")
        self.assertEqual(r.cohort_status, "RESEARCH_CANDIDATE_REVIEW_REQUIRED")
        self.assertEqual(r.curiosity_experiment,
                         "PRECOMMIT_NEW_UNSEEN_QUOTE_SAMPLE")
        self.assertFalse(r.live_execution_authorized)
        self.assertFalse(r.may_promote_strategy)
        self.assertEqual(r.orders_submitted, 0)
        self.assertEqual(len(r.receipt_sha256), 64)
        self.assertEqual(r.owner_view()["learning_scope"],
                         "PROSPECTIVE_VIRTUAL_QUOTES_ONLY")

    def test_conservative_learning_rejects_insufficient_negative_and_gap(self):
        for status, gaps in (
            ("INSUFFICIENT_EVIDENCE", 0),
            ("HOLDOUT_INSUFFICIENT", 0),
            ("UNSTABLE_OR_NEGATIVE_QUOTE_EDGE", 0),
            ("RESEARCH_CANDIDATE_REVIEW_REQUIRED", 2),
        ):
            with self.subTest(status=status, gaps=gaps):
                with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                           "run_unified_cognitive_cycle",
                           return_value=mock_report(status=status, gaps=gaps)):
                    r = self.synthesize()
                self.assertEqual(r.action, "WAIT")
                self.assertFalse(r.live_execution_authorized)
                if gaps:
                    self.assertIn("INCOMPLETE_QUOTE_PATHS",
                                  r.quarantine_reasons)
                else:
                    self.assertIn("SHADOW_ALPHA_NOT_VALIDATED",
                                  r.quarantine_reasons)

    def test_buy_sell_and_methods_never_cross_learn(self):
        for data, overrides in (
            (mock_report(method="SWEEP"), {}),
            (mock_report(side="SELL"), {}),
            (mock_report(), {"research_method": "SWEEP"}),
            (mock_report(), {"brain": brain(ScalpSide.SELL),
                             "exit_plan": exit_plan("SELL", 2010., 1970.)}),
        ):
            with self.subTest(overrides=overrides):
                with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                           "run_unified_cognitive_cycle", return_value=data):
                    r = self.synthesize(**overrides)
                self.assertEqual(r.action, "WAIT")
                self.assertIn("NO_CAUSALLY_MATCHED_SHADOW_COHORT",
                              r.quarantine_reasons)

    def test_adaptive_entry_and_exit_geometry_still_gate_research(self):
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle", return_value=mock_report()):
            for updates in (
                {"brain": brain(ready=False)},
                {"exit_plan": None},
                {"exit_plan": exit_plan("BUY", 2010., 2030.)},
            ):
                with self.subTest(updates=updates):
                    r = self.synthesize(**updates)
                    self.assertEqual(r.action, "WAIT")
                    self.assertIn("ADAPTIVE_ENTRY_OR_EXIT_NOT_RESEARCH_READY",
                                  r.quarantine_reasons)

    def test_same_evidence_is_deterministic_and_causal_sources_are_bound(self):
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle", return_value=mock_report()):
            a, b = self.synthesize(), self.synthesize()
            c = self.synthesize(source_digest="f" * 64)
        self.assertEqual(a, b)
        self.assertNotEqual(a.receipt_sha256, c.receipt_sha256)
        self.assertEqual(a.cognitive_source_sha256, "b" * 64)

    def test_rejects_unverified_brain_execution_and_bad_input(self):
        for updates in (
            {"brain": replace(brain(), live_risk_authorized=True)},
            {"exit_plan": replace(exit_plan(), live_execution_authorized=True)},
            {"research_method": ""},
            {"as_of_utc": datetime(2026, 10, 14)},
            {"expected_entry": float("nan")},
        ):
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError):
                    self.synthesize(**updates)

    def test_rejects_forged_cognitive_live_flags(self):
        for change in (
            {"ledger_status": "EXECUTION_READY"},
            {"real_execution_authorized": True},
            {"production_mutation_authorized": True},
            {"orders_submitted": 1},
            {"observation_sha256": "bad"},
        ):
            with self.subTest(change=change):
                data = dict(mock_report(), **change)
                with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                           "run_unified_cognitive_cycle", return_value=data):
                    with self.assertRaisesRegex(ValueError,
                                                "cognitive_research_proof_invalid"):
                        self.synthesize()

    def test_conflicting_duplicate_semantic_cohorts_are_not_consensus(self):
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle",
                   return_value=mock_report(duplicate=True)):
            with self.assertRaisesRegex(ValueError,
                                        "ambiguous_duplicate_research_cohort"):
                self.synthesize()

    def test_mismatched_metacognitive_status_is_not_evidence(self):
        source = mock_report()
        source["curiosity_hypotheses"][0]["status"] = "INSUFFICIENT_EVIDENCE"
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle", return_value=source):
            with self.assertRaisesRegex(ValueError,
                                        "cognitive_research_status_contradiction"):
                self.synthesize()

    def test_matching_saved_checkpoint_can_be_reviewed_but_never_executed(self):
        saved = run_unified_cognitive_cycle(
            self.db, as_of_utc=CLOCK-timedelta(minutes=10))
        summary = verify_cognitive_history(self.db)
        self.assertEqual(summary["active_observation_sha256"],
                         saved["observation_sha256"])
        self.assertEqual(summary["last_event_kind"], "LEARN")
        snapshot = {**mock_report(),
                    "observation_sha256":saved["observation_sha256"]}
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle", return_value=snapshot):
            item=self.synthesize()
        self.assertEqual(item.action, "VIRTUAL_EXPERIMENT_REVIEW_ONLY")
        self.assertEqual(item.cognitive_active_checkpoint_sha256,
                         saved["active_checkpoint_sha256"])
        self.assertEqual(item.cognitive_chain_head_sha256,
                         summary["chain_head_sha256"])
        self.assertFalse(item.live_execution_authorized)

    def test_stale_saved_learning_checkpoint_blocks_positive_virtual_review(self):
        saved = run_unified_cognitive_cycle(
            self.db, as_of_utc=CLOCK-timedelta(minutes=10))
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle", return_value=mock_report()):
            item=self.synthesize()
        self.assertEqual(item.action, "WAIT")
        self.assertIn("ACTIVE_COGNITIVE_CHECKPOINT_NOT_CURRENT_SNAPSHOT",
                      item.quarantine_reasons)
        self.assertEqual(item.cognitive_active_checkpoint_sha256,
                         saved["active_checkpoint_sha256"])

    def test_real_owner_rollback_can_never_be_bypassed_by_shadow_preview(self):
        first = run_unified_cognitive_cycle(
            self.db, as_of_utc=CLOCK-timedelta(minutes=20))
        observed = (CLOCK-timedelta(minutes=15)).timestamp()
        exited = observed+60
        self.db.execute("""INSERT INTO prospective_shadow(
            symbol,bar_close,observed_at,tick_at,method,regime,side,
            bid,ask,entry,stop,target,risk,rr,evidence_score,
            official_news_verified,blockers,state,last_quote_epoch,
            exit_at,exit_price,reason,virtual_net_r
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            "XAUUSD",datetime.fromtimestamp(observed-300,timezone.utc).isoformat(),
            observed,observed,"TREND_PULLBACK","TREND_UP","BUY",
            100.,100.1,100.1,99.,103.,1.1,2.,.85,
            0,'["news_unverified"]',"VIRTUAL_QUOTED",exited,
            exited,101.,"VIRTUAL_QUOTE_ONLY",.3,
        ))
        self.db.commit()
        second = run_unified_cognitive_cycle(
            self.db, as_of_utc=CLOCK-timedelta(minutes=5))
        self.assertNotEqual(first["observation_sha256"],
                            second["observation_sha256"])
        rollback_cognitive_research(
            self.db, to_receipt_sha256=first["active_checkpoint_sha256"],
            as_of_utc=CLOCK, owner_approved=True)
        audit = verify_cognitive_history(self.db)
        self.assertEqual(audit["last_event_kind"], "ROLLBACK")
        self.assertEqual(audit["active_observation_sha256"],
                         first["observation_sha256"])
        snapshot = {**mock_report(),
                    "observation_sha256":second["observation_sha256"]}
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle", return_value=snapshot):
            item=self.synthesize(as_of_utc=CLOCK+timedelta(minutes=1))
        self.assertEqual(item.action, "WAIT")
        self.assertIn("OWNER_RESEARCH_ROLLBACK_HOLD", item.quarantine_reasons)
        self.assertIn("ACTIVE_COGNITIVE_CHECKPOINT_NOT_CURRENT_SNAPSHOT",
                      item.quarantine_reasons)
        self.assertEqual(item.cognitive_active_checkpoint_sha256,
                         first["active_checkpoint_sha256"])
        self.assertEqual(item.cognitive_chain_head_sha256,
                         audit["chain_head_sha256"])
        self.assertFalse(item.may_promote_strategy)

    def test_future_history_event_blocks_stale_asof_review(self):
        run_unified_cognitive_cycle(
            self.db, as_of_utc=CLOCK+timedelta(minutes=10))
        data = mock_report()
        data["observation_sha256"] = verify_cognitive_history(
            self.db)["active_observation_sha256"]
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle", return_value=data):
            item=self.synthesize()
        self.assertEqual(item.action, "WAIT")
        self.assertIn("COGNITIVE_HISTORY_NEWER_THAN_RESEARCH_CLOCK",
                      item.quarantine_reasons)

    def test_tampered_ledger_prevents_even_readonly_synthesis(self):
        run_unified_cognitive_cycle(
            self.db, as_of_utc=CLOCK-timedelta(minutes=10))
        with self.db:
            self.db.execute(
                "UPDATE katarina_cognitive_ledger "
                "SET payload_json='{}' WHERE seq=1")
        with patch("katarina.intelligence.cognition.unified_adaptive_research_cycle."
                   "run_unified_cognitive_cycle", return_value=mock_report()):
            with self.assertRaisesRegex(ValueError,
                                        "cognitive_ledger_chain_tampered"):
                self.synthesize()



if __name__ == "__main__":
    unittest.main()
