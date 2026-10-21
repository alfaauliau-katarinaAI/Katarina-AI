"""Forward-only strategy evidence monitor for KATARINA.

This module NEVER creates broker orders, estimates a win probability, or
authorizes real-money trading. It lets a strategy reach the existing risk
review ONLY after a pre-frozen strategy survives cost-verified PAPER/DEAL
observations. Replayed 2025/2026 data previously inspected are NOT forward
evidence.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from random import Random
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ClosedStrategyTrade:
    trade_id: str
    symbol: str
    strategy_id: str
    closed_at_utc: datetime
    net_r: float
    provenance: str  # PAPER or BROKER_DEAL; historical optimization is excluded
    costs_verified: bool  # spread, slippage and commission in net_r


@dataclass(frozen=True, slots=True)
class StrategyEvidenceDecision:
    eligible_for_risk_review: bool
    reason: str
    risk_multiplier: float
    forward_trades: int
    forward_mean_r: float
    lower_95pct_mean_r: float
    profit_factor: float
    max_realized_drawdown_r: float
    live_authorized: bool = False


class ForwardStrategyEvidenceGate:
    """Conservative, deterministic week-block bootstrap on *new* trades.

    A candidate must be explicitly frozen before the evaluation observations.
    Return values NEVER override broker sizing, SL, drawdown or live approval.
    The bootstrap is a stability screen, not a future-return guarantee.
    """

    def __init__(
        self,
        *,
        minimum_trades: int = 40,
        minimum_weeks: int = 12,
        minimum_months: int = 4,
        minimum_losing_trades: int = 5,
        minimum_profit_factor: float = 1.20,
        maximum_drawdown_r: float = 12.0,
        bootstrap_draws: int = 1000,
    ):
        if (minimum_trades < 10 or minimum_weeks < 4 or
                minimum_months < 2 or minimum_losing_trades < 1 or
                not isfinite(minimum_profit_factor) or minimum_profit_factor <= 1 or
                not isfinite(maximum_drawdown_r) or maximum_drawdown_r <= 0 or
                bootstrap_draws < 200):
            raise ValueError("invalid_forward_evidence_thresholds")
        self.minimum_trades = minimum_trades
        self.minimum_weeks = minimum_weeks
        self.minimum_months = minimum_months
        self.minimum_losing_trades = minimum_losing_trades
        self.minimum_profit_factor = minimum_profit_factor
        self.maximum_drawdown_r = maximum_drawdown_r
        self.bootstrap_draws = bootstrap_draws

    @staticmethod
    def _aware(value: datetime) -> bool:
        return isinstance(value, datetime) and (
            value.tzinfo is not None and value.utcoffset() is not None)

    @staticmethod
    def _deny(reason: str, *, count: int = 0, mean: float = 0.,
              lower: float = 0., pf: float = 0.,
              max_dd: float = 0.) -> StrategyEvidenceDecision:
        return StrategyEvidenceDecision(False, reason, 0., count,
                                         mean, lower, pf, max_dd)

    def assess(
        self,
        *,
        symbol: str,
        strategy_id: str,
        frozen_at_utc: datetime,
        as_of_utc: datetime,
        trades: Sequence[ClosedStrategyTrade],
    ) -> StrategyEvidenceDecision:
        if (not symbol or not strategy_id or
                not self._aware(frozen_at_utc) or not self._aware(as_of_utc)):
            return self._deny("unverified_strategy_identity_or_time")
        frozen = frozen_at_utc.astimezone(timezone.utc)
        now = as_of_utc.astimezone(timezone.utc)
        if frozen >= now:
            return self._deny("strategy_not_frozen_before_observation")
        if not trades:
            return self._deny("no_forward_trades")
        seen: set[str] = set()
        verified = []
        for trade in trades:
            try:
                valid_return = isfinite(float(trade.net_r))
            except (TypeError, ValueError, OverflowError):
                valid_return = False
            if (not trade.trade_id or trade.trade_id in seen or
                    trade.symbol != symbol or trade.strategy_id != strategy_id or
                    not self._aware(trade.closed_at_utc) or
                    not valid_return):
                return self._deny("invalid_duplicate_or_mismatched_trade")
            seen.add(trade.trade_id)
            instant = trade.closed_at_utc.astimezone(timezone.utc)
            if instant > now:
                return self._deny("future_trade_leakage")
            if instant <= frozen:
                # Previous optimization-period trades are not forward evidence.
                continue
            if trade.provenance not in ("PAPER", "BROKER_DEAL") or not trade.costs_verified:
                return self._deny("unverified_forward_provenance_or_costs")
            verified.append((instant, float(trade.net_r)))
        verified.sort(key=lambda x: x[0])
        n = len(verified)
        if n < self.minimum_trades:
            return self._deny("insufficient_forward_trades", count=n)

        weekblocks: dict[tuple[int, int], list[float]] = defaultdict(list)
        months = set()
        pos = neg = 0.
        losses = 0
        peak = pnl = max_dd = 0.
        for instant, value in verified:
            year, week, _ = instant.isocalendar()
            weekblocks[(year, week)].append(value)
            months.add((instant.year, instant.month))
            pos += max(value, 0.)
            neg += -min(value, 0.)
            losses += value < 0
            pnl += value
            peak = max(peak, pnl)
            max_dd = max(max_dd, peak - pnl)
        mean = pnl / n
        pf = pos / neg if neg > 0 else 0.
        if (len(weekblocks) < self.minimum_weeks or
                len(months) < self.minimum_months or
                losses < self.minimum_losing_trades):
            return self._deny("insufficient_independent_forward_coverage",
                              count=n, mean=mean, pf=pf, max_dd=max_dd)
        if mean <= 0 or pf < self.minimum_profit_factor or max_dd > self.maximum_drawdown_r:
            return self._deny("poor_forward_expectancy_or_drawdown",
                              count=n, mean=mean, pf=pf, max_dd=max_dd)

        # Sample whole calendar weeks, preserving same-week trade dependence.
        blocks = list(weekblocks.values())
        random = Random(20261011)
        means = []
        for _ in range(self.bootstrap_draws):
            sample = [v for _week in range(len(blocks))
                      for v in blocks[random.randrange(len(blocks))]]
            means.append(sum(sample) / len(sample))
        means.sort()
        lower = means[int(.025 * len(means))]
        if lower <= 0:
            return self._deny("forward_confidence_interval_includes_zero",
                              count=n, mean=mean, lower=lower, pf=pf, max_dd=max_dd)

        # The evidence gate can only SHRINK a separately approved risk budget.
        quality_fraction = min(.75, max(.10, lower / mean))
        return StrategyEvidenceDecision(
            True, "forward_paper_evidence_for_risk_review_only",
            quality_fraction, n, mean, lower, pf, max_dd)
