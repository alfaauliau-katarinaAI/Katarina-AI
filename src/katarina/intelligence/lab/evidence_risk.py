"""Katarina evidence-weighted risk gate (research-only; NEVER an order API).

A high technical score, a positive retrospective subset, or an assumed-cost
backtest cannot increase risk. Evidence must be independently verified,
point-in-time, cost-stressed, and from a frozen strategy. This module always
reports a ZERO live-authorized budget.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class StrategyEvidence:
    """Verified *per strategy+side+regime* statistics, never pooled indiscriminately."""
    symbol: str
    strategy: str
    side: str
    regime: str
    historical_trades: int = 0
    forward_trades: int = 0
    forward_net_mean_r: float | None = None
    forward_net_profit_factor: float | None = None
    cost_stress_mean_r: float | None = None
    forward_lower_confidence_r: float | None = None
    chronological_segment_means: tuple[float, ...] = ()
    independent_regimes: int = 0
    strategy_frozen_before_forward: bool = False
    untouched_forward_held_out: bool = False
    causal_prices_verified: bool = False
    broker_commission_spread_slippage_verified: bool = False
    execution_fills_verified: bool = False
    independent_audit_verified: bool = False


@dataclass(frozen=True, slots=True)
class VerifiedRiskState:
    """Values are account fractions, not percentages. Unknown state blocks risk."""
    telemetry_verified: bool = False
    day_drawdown: float | None = None
    peak_drawdown: float | None = None
    committed_open_risk: float | None = None
    same_direction_correlated_risk: float | None = None
    market_health_verified: bool = False
    broker_execution_health_verified: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceRiskDecision:
    level: str
    research_risk_cap_fraction: float
    live_authorized_fraction: float
    reasons: tuple[str, ...]
    live_execution_authorized: bool = False

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "research_risk_cap_fraction": self.research_risk_cap_fraction,
            "live_authorized_fraction": self.live_authorized_fraction,
            "live_execution_authorized": self.live_execution_authorized,
            "reasons": list(self.reasons),
            "scope": "RESEARCH_PAPER_RISK_CAP_ONLY",
        }


class EvidenceRiskGate:
    """Conservative caps 0.25%, moderate 0.50%, aggressive 1.00% per idea.

    No live authorization or order placement exists in this class.
    """
    MAX_OPEN = .02
    MAX_CORRELATED = .015
    DAILY_STOP = .02
    PEAK_STOP = .10
    PEAK_REDUCE = .05

    @staticmethod
    def _pause(*reasons: str) -> EvidenceRiskDecision:
        return EvidenceRiskDecision("WAIT", 0., 0., tuple(reasons) or ("unknown",))

    @staticmethod
    def _finite_nonnegative(value: float | None) -> bool:
        return isinstance(value, (int, float)) and isfinite(value) and value >= 0

    def assess(
        self, evidence: StrategyEvidence | None, state: VerifiedRiskState | None,
    ) -> EvidenceRiskDecision:
        if evidence is None:
            return self._pause("missing_strategy_evidence")
        if state is None or not state.telemetry_verified:
            return self._pause("account_risk_telemetry_unverified")
        measurements = (
            state.day_drawdown, state.peak_drawdown,
            state.committed_open_risk, state.same_direction_correlated_risk,
        )
        if not all(self._finite_nonnegative(v) for v in measurements):
            return self._pause("invalid_account_risk_telemetry")
        if not state.market_health_verified or not state.broker_execution_health_verified:
            return self._pause("broker_or_market_health_unverified")
        if state.day_drawdown >= self.DAILY_STOP:
            return self._pause("daily_drawdown_stop")
        if state.peak_drawdown >= self.PEAK_STOP:
            return self._pause("peak_drawdown_stop")
        if state.committed_open_risk >= self.MAX_OPEN:
            return self._pause("portfolio_risk_capacity_exhausted")
        if state.same_direction_correlated_risk >= self.MAX_CORRELATED:
            return self._pause("correlated_risk_capacity_exhausted")

        if (not evidence.symbol or not evidence.strategy
                or evidence.side not in ("BUY", "SELL") or not evidence.regime):
            return self._pause("invalid_strategy_identity")
        if (not isinstance(evidence.historical_trades, int)
                or not isinstance(evidence.forward_trades, int)
                or not isinstance(evidence.independent_regimes, int)
                or min(evidence.historical_trades, evidence.forward_trades,
                       evidence.independent_regimes) < 0):
            return self._pause("invalid_evidence_counts")

        verified = (
            evidence.strategy_frozen_before_forward
            and evidence.untouched_forward_held_out
            and evidence.causal_prices_verified
            and evidence.broker_commission_spread_slippage_verified
            and evidence.execution_fills_verified
            and evidence.independent_audit_verified
        )
        if not verified:
            return self._pause("independent_forward_and_execution_proof_missing")
        means = evidence.chronological_segment_means
        values = (
            evidence.forward_net_mean_r, evidence.forward_net_profit_factor,
            evidence.cost_stress_mean_r, evidence.forward_lower_confidence_r,
            *means,
        )
        if not all(isinstance(v, (float, int)) and isfinite(v) for v in values):
            return self._pause("missing_or_nonfinite_forward_metrics")
        if (evidence.historical_trades < 150 or evidence.forward_trades < 40
                or evidence.forward_net_mean_r <= 0 or
                evidence.forward_net_profit_factor < 1.2 or
                evidence.cost_stress_mean_r <= 0 or
                evidence.forward_lower_confidence_r <= 0 or
                len(means) < 3 or any(v <= 0 for v in means)):
            return self._pause("positive_independent_edge_not_proven")

        level, cap = "CONSERVATIVE", .0025
        if (evidence.forward_trades >= 120
                and evidence.forward_net_profit_factor >= 1.3
                and evidence.cost_stress_mean_r >= .07
                and evidence.independent_regimes >= 2):
            level, cap = "MODERATE", .005
        if (evidence.forward_trades >= 250
                and evidence.forward_net_profit_factor >= 1.5
                and evidence.cost_stress_mean_r >= .12
                and len(means) >= 4 and evidence.independent_regimes >= 3):
            level, cap = "AGGRESSIVE", .01

        reasons = ["verified_independent_edge"]
        if state.peak_drawdown >= self.PEAK_REDUCE:
            cap *= .5
            reasons.append("drawdown_risk_halved")
        cap = min(
            cap,
            self.MAX_OPEN - state.committed_open_risk,
            self.MAX_CORRELATED - state.same_direction_correlated_risk,
        )
        if cap <= 1e-12:
            return self._pause("account_risk_capacity_exhausted")
        # A research cap is NOT a trading permission; explicit real account
        # integration/reconciliation and a separate deployment gate are needed.
        return EvidenceRiskDecision(level, round(cap, 9), 0., tuple(reasons))


def assess_legacy_august_audit(audit: dict) -> EvidenceRiskDecision:
    """Never convert retrospective broker quotes into independent forward fills."""
    if not isinstance(audit, dict) or audit.get("action") != "WAIT":
        return EvidenceRiskGate._pause("untrusted_or_missing_broker_research")
    if (audit.get("tick_quote_mean_assumed_r") is None or
            audit.get("tick_quote_profit_factor_assumed") is None):
        return EvidenceRiskGate._pause("historical_risk_metrics_missing")
    try:
        mean = float(audit["tick_quote_mean_assumed_r"])
        pf = float(audit["tick_quote_profit_factor_assumed"])
    except (TypeError, ValueError, OverflowError):
        return EvidenceRiskGate._pause("historical_risk_metrics_invalid")
    if not isfinite(mean) or not isfinite(pf):
        return EvidenceRiskGate._pause("historical_risk_metrics_invalid")
    if mean <= 0 or pf < 1.2:
        return EvidenceRiskGate._pause("negative_or_insufficient_historical_edge",
                                       "no_independent_forward_fill_history")
    evidence = StrategyEvidence(
        symbol="17-market-research", strategy="precommitted_alt_setups",
        side="BUY", regime="MIXED",
        historical_trades=int(audit.get("tick_quote_complete", 0)),
        forward_trades=0,
        forward_net_mean_r=audit.get("tick_quote_mean_assumed_r"),
        forward_net_profit_factor=audit.get("tick_quote_profit_factor_assumed"),
        strategy_frozen_before_forward=True,
    )
    return EvidenceRiskGate().assess(evidence, VerifiedRiskState())