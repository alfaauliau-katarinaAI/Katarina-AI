"""Single manual, no-orders acceptance view of the *existing* Katarina stack.

Does not start MT5, connect networks, create workers, place orders, alter
configurations, write data or authorize promotions. Intended for pinned
GitHub/VPS source synchronization and optional read-only shadow DB checking.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "src"))


def build_stage3_evidence_backlog(report: dict) -> dict:
    """Read-only collection checklist; it never overrides any trading gate.

    Cohort rows come exclusively from the validated, past-only shadow lab.
    No fabricated targets or thresholds are supplied for deferred decisions.
    """
    if report.get("data_integrity") != "VALID":
        raise ValueError("stage3_evidence_source_not_verified")
    cohorts = report.get("cohorts")
    if not isinstance(cohorts, list):
        raise ValueError("stage3_evidence_cohorts_invalid")
    items = []
    for cohort in sorted(cohorts, key=lambda c: (
            c["symbol"], c["method"], c["side"], c["regime"])):
        tasks = []
        if cohort["gapped"] > 0:
            tasks.append("RECOVER_MISSING_CAUSAL_QUOTE_PATHS_WITHOUT_IMPUTATION")
        if cohort["pending"] > 0:
            tasks.append("WAIT_FOR_OPEN_VIRTUAL_OBSERVATIONS_TO_CLOSE")
        if cohort["status"] == "INSUFFICIENT_EVIDENCE":
            tasks.append("COLLECT_MORE_INDEPENDENT_CLOSED_QUOTE_OUTCOMES")
        elif cohort["status"] == "HOLDOUT_INSUFFICIENT":
            tasks.append("EXTEND_UNSEEN_CHRONOLOGICAL_HOLDOUT")
        elif cohort["status"] == "UNSTABLE_OR_NEGATIVE_QUOTE_EDGE":
            tasks.append("PRECOMMIT_DISCONFIRMING_ALTERNATIVE_OR_WAIT")
        elif cohort["status"] == "RESEARCH_CANDIDATE_REVIEW_REQUIRED":
            tasks.append("REPLICATE_ON_NEW_UNSEEN_FORWARD_WINDOW")
        else:
            raise ValueError("stage3_evidence_status_unknown")
        items.append({
            "symbol": cohort["symbol"], "method": cohort["method"],
            "side": cohort["side"], "regime": cohort["regime"],
            "research_status": cohort["status"],
            "observations_recorded": cohort["recorded"],
            "completed_virtual_outcomes": cohort["completed"],
            "unobserved_quote_gaps": cohort["gapped"],
            "pending_virtual_outcomes": cohort["pending"],
            "quote_coverage": cohort["coverage"],
            "next_research_tasks": tasks,
            "broker_edge_proven": False,
        })
    return {
        "mode": "READ_ONLY_EVIDENCE_COLLECTION_BACKLOG",
        "observed_shadow_rows": report["rows_read"],
        "cohorts": items,
        "common_unverified_evidence": [
            "AUTHENTICATED_BROKER_BID_ASK_AND_SESSION_TIME",
            "ACTUAL_SPREAD_COMMISSION_SLIPPAGE_AND_EXECUTION_FILLS",
            "PRECOMMITTED_UNSEEN_PROSPECTIVE_FORWARD_EVALUATION",
        ],
        "no_automatic_data_collection": True,
        "may_promote_strategy": False,
        "may_authorize_live": False,
        "orders_submitted": 0,
    }


def verify(profile: dict, *, root: Path = ROOT, shadow_db: Path | None = None) -> dict:
    if profile.get("schema_version") != 1 or profile.get("profile") != "KATARINA_UNIFIED_V1_RESEARCH_ONLY":
        raise ValueError("unrecognized_unified_profile")
    parts=profile.get("canonical")
    disabled=profile.get("deferred")
    modes=profile.get("operating_mode")
    # One brain owns perception, cognition and shared knowledge; no specialist runtime.
    expected_parts = {
        "core", "brain", "observer", "shadow", "risk",
        "manual_positions", "capital", "broker_readonly",
        "recovery", "runtime_memory", "cognition", "knowledge_memory",
        "market_perception", "adaptive_research", "runtime_control", "market_sensor", "health",
    }
    if (not isinstance(parts,dict) or set(parts)!=expected_parts
            or not isinstance(disabled,dict)):
        raise ValueError("incomplete_unified_component_registry")
    if profile.get("organization") != {
        "architecture":"SINGLE_COGNITIVE_BRAIN", "management":"REMOVED",
        "specialist_workers":0,
    } or "on_hold" in profile:
        raise ValueError("single_brain_organization_required")
    expected_paths = {
        "brain":"src/katarina/intelligence/unified_brain.py",
        "observer":"src/katarina/intelligence/brain_observer.py",
        "runtime_control":"src/katarina/intelligence/brain_runtime_control.py",
        "market_sensor":"src/katarina/adapters/mt5_readonly_market.py",
        "health":"src/katarina/health/engine.py",
        "cognition":"src/katarina/intelligence/unified_cognitive_cycle.py",
        "knowledge_memory":"src/katarina/memory/neuro_link.py",
        "market_perception":"src/katarina/intelligence/market_decision_brain_v3.py",
        "adaptive_research":"src/katarina/intelligence/unified_adaptive_research_cycle.py",
    }
    if any(parts.get(k) != v for k,v in expected_paths.items()):
        raise ValueError("invalid_canonical_single_brain_path")
    if profile.get("architecture_contract") != "config/katarina_brain_boundary_v1.json":
        raise ValueError("brain_boundary_contract_required")
    boundary=json.loads((root/profile["architecture_contract"]).read_text())
    if (boundary.get("owner") != "UnifiedKatarinaBrain"
            or boundary.get("delivery_mode") != "DISABLED"
            or boundary.get("background_workers") != 0
            or boundary.get("risk_governor_owned_by_brain") is not False
            or set(boundary.get("external_boundaries", [])) != {
                "independent_risk_governor", "cloud_hands_with_local_survival_guardian",
                "mt5", "broker", "portable_host", "configured_language_model",
                "owner_granted_research_sources", "owner_browser_surface"}
            or set(boundary.get("internal_capabilities", [])) != {
                "observer", "market_perception", "cognition", "knowledge_memory", "shadow",
                "adaptive_research", "capital", "recovery", "health", "runtime_control",
                "core", "manual_positions", "runtime_memory", "dialog", "model_routing",
                "bounded_tools", "dialog_history", "nonexecuting_feedback"}):
        raise ValueError("brain_boundary_contract_mismatch")
    if set(disabled)!={
        "external_ai_workers","autonomous_source_rewrite",
        "unverified_broker_provenance","unverified_broker_clock",
        "automatic_capital_state_migration","background_scheduler",
        "live_execution"
    } or any(type(flag) is not bool or flag for flag in disabled.values()):
        raise ValueError("unapproved_unified_capability_enabled")
    if not isinstance(modes,dict) or modes.get("order_submission")!="DISABLED":
        raise ValueError("order_submission_must_remain_disabled")
    if "management" in modes:
        raise ValueError("single_brain_organization_required")
    if modes.get("core")!="TESTER_ONLY" or modes.get("broker")!="OFFLINE_ADAPTER_IMPORT_ONLY":
        raise ValueError("unsafe_runtime_mode")
    limits=profile.get("owner_limits")
    expected={
        "profit_lock_fraction":.25,
        "max_risk_per_entry_fraction":.05,
        "max_open_risk_fraction":.08,
        "caution_drawdown_from":.10,
        "recovery_only_from":.23,
        "extreme_drawdown_from":.35,
    }
    if not isinstance(limits,dict) or set(limits)!=set(expected) or any(
        type(limits[k]) not in (float,int) or limits[k]!=v
        for k,v in expected.items()
    ):
        raise ValueError("owner_limits_changed")
    digest={}
    for name,rel in sorted(parts.items()):
        if (not isinstance(rel,str) or not rel.startswith(("src/","scripts/"))
                or Path(rel).is_absolute() or ".." in Path(rel).parts):
            raise ValueError("invalid_canonical_module_path")
        path=root/rel
        if not path.is_file():
            raise ValueError("missing_canonical_component:"+name)
        digest[name]=sha256(path.read_bytes()).hexdigest()

    # Validate actual import and construction of non-trading core, risk,
    # reserve accounting and a real but order-free shadow learning path.
    from katarina.contracts.runtime import RuntimeMode
    from katarina.core.orchestrator import KatarinaOrchestrator,OrchestratorConfig
    from katarina.engines.risk import (
        RiskGovernor, RiskRequest, RiskAction, DrawdownAuthority, DrawdownMode,
    )
    from katarina.engines.capital import CapitalCompoundingEngine
    from katarina.intelligence.prospective_shadow_book import ProspectiveShadowBook
    from katarina.intelligence.self_evolution_lab import (
        evaluate_shadow_self_evolution,derive_shadow_research_policy,
    )
    from katarina.intelligence.unified_brain import UnifiedKatarinaBrain
    from katarina.memory.store import MemoryStore
    from katarina.adapters.mt5_account_pnl import Mt5ReadOnlyPnLAdapter
    core=KatarinaOrchestrator(OrchestratorConfig(RuntimeMode.TESTER,32))
    governor=RiskGovernor.from_config(root/"config/risk_governor_v2.json")
    capital=CapitalCompoundingEngine()
    if core.new_live_risk_allowed or capital.reserve_fraction!=.25:
        raise ValueError("unsafe_core_or_capital")
    # The Owner's rule is ADDITIVE 25% of actual balance at EACH doubling,
    # not merely a nominal config value. Exercise a separate offline ledger;
    # no real broker state is read or modified.
    capital.initialize(10_000)
    for observed, reserve, active in (
        (20_000, 5_000, 15_000),
        (40_000, 15_000, 25_000),
        (80_000, 35_000, 45_000),
    ):
        event=capital.observe_balance(observed)
        snapshot=capital.snapshot()
        if (not event.milestone_triggered
                or abs(snapshot.reserve_balance-reserve)>1e-8
                or abs(snapshot.active_balance-active)>1e-8):
            raise ValueError("cumulative_profit_lock_policy_mismatch")
        # Retries, duplicate snapshots and restarts must not lock again.
        if (capital.observe_balance(observed).milestone_triggered
                or abs(capital.snapshot().reserve_balance-reserve)>1e-8):
            raise ValueError("duplicate_profit_lock_milestone")
    restored=CapitalCompoundingEngine()
    restored.restore_state(capital.snapshot_state())
    if (restored.observe_balance(80_000).milestone_triggered
            or abs(restored.snapshot().reserve_balance-35_000)>1e-8):
        raise ValueError("profit_lock_restart_idempotence_mismatch")
    if (governor.hard_per_trade>.05 or governor.max_open_risk>.08
            or governor.max_drawdown>.35 or governor.max_daily_drawdown>.35):
        raise ValueError("owner_risk_limits_exceeded")
    # Same-day emergency latching is a final Owner safety rule.
    # A return below the nominal DD threshold must not reopen new entry.
    locked=DrawdownAuthority(
        "broker-day", DrawdownMode.EMERGENCY_LOCKDOWN, .12, False, True,
    )
    for kind in ("NORMAL", "RECOVERY_FACTOR", "EXTREME_RECOVERY"):
        decision=governor.evaluate(RiskRequest(
            .01, 0., .12, .1, 2., True, True, .12,
            entry_kind=kind, trading_day_key="broker-day",
            drawdown_authority=locked,
            risk_capital=8800, risk_reference_capital=10000,
            account_currency="USD",
        ))
        if decision.action is not RiskAction.PAUSE or decision.approved_fraction!=0:
            raise ValueError("same_day_emergency_lockdown_bypass")
    if not callable(Mt5ReadOnlyPnLAdapter):
        raise ValueError("broker_read_only_adapter_missing")
    if shadow_db is None:
        db=sqlite3.connect(":memory:")
        db_source="IN_MEMORY_EMPTY_NO_MARKET_EDGE"
        source_path=None
    else:
        target=Path(shadow_db).resolve(strict=True)
        if not target.is_file() or target.suffix.lower() not in (".db",".sqlite",".sqlite3"):
            raise ValueError("invalid_readonly_shadow_db")
        db=sqlite3.connect("file:"+target.as_posix()+"?mode=ro",uri=True)
        db_source="READ_ONLY_EXISTING_SQLITE"
        source_path=str(target)
    memory=MemoryStore(":memory:")
    try:
        if shadow_db is None:
            ProspectiveShadowBook(db)
        now=datetime.now(timezone.utc)
        report=evaluate_shadow_self_evolution(db,as_of_utc=now)
        proposal=derive_shadow_research_policy(report)
        brain=UnifiedKatarinaBrain(db,memory)
        unified=brain.run_unified_cognitive_cycle(
            as_of_utc=now,persist=False)
        cognitive=unified["cognition"]
        gate=brain.control.delivery.inspect(
            "offline-acceptance", RiskRequest(.01,0.,0.,.1,2.,True,True), governor)
        if (gate["delivery_status"] != "BLOCKED_LIVE_OFF" or gate["orders_submitted"] != 0
                or gate["queued_for_retry"] or gate["live_execution_authorized"]):
            raise RuntimeError("brain_delivery_gate_bypass")
        if (cognitive["orders_submitted"]!=0
                or cognitive["real_execution_authorized"]
                or cognitive["production_mutation_authorized"]
                or cognitive["ledger_status"]!="READ_ONLY_PREVIEW"):
            raise RuntimeError("unified_brain_safety_violation")
    finally:
        memory.close()
        db.close()
    return {
        "profile":profile["profile"],
        "status":"INTEGRATED_OFFLINE_ENGINEERING_ONLY",
        "modules_verified":len(digest),
        "module_sha256":digest,
        "mode":"TESTER_NO_ORDERS",
        "management":"REMOVED",
        "brain_architecture":unified["architecture"],
        "specialist_workers":unified["specialist_workers"],
        "neuro_link_shared_memory":unified["knowledge_memory"]["shared_memory"],
        "runtime_owner":"UnifiedKatarinaBrain",
        "internal_capabilities":boundary["internal_capabilities"],
        "independent_risk_external":True,
        "delivery_gate":gate["delivery_status"],
        "cumulative_profit_lock":"VERIFIED_THREE_MILESTONES_AND_RESTART",
        "same_day_emergency_lockdown":"VERIFIED_NO_NEW_ENTRY",
        "unverified_optional_components_disabled":True,
        "shadow_source":db_source,
        "shadow_db_path":source_path,
        "shadow_observations":report["rows_read"],
        "shadow_cohorts":len(report["cohorts"]),
        "stage3_evidence_backlog":build_stage3_evidence_backlog(report),
        "learning_integrity":report["data_integrity"],
        "learning_policy_valid":proposal.integrity_ok,
        "learning_source_sha256":report["source_digest_sha256"],
        "unified_cognitive_cycle":"COMPLETE_READONLY_PREVIEW",
        "cognitive_matured_samples":cognitive["matured_observations"],
        "cognitive_epistemic_gaps":len(
            cognitive["metacognition"]["uncertainty_flags"]),
        "cognitive_curiosity_experiments":len(
            cognitive["curiosity_hypotheses"]),
        "cognitive_no_real_orders":cognitive["orders_submitted"]==0,
        "real_broker_edge_proven":False,
        "human_live_approval":False,
        "live_execution_authorized":False,
        "orders_submitted":0,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",type=Path,default=ROOT/"config/katarina_unified_v1.json")
    parser.add_argument("--shadow-db",type=Path,default=None)
    args=parser.parse_args()
    profile=json.loads(args.profile.read_text(encoding="utf-8"))
    print(json.dumps(verify(profile,shadow_db=args.shadow_db),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
