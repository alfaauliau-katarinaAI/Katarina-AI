"""V6 integration contract: fail closed and never infer broker live readiness."""
from __future__ import annotations
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
from katarina.intelligence.lab.unified_intraday_gate import check_candidate,min_capital_for_broker
from katarina.intelligence.lab.intraday_scalp_research import Candidate

class TestIntegratedResearchGate(unittest.TestCase):
    def test_current_broker_min_contract_risk_scenario(self):
        info=SimpleNamespace(trade_tick_size=.01,trade_tick_value_loss=1.0,
                             volume_min=.1)
        self.assertAlmostEqual(min_capital_for_broker(info,.50,"INTRADAY"),2000.)
        self.assertAlmostEqual(min_capital_for_broker(info,.50,"SCALP_EXTREME"),5000.)
    def test_missing_tick_value_not_claim_feasible(self):
        info=SimpleNamespace(trade_tick_size=.01,trade_tick_value_loss=0.,
                             volume_min=.1)
        self.assertIsNone(min_capital_for_broker(info,.50,"INTRADAY"))
    def test_missing_history_rejects_before_brain(self):
        dt=[("time","<i8"),("open","<f8"),("high","<f8"),
            ("low","<f8"),("close","<f8"),("spread","<i8")]
        m5=np.zeros(8,dtype=dt);m15=np.zeros(8,dtype=dt);h1=np.zeros(8,dtype=dt)
        for a,step in ((m5,300),(m15,900),(h1,3600)):
            a["time"]=1_700_000_000+np.arange(8)*step
        x=Candidate("XAUUSD.vx",int(m5["time"][5])+300,
                    5,"BUY","INTRADAY",.9,1.,.04,100.,("fixture",))
        gate,why=check_candidate(x,m5,m15,h1,
            {"M5":m5["time"],"M15":m15["time"],"H1":h1["time"]},
            .01,Mock(),Mock(),Mock())
        self.assertIsNone(gate)
        self.assertEqual(why,"missing_history")
    def test_ineligible_candidate_does_not_fabricate_authorization(self):
        x=Candidate("US30.vx",1_700_000_000,90,"SELL",
                  "INTRADAY",.94,1.2,.04,100.,("fixture",))
        self.assertTrue(x.research_only)
        self.assertFalse(x.live_execution_authorized)
if __name__=="__main__":unittest.main()