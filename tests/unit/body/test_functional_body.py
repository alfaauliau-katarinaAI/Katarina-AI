from __future__ import annotations

import importlib
import unittest

from katarina.body import STAGE_MODULES
from katarina.body.functional import (
    BacktestEvent,
    EconomicObservation,
    EvolutionStatus,
    ExecutionIntent,
    LearningObservation,
    MarketFeatureSnapshot,
    ModelArtifact,
    LivePreflightCheck,
    PortfolioAllocation,
    PositionObservation,
    RegimeEvidence,
    TesterEvaluationIntent,
    StressScenario,
    TestGate,
    TimeframeObservation,
    TradeOutcome,
)


def component(stage: int):
    return importlib.import_module(STAGE_MODULES[stage]).Component()


class MarketBrainBodyTests(unittest.TestCase):
    def test_stage11_market_intelligence(self):
        c = component(11)
        snap = MarketFeatureSnapshot(1, 100, {"ema_fast": 2000})
        c.observe(snap)
        self.assertEqual(c.latest(1), snap)

    def test_stage12_multi_timeframe(self):
        c = component(12)
        self.assertEqual(
            c.bucket_open_ns(125_000_000_000, 60),
            120_000_000_000,
        )
        obs = TimeframeObservation(1, 60, 120_000_000_000, {"close": 10})
        c.observe(obs)
        self.assertEqual(c.latest(1, 60), obs)

    def test_stage13_regime_is_unclassified_without_policy(self):
        c = component(13)
        label = c.observe(RegimeEvidence(1, 100, 10, 20, 30))
        self.assertEqual(label, "UNCLASSIFIED_POLICY_PENDING")

    def test_stage14_specialist_has_no_signal_without_strategy(self):
        out = component(14).analyze({"price_units": 100})
        self.assertEqual(out["signal"], "NO_SIGNAL")
        self.assertFalse(out["live_execution_authority"])

    def test_stage15_decision_defaults_to_no_trade(self):
        out = component(15).decide({"candidate": "buy"})
        self.assertEqual(out["decision"], "NO_TRADE")

    def test_stage16_risk_governor_denies_unfinalized_policy(self):
        out = component(16).authorize({"risk": "candidate"})
        self.assertFalse(out["approved"])
        self.assertFalse(out["live_risk_ready"])

    def test_stage17_sizing_is_zero_without_policy(self):
        out = component(17).size({"stop_units": 100})
        self.assertEqual(out["quantity_units"], 0)
        self.assertFalse(out["approved"])


class ExecutionEvaluationBodyTests(unittest.TestCase):
    def test_stage18_execution_stages_but_does_not_execute(self):
        c = component(18)
        out = c.stage_intent(ExecutionIntent("i1", 1, "BUY", 100))
        self.assertFalse(out["accepted_for_live_execution"])

    def test_stage19_position_manager_is_revision_monotonic(self):
        c = component(19)
        c.observe(PositionObservation("p1", 1, "BUY", 10, 1000, 2))
        with self.assertRaises(ValueError):
            c.observe(PositionObservation("p1", 1, "BUY", 10, 1000, 1))
        self.assertEqual(len(c.snapshot()), 1)

    def test_stage20_trade_evaluation(self):
        summary = component(20).summarize(
            (
                TradeOutcome("a", 10),
                TradeOutcome("b", -4),
                TradeOutcome("c", -8),
                TradeOutcome("d", 3),
            )
        )
        self.assertEqual(summary.trade_count, 4)
        self.assertEqual(summary.total_pnl_units, 1)
        self.assertEqual(summary.max_drawdown_units, 12)


class ResearchLearningBodyTests(unittest.TestCase):
    def test_stage21_research_ids_are_deterministic(self):
        c = component(21)
        a = c.register("h", {"b": 2, "a": 1})
        b = c.register("h", {"a": 1, "b": 2})
        self.assertEqual(a.experiment_id, b.experiment_id)

    def test_stage22_backtest_normalizes_event_order(self):
        c = component(22)
        events = (
            BacktestEvent(20, 2, {"v": 2}),
            BacktestEvent(10, 1, {"v": 1}),
        )
        ordered = c.normalize_events(events)
        self.assertEqual([x.time_ns for x in ordered], [10, 20])

    def test_stage22_duplicate_event_identity_rejected(self):
        c = component(22)
        events = (
            BacktestEvent(10, 1, {}),
            BacktestEvent(10, 1, {}),
        )
        with self.assertRaises(ValueError):
            c.normalize_events(events)

    def test_stage23_walk_forward_has_no_train_test_overlap(self):
        windows = component(23).windows(
            100,
            train_samples=40,
            test_samples=10,
            step_samples=10,
        )
        self.assertTrue(windows)
        self.assertTrue(
            all(w.train_end == w.test_start for w in windows)
        )

    def test_stage24_monte_carlo_is_seed_deterministic(self):
        c = component(24)
        a = c.bootstrap((10, -5, 3), trials=50, seed=7)
        b = c.bootstrap((10, -5, 3), trials=50, seed=7)
        self.assertEqual(a, b)

    def test_stage25_tester_evaluation_never_mutates_broker(self):
        c = component(25)
        out = c.record(TesterEvaluationIntent("s1", {"side": "BUY"}))
        self.assertTrue(out["tester_only"])
        self.assertFalse(out["broker_mutation"])

    def test_stage26_learning_is_idempotent_by_observation_id(self):
        c = component(26)
        obs = LearningObservation("o1", {"x": 1}, 10)
        self.assertTrue(c.observe(obs))
        self.assertFalse(c.observe(obs))

    def test_stage27_ml_artifact_registry(self):
        c = component(27)
        artifact = ModelArtifact("m1", "1", "a" * 64, {"score_ppm": 1})
        c.register(artifact)
        self.assertEqual(c.get("m1"), artifact)

    def test_stage28_model_promotion_and_rollback(self):
        c = component(28)
        self.assertTrue(c.promote("m1", validated=True))
        self.assertTrue(c.promote("m2", validated=True))
        self.assertEqual(c.champion, "m2")
        self.assertEqual(c.rollback(), "m1")


class PortfolioOperationsBodyTests(unittest.TestCase):
    def test_stage29_economic_revision_is_monotonic(self):
        c = component(29)
        c.observe(EconomicObservation("CPI", 100, 10, revision=2))
        with self.assertRaises(ValueError):
            c.observe(EconomicObservation("CPI", 90, 9, revision=1))

    def test_stage30_portfolio_allocation_is_bounded(self):
        c = component(30)
        allocation = PortfolioAllocation({"XAUUSD": 600000, "BTCUSD": 400000})
        self.assertEqual(c.validate(allocation), allocation)
        with self.assertRaises(ValueError):
            PortfolioAllocation({"XAUUSD": 800000, "BTCUSD": 300000})

    def test_stage31_global_exposure(self):
        snap = component(31).calculate({"XAUUSD": 100, "BTCUSD": -40})
        self.assertEqual(snap.gross_units, 140)
        self.assertEqual(snap.net_units, 60)

    def test_stage32_dashboard_rejects_duplicate_keys(self):
        c = component(32)
        self.assertEqual(c.compose({"a": 1}, {"b": 2}), {"a": 1, "b": 2})
        with self.assertRaises(ValueError):
            c.compose({"a": 1}, {"a": 2})

    def test_stage33_test_gate(self):
        c = component(33)
        self.assertTrue(c.all_pass((TestGate("unit", True), TestGate("audit", True))))
        self.assertFalse(c.all_pass((TestGate("unit", True), TestGate("audit", False))))

    def test_stage34_constitution_guard_blocks_live_authority(self):
        ok, reasons = component(34).evaluate(
            {"live_execution_authority": True}
        )
        self.assertFalse(ok)
        self.assertIn("LIVE_EXECUTION_AUTHORITY_FORBIDDEN", reasons)


class ValidationEvolutionBodyTests(unittest.TestCase):
    def test_stage35_mt5_tester_job_validation(self):
        from katarina.body.functional import MT5TesterJob

        c = component(35)
        self.assertTrue(
            c.validate_job(
                MT5TesterJob(
                    "Katarina.ex5",
                    "XAUUSD",
                    "M1",
                    "2026.01.01",
                    "2026.02.01",
                )
            )
        )

    def test_stage36_live_preflight_is_read_only(self):
        c = component(36)
        checks = tuple(
            LivePreflightCheck(name, True)
            for name in c.REQUIRED_CHECKS
        )
        out = c.evaluate(checks)
        self.assertTrue(out["passed"])
        self.assertFalse(out["broker_mutation"])
        self.assertFalse(out["live_execution_authority"])
        result = c.process({})
        self.assertTrue(result.accepted)
        self.assertFalse(result.live_execution_authority)

    def test_stage37_stress_matrix(self):
        c = component(37)
        scenarios = (
            StressScenario("disconnect", True),
            StressScenario("stale_data", True),
        )
        self.assertTrue(
            c.evaluate(
                scenarios,
                {"disconnect": True, "stale_data": True},
            )
        )

    def test_stage38_micro_risk_is_locked(self):
        out = component(38).validate({"candidate": True})
        self.assertFalse(out["approved"])
        self.assertFalse(out["live_risk_ready"])

    def test_stage39_performance_monitoring(self):
        c = component(39)
        c.increment("events", 2)
        c.gauge("queue_depth", 3)
        snap = c.snapshot()
        self.assertEqual(snap["counters"]["events"], 2)
        self.assertEqual(snap["gauges"]["queue_depth"], 3)

    def test_stage40_evolution_requires_tests_and_constitution(self):
        c = component(40)
        c.propose("p1", "candidate improvement")
        rejected = c.mark_validated(
            "p1",
            tests_passed=True,
            constitution_passed=False,
        )
        self.assertEqual(rejected.status, EvolutionStatus.REJECTED)
        c.propose("p2", "safe improvement")
        validated = c.mark_validated(
            "p2",
            tests_passed=True,
            constitution_passed=True,
        )
        self.assertEqual(validated.status, EvolutionStatus.VALIDATED)


if __name__ == "__main__":
    unittest.main()
