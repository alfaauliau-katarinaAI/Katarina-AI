"""Research-only bridge: adaptive entry evidence plus structural exit evidence.

Returns an immutable Owner-readable receipt. No order sender, cloud transport,
authentication, risk approval, or action-capable Owner control exists here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
import re

from katarina.intelligence.cognition.adaptive_observation import BrainV2Observation
from katarina.intelligence.perception.structure_exit_plan import StructuralExitPlan

_HASH = re.compile(r"[0-9a-f]{64}\Z")
_HAND = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")


@dataclass(frozen=True)
class OwnerResearchReceipt:
    digest: str
    observed_utc: str
    source_digest: str
    symbol: str
    side: str
    regime: str
    playbook: str
    action: str
    entry: float
    stop: float | None
    target: float | None
    reasons: tuple[str, ...]
    hand_id: str | None
    research_only: bool = True
    live_execution_authorized: bool = False
    strategy_promoted: bool = False
    orders_submitted: int = 0

    def owner_view(self) -> dict:
        return dict(asdict(self), hand_trust="UNVERIFIED_TELEMETRY",
                    controls="READ_ONLY")


def research_handoff(
    *, brain: BrainV2Observation, exit_plan: StructuralExitPlan | None,
    symbol: str, entry: float, as_of_utc: datetime,
    source_digest: str, hand_id: str | None = None,
) -> OwnerResearchReceipt:
    if not isinstance(brain, BrainV2Observation):
        raise ValueError("brain_observation_required")
    if not brain.research_only or brain.live_risk_authorized:
        raise ValueError("brain_must_be_research_only")
    proposal = brain.proposal
    if not proposal.research_only or proposal.live_risk_authorized:
        raise ValueError("entry_must_be_research_only")
    if exit_plan is not None and (
        not isinstance(exit_plan, StructuralExitPlan)
        or not exit_plan.research_only or exit_plan.live_execution_authorized
    ):
        raise ValueError("exit_must_be_research_only")
    if not symbol or symbol != proposal.symbol:
        raise ValueError("symbol_mismatch")
    if type(entry) not in (float, int) or not isfinite(entry) or entry <= 0:
        raise ValueError("invalid_entry")
    if not isinstance(as_of_utc, datetime) or as_of_utc.tzinfo is None or as_of_utc.utcoffset() is None:
        raise ValueError("invalid_timestamp")
    if not isinstance(source_digest, str) or not _HASH.fullmatch(source_digest):
        raise ValueError("unverified_source_digest")
    if hand_id is not None and (
        not isinstance(hand_id, str) or not _HAND.fullmatch(hand_id)
    ):
        raise ValueError("untrusted_hand_id")

    side = proposal.side.value
    reasons = []
    if not proposal.ready_for_research or side not in ("BUY", "SELL"):
        reasons.append("ENTRY_NOT_RESEARCH_READY")
    if (proposal.strategy != brain.regime.playbook
            or proposal.state != brain.regime.state):
        reasons.append("REGIME_PLAYBOOK_MISMATCH")
    stop = target = None
    if exit_plan is None:
        reasons.append("STRUCTURAL_EXIT_MISSING")
    else:
        if exit_plan.direction != side:
            reasons.append("DIRECTION_MISMATCH")
        if not exit_plan.approved_for_research or exit_plan.blockers:
            reasons.append("EXIT_NOT_RESEARCH_READY")
        if any(type(v) not in (int, float) or not isfinite(v) or v <= 0
               for v in (exit_plan.stop, exit_plan.target)):
            reasons.append("INVALID_EXIT_PRICES")
        elif side == "BUY" and not exit_plan.stop < entry < exit_plan.target:
            reasons.append("BUY_STOP_TARGET_GEOMETRY")
        elif side == "SELL" and not exit_plan.target < entry < exit_plan.stop:
            reasons.append("SELL_STOP_TARGET_GEOMETRY")
        if not reasons:
            stop, target = float(exit_plan.stop), float(exit_plan.target)
    details = dict(
        observed_utc=as_of_utc.astimezone(timezone.utc).isoformat(),
        source_digest=source_digest, symbol=symbol, side=side,
        regime=brain.regime.state.value, playbook=proposal.strategy.value,
        action="RESEARCH_CANDIDATE" if not reasons else "WAIT",
        entry=float(entry), stop=stop, target=target,
        reasons=tuple(sorted(set(reasons))), hand_id=hand_id,
    )
    receipt = sha256(json.dumps(details, sort_keys=True, allow_nan=False,
                                separators=(",", ":")).encode()).hexdigest()
    return OwnerResearchReceipt(digest=receipt, **details)
