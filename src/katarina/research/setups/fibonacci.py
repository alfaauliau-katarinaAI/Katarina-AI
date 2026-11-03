"""WP8b causal Fibonacci retracement using a past H1 range, no future pivot."""
from .core import checked_side, closed_bars, param, signal, trend


def detect(bars_by_tf, as_of, params, side):
    checked_side(side)
    n = param(params, "swing_lookback", integer=True, low=3)
    low_ratio = param(params, "fib_min", low=0, upper=1)
    high_ratio = param(params, "fib_max", low=0, upper=1)
    buffer = param(params, "stop_buffer", low=0.0000001)
    if not low_ratio < high_ratio:
        return []
    direction, regime = trend(bars_by_tf, as_of, params)
    if direction != side:
        return []
    h1 = closed_bars(bars_by_tf, "H1", as_of, n, 60)
    m5 = closed_bars(bars_by_tf, "M5", as_of, 1, 5)
    if len(h1) != n or not m5:
        return []
    hi = max(x["high"] for x in h1)
    lo = min(x["low"] for x in h1)
    width = hi - lo
    if width <= 0:
        return []
    last = m5[-1]
    if side == "BUY":
        band_lo, band_hi = hi - width * high_ratio, hi - width * low_ratio
        if not (band_lo <= last["close"] <= band_hi and last["close"] > last["open"]):
            return []
        stop = lo - buffer
    else:
        band_lo, band_hi = lo + width * low_ratio, lo + width * high_ratio
        if not (band_lo <= last["close"] <= band_hi and last["close"] < last["open"]):
            return []
        stop = hi + buffer
    return signal("fibonacci", side, as_of, last, stop, params, direction, regime)
