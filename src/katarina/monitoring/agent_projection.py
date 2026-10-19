"""Read-only owner-facing projection of ONE canonical Katarina brain.

These are capability lanes, not additional agents, processes or trade permissions.
Never infer component execution from a repository file or a healthy heartbeat.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Any

LANES = (
    ("SCAN", "Observasi pasar dan validasi sumber"),
    ("ANALYST", "Penalaran dan analisis peluang"),
    ("STRATEGY", "Evaluasi strategi dan rencana"),
    ("BALANCE", "Penilaian risiko dan eksposur"),
    ("EXEC", "Gerbang eksekusi MT5"),
    ("AUDIT", "Bukti observasi dan journal"),
)


def project_agent_board(evidence: Mapping[str, Any], *, delivery: str = "DISABLED") -> dict:
    """Render only independently supported fields from the existing /status check.

    Data is supplied by runtime_evidence.read_runtime, which already handles
    freshness, ACK and live-off invariants. No file, lock or account I/O here.
    """
    if not isinstance(evidence, Mapping):
        evidence = {}
    passed = evidence.get("result") == "PASS_READONLY_SNAPSHOT_ONLY"
    count = evidence.get("received_market_data_symbols")
    cycles = evidence.get("cycles")
    successful = evidence.get("successful_cycles")
    if type(count) is not int or not 1 <= count <= 17:
        count = None
    if type(cycles) is not int or cycles < 0:
        cycles = None
    if type(successful) is not int or successful < 0:
        successful = None
    blockers = evidence.get("blockers")
    blockers = sorted(set(b for b in blockers
                          if isinstance(b, str) and len(b) <= 96)) if isinstance(blockers, list) else []
    delivery_off = delivery == "DISABLED"
    operational = evidence.get("operational")
    operational = operational if isinstance(operational, dict) and passed else {}
    cards = operational.get("technical_evaluations")
    cards = cards if isinstance(cards, list) else []
    book = operational.get("account_book_observed") is True
    statuses = {
        "SCAN": ("OBSERVED" if passed and count is not None else "BLOCKED",
                 "Snapshot pasar lolos pemeriksaan" if passed and count is not None
                 else "Bukti observasi terbaru tidak memadai"),
        "ANALYST": ("NOT_ATTESTED", "Aktivitas analisis belum dibuktikan oleh snapshot"),
        "STRATEGY": ("NOT_ATTESTED", "Evaluasi strategi tidak sama dengan kelayakan live"),
        "BALANCE": ("NOT_ATTESTED", "Risk Governor independen tidak diuji oleh status ini"),
        "EXEC": ("LIVE_OFF" if delivery_off else "NOT_ATTESTED",
                 "Pengiriman order dinonaktifkan" if delivery_off
                 else "Status gerbang pengiriman belum terverifikasi"),
        "AUDIT": ("SNAPSHOT_PASS" if passed else "BLOCKED",
                  "Struktur dan freshness snapshot lolos" if passed
                  else "Snapshot gagal pemeriksaan"),
    }
    if cards:
        statuses["ANALYST"] = ("TECHNICAL_EVALUATED", str(len(cards)) + " analisis teknis nyata; bukan panggilan model bahasa")
        statuses["STRATEGY"] = ("RESEARCH_EVALUATED", "Metode dan tindakan dari output mesin; belum bukti profit atau izin trading")
    if book:
        statuses["BALANCE"] = ("BOOK_OBSERVED", "Posisi/order broker dibaca; Risk Governor belum memberi izin eksekusi")
    return {
        "operational": operational,
        "schema_version": 1,
        "architecture": "SINGLE_UNIFIED_KATARINA_BRAIN",
        "visualization_only": True,
        "agent_workers_started": 0,
        "source": "READONLY_RUNTIME_SNAPSHOT",
        "observed_at_utc": evidence.get("assessed_at_utc")
            if isinstance(evidence.get("assessed_at_utc"), str) else None,
        "result": "SNAPSHOT_PASS" if passed else "BLOCKED",
        "blockers": blockers,
        "market_symbols": count if passed else None,
        "cycles": cycles,
        "successful_cycles": successful,
        "delivery": "DISABLED" if delivery_off else "UNVERIFIED",
        "live_execution_authorized": False,
        "broker_execution_verified": False,
        "profit_verified": False,
        "lanes": [{"id": name, "description": description,
                   "status": statuses[name][0], "reason": statuses[name][1]}
                  for name, description in LANES],
    }
