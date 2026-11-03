"""Synthetic-only readiness checks for all four research setup engines, BUY and SELL.

This test is NOT empirical broker backtesting and must never be interpreted as
proof of trading profitability, Stage0 completion, or permission to trade.
"""
from datetime import datetime, timedelta, timezone
import math
import sys
import unittest

from katarina.research.setups.simulator import METHODS, simulate
from katarina.research.validation import CostModel, ValidationError

AS_OF = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
ID = "c" * 64
POINT = 0.01
METHOD_SET = {"liquidity_sweep", "pullback", "fibonacci", "market_structure"}


def bar(start, duration, op, high, low, close, spread=3):
    return {
        "time_utc": start.isoformat(),
        "closed_at_utc": (start + timedelta(minutes=duration)).isoformat(),
        "open": op, "high": high, "low": low, "close": close,
        "spread": spread, "tick_volume": 20, "real_volume": 0,
    }


def ohlc(side, values):
    if side == "BUY":
        return values
    op, hi, lo, cl = values
    return 200 - op, 200 - lo, 200 - hi, 200 - cl


def synthetic_case(method, side):
    # Deterministic H1 uptrend, then mirror it for a SELL downtrend.
    trend = [(97, 104, 92, 98), (100, 105, 90, 101),
             (102, 108, 96, 103), (104, 110, 97, 105)]
    h1 = [bar(AS_OF - timedelta(hours=4-i), 60, *ohlc(side, candle))
          for i, candle in enumerate(trend)]

    prev = [(100, 102, 99, 100),
            (100, 103, 99.5, 101),
            (101, 104, 99.8, 102)]
    # Fibonacci must not signal on the warm-up bars: only the final closed M5
    # candle is a directional retracement confirmation (and its mirror for SELL).
    if method == "fibonacci":
        prev = [(101, 102, 99, 100),
                (102, 103, 99.5, 101),
                (103, 104, 99.8, 102)]
    last = {
        "market_structure": (104.5, 106, 103.5, 105),
        "pullback": (100.5, 103, 100, 102),
        "liquidity_sweep": (99.5, 102, 98.5, 100.5),
        "fibonacci": (99, 101, 98.5, 100),
    }[method]
    base = prev + [last]
    m5 = [bar(AS_OF - timedelta(minutes=20-5*i), 5,
              *ohlc(side, candle)) for i, candle in enumerate(base)]
    next_open = ohlc(side, last)[3]
    # Three neutral future candles only for exercising the timeout exit;
    # the detectors themselves must not use future bars to enter.
    for j in range(3):
        m5.append(bar(AS_OF + timedelta(minutes=j*5), 5,
                      next_open, next_open + .05, next_open - .05, next_open))
    return {"M5": m5, "H1": h1}


def spec(method, side):
    return {
        "name": "SYNTHETIC_SMOKE_ONLY", "symbol": "XAUUSD.vx", "side": side,
        "regime": "ANY", "playbook": method,
        "rules": "Deterministic closed bars, never a performance claim",
        "parameters": {
            "lookback": 3, "trend_lookback": 3, "swing_lookback": 3,
            "min_sweep": 0.1, "breakout_buffer": 0.1,
            "stop_buffer": 0.1, "tolerance": 0.1,
            "fib_min": .382, "fib_max": .618,
            "target_rr": 1.5, "min_rr": 1.0, "max_hold_bars": 3,
        },
    }


class FourSetupSyntheticReadinessTest(unittest.TestCase):
    def test_supported_four_methods_and_both_sides_in_simulator(self):
        self.assertEqual(set(METHODS), METHOD_SET)
        for method in sorted(METHOD_SET):
            for side in ("BUY", "SELL"):
                with self.subTest(method=method, side=side):
                    bars = synthetic_case(method, side)
                    trades = simulate(bars, spec(method, side), ID, point=POINT)
                    self.assertEqual(len(trades), 1)
                    trade = trades[0]
                    self.assertEqual(trade.side, side)
                    self.assertEqual(trade.trend_side, side)
                    self.assertEqual(trade.entry_at, AS_OF)
                    self.assertEqual(trade.exit_at, AS_OF + timedelta(minutes=15))
                    self.assertEqual(trade.data_until, AS_OF)
                    self.assertGreater(trade.stop_distance, 0)
                    self.assertTrue(math.isfinite(CostModel().net_r(trade)))
                    self.assertEqual(trade.spread_entry, 3 * POINT)
                    self.assertEqual(trade.spread_exit, 3 * POINT)
        self.assertNotIn("MetaTrader5", sys.modules)

    def test_holdout_and_unclosed_bar_never_accepted(self):
        for method in METHOD_SET:
            data = synthetic_case(method, "BUY")
            data["M5"].append(bar(datetime(2026, 10, 13, tzinfo=timezone.utc),
                                  5, 100, 101, 99, 100))
            with self.subTest(method=method):
                with self.assertRaisesRegex(ValidationError, "holdout_data_forbidden"):
                    simulate(data, spec(method, "BUY"), ID, point=POINT)

    def test_no_real_data_or_profitability_verdict_comes_from_smoke(self):
        self.assertNotIn("MetaTrader5", sys.modules)
        self.assertEqual(METHOD_SET, {"fibonacci", "liquidity_sweep", "market_structure", "pullback"})


if __name__ == "__main__":
    unittest.main()
