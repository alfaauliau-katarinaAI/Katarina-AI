"""One read-only research synthesis of cognitive memory, curiosity and entry/exit.

Research evidence is matched by EXACT symbol/method/side/regime. This is an
offline review of quote-only observations, never an executable signal.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import sqlite3

from katarina.intelligence.cognition.adaptive_observation import BrainV2Observation
from katarina.intelligence.perception.structure_exit_plan import StructuralExitPlan
from katarina.intelligence.cognition.unified_cognitive_cycle import (
    run_unified_cognitive_cycle, verify_cognitive_history,
)
from katarina.intelligence.cognition.unified_research_handoff import research_handoff

_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class UnifiedOfflineResearchDecision:
    """Immutable evidence assessment; never has permission to place orders."""
    receipt_sha256: str
    as_of_utc: str
    symbol: str
    method: str
    side: str
    regime: str
    entry_exit_receipt_sha256: str
    cognitive_source_sha256: str
    cognitive_active_checkpoint_sha256: str | None
    cognitive_chain_head_sha256: str
    cognitive_mode: str
    action: str
    cohort_status: str | None
    matured_observations: int
    observed_cohort_samples: int
    curiosity_experiment: str | None
    quarantine_reasons: tuple[str, ...]
    learning_scope: str = "PROSPECTIVE_VIRTUAL_QUOTES_ONLY"
    independent_broker_evidence_proven: bool = False
    may_promote_strategy: bool = False
    live_execution_authorized: bool = False
    orders_submitted: int = 0

    def owner_view(self) -> dict:
        return asdict(self)


def synthesize_offline_research(
    db: sqlite3.Connection, *, brain: BrainV2Observation,
    exit_plan: StructuralExitPlan | None, symbol: str, expected_entry: float,
    research_method: str, as_of_utc: datetime, source_digest: str,
    hand_id: str | None = None,
) -> UnifiedOfflineResearchDecision:
    """Fuse current causal quote memory with adaptive Entry/Exit, fail closed.

    'research_method' deliberately has no automatic mapping from a playbook:
    SWEEP and TREND_PULLBACK are not interchangeable just because both BUY.
    A method mismatch is quarantined instead of fabricating learning transfer.
    """
    if (not isinstance(research_method, str) or not research_method
            or len(research_method) > 128):
        raise ValueError("invalid_research_method")
    entry_review = research_handoff(
        brain=brain, exit_plan=exit_plan, symbol=symbol, entry=expected_entry,
        as_of_utc=as_of_utc, source_digest=source_digest, hand_id=hand_id)
    cognition = run_unified_cognitive_cycle(
        db, as_of_utc=as_of_utc, persist=False)
    if (cognition.get("ledger_status") != "READ_ONLY_PREVIEW"
            or cognition.get("orders_submitted") != 0
            or cognition.get("real_execution_authorized") is not False
            or cognition.get("production_mutation_authorized") is not False
            or not isinstance(cognition.get("observation_sha256"), str)
            or not _SHA.fullmatch(cognition["observation_sha256"])):
        raise ValueError("cognitive_research_proof_invalid")
    # Read the persisted Owner-approved research history before interpreting
    # live quote shadow state. A read-only preview must never silently
    # override an Owner rollback or an older active learning checkpoint.
    history = verify_cognitive_history(db)
    if (history.get("integrity") != "VALID"
            or type(history.get("events")) is not int
            or history["events"] < 0
            or not isinstance(history.get("chain_head_sha256"), str)
            or not _SHA.fullmatch(history["chain_head_sha256"])):
        raise ValueError("invalid_cognitive_checkpoint_history")
    key = (symbol, research_method, entry_review.side, entry_review.regime)
    matches = [
        row for row in cognition["semantic_memory"]
        if tuple(row.get(k) for k in ("symbol","method","side","regime")) == key
    ]
    curiosities = [
        row for row in cognition["curiosity_hypotheses"]
        if tuple(row.get(k) for k in ("symbol","method","side","regime")) == key
    ]
    if len(matches) > 1 or len(curiosities) > 1:
        raise ValueError("ambiguous_duplicate_research_cohort")
    cohort = matches[0] if matches else None
    question = curiosities[0] if curiosities else None
    blockers = []
    if history["events"]:
        if (not isinstance(history.get("active_checkpoint_sha256"), str)
                or not _SHA.fullmatch(history["active_checkpoint_sha256"])
                or not isinstance(history.get("active_observation_sha256"), str)
                or not _SHA.fullmatch(history["active_observation_sha256"])):
            raise ValueError("invalid_cognitive_active_checkpoint")
        if history.get("last_event_kind") == "ROLLBACK":
            blockers.append("OWNER_RESEARCH_ROLLBACK_HOLD")
        elif history.get("last_event_kind") != "LEARN":
            raise ValueError("invalid_cognitive_history_event")
        try:
            last_at = datetime.fromisoformat(history["last_event_as_of_utc"])
        except (ValueError, TypeError) as exc:
            raise ValueError("invalid_cognitive_checkpoint_clock") from exc
        if last_at.tzinfo is None or last_at.utcoffset() is None:
            raise ValueError("invalid_cognitive_checkpoint_clock")
        if last_at.astimezone(timezone.utc) > as_of_utc.astimezone(timezone.utc):
            blockers.append("COGNITIVE_HISTORY_NEWER_THAN_RESEARCH_CLOCK")
        if history["active_observation_sha256"] != cognition["observation_sha256"]:
            blockers.append("ACTIVE_COGNITIVE_CHECKPOINT_NOT_CURRENT_SNAPSHOT")
    elif (history.get("last_event_kind") is not None
          or history.get("active_checkpoint_sha256") is not None):
        raise ValueError("invalid_empty_cognitive_history")
    if entry_review.action != "RESEARCH_CANDIDATE":
        blockers.append("ADAPTIVE_ENTRY_OR_EXIT_NOT_RESEARCH_READY")
    if research_method != entry_review.playbook:
        blockers.append("METHOD_TO_PLAYBOOK_NOT_VERIFIED")
    if cohort is None or question is None:
        blockers.append("NO_CAUSALLY_MATCHED_SHADOW_COHORT")
    else:
        if cohort["status"] != question["status"]:
            raise ValueError("cognitive_research_status_contradiction")
        if cohort["status"] != "RESEARCH_CANDIDATE_REVIEW_REQUIRED":
            blockers.append("SHADOW_ALPHA_NOT_VALIDATED")
        if cohort.get("gapped", 0):
            blockers.append("INCOMPLETE_QUOTE_PATHS")
        if not question.get("broker_costs_verified") is False:
            raise ValueError("unsupported_broker_cost_verification")
    # Broker fills, OOS prospective evidence and real costs must be proven
    # separately even when exploratory virtual diagnostics look promising.
    blockers.append("REAL_BROKER_FORWARD_EVIDENCE_MISSING")
    action = ("VIRTUAL_EXPERIMENT_REVIEW_ONLY"
              if not blockers[:-1] else "WAIT")
    details = dict(
        as_of_utc=as_of_utc.astimezone(timezone.utc).isoformat(),
        symbol=symbol, method=research_method, side=entry_review.side,
        regime=entry_review.regime,
        entry_exit_receipt_sha256=entry_review.digest,
        cognitive_source_sha256=cognition["observation_sha256"],
        cognitive_active_checkpoint_sha256=history["active_checkpoint_sha256"],
        cognitive_chain_head_sha256=history["chain_head_sha256"],
        cognitive_mode=cognition["ledger_status"],
        action=action,
        cohort_status=cohort["status"] if cohort else None,
        matured_observations=cognition["matured_observations"],
        observed_cohort_samples=cohort["completed"] if cohort else 0,
        curiosity_experiment=(question["scientific_experiment"]
                              if question else None),
        quarantine_reasons=tuple(sorted(set(blockers))),
    )
    receipt = sha256(json.dumps(
        details, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()
    return UnifiedOfflineResearchDecision(receipt_sha256=receipt, **details)
