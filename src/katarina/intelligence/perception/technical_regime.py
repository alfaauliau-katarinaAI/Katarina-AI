"""Closed-candle Wilder ADX and research-only market regime diagnostics.

Indicator values are descriptive, not trade signals. Caller validates bar
chronology and OHLC before using this module.
"""
from __future__ import annotations

from math import isfinite


def wilder_adx(bars, period=14):
    """Return latest ADX / +DI / -DI using Wilder's recursive smoothing.

    Initialization uses the first `period` complete true ranges, then the
    first `period` DX values. Never includes an unfinished candle.
    """
    if not isinstance(period, int) or period < 2:
        raise ValueError("invalid_adx_period")
    if len(bars) < 2 * period + 1:
        raise ValueError("insufficient_adx_bars")

    true_ranges = []
    plus_moves = []
    minus_moves = []
    for previous, current in zip(bars[:-1], bars[1:]):
        high, low = float(current["high"]), float(current["low"])
        prior_high, prior_low = float(previous["high"]), float(previous["low"])
        prior_close = float(previous["close"])
        tr = max(high - low, abs(high - prior_close), abs(low - prior_close))
        rise, fall = high - prior_high, prior_low - low
        true_ranges.append(tr)
        plus_moves.append(rise if rise > fall and rise > 0 else 0.0)
        minus_moves.append(fall if fall > rise and fall > 0 else 0.0)

    smoothed_tr = sum(true_ranges[:period])
    smoothed_plus = sum(plus_moves[:period])
    smoothed_minus = sum(minus_moves[:period])
    dx_values = []
    adx_value = None
    plus_di = minus_di = 0.0
    for index in range(period - 1, len(true_ranges)):
        if index >= period:
            smoothed_tr = smoothed_tr - smoothed_tr / period + true_ranges[index]
            smoothed_plus = smoothed_plus - smoothed_plus / period + plus_moves[index]
            smoothed_minus = smoothed_minus - smoothed_minus / period + minus_moves[index]
        plus_di = 100 * smoothed_plus / smoothed_tr if smoothed_tr > 0 else 0.0
        minus_di = 100 * smoothed_minus / smoothed_tr if smoothed_tr > 0 else 0.0
        strength = plus_di + minus_di
        dx = 100 * abs(plus_di - minus_di) / strength if strength > 0 else 0.0
        if adx_value is None:
            dx_values.append(dx)
            if len(dx_values) == period:
                adx_value = sum(dx_values) / period
        else:
            adx_value = (adx_value * (period - 1) + dx) / period

    result = dict(adx14=adx_value, plus_di14=plus_di, minus_di14=minus_di)
    if not all(isfinite(x) and 0 <= x <= 100 + 1e-7 for x in result.values()):
        raise ValueError("invalid_adx_values")
    return result


def classify_market_regime(five):
    """Separate trend hypotheses from range/transition for later validation."""
    adx = five.get("adx14")
    plus = five.get("plus_di14")
    minus = five.get("minus_di14")
    efficiency = five.get("efficiency")
    if not all(isinstance(v, (int, float)) and isfinite(v)
               for v in (adx, plus, minus, efficiency)):
        return "UNKNOWN"
    if adx >= 25 and efficiency >= 0.30:
        if five.get("direction") == "UP" and plus > minus:
            return "TREND_UP"
        if five.get("direction") == "DOWN" and minus > plus:
            return "TREND_DOWN"
    if adx <= 18 and efficiency <= 0.25:
        return "RANGE"
    return "TRANSITION"
