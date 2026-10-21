"""Unified cognition for the EXISTING read-only Katarina shadow brain.

Runs inside the canonical observer, without a second worker, external models,
code mutation, production promotion or broker orders. Produces deterministic
episodic/semantic memory, descriptive world/regime transitions, falsifiable
causal alternatives, curiosity experiments and metacognitive error reviews.

The append-only SHA256 ledger supports reproducibility, restart and
Owner-initiated research rollback. None of its outputs are broker P/L.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
import json
import sqlite3

from katarina.intelligence.cognition.self_evolution_lab import (
    _read, evaluate_shadow_self_evolution, derive_shadow_research_policy,
)

VERSION = "KATARINA_UNIFIED_COGNITIVE_CYCLE_V1"
GENESIS = "0" * 64
MAX_LEDGER = 50000
MAX_EPISODIC_EXAMPLES = 64
REQUIRED_COLUMNS = (
    "seq", "kind", "as_of_utc", "observation_sha256", "payload_json",
    "previous_sha256", "entry_sha256",
)


def _digest(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True,
                              separators=(",", ":"), allow_nan=False
                              ).encode("utf-8")).hexdigest()


def _utc(at: datetime) -> datetime:
    if not isinstance(at, datetime) or at.tzinfo is None:
        raise ValueError("timezone_aware_cognitive_clock_required")
    t = at.astimezone(timezone.utc)
    if not isfinite(t.timestamp()):
        raise ValueError("invalid_cognitive_clock")
    return t


def _schema(db: sqlite3.Connection, *, create: bool) -> bool:
    exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='katarina_cognitive_ledger'").fetchone()
    if not exists and not create:
        return False
    if not exists:
        db.execute("""CREATE TABLE katarina_cognitive_ledger (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL, as_of_utc TEXT NOT NULL,
            observation_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL,
            previous_sha256 TEXT NOT NULL, entry_sha256 TEXT NOT NULL)""")
    columns = tuple(r[1] for r in db.execute(
        "PRAGMA table_info(katarina_cognitive_ledger)").fetchall())
    if columns != REQUIRED_COLUMNS:
        raise ValueError("cognitive_ledger_schema_mismatch")
    return True


def _history(db: sqlite3.Connection) -> tuple[list[dict], dict | None]:
    if not _schema(db, create=False):
        return [], None
    events = []
    prior = GENESIS
    prior_clock = None
    active = None
    for seq, kind, when, observation, raw, previous, receipt in db.execute(
        "SELECT seq,kind,as_of_utc,observation_sha256,payload_json,"
        "previous_sha256,entry_sha256 FROM katarina_cognitive_ledger "
        "ORDER BY seq ASC"):
        if len(events) >= MAX_LEDGER or kind not in ("LEARN", "ROLLBACK"):
            raise ValueError("cognitive_ledger_limit_or_kind_invalid")
        if seq != len(events) + 1:
            raise ValueError("cognitive_ledger_sequence_gap")
        try:
            if not isinstance(when, str):
                raise ValueError("invalid_ledger_time")
            event_clock = _utc(datetime.fromisoformat(when))
        except (TypeError, ValueError, OverflowError, OSError) as exc:
            raise ValueError("cognitive_ledger_timestamp_invalid") from exc
        if prior_clock is not None and event_clock < prior_clock:
            raise ValueError("cognitive_ledger_clock_regressed")
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("invalid_ledger_payload")
        except (TypeError, ValueError) as exc:
            raise ValueError("cognitive_ledger_payload_corrupt") from exc
        data = dict(seq=seq, kind=kind, as_of_utc=when,
                    observation_sha256=observation, payload=payload,
                    previous_sha256=previous)
        if previous != prior or _digest(data) != receipt:
            raise ValueError("cognitive_ledger_chain_tampered")
        event = dict(data, entry_sha256=receipt)
        if kind == "LEARN":
            if payload.get("version") != VERSION:
                raise ValueError("cognitive_ledger_version_mismatch")
            active = event
        else:
            target = payload.get("target_receipt_sha256")
            selected = next((r for r in events if
                             r["entry_sha256"] == target and
                             r["kind"] == "LEARN"), None)
            if selected is None:
                raise ValueError("cognitive_rollback_target_invalid")
            active = selected
        events.append(event)
        prior = receipt
        prior_clock = event_clock
    return events, active


def _world(rows: list[dict]) -> dict:
    """Observed conditional quote outcomes, not calibrated market forecasts."""
    groups = defaultdict(list)
    timelines = defaultdict(list)
    for r in rows:
        key = (r["symbol"], r["method"], r["side"], r["regime"])
        groups[key].append(r)
        timelines[r["symbol"]].append(r)
    cohort_models = []
    for key, entries in sorted(groups.items()):
        done = [r for r in entries if r["status"] == "VIRTUAL_QUOTED"]
        gaps = sum(r["status"] == "UNCERTAIN_GAP" for r in entries)
        pending = sum(r["status"] == "OPEN" for r in entries)
        matured = len(done) + gaps
        avg = round(sum(r["net_r"] for r in done) / len(done), 6) if done else None
        cohort_models.append({
            "symbol":key[0], "method":key[1], "side":key[2],
            "regime":key[3], "quoted_outcomes":len(done),
            "unobserved_gaps":gaps, "pending":pending,
            "matured_coverage":round(len(done)/matured, 6) if matured else None,
            "descriptive_mean_virtual_r":avg,
            "broker_cost_reconciled":False,
        })
    transitions = []
    for symbol, samples in sorted(timelines.items()):
        chronology = sorted(samples, key=lambda r:(r["observed"],r["id"]))
        counts = Counter((a["regime"], b["regime"])
                         for a,b in zip(chronology, chronology[1:]))
        for (from_regime,to_regime),count in sorted(counts.items()):
            transitions.append(dict(symbol=symbol,from_regime=from_regime,
                                    to_regime=to_regime,observed_count=count))
    return {
        "model_type":"DESCRIPTIVE_REGIME_TRANSITIONS_NOT_PREDICTIVE",
        "cohorts":cohort_models,
        "regime_transitions":transitions,
        "historical_window_rows":len(rows),
        "unseen_future_returns_used":False,
    }


def _hypotheses(report: dict) -> tuple[list[dict], list[dict]]:
    """Falsifiable explanations + disconfirming sandbox tests, no causal claim."""
    questions = []
    error_reviews = []
    for c in report["cohorts"]:
        key = {x:c[x] for x in ("symbol","method","side","regime")}
        status=c["status"]
        reason = {
            "INSUFFICIENT_EVIDENCE":"MORE_CLOSED_OUTCOMES_REQUIRED",
            "HOLDOUT_INSUFFICIENT":"OUT_OF_SAMPLE_UNDERPOWERED",
            "UNSTABLE_OR_NEGATIVE_QUOTE_EDGE":"NEGATIVE_OR_UNSTABLE_HELDOUT",
            "RESEARCH_CANDIDATE_REVIEW_REQUIRED":"POSITIVE_VIRTUAL_DIAGNOSTIC_NEEDS_REPLICATION",
        }.get(status,"UNRECOGNIZED_RESEARCH_STATUS")
        c["baseline"]  # required field: a malformed candidate is rejected with KeyError
        training = c.get("training") or {}
        holdout = c.get("holdout") or {}
        if ((training.get("mean_modelled_r") or 0)>0
                and (holdout.get("mean_modelled_r") or 0)<=0
                and holdout.get("observations",0)>0):
            error_reviews.append({**key,"error":"TRAIN_TO_HOLDOUT_SIGN_REVERSAL",
                                  "remedy":"REJECT_SELECTION_AND_PREREGISTER_NEW_FORWARD_WINDOW"})
        if (c.get("coverage") is not None and c["coverage"]<.80):
            error_reviews.append({**key,"error":"MISSING_QUOTE_PATH_BIAS",
                                  "remedy":"RECOVER_CAUSAL_TICK_COVERAGE_WITHOUT_FILL_IMPUTATION"})
        if status == "RESEARCH_CANDIDATE_REVIEW_REQUIRED":
            action="PRECOMMIT_NEW_UNSEEN_QUOTE_SAMPLE"
            question="Does the association persist on NEW untouched quotes after actual spread and costs?"
        elif status == "UNSTABLE_OR_NEGATIVE_QUOTE_EDGE":
            action="TEST_DIFFERENT_METHOD_OR_WAIT"
            question="Does a different pre-registered setup outperform WAIT under the same regime?"
        else:
            action="COLLECT_COMPLETE_CAUSAL_OBSERVATIONS"
            question="Can the sampling gap and independent-day minimum be resolved without selection bias?"
        questions.append({
            **key,"question":question,"status":status,
            "curiosity_priority":(3 if status=="INSUFFICIENT_EVIDENCE"
                                  else 2 if status=="HOLDOUT_INSUFFICIENT"
                                  else 1 if status=="RESEARCH_CANDIDATE_REVIEW_REQUIRED"
                                  else 0),
            "scientific_experiment":action,
            "hypothesis":"Method/side/regime may correlate with future quote outcomes",
            "causal_alternatives":[
                "unobserved volatility or macro confounder",
                "spread and execution costs",
                "selection bias from incomplete quote paths",
            ],
            "falsification":"Disconfirm on new chronological observations, including all gaps",
            "broker_execution_claim":False,
            "reason":reason, "completed_samples":c.get("completed",0),
            "missing_samples":c.get("gapped",0),
            "trained_threshold":c.get("proposed_min_evidence_score"),
            "virtual_train_mean_r":training.get("mean_modelled_r"),
            "virtual_holdout_mean_r":holdout.get("mean_modelled_r"),
            "broker_costs_verified":False,
        })
    questions.sort(key=lambda q:(-q["curiosity_priority"],
                                  q["symbol"],q["method"],q["side"],q["regime"]))
    return questions,error_reviews


def _compute(db: sqlite3.Connection, at: datetime) -> dict:
    clock = _utc(at)
    rows, issue = _read(db, clock.timestamp())
    if issue:
        raise ValueError("cognitive_shadow_evidence_invalid:" + issue)
    report = evaluate_shadow_self_evolution(db, as_of_utc=clock)
    if report["data_integrity"] != "VALID":
        raise ValueError("cognitive_learning_report_invalid")
    policy = derive_shadow_research_policy(report)
    if not policy.integrity_ok:
        raise ValueError("cognitive_learning_policy_invalid")
    # The persistent identity is independent of the wall clock; only CLOSED
    # outcomes are fingerprints. Open position/time updates are not learning.
    matured = [{k:r[k] for k in (
        "id","symbol","method","side","regime","observed","exited",
        "status","net_r","score","news_verified")} for r in rows
        if r["status"] != "OPEN"]
    source = _digest(matured)
    questions, errors = _hypotheses(report)
    incomplete = sum(c["gapped"] for c in report["cohorts"])
    no_news = sum(not r["news_verified"] for r in matured)
    reflections = {
        "uncertainty_flags":sorted(set(
            (["REAL_BROKER_FILLS_MISSING","ACTUAL_COSTS_UNVERIFIED",
              "NO_CAUSAL_INTERVENTION_PROOF","UNSEEN_PROSPECTIVE_ALPHA_NOT_PROVEN"]
             + (["QUOTE_PATH_GAPS"] if incomplete else [])
             + (["OFFICIAL_NEWS_INCOMPLETE"] if no_news else [])
             + (["NO_MATURE_OBSERVATIONS"] if not matured else [])))),
        "error_reviews":errors,
        "can_modify_own_code":False,
        "may_promote_strategy":False,
        "review_critics_from_existing_lab":report["reviewers"],
    }
    return {
        "version":VERSION,
        "as_of_utc":clock.isoformat(),
        "matured_observations":len(matured),
        "observation_sha256":source,
        "episodic_memory":matured[-MAX_EPISODIC_EXAMPLES:],
        "semantic_memory":[{k:c.get(k) for k in (
            "symbol","method","side","regime","status",
            "recorded","completed","gapped","pending","coverage",
            "proposed_min_evidence_score")}
                           for c in report["cohorts"]],
        "world_model":_world(rows),
        "causal_reasoning":"FALSIFIABLE_ASSOCIATIONS_NO_CAUSAL_CERTAINTY",
        "curiosity_hypotheses":questions,
        "scientific_experiment_review":{
            "method":"PREREGISTERED_CHRONOLOGICAL_TRAIN_HOLDOUT_VIRTUAL_QUOTES",
            "tested_groups":len(report["cohorts"]),
            "quote_candidates_for_independent_review":sum(
                c["status"]=="RESEARCH_CANDIDATE_REVIEW_REQUIRED"
                for c in report["cohorts"]),
            "production_action":"WAIT",
            "heldout_not_independent_real_forward":True,
        },
        "metacognition":reflections,
        "next_shadow_sampling_policy":policy.to_dict(),
        "orders_submitted":0,
        "real_execution_authorized":False,
        "production_mutation_authorized":False,
        "requires_owner_approval_for_production":True,
    }


def verify_cognitive_history(db: sqlite3.Connection) -> dict:
    """Pure read-only receipt verification; does not mutate the ledger."""
    events, active = _history(db)
    return {
        "events":len(events),
        "active_checkpoint_sha256":active["entry_sha256"] if active else None,
        "active_observation_sha256":active["observation_sha256"] if active else None,
        "active_checkpoint_as_of_utc":active["as_of_utc"] if active else None,
        "chain_head_sha256":events[-1]["entry_sha256"] if events else GENESIS,
        "last_event_kind":events[-1]["kind"] if events else None,
        "last_event_as_of_utc":events[-1]["as_of_utc"] if events else None,
        "integrity":"VALID",
    }


def run_unified_cognitive_cycle(
    db: sqlite3.Connection, *, as_of_utc: datetime,
    persist: bool = True,
) -> dict:
    """One bounded iteration; idempotent and restart-safe on existing DB."""
    clock = _utc(as_of_utc)
    # Validate data BEFORE creating any ledger or modifying persistent memory.
    episode = _compute(db, clock)
    if not persist:
        return {**episode,"ledger_status":"READ_ONLY_PREVIEW",
                "active_checkpoint_sha256":None}
    with db:
        _schema(db, create=True)
        events, active = _history(db)
        if events and clock < _utc(datetime.fromisoformat(events[-1]["as_of_utc"])):
            raise ValueError("cognitive_learning_clock_regressed")
        identical = next((e for e in reversed(events)
                          if e["kind"]=="LEARN" and
                          e["observation_sha256"]==episode["observation_sha256"]),None)
        if identical:
            active_matches = bool(
                active and active["entry_sha256"] == identical["entry_sha256"])
            return {**(identical["payload"] if active_matches
                       else active["payload"]),
                    "ledger_status":("ALREADY_LEARNED_NO_REWRITE" if active_matches
                                     else "OWNER_ROLLBACK_HOLD_NEW_RESEARCH"),
                    "active_checkpoint_sha256":active["entry_sha256"] if active else None,
                    "source_snapshot_matches_active":active_matches}
        if len(events)>=MAX_LEDGER:
            raise ValueError("cognitive_ledger_capacity_reached")
        prev=events[-1]["entry_sha256"] if events else GENESIS
        seq=events[-1]["seq"]+1 if events else 1
        event=dict(seq=seq,kind="LEARN",as_of_utc=clock.isoformat(),
                   observation_sha256=episode["observation_sha256"],
                   payload=episode,previous_sha256=prev)
        receipt=_digest(event)
        db.execute("""INSERT INTO katarina_cognitive_ledger(
            seq,kind,as_of_utc,observation_sha256,payload_json,
            previous_sha256,entry_sha256) VALUES (?,?,?,?,?,?,?)""",(
            seq,"LEARN",clock.isoformat(),episode["observation_sha256"],
            json.dumps(episode,sort_keys=True,separators=(",",":"),
                       allow_nan=False),prev,receipt))
        return {**episode,"ledger_status":"LEARNED_AND_CHECKPOINTED",
                "active_checkpoint_sha256":receipt,
                "source_snapshot_matches_active":True}


def rollback_cognitive_research(
    db: sqlite3.Connection, *, to_receipt_sha256: str,
    as_of_utc: datetime, owner_approved: bool = False,
) -> dict:
    """Append an Owner-approved research rollback. Never reverts broker data."""
    clock=_utc(as_of_utc)
    if owner_approved is not True:
        raise PermissionError("owner_approval_required_for_rollback")
    with db:
        events, active=_history(db)
        if not events:
            raise ValueError("no_cognitive_checkpoint")
        target=next((x for x in events if
                     x["entry_sha256"]==to_receipt_sha256 and
                     x["kind"]=="LEARN"),None)
        if target is None:
            raise ValueError("unknown_or_nonlearn_checkpoint")
        if datetime.fromisoformat(target["as_of_utc"]) > clock:
            raise ValueError("future_rollback_checkpoint_forbidden")
        if clock < _utc(datetime.fromisoformat(events[-1]["as_of_utc"])):
            raise ValueError("cognitive_rollback_clock_regressed")
        if active and active["entry_sha256"]==target["entry_sha256"]:
            return {"rollback":"ALREADY_ACTIVE",
                    "active_checkpoint_sha256":to_receipt_sha256}
        if len(events)>=MAX_LEDGER:
            raise ValueError("cognitive_ledger_capacity_reached")
        prev=events[-1]["entry_sha256"]
        seq=events[-1]["seq"]+1
        payload={"target_receipt_sha256":to_receipt_sha256,
                 "reason":"OWNER_APPROVED_RESEARCH_ONLY_ROLLBACK",
                 "live_authorization":False}
        event=dict(seq=seq,kind="ROLLBACK",as_of_utc=clock.isoformat(),
                   observation_sha256=target["observation_sha256"],
                   payload=payload,previous_sha256=prev)
        receipt=_digest(event)
        db.execute("""INSERT INTO katarina_cognitive_ledger(
            seq,kind,as_of_utc,observation_sha256,payload_json,
            previous_sha256,entry_sha256) VALUES (?,?,?,?,?,?,?)""",(
            seq,"ROLLBACK",clock.isoformat(),target["observation_sha256"],
            json.dumps(payload,sort_keys=True,separators=(",",":"),
                       allow_nan=False),prev,receipt))
        return {"rollback":"OWNER_RESEARCH_ROLLBACK_RECORDED",
                "active_checkpoint_sha256":to_receipt_sha256,
                "new_audit_receipt_sha256":receipt,
                "orders_submitted":0,"live_authorization":False}
