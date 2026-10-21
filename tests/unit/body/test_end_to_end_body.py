from __future__ import annotations

import importlib
import unittest

from katarina.body import STAGE_MODULES
from katarina.body.functional import (
    ExecutionIntent,
    MarketFeatureSnapshot,
    RegimeEvidence,
    TesterEvaluationIntent,
    TimeframeObservation,
)


def component(stage: int):
    return importlib.import_module(STAGE_MODULES[stage]).Component()


class EndToEndBodyFailClosedTests(unittest.TestCase):
    def test_market_to_execution_path_remains_fail_closed(self):
        market = component(11)
        market.observe(
            MarketFeatureSnapshot(
                instrument_id=1,
                observed_at_ns=1_000,
                features={
                    "price_units": 3_000_000,
                    "ema_fast_units": 2_999_000,
                    "ema_slow_units": 2_998_000,
                },
            )
        )
        self.assertIsNotNone(market.latest(1))

        mtf = component(12)
        mtf.observe(
            TimeframeObservation(
                instrument_id=1,
                timeframe_seconds=60,
                open_time_ns=0,
                values={"close_units": 3_000_000},
            )
        )
        self.assertIsNotNone(mtf.latest(1, 60))

        regime = component(13)
        label = regime.observe(
            RegimeEvidence(
                instrument_id=1,
                observed_at_ns=1_000,
                trend_score_ppm=500_000,
                volatility_score_ppm=100_000,
                liquidity_score_ppm=500_000,
            )
        )
        self.assertEqual(label, "UNCLASSIFIED_POLICY_PENDING")

        specialist = component(14).analyze({"instrument_id": 1})
        self.assertEqual(specialist["signal"], "NO_SIGNAL")
        self.assertFalse(specialist["live_execution_authority"])

        decision = component(15).decide(specialist)
        self.assertEqual(decision["decision"], "NO_TRADE")
        self.assertFalse(decision["live_execution_authority"])

        risk = component(16).authorize(decision)
        self.assertFalse(risk["approved"])
        self.assertFalse(risk["live_risk_ready"])

        sizing = component(17).size(risk)
        self.assertFalse(sizing["approved"])
        self.assertEqual(sizing["quantity_units"], 0)

        execution = component(18)
        staged = execution.stage_intent(
            ExecutionIntent(
                intent_id="audit-intent",
                instrument_id=1,
                side="BUY",
                quantity_units=1,
            )
        )
        self.assertFalse(staged["accepted_for_live_execution"])

        tester_evidence = component(25).record(
            TesterEvaluationIntent("tester-audit", staged)
        )
        self.assertTrue(tester_evidence["tester_only"])
        self.assertFalse(tester_evidence["broker_mutation"])

        micro = component(38).validate(
            {"tester_evidence": tester_evidence}
        )
        self.assertFalse(micro["approved"])
        self.assertFalse(micro["live_risk_ready"])
        self.assertFalse(micro["live_execution_authority"])

    def test_policy_pending_process_calls_are_blocked(self):
        for stage in (14, 15, 16, 17, 38):
            with self.subTest(stage=stage):
                result = component(stage).process({"audit": True})
                self.assertFalse(result.accepted)
                self.assertFalse(result.live_risk_ready)
                self.assertFalse(result.live_execution_authority)

    def test_execution_path_process_calls_are_blocked(self):
        for stage in (18, 19):
            with self.subTest(stage=stage):
                result = component(stage).process({"audit": True})
                self.assertFalse(result.accepted)
                self.assertFalse(result.live_execution_authority)

    def test_windows_dependent_stages_never_imply_windows_validation(self):
        for stage in (35, 36, 38):
            with self.subTest(stage=stage):
                c = component(stage)
                self.assertTrue(c.SPEC.windows_required)
                self.assertFalse(c.SPEC.live_risk_ready)
                self.assertFalse(c.SPEC.live_execution_authority)


if __name__ == "__main__":
    unittest.main()
