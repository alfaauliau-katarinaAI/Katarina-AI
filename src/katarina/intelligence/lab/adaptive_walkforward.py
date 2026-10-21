"""Causal adaptive research selector; never connects to a broker.

The replay learns ONLY from completed, previously known paper outcomes.
Existing V6 outcomes are historically inspected, so no independent OOS
or strategy profitability claim follows from this simulation.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
import heapq
from math import isfinite, sqrt
from statistics import mean, pstdev
from typing import Iterable

from katarina.intelligence.broker.broker_scan_universe import CROSSES, MAJORS


@dataclass(frozen=True)
class PaperEvent:
    """A paper opportunity with a *retrospective* modeled outcome.

    At decision time, only properties other than modeled_r/exit_time may
    influence selection. modeled_r becomes visible once exit_time is past.
    """
    symbol: str
    strategy_id: str
    side: str
    cut: int
    exit_time: int
    modeled_r: float
    score: float
    spread_atr: float
    market_regime: str = "UNOBSERVED"

    def __post_init__(self):
        if not self.symbol or not self.strategy_id or self.side not in ("BUY", "SELL"):
            raise ValueError("bad_strategy_or_symbol")
        if not isinstance(self.cut, int) or not isinstance(self.exit_time, int):
            raise ValueError("bad_times")
        if self.cut <= 0 or self.exit_time <= self.cut:
            raise ValueError("noncausal_timestamps")
        if not all(isfinite(float(v)) for v in
                   (self.modeled_r, self.score, self.spread_atr)):
            raise ValueError("invalid_paper_values")
        if self.spread_atr < 0:
            raise ValueError("negative_spread")

    @property
    def family(self) -> str:
        symbol = self.symbol.upper().split(".")[0]
        if any(symbol.startswith(s) for s in MAJORS):
            return "FX_MAJOR"
        if any(symbol.startswith(s) for s in CROSSES):
            return "FX_CROSS"
        if symbol.startswith("XAU"):
            return "GOLD"
        if symbol.startswith("BTC"):
            return "BTC"
        if symbol.startswith(("XTI", "WTI", "USOIL", "BRENT", "UKOIL", "XBR")):
            return "OIL"
        if symbol.startswith(("US30", "DJ30", "NAS100", "US100", "USTEC", "NDX")):
            return "US_INDEX"
        return "OTHER"

    @property
    def context(self) -> str:
        # The V6 archive lacks real, point-in-time H1 regime labels.
        # Spread/ATR and score are observable opportunity proxies, NOT trend.
        if self.market_regime != "UNOBSERVED":
            return "OBSERVED:" + self.market_regime
        if self.spread_atr <= .11 and self.score >= .78:
            return "PROXY_LOW_FRICTION_QUALITY"
        if self.spread_atr >= .18:
            return "PROXY_HIGH_FRICTION"
        return "PROXY_OTHER"


@dataclass(frozen=True)
class MemoryEstimate:
    source: str
    samples: int
    mean_r: float
    profit_factor: float | None
    conservative_score: float
    drift_r: float | None
    eligible: bool
    reason: str


class StrategyPerformanceMemory:
    """Bounded completed-paper-outcome history with contextual fallback."""

    def __init__(self, *, window: int = 60):
        if window < 24:
            raise ValueError("window_too_small")
        self.window = window
        self.history: dict[tuple[str, ...], deque[float]] = defaultdict(
            lambda: deque(maxlen=self.window))
        self.closed_count = 0

    @staticmethod
    def keys(event: PaperEvent):
        s, f, side, context = (
            event.strategy_id, event.family, event.side, event.context)
        return (("strategy_family_side_context", (s, f, side, context), 10),
                ("strategy_family_side", (s, f, side), 16),
                ("strategy_side", (s, side), 24))

    def observe_closed(self, event: PaperEvent, *, known_at: int, extra_cost_r=0.):
        if event.exit_time >= known_at:
            raise ValueError("outcome_not_yet_known")
        value = event.modeled_r - extra_cost_r
        for _, key, _ in self.keys(event):
            self.history[key].append(value)
        self.closed_count += 1

    def estimate(self, event: PaperEvent) -> MemoryEstimate:
        for name, key, minimum in self.keys(event):
            data = list(self.history[key])
            n = len(data)
            if n < minimum:
                continue
            avg = mean(data)
            wins = sum(v for v in data if v > 0)
            losses = -sum(v for v in data if v < 0)
            pf = wins / losses if losses > 0 else (99.0 if wins else None)
            uncertainty = .5 * pstdev(data) / sqrt(n)
            conservative = avg - uncertainty
            drift = None
            if n >= 24:
                half = min(12, n // 2)
                drift = mean(data[-half:]) - mean(data[-2*half:-half])
            # Predeclared research admission rules, NOT a calibrated
            # prediction of profit or a statistical confidence interval.
            if conservative <= .05:
                reason = "nonpositive_cost_aware_edge"
            elif pf is None or pf < 1.15:
                reason = "profit_factor_too_low"
            elif drift is not None and drift < -.35:
                reason = "recent_performance_deteriorating"
            else:
                reason = "research_candidate_only"
            return MemoryEstimate(name, n, round(avg, 6),
                                  round(pf, 6) if pf is not None and isfinite(pf) else pf,
                                  round(conservative, 6),
                                  round(drift, 6) if drift is not None else None,
                                  reason == "research_candidate_only", reason)
        return MemoryEstimate("none", 0, 0.0, None, 0.0, None,
                              False, "insufficient_closed_shadow_observations")


class SimulatedRiskGuard:
    """Pure shadow equity model; does not alter the production risk governor."""

    def __init__(self, *, risk_fraction=.0025, max_drawdown=.08,
                 max_open=2):
        if not 0 < risk_fraction <= .0025 or not 0 < max_drawdown <= .15:
            raise ValueError("research_risk_exceeds_limit")
        self.risk_fraction = risk_fraction
        self.max_drawdown = max_drawdown
        self.max_open = max_open
        self.equity = 1.0
        self.peak = 1.0
        self.drawdown = 0.0
        self.open_families: dict[int, str] = {}
        self.next_slot = 0
        self.closed_returns = []
        self.max_drawdown_seen = 0.0

    def reserve(self, event: PaperEvent):
        if self.drawdown >= self.max_drawdown:
            return None, "portfolio_drawdown_stop"
        if len(self.open_families) >= self.max_open:
            return None, "max_open_positions"
        if event.family in self.open_families.values():
            return None, "family_exposure_limit"
        amount = self.risk_fraction if self.drawdown < .04 else self.risk_fraction / 2
        self.next_slot += 1
        self.open_families[self.next_slot] = event.family
        return (self.next_slot, amount), "reserved_paper_only"

    def close(self, slot: int, risk: float, net_r: float):
        if slot not in self.open_families:
            raise ValueError("unknown_paper_slot")
        del self.open_families[slot]
        before = self.equity
        self.equity = max(0.0, self.equity * (1.0 + risk * net_r))
        self.peak = max(self.peak, self.equity)
        self.drawdown = (self.peak - self.equity) / self.peak
        self.max_drawdown_seen = max(self.max_drawdown_seen, self.drawdown)
        self.closed_returns.append((self.equity - before) / before if before else -1.0)


def _trade_metrics(values: list[float]) -> dict:
    if not values:
        return {"trades": 0, "expectancy_r": None, "profit_factor": None,
                "win_pct": None}
    pos = sum(x for x in values if x > 0)
    neg = -sum(x for x in values if x < 0)
    return {"trades": len(values), "expectancy_r": round(mean(values), 6),
            "profit_factor": round(pos / neg, 6) if neg else None,
            "win_pct": round(100 * sum(x > 0 for x in values) / len(values), 2)}


def _month(timestamp: int) -> str:
    # Broker-coded timestamps; no assertion that historical timezone is UTC.
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m")


def replay_walk_forward(events: Iterable[PaperEvent], *,
                        extra_cost_r=0.0, risk_fraction=.0025,
                        memory_window=60) -> dict:
    """Strict chronological paper replay.

    Every V6 baseline event has a shadow label eventually; no skipped event's
    outcome is visible before its own exit_time. Observational feedback is
    deliberately available even for rejected events, because this dataset
    records V6 baseline paper candidates. This is NOT executable-fill OOS.
    """
    if not 0 <= extra_cost_r <= .5:
        raise ValueError("invalid_cost_stress")
    ordered = sorted(events, key=lambda e: (e.cut, e.symbol, e.side))
    if not ordered:
        return {"status": "NO_ARCHIVED_EVENTS", "events": 0, "orders_sent": 0,
                "live_execution_authorized": False}
    memory = StrategyPerformanceMemory(window=memory_window)
    guard = SimulatedRiskGuard(risk_fraction=risk_fraction)
    pending = []
    decisions = []
    traded_r = []
    completed = []
    monthly = defaultdict(lambda: {"selected": 0, "closed": 0, "sum_r": 0.0})
    serial = 0
    latest_decision = None

    def mature(before: int):
        while pending and pending[0][0] < before:
            _, _, ev, reservation = heapq.heappop(pending)
            memory.observe_closed(ev, known_at=before, extra_cost_r=extra_cost_r)
            if reservation is not None:
                slot, risk = reservation
                realized = ev.modeled_r - extra_cost_r
                guard.close(slot, risk, realized)
                traded_r.append(realized)
                monthly[_month(ev.exit_time)]["closed"] += 1
                monthly[_month(ev.exit_time)]["sum_r"] += realized
                completed.append({"symbol": ev.symbol, "strategy_id": ev.strategy_id,
                                  "side": ev.side, "signal_time": ev.cut,
                                  "exit_time": ev.exit_time,
                                  "R_net_stressed": round(realized, 6),
                                  "risk_fraction": risk,
                                  "equity_after": round(guard.equity, 8)})
    # Handle multiple competing strategies at the same clock instant without
    # consulting their outcomes. Enforce at most one approval per timestamp.
    idx = 0
    while idx < len(ordered):
        now = ordered[idx].cut
        mature(now)
        end = idx + 1
        while end < len(ordered) and ordered[end].cut == now:
            end += 1
        batch = ordered[idx:end]
        ranked = sorted(((memory.estimate(ev), ev) for ev in batch),
                        key=lambda pair: (-pair[0].conservative_score,
                                          pair[1].strategy_id, pair[1].symbol))
        winner = next(((est, ev) for est, ev in ranked if est.eligible), None)
        reservation = None
        admitted = None
        skip_reason = "no_strategy_with_positive_recent_evidence"
        if winner:
            reservation, skip_reason = guard.reserve(winner[1])
            if reservation is not None:
                admitted = winner[1]
                monthly[_month(now)]["selected"] += 1
        for estimate, ev in ranked:
            chosen = admitted is ev
            decisions.append({
                "symbol": ev.symbol, "strategy_id": ev.strategy_id,
                "cut_broker_time": ev.cut, "side": ev.side,
                "context": ev.context, "memory_source": estimate.source,
                "prior_closed_samples": estimate.samples,
                "prior_estimated_mean_r": estimate.mean_r,
                "prior_conservative_score": estimate.conservative_score,
                "memory_reason": estimate.reason,
                "admitted_research_only": chosen,
                "decision": "PAPER_SELECT" if chosen else "WAIT",
                "reason": "historical_shadow_admission" if chosen else
                          (skip_reason if winner and winner[1] is ev else estimate.reason),
                "live_execution_authorized": False})
            serial += 1
            heapq.heappush(pending, (ev.exit_time, serial, ev,
                                    reservation if chosen else None))
        latest_decision = now
        idx = end
    mature(max(ev.exit_time for ev in ordered) + 1)
    # The archive contains only V6's previously selected trades, not all
    # opportunities: this benchmark is *conditional on those baseline picks*.
    base_guard = SimulatedRiskGuard(risk_fraction=risk_fraction, max_open=100000)
    baseline_r = []
    for event in sorted(ordered, key=lambda e: (e.exit_time, e.cut)):
        net = event.modeled_r - extra_cost_r
        base_guard.equity = max(0.0, base_guard.equity * (1.0 + risk_fraction * net))
        base_guard.peak = max(base_guard.peak, base_guard.equity)
        base_guard.max_drawdown_seen = max(
            base_guard.max_drawdown_seen,
            (base_guard.peak - base_guard.equity) / base_guard.peak)
        baseline_r.append(net)
    return {
        "status": "HISTORICAL_RESEARCH_ONLY",
        "events": len(ordered), "as_of_last_broker_time": latest_decision,
        "shadow_outcomes_matured": memory.closed_count,
        "replay_conditions": {
            "strict_close_before_next_decision": True,
            "learn_from_rejected_V6_shadow_labels": True,
            "modeled_fee_already_in_R": True,
            "additional_cost_R": extra_cost_r,
            "actual_market_regimes_available": any(
                x.market_regime != "UNOBSERVED" for x in ordered),
            "historical_broker_dst_validated": False,
            "real_broker_fills_validated": False,
            "independent_unseen_holdout": False,
        },
        "adaptive": {
            **_trade_metrics(traded_r),
            "equity_end": round(guard.equity, 8),
            "return_pct": round(100 * (guard.equity - 1), 4),
            "max_drawdown_pct": round(100 * guard.max_drawdown_seen, 4),
            "wait_events": len(ordered) - len(traded_r),
            "months": {k: {
                **v, "sum_r": round(v["sum_r"], 5)}
                for k, v in sorted(monthly.items())},
        },
        "v6_conditional_benchmark": {
            **_trade_metrics(baseline_r),
            "equity_end": round(base_guard.equity, 8),
            "return_pct": round(100 * (base_guard.equity - 1), 4),
            "max_drawdown_pct": round(100 * base_guard.max_drawdown_seen, 4),
        },
        "decisions": decisions,
        "completed_paper_trades": completed,
        "orders_sent": 0, "live_execution_authorized": False,
        "production_gate_unchanged": True,
    }
