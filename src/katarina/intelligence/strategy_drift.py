"""Deterministic strategy drift monitor over durable SHADOW/PAPER results.

No trading orders, no optimization and no live authorization. If forward
evidence is missing or deteriorates, only NO_TRADE may be returned.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from katarina.intelligence.shadow_journal import ShadowJournal, _utc
from katarina.intelligence.strategy_evidence import (
    ForwardStrategyEvidenceGate,
)


@dataclass(frozen=True, slots=True)
class StrategyDriftDecision:
    state: str  # NO_TRADE or RISK_REVIEW_ONLY
    reason: str
    risk_multiplier: float
    eligible_observations: int
    live_execution_authorized: bool = False


class StrategyDriftMonitor:
    def __init__(self, *, gate: ForwardStrategyEvidenceGate | None = None,
                 recent_trades: int = 12, max_staleness_days: int = 21,
                 max_consecutive_losses: int = 5,
                 max_explicit_cost_r: float = .20):
        if recent_trades < 8 or max_staleness_days < 1 or max_consecutive_losses < 2:
            raise ValueError("invalid_drift_parameters")
        if not isfinite(max_explicit_cost_r) or max_explicit_cost_r <= 0:
            raise ValueError("invalid_cost_threshold")
        self.gate = gate or ForwardStrategyEvidenceGate()
        self.recent_trades = recent_trades
        self.max_staleness_days = max_staleness_days
        self.max_consecutive_losses = max_consecutive_losses
        self.max_explicit_cost_r = max_explicit_cost_r

    @staticmethod
    def _deny(reason: str, count: int = 0) -> StrategyDriftDecision:
        return StrategyDriftDecision("NO_TRADE", reason, 0., count)

    def review(self, *, journal: ShadowJournal,
               symbol: str, strategy_id: str, strategy_version: str,
               frozen_at_utc: datetime, as_of_utc: datetime) -> StrategyDriftDecision:
        try:
            now = _utc(as_of_utc)
            frozen = _utc(frozen_at_utc)
        except ValueError:
            return self._deny("unverified_timestamp")
        if not symbol or not strategy_id or not strategy_version:
            return self._deny("missing_strategy_version")
        relevant_signals = [
            s for s in journal._signals.values()
            if s.symbol == symbol and s.strategy_id == strategy_id
            and s.strategy_version == strategy_version and s.action == "ACCEPT"
        ]
        if any(_utc(s.frozen_at_utc) != frozen for s in relevant_signals):
            return self._deny("mixed_or_changed_strategy_freeze")
        outcomes = journal.forward_outcomes(
            symbol=symbol, strategy_id=strategy_id,
            strategy_version=strategy_version)
        if any(t.closed_at_utc > now for t in outcomes):
            return self._deny("future_forward_close")
        eligible = [t for t in outcomes if frozen < t.closed_at_utc <= now]
        count = len(eligible)
        evidence = self.gate.assess(
            symbol=symbol, strategy_id=strategy_id,
            frozen_at_utc=frozen, as_of_utc=now, trades=outcomes)
        if not evidence.eligible_for_risk_review:
            return self._deny(evidence.reason, count)
        recent = sorted(eligible, key=lambda x: x.closed_at_utc)[-self.recent_trades:]
        if len(recent) < self.recent_trades:
            return self._deny("insufficient_recent_trades", count)
        if now - recent[-1].closed_at_utc > timedelta(days=self.max_staleness_days):
            return self._deny("stale_strategy_evidence", count)
        streak = 0
        for row in reversed(recent):
            if row.net_r < 0:
                streak += 1
            else:
                break
        if streak >= self.max_consecutive_losses:
            return self._deny("recent_loss_streak", count)
        if sum(t.net_r for t in recent) <= 0:
            return self._deny("negative_recent_net_expectancy", count)
        # Explicit costs here exclude implicit spread already included in gross.
        # If actual spread/fees are not attested, forward evidence is denied
        # earlier by ForwardStrategyEvidenceGate.
        for close in journal._closes.values():
            parent = journal._signals[close.signal_id]
            if (parent.symbol != symbol or parent.strategy_id != strategy_id
                    or parent.strategy_version != strategy_version
                    or not frozen < close.closed_at_utc <= now):
                continue
            cost_r = (-close.commission_account - close.swap_account
                      + close.slippage_cost_account) / close.initial_risk_account
            if not isfinite(cost_r) or cost_r > self.max_explicit_cost_r:
                return self._deny("excessive_verified_trading_cost", count)
        return StrategyDriftDecision(
            "RISK_REVIEW_ONLY", "forward_edge_and_recent_costs_within_limits",
            evidence.risk_multiplier, count)
