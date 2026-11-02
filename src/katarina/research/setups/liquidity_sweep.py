"""WP8b liquidity-sweep hypothesis: wick through prior closed range, reversal."""
from .core import checked_side, closed_bars, param, signal, trend


def detect(bars_by_tf, as_of, params, side):
    checked_side(side)
    n = param(params, "lookback", integer=True, low=2)
    sweep = param(params, "min_sweep", low=0)
    buffer = param(params, "stop_buffer", low=0.0000001)
    direction, regime = trend(bars_by_tf, as_of, params)
    bars = closed_bars(bars_by_tf, "M5", as_of, n + 1, 5)
    if len(bars) < n + 1:
        return []
    past, last = bars[:-1], bars[-1]
    if side == "BUY":
        level = min(x["low"] for x in past)
        if not (last["low"] < level - sweep and last["close"] > level
                and last["close"] > last["open"]):
            return []
        stop = last["low"] - buffer
    else:
        level = max(x["high"] for x in past)
        if not (last["high"] > level + sweep and last["close"] < level
                and last["close"] < last["open"]):
            return []
        stop = last["high"] + buffer
    return signal("liquidity_sweep", side, as_of, last, stop, params, direction, regime)
