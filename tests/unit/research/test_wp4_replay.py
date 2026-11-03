"""WP4 T6 replay: causal closed bars and observed spread without MT5/network."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from katarina.research.validation import ValidationError
from scripts.research.replay_technical_signals import replay_symbol

BASE=datetime(2026,1,5,tzinfo=timezone.utc)
MINUTES={"M5":5,"M15":15,"H1":60,"H4":240}


def archive():
    rows={}
    for tf,mins in MINUTES.items():
        origin=BASE if tf=="M5" else BASE-timedelta(minutes=60*mins)
        length=56 if tf=="M5" else 55
        rows[tf]=[{"time_utc":(origin+timedelta(minutes=mins*i)).isoformat(),
                   "closed_at_utc":(origin+timedelta(minutes=mins*(i+1))).isoformat(),
                   "open":100., "high":101., "low":99., "close":100.,
                   "tick_volume":10, "spread":7, "real_volume":0}
                  for i in range(length)]
    return rows


class Spy:
    def __init__(self):
        self.calls=[]
    def evaluate(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(market_state="UPTREND",playbook="PULLBACK",
                               decision_detail=SimpleNamespace(technical_signal="BUY"))


class ReplayTest(unittest.TestCase):
    def test_only_closed_bars_and_actual_quote_spread(self):
        spy=Spy()
        result=replay_symbol(archive(),"XAUUSD",point=.01,pipeline=spy)
        self.assertEqual(result["evaluated"],2)
        self.assertEqual(result["signals"][0]["technical_signal"],"BUY")
        self.assertEqual(result["signals"][0]["count"],2)
        self.assertEqual(spy.calls[0]["actual_spread"],.07)
        for kw in spy.calls:
            at=kw["as_of_utc"]
            self.assertTrue(all(item.closed_at_utc<=at
                                for bars in kw["candles"].values() for item in bars))

    def test_future_ohlc_does_not_change_past_asof(self):
        bars=archive()
        expected=replay_symbol(bars,"XAUUSD",point=.01,pipeline=Spy())
        later=BASE+timedelta(minutes=56*5)
        bars["M5"].append({"time_utc":later.isoformat(),
                           "closed_at_utc":(later+timedelta(minutes=5)).isoformat(),
                           "open":1,"high":999,"low":1,"close":999,
                           "spread":20,"tick_volume":3,"real_volume":0})
        actual=replay_symbol(bars,"XAUUSD",point=.01,pipeline=Spy(),
                             max_cycles=56)
        self.assertEqual(actual,expected)

    def test_no_zero_or_missing_spread_point_default(self):
        with self.assertRaisesRegex(ValidationError,"point_missing"):
            replay_symbol(archive(),"XAUUSD",point=0,pipeline=Spy())


if __name__=="__main__":
    unittest.main()
