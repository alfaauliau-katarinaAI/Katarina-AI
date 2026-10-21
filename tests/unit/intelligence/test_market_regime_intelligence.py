"""Deterministic causal behavior and no-trading guarantees for regime v1."""
import json,unittest
from datetime import datetime,timezone
from katarina.intelligence.perception.market_regime_intelligence import (
    classify_regime,PROFILES,_reversal_structure)

NOW=datetime(2026,10,9,12,tzinfo=timezone.utc)

def fixture(kind,seconds,n=120):
    times=NOW.timestamp()-(n*seconds)
    result=[]
    for i in range(n):
        if kind=="UP":price=100+i*.30
        elif kind=="DOWN":price=160-i*.30
        elif kind=="RANGE":price=120+(.4 if i%2 else -.4)
        elif kind=="FLAT":price=120
        else:raise ValueError(kind)
        result.append(dict(time=times+i*seconds,open=price,
            high=price+.52,low=price-.52,close=price,
            tick_volume=100+i%7))
    return result

class MarketRegimeIntelligenceTests(unittest.TestCase):
    def test_seven_registered_symbols_have_distinct_profiles(self):
        self.assertEqual(len(PROFILES),7)
        self.assertEqual(len(set((p["trend_adx"],p["range_adx"],
                p["reversal_sweep_atr"]) for p in PROFILES.values())),7)

    def test_three_timeframe_bullish_continuation(self):
        q=classify_regime("NAS100.vx",fixture("UP",300),fixture("UP",900),
             fixture("UP",3600),NOW,fixture("UP",60,60))
        self.assertEqual(q["regime"],"CONTINUATION_UP")
        self.assertEqual(q["entry_timing"],"M1_ALIGNED")
        self.assertFalse(q["entry_authorized"])
        self.assertFalse(q["evidence_is_profit_probability"])
        self.assertTrue(50<=q["evidence_score_0_100"]<=95)
        json.dumps(q,allow_nan=False)

    def test_three_timeframe_bearish_continuation(self):
        q=classify_regime("XAUUSD.vx",fixture("DOWN",300),
            fixture("DOWN",900),fixture("DOWN",3600),NOW)
        self.assertEqual(q["regime"],"CONTINUATION_DOWN")

    def test_sideways_when_m5_and_m15_no_trend(self):
        q=classify_regime("US30.vx",fixture("RANGE",300),
            fixture("RANGE",900),fixture("UP",3600),NOW)
        self.assertEqual(q["regime"],"SIDEWAYS")
        self.assertEqual(q["direction"],"NONE")

    def test_transition_when_higher_timeframes_conflict(self):
        q=classify_regime("EURUSD.vx",fixture("UP",300),
            fixture("DOWN",900),fixture("UP",3600),NOW)
        self.assertEqual(q["regime"],"TRANSITION")
        self.assertIsNone(q["evidence_score_0_100"])

    def test_timeframe_alignment_reports_each_frame(self):
        q=classify_regime("NAS100.vx",fixture("UP",300),fixture("UP",900),
             fixture("UP",3600),NOW)
        self.assertEqual(q["timeframe_alignment"],{"H1":"ALIGNED","M15":"ALIGNED","M5":"ALIGNED"})
        q=classify_regime("NAS100.vx",fixture("DOWN",300),
             fixture("UP",900),fixture("UP",3600),NOW)
        self.assertEqual(q["regime"],"PULLBACK_UP")
        self.assertEqual(q["timeframe_alignment"],{"H1":"ALIGNED","M15":"ALIGNED","M5":"CONFLICTING"})
        q=classify_regime("EURUSD.vx",fixture("UP",300),fixture("DOWN",900),fixture("UP",3600),NOW)
        self.assertEqual(set(q["timeframe_alignment"].values()),{"NEUTRAL"})
        self.assertEqual(classify_regime("UNKNOWN.vx",[],[],[],NOW)["timeframe_alignment"],{})

    def test_pullback_is_not_mislabeled_as_reversal(self):
        q=classify_regime("NAS100.vx",fixture("DOWN",300),
             fixture("UP",900),fixture("UP",3600),NOW)
        self.assertEqual(q["regime"],"PULLBACK_UP")
        self.assertFalse(q["reversal_confirmation"])
        self.assertFalse(q["entry_authorized"])

    def test_M15_M5_local_continuation_with_neutral_H1(self):
        q=classify_regime("XAUUSD.vx",fixture("UP",300),
             fixture("UP",900),fixture("RANGE",3600),NOW)
        self.assertEqual(q["regime"],"LOCAL_CONTINUATION_UP")
        self.assertFalse(q["evidence_is_calibrated"])

    def test_fully_confirmed_reversal_requires_both_sweep_and_break(self):
        h1=fixture("DOWN",3600)
        m15=fixture("RANGE",900)
        # Make M15 most recent 24 closed bars recover bullish direction.
        for j in range(96,120):
            p=120+(j-95)*.55
            m15[j].update(open=p-.3,high=p+.52,low=p-.52,close=p)
        f=fixture("RANGE",300)
        f[-5].update(open=119.5,high=120,low=117.0,close=119)
        f[-1].update(open=120.0,high=125.0,low=119.5,close=124.)
        q=classify_regime("XAUUSD.vx",f,m15,h1,NOW)
        self.assertEqual(q["regime"],"REVERSAL_UP")
        self.assertTrue(q["reversal_confirmation"])
        self.assertFalse(q["entry_authorized"])

    def test_stale_H1_does_not_silently_use_old_trend(self):
        h1=fixture("UP",3600)
        for b in h1:b["time"]-=24*3600
        q=classify_regime("NAS100.vx",fixture("UP",300),
            fixture("UP",900),h1,NOW)
        self.assertEqual(q["regime"],"UNKNOWN")
        self.assertFalse(q["entry_authorized"])

    def test_missing_and_unregistered_never_inherit_strategy(self):
        q=classify_regime("FAKE.vx",fixture("UP",300),fixture("UP",900),
                          fixture("UP",3600),NOW)
        self.assertEqual(q["reason_codes"],["symbol_profile_not_registered"])
        q=classify_regime("NAS100.vx",fixture("UP",300)[:10],fixture("UP",900),
                          fixture("UP",3600),NOW)
        self.assertEqual(q["regime"],"UNKNOWN")

    def test_unfinished_m5_cannot_leak_future(self):
        f=fixture("UP",300)
        f[-1]["time"]=NOW.timestamp()-100
        q=classify_regime("NAS100.vx",f,fixture("UP",900),
                           fixture("UP",3600),NOW)
        self.assertEqual(q["regime"],"UNKNOWN")

    def test_reversal_event_is_causal_and_requires_later_bar(self):
        f=fixture("RANGE",300)
        # A fresh sweep of previous 12 lows at -5. After that, a big
        # displacement candle closes above all highs of prior 8 bars.
        s=f[-5];s.update(open=119.5,high=120,low=117.0,close=119)
        new=f[-1];new.update(open=120,high=125,low=119.5,close=124)
        profile=PROFILES["XAUUSD.vx"]
        self.assertEqual(_reversal_structure(f,1.,profile)[0],"UP")
        # Without a *later* closed break, sweep alone is insufficient.
        f[-1]=fixture("RANGE",300)[-1]
        self.assertIsNone(_reversal_structure(f,1.,profile))

    def test_invalid_prices_fail_closed(self):
        x=fixture("UP",900)
        x[-10]["high"]=-1
        q=classify_regime("NAS100.vx",fixture("UP",300),x,
             fixture("UP",3600),NOW)
        self.assertEqual(q["regime"],"UNKNOWN")

if __name__=="__main__":
    unittest.main()
