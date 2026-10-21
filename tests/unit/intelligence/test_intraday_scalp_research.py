"""Full-candle intraday/scalp: no forward price peeking, conservative fills."""
import unittest
import numpy as np
from katarina.intelligence.intraday_scalp_research import (
    Candidate,trailing_mean,previous_extremes,vector_prefilter,fill_next_open)

DT=[("time","<i8"),("open","<f8"),("high","<f8"),
    ("low","<f8"),("close","<f8"),("tick_volume","<i8"),
    ("spread","<i8"),("real_volume","<i8")]

def bars(n=250,sec=300):
    x=np.zeros(n,dtype=DT)
    x["time"]=1_700_000_000+np.arange(n)*sec
    x["open"]=100+.02*np.arange(n)
    x["close"]=x["open"]+.04
    x["high"]=x["close"]+.3
    x["low"]=x["open"]-.3
    x["spread"]=2
    x["tick_volume"]=200
    return x

class TestIntradayScalpFullBar(unittest.TestCase):
    def test_trailing_average_is_current_and_past_only(self):
        x=trailing_mean([1,2,3,4,5],3)
        self.assertTrue(np.isnan(x[1]))
        self.assertAlmostEqual(x[2],2.)
        self.assertAlmostEqual(x[4],4.)

    def test_previous_channel_excludes_current_bar(self):
        b=bars()
        old=b["high"][180]
        b["high"][180]+=400
        hi,lo=previous_extremes(b,20)
        self.assertLess(hi[180],b["high"][180])
        self.assertEqual(hi[181],b["high"][180])

    def test_no_future_bar_used_for_earlier_signal(self):
        m5=bars(250,300);m15=bars(150,900);h1=bars(110,3600)
        s1,_=vector_prefilter("US30.vx",m5,m15,h1,.01)
        m5["high"][220:]*=1.4
        m5["close"][220:]*=1.1
        s2,_=vector_prefilter("US30.vx",m5,m15,h1,.01)
        prior=lambda xs:[(x.cut,x.side,x.mode) for x in xs if x.idx<190]
        self.assertEqual(prior(s1),prior(s2))

    def test_prospective_scanner_can_include_newest_closed_bar_without_future_exit(self):
        m5=bars(300,300);m15=bars(150,900);h1=bars(110,3600)
        _,backtest=vector_prefilter("US30.vx",m5,m15,h1,.01)
        _,forward=vector_prefilter("US30.vx",m5,m15,h1,.01,
                                  allow_unresolved_latest=True)
        self.assertGreater(forward["closed_bars_considered"],
                           backtest["closed_bars_considered"])

    def test_large_spread_rejects_all_setups(self):
        m5=bars(260,300);m15=bars(150,900);h1=bars(110,3600)
        m5["spread"]=999999
        res,metrics=vector_prefilter("XAUUSD.vx",m5,m15,h1,.01)
        self.assertEqual(res,[])
        self.assertGreater(metrics["closed_bars_considered"],0)

    def test_stop_first_when_both_reachable_in_bar(self):
        b=bars(120)
        b["open"][91]=100.
        b["high"][91]=104.
        b["low"][91]=98.
        e=Candidate("US30.vx",int(b["time"][91]),90,"BUY","INTRADAY",
                    .8,1.,.05,99.,("fixture",))
        v=fill_next_open(b,e,.01)
        self.assertIsNotNone(v)
        self.assertEqual(v["raw_outcome"],"SL")
        self.assertLess(v["R"],0)
        self.assertFalse(e.live_execution_authorized)

    def test_gapped_bar_has_no_pretend_fill(self):
        b=bars(120)
        b["time"][91]+=600
        e=Candidate("US30.vx",int(b["time"][90])+300,90,"BUY","INTRADAY",
                    .8,1.,.05,99.,("fixture",))
        self.assertIsNone(fill_next_open(b,e,.01))

    def test_extreme_scalp_has_tighter_holding_cap(self):
        b=bars(120)
        e=Candidate("US30.vx",int(b["time"][91]),90,"BUY","SCALP_EXTREME",
                    .9,1.,.01,99.,("fixture",))
        v=fill_next_open(b,e,.01)
        if v:
            self.assertLessEqual(v["hold_bars"],8)
            self.assertEqual(v["model_rr"],1.3)

if __name__=="__main__":unittest.main()