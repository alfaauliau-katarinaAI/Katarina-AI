"""Predeclared directional-evidence guards are symmetric and causal."""
import unittest
from datetime import datetime,timedelta,timezone
from dataclasses import replace

from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
from katarina.intelligence.perception.directional_consensus import assess_direction

NOW=datetime(2026,10,13,0,0,tzinfo=timezone.utc)


def bars(minutes,sign):
    vals=[]
    for i in range(75):
        close=100.+sign*i*.15
        start=NOW-timedelta(minutes=(75-i)*minutes)
        vals.append(SensorCandle(start,
            close-sign*.05,close+.22,close-.23,close))
    return vals


def frames(sign):
    return {"M5":bars(5,sign),"M15":bars(15,sign),"H1":bars(60,sign)}


class TestSideSpecificDirectionalEvidence(unittest.TestCase):
    def test_buy_on_rising_h1_m15_alignment(self):
        r=assess_direction(candles=frames(+1),as_of_utc=NOW,
                           side="BUY",regime="TREND_UP")
        self.assertEqual(r.verdict,"THREE_TIMEFRAME_AGREEMENT")
        self.assertFalse(r.veto_strong_contradiction)
        self.assertGreater(r.h1_momentum_atr,0)
        self.assertFalse(r.not_a_win_probability is False)
        self.assertTrue(any("BUY" in v for v in r.supports))

    def test_sell_on_falling_h1_m15_alignment(self):
        r=assess_direction(candles=frames(-1),as_of_utc=NOW,
                           side="SELL",regime="TREND_DOWN")
        self.assertEqual(r.verdict,"THREE_TIMEFRAME_AGREEMENT")
        self.assertFalse(r.veto_strong_contradiction)
        self.assertLess(r.h1_momentum_atr,0)
        self.assertTrue(any("SELL" in v for v in r.supports))

    def test_clear_buy_against_both_frames_vetoes_technical_only(self):
        r=assess_direction(candles=frames(-1),as_of_utc=NOW,
                           side="BUY",regime="TREND_UP")
        self.assertTrue(r.veto_strong_contradiction)
        self.assertEqual(r.verdict,"H1_M15_STRONG_OPPOSITION_WAIT")
        self.assertTrue(any("H1" in x for x in r.challenges))
        self.assertTrue(any("M15" in x for x in r.challenges))

    def test_clear_sell_against_both_frames_vetoes_technical_only(self):
        r=assess_direction(candles=frames(+1),as_of_utc=NOW,
                           side="SELL",regime="PULLBACK_DOWN")
        self.assertTrue(r.veto_strong_contradiction)

    def test_reversal_and_range_intentionally_exempt_from_veto(self):
        for state in ("REVERSAL_UP","SIDEWAYS","BREAKOUT_UP"):
            r=assess_direction(candles=frames(-1),as_of_utc=NOW,
                               side="BUY",regime=state)
            self.assertFalse(r.veto_strong_contradiction)

    def test_future_candle_and_unknown_side_fail_closed(self):
        x=frames(1)
        x["H1"][-1]=replace(x["H1"][-1],
            closed_at_utc=NOW+timedelta(seconds=10))
        with self.assertRaises(ValueError):
            assess_direction(candles=x,as_of_utc=NOW,
                             side="BUY",regime="TREND_UP")
        with self.assertRaises(ValueError):
            assess_direction(candles=frames(1),as_of_utc=NOW,
                             side="WAIT",regime="TREND_UP")


if __name__=="__main__":unittest.main()
