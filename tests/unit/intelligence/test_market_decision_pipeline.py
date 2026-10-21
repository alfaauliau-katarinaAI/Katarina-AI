"""Functional smoke tests for closed-candle market decisions; no walk-forward or orders."""
import unittest
from datetime import datetime, timedelta, timezone

from katarina.intelligence.cognition.market_decision_pipeline import (
    MarketDecisionPipeline, SensorCandle,
)

NOW = datetime(2026, 10, 9, 16, 0, tzinfo=timezone.utc)
STEP = {"M5": 5, "M15": 15, "H1": 60}


def market(kind="up", volume=True):
    ret = {}
    for tf, mins in STEP.items():
        rows = []
        for j in range(90):
            t = NOW - timedelta(minutes=(90-j)*mins)
            if kind == "up":
                p = 4200 + j*0.4
                q = p + .30
            elif kind == "down":
                p = 4240 - j*.4
                q = p - .30
            elif kind == "range":
                p = 4200 + (-1 if j % 2 else 1)*.65
                q = p - .30 if j % 2 == 0 else p+.30
            else:
                raise ValueError("unsupported_fixture")
            rows.append(SensorCandle(t, p, max(p,q)+.20, min(p,q)-.20, q,
                                     (100+j%5) if volume else None))
        ret[tf] = rows
    return ret


class TestMarketDecisionPipeline(unittest.TestCase):
    def setUp(self):
        self.p = MarketDecisionPipeline()
        self.base = dict(symbol="XAUUSD.vx", as_of_utc=NOW,
                         actual_spread=.02, broker_session_open=True,
                         data_fresh=True, news_blackout=False,
                         news_context_verified=True)

    def evaluate(self, bars=None, **changes):
        data = {**self.base, "candles": market() if bars is None else bars, **changes}
        return self.p.evaluate(**data)

    def test_uptrend_routes_buy_with_capped_risk_reference(self):
        result = self.evaluate(active_capital_native=1000)
        self.assertEqual(result.action, "BUY", result)
        self.assertEqual(result.playbook, "TREND_PULLBACK")
        self.assertEqual(result.market_state, "TREND_UP")
        self.assertAlmostEqual(result.risk_fraction_reference, .0125)
        self.assertTrue(result.research_only)
        self.assertFalse(result.live_execution_authorized)
        self.assertIn("fib_retracements", result.tools)
        self.assertEqual(result.tools["vwap_source"],
                         "ROLLING20_M5_BROKER_TICK_VOLUME_PROXY_NOT_EXCHANGE_VOLUME")

    def test_optional_structural_entry_gate_vetoes_and_explains(self):
        original = self.evaluate()
        filtered = self.evaluate(use_structural_entry_gate=True)
        self.assertEqual(original.action, "BUY")
        self.assertIsNotNone(filtered.entry_quality)
        self.assertFalse(filtered.entry_quality.live_execution_authorized)
        self.assertEqual(filtered.action, "WAIT")
        self.assertEqual(filtered.decision_detail.decision, "WAIT")
        self.assertIn("structural_entry_quality_rejected",
                      filtered.decision_detail.blockers)

    def test_semantic_playbook_gate_rejects_fake_pullback(self):
        result = self.evaluate(use_semantic_setup_gate=True)
        self.assertEqual(result.playbook, "TREND_PULLBACK")
        self.assertEqual(result.action, "WAIT")
        self.assertIsNotNone(result.semantic_setup)
        self.assertFalse(result.semantic_setup.pattern_confirmed)
        self.assertIn("playbook_semantics_not_confirmed",
                      result.decision_detail.blockers)
        self.assertFalse(result.live_execution_authorized)

    def test_downtrend_routes_sell(self):
        result = self.evaluate(market("down"))
        self.assertEqual(result.action, "SELL", result)
        self.assertEqual(result.market_state, "TREND_DOWN")

    def test_range_is_not_forced_into_trend(self):
        result = self.evaluate(market("range"))
        self.assertNotIn(result.market_state, ("TREND_UP", "TREND_DOWN"))
        self.assertFalse(result.live_execution_authorized)

    def test_high_spread_blocks(self):
        result = self.evaluate(actual_spread=10.0)
        self.assertEqual(result.action, "WAIT")

    def test_news_blackout_blocks(self):
        result = self.evaluate(news_blackout=True)
        self.assertEqual(result.action, "WAIT")
        self.assertIn("high_impact_news_blackout", result.reasons)

    def test_news_context_missing_blocks_even_good_setup(self):
        result = self.evaluate(news_context_verified=False)
        self.assertEqual(result.market_state, "TREND_UP")
        self.assertEqual(result.action, "WAIT")
        self.assertIn("news_context_unverified_no_trade", result.reasons)

    def test_market_session_closed_blocks(self):
        result = self.evaluate(broker_session_open=False)
        self.assertEqual(result.action, "WAIT")

    def test_stale_frames_block(self):
        result = self.evaluate(as_of_utc=NOW+timedelta(hours=5))
        self.assertEqual(result.action, "WAIT")
        self.assertTrue(any("stale" in s for s in result.reasons))

    def test_future_bar_blocks(self):
        data = market()
        data["M5"][-1] = SensorCandle(NOW+timedelta(minutes=5),
                                     4237, 4238, 4236, 4237.5, 103)
        result = self.evaluate(data)
        self.assertEqual(result.action, "WAIT")
        self.assertEqual(result.market_state, "UNKNOWN")

    def test_insufficient_data_blocks(self):
        data = market()
        data["M15"] = data["M15"][:20]
        self.assertIn("insufficient", self.evaluate(data).reasons[0])

    def test_no_volume_does_not_fabricate_vwap(self):
        result = self.evaluate(market(volume=False))
        self.assertIsNone(result.tools["broker_tick_volume_vwap"])
        self.assertIsNone(result.tools["relative_tick_volume"])

    def test_nan_bar_blocks(self):
        data = market()
        x = data["H1"][-1]
        data["H1"][-1] = SensorCandle(x.closed_at_utc,x.open,x.high,
                                       x.low,float("nan"),x.tick_volume)
        self.assertEqual(self.evaluate(data).action,"WAIT")

    def test_risk_input_is_not_execution_permission(self):
        result = self.evaluate(active_capital_native=-1)
        self.assertEqual(result.action, "WAIT")
        self.assertFalse(result.live_execution_authorized)


if __name__ == "__main__":
    unittest.main()