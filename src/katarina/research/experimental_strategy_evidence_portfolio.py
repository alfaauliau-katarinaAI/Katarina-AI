"""Historical research variant. Not registered in the runtime or live execution.

Preserved from brain-intelligence-admission; production engine stays unchanged.
"""


from dataclasses import dataclass
from math import floor, isfinite
from typing import Mapping, Sequence

from katarina.engines.account_risk_state import AccountRiskCoordinator
from katarina.engines.execution import ExecutionEngine, ExecutionIntent
from katarina.engines.exposure import CorrelationExposureEngine
from katarina.engines.manual_risk import AccountRiskAssessment
from katarina.engines.opportunity import RankedOpportunity
from katarina.intelligence.shadow.strategy_evidence import StrategyEvidenceDecision
from katarina.intelligence.shadow.strategy_drift import StrategyDriftDecision


@dataclass(frozen=True, slots=True)
class MultiSymbolCandidate:
    opportunity: RankedOpportunity
    requested_risk_fraction: float
    base_volume: float
    volume_min: float
    volume_step: float
    stop_loss: float
    take_profit: float | None
    decision_id: str
    risk_id: str
    spread_ok: bool = True
    quality_risk_multiplier: float = 1.0
    strategy_id: str = ""


@dataclass(frozen=True, slots=True)
class PlannedExecution:
    symbol: str
    instrument_id: int
    spec_revision: int
    score: float
    approved_risk_fraction: float
    reservation_id: str
    intent: ExecutionIntent


@dataclass(frozen=True, slots=True)
class RejectedExecution:
    symbol: str
    reason: str


@dataclass(frozen=True, slots=True)
class MultiSymbolExecutionPlan:
    accepted: tuple[PlannedExecution, ...]
    rejected: tuple[RejectedExecution, ...]
    total_reserved_fraction: float


class MultiSymbolExecutionOrchestrator:
    """Serial multi-market admission authority.

    Ranked opportunities are processed best-first. Every accepted candidate:
    1) passes shared-account Risk Governor and atomically reserves risk;
    2) passes portfolio correlation exposure with existing + newly accepted risk;
    3) scales broker volume if Risk Governor reduces the request;
    4) passes execution preflight;
    5) becomes an idempotent ExecutionIntent.

    No candidate can race another candidate around the 8% account cap because
    reservations are committed before the next candidate is evaluated.
    """

    def __init__(
        self,
        *,
        risk: AccountRiskCoordinator,
        execution: ExecutionEngine | None = None,
        correlation: CorrelationExposureEngine | None = None,
        max_new_positions: int = 5,
        correlation_cap: float = 0.08,
        require_correlation_evidence: bool = False,
        min_correlation_observations: int = 20,
        require_strategy_evidence: bool = False,
        require_drift_clearance: bool = False,
        exclusive_exposure_groups: Mapping[str, str] | None = None,
    ):
        if max_new_positions <= 0:
            raise ValueError("max_new_positions")
        if min_correlation_observations < 3:
            raise ValueError("min_correlation_observations")
        self.risk=risk
        self.execution=execution or ExecutionEngine()
        self.correlation=correlation or CorrelationExposureEngine()
        self.max_new_positions=max_new_positions
        self.correlation_cap=correlation_cap
        self.require_correlation_evidence=bool(require_correlation_evidence)
        self.min_correlation_observations=int(min_correlation_observations)
        self.require_strategy_evidence=bool(require_strategy_evidence)
        self.require_drift_clearance=bool(require_drift_clearance)
        self.exclusive_exposure_groups=dict(exclusive_exposure_groups or {})
        if any(not symbol or not group for symbol,group in self.exclusive_exposure_groups.items()):
            raise ValueError("invalid_exclusive_exposure_group")

    def _valid_correlation_inputs(
        self, symbols: Sequence[str], returns: Mapping[str,Sequence[float]],
    ) -> bool:
        lengths=set()
        try:
            for symbol in symbols:
                series=returns.get(symbol)
                if series is None or len(series)<self.min_correlation_observations:
                    return False
                values=[float(value) for value in series]
                if any(not isfinite(value) for value in values):
                    return False
                if max(values)-min(values)<=1e-15:
                    return False
                lengths.add(len(values))
        except (TypeError, ValueError, OverflowError):
            return False
        return len(lengths)==1

    @staticmethod
    def _quantize_volume(value: float, minimum: float, step: float) -> float:
        if any(not isfinite(x) for x in (value,minimum,step)) or value <= 0 or minimum <= 0 or step <= 0:
            return 0.0
        units=floor((value+1e-12)/step)
        result=round(units*step,8)
        return result if result+1e-12 >= minimum else 0.0

    @staticmethod
    def _reservation_id(c: MultiSymbolCandidate) -> str:
        return f"multi:{c.opportunity.instrument_id}:{c.decision_id}"

    def build_plan(
        self,
        candidates: Sequence[MultiSymbolCandidate],
        *,
        positions: AccountRiskAssessment,
        day_key: str,
        returns: Mapping[str,Sequence[float]],
        existing_symbol_risks: Mapping[str,float] | None = None,
        health_ok: bool = True,
        reconciled: bool = True,
        execution_armed: bool = True,
        fresh: bool = True,
        account_currency: str | None = None,
        evidence_decisions: Mapping[tuple[str, str], StrategyEvidenceDecision] | None = None,
        drift_decisions: Mapping[tuple[str, str], StrategyDriftDecision] | None = None,
    ) -> MultiSymbolExecutionPlan:
        accepted=[]
        rejected=[]
        symbol_risks={k:max(0.0,float(v)) for k,v in (existing_symbol_risks or {}).items()}
        seen=set()

        ordered=sorted(candidates,key=lambda c:(-c.opportunity.score,c.opportunity.symbol))
        for c in ordered:
            symbol=c.opportunity.symbol
            if len(accepted) >= self.max_new_positions:
                rejected.append(RejectedExecution(symbol,"max_new_positions"))
                continue
            if symbol in seen:
                rejected.append(RejectedExecution(symbol,"duplicate_symbol_candidate"))
                continue
            seen.add(symbol)

            if c.opportunity.instrument_id <= 0 or c.opportunity.proposal.side.value not in {"BUY","SELL"}:
                rejected.append(RejectedExecution(symbol,"invalid_opportunity"))
                continue
            # A score or indicator alone must never be treated as verified alpha.
            # Strict mode requires forward PAPER/DEAL results from a frozen setup.
            evidence=None
            if self.require_strategy_evidence:
                evidence=(evidence_decisions or {}).get((symbol,c.strategy_id))
                if (not c.strategy_id or not isinstance(evidence,StrategyEvidenceDecision)
                        or not evidence.eligible_for_risk_review
                        or evidence.live_authorized
                        or not isfinite(evidence.risk_multiplier)
                        or not 0 < evidence.risk_multiplier <= .75):
                    rejected.append(RejectedExecution(symbol,"strategy_forward_evidence_missing"))
                    continue

            drift=None
            if self.require_drift_clearance:
                drift=(drift_decisions or {}).get((symbol,c.strategy_id))
                if (not c.strategy_id or not isinstance(drift,StrategyDriftDecision)
                        or drift.state != "RISK_REVIEW_ONLY"
                        or drift.live_execution_authorized
                        or not isfinite(drift.risk_multiplier)
                        or not 0 < drift.risk_multiplier <= .75):
                    rejected.append(RejectedExecution(symbol,"strategy_drift_no_trade"))
                    continue

            group=self.exclusive_exposure_groups.get(symbol)
            if group is not None:
                # Caller must explicitly attest current symbol risks were reconciled.
                if existing_symbol_risks is None:
                    rejected.append(RejectedExecution(symbol,"exclusive_group_positions_unverified"))
                    continue
                if any(self.exclusive_exposure_groups.get(other)==group and exposure>0
                       for other,exposure in symbol_risks.items()):
                    rejected.append(RejectedExecution(symbol,"exclusive_exposure_group_busy"))
                    continue

            quality_multiplier=max(0.0,min(1.0,float(c.quality_risk_multiplier)))
            if evidence is not None:
                quality_multiplier=min(quality_multiplier,evidence.risk_multiplier)
            if drift is not None:
                quality_multiplier=min(quality_multiplier,drift.risk_multiplier)
            req=max(0.0,float(c.requested_risk_fraction))*quality_multiplier
            if req <= 0:
                rejected.append(RejectedExecution(symbol,"invalid_requested_risk_or_quality"))
                continue
            if c.base_volume <= 0 or c.stop_loss <= 0:
                rejected.append(RejectedExecution(symbol,"invalid_execution_geometry"))
                continue

            reservation_id=self._reservation_id(c)
            auth=self.risk.authorize_and_reserve(
                positions,
                reservation_id=reservation_id,
                day_key=day_key,
                requested_fraction=req,
                uncertainty=c.opportunity.proposal.uncertainty,
                expected_rr=c.opportunity.proposal.expected_rr,
                health_ok=health_ok,
                reconciled=reconciled,
                account_currency=account_currency,
            )
            if auth.approved_fraction <= 0 or auth.action not in {"APPROVE","REDUCE"}:
                rejected.append(RejectedExecution(symbol,auth.reason))
                continue

            tentative=dict(symbol_risks)
            tentative[symbol]=tentative.get(symbol,0.0)+auth.approved_fraction
            if self.require_correlation_evidence and not self._valid_correlation_inputs(
                tuple(tentative),returns
            ):
                self.risk.state_engine.reservations.release(reservation_id)
                rejected.append(RejectedExecution(symbol,"correlation_data_unverified"))
                continue
            exposure=self.correlation.assess(tentative,returns,cap=self.correlation_cap)
            if not exposure.allowed:
                self.risk.state_engine.reservations.release(reservation_id)
                rejected.append(RejectedExecution(symbol,"correlation_exposure_cap"))
                continue

            # base_volume was sized against c.requested_risk_fraction, BEFORE
            # any quality/evidence multiplier. Scaling by req would silently
            # undo that multiplier and leave the physical lot too large.
            scaled_volume=c.base_volume*(auth.approved_fraction/float(c.requested_risk_fraction))
            volume=self._quantize_volume(scaled_volume,c.volume_min,c.volume_step)
            if volume <= 0:
                self.risk.state_engine.reservations.release(reservation_id)
                rejected.append(RejectedExecution(symbol,"approved_risk_below_minimum_volume"))
                continue

            intent_id=ExecutionEngine.deterministic_id({
                "symbol":symbol,
                "instrument_id":c.opportunity.instrument_id,
                "decision_id":c.decision_id,
                "risk_id":c.risk_id,
                "reservation_id":reservation_id,
                "volume":volume,
                "sl":c.stop_loss,
                "tp":c.take_profit,
            })
            intent=ExecutionIntent(
                intent_id=intent_id,
                side=c.opportunity.proposal.side.value,
                symbol=symbol,
                volume=volume,
                stop_loss=c.stop_loss,
                take_profit=c.take_profit,
                decision_id=c.decision_id,
                risk_id=c.risk_id,
                instrument_id=c.opportunity.instrument_id,
                spec_revision=getattr(c.opportunity,"spec_revision",0),
            )
            preflight=self.execution.preflight(
                intent,
                execution_armed=execution_armed,
                fresh=fresh,
                reconciled=reconciled,
                spread_ok=c.spread_ok,
            )
            if not preflight.allowed:
                self.risk.state_engine.reservations.release(reservation_id)
                rejected.append(RejectedExecution(symbol,preflight.reason))
                continue
            self.execution.reserve(intent)
            symbol_risks[symbol]=tentative[symbol]
            accepted.append(PlannedExecution(
                symbol=symbol,
                instrument_id=c.opportunity.instrument_id,
                spec_revision=getattr(c.opportunity,"spec_revision",0),
                score=c.opportunity.score,
                approved_risk_fraction=auth.approved_fraction,
                reservation_id=reservation_id,
                intent=intent,
            ))

        return MultiSymbolExecutionPlan(
            tuple(accepted),tuple(rejected),
            sum(x.approved_risk_fraction for x in accepted),
        )
