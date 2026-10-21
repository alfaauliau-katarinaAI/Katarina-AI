"""Adaptive playbook suggestions for KATARINA scalper. No broker execution.

Compact price action, regime and existing hard protections; RSI/BB/VWAP/ADX
are deliberately NOT mandatory entry confirmations. No risk code is modified.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from katarina.intelligence.perception.adaptive_regime import MarketRead, MarketState, Playbook


class ScalpSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


@dataclass(frozen=True)
class ClosedPriceContext:
    open: float
    high: float
    low: float
    close: float
    previous_close: float
    previous_channel_high: float  # strictly prior closed bars; excludes current
    previous_channel_low: float
    atr: float
    spread_to_atr: float
    data_fresh: bool
    broker_session_open: bool
    news_blackout: bool = False


@dataclass(frozen=True)
class ResearchEntryPlan:
    symbol: str
    state: MarketState
    strategy: Playbook
    side: ScalpSide
    ready_for_research: bool
    evidence: tuple[str, ...]
    seasonality_tilt: float
    research_only: bool = True
    live_risk_authorized: bool = False


class AdaptiveScalpRouter:
    """One regime -> one playbook; technical vetoes limited to necessary checks.

    Always call the authoritative broker/risk/exposure governors later in the
    execution path. Returning a research suggestion does not authorize orders.
    """

    def __init__(self, max_spread_atr: float = .42):
        if not 0 < max_spread_atr < 1:
            raise ValueError("invalid cost threshold")
        self.max_spread_atr = max_spread_atr

    @staticmethod
    def _wait(symbol: str, state: MarketState, strategy: Playbook, reason: str, tilt: float):
        return ResearchEntryPlan(symbol, state, strategy, ScalpSide.WAIT, False,
                                 (reason,), tilt)

    def plan(self, symbol: str, regime: MarketRead, candle: ClosedPriceContext,
             *, seasonality_tilt: float = 0.0) -> ResearchEntryPlan:
        if not symbol:
            raise ValueError("missing symbol")
        if not isfinite(seasonality_tilt) or not -.10 <= seasonality_tilt <= .10:
            raise ValueError("invalid seasonal modifier")
        state, mode = regime.state, regime.playbook
        def wait(reason: str):
            return self._wait(symbol, state, mode, reason, seasonality_tilt)
        values = (candle.open,candle.high,candle.low,candle.close,candle.previous_close,
                  candle.previous_channel_high,candle.previous_channel_low,candle.atr,candle.spread_to_atr)
        if not all(isfinite(x) for x in values):
            return wait("invalid_nonfinite_price")
        if (candle.atr <= 0 or candle.spread_to_atr < 0 or
                candle.low > min(candle.open,candle.close) or
                candle.high < max(candle.open,candle.close) or
                candle.previous_channel_high <= candle.previous_channel_low):
            return wait("invalid_market_geometry")
        if not candle.data_fresh or not candle.broker_session_open:
            return wait("market_not_currently_tradable")
        if candle.news_blackout:
            return wait("high_impact_news_blackout")
        if candle.spread_to_atr > self.max_spread_atr:
            return wait("spread_too_wide_relative_to_atr")
        if mode is Playbook.OBSERVE:
            return wait("regime_not_structurally_resolved")

        side = regime.directional_bias
        candle_body = 1 if candle.close > candle.open else -1 if candle.close < candle.open else 0
        price_change = 1 if candle.close > candle.previous_close else -1 if candle.close < candle.previous_close else 0
        channel_width = candle.previous_channel_high - candle.previous_channel_low
        where = (candle.close - candle.previous_channel_low) / channel_width
        # Soft context only: seasonality never overrides trade direction.
        reasons = [state.value.lower(), "closed_bar_price_action"]
        if abs(seasonality_tilt) > .005:
            reasons.append("past_known_hour_weekday_context_not_signal")

        if mode is Playbook.RANGE_FADE:
            low_zone = where <= .30
            high_zone = where >= .70
            lower_rejection = candle.low < candle.previous_channel_low and candle.close > candle.low
            upper_rejection = candle.high > candle.previous_channel_high and candle.close < candle.high
            if low_zone and (candle_body > 0 or lower_rejection or price_change > 0):
                side = 1
            elif high_zone and (candle_body < 0 or upper_rejection or price_change < 0):
                side = -1
            else:
                return wait("wait_for_channel_edge_rejection")
            reasons.append("range_edge_rejection")
        elif mode is Playbook.TREND_PULLBACK:
            # A quick reclaim or in-direction close is enough; no simultaneous
            # RSI/ADX/EMA/BB/VWAP checklist.
            if side not in (-1,1):
                return wait("trend_side_unknown")
            bounce = candle_body == side or price_change == side
            if not bounce:
                return wait("waiting_for_price_confirmation")
            reasons.append("trend_pullback_or_continuation")
        elif mode is Playbook.BREAKOUT_RETEST:
            # Wait for *closed* break confirmation; no intrabar repainting.
            broken = (candle.close > candle.previous_channel_high) if side > 0 else (
                      candle.close < candle.previous_channel_low)
            if not broken or (candle_body != side and price_change != side):
                return wait("waiting_for_closed_breakout")
            reasons.append("confirmed_structural_breakout")
        elif mode is Playbook.REVERSAL_RECLAIM:
            if candle_body != side and price_change != side:
                return wait("waiting_for_reclaim_confirmation")
            reasons.append("structure_reclaim_direction_confirmed")
        else:
            return wait("unsupported_playbook")
        final_side = ScalpSide.BUY if side > 0 else ScalpSide.SELL
        return ResearchEntryPlan(symbol, state, mode, final_side, True,
                                 tuple(reasons), seasonality_tilt)
