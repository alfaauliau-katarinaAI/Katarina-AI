import unittest
from katarina.intelligence.perception.market import MarketIntelligenceEngine
from katarina.intelligence.perception.timeframe import MultiTimeframeEngine, TimeframeView
from katarina.intelligence.perception.regime import MarketRegimeEngine, Regime
from katarina.intelligence.perception.xauusd import XauusdSpecialistV1
from katarina.engines.decision import DecisionEngine, DecisionAction

class Stage1115Tests(unittest.TestCase):
    def test_market_features(self):
        r=MarketIntelligenceEngine().analyze([100,101,102,103],bid=102.9,ask=103.1)
        self.assertTrue(r.sufficient); self.assertGreater(r.momentum,0); self.assertGreaterEqual(r.volatility,0)
    def test_mtf_alignment(self):
        r=MultiTimeframeEngine().assess({"M15":TimeframeView("M15",1,.8),"H1":TimeframeView("H1",1,.9)})
        self.assertEqual(r.dominant_direction,1); self.assertGreater(r.alignment,.8)
    def test_regime_unknown_fails_closed(self):
        r=MarketRegimeEngine().classify(momentum=.1,volatility=.01,alignment=.8,history_ok=False)
        self.assertEqual(r.regime,Regime.UNKNOWN); self.assertTrue(r.out_of_distribution)
    def test_xauusd_specialist_blocks_high_vol(self):
        regime=MarketRegimeEngine().classify(momentum=.1,volatility=.06,alignment=.9)
        a=XauusdSpecialistV1().assess(regime=regime,momentum=.1,spread_bps=1,session="LONDON")
        self.assertFalse(a.valid_domain); self.assertEqual(a.bias,0)
    def test_decision_never_authorizes_live_risk(self):
        regime=MarketRegimeEngine().classify(momentum=.02,volatility=.003,alignment=.9)
        a=XauusdSpecialistV1().assess(regime=regime,momentum=.02,spread_bps=1,session="LONDON")
        d=DecisionEngine().decide(a,expected_rr=2.0,system_healthy=True)
        self.assertIn(d.action,{DecisionAction.BUY,DecisionAction.NO_TRADE}); self.assertFalse(d.live_risk_authorized)
    def test_unhealthy_system_safe_mode(self):
        regime=MarketRegimeEngine().classify(momentum=.02,volatility=.003,alignment=.9)
        a=XauusdSpecialistV1().assess(regime=regime,momentum=.02,spread_bps=1,session="LONDON")
        self.assertEqual(DecisionEngine().decide(a,expected_rr=2,system_healthy=False).action,DecisionAction.SAFE_MODE)
if __name__=="__main__": unittest.main()
