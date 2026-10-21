import unittest

from katarina.engines.scalper_entry import ScalperEntryEngine, ScalperSnapshot
from katarina.engines.decision import DecisionAction, DecisionEngine
from katarina.engines.risk import RiskAction, RiskGovernor, RiskRequest
from katarina.intelligence.perception.regime import Regime, RegimeAssessment


class ScalperEntryPipelineTests(unittest.TestCase):
    def test_trend_candidate_reaches_risk_governor_but_not_live_authority(self):
        snapshot = ScalperSnapshot(
            open=2000.0, high=2003.0, low=1999.4, close=2001.5,
            ema10=2000.0, ema50=1995.0, ema50_prev=1994.0,
            rsi14=55.0, rsi2=50.0,
            bb_lower=1988.0, bb_mid=2000.0, bb_upper=2012.0,
            atr14=5.0, atr_avg50=5.0, adx14=30.0,
            reference_high=2005.0, reference_low=1995.0, vwap=1999.0,
            tick_velocity_norm=.5, orderflow_imbalance=.25,
            mtf_alignment=.85, htf_direction=1, spread_bps=1.0,
            session="LONDON", data_fresh=True, news_blackout=False,
        )
        proposal = ScalperEntryEngine().evaluate(RegimeAssessment(Regime.TREND_UP,.85,False), snapshot)
        candidate = DecisionEngine().decide_scalper(proposal, system_healthy=True)
        self.assertEqual(candidate.action, DecisionAction.BUY)
        self.assertFalse(candidate.live_risk_authorized)

        risk = RiskGovernor(hard_per_trade=.04).evaluate(
            RiskRequest(.0025, 0.0, 0.0, candidate.uncertainty, candidate.expected_rr, True, True)
        )
        self.assertIn(risk.action, {RiskAction.APPROVE, RiskAction.REDUCE})
        self.assertLessEqual(risk.approved_fraction, .04)

    def test_wide_spread_stops_before_decision(self):
        snapshot = ScalperSnapshot(
            open=2000.0, high=2003.0, low=1999.4, close=2001.5,
            ema10=2000.0, ema50=1995.0, ema50_prev=1994.0,
            rsi14=55.0, rsi2=50.0,
            bb_lower=1988.0, bb_mid=2000.0, bb_upper=2012.0,
            atr14=5.0, atr_avg50=5.0, adx14=30.0,
            reference_high=2005.0, reference_low=1995.0, vwap=1999.0,
            tick_velocity_norm=.5, orderflow_imbalance=.25,
            mtf_alignment=.85, htf_direction=1, spread_bps=9.0,
            session="LONDON", data_fresh=True, news_blackout=False,
        )
        proposal = ScalperEntryEngine().evaluate(RegimeAssessment(Regime.TREND_UP,.85,False), snapshot)
        candidate = DecisionEngine().decide_scalper(proposal, system_healthy=True)
        self.assertEqual(candidate.action, DecisionAction.NO_TRADE)


if __name__ == "__main__":
    unittest.main()
