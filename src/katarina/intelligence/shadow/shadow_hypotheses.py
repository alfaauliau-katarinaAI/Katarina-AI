"""Pre-registered, read-only market-regime hypotheses (not order signals).

Every tested candle must be fully closed. Shadow entries are observed after
the close with current bid/ask, never at an unknowable historical candle fill.
No strategy in this module is authorized for live execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from statistics import mean

FAMILY = "trend_impulse_break_v1"
LOOKBACK = 6
MIN_VOLUME_RATIO = 1.25
MIN_BODY_FRACTION = 0.60
BREAK_ATR = 0.05
MAX_CANDLE_ATR = 3.0


def propose(row):
    """Return zero or one bounded trend hypothesis from closed M1/M5 evidence.

    Range, transition, unknown and unvalidated market conditions abstain.
    The scanner is allowed to observe the hypothesis even when macro context
    blocks it, so filtering can be studied later without retroactive labels.
    """
    one, five = row.get("m1"), row.get("m5")
    bars = row.get("m1_bars")
    if not isinstance(one, dict) or not isinstance(five, dict):
        return []
    if not isinstance(bars, list) or len(bars) < 30:
        return []
    regime = row.get("regime_detail")
    if regime not in ("TREND_UP", "TREND_DOWN"):
        return []
    side = "BUY" if regime == "TREND_UP" else "SELL"
    if side not in row.get("allowed_sides", ()):
        return []
    if not 0 <= one.get("close_age_seconds", float("inf")) <= 90:
        return []
    atr = float(one.get("atr", 0))
    if not isfinite(atr) or atr <= 0:
        return []
    candle = bars[-1]
    try:
        o, h, l, c = (float(candle[k]) for k in ("open", "high", "low", "close"))
        tick = float(candle["tick_volume"])
        baseline = mean(float(b["tick_volume"]) for b in bars[-21:-1])
        previous_high = max(float(b["high"]) for b in bars[-LOOKBACK-1:-1])
        previous_low = min(float(b["low"]) for b in bars[-LOOKBACK-1:-1])
        bar_open_time = int(candle["time"])
        ema = float(one["ema20"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return []
    if not all(isfinite(v) for v in (o,h,l,c,tick,baseline,previous_high,previous_low,ema)):
        return []
    width = h-l
    if not (0 < width <= MAX_CANDLE_ATR*atr and baseline > 0):
        return []
    body_fraction = abs(c-o)/width
    volume_ratio = tick/baseline
    if body_fraction < MIN_BODY_FRACTION or volume_ratio < MIN_VOLUME_RATIO:
        return []
    if side == "BUY":
        matched = (c > o and c >= h-0.25*width and
                   c > previous_high + BREAK_ATR*atr and c > ema)
    else:
        matched = (c < o and c <= l+0.25*width and
                   c < previous_low - BREAK_ATR*atr and c < ema)
    if not matched:
        return []
    # Broker quotes and actual costs are evaluated elsewhere. This is not R.
    return [dict(family=FAMILY, side=side,
                 signal_bar_close_utc=datetime.fromtimestamp(bar_open_time+60,
                                        timezone.utc).isoformat(),
                 bar_body_fraction=round(body_fraction, 6),
                 volume_ratio=round(volume_ratio, 6),
                 breakout_atr=round(((c-previous_high) if side=="BUY"
                                     else (previous_low-c))/atr, 6),
                 regime=regime, research_only=True,
                 live_risk_authorized=False)]
