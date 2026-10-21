"""Fail-closed evidence-dependent risk regression; no live orders."""
import unittest
from dataclasses import replace

from katarina.intelligence.lab.evidence_risk import (
    EvidenceRiskGate, StrategyEvidence, VerifiedRiskState,
    assess_legacy_august_audit,
)


class EvidenceRiskTests(unittest.TestCase):
    def setUp(self):
        self.gate = EvidenceRiskGate()
        self.evidence = StrategyEvidence(
            symbol="XAUUSD.vx", strategy="FROZEN_SWEEP", side="SELL",
            regime="TREND_DOWN",
            historical_trades=400, forward_trades=280,
            forward_net_mean_r=.30, forward_net_profit_factor=1.65,
            cost_stress_mean_r=.2, forward_lower_confidence_r=.06,
            chronological_segment_means=(.12, .25, .17, .34),
            independent_regimes=3,
            strategy_frozen_before_forward=True,
            untouched_forward_held_out=True,
            causal_prices_verified=True,
            broker_commission_spread_slippage_verified=True,
            execution_fills_verified=True,
            independent_audit_verified=True,
        )
        self.state = VerifiedRiskState(
            telemetry_verified=True, day_drawdown=0., peak_drawdown=0.,
            committed_open_risk=0., same_direction_correlated_risk=0.,
            market_health_verified=True, broker_execution_health_verified=True,
        )

    def test_without_data_never_authorizes(self):
        for e, s in ((None, self.state), (self.evidence, None),
                     (self.evidence, VerifiedRiskState())):
            with self.subTest(e=e, s=s):
                decision = self.gate.assess(e, s)
                self.assertEqual(decision.level, "WAIT")
                self.assertEqual(decision.research_risk_cap_fraction, 0.)
                self.assertEqual(decision.live_authorized_fraction, 0.)

    def test_aggressive_verified_only_and_still_not_live(self):
        d = self.gate.assess(self.evidence, self.state)
        self.assertEqual(d.level, "AGGRESSIVE")
        self.assertAlmostEqual(d.research_risk_cap_fraction, .01)
        self.assertFalse(d.live_execution_authorized)
        self.assertEqual(d.live_authorized_fraction, 0)

    def test_conservative_and_moderate_tiers(self):
        conservative = replace(self.evidence, forward_trades=45,
                               forward_net_profit_factor=1.22,
                               cost_stress_mean_r=.03, independent_regimes=1)
        a = self.gate.assess(conservative, self.state)
        self.assertEqual(a.level, "CONSERVATIVE")
        self.assertAlmostEqual(a.research_risk_cap_fraction, .0025)
        moderate = replace(self.evidence, forward_trades=125,
                           forward_net_profit_factor=1.32,
                           cost_stress_mean_r=.09, independent_regimes=2)
        b = self.gate.assess(moderate, self.state)
        self.assertEqual(b.level, "MODERATE")
        self.assertAlmostEqual(b.research_risk_cap_fraction, .005)

    def test_short_history_still_wait_not_micro_lot(self):
        e = replace(self.evidence, historical_trades=20, forward_trades=20)
        self.assertEqual(self.gate.assess(e, self.state).level, "WAIT")

    def test_each_evidence_proof_is_mandatory(self):
        flags = ("strategy_frozen_before_forward",
                 "untouched_forward_held_out",
                 "causal_prices_verified",
                 "broker_commission_spread_slippage_verified",
                 "execution_fills_verified",
                 "independent_audit_verified")
        for flag in flags:
            with self.subTest(flag=flag):
                e = replace(self.evidence, **{flag: False})
                self.assertEqual(self.gate.assess(e, self.state).level, "WAIT")

    def test_require_positive_lower_bound_and_cost_stress(self):
        for edits in ({"forward_lower_confidence_r": -0.001},
                      {"cost_stress_mean_r": 0.},
                      {"forward_net_mean_r": -.1},
                      {"forward_net_profit_factor": 1.19},
                      {"chronological_segment_means": (.2, -.1, .3)},
                      {"forward_net_mean_r": float("nan")},
                      {"forward_lower_confidence_r": None}):
            with self.subTest(edits=edits):
                self.assertEqual(self.gate.assess(replace(self.evidence, **edits),
                                                  self.state).level, "WAIT")

    def test_drawdown_stop_and_reduction(self):
        for fields, reason in (({"day_drawdown": .35}, "daily_drawdown_stop"),
                               ({"peak_drawdown": .10}, "peak_drawdown_stop")):
            d = self.gate.assess(self.evidence, replace(self.state, **fields))
            self.assertEqual(d.level, "WAIT")
            self.assertIn(reason, d.reasons)
        d = self.gate.assess(self.evidence,
                             replace(self.state, peak_drawdown=.055))
        self.assertEqual(d.level, "AGGRESSIVE")
        self.assertAlmostEqual(d.research_risk_cap_fraction, .005)

    def test_portfolio_and_correlation_caps(self):
        d = self.gate.assess(self.evidence,
            replace(self.state, committed_open_risk=.018,
                    same_direction_correlated_risk=.0145))
        self.assertAlmostEqual(d.research_risk_cap_fraction, .0005)
        for state in (replace(self.state, committed_open_risk=.02),
                      replace(self.state, same_direction_correlated_risk=.015)):
            self.assertEqual(self.gate.assess(self.evidence, state).level, "WAIT")

    def test_corrupted_risk_telemetry_wait(self):
        for value in (None, -0.01, float("nan"), float("inf")):
            d = self.gate.assess(self.evidence,
                replace(self.state, same_direction_correlated_risk=value))
            self.assertEqual(d.level, "WAIT")

    def test_health_failure_wait(self):
        for updates in ({"market_health_verified": False},
                        {"broker_execution_health_verified": False}):
            self.assertEqual(self.gate.assess(
                self.evidence, replace(self.state, **updates)).level, "WAIT")

    def test_historical_august_never_upgraded(self):
        x = {"action": "WAIT", "tick_quote_complete": 157,
             "tick_quote_mean_assumed_r": -.315584,
             "tick_quote_profit_factor_assumed": .593206}
        d = assess_legacy_august_audit(x)
        self.assertEqual(d.level, "WAIT")
        self.assertEqual(d.research_risk_cap_fraction, 0.)
        self.assertEqual(d.live_authorized_fraction, 0.)
        self.assertEqual(assess_legacy_august_audit({}).level, "WAIT")

if __name__ == "__main__":
    unittest.main()