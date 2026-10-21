"""Cross-gate integration: statistical evidence plus broker cost/margin limits."""
import unittest
from dataclasses import replace
from pathlib import Path

from katarina.engines.broker_aware_sizing import (
    AccountFacts, BrokerFacts, TradingCosts, EvidenceQualifiedResearchSizing,
)
from katarina.engines.risk import RiskGovernor
from katarina.intelligence.lab.evidence_risk import StrategyEvidence, VerifiedRiskState


CONFIG = Path(__file__).resolve().parents[3] / "config" / "risk_governor_v2.json"


class EvidenceQualifiedSizingTests(unittest.TestCase):
    def setUp(self):
        self.gate = EvidenceQualifiedResearchSizing(RiskGovernor.from_config(CONFIG))
        self.account = AccountFacts(
            "USD", 10000, 10000, 10000, 6000,
            uncertainty=.1, expected_rr=2.0, verified=True)
        self.broker = BrokerFacts("USD", 1, 100, .01, 50, .01, 1000, verified=True)
        self.costs = TradingCosts(.02, .03, .5, verified=True)
        self.evidence = StrategyEvidence(
            symbol="XAUUSD.vx", strategy="FROZEN", side="BUY", regime="TREND_UP",
            historical_trades=350, forward_trades=300,
            forward_net_mean_r=.35, forward_net_profit_factor=1.7,
            cost_stress_mean_r=.19, forward_lower_confidence_r=.08,
            chronological_segment_means=(.1,.2,.3,.4),
            independent_regimes=3, strategy_frozen_before_forward=True,
            untouched_forward_held_out=True, causal_prices_verified=True,
            broker_commission_spread_slippage_verified=True,
            execution_fills_verified=True, independent_audit_verified=True)
        self.state = VerifiedRiskState(
            telemetry_verified=True, day_drawdown=0, peak_drawdown=0,
            committed_open_risk=0, same_direction_correlated_risk=0,
            market_health_verified=True, broker_execution_health_verified=True)

    def qualify(self, **overrides):
        args=dict(evidence=self.evidence, risk_state=self.state,
                  account=self.account, broker=self.broker, costs=self.costs,
                  side="BUY", entry=4200, stop=4190)
        args.update(overrides)
        return self.gate.qualify(**args)

    def test_missing_proof_refuses_even_paper_volume(self):
        for changes in ({"evidence":None},
                        {"risk_state":None},
                        {"evidence":replace(self.evidence,execution_fills_verified=False)},
                        {"evidence":replace(self.evidence,forward_net_mean_r=-.1)}):
            with self.subTest(changes=changes):
                q=self.qualify(**changes)
                self.assertFalse(q.eligible_for_research)
                self.assertEqual(q.volume,0)
                self.assertFalse(q.live_execution_authorized)

    def test_aggressive_budget_is_min_of_two_governors(self):
        q=self.qualify()
        self.assertTrue(q.eligible_for_research)
        self.assertAlmostEqual(q.fraction,.0075)
        self.assertLessEqual(q.buffered_loss_native,q.budget_native)
        self.assertFalse(q.live_execution_authorized)

    def test_tier_reduction_reduces_position(self):
        strong=self.qualify()
        limited=replace(self.evidence,forward_trades=45,
                        forward_net_profit_factor=1.21,
                        cost_stress_mean_r=.03,independent_regimes=1)
        weak=self.qualify(evidence=limited)
        self.assertTrue(weak.eligible_for_research)
        self.assertAlmostEqual(weak.fraction,.0025)
        self.assertLess(weak.volume,strong.volume)

    def test_account_risk_mismatch_refuses(self):
        q=self.qualify(account=replace(self.account,committed_risk_fraction=.01))
        self.assertEqual(q.reason,"account_evidence_snapshot_mismatch")
        q=self.qualify(risk_state=replace(self.state,day_drawdown=.05))
        self.assertFalse(q.eligible_for_research)

    def test_broker_cost_and_margin_still_enforced(self):
        self.assertFalse(self.qualify(broker=replace(self.broker,verified=False)).eligible_for_research)
        self.assertFalse(self.qualify(costs=replace(self.costs,verified=False)).eligible_for_research)
        self.assertFalse(self.qualify(account=replace(self.account,available_margin=5)).eligible_for_research)
        self.assertFalse(self.qualify(side="SELL").eligible_for_research)

    def test_daily_stop_blocks_all(self):
        state=replace(self.state,day_drawdown=.35)
        account=replace(self.account,daily_drawdown=.35)
        self.assertEqual(self.qualify(risk_state=state,account=account).volume,0)

if __name__=="__main__":
    unittest.main()
