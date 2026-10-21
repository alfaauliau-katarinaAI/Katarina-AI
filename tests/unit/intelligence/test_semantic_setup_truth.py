"""Semantic strategy labels must imply observable causal structure."""
import unittest
from datetime import datetime,timedelta,timezone
from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
from katarina.intelligence.perception.semantic_setup_truth import CausalSetupValidator
NOW=datetime(2026,10,9,16,0,tzinfo=timezone.utc)

def candles(minutes=5):
    return [SensorCandle(NOW-timedelta(minutes=(60-i)*minutes),
              100.0,100.22,99.78,100.04,100) for i in range(60)]
class TestSemanticSetup(unittest.TestCase):
    def setUp(self):
        self.m5=candles()
        self.v=CausalSetupValidator()
        self.opt=dict(side="BUY",playbook="BREAKOUT_RETEST",m5=self.m5,
             m15=candles(15),h1=candles(60),spread=.02,as_of_utc=NOW)
    def test_no_breakout_means_not_a_retest(self):
        r=self.v.assess(**self.opt)
        self.assertFalse(r.pattern_confirmed)
        self.assertIn("prior_closed_candle_broke_earlier_range",r.blockers)
        self.assertFalse(r.live_execution_authorized)
    def test_actual_breakout_retest_on_closed_candles(self):
        m=list(self.m5)
        m[-2]=SensorCandle(m[-2].closed_at_utc,100.03,101.4,99.8,101.0,100)
        m[-1]=SensorCandle(m[-1].closed_at_utc,100.35,101.0,100.22,100.8,100)
        r=self.v.assess(**(self.opt|dict(m5=m)))
        self.assertTrue(r.pattern_confirmed,r.blockers)
        self.assertGreater(r.setup_level,100.2)
        self.assertFalse(r.live_execution_authorized)
    def test_range_requires_sweep_and_closure(self):
        r=self.v.assess(**(self.opt|dict(playbook="RANGE_FADE")))
        self.assertFalse(r.pattern_confirmed)
        self.assertIn("prior_range_extreme_tested",r.blockers)
    def test_reversal_requires_sweep(self):
        r=self.v.assess(**(self.opt|dict(playbook="REVERSAL_RECLAIM")))
        self.assertFalse(r.pattern_confirmed)
        self.assertIn("prior_swing_liquidity_swept",r.blockers)
    def test_false_trend_pullback_not_just_bullish_bar(self):
        r=self.v.assess(**(self.opt|dict(playbook="TREND_PULLBACK")))
        self.assertFalse(r.pattern_confirmed)
        self.assertIn("prior_countertrend_closed_candles",r.blockers)
    def test_future_leak_rejected(self):
        bad=list(self.m5)
        b=bad[-1];bad[-1]=SensorCandle(NOW+timedelta(minutes=1),
                b.open,b.high,b.low,b.close)
        with self.assertRaisesRegex(ValueError,"future_or_unordered"):
            self.v.assess(**(self.opt|dict(m5=bad)))
    def test_spread_veto(self):
        r=self.v.assess(**(self.opt|dict(spread=100)))
        self.assertFalse(r.pattern_confirmed)
        self.assertIn("spread_exceeds_semantic_setup_budget",r.blockers)
    def test_bad_geometry_fails(self):
        bad=list(self.m5)
        b=bad[-1];bad[-1]=SensorCandle(b.closed_at_utc,100.,99.,98.,100.)
        with self.assertRaisesRegex(ValueError,"geometry"):
            self.v.assess(**(self.opt|dict(m5=bad)))
if __name__=="__main__":unittest.main()