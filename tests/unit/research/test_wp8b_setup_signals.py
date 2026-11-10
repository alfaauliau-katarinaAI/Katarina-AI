"""WP8b-A synthetic causal detector tests; no MT5, network, broker or orders."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from katarina.research.setups import fibonacci, liquidity_sweep, market_structure, pullback
from katarina.research.validation import ValidationError

BASE = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)


def bar(start, tf, op, hi, lo, cl):
    minutes = 60 if tf == "H1" else 5
    return {"time_utc": start.isoformat(),
            "closed_at_utc": (start + timedelta(minutes=minutes)).isoformat(),
            "open": op, "high": hi, "low": lo, "close": cl,
            "spread": 1, "tick_volume": 10, "real_volume": 1}


def past_trend(side="BUY"):
    offset = BASE - timedelta(hours=6)
    closes = [100, 101, 102, 103] if side == "BUY" else [113, 112, 111, 110]
    return [bar(offset + timedelta(hours=i), "H1", c, c+2, c-2, c)
            for i, c in enumerate(closes)]


def args(**kw):
    values = {"lookback": 3, "trend_lookback": 3,
              "min_sweep": 0.1, "stop_buffer": 0.1,
              "target_rr": 2.0, "min_rr": 1.5, "tolerance": .5,
              "fib_min": .382, "fib_max": .618,
              "swing_lookback": 3, "breakout_buffer": .2}
    values.update(kw)
    return values


def m5(rows):
    return [bar(BASE + timedelta(minutes=i * 5), "M5", *row)
            for i, row in enumerate(rows)]


class WP8bSignalsTest(unittest.TestCase):
    def test_sweep_buy_and_sell_are_separate(self):
        buy = {"M5": m5([(101, 102, 100, 101)] * 3 +
                         [(100, 102, 99, 101.2)]),
               "H1": past_trend("BUY")}
        sell = {"M5": m5([(109, 110, 108, 109)] * 3 +
                          [(111, 112, 108, 109)]),
                "H1": past_trend("SELL")}
        when = BASE + timedelta(minutes=20)
        b = liquidity_sweep.detect(buy, when, args(), "BUY")
        s = liquidity_sweep.detect(sell, when, args(), "SELL")
        self.assertEqual(len(b), 1)
        self.assertEqual(len(s), 1)
        self.assertLess(b[0].invalidation, b[0].entry_mid)
        self.assertGreater(s[0].invalidation, s[0].entry_mid)
        self.assertEqual(b[0].setup, "liquidity_sweep")
        self.assertEqual(s[0].side, "SELL")

    def test_pullback_buy(self):
        bars = {"M5": m5([(100.2, 101, 99.8, 100.5),
                           (100.5, 102, 100.0, 101),
                           (101, 102.5, 100.5, 101.5),
                           (100.7, 102, 100.6, 101.3)]),
                "H1": past_trend()}
        signals = pullback.detect(bars, BASE + timedelta(minutes=20), args(), "BUY")
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].trend_side, "BUY")

    def test_fibonacci_buy(self):
        bars = {"M5": m5([(101.5, 103, 101, 102.0)]),
                "H1": past_trend()}
        out = fibonacci.detect(bars, BASE + timedelta(minutes=5), args(), "BUY")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].regime, "UPTREND")

    def test_structure_break_buy(self):
        bars = {"M5": m5([(101, 102, 100, 101),
                           (102, 103, 101, 102),
                           (103, 104, 102, 103),
                           (104.5, 106, 104.1, 105.5)]),
                "H1": past_trend()}
        out = market_structure.detect(bars, BASE + timedelta(minutes=20), args(), "BUY")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].setup, "market_structure")

    def test_pullback_sell(self):
        bars = {"M5": m5([(111, 112, 109, 110),
                           (110, 111, 108.5, 109),
                           (109, 110, 108, 108.5),
                           (110, 110.5, 108, 108.7)]),
                "H1": past_trend("SELL")}
        out = pullback.detect(bars, BASE + timedelta(minutes=20), args(), "SELL")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].trend_side, "SELL")

    def test_fibonacci_sell(self):
        bars = {"M5": m5([(112, 113, 110.5, 111)]),
                "H1": past_trend("SELL")}
        out = fibonacci.detect(bars, BASE + timedelta(minutes=5), args(), "SELL")
        self.assertEqual(len(out), 1)
        self.assertLess(out[0].target, out[0].entry_mid)

    def test_structure_break_sell(self):
        bars = {"M5": m5([(111, 113, 109, 110),
                           (110, 112, 108, 109),
                           (109, 111, 107, 108),
                           (107, 107.5, 106.4, 106.5)]),
                "H1": past_trend("SELL")}
        out = market_structure.detect(bars, BASE + timedelta(minutes=20), args(), "SELL")
        self.assertEqual(len(out), 1)
        self.assertGreater(out[0].invalidation, out[0].entry_mid)

    def test_future_ohlc_never_read(self):
        bars = {"M5": m5([(101, 102, 100, 101)] * 3 +
                         [(100, 102, 99, 101.2)]),
                "H1": past_trend("BUY")}
        when = BASE + timedelta(minutes=20)
        expected = liquidity_sweep.detect(bars, when, args(), "BUY")
        future = bar(BASE + timedelta(minutes=20), "M5", 1, 1, 1, 1)
        future["close"] = "-9999"
        future["high"] = "-999"
        bars["M5"].append(future)
        self.assertEqual(liquidity_sweep.detect(bars, when, args(), "BUY"), expected)

    def test_no_lookahead_signal_after_missing_last_bar(self):
        bars = {"M5": m5([(101, 102, 100, 101)] * 3 +
                         [(100, 102, 99, 101.2)]),
                "H1": past_trend()}
        self.assertEqual(liquidity_sweep.detect(bars, BASE + timedelta(minutes=25),
                                                 args(), "BUY"), [])

    def test_missing_parameters_fail_closed(self):
        bars = {"M5": m5([(101, 102, 100, 101)] * 3 +
                         [(100, 102, 99, 101.2)]),
                "H1": past_trend()}
        parameters = args()
        del parameters["target_rr"]
        with self.assertRaises(ValidationError):
            liquidity_sweep.detect(bars, BASE + timedelta(minutes=20),
                                    parameters, "BUY")

    def test_holdout_time_rejected(self):
        bars = {"M5": m5([(101, 102, 100, 101)] * 3 +
                         [(100, 102, 99, 101.2)]),
                "H1": past_trend()}
        with self.assertRaises(ValidationError):
            liquidity_sweep.detect(bars, datetime(2026, 10, 14, tzinfo=timezone.utc),
                                    args(), "BUY")

    def test_invalid_side_rejected(self):
        with self.assertRaises(ValidationError):
            market_structure.detect({"M5": [], "H1": []}, BASE,
                                    args(), "BOTH")


if __name__ == "__main__":
    unittest.main()
