"""Audit Owner-approved Master Design against present offline implementation.

Never edits broker data, changes policy, starts MT5, makes orders, or claims
source-file existence proves real-world release readiness.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from katarina.governance.unified_verification import verify

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config" / "master_design_traceability_v1.json"
EXPECTED_AREA_IDS = {f"A{i:02d}" for i in range(1, 19)}
EXPECTED_DECISION_IDS = {f"D{i}" for i in range(1, 7)}
VALID_STATUSES = {"OFFLINE_VERIFIED", "PARTIAL", "NOT_INTEGRATED", "REMOVED"}
BASELINE = "docs/architecture/KATARINA_OWNER_DESIGN_BASELINE_20261014.md"


def _file_digest(root: Path, relative: str) -> str:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("invalid_master_design_evidence_path")
    target = Path(relative)
    if target.is_absolute() or ".." in target.parts:
        raise ValueError("invalid_master_design_evidence_path")
    resolved = (root / target).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("missing_or_outside_master_design_evidence:" + relative)
    return sha256(resolved.read_bytes()).hexdigest()


def audit_master_design(
    *,
    root: Path = ROOT,
    manifest: dict | None = None,
    run_acceptance: bool = True,
) -> dict:
    root = root.resolve()
    if manifest is None:
        manifest = json.loads((root / "config" / "master_design_traceability_v1.json").read_text())
    if (type(manifest) is not dict or
            manifest.get("schema_version") != 1 or
            manifest.get("operating_scope") != "RESEARCH_ONLY_NO_REAL_ORDERS" or
            manifest.get("canonical_profile") != "config/katarina_unified_v1.json" or
            manifest.get("release_gate") != "BLOCKED_PENDING_BROKER_EVIDENCE_AND_OWNER_AUTHORIZATION"):
        raise ValueError("master_design_registry_contract_mismatch")
    areas = manifest.get("approved_areas")
    decisions = manifest.get("deferred_decisions")
    if not isinstance(areas, list) or not isinstance(decisions, list):
        raise ValueError("master_design_registry_missing_areas_or_decisions")
    if (len(areas) != 18 or {a.get("id") for a in areas} != EXPECTED_AREA_IDS or
            len(decisions) != 6 or {d.get("id") for d in decisions} != EXPECTED_DECISION_IDS):
        raise ValueError("master_design_area_or_decision_missing")
    if any(d.get("status") != "AWAIT_OWNER_DECISION" for d in decisions):
        raise ValueError("deferred_owner_decision_invented")
    statuses = {}
    file_hashes = {}
    for area in areas:
        aid = area["id"]
        status = area.get("status")
        if status not in VALID_STATUSES:
            raise ValueError("master_design_invalid_implementation_status:" + aid)
        if ((aid == "A18") != (status == "REMOVED")):
            raise ValueError("master_design_management_removal_mismatch")
        if status == "OFFLINE_VERIFIED" and aid not in {"A01", "A02", "A07", "A09"}:
            raise ValueError("master_design_unsubstantiated_offline_certification:" + aid)
        if not isinstance(area.get("requirement"), str) or not area["requirement"].strip():
            raise ValueError("master_design_requirement_missing:" + aid)
        if not isinstance(area.get("remaining"), str) or not area["remaining"].strip():
            raise ValueError("master_design_remaining_gap_missing:" + aid)
        evidence = area.get("evidence_paths")
        tests = area.get("test_paths")
        if not isinstance(evidence, list) or not evidence or not isinstance(tests, list):
            raise ValueError("master_design_evidence_missing:" + aid)
        if status == "OFFLINE_VERIFIED" and not tests:
            raise ValueError("master_design_verified_without_tests:" + aid)
        for path in evidence + tests:
            file_hashes[path] = _file_digest(root, path)
        statuses[aid] = status
    _file_digest(root, BASELINE)
    _file_digest(root, manifest["canonical_profile"])
    if run_acceptance:
        profile = json.loads((root / manifest["canonical_profile"]).read_text())
        actual = verify(profile, root=root)
        if (actual["status"] != "INTEGRATED_OFFLINE_ENGINEERING_ONLY" or
                actual["modules_verified"] != 17 or
                actual["orders_submitted"] != 0 or
                actual["live_execution_authorized"] or
                actual["management"] != "REMOVED" or
                actual["cumulative_profit_lock"] != "VERIFIED_THREE_MILESTONES_AND_RESTART" or
                actual["same_day_emergency_lockdown"] != "VERIFIED_NO_NEW_ENTRY"):
            raise ValueError("master_design_canonical_acceptance_failed")
    counts = Counter(statuses.values())
    return {
        "result": "TRACEABILITY_ACCOUNTED_FOR_NOT_FULLY_IMPLEMENTED",
        "registered_approved_areas": len(areas),
        "deferred_owner_decisions": len(decisions),
        "counts": {status: counts[status] for status in
                   ("OFFLINE_VERIFIED", "PARTIAL", "NOT_INTEGRATED", "REMOVED")},
        "areas": statuses,
        "files_with_verified_sha256": len(file_hashes),
        "evidence_sha256": sha256(json.dumps(
            file_hashes, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest(),
        "readiness": "OFFLINE_ENGINEERING_ONLY",
        "live_trading_authorized": False,
        "master_design_fully_implemented": False,
        "deferred_decisions_resolved": False,
        "proof_scope": "SOURCE_EVIDENCE_PLUS_OFFLINE_ACCEPTANCE_NOT_PRODUCTION_CERTIFICATION",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(audit_master_design(root=args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
