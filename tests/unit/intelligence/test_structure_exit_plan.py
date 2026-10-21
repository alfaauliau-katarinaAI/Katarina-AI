"""Fail-closed tests for conditional, causal structural SL/TP research."""
import unittest
from datetime import datetime,timedelta,timezone
from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
from katarina.intelligence.perception.structure_exit_plan import StructuralExitPlanner

NOW=datetime(2026,10,9,16,0,tzinfo=timezone.utc)
def bars(minutes, direction=1):
    result=[]
    for i in range(60):
        p=100+direction*.02*i
        q=p+direction*.008
        result.append(SensorCandle(
            NOW-timedelta(minutes=(60-i)*minutes),
            p,max(p,q)+(.6 if minutes!=5 else .18),
            min(p,q)-(.6 if minutes!=5 else .18),q,120))
    return result

class TestStructureExit(unittest.TestCase):
    def setUp(self):
        self.engine=StructuralExitPlanner()
        self.data=dict(
            side="BUY",m5=bars(5),m15=bars(15),h1=bars(60),
            expected_entry=101.2,spread=.02,point=.01,as_of_utc=NOW
        )

    def test_buy_levels_and_never_trade_live(self):
        r=self.engine.plan(**self.data)
        self.assertFalse(r.live_execution_authorized)
        self.assertTrue(r.research_only)
        if r.approved_for_research:
            self.assertLess(r.stop, self.data["expected_entry"])
            self.assertGreater(r.target,self.data["expected_entry"])
            self.assertGreaterEqual(r.reward_risk,1.25)
        else:
            self.assertGreater(len(r.blockers),0)

    def test_sell_levels_and_never_trade_live(self):
        rows=dict(side="SELL",m5=bars(5,-1),m15=bars(15,-1),
                  h1=bars(60,-1),expected_entry=98.8)
        r=self.engine.plan(**(self.data|rows))
        self.assertFalse(r.live_execution_authorized)
        if r.approved_for_research:
            self.assertGreater(r.stop,98.8)
            self.assertLess(r.target,98.8)

    def test_future_bar_rejected(self):
        values=list(self.data["m5"])
        last=values[-1]
        values[-1]=SensorCandle(NOW+timedelta(minutes=5),
              last.open,last.high,last.low,last.close)
        with self.assertRaisesRegex(ValueError,"future_or_unordered"):
            self.engine.plan(**(self.data|dict(m5=values)))

    def test_unordered_bar_rejected(self):
        values=list(self.data["h1"])
        values[-1]=values[-2]
        with self.assertRaisesRegex(ValueError,"future_or_unordered"):
            self.engine.plan(**(self.data|dict(h1=values)))

    def test_insufficient_data_rejected(self):
        with self.assertRaisesRegex(ValueError,"insufficient"):
            self.engine.plan(**(self.data|dict(m15=self.data["m15"][-12:])))

    def test_invalid_entry_spread_and_parameters(self):
        for change in (dict(expected_entry=float("nan")),dict(spread=-1),
                       dict(point=0),dict(side="WAIT")):
            with self.assertRaises(ValueError):
                self.engine.plan(**(self.data|change))
        with self.assertRaises(ValueError):
            StructuralExitPlanner(min_rr=3,max_rr=2)

if __name__=="__main__":unittest.main()