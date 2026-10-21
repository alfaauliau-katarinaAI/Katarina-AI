"""Explainable autonomous advisory: six questions without unsafe broker execution."""
import unittest
from datetime import datetime, timedelta, timezone

from katarina.intelligence.cognition.market_decision_pipeline import (
    MarketDecisionPipeline, SensorCandle,
)

NOW = datetime(2026, 10, 9, 16, 0, tzinfo=timezone.utc)
TF = {"M5": 5, "M15": 15, "H1": 60}


def sample(kind="up"):
    out = {}
    for tf, minutes in TF.items():
        rows = []
        for i in range(100):
            stamp = NOW - timedelta(minutes=(100-i)*minutes)
            if kind == "up":
                price, close = 4200+i*.4, 4200+i*.4+.3
            elif kind == "down":
                price, close = 4240-i*.4, 4240-i*.4-.3
            else:
                price = 4200 + (-1 if i % 2 else 1)*.65
                close = price + (.3 if i%2 else -.3)
            rows.append(SensorCandle(stamp, price, max(price,close)+.2,
                                     min(price,close)-.2, close, 100+i%6))
        out[tf]=rows
    return out


class TestExplainableMarketDecision(unittest.TestCase):
    def setUp(self):
        self.pipeline = MarketDecisionPipeline()
        self.options=dict(
            symbol="XAUUSD.vx", as_of_utc=NOW,
            actual_spread=.02, broker_session_open=True, data_fresh=True,
            news_blackout=False, news_context_verified=True,
        )

    def get(self, kind="up", **changes):
        return self.pipeline.evaluate(candles=sample(kind), **(self.options | changes))

    def test_bullish_direction_scenarios_and_flexible_routing(self):
        report=self.get()
        self.assertEqual(report.action,"BUY")  # legacy research suggestion
        d=report.decision_detail
        self.assertEqual(d.activity,"TRENDING")
        self.assertEqual(d.direction,"BULLISH")
        self.assertEqual(d.primary.direction,"BULLISH")
        self.assertEqual(d.alternative.direction,"BEARISH")
        self.assertEqual(d.selected_strategy,"TREND_PULLBACK")
        self.assertEqual(d.signal,"BUY")
        self.assertEqual(d.decision,"RESEARCH_SETUP")
        self.assertTrue(d.entry_ready_for_research)
        self.assertGreater(d.primary.invalidation,0)
        self.assertGreater(d.primary.target,d.primary.reference_price)
        self.assertGreaterEqual(d.primary.indicative_rr,1)
        self.assertFalse(d.evidence_score_is_probability)
        self.assertFalse(d.live_execution_authorized)
        self.assertLess(d.support,d.resistance)
        self.assertEqual(d.snapshot_utc,(NOW-timedelta(minutes=5)).isoformat())
        self.assertTrue(any("H1" in x for x in d.explanations_id))
        self.assertGreaterEqual(len(d.ranked_strategies),2)
        self.assertGreaterEqual(
            d.ranked_strategies[0].evidence_score,
            d.ranked_strategies[1].evidence_score)

    def test_bearish_scenario_has_downside_and_reversal_alternative(self):
        d=self.get("down").decision_detail
        self.assertEqual(d.direction,"BEARISH")
        self.assertEqual(d.primary.direction,"BEARISH")
        self.assertLess(d.primary.target,d.primary.reference_price)
        self.assertGreater(d.primary.invalidation,d.primary.reference_price)
        self.assertEqual(d.alternative.direction,"BULLISH")
        self.assertFalse(d.live_execution_authorized)

    def test_sideways_does_not_invent_directional_forecast(self):
        d=self.get("range").decision_detail
        self.assertNotIn(d.activity,("TRENDING","BREAKOUT"))
        if d.direction=="SIDEWAYS":
            self.assertIn(d.primary.direction,
                          ("SIDEWAYS", "BULLISH_WITHIN_RANGE", "BEARISH_WITHIN_RANGE"))
            if d.primary.direction == "SIDEWAYS":
                self.assertIsNone(d.primary.indicative_rr)
            else:
                self.assertIn(d.selected_strategy, ("RANGE_FADE", "OBSERVE"))
        else:
            self.assertIn("market_structure_not_resolved",d.blockers)
            self.assertEqual(d.decision,"WAIT")

    def test_unverified_news_is_hard_veto_but_market_analysis_remains(self):
        d=self.get(news_context_verified=False).decision_detail
        self.assertEqual(d.direction,"BULLISH")
        self.assertEqual(d.decision,"WAIT")
        self.assertEqual(d.signal,"WAIT")
        self.assertIn("news_context_not_verified",d.blockers)
        self.assertIn("Verifikasi konteks berita sebelum entry.",d.next_check)

    def test_hard_news_blackout_beats_high_strategy_score(self):
        d=self.get(news_blackout=True).decision_detail
        self.assertEqual(d.decision,"WAIT")
        self.assertIn("high_impact_news_blackout",d.blockers)
        self.assertFalse(d.entry_ready_for_research)

    def test_closed_market_and_no_fresh_data_are_vetoes(self):
        a=self.get(broker_session_open=False).decision_detail
        b=self.get(data_fresh=False).decision_detail
        self.assertIn("broker_session_closed",a.blockers)
        self.assertIn("stale_market_data",b.blockers)

    def test_spread_blocks_and_next_action_explained(self):
        d=self.get(actual_spread=10).decision_detail
        self.assertEqual(d.decision,"WAIT")
        self.assertIn("spread_excessive_relative_to_atr",d.blockers)
        self.assertTrue(any("spread" in text for text in d.next_check))

    def test_invalid_or_future_bars_not_promoted(self):
        bars=sample()
        last=bars["M15"][-1]
        bars["M15"][-1]=SensorCandle(NOW+timedelta(minutes=15),
            last.open,last.high,last.low,last.close,last.tick_volume)
        r=self.pipeline.evaluate(candles=bars,**self.options)
        self.assertEqual(r.action,"WAIT")
        self.assertIsNone(r.decision_detail)

    def test_never_ready_for_live_execution(self):
        for kind in ("up","down","range"):
            d=self.get(kind).decision_detail
            self.assertTrue(d.research_only)
            self.assertFalse(d.live_execution_authorized)
            self.assertTrue(d.explanations)
            self.assertGreaterEqual(len(d.next_check),1)


if __name__=="__main__":
    unittest.main()