import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from katarina.engines.account_risk_state import AccountRiskCoordinator, AccountRiskStateEngine
from katarina.engines.manual_risk import SharedAccountRiskEngine
from katarina.research.experimental_strategy_evidence_portfolio import MultiSymbolCandidate, MultiSymbolExecutionOrchestrator
from katarina.engines.opportunity import RankedOpportunity
from katarina.engines.risk import RiskGovernor
from katarina.engines.scalper_entry import EntryMode, EntryProposal, EntrySide
from katarina.intelligence.shadow.strategy_drift import StrategyDriftDecision
from katarina.intelligence.shadow.strategy_evidence import (
    ClosedStrategyTrade, ForwardStrategyEvidenceGate, StrategyEvidenceDecision,
)


def make_candidate(symbol, iid, score=.95):
    return MultiSymbolCandidate(
        opportunity=RankedOpportunity(
            symbol=symbol, instrument_id=iid, spec_revision=1,
            score=score, asset_class="METAL",
            proposal=EntryProposal(
                True, EntrySide.BUY, EntryMode.TREND_PULLBACK,
                score, .05, 2., 1., 3, ("closed_bar",)
            ),
            reasons=("test",),
        ),
        requested_risk_fraction=.05, base_volume=.1,
        volume_min=.01, volume_step=.01, stop_loss=1.,
        take_profit=2., decision_id=f"decision-{iid}",
        risk_id=f"risk-{iid}", strategy_id="GOLD_OR",
    )


def verified_paper_evidence():
    gate=ForwardStrategyEvidenceGate(bootstrap_draws=300)
    first=datetime(2026,6,1,tzinfo=timezone.utc)
    events=[ClosedStrategyTrade(
        trade_id=f"p-{i}", symbol="XAUUSD", strategy_id="GOLD_OR",
        closed_at_utc=first+timedelta(days=2*i),
        net_r=1.1 if i%4!=3 else -.35,
        provenance="PAPER", costs_verified=True)
        for i in range(60)]
    result=gate.assess(
        symbol="XAUUSD",strategy_id="GOLD_OR",
        frozen_at_utc=datetime(2026,5,31,tzinfo=timezone.utc),
        as_of_utc=datetime(2026,10,11,tzinfo=timezone.utc),trades=events)
    assert result.eligible_for_risk_review
    return result


class StrategyAndExposureRoutingTests(unittest.TestCase):
    def setUp(self):
        self.state=AccountRiskStateEngine(max_open_risk=.08)
        self.risk=AccountRiskCoordinator(self.state,RiskGovernor())
        self.positions=SharedAccountRiskEngine().assess([],equity=10000)

    def test_strict_mode_rejects_uncertified_historical_alpha(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,require_strategy_evidence=True)
        plan=router.build_plan(
            [make_candidate("XAUUSD",1)],positions=self.positions,
            day_key="2026-10-11",returns={"XAUUSD":[1,0,-1]})
        self.assertEqual(len(plan.accepted),0)
        self.assertEqual(plan.rejected[0].reason,"strategy_forward_evidence_missing")
        self.assertEqual(self.state.reservations.total_fraction,0)

    def test_verified_paper_alpha_only_reduces_the_requested_risk(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,require_strategy_evidence=True)
        decision=verified_paper_evidence()
        plan=router.build_plan(
            [make_candidate("XAUUSD",1)],positions=self.positions,
            day_key="2026-10-11",returns={"XAUUSD":[1,0,-1]},
            evidence_decisions={("XAUUSD","GOLD_OR"):decision})
        self.assertEqual(len(plan.accepted),1)
        self.assertLess(plan.accepted[0].approved_risk_fraction,.05)
        self.assertLess(plan.accepted[0].intent.volume,.1)
        self.assertAlmostEqual(plan.total_reserved_fraction,
                               self.state.reservations.total_fraction)
        self.assertFalse(decision.live_authorized)

    def test_exclusive_gold_group_prevents_two_correlated_gold_trades(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,
            exclusive_exposure_groups={"XAUUSD":"GOLD","XAUEUR":"GOLD"})
        plan=router.build_plan(
            [make_candidate("XAUUSD",1,.95),make_candidate("XAUEUR",2,.90)],
            positions=self.positions,day_key="2026-10-11",
            returns={"XAUUSD":[1,0,-1],"XAUEUR":[1,0,-1]},
            existing_symbol_risks={})
        self.assertEqual([x.symbol for x in plan.accepted],["XAUUSD"])
        self.assertEqual(plan.rejected[0].reason,"exclusive_exposure_group_busy")
        self.assertAlmostEqual(self.state.reservations.total_fraction,.05)

    def test_missing_reconciled_group_risk_blocks_even_first_trade(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,
            exclusive_exposure_groups={"XAUUSD":"GOLD","XAUEUR":"GOLD"})
        plan=router.build_plan(
            [make_candidate("XAUUSD",1)],positions=self.positions,
            day_key="2026-10-11",returns={})
        self.assertEqual(len(plan.accepted),0)
        self.assertEqual(plan.rejected[0].reason,"exclusive_group_positions_unverified")
        self.assertEqual(self.state.reservations.total_fraction,0)

    def test_existing_gold_exposure_prevents_new_gold_trade(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,
            exclusive_exposure_groups={"XAUUSD":"GOLD","XAUEUR":"GOLD"})
        plan=router.build_plan(
            [make_candidate("XAUEUR",2)],positions=self.positions,
            day_key="2026-10-11",returns={},
            existing_symbol_risks={"XAUUSD":.01})
        self.assertEqual(len(plan.accepted),0)
        self.assertEqual(plan.rejected[0].reason,"exclusive_exposure_group_busy")
        self.assertEqual(self.state.reservations.total_fraction,0)

    def test_quality_multiplier_changes_both_risk_budget_and_physical_lots(self):
        router=MultiSymbolExecutionOrchestrator(risk=self.risk)
        proposal=replace(make_candidate("XAUUSD",1),quality_risk_multiplier=.5)
        plan=router.build_plan(
            [proposal],positions=self.positions,day_key="2026-10-11",
            returns={"XAUUSD":[1,0,-1]},
        )
        self.assertEqual(len(plan.accepted),1)
        self.assertAlmostEqual(plan.accepted[0].approved_risk_fraction,.025)
        self.assertAlmostEqual(plan.accepted[0].intent.volume,.05)
        self.assertAlmostEqual(self.state.reservations.total_fraction,.025)

    def test_bogus_quality_evidence_multiplier_is_rejected(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,require_strategy_evidence=True)
        forged=StrategyEvidenceDecision(
            True,"unverified_approval",float("nan"),60,.2,.1,1.3,5.)
        plan=router.build_plan(
            [make_candidate("XAUUSD",1)],positions=self.positions,
            day_key="2026-10-11",returns={},
            evidence_decisions={("XAUUSD","GOLD_OR"):forged})
        self.assertEqual(len(plan.accepted),0)
        self.assertEqual(plan.rejected[0].reason,"strategy_forward_evidence_missing")
        self.assertEqual(self.state.reservations.total_fraction,0)

    def test_drift_no_trade_prevents_reservation_even_when_forward_was_good(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,require_strategy_evidence=True,
            require_drift_clearance=True)
        forward=verified_paper_evidence()
        stopped=StrategyDriftDecision("NO_TRADE","recent_loss_streak",0.,60)
        plan=router.build_plan(
            [make_candidate("XAUUSD",1)],positions=self.positions,
            day_key="2026-10-11",returns={"XAUUSD":[1,0,-1]},
            evidence_decisions={("XAUUSD","GOLD_OR"):forward},
            drift_decisions={("XAUUSD","GOLD_OR"):stopped})
        self.assertEqual(len(plan.accepted),0)
        self.assertEqual(plan.rejected[0].reason,"strategy_drift_no_trade")
        self.assertAlmostEqual(self.state.reservations.total_fraction,0)

    def test_drift_clearance_cannot_increase_lots_or_override_risk(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,require_strategy_evidence=True,
            require_drift_clearance=True)
        forward=verified_paper_evidence()
        drift=StrategyDriftDecision(
            "RISK_REVIEW_ONLY","forward_edge_and_recent_costs_within_limits",
            .20,60)
        plan=router.build_plan(
            [make_candidate("XAUUSD",1)],positions=self.positions,
            day_key="2026-10-11",returns={"XAUUSD":[1,0,-1]},
            evidence_decisions={("XAUUSD","GOLD_OR"):forward},
            drift_decisions={("XAUUSD","GOLD_OR"):drift})
        self.assertEqual(len(plan.accepted),1)
        self.assertAlmostEqual(plan.accepted[0].approved_risk_fraction,.01)
        self.assertAlmostEqual(plan.accepted[0].intent.volume,.02)
        self.assertFalse(drift.live_execution_authorized)

    def test_missing_drift_attestation_is_no_trade(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,require_drift_clearance=True)
        plan=router.build_plan(
            [make_candidate("XAUUSD",1)],positions=self.positions,
            day_key="2026-10-11",returns={"XAUUSD":[1,0,-1]})
        self.assertEqual(len(plan.accepted),0)
        self.assertEqual(plan.rejected[0].reason,"strategy_drift_no_trade")

    def test_failed_forward_evidence_cannot_be_forgiven_by_higher_score(self):
        router=MultiSymbolExecutionOrchestrator(
            risk=self.risk,require_strategy_evidence=True)
        denied=StrategyEvidenceDecision(
            False,"forward_confidence_interval_includes_zero",
            0.,60,.2,-.1,1.3,5.)
        plan=router.build_plan(
            [make_candidate("XAUUSD",1,1.0)],positions=self.positions,
            day_key="2026-10-11",returns={},
            evidence_decisions={("XAUUSD","GOLD_OR"):denied})
        self.assertEqual(len(plan.accepted),0)
        self.assertEqual(plan.rejected[0].reason,"strategy_forward_evidence_missing")


if __name__ == "__main__":
    unittest.main()
