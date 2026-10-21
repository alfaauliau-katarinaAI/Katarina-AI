"""Guard precommitted Aug 2026 side-specific price-action hypotheses."""
import unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
from katarina.intelligence.lab.precommitted_setup_research import (
    _propose,research_alternatives,FROZEN_RULE_VERSION,
)

NOW=datetime(2026,8,20,21,0,tzinfo=timezone.utc)


def candles(interval, count=80):
    out=[]
    for i in range(count):
        dt=NOW-timedelta(minutes=(count-1-i)*interval)
        out.append(SensorCandle(dt,100.,101.,99.,100.))
    return out


def fixture():
    return {"M5":candles(5),"M15":candles(15),"H1":candles(60)}


class TestFrozenResearchPatterns(unittest.TestCase):
    def test_prior_range_sweep_and_reclaim_must_close_inside(self):
        f=fixture()
        a=f["M5"][-5]
        f["M5"][-5]=replace(a,high=104.)
        end=f["M5"][-1]
        f["M5"][-1]=replace(end,open=99.15,high=100.,
                           low=98.5,close=99.45)
        cases=_propose(f,.05)
        valid=[x for x in cases if x["method"]=="RANGE_SWEEP_RECLAIM"]
        self.assertEqual(len(valid),1)
        self.assertEqual(valid[0]["side"],"BUY")
        self.assertLess(valid[0]["stop"],end.low)
        self.assertGreater(valid[0]["target"],end.close)
        self.assertEqual(valid[0]["frozen_rule_version"],FROZEN_RULE_VERSION)
        self.assertFalse(valid[0]["broker_execution_allowed"])

    def test_never_guess_winner_when_sweep_not_reclaimed(self):
        f=fixture()
        a=f["M5"][-5]
        f["M5"][-5]=replace(a,high=104.)
        end=f["M5"][-1]
        f["M5"][-1]=replace(end,open=99.5,high=100,
                           low=98,close=98.5)
        self.assertFalse(any(x["method"]=="RANGE_SWEEP_RECLAIM"
                         for x in _propose(f,.05)))

    def test_prior_breakout_and_current_retest_are_different_bars(self):
        f=fixture()
        old=f["M5"][-8]
        f["M5"][-8]=replace(old,low=97.)
        prev=f["M5"][-2]
        f["M5"][-2]=replace(prev,open=100.8,low=100.8,high=102.5,
                            close=102.)
        last=f["M5"][-1]
        f["M5"][-1]=replace(last,open=101.4,low=101.,high=102.,
                            close=101.7)
        xs=_propose(f,.05)
        b=[x for x in xs if x["method"]=="BREAKOUT_RETEST_LEVEL"]
        self.assertEqual(len(b),1)
        self.assertEqual(b[0]["side"],"BUY")
        self.assertGreater(b[0]["rr_signal_proxy"],1.25)

    def test_any_future_higher_timeframe_is_hard_rejected(self):
        f=fixture()
        last=f["H1"][-1]
        f["H1"][-1]=replace(last,closed_at_utc=NOW+timedelta(minutes=1))
        with self.assertRaisesRegex(ValueError,"future_bar_leak"):
            _propose(f,.05)

    def test_zero_spread_or_excessive_spread_does_not_create_signal(self):
        f=fixture()
        self.assertEqual(_propose(f,0),[])
        self.assertEqual(_propose(f,100),[])

    def test_research_output_no_order_authorization_or_faked_labels(self):
        f=fixture()
        d={"TEST.vx":f}
        spreads={int(c.closed_at_utc.timestamp()):.05 for c in f["M5"]}
        result=research_alternatives(d,{"TEST.vx":spreads},
            window_start=NOW-timedelta(hours=3),
            window_end=NOW,max_cuts_per_symbol=200)
        self.assertEqual(result["orders_sent"],0)
        self.assertFalse(result["live_execution_authorized"])
        self.assertTrue(result["no_untouched_OOS_claim_without_prior_data_provenance"])
        self.assertEqual(result["simulated_outcomes"],0)
        self.assertEqual(result["all_plus_0_15R_assumed"]["n"],0)

    def test_invalid_bounds_fail_without_broker_calls(self):
        with self.assertRaises(ValueError):
            research_alternatives({}, {},window_start=NOW,
                window_end=NOW-timedelta(days=1))


if __name__=="__main__":unittest.main()
