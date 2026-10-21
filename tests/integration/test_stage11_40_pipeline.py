import unittest

from katarina.intelligence.market import MarketIntelligenceEngine
from katarina.intelligence.timeframe import MultiTimeframeEngine, TimeframeView
from katarina.intelligence.regime import MarketRegimeEngine
from katarina.intelligence.xauusd import XauusdSpecialistV1
from katarina.engines.decision import DecisionEngine, DecisionAction
from katarina.engines.risk import RiskGovernor, RiskRequest
from katarina.engines.sizing import PositionSizingEngine
from katarina.engines.execution import ExecutionEngine, ExecutionIntent
from katarina.adapters.paper import PaperExecutionVenue, PaperOrder
from katarina.governance.live_validation import LiveMicroRiskValidator, LiveValidationEvidence
from katarina.governance.evolution import ContinuousEvolutionController, EvolutionProposal

class Stage1140PipelineTests(unittest.TestCase):
    def test_analysis_to_paper_path_preserves_authority(self):
        mi=MarketIntelligenceEngine().analyze([2000,2002,2005,2010],bid=2009.8,ask=2010.2)
        mtf=MultiTimeframeEngine().assess({"M15":TimeframeView("M15",1,.8),"H1":TimeframeView("H1",1,.9)})
        regime=MarketRegimeEngine().classify(momentum=mi.momentum,volatility=mi.volatility,alignment=mtf.alignment)
        spec=XauusdSpecialistV1().assess(regime=regime,momentum=mi.momentum,spread_bps=mi.spread_bps,session="LONDON")
        candidate=DecisionEngine().decide(spec,expected_rr=2.0,system_healthy=True)
        self.assertFalse(candidate.live_risk_authorized)
        if candidate.action in {DecisionAction.BUY,DecisionAction.SELL}:
            risk=RiskGovernor().evaluate(RiskRequest(.01,0,0,candidate.uncertainty,candidate.expected_rr,True,True))
            self.assertLessEqual(risk.approved_fraction,.05)
            size=PositionSizingEngine().size(equity=10000,risk_fraction=risk.approved_fraction,stop_distance=10,value_per_price_unit_per_lot=10,volume_min=.01,volume_max=10,volume_step=.01)
            self.assertTrue(size.valid)
            intent=ExecutionIntent("intent-1",candidate.action.value,"XAUUSD",size.volume,1990,None,"decision-1","risk-1")
            execution=ExecutionEngine()
            self.assertFalse(execution.preflight(intent,execution_armed=False,fresh=True,reconciled=True,spread_ok=True).allowed)
            fill=PaperExecutionVenue().execute(PaperOrder("paper-1",candidate.action.value,2010,size.volume))
            self.assertGreater(fill.volume,0)

    def test_live_micro_gate_default_is_blocked(self):
        evidence=LiveValidationEvidence(False,False,False,False,False,False,.001)
        self.assertFalse(LiveMicroRiskValidator().evaluate(evidence).allowed)

    def test_evolution_requires_governed_review(self):
        d=ContinuousEvolutionController().decide(EvolutionProposal("p","h","v2",True,True))
        self.assertEqual(d.action,"PROMOTION_REVIEW")
        self.assertFalse(ContinuousEvolutionController().autonomous_live_promotion_allowed())

if __name__=="__main__": unittest.main()
