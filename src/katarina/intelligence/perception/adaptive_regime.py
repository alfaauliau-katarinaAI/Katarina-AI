"""KATARINA adaptive market-regime observer v2 — research-only, causal.

This module is additive and never calls a broker, position sizer, or risk governor.
It uses *closed* M5/M15/H1 evidence. Scores are descriptive, not win probabilities.
Unverified reversal and breakout hypotheses are never asserted as facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Mapping


class MarketState(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    SIDEWAYS = "SIDEWAYS"
    PULLBACK_UP = "PULLBACK_UP"
    PULLBACK_DOWN = "PULLBACK_DOWN"
    BREAKOUT_UP = "BREAKOUT_UP"
    BREAKOUT_DOWN = "BREAKOUT_DOWN"
    REVERSAL_UP = "REVERSAL_UP"
    REVERSAL_DOWN = "REVERSAL_DOWN"
    VOLATILITY_SHOCK = "VOLATILITY_SHOCK"
    TRANSITION = "TRANSITION"
    UNKNOWN = "UNKNOWN"


class Playbook(str, Enum):
    TREND_PULLBACK = "TREND_PULLBACK"
    RANGE_FADE = "RANGE_FADE"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"
    REVERSAL_RECLAIM = "REVERSAL_RECLAIM"
    MOMENTUM_CONTINUATION = "MOMENTUM_CONTINUATION"
    OBSERVE = "OBSERVE"


@dataclass(frozen=True)
class ClosedFrame:
    direction: int   # -1, 0, +1 from last closed bar
    adx: float
    efficiency: float   # Kaufman-like directional efficiency [0,1]
    atr: float
    closed_at_utc: datetime


@dataclass(frozen=True)
class StructuralEvidence:
    """Optional verified *closed-bar* price-action signals.

    Directions mean +1 bullish, -1 bearish, 0 absent. No OHLC data -> no
    structural claims. ATR ratio compares realized ATR to prior-only baseline.
    """
    swing_break: int = 0
    swing_reclaim: int = 0
    rejection_direction: int = 0
    atr_ratio: float = 1.0
    spread_to_atr: float = 0.0
    channel_position: float = 0.5


@dataclass(frozen=True)
class MarketRead:
    state: MarketState
    playbook: Playbook
    directional_bias: int
    evidence_strength: float
    volatility_condition: str
    reasons: tuple[str, ...]
    research_only: bool = True
    execution_authorized: bool = False


class AdaptiveRegimeEngine:
    """Causal MTF classifier; never convert evidence strength to profit probability.

    The structural layer is deliberately separate from trend direction and can
    remain unavailable. Entry thresholds belong in a playbook, not the regime.
    """

    @staticmethod
    def _reject(reason: str) -> MarketRead:
        return MarketRead(MarketState.UNKNOWN, Playbook.OBSERVE, 0, 0.0,
                          "UNKNOWN", (reason,))

    @staticmethod
    def _emit(state: MarketState, strength: float, vol: str,
              *reasons: str) -> MarketRead:
        side = 1 if state.value.endswith("_UP") else -1 if state.value.endswith("_DOWN") else 0
        routes = {
            MarketState.TREND_UP: Playbook.TREND_PULLBACK,
            MarketState.TREND_DOWN: Playbook.TREND_PULLBACK,
            MarketState.PULLBACK_UP: Playbook.TREND_PULLBACK,
            MarketState.PULLBACK_DOWN: Playbook.TREND_PULLBACK,
            MarketState.SIDEWAYS: Playbook.RANGE_FADE,
            MarketState.BREAKOUT_UP: Playbook.BREAKOUT_RETEST,
            MarketState.BREAKOUT_DOWN: Playbook.BREAKOUT_RETEST,
            MarketState.REVERSAL_UP: Playbook.REVERSAL_RECLAIM,
            MarketState.REVERSAL_DOWN: Playbook.REVERSAL_RECLAIM,
        }
        return MarketRead(state, routes.get(state, Playbook.OBSERVE),
                          side, round(min(1., max(0., strength)), 4), vol,
                          tuple(reasons))

    def assess(self, *, frames: Mapping[str, ClosedFrame], as_of_utc: datetime,
               structure: StructuralEvidence | None = None) -> MarketRead:
        if as_of_utc.tzinfo is None:
            return self._reject("as_of_timestamp_not_utc_aware")
        if any(k not in frames for k in ("M5", "M15", "H1")):
            return self._reject("missing_required_closed_timeframes")
        f5, f15, fh = (frames[k] for k in ("M5", "M15", "H1"))
        for frame in (f5, f15, fh):
            if (frame.closed_at_utc.tzinfo is None
                    or frame.closed_at_utc.astimezone(timezone.utc) > as_of_utc.astimezone(timezone.utc)):
                return self._reject("future_or_naive_candle")
            if frame.direction not in (-1, 0, 1):
                return self._reject("invalid_direction")
            if not all(isfinite(v) for v in (frame.adx, frame.efficiency, frame.atr)):
                return self._reject("nonfinite_market_data")
            if not (0 <= frame.adx <= 100 and 0 <= frame.efficiency <= 1 and frame.atr > 0):
                return self._reject("invalid_indicator_range")
        e = structure or StructuralEvidence()
        if (any(v not in (-1, 0, 1) for v in
                (e.swing_break, e.swing_reclaim, e.rejection_direction))
                or not all(isfinite(v) for v in (e.atr_ratio, e.spread_to_atr, e.channel_position))
                or e.atr_ratio <= 0 or e.spread_to_atr < 0
                or not 0 <= e.channel_position <= 1):
            return self._reject("invalid_structural_evidence")
        vol = "SHOCK" if e.atr_ratio >= 2.5 else (
            "EXPANSION" if e.atr_ratio >= 1.25 else
            "CONTRACTION" if e.atr_ratio <= .65 else "NORMAL")
        # Require positive *closed* structure for reversal; opposite M5 alone is often pullback.
        if (e.swing_reclaim != 0 and e.rejection_direction == e.swing_reclaim
                and f15.direction == e.swing_reclaim and fh.direction == -e.swing_reclaim):
            state = MarketState.REVERSAL_UP if e.swing_reclaim > 0 else MarketState.REVERSAL_DOWN
            return self._emit(state, .55 + .20 * f15.efficiency, vol,
                              "verified_swing_reclaim", "rejection", "higher_tf_opposed")
        if (e.swing_break != 0 and f5.direction == e.swing_break
                and e.atr_ratio >= 1.10 and f5.efficiency >= .30):
            state = MarketState.BREAKOUT_UP if e.swing_break > 0 else MarketState.BREAKOUT_DOWN
            return self._emit(state, .55 + .25 * f5.efficiency, vol,
                              "closed_swing_break", "range_expansion")
        if vol == "SHOCK":
            return self._emit(MarketState.VOLATILITY_SHOCK, .35, vol,
                              "unconfirmed_volatility_shock")
        longer_trend = (fh.direction != 0 and fh.direction == f15.direction
                        and (fh.efficiency >= .22 or fh.adx >= 20)
                        and (f15.efficiency >= .23 or f15.adx >= 20))
        if longer_trend:
            long_dir = fh.direction
            if f5.direction == -long_dir and f5.efficiency >= .18:
                state = MarketState.PULLBACK_UP if long_dir > 0 else MarketState.PULLBACK_DOWN
                return self._emit(state, .46 + .23 * fh.efficiency, vol,
                                  "aligned_h1_m15", "opposing_m5_pullback")
            state = MarketState.TREND_UP if long_dir > 0 else MarketState.TREND_DOWN
            return self._emit(state, .51 + .25 * (fh.efficiency + f15.efficiency) / 2,
                              vol, "aligned_h1_m15", "directional_continuation")
        # Two weak frames are enough for a range *context*, not a guaranteed bounce.
        weak = sum((f5.efficiency <= .26 or f5.adx < 18,
                    f15.efficiency <= .28 or f15.adx < 18,
                    fh.efficiency <= .20 or fh.adx < 16))
        if weak >= 2 and e.swing_break == 0:
            return self._emit(MarketState.SIDEWAYS, .42 + .1 * weak, vol,
                              "multi_frame_low_directional_efficiency")
        # Avoid calling every disagreement a reversal.
        return self._emit(MarketState.TRANSITION, .30, vol, "conflicting_mtf_without_structure")


def from_archived_frames(symbol: str, frames: Mapping[str, Mapping[str, object]],
                         time_utc: str) -> tuple[dict[str, ClosedFrame], datetime]:
    """Strict adapter for KATARINA archived diagnostics; no future target read."""
    instant = datetime.fromisoformat(time_utc.replace("Z", "+00:00"))
    result = {}
    for k in ("M5", "M15", "H1"):
        f = frames[k]
        direction = {"UP": 1, "DOWN": -1, "MIXED": 0, "NONE": 0}.get(str(f["direction"]), 0)
        # Archived diagnostic records all three frames as closed as of decision time.
        result[k] = ClosedFrame(direction, float(f["adx14"]),
                                float(f["efficiency"]), float(f["atr"]), instant)
    return result, instant
