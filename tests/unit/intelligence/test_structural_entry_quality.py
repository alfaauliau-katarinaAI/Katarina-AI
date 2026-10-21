"""Structural Entry Quality invariants: purely closed market evidence."""
import unittest
from datetime import datetime, timedelta, timezone
from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
from katarina.intelligence.perception.structural_entry_quality import StructuralEntryQuality

NOW=datetime(2026,10,9,15,0,tzinfo=timezone.utc)
PERIODS={"M5":5,"M15":15,"H1":60}
def candles(up=True):
    data={}
    for key,mins in PERIODS.items():
        sequence=[]
        for i in range(64):
            p=(110 if up else 160)+(i*.15 if up else -i*.15)
            close=p+(.07 if up else -.07)
            sequence.append(SensorCandle(NOW-timedelta(minutes=(64-i)*mins),
                 p,max(p,close)+.19,min(p,close)-.19,close,100))
        data[key]=sequence
    return data

class TestStructuralEntry(unittest.TestCase):
    def setUp(self):
        self.r=StructuralEntryQuality()
        self.data=candles()
        self.opts=dict(side="BUY",playbook="TREND_PULLBACK",
          m5=self.data["M5"],m15=self.data["M15"],h1=self.data["H1"],
          spread=.02,as_of_utc=NOW)

    def test_is_research_only_not_live_authorization(self):
        result=self.r.assess(**self.opts)
        self.assertFalse(result.live_execution_authorized)
        self.assertTrue(result.research_only)
        self.assertEqual(result.side,"BUY")
        self.assertTrue(result.next_trigger)

    def test_future_bar_rejected(self):
        bad=list(self.data["M5"])
        last=bad[-1]
        bad[-1]=SensorCandle(NOW+timedelta(minutes=5),
            last.open,last.high,last.low,last.close,last.tick_volume)
        with self.assertRaisesRegex(ValueError,"future_or_unordered"):
            self.r.assess(**(self.opts|dict(m5=bad)))

    def test_unordered_bars_rejected(self):
        bad=list(self.data["M5"])
        bad[-1]=bad[-2]
        with self.assertRaisesRegex(ValueError,"future_or_unordered"):
            self.r.assess(**(self.opts|dict(m5=bad)))

    def test_stale_invalid_unverified_inputs_not_silent(self):
        with self.assertRaisesRegex(ValueError,"naive"):
            self.r.assess(**(self.opts|dict(as_of_utc=datetime(2026,10,9))))
        with self.assertRaisesRegex(ValueError,"invalid_side"):
            self.r.assess(**(self.opts|dict(side="WAIT")))
        with self.assertRaisesRegex(ValueError,"insufficient"):
            self.r.assess(**(self.opts|dict(h1=self.data["H1"][:10])))

    def test_spread_veto_is_hard(self):
        r=self.r.assess(**(self.opts|dict(spread=100)))
        self.assertFalse(r.eligible)
        self.assertIn("spread_too_expensive",r.blockers)

    def test_range_requires_reversal_evidence(self):
        r=self.r.assess(**(self.opts|dict(playbook="RANGE_FADE")))
        self.assertFalse(r.eligible)
        self.assertTrue(set(r.blockers)&{"no_range_reversal_evidence","not_at_range_edge"})

    def test_breakout_requires_retest_not_only_bullish_candle(self):
        r=self.r.assess(**(self.opts|dict(playbook="BREAKOUT_RETEST")))
        self.assertFalse(r.eligible)
        self.assertIn("breakout_retest_not_confirmed",r.blockers)

    def test_evidence_score_not_automatically_acceptance(self):
        r=self.r.assess(**self.opts)
        self.assertGreaterEqual(r.score,0)
        self.assertLessEqual(r.score,1)
        if r.blockers:self.assertFalse(r.eligible)

if __name__=="__main__":unittest.main()