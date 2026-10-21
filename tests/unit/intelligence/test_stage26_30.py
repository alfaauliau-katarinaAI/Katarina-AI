import unittest
from datetime import datetime,timedelta,timezone
from katarina.intelligence.perception.learning import LearningEngine
from katarina.intelligence.perception.simple_ml import MachineLearningV1
from katarina.governance.models import ModelPromotionController,PromotionEvidence,ModelState
from katarina.intelligence.perception.economics import EconomicIntelligenceEngine,EconomicEvent
from katarina.engines.portfolio import PortfolioEngine

class Stage2630Tests(unittest.TestCase):
    def test_learning_no_direct_mutation(self):
        e=LearningEngine(); self.assertFalse(e.production_mutation_allowed()); self.assertTrue(e.detect_drift([0,0],[1,1],threshold=.5).detected)
    def test_ml_probability(self):
        m=MachineLearningV1().train([[0],[1],[2],[3]],[0,0,1,1],epochs=200); self.assertLess(m.predict_proba([0]),m.predict_proba([3]))
    def test_promotion_all_gates(self):
        d=ModelPromotionController().evaluate(PromotionEvidence(True,True,True,True,True)); self.assertTrue(d.allowed); self.assertEqual(d.target_state,ModelState.ACTIVE)
    def test_promotion_fails_closed(self):
        d=ModelPromotionController().evaluate(PromotionEvidence(True,False,True,True,True)); self.assertFalse(d.allowed)
    def test_economic_blackout(self):
        now=datetime.now(timezone.utc); e=EconomicEvent("NFP",now+timedelta(minutes=5),3,("USD",))
        self.assertTrue(EconomicIntelligenceEngine().assess([e],now_utc=now).blackout)
    def test_portfolio_total_cap(self):
        p=PortfolioEngine().allocate({"XAUUSD":.04,"EURUSD":.04,"GBPUSD":.04},max_total_risk=.08); self.assertLessEqual(p.total_risk,.08)
if __name__=="__main__": unittest.main()
