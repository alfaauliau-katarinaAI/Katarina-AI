import tempfile,unittest
from pathlib import Path
from katarina.engines.exposure import CorrelationExposureEngine
from katarina.monitoring.dashboard import Dashboard,DashboardSnapshot
from katarina.monitoring.operational_dashboard import OperationalDashboardSnapshot
from katarina.governance.ci import AutomatedTestingPolicy
from katarina.governance.constitution import ConstitutionGuard
from katarina.adapters.tester import TesterEvent,TesterTransport,StrategyTesterIntegration

class Stage3135Tests(unittest.TestCase):
    def test_correlation_penalizes(self):
        r=CorrelationExposureEngine().assess({"A":.04,"B":.04},{"A":[1,2,3],"B":[2,4,6]},cap=.08); self.assertFalse(r.allowed); self.assertGreater(r.correlation_penalty,0)
    def test_dashboard_serializes(self):
        s=DashboardSnapshot("RUNNING","OK",False,1000,.01,"RANGE","NO_TRADE","v1",{}); self.assertIn('"execution_armed":false',Dashboard().render_json(s))
    def test_extended_dashboard_serializes(self):
        s=OperationalDashboardSnapshot("RUNNING","OK",False,1000,.01,.02,.02,.01,.01,0,.01,.04,.04,False,"RANGE","RANGE_MEAN_REVERSION","NO_TRADE",True,False,1.4,1.8,.52,(),{})
        self.assertIn('"remaining_risk_capacity":0.04',Dashboard().render_operational_json(s))
    def test_ci_fail_closed(self):
        self.assertFalse(AutomatedTestingPolicy().assess({"unit":True}).passed)
        self.assertTrue(AutomatedTestingPolicy().assess({"unit":True,"static":True,"compile":True,"audit":True}).passed)
    def test_constitution_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"KATARINA_CONSTITUTION.md"; p.write_text("frozen")
            g=ConstitutionGuard(); self.assertTrue(g.verify(p,g.digest(p)).valid); self.assertFalse(g.proposed_paths_allowed(["KATARINA_CONSTITUTION.md"]))
    def test_tester_deterministic_order(self):
        t=TesterTransport([TesterEvent(2,"b",{}),TesterEvent(1,"a",{})]); out=StrategyTesterIntegration().replay(t); self.assertEqual([x.sequence for x in out],[1,2])
if __name__=="__main__": unittest.main()
