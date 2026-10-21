"""Registered alternative market hypotheses: broker clock and causal rules."""
from datetime import datetime,timezone
import unittest

from katarina.intelligence.perception.alternative_symbol_playbooks import (
    SYMBOLS,propose as propose_alternative)
from katarina.intelligence.perception.symbol_playbooks import SYMBOLS as LIVE_RESEARCH

class AlternativeSymbolTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,9,24,1,40,tzinfo=timezone.utc)
        base=self.now.timestamp()-120*60
        self.m1=[]
        for i in range(120):
            self.m1.append(dict(time=base+i*60,
              open=100.,high=100.4,low=99.6,close=100.1,
              tick_volume=100.))
        base5=self.now.timestamp()-120*300
        self.m5=[]
        for i in range(120):
            self.m5.append(dict(time=base5+i*300,
                open=100.,high=100.4,low=99.6,close=100.1,
                tick_volume=100.))
        origin=datetime(2026,9,24,1,1,tzinfo=timezone.utc).timestamp()
        self.day=[]
        for i in range(39):
            self.day.append(dict(time=origin+i*60,open=100.,
                 high=100.4,low=99.6,close=100.1,tick_volume=100.))

    def test_separate_alternatives_from_registered_observer(self):
        self.assertEqual(set(SYMBOLS),{"XAUUSD.vx","US30.vx","JPN225.vx"})
        for symbol in SYMBOLS:
            self.assertNotEqual(SYMBOLS[symbol],LIVE_RESEARCH[symbol])

    def test_alternative_does_not_inherit_nas_strategy(self):
        with self.assertRaisesRegex(ValueError,"no_cross_market_alternative"):
            propose_alternative("NAS100.vx",self.m1,self.m5,[],self.now)

    def test_index_opening_range_uses_actual_broker_0101_candle(self):
        self.m1[-2].update(close=100.1)
        self.m1[-1].update(open=100.7,high=102.2,low=100.65,close=101.9)
        self.day[-1]=dict(self.m1[-1])
        answer=propose_alternative("JPN225.vx",self.m1,self.m5,self.day,self.now)
        self.assertEqual(len(answer),1)
        self.assertEqual(answer[0]["side"],"BUY")
        self.assertIn("nikkei_",answer[0]["family"])
        self.assertLess(answer[0]["hypothetical_stop"],answer[0]["hypothetical_target"])
        self.assertFalse(answer[0]["live_authorized"])

    def test_unknown_opening_session_does_not_fabricate_0030(self):
        self.m1[-1].update(open=100.7,high=102.2,low=100.65,close=101.9)
        too_early=[dict(b,time=b["time"]-70*60) for b in self.day]
        self.assertEqual(propose_alternative(
            "JPN225.vx",self.m1,self.m5,too_early,self.now),[])

    def test_future_day_candle_rejected(self):
        self.day[-1]["time"]=self.now.timestamp()
        with self.assertRaisesRegex(ValueError,"unclosed_market_data_forbidden"):
            propose_alternative("JPN225.vx",self.m1,self.m5,self.day,self.now)

if __name__=="__main__":
    unittest.main()
