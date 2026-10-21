"""Only pre-registered, closed-bar hypotheses; never orders."""
import json
import unittest
from datetime import datetime, timezone

from katarina.intelligence.perception.screening import features, screen
from katarina.intelligence.shadow.shadow_hypotheses import FAMILY, propose

NOW = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)


def trending(side, timeframe):
    size = 60 if timeframe == "m1" else 300
    end = int(NOW.timestamp())-size
    result = []
    up = side == "BUY"
    for i in range(120):
        base = (100 + 0.2*i) if up else (130 - 0.2*i)
        o = base-0.10 if up else base+0.10
        c = base+0.10 if up else base-0.10
        hi = base+0.15
        lo = base-0.15
        volume = 100
        if timeframe=="m1" and i == 119:
            o = base+0.12 if up else base-0.12
            hi = base+0.90 if up else base+0.15
            lo = base+0.05 if up else base-0.90
            c = base+0.84 if up else base-0.84
            volume = 500
        result.append(dict(time=end-(119-i)*size,
                           open=o, high=hi, low=lo, close=c,
                           tick_volume=volume))
    return result


def row(side, mode=4):
    m1 = trending(side, "m1")
    m5 = trending(side, "m5")
    last = m1[-1]["close"]
    return dict(symbol="DEMO", base="EUR", profit="USD", trade_mode=mode,
                connected=True, tick_time=NOW.timestamp(),
                bid=last-0.01, ask=last+0.01,
                m1=features(m1,60,NOW),
                m5=features(m5,300,NOW),
                m1_bars=m1, m5_bars=m5, errors=[])


class ClearContext:
    def assess(self, exposure, now):
        return dict(ready=True,reasons=[])


class BlockedContext:
    def assess(self, exposure, now):
        return dict(ready=False,reasons=["calendar_unavailable"])


class ResearchHypothesesTests(unittest.TestCase):
    def test_buy_only_in_uptrend(self):
        result = screen([row("BUY")], ClearContext(), NOW)
        signal = result["symbols"][0]["shadow_hypotheses"]
        # The old universal trend hypothesis may be tested directly, but
        # the market observer never assigns it to an unregistered instrument.
        self.assertEqual(signal,[])
        self.assertEqual(result["shadow_candidate_count"],0)
        self.assertEqual(result["shadow_candidate_watchlist"],[])
        original=row("BUY")
        self.assertEqual(propose({**original,"allowed_sides":["BUY"],
            "regime_detail":"TREND_UP"})[0]["family"],FAMILY)
        self.assertEqual(result["symbols"][0]["action"],"NO_TRADE")
        self.assertFalse(result["live_execution_enabled"])
        self.assertGreater(propose({**original,"allowed_sides":["BUY"],
            "regime_detail":"TREND_UP"})[0]["breakout_atr"],0)
        json.dumps(result,allow_nan=False)

    def test_sell_only_in_downtrend(self):
        result = screen([row("SELL")], ClearContext(), NOW)
        signal = result["symbols"][0]["shadow_hypotheses"]
        self.assertEqual(signal,[])
        original=row("SELL")
        self.assertEqual(propose({**original,"allowed_sides":["SELL"],
            "regime_detail":"TREND_DOWN"})[0]["side"],"SELL")

    def test_broker_side_restriction(self):
        self.assertEqual(screen([row("BUY",mode=2)],ClearContext(),NOW)
                         ["symbols"][0]["shadow_hypotheses"],[])
        self.assertEqual(screen([row("SELL",mode=1)],ClearContext(),NOW)
                         ["symbols"][0]["shadow_hypotheses"],[])

    def test_macro_outage_keeps_observation_but_never_trade(self):
        result = screen([row("BUY")],BlockedContext(),NOW)
        observed = result["symbols"][0]
        self.assertEqual(observed["shadow_hypotheses"],[])
        self.assertFalse(observed["research_candidate"])
        self.assertEqual(observed["action"],"NO_TRADE")
        self.assertEqual(result["research_watchlist"],[])

    def test_stale_quote_rejects_hypothesis(self):
        candidate = row("BUY")
        candidate["tick_time"] -= 31
        result = screen([candidate],ClearContext(),NOW)
        self.assertEqual(result["symbols"][0]["shadow_hypotheses"],[])

    def test_stale_bar_rejects_hypothesis(self):
        candidate = row("BUY")
        candidate["m1"]["close_age_seconds"] = 91
        self.assertEqual(propose({**candidate,
           "allowed_sides":["BUY"],"regime_detail":"TREND_UP"}), [])

    def test_volume_confirmation_required(self):
        candidate = row("BUY")
        candidate["m1_bars"][-1]["tick_volume"] = 100
        self.assertEqual(propose({**candidate,
           "allowed_sides":["BUY"],"regime_detail":"TREND_UP"}),[])

    def test_no_breakout_when_last_bar_not_outside_prior_high(self):
        candidate = row("BUY")
        latest = candidate["m1_bars"][-1]
        latest["close"] = latest["open"]+0.01
        self.assertEqual(propose({**candidate,
           "allowed_sides":["BUY"],"regime_detail":"TREND_UP"}),[])

    def test_range_and_transition_abstain(self):
        candidate = row("BUY")
        for regime in ("RANGE","TRANSITION","UNKNOWN",None):
            self.assertEqual(propose({**candidate,
                "allowed_sides":["BUY"],"regime_detail":regime}),[])

    def test_no_raw_bar_evidence_abstains(self):
        candidate = row("BUY")
        del candidate["m1_bars"]
        self.assertEqual(propose({**candidate,
            "allowed_sides":["BUY"],"regime_detail":"TREND_UP"}),[])


if __name__=="__main__":
    unittest.main()
