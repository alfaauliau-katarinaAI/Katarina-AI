import unittest

from katarina.engines.scalper_entry import ScalperEntryEngine, ScalperSnapshot
from katarina.intelligence.perception.regime import Regime, RegimeAssessment


class MultiMarketScalperCompatibilityTests(unittest.TestCase):
    def _snap(self,**kw):
        base=dict(
            open=100,high=101,low=99.8,close=100.5,
            ema10=100.2,ema50=100,ema50_prev=99.99,
            rsi14=55,rsi2=50,bb_lower=97,bb_mid=100,bb_upper=103,
            atr14=1,atr_avg50=1,adx14=30,reference_high=101.5,reference_low=98.5,
            vwap=100,tick_velocity_norm=.5,orderflow_imbalance=.3,mtf_alignment=.8,
            htf_direction=1,spread_bps=5,session="ASIA",
        )
        base.update(kw)
        return ScalperSnapshot(**base)

    def test_explicit_broker_session_unlocks_non_legacy_session(self):
        r=RegimeAssessment(Regime.TREND_UP,.9,False)
        p=ScalperEntryEngine().evaluate(r,self._snap(tradable_session=True,spread_limit_bps=6))
        self.assertTrue(p.valid)

    def test_without_override_legacy_session_guard_remains(self):
        r=RegimeAssessment(Regime.TREND_UP,.9,False)
        p=ScalperEntryEngine().evaluate(r,self._snap())
        self.assertFalse(p.valid)
        self.assertIn("outside_liquid_session",p.reasons)


if __name__=="__main__": unittest.main()
