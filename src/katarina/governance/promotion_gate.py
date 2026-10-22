"""Promotion gate: active decision and risk files may only change with a promotion record.

`config/promotion_lock.json` pins the SHA-256 of every file that decides what Katarina
trades and how much it risks. A change to any of them must come with a promotion record
under `docs/governance/promotions/` that carries a passing validation report and an
explicit Owner approval (see docs/ROADMAP.md, "Gerbang promosi"). CI fails otherwise.

Read-only checks; nothing here sends orders, edits strategies or changes risk.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

LOCK_PATH = "config/promotion_lock.json"
RECORD_DIR = "docs/governance/promotions"
BASELINE_KIND = "BASELINE_PRE_GATE"
PROMOTION_KIND = "PROMOTION"


def file_sha256(path: Path) -> str:
    """Hash with LF line endings so Windows and Linux checkouts agree."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def current_hashes(root: Path, files) -> dict[str, str]:
    result = {}
    for rel in sorted(files):
        path = root / rel
        result[rel] = file_sha256(path) if path.is_file() else "MISSING"
    return result


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def record_problems(root: Path, record: dict, record_path: str) -> list[str]:
    """Why a promotion record cannot authorize the locked state (empty = valid)."""
    problems = []
    if not record_path.startswith(RECORD_DIR + "/"):
        problems.append(f"record_outside_{RECORD_DIR}")
    kind = record.get("kind")
    if kind not in (BASELINE_KIND, PROMOTION_KIND):
        problems.append("record_kind_invalid")
    approval = record.get("owner_approval") or {}
    if not str(approval.get("approved_by", "")).strip() or not str(approval.get("date", "")).strip():
        problems.append("owner_approval_missing")
    validation = record.get("validation") or {}
    if kind == PROMOTION_KIND:
        if validation.get("status") != "PASS":
            problems.append("validation_not_pass")
        report = str(validation.get("report", ""))
        if not report or not (root / report).is_file():
            problems.append("validation_report_missing")
        elif validation.get("report_sha256") != file_sha256(root / report):
            problems.append("validation_report_hash_mismatch")
    if kind == BASELINE_KIND and record.get("id") != "P-0000":
        problems.append("baseline_only_allowed_as_P-0000")
    if not isinstance(record.get("files"), dict) or not record["files"]:
        problems.append("record_files_missing")
    return problems


def check(root: Path) -> list[str]:
    """Return human-readable violations; empty list means the gate passes."""
    root = Path(root)
    lock = load_json(root / LOCK_PATH)
    files = lock.get("files") or {}
    if not files:
        return ["promotion_lock_has_no_files"]
    violations = []
    actual = current_hashes(root, files)
    changed = [rel for rel, digest in files.items() if actual.get(rel) != digest]
    for rel in changed:
        violations.append(
            f"{rel}: berubah tanpa catatan promosi (terkunci {files[rel][:12]}, sekarang {actual[rel][:12]})")
    record_path = str(lock.get("promotion_record", ""))
    if not record_path or not (root / record_path).is_file():
        violations.append(f"catatan promosi tidak ditemukan: {record_path or '-'}")
        return violations
    record = load_json(root / record_path)
    for problem in record_problems(root, record, record_path):
        violations.append(f"{record_path}: {problem}")
    if record.get("files") != files:
        violations.append(f"{record_path}: daftar hash tidak sama dengan {LOCK_PATH}")
    return violations


def write_lock(root: Path, record_path: str) -> dict:
    """Pin the current hashes of the record's files after validating the record."""
    root = Path(root)
    record = load_json(root / record_path)
    problems = record_problems(root, record, record_path)
    if problems:
        raise ValueError("promotion_record_invalid:" + ",".join(problems))
    hashes = current_hashes(root, record["files"])
    if hashes != record["files"]:
        raise ValueError("record_hashes_do_not_match_current_files")
    lock = {
        "schema_version": 1,
        "description": ("SHA-256 of files that decide Katarina's active trades and risk. "
                        "Change only through docs/ROADMAP.md 'Gerbang promosi'."),
        "promotion_record": record_path,
        "files": hashes,
    }
    with open(root / LOCK_PATH, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(lock, indent=2) + "\n")
    return lock
