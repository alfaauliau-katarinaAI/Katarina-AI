"""Native contextual market reasoning: fail-closed, resolved-experience only."""
import unittest
from dataclasses import replace
from datetime import timedelta

from katarina.intelligence.cognition.market_decision import (
    MarketDecisionBrain, DecisionCard,
)
from katarina.intelligence.news.news_intelligence import NewsContext
from katarina.intelligence.cognition.contextual_decision_intelligence import (
    ContextualDecisionIntelligence, MacroEvidence, ResolvedExperience, RiskSituation,
)
from tests.unit.intelligence.test_market_decision_pipeline import NOW,market


SYMBOL="XAUUSD.vx"
STRATEGY="TREND_PULLBACK"
RISK=RiskSituation(system_healthy=True,broker_session_open=True,quote_fresh=True,
                   drawdown_fraction=0.,realized_daily_loss_r=0,
                   open_positions=0,gross_exposure_fraction=0)
NEWS=NewsContext(True,False,.2,.1,2,2,("news_context_ready",))


def card(side="BUY",state="TREND_UP"):
    return DecisionCard(
        symbol=SYMBOL, analyzed_at_utc=NOW.isoformat(), market_phase="TREND",
        directional_bias="BULLISH" if side=="BUY" else "BEARISH",
        market_state=state,evidence_score=.79,evidence_not_probability=True,
        market_explanation="Verified closed-candle uptrend.",
        primary_scenario="Conditional continuation.",alternative_scenario="Break invalidates.",
        primary_target=4300 if side=="BUY" else 4150,
        invalidation_level=4180 if side=="BUY" else 4250,
        target_kind="prior_H1_boundary",
        strategy=STRATEGY,technical_signal=side,decision="WAIT",
        strategy_validated=False,rr_after_spread_estimate=1.9,
        evidence=("M15_M5_alignment",),blockers=("pair_strategy_edge_not_validated",),
        next_trigger="wait for closed bar")


def macro(side="BUY",ago=30,source="fed", verified=True):
    return MacroEvidence(
        source_id=source,
        published_at_utc=NOW-timedelta(minutes=ago),
        observed_at_utc=NOW-timedelta(minutes=max(0,ago-3)),
        affected_symbol=SYMBOL,
        favored_side=side,
        policy_direction="Policy statement retains tightening bias.",
        transmission_mechanism="Real rate and USD repricing channel.",
        source_verified=verified,
    )


def histories(n=60,*, verified=True, costed=True, forward=True,
              side="BUY", result=1.0, last_negative=False):
    rows=[]
    for i in range(n):
        # Three separate calendar months; all outcomes known BEFORE NOW.
        mon=(7,8,9)[i%3]
        d=NOW.replace(month=mon,day=2+(i//3)%26,hour=6)
        r=(-.4 if i%4==0 else result)
        if last_negative and i>=n-20:r=-1.0
        rows.append(ResolvedExperience(
            symbol=SYMBOL,strategy=STRATEGY,side=side,regime="TREND_UP",
            signal_at_utc=d,resolved_at_utc=d+timedelta(hours=2),
            net_r=r,bid_ask_replay_verified=verified,cost_reconciled=costed,
            independently_forward_observed=forward))
    return rows


class TestContextualDecisionIntelligence(unittest.TestCase):
    def setUp(self):
        self.brain=ContextualDecisionIntelligence()
        self.args=dict(card=card(),as_of_utc=NOW,news=NEWS,macro=[macro()],
                       experience=histories(),risk=RISK,observed_spread=.15,
                       m15_atr=1.6)

    def assess(self,**updates):
        return self.brain.evaluate(**{**self.args,**updates})

    def test_robust_resolved_forward_can_only_release_paper_observation(self):
        actual=self.assess()
        self.assertEqual(actual.action,"PAPER_OBSERVATION_ONLY",actual.blocking_reasons)
        self.assertFalse(actual.live_execution_authorized)
        self.assertEqual(actual.production_risk_fraction,0.)
        self.assertEqual(actual.conditional_side,"BUY")
        self.assertGreater(actual.historical_context_stats["verified_forward"]["n"],45)
        self.assertIn("causal_forward_performance_gate_passed",actual.confirming_evidence)

    def test_existing_unvalidated_v9_history_cannot_be_promoted(self):
        actual=self.assess(experience=histories(forward=False))
        self.assertEqual(actual.action,"WAIT")
        self.assertIn("insufficient_verified_forward_experience",actual.blocking_reasons)
        self.assertEqual(actual.historical_context_stats["verified_forward"]["n"],0)

    def test_no_history_yields_explicit_wait(self):
        actual=self.assess(experience=[])
        self.assertEqual(actual.action,"WAIT")
        self.assertIn("insufficient_verified_forward_experience",actual.blocking_reasons)
        self.assertEqual(actual.historical_context_stats["n"],0)

    def test_future_resolved_result_blocks_all_history(self):
        future=replace(histories(1)[0],resolved_at_utc=NOW+timedelta(hours=1))
        actual=self.assess(experience=histories()+[future])
        self.assertEqual(actual.action,"WAIT")
        self.assertIn("outcome_ledger_violates_point_in_time",actual.blocking_reasons)
        self.assertEqual(actual.historical_context_stats["n"],0)

    def test_out_of_order_entry_label_blocks_history(self):
        history=histories()
        wrong=replace(history[0],signal_at_utc=history[0].resolved_at_utc)
        actual=self.assess(experience=history+[wrong])
        self.assertIn("outcome_ledger_violates_point_in_time",actual.blocking_reasons)

    def test_no_cross_symbol_or_side_performance_reuse(self):
        alien=[replace(x,symbol="NAS100.vx") for x in histories()]
        actual=self.assess(experience=alien)
        self.assertEqual(actual.action,"WAIT")
        self.assertEqual(actual.historical_context_stats["n"],0)

    def test_unverified_macro_cannot_authorize(self):
        actual=self.assess(macro=[macro(verified=False)])
        self.assertIn("macro_policy_transmission_not_verified",actual.blocking_reasons)

    def test_future_macro_cannot_authorize(self):
        case=replace(macro(),observed_at_utc=NOW+timedelta(seconds=5))
        actual=self.assess(macro=[case])
        self.assertIn("future_or_unobserved_macro_information",actual.blocking_reasons)

    def test_macro_conflict_blocks_entry(self):
        actual=self.assess(macro=[macro("SELL")])
        self.assertIn("macro_technical_direction_conflict",actual.blocking_reasons)
        self.assertEqual(actual.conditional_side,"BUY")
        self.assertEqual(actual.action,"WAIT")

    def test_disagreeing_verified_sources_block(self):
        actual=self.assess(macro=[macro("BUY"),macro("SELL",source="bls")])
        self.assertIn("contradictory_macro_direction",actual.blocking_reasons)

    def test_spread_and_risk_guardrails(self):
        too_costly=self.assess(observed_spread=.9)
        self.assertIn("spread_exceeds_M15_volatility_budget",too_costly.blocking_reasons)
        risk=replace(RISK,drawdown_fraction=.05,realized_daily_loss_r=-2.4,
                     open_positions=1,gross_exposure_fraction=.003)
        blocked=self.assess(risk=risk)
        for reason in ("drawdown_pause","daily_loss_pause",
                       "concurrent_paper_limit","paper_exposure_cap"):
            self.assertIn(reason,blocked.blocking_reasons)

    def test_news_missing_or_blackout_blocks(self):
        no_news=replace(NEWS,ready=False,matched_items=0,source_count=0)
        self.assertIn("no_verified_relevant_news",
                      self.assess(news=no_news).blocking_reasons)
        self.assertIn("high_impact_news_blackout",
                      self.assess(news=replace(NEWS,blackout=True)).blocking_reasons)

    def test_market_uncertainty_blocks_even_with_good_memory(self):
        x=self.assess(card=card(state="VOLATILITY_SHOCK"))
        self.assertIn("uncertain_or_shock_regime",x.blocking_reasons)

    def test_drift_detection_stops_good_old_average(self):
        x=self.assess(experience=histories(last_negative=True))
        self.assertIn("resolved_forward_performance_not_stable",x.blocking_reasons)

    def test_geometry_and_technical_signal_are_not_rationalized(self):
        weird=replace(card(),rr_after_spread_estimate=.5,technical_signal="WAIT")
        x=self.assess(card=weird)
        self.assertIn("no_confirmed_closed_candle_entry",x.blocking_reasons)
        self.assertIn("risk_reward_geometry_not_favorable",x.blocking_reasons)
        self.assertEqual(x.conditional_side,"WAIT")

    def test_opposing_directional_evidence_survives_contextual_pipeline(self):
        opposing=replace(
            card(),directional_alignment="H1_M15_STRONG_OPPOSITION_WAIT",
            directional_observations=("H1_closed_structure_opposes_BUY",
                                      "M15_closed_momentum_opposes_BUY"),
            directional_h1_momentum_atr=-2.1,
            directional_m15_momentum_atr=-1.2)
        result=self.assess(card=opposing)
        self.assertEqual(result.action,"WAIT")
        self.assertIn("H1_M15_directional_contradiction",
                      result.blocking_reasons)
        dumped=result.to_dict()
        self.assertEqual(dumped["directional_alignment"],
                         "H1_M15_STRONG_OPPOSITION_WAIT")
        self.assertEqual(len(dumped["directional_observations"]),2)
        self.assertEqual(dumped["directional_h1_momentum_atr"],-2.1)
        self.assertFalse(dumped["live_execution_authorized"])

    def test_spread_risk_budget_is_visible_in_existing_context_card(self):
        expensive=replace(card(),pre_entry_spread_fraction_of_stop_risk=.315)
        x=self.assess(card=expensive)
        self.assertEqual(x.to_dict()["pre_entry_spread_fraction_of_stop_risk"],.315)
        self.assertFalse(x.live_execution_authorized)

    def test_existing_context_includes_real_pattern_evidence_and_rejection(self):
        false_pattern=replace(card(),
            pattern_semantically_confirmed=False,
            pattern_semantic_blockers=(
                "prior_countertrend_closed_candles",
                "closed_candle_resumption"))
        result=self.assess(card=false_pattern).to_dict()
        self.assertFalse(result["pattern_semantically_confirmed"])
        self.assertEqual(len(result["pattern_semantic_blockers"]),2)
        self.assertFalse(result["live_execution_authorized"])

    def test_additive_native_brain_gateway_does_not_activate_orders(self):
        brain=MarketDecisionBrain()
        result=brain.evaluate_contextually(
            symbol=SYMBOL,candles=market("up"),
            as_of_utc=NOW,actual_spread=.02,
            news_context=NEWS,macro_evidence=[macro()],
            resolved_experience=[],risk_situation=RISK)
        self.assertEqual(result.symbol,SYMBOL)
        self.assertEqual(result.action,"WAIT")
        self.assertTrue(result.research_only)
        self.assertFalse(result.live_execution_authorized)
        self.assertEqual(result.production_risk_fraction,0.)
        self.assertIsNotNone(result.next_recheck)
        self.assertEqual(result.confidence_is_profit_probability,False)

    def test_gateway_market_candle_without_new_news_wait(self):
        result=MarketDecisionBrain().evaluate_contextually(
            symbol=SYMBOL,candles=market("down"),as_of_utc=NOW,
            actual_spread=.02,news_context=replace(NEWS,ready=False),
            macro_evidence=(),resolved_experience=histories(),risk_situation=RISK)
        self.assertEqual(result.action,"WAIT")
        self.assertIn("macro_policy_transmission_not_verified",result.blocking_reasons)

    def test_nonfinite_cost_is_blocked(self):
        x=self.assess(observed_spread=float("nan"))
        self.assertIn("invalid_broker_cost_or_atr",x.blocking_reasons)


if __name__=="__main__":
    unittest.main()
