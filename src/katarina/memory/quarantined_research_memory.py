"""Append-only, quarantine-first memory of untrusted research/Hand receipts.

This ledger stores raw research observations from Adaptive Brain/Entry/Exit
without treating duplicated Hands or hashes as independent alpha evidence.
It never promotes a strategy, updates risk or sends a broker command.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3

from katarina.intelligence.cognition.unified_research_handoff import OwnerResearchReceipt
from katarina.intelligence.lab.offline_hand_telemetry import consolidate_hand_reports

_TABLE = "katarina_quarantined_research_memory"
_COLUMNS = ("id","hand_id","symbol","observed_utc","source_digest",
            "payload_json","payload_sha256")
_MAX_ROWS = 50000


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False)


def _invalid_constant(token: str) -> None:
    raise ValueError("research_memory_nonfinite_number:" + token)


def _parse(row: dict) -> dict:
    raw, digest = row["payload_json"], row["payload_sha256"]
    if (not isinstance(raw, str) or not isinstance(digest, str)
            or sha256(raw.encode()).hexdigest() != digest):
        raise ValueError("quarantined_research_memory_digest_mismatch")
    try:
        value = json.loads(raw, parse_constant=_invalid_constant)
    except (ValueError, TypeError) as exc:
        raise ValueError("quarantined_research_memory_payload_invalid") from exc
    if (not isinstance(value, dict) or
            any(value.get(k) != row[k] for k in
                ("hand_id","symbol","observed_utc","source_digest")) or
            value.get("live_execution_authorized") is not False or
            value.get("orders_submitted") != 0 or
            value.get("controls") != "READ_ONLY" or
            value.get("hand_trust") != "UNVERIFIED_TELEMETRY"):
        raise ValueError("quarantined_research_memory_evidence_invalid")
    return value


def _schema(db: sqlite3.Connection, *, create: bool) -> bool:
    exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (_TABLE,)).fetchone()
    if exists is None and not create:
        return False
    if exists is None:
        db.execute(f"""CREATE TABLE {_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            observed_utc TEXT NOT NULL,
            source_digest TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            UNIQUE(hand_id, symbol, observed_utc)
        )""")
    columns = tuple(row[1] for row in db.execute(
        f"PRAGMA table_info({_TABLE})"))
    if columns != _COLUMNS:
        raise ValueError("quarantined_research_memory_schema_mismatch")
    if create:
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS {_TABLE}_no_update
                      BEFORE UPDATE ON {_TABLE} BEGIN
                      SELECT RAISE(ABORT, 'research_memory_append_only');
                      END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS {_TABLE}_no_delete
                      BEFORE DELETE ON {_TABLE} BEGIN
                      SELECT RAISE(ABORT, 'research_memory_append_only');
                      END""")
    return True


@dataclass(frozen=True)
class ResearchMemoryAppend:
    inserted: bool
    receipt_sha256: str
    status: str = "QUARANTINED_UNAUTHENTICATED_SOURCE"


def append_quarantined_research(
    db: sqlite3.Connection, *, receipt: OwnerResearchReceipt,
    inspected_at_utc: datetime,
) -> ResearchMemoryAppend:
    """Validate receipt consistency and persist without trusting its sender."""
    # Input checks happen before any schema writes.
    consolidate_hand_reports([receipt], inspected_at_utc=inspected_at_utc)
    raw = _canonical(receipt.owner_view())
    digest = sha256(raw.encode()).hexdigest()
    with db:
        _schema(db, create=True)
        existing = db.execute(
            f"SELECT * FROM {_TABLE} WHERE hand_id=? AND symbol=? "
            "AND observed_utc=?",
            (receipt.hand_id, receipt.symbol, receipt.observed_utc),
        ).fetchone()
        if existing:
            verified_existing = dict(zip(_COLUMNS, existing))
            _parse(verified_existing)
            if verified_existing["payload_sha256"] != digest:
                raise ValueError("quarantined_research_idempotency_conflict")
            return ResearchMemoryAppend(False, digest)
        count = db.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0]
        if count >= _MAX_ROWS:
            raise ValueError("quarantined_research_capacity_exceeded")
        db.execute(
            f"INSERT INTO {_TABLE} (hand_id,symbol,observed_utc,"
            "source_digest,payload_json,payload_sha256) VALUES (?,?,?,?,?,?)",
            (receipt.hand_id, receipt.symbol, receipt.observed_utc,
             receipt.source_digest, raw, digest))
    return ResearchMemoryAppend(True, digest)


def read_quarantined_research(
    db: sqlite3.Connection, *, as_of_utc: datetime,
) -> dict:
    """Read-only review; origin remains unverified after local SHA checks."""
    if (not isinstance(as_of_utc, datetime) or as_of_utc.tzinfo is None
            or as_of_utc.utcoffset() is None):
        raise ValueError("invalid_research_memory_review_clock")
    clock = as_of_utc.astimezone(timezone.utc)
    rows = []
    if _schema(db, create=False):
        cursor = db.execute(
            f"SELECT * FROM {_TABLE} ORDER BY observed_utc,hand_id,symbol")
        for stored in cursor:
            row = dict(zip(_COLUMNS, stored))
            value = _parse(row)
            try:
                observed = datetime.fromisoformat(value["observed_utc"])
            except (TypeError, ValueError) as exc:
                raise ValueError("quarantined_research_time_invalid") from exc
            if observed.tzinfo is None or observed.utcoffset() is None:
                raise ValueError("quarantined_research_time_invalid")
            if observed.astimezone(timezone.utc) <= clock:
                rows.append(value)
    reused = {}
    for row in rows:
        key = (row["symbol"], row["source_digest"])
        reused.setdefault(key, set()).add(row["hand_id"])
    repeated = tuple(sorted({
        symbol for (symbol, _), hands in reused.items() if len(hands) > 1
    }))
    return {
        "status":"QUARANTINED_UNAUTHENTICATED_RESEARCH_MEMORY",
        "as_of_utc":clock.isoformat(),
        "recorded_receipts":len(rows),
        "reported_source_fingerprints":len(reused),
        "reused_source_symbols":repeated,
        "next_curiosity_tasks":tuple({
            "symbol":symbol,
            "experiment":"COLLECT_NEW_INDEPENDENT_CAUSAL_QUOTE_SOURCES",
            "production_action":"WAIT",
        } for symbol in repeated),
        "owner_reports":tuple(rows),
        "source_origin_authenticated":False,
        "independent_alpha_samples_proven":False,
        "may_promote_strategy":False,
        "live_execution_authorized":False,
        "orders_submitted":0,
    }
