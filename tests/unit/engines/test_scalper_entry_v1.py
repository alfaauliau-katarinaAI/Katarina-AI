import unittest

from katarina.engines.scalper_entry import (
    EntryMode,
    EntrySide,
    ScalperEntryEngine,
    ScalperSnapshot,
)
from katarina.engines.decision import DecisionAction, DecisionEngine
from katarina.intelligence.perception.regime import Regime, RegimeAssessment


def base_snapshot(**overrides):
    data = dict(
        open=2000.0,
        high=2003.0,
        low=1998.0,
        close=2001.0,
        ema10=2000.5,
        ema50=1995.0,
        ema50_prev=1994.0,
        rsi14=55.0,
        rsi2=50.0,
        bb_lower=1988.0,
        bb_mid=2000.0,
        bb_upper=2012.0,
        atr14=5.0,
        atr_avg50=5.0,
        adx14=28.0,
        reference_high=2005.0,
        reference_low=1995.0,
        vwap=1999.0,
        tick_velocity_norm=0.6,
        orderflow_imbalance=0.3,
        mtf_alignment=0.8,
        htf_direction=1,
        spread_bps=1.0,
        session="LONDON",
        data_fresh=True,
        news_blackout=False,
    )
    data.update(overrides)
    return ScalperSnapshot(**data)


class ScalperEntryV1Tests(unittest.TestCase):
    def setUp(self):
        self.engine = ScalperEntryEngine()

    def test_trend_pullback_buy(self):
        regime = RegimeAssessment(Regime.TREND_UP, .8, False)
        s = base_snapshot(low=1999.5, close=2001.0, open=1999.8, ema10=2000.0, rsi14=55, adx14=30)
        p = self.engine.evaluate(regime, s)
        self.assertTrue(p.valid)
        self.assertEqual(p.mode, EntryMode.TREND_PULLBACK)
        self.assertEqual(p.side, EntrySide.BUY)
        self.assertGreaterEqual(p.score, .65)
        self.assertGreater(p.expected_rr, 1.0)

    def test_trend_blocks_htf_conflict(self):
        regime = RegimeAssessment(Regime.TREND_UP, .8, False)
        p = self.engine.evaluate(regime, base_snapshot(htf_direction=-1))
        self.assertFalse(p.valid)
        self.assertIn("htf_bias_conflict", p.reasons)

    def test_range_mean_reversion_buy(self):
        regime = RegimeAssessment(Regime.RANGE, .7, False)
        s = base_snapshot(
            open=1989.0, close=1987.0, low=1986.5, high=1990.0,
            rsi2=6.0, bb_lower=1988.0, bb_mid=1995.0, bb_upper=2002.0,
            atr14=5.0, adx14=17.0, mtf_alignment=.35, htf_direction=0,
        )
        p = self.engine.evaluate(regime, s)
        self.assertTrue(p.valid)
        self.assertEqual(p.mode, EntryMode.RANGE_MEAN_REVERSION)
        self.assertEqual(p.side, EntrySide.BUY)

    def test_range_rejects_strong_adx(self):
        regime = RegimeAssessment(Regime.RANGE, .7, False)
        s = base_snapshot(rsi2=5, close=1987, bb_lower=1988, adx14=31, mtf_alignment=.3, htf_direction=0)
        p = self.engine.evaluate(regime, s)
        self.assertFalse(p.valid)
        self.assertIn("range_adx_too_high", p.reasons)

    def test_momentum_breakout_buy(self):
        regime = RegimeAssessment(Regime.HIGH_VOL, .85, False)
        s = base_snapshot(
            open=2000, close=2010, high=2011, low=1999,
            reference_high=2006, reference_low=1994,
            atr14=8, atr_avg50=5, adx14=35,
            tick_velocity_norm=.8, orderflow_imbalance=.5,
            vwap=2003, mtf_alignment=.7, htf_direction=1,
        )
        p = self.engine.evaluate(regime, s)
        self.assertTrue(p.valid)
        self.assertEqual(p.mode, EntryMode.MOMENTUM_BREAKOUT)
        self.assertEqual(p.side, EntrySide.BUY)

    def test_news_blackout_is_fail_closed(self):
        regime = RegimeAssessment(Regime.TREND_UP, .8, False)
        p = self.engine.evaluate(regime, base_snapshot(news_blackout=True))
        self.assertFalse(p.valid)
        self.assertIn("high_impact_news_blackout", p.reasons)

    def test_stale_data_is_fail_closed(self):
        regime = RegimeAssessment(Regime.RANGE, .8, False)
        p = self.engine.evaluate(regime, base_snapshot(data_fresh=False))
        self.assertFalse(p.valid)
        self.assertIn("stale_data", p.reasons)

    def test_unknown_regime_no_trade(self):
        p = self.engine.evaluate(RegimeAssessment(Regime.UNKNOWN, 0, True), base_snapshot())
        self.assertFalse(p.valid)

    def test_decision_never_authorizes_live_risk(self):
        regime = RegimeAssessment(Regime.TREND_UP, .8, False)
        p = self.engine.evaluate(regime, base_snapshot(low=1999.5, close=2001, open=1999.8, ema10=2000, rsi14=55))
        d = DecisionEngine().decide_scalper(p, system_healthy=True)
        self.assertEqual(d.action, DecisionAction.BUY)
        self.assertFalse(d.live_risk_authorized)

    def test_unhealthy_system_forces_safe_mode(self):
        regime = RegimeAssessment(Regime.TREND_UP, .8, False)
        p = self.engine.evaluate(regime, base_snapshot(low=1999.5, close=2001, open=1999.8, ema10=2000, rsi14=55))
        d = DecisionEngine().decide_scalper(p, system_healthy=False)
        self.assertEqual(d.action, DecisionAction.SAFE_MODE)


if __name__ == "__main__":
    unittest.main()
