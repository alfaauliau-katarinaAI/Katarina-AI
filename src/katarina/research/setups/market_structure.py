"""WP8b confirmed M5 close-break of prior closed-bar structure."""
from .core import checked_side, closed_bars, param, signal, trend


def detect(bars_by_tf, as_of, params, side):
    checked_side(side)
    n = param(params, "lookback", integer=True, low=2)
    excess = param(params, "breakout_buffer", low=0)
    buffer = param(params, "stop_buffer", low=0.0000001)
    direction, regime = trend(bars_by_tf, as_of, params)
    if direction != side:
        return []
    bars = closed_bars(bars_by_tf, "M5", as_of, n + 1, 5)
    if len(bars) < n + 1:
        return []
    prev, last = bars[:-1], bars[-1]
    if side == "BUY":
        if not last["close"] > max(x["high"] for x in prev) + excess:
            return []
        stop = min(x["low"] for x in prev) - buffer
    else:
        if not last["close"] < min(x["low"] for x in prev) - excess:
            return []
        stop = max(x["high"] for x in prev) + buffer
    return signal("market_structure", side, as_of, last, stop, params, direction, regime)
