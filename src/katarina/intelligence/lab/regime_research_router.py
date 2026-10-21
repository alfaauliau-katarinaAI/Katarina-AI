"""Fail-closed market-context selector for RESEARCH alerts, never broker instructions.

This module deliberately has no MetaTrader5 dependency, order method, strategy
promotion flag, or live authorization surface. It does not calculate the features:
upstream must use causally closed bar and verified news/quote inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite


@dataclass(frozen=True)
class ObservedMarketContext:
    symbol: str
    now_utc: datetime
    latest_closed_m5_utc: datetime
    market_open: bool = False
    quote_age_seconds: float | None = None
    h1_adx_closed: float | None = None
    vwap_reclaim_side: int = 0
    donchian24_breakout_side: int = 0
    news_cleared: bool = False
    broker_costs_verified: bool = False
    estimated_total_cost_r: float | None = None
    active_portfolio_positions: int | None = None
    source_is_replay_or_paper: bool = True


@dataclass(frozen=True)
class ContextDecision:
    broker_action: str
    shadow_candidate: str | None
    shadow_side: str | None
    reasons: tuple[str, ...]
    risk_fraction_for_paper_model: float
    live_authorized: bool


GOLD_ID = "XAUUSD_VWAP_RECLAIM_ADX25_M5_RR1P5_3H_RESEARCH_20261011"
JPN_ID = "JPN225_DONCHIAN24_LOW_ADX18_M5_RR2_3H_RESEARCH_20261011"


def select_shadow_context(ctx: ObservedMarketContext) -> ContextDecision:
    """Return a research-only idea or NO_TRADE; never permits live broker action."""
    def deny(reason: str) -> ContextDecision:
        return ContextDecision("NO_TRADE", None, None, (reason,), 0.0, False)

    if ctx.now_utc.tzinfo is None or ctx.latest_closed_m5_utc.tzinfo is None:
        return deny("timezone_unverified")
    now = ctx.now_utc.astimezone(timezone.utc)
    closed = ctx.latest_closed_m5_utc.astimezone(timezone.utc)
    age = (now-closed).total_seconds()
    if not 0 <= age <= 600:
        return deny("closed_m5_missing_or_stale")
    if not ctx.source_is_replay_or_paper:
        return deny("not_research_or_paper_source")
    if not ctx.market_open or ctx.quote_age_seconds is None:
        return deny("market_or_quote_unknown")
    if not isfinite(ctx.quote_age_seconds) or not 0 <= ctx.quote_age_seconds <= 15:
        return deny("stale_quote")
    if not ctx.news_cleared:
        return deny("unverified_news_clearance")
    if not ctx.broker_costs_verified or ctx.estimated_total_cost_r is None:
        return deny("unverified_broker_costs")
    if not isfinite(ctx.estimated_total_cost_r) or not 0 <= ctx.estimated_total_cost_r <= 0.10:
        return deny("cost_too_high_or_unknown")
    if ctx.active_portfolio_positions is None or ctx.active_portfolio_positions != 0:
        return deny("unreconciled_or_open_portfolio_exposure")
    if ctx.h1_adx_closed is None or not isfinite(ctx.h1_adx_closed):
        return deny("closed_h1_regime_unknown")
    hour = now.hour
    if ctx.symbol == "XAUUSD.vx":
        if not 6 <= hour < 9:
            return deny("outside_gold_utc_session")
        if ctx.h1_adx_closed < 25:
            return deny("not_gold_trending_regime")
        side = ctx.vwap_reclaim_side
        if side not in (-1, 1):
            return deny("no_closed_gold_vwap_signal")
        sid = GOLD_ID
    elif ctx.symbol == "JPN225.vx":
        if not 12 <= hour < 15:
            return deny("outside_jpn_utc_session")
        if ctx.h1_adx_closed > 18:
            return deny("not_jpn_low_adx_regime")
        side = ctx.donchian24_breakout_side
        if side not in (-1, 1):
            return deny("no_closed_jpn_donchian_signal")
        sid = JPN_ID
    else:
        return deny("unvalidated_symbol")
    # Research route only. Even a valid context does not equal statistically valid alpha.
    return ContextDecision(
        broker_action="NO_TRADE",
        shadow_candidate=sid,
        shadow_side="BUY" if side == 1 else "SELL",
        reasons=("historical_research_context_only", "forward_alpha_unverified"),
        risk_fraction_for_paper_model=0.005,
        live_authorized=False,
    )
