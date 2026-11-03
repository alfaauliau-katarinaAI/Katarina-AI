"""WP8b H1-trend / M5-mean pullback hypothesis, closed bars only."""
from .core import checked_side, closed_bars, param, signal, trend


def detect(bars_by_tf, as_of, params, side):
    checked_side(side)
    n = param(params, "lookback", integer=True, low=2)
    tolerance = param(params, "tolerance", low=0)
    buffer = param(params, "stop_buffer", low=0.0000001)
    direction, regime = trend(bars_by_tf, as_of, params)
    if direction != side:
        return []
    bars = closed_bars(bars_by_tf, "M5", as_of, n + 1, 5)
    if len(bars) < n + 1:
        return []
    prev, last = bars[:-1], bars[-1]
    mean = sum(x["close"] for x in prev) / len(prev)
    if side == "BUY":
        if not (last["low"] <= mean + tolerance
                and last["close"] > mean and last["close"] > last["open"]):
            return []
        stop = min(x["low"] for x in bars) - buffer
    else:
        if not (last["high"] >= mean - tolerance
                and last["close"] < mean and last["close"] < last["open"]):
            return []
        stop = max(x["high"] for x in bars) + buffer
    return signal("pullback", side, as_of, last, stop, params, direction, regime)
