"""Brain-owned offline control: health, capital, recovery, audit and OFF gate.

Risk Governor is supplied independently at the boundary. There is deliberately
no transport, order callback, pending-send queue, scheduler or enable switch.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite

from katarina.engines.capital import CapitalCompoundingEngine
from katarina.engines.execution_recovery import ManagementRecoveryCoordinator
from katarina.engines.risk import RiskGovernor, RiskRequest, RiskAction
from katarina.health.engine import HealthSafetyEngine
from katarina.memory.store import MemoryStore

CHECKPOINT = "single_brain_runtime_checkpoint_v1"
SCOPE = "OFFLINE_BRAIN_RUNTIME_ONLY"


class DisabledDeliveryGate:
    """Audit independent risk assessment, then always refuse actual delivery."""

    def inspect(self, plan_id: str, request: RiskRequest, governor: RiskGovernor | None) -> dict:
        if not isinstance(plan_id, str) or not plan_id or not isinstance(request, RiskRequest):
            raise ValueError("invalid_brain_action_plan")
        digest = sha256(json.dumps(asdict(request), sort_keys=True,
                                  allow_nan=False).encode()).hexdigest()
        if not isinstance(governor, RiskGovernor):
            risk_action, risk_reason = "NOT_REVIEWED", "INDEPENDENT_RISK_GOVERNOR_REQUIRED"
        else:
            result = governor.evaluate(request)
            risk_action, risk_reason = result.action.value, result.reason
        return {
            "plan_id":plan_id, "request_sha256":digest,
            "risk_action":risk_action, "risk_reason":risk_reason,
            "risk_allows_review":risk_action in (RiskAction.APPROVE.value, RiskAction.REDUCE.value),
            "delivery_status":"BLOCKED_LIVE_OFF", "queued_for_retry":False,
            "orders_submitted":0, "live_execution_authorized":False,
        }


class BrainRuntimeControl:
    """Internal capabilities share their owner's immutable research memory."""

    def __init__(self, memory: MemoryStore):
        self.memory = memory
        from katarina.intelligence.cognition.owner_research_review import OwnerResearchReview
        self.research_review = OwnerResearchReview(memory)
        self.capital = CapitalCompoundingEngine()
        self.recovery = ManagementRecoveryCoordinator()
        self.health = HealthSafetyEngine()
        self.delivery = DisabledDeliveryGate()
        self.phase = "OFFLINE"
        self.last_error = None
        previous = memory.load_latest_operational_event(CHECKPOINT)
        if previous is not None:
            self.restore(previous["payload"])

    def restore(self, payload: dict) -> None:
        if (not isinstance(payload, dict) or payload.get("scope") != SCOPE
                or payload.get("version") != 1 or payload.get("delivery") != "DISABLED"
                or set(payload) != {"scope", "version", "delivery", "capital", "recovery"}
                or not isinstance(payload["capital"], dict) or not payload["capital"]
                or not isinstance(payload["recovery"], dict)):
            raise ValueError("invalid_offline_brain_checkpoint")
        # Validate both candidates before replacing either live in-memory object.
        capital = CapitalCompoundingEngine()
        capital.restore_state(payload["capital"])
        fields = {"side", "target_remaining_volume", "desired_stop", "origin",
                  "reduce_inflight", "modify_inflight", "last_volume", "last_stop"}
        for position, state in payload["recovery"].items():
            if (not isinstance(position, str) or not position
                    or not isinstance(state, dict) or set(state) != fields
                    or state["side"] not in {"BUY", "SELL"}
                    or state["origin"] != "KATARINA"
                    or type(state["reduce_inflight"]) is not bool
                    or type(state["modify_inflight"]) is not bool):
                raise ValueError("invalid_offline_recovery_checkpoint")
            for name in ("target_remaining_volume", "desired_stop", "last_volume", "last_stop"):
                value = state[name]
                if value is None and name != "target_remaining_volume":
                    continue
                if type(value) not in (int, float) or not isfinite(value) or value < 0:
                    raise ValueError("invalid_offline_recovery_checkpoint")
        recovery = ManagementRecoveryCoordinator()
        recovery.restore_state(payload["recovery"])
        self.capital, self.recovery = capital, recovery
        # Old health/connectivity never grants permission after a restart.
        self.health = HealthSafetyEngine()
        self.phase, self.last_error = "OFFLINE", None

    def checkpoint(self) -> str:
        payload = {
            "scope":SCOPE, "version":1, "delivery":"DISABLED",
            "capital":self.capital.snapshot_state(),
            "recovery":self.recovery.snapshot_state(),
        }
        result = self.memory.append_operational_event(CHECKPOINT, payload)
        return result.record_id

    def audit_phase(self, phase: str, *, error: Exception | None = None) -> dict:
        if phase not in {"OBSERVING", "COMPLETE", "BLOCKED"}:
            raise ValueError("invalid_brain_runtime_phase")
        self.phase = phase
        self.last_error = type(error).__name__ if error is not None else None
        # No credentials, account identities, paths or exception messages in audit.
        event = {
            "scope":SCOPE, "phase":phase, "error_type":self.last_error,
            "observed_at_utc":datetime.now(timezone.utc).isoformat(),
            "orders_submitted":0, "live_execution_authorized":False,
        }
        self.memory.append_operational_event("single_brain_runtime_audit_v1", event)
        return event

    def snapshot(self) -> dict:
        return {
            "phase":self.phase, "last_error_type":self.last_error,
            "capital_initialized":self.capital.initialized,
            "capital_scope":SCOPE, "capital_automatically_migrated":False,
            "recovery_positions":len(self.recovery.snapshot_state()),
            "health_requires_fresh_observations":True,
            "delivery":"DISABLED", "pending_delivery_queue":0,
            "research_review_scope":"VERSION_BOUND_LOCAL_OWNER_REVIEW_NO_ACTIVATION",
            "orders_submitted":0, "live_execution_authorized":False,
        }
