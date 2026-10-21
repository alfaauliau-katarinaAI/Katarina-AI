"""Broker-aware *research-only* exit lifecycle feasibility checks.

This cannot choose an optimal portfolio exit or send/modify any broker order.
The Owner's deferred predictive exit model/fees remain intentionally unset.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
import json
import re

from katarina.intelligence.cognition.unified_research_handoff import OwnerResearchReceipt

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ACTIONS = ("HOLD", "FULL", "PARTIAL", "TRAIL")
_SIDES = ("BUY", "SELL")
_OWNERS = ("KATARINA", "OWNER_MANUAL")
_SOURCE_FIELDS = ("observed_utc","source_digest","symbol","side",
                  "regime","playbook","action","entry","stop","target",
                  "reasons","hand_id")


def _dec(value, field: str, *, minimum: Decimal = Decimal("0")) -> Decimal:
    if type(value) not in (int, float, Decimal, str):
        raise ValueError("invalid_exit_numeric_" + field)
    try:
        v = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid_exit_numeric_" + field) from exc
    if not v.is_finite() or v < minimum:
        raise ValueError("invalid_exit_numeric_" + field)
    return v


def _verify_source_receipt(source: OwnerResearchReceipt,
                           inspected_at: datetime) -> None:
    """Local checksum and chronology, never authentication of Hand origin."""
    if source.action not in ("RESEARCH_CANDIDATE", "WAIT"):
        raise ValueError("untrusted_exit_source_action")
    if source.side not in _SIDES or not isinstance(source.symbol, str) or not source.symbol:
        raise ValueError("untrusted_exit_source_identity")
    if (not isinstance(source.source_digest, str)
            or not _HEX.fullmatch(source.source_digest)):
        raise ValueError("untrusted_exit_source_digest")
    if (not isinstance(source.reasons, tuple)
            or not all(isinstance(x, str) and x for x in source.reasons)):
        raise ValueError("untrusted_exit_source_reasons")
    entry = _dec(source.entry, "source_entry", minimum=Decimal("0.00000001"))
    if source.action == "WAIT":
        if (not source.reasons or source.stop is not None
                or source.target is not None):
            raise ValueError("inconsistent_wait_exit_source")
    else:
        if source.reasons:
            raise ValueError("inconsistent_candidate_exit_source")
        stop = _dec(source.stop, "source_stop", minimum=Decimal("0.00000001"))
        target = _dec(source.target, "source_target", minimum=Decimal("0.00000001"))
        if ((source.side == "BUY" and not stop < entry < target)
                or (source.side == "SELL" and not target < entry < stop)):
            raise ValueError("invalid_source_exit_geometry")
    try:
        born = datetime.fromisoformat(source.observed_utc)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_source_clock") from exc
    if born.tzinfo is None or born.utcoffset() is None:
        raise ValueError("invalid_source_clock")
    if born.astimezone(timezone.utc) > inspected_at.astimezone(timezone.utc):
        raise ValueError("future_entry_research_evidence")
    data = {key:getattr(source, key) for key in _SOURCE_FIELDS}
    try:
        digest = sha256(json.dumps(
            data, sort_keys=True, separators=(",", ":"),
            allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError) as exc:
        raise ValueError("unverifiable_exit_research_source") from exc
    if not compare_digest(source.digest, digest):
        raise ValueError("exit_research_receipt_digest_mismatch")


def _on_broker_volume_grid(
    volume: Decimal, minimum: Decimal, maximum: Decimal, step: Decimal,
) -> bool:
    return (minimum <= volume <= maximum
            and (volume - minimum) % step == 0)


@dataclass(frozen=True)
class OfflineExitFeasibility:
    receipt_sha256: str
    observed_utc: str
    symbol: str
    side: str
    position_owner: str
    requested_action: str
    research_action: str
    volume_before: str
    close_volume: str | None
    volume_after: str | None
    proposed_stop: str | None
    blockers: tuple[str, ...]
    source_receipt_sha256: str
    broker_costs_verified: bool = False
    broker_acknowledgement_received: bool = False
    owner_manual_positions_modified: bool = False
    live_execution_authorized: bool = False
    orders_submitted: int = 0

    def owner_view(self) -> dict:
        return asdict(self)


def review_offline_exit_lifecycle(
    *, source: OwnerResearchReceipt, position_symbol: str, position_owner: str,
    side: str, volume, broker_min_volume, broker_max_volume,
    broker_volume_step, bid, ask, broker_stop_distance,
    broker_freeze_distance, action: str,
    observed_utc: datetime, close_volume=None,
    existing_sl=None, proposed_sl=None,
) -> OfflineExitFeasibility:
    """Check feasibility, not profitability or whether an exit SHOULD occur.

    All stops/volumes/distances come from caller-supplied broker specs. Even a
    geometrically feasible plan is blocked from execution until independent
    broker/Risk Governor verification and authenticated authorization.
    """
    if (not isinstance(source, OwnerResearchReceipt)
            or not source.research_only or source.live_execution_authorized
            or source.strategy_promoted or source.orders_submitted != 0
            or not _HEX.fullmatch(source.digest)):
        raise ValueError("invalid_exit_research_source")
    if side not in _SIDES or position_owner not in _OWNERS or action not in _ACTIONS:
        raise ValueError("unsupported_exit_instruction")
    if (not isinstance(position_symbol, str) or not position_symbol
            or position_symbol != source.symbol):
        raise ValueError("exit_symbol_mismatch")
    if side != source.side:
        raise ValueError("exit_side_mismatch")
    if (not isinstance(observed_utc, datetime) or observed_utc.tzinfo is None
            or observed_utc.utcoffset() is None):
        raise ValueError("invalid_exit_observation_clock")
    _verify_source_receipt(source, observed_utc)
    min_vol = _dec(broker_min_volume,"minimum_volume",minimum=Decimal("0.00000001"))
    step = _dec(broker_volume_step,"volume_step",minimum=Decimal("0.00000001"))
    max_vol = _dec(broker_max_volume,"maximum_volume",minimum=min_vol)
    current = _dec(volume,"position_volume",minimum=min_vol)
    if not _on_broker_volume_grid(current,min_vol,max_vol,step):
        raise ValueError("position_volume_not_on_broker_grid")
    bid_p = _dec(bid,"bid",minimum=Decimal("0.00000001"))
    ask_p = _dec(ask,"ask",minimum=Decimal("0.00000001"))
    if ask_p < bid_p:
        raise ValueError("invalid_bid_ask_spread")
    stop_distance = _dec(broker_stop_distance,"stop_distance")
    freeze_distance = _dec(broker_freeze_distance,"freeze_distance")
    prior_sl = (_dec(existing_sl,"existing_sl",minimum=Decimal("0.00000001"))
                if existing_sl is not None else None)
    new_sl = (_dec(proposed_sl,"proposed_sl",minimum=Decimal("0.00000001"))
              if proposed_sl is not None else None)
    requested_close = (_dec(close_volume,"close_volume",minimum=Decimal("0.00000001"))
                       if close_volume is not None else None)
    reasons = []
    effective_close = None
    remainder = None
    accepted_sl = None
    if source.action != "RESEARCH_CANDIDATE":
        reasons.append("ENTRY_RESEARCH_NOT_READY")
    if position_owner == "OWNER_MANUAL" and action != "HOLD":
        reasons.append("MANUAL_OWNER_POSITION_PROTECTED")
    if action == "HOLD":
        if requested_close is not None or new_sl is not None:
            reasons.append("HOLD_CANNOT_MUTATE_POSITION")
    elif action == "FULL":
        if requested_close is not None and requested_close != current:
            reasons.append("FULL_CLOSE_VOLUME_MISMATCH")
        if new_sl is not None:
            reasons.append("FULL_CLOSE_CANNOT_CHANGE_SL")
        if not reasons:
            effective_close, remainder = current, Decimal("0")
    elif action == "PARTIAL":
        if requested_close is None or new_sl is not None:
            reasons.append("PARTIAL_NEEDS_EXACT_CLOSE_VOLUME")
        elif requested_close >= current:
            reasons.append("PARTIAL_REQUIRES_NONZERO_REMAINDER")
        else:
            remains = current - requested_close
            if (not _on_broker_volume_grid(requested_close,min_vol,max_vol,step)
                    or not _on_broker_volume_grid(remains,min_vol,max_vol,step)):
                reasons.append("PARTIAL_VOLUME_OR_REMAINDER_BROKER_INVALID")
            elif not reasons:
                effective_close, remainder = requested_close, remains
    elif action == "TRAIL":
        if new_sl is None or requested_close is not None:
            reasons.append("TRAIL_REQUIRES_ONLY_NEW_STOP")
        else:
            guard = max(stop_distance,freeze_distance)
            if side == "BUY" and not (
                new_sl < bid_p-guard
                and (prior_sl is None or new_sl > prior_sl)):
                reasons.append("BUY_TRAIL_NONPROTECTIVE_OR_BROKER_DISTANCE")
            elif side == "SELL" and not (
                new_sl > ask_p+guard
                and (prior_sl is None or new_sl < prior_sl)):
                reasons.append("SELL_TRAIL_NONPROTECTIVE_OR_BROKER_DISTANCE")
            elif not reasons:
                accepted_sl = new_sl
    research_action = ("WAIT" if reasons else
                       "HOLD_RESEARCH_ONLY" if action == "HOLD" else
                       "EXIT_FEASIBLE_RESEARCH_ONLY")
    data = dict(
        observed_utc=observed_utc.astimezone(timezone.utc).isoformat(),
        symbol=position_symbol, side=side, position_owner=position_owner,
        requested_action=action, research_action=research_action,
        volume_before=str(current),
        close_volume=str(effective_close) if effective_close is not None else None,
        volume_after=str(remainder) if remainder is not None else None,
        proposed_stop=str(accepted_sl) if accepted_sl is not None else None,
        blockers=tuple(sorted(set(reasons))),source_receipt_sha256=source.digest,
    )
    digest=sha256(json.dumps(data,sort_keys=True,separators=(",",":"),
                             allow_nan=False).encode()).hexdigest()
    return OfflineExitFeasibility(receipt_sha256=digest,**data)
