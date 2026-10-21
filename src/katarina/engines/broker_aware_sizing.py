"""Conservative research-only Stage 16/17 sizing; never creates orders."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from math import isfinite
from katarina.engines.risk import RiskAction, RiskGovernor, RiskRequest
from katarina.intelligence.lab.evidence_risk import (
    EvidenceRiskGate, StrategyEvidence, VerifiedRiskState,
)


@dataclass(frozen=True)
class BrokerFacts:
    currency: str
    contract_revision: int
    loss_per_price_unit_per_lot: float
    min_volume: float
    max_volume: float
    volume_step: float
    margin_per_lot: float
    verified: bool = False


@dataclass(frozen=True)
class TradingCosts:
    spread_distance: float
    adverse_slippage_distance: float
    round_trip_fee_per_lot: float
    verified: bool = False


@dataclass(frozen=True)
class AccountFacts:
    native_currency: str
    active_capital: float
    equity: float
    peak_reference_capital: float
    available_margin: float
    committed_risk_fraction: float = 0.0
    daily_drawdown: float = 0.0
    total_drawdown: float = 0.0
    healthy: bool = True
    reconciled: bool = True
    unbounded_risk: bool = False
    uncertainty: float | None = None
    expected_rr: float | None = None
    verified: bool = False


@dataclass(frozen=True)
class Qualification:
    eligible_for_research: bool
    reason: str
    volume: float = 0.0
    fraction: float = 0.0
    budget_native: float = 0.0
    buffered_loss_native: float = 0.0
    margin_native: float = 0.0
    live_execution_authorized: bool = False


class ResearchCostMarginGate:
    """Use *confirmed* native-money facts; no account/market autodiscovery."""

    def __init__(self, governor: RiskGovernor):
        self.governor = governor

    def qualify(self, *, account: AccountFacts, broker: BrokerFacts,
                costs: TradingCosts, side: str, entry: float, stop: float,
                evidence_cap_fraction: float | None = None) -> Qualification:
        reject = lambda reason: Qualification(False, reason)
        if not (account.verified and broker.verified and costs.verified):
            return reject("unverified_account_contract_or_cost")
        if account.uncertainty is None or account.expected_rr is None:
            return reject("missing_signal_quality_evidence")
        if not account.native_currency or account.native_currency != broker.currency:
            return reject("currency_unverified_or_mismatch")
        if side not in ("BUY", "SELL"):
            return reject("invalid_side")
        values = (account.active_capital, account.equity, account.peak_reference_capital,
                  account.available_margin, account.committed_risk_fraction,
                  account.daily_drawdown, account.total_drawdown,
                  account.uncertainty, account.expected_rr,
                  broker.loss_per_price_unit_per_lot, broker.min_volume,
                  broker.max_volume, broker.volume_step, broker.margin_per_lot,
                  costs.spread_distance, costs.adverse_slippage_distance,
                  costs.round_trip_fee_per_lot, entry, stop)
        if any(not isfinite(v) for v in values):
            return reject("nonfinite_evidence")
        capital = min(account.active_capital, account.equity)
        if (capital <= 0 or account.available_margin <= 0 or
            account.peak_reference_capital < capital or broker.contract_revision < 1 or
            broker.loss_per_price_unit_per_lot <= 0 or broker.min_volume <= 0 or
            broker.max_volume < broker.min_volume or broker.volume_step <= 0 or
            broker.margin_per_lot <= 0 or min(entry, stop) <= 0 or
            min(costs.spread_distance, costs.adverse_slippage_distance,
                costs.round_trip_fee_per_lot) < 0):
            return reject("invalid_account_or_broker_spec")
        if (side == "BUY" and stop >= entry) or (side == "SELL" and stop <= entry):
            return reject("stop_missing_or_wrong_side")
        per_lot = ((abs(entry-stop) + costs.spread_distance +
                    costs.adverse_slippage_distance) * broker.loss_per_price_unit_per_lot +
                   costs.round_trip_fee_per_lot)
        if not isfinite(per_lot) or per_lot <= 0:
            return reject("invalid_buffered_loss")
        risk = self.governor.evaluate(RiskRequest(
            None, account.committed_risk_fraction, account.total_drawdown,
            account.uncertainty, account.expected_rr, account.healthy,
            account.reconciled, account.daily_drawdown,
            account.unbounded_risk, capital, account.peak_reference_capital,
            account.native_currency))
        if risk.action not in (RiskAction.APPROVE, RiskAction.REDUCE):
            return reject("governor_" + risk.reason)
        # Evidence is a ceiling, never a multiplier or order permission.
        cap = risk.approved_fraction
        if evidence_cap_fraction is not None:
            if (not isfinite(evidence_cap_fraction) or
                    not 0 < evidence_cap_fraction <= .01):
                return reject("invalid_evidence_cap")
            cap = min(cap, evidence_cap_fraction)
        budget = capital*cap
        usable_margin = account.available_margin*.90
        affordable = min(broker.max_volume, budget/per_lot,
                         usable_margin/broker.margin_per_lot)
        if affordable < broker.min_volume:
            return reject("min_lot_exceeds_risk_or_margin")
        minimum = Decimal(str(broker.min_volume))
        step = Decimal(str(broker.volume_step))
        steps = ((Decimal(str(affordable))-minimum)/step).to_integral_value(rounding=ROUND_FLOOR)
        volume = float(minimum+steps*step)
        buffered_loss, margin = volume*per_lot, volume*broker.margin_per_lot
        if (volume < broker.min_volume or volume > broker.max_volume or
            buffered_loss > budget+1e-9 or margin > usable_margin+1e-9):
            return reject("cost_or_margin_exceeds_budget")
        return Qualification(True, "qualified_for_research_only", volume,
                             cap, budget, buffered_loss, margin)

class EvidenceQualifiedResearchSizing:
    """Apply verified evidence AND legacy capital/broker governor jointly.

    Explicit research-only path: missing proof, broker facts or reconciled
    risk telemetry always blocks the sizing quote.
    """
    def __init__(self, governor: RiskGovernor):
        self._sizing = ResearchCostMarginGate(governor)
        self._evidence = EvidenceRiskGate()

    def qualify(self, *, evidence: StrategyEvidence | None,
                risk_state: VerifiedRiskState | None,
                account: AccountFacts, broker: BrokerFacts,
                costs: TradingCosts, side: str, entry: float,
                stop: float) -> Qualification:
        if evidence is not None and evidence.side != side:
            return Qualification(False, "strategy_side_evidence_mismatch")
        gate = self._evidence.assess(evidence, risk_state)
        if gate.research_risk_cap_fraction <= 0:
            return Qualification(False, "evidence_" + gate.reasons[0])
        if (risk_state is None or not account.verified
                or not risk_state.telemetry_verified
                or not risk_state.market_health_verified
                or not risk_state.broker_execution_health_verified):
            return Qualification(False, "reconciled_risk_state_missing")
        pairs = ((account.daily_drawdown, risk_state.day_drawdown),
                 (account.total_drawdown, risk_state.peak_drawdown),
                 (account.committed_risk_fraction,
                  risk_state.committed_open_risk))
        if any(b is None or not isfinite(a) or not isfinite(b)
               or abs(a-b) > 1e-9 for a,b in pairs):
            return Qualification(False, "account_evidence_snapshot_mismatch")
        return self._sizing.qualify(
            account=account, broker=broker, costs=costs,
            side=side, entry=entry, stop=stop,
            evidence_cap_fraction=gate.research_risk_cap_fraction,
        )
