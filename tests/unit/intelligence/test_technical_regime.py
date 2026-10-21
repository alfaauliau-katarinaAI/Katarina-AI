"""Causal market-regime diagnostics; no strategy promotion."""
import json
import unittest
from datetime import datetime, timezone

from katarina.intelligence.perception.technical_regime import (
    classify_market_regime, wilder_adx,
)
from katarina.intelligence.perception.screening import features, screen

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


def bars(kind, seconds=300, n=120):
    end = int(NOW.timestamp()) - seconds
    output = []
    for i in range(n):
        if kind == "UP":
            price = 100 + i * 0.2
        elif kind == "DOWN":
            price = 130 - i * 0.2
        elif kind == "RANGE":
            price = 115 + (0.4 if i % 2 else -0.4)
        elif kind == "FLAT":
            price = 100
        else:
            raise ValueError(kind)
        output.append(dict(time=end-(n-i-1)*seconds,
                           open=price, high=price+0.5,
                           low=price-0.5, close=price,
                           tick_volume=100+i%9))
    return output


class Context:
    def assess(self, currencies, now):
        return {"ready": True, "reasons": []}


class RegimeTests(unittest.TestCase):
    def test_directional_trend_strength(self):
        for kind, expected in (("UP", "TREND_UP"), ("DOWN", "TREND_DOWN")):
            with self.subTest(kind=kind):
                computed = features(bars(kind), 300, NOW)
                self.assertGreater(computed["adx14"], 90)
                self.assertGreater(computed["efficiency"], 0.95)
                dominant = "plus_di14" if kind == "UP" else "minus_di14"
                opposite = "minus_di14" if kind == "UP" else "plus_di14"
                self.assertGreater(computed[dominant], computed[opposite])
                self.assertEqual(classify_market_regime(computed), expected)

    def test_range_classification(self):
        computed = features(bars("RANGE"), 300, NOW)
        self.assertLessEqual(computed["adx14"], 18)
        self.assertLessEqual(computed["efficiency"], 0.25)
        self.assertEqual(classify_market_regime(computed), "RANGE")

    def test_technical_values_are_scale_invariant(self):
        source = bars("UP")
        scaled = [{k:(v*0.01 if k in ("open","high","low","close") else v)
                   for k,v in b.items()} for b in source]
        original, smaller = wilder_adx(source), wilder_adx(scaled)
        for key in original:
            self.assertAlmostEqual(original[key], smaller[key], places=8)

    def test_flat_directional_movement_is_zero(self):
        values = wilder_adx(bars("FLAT"))
        self.assertEqual(values, dict(adx14=0.0, plus_di14=0.0, minus_di14=0.0))

    def test_insufficient_closed_bars_rejected(self):
        with self.assertRaises(ValueError):
            wilder_adx(bars("UP", n=20))

    def test_unknown_regime_fail_closed(self):
        self.assertEqual(classify_market_regime(dict(adx14=float("nan"),
            plus_di14=20, minus_di14=20, efficiency=0.5)), "UNKNOWN")
        self.assertEqual(classify_market_regime(dict()), "UNKNOWN")

    def test_bad_tick_volume_rejected(self):
        for value in (float("nan"), float("inf"), -1):
            data = bars("UP")
            data[-1]["tick_volume"] = value
            with self.assertRaisesRegex(ValueError, "invalid_tick_volume"):
                features(data, 300, NOW)

    def test_screen_is_research_only(self):
        m1 = features(bars("UP", seconds=60), 60, NOW)
        m5 = features(bars("UP"), 300, NOW)
        row = dict(symbol="TEST", base="EUR", profit="USD", trade_mode=4,
                   connected=True, tick_time=NOW.timestamp(), bid=123.8,
                   ask=123.82, errors=[], m1=m1, m5=m5)
        survey = screen([row], Context(), NOW)
        self.assertEqual(survey["symbols"][0]["regime_detail"], "TREND_UP")
        self.assertEqual(survey["symbols"][0]["action"], "NO_TRADE")
        self.assertFalse(survey["live_execution_enabled"])
        self.assertFalse(survey["symbols"][0]["live_risk_authorized"])
        json.dumps(survey, allow_nan=False)
        row["tick_time"] -= 31
        stale = screen([row], Context(), NOW)["symbols"][0]
        self.assertEqual(stale["regime_detail"], "UNKNOWN")
        self.assertFalse(stale["research_candidate"])


if __name__ == "__main__":
    unittest.main()
