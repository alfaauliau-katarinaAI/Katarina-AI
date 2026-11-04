"""Safe cleanup for a Katarina development worktree: report by default, delete only allowlisted caches.

Spec: docs/maintenance/AUTO_CLEANUP_CODING_GATE.md section C (Owner mandate, PR #278).

  python scripts/governance/safe_cleanup.py --check        # report (default; same as --dry-run)
  python scripts/governance/safe_cleanup.py --dry-run
  python scripts/governance/safe_cleanup.py --apply-safe   # delete allowlisted untracked artifacts only

Rules (fail closed):
- Only generated artifacts on an explicit allowlist may be deleted (``__pycache__``, ``*.pyc``,
  ``.pytest_cache`` and similar caches, regenerable ``build/`` report folders). ``build/code-gate`` is
  kept: it holds the gate failure ledger.
- Each target must be untracked by Git, resolve inside the worktree, and have no symlink/junction/
  reparse point anywhere on its path. Runtime/evidence locations are refused outright: ``state``,
  ``backups``, ``private``, ``logs``, ``broker-ticks``, ``.git``, ``.katarina-envs``,
  ``docs/governance`` and SQLite/WAL/SHM/DB files, even inside an allowlisted folder.
- ``--apply-safe`` refuses the production checkout (``C:\\Katarina\\code`` or a ``.katarina-production``
  marker), the ``main`` branch, and runs that started from a different HEAD/working tree than planned.
- Tracked source is never deleted. Duplicates and unreachable modules are reported as
  ``DELETE_CANDIDATE`` for a manual, reviewed PR (``DELETE_CONFIRMED`` needs evidence).
- Idempotent; every apply appends an audit line to ``build/code-gate/cleanup-audit.jsonl``.
No VPS, broker, network or scheduler is used.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis"}
ALLOWED_FILE_GLOBS = ("*.pyc", "*.pyo", "*~", "*.swp", "*.swo", ".DS_Store", "Thumbs.db")
# Regenerable report folders written by CI/governance tools (see katarina-body-ci.yml upload list).
ALLOWED_BUILD_DIRS = ("build/validation", "build/body", "build/stage10", "build/governance", "build/discovery")
KEEP_BUILD_DIRS = ("build/code-gate",)
DENY_SEGMENTS = {"state", "backups", "private", "logs", "broker-ticks", ".git", ".katarina-envs",
                 "readonly-observer", "node_modules"}
DENY_PREFIXES = ("docs/governance/",)
DENY_SUFFIXES = (".sqlite3", ".sqlite", ".db", "-wal", "-shm", ".wal", ".shm", ".csv.gz", ".jsonl")
PRODUCTION_ROOTS = {r"c:\katarina\code"}
# Identity/contract items from docs/maintenance/CLEANUP_PLAN.md: reported as PROTECTED_KEEP, never candidates.
PROTECTED_KEEP = {"scripts/ai/run_market_brain.py", "scripts/ai/run_decision_brain_v3.py",
                  "katarina.domain", "katarina.entrypoints", "katarina.ports"}
SKIP_WALK = {".git", ".katarina-envs", "node_modules"}


class Refused(Exception):
    pass


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          text=True, timeout=60).stdout


def tracked(root: Path) -> set[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], stdout=subprocess.PIPE, check=True,
                         timeout=60).stdout
    return {p for p in out.decode("utf-8", "surrogateescape").split("\0") if p}


def _is_link_like(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)  # Windows junction / reparse point
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def guard(root: Path, rel: str, tracked_set: set[str]) -> None:
    """Raise Refused unless rel is a deletable allowlisted artifact."""
    posix = PurePosixPath(rel)
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise Refused("PATH_ESCAPE")
    lower_parts = {p.lower() for p in posix.parts}
    if lower_parts & DENY_SEGMENTS:
        raise Refused("PROTECTED_LOCATION")
    lowered = rel.lower()
    if lowered.startswith(DENY_PREFIXES):
        raise Refused("PROTECTED_LOCATION")
    target = root / rel
    current = root
    for part in posix.parts:  # no link anywhere on the path, including the target itself
        current = current / part
        if _is_link_like(current):
            raise Refused("SYMLINK_OR_JUNCTION")
    resolved = target.resolve()
    if resolved != root and root not in resolved.parents:
        raise Refused("OUTSIDE_WORKTREE")
    if rel in tracked_set or any(t.startswith(rel.rstrip("/") + "/") for t in tracked_set):
        raise Refused("TRACKED_BY_GIT")
    if target.is_dir():
        for dirpath, dirnames, filenames in os.walk(target, followlinks=False):
            for name in dirnames + filenames:
                full = Path(dirpath) / name
                if _is_link_like(full):
                    raise Refused("SYMLINK_OR_JUNCTION")
                if name.lower().endswith(DENY_SUFFIXES) or name.lower() in DENY_SEGMENTS:
                    raise Refused("PROTECTED_CONTENT")
    elif lowered.endswith(DENY_SUFFIXES):
        raise Refused("PROTECTED_CONTENT")


def _artifact_candidates(root: Path) -> list[tuple[str, str]]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        if rel_dir in KEEP_BUILD_DIRS:
            dirnames[:] = []
            continue
        if rel_dir in ALLOWED_BUILD_DIRS:
            found.append((rel_dir, "BUILD_REPORT_DIR"))
            dirnames[:] = []
            continue
        keep = []
        for name in dirnames:
            rel = f"{rel_dir}/{name}" if rel_dir else name
            if name in SKIP_WALK:
                continue
            if name in ALLOWED_DIR_NAMES:
                found.append((rel, "CACHE_DIR"))
            else:
                keep.append(name)
        dirnames[:] = keep
        for name in filenames:
            if any(fnmatch.fnmatch(name, pattern) for pattern in ALLOWED_FILE_GLOBS):
                found.append((f"{rel_dir}/{name}" if rel_dir else name, "TEMP_FILE"))
    return sorted(found)


def _delete_candidates(root: Path, tracked_set: set[str]) -> list[dict]:
    """Tracked files that only a reviewed PR may remove: hash duplicates and unreachable modules."""
    by_hash = defaultdict(list)
    for rel in sorted(tracked_set):
        path = root / rel
        if not path.is_file() or path.stat().st_size < 64 or PurePosixPath(rel).name == "__init__.py":
            continue
        by_hash[hashlib.sha256(path.read_bytes()).hexdigest()].append(rel)
    out = [{"paths": paths, "label": "PROTECTED_KEEP" if set(paths) <= PROTECTED_KEEP else "DELETE_CANDIDATE",
            "reason": "IDENTICAL_CONTENT",
            "required_before_delete": "check dynamic imports, launchers, stage config, workflows, tests, manifest"}
           for paths in by_hash.values() if len(paths) > 1]
    try:
        sys.path.insert(0, str(root / "scripts" / "governance"))
        import runtime_import_map as rim
        categories = {name: row["category"] for name, row in rim.build(root)["modules"].items()}
    except Exception:  # reporting only; never blocks or widens deletion
        categories = None
    if categories:
        for module, category in sorted(categories.items()):
            if category == "D":
                out.append({"paths": [module], "reason": "UNREACHABLE_MODULE",
                            "label": "PROTECTED_KEEP" if module in PROTECTED_KEEP else "DELETE_CANDIDATE",
                            "required_before_delete": "architecture contract (entrypoints/ports) may protect it"})
    return out


def _production(root: Path) -> bool:
    return str(root).lower().rstrip("\\/") in PRODUCTION_ROOTS or (root / ".katarina-production").exists()


def _fingerprint(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip() + "|" + hashlib.sha256(
        _git(root, "status", "--porcelain=v1", "--untracked-files=no").encode()).hexdigest()


def _require_worktree_root(root: Path) -> None:
    top = _git(root, "rev-parse", "--show-toplevel").strip()
    if not top or Path(top).resolve() != root:
        raise Refused("NOT_A_GIT_WORKTREE_ROOT")


def plan(root: Path) -> dict:
    root = root.resolve()
    _require_worktree_root(root)
    tracked_set = tracked(root)
    artifacts, refused = [], []
    for rel, kind in _artifact_candidates(root):
        try:
            guard(root, rel, tracked_set)
            artifacts.append({"path": rel, "kind": kind, "action": "WOULD_DELETE",
                              "reason": "ALLOWLISTED_UNTRACKED_GENERATED_ARTIFACT"})
        except Refused as error:
            refused.append({"path": rel, "kind": kind, "action": "REFUSED", "reason": str(error)})
    candidates = _delete_candidates(root, tracked_set)
    return {"schema_version": 1, "root": str(root), "worktree_fingerprint": _fingerprint(root),
            "artifacts": artifacts, "refused": refused, "delete_candidates": candidates,
            "summary": {"would_delete": len(artifacts), "refused": len(refused),
                        "delete_candidates": sum(c["label"] == "DELETE_CANDIDATE" for c in candidates),
                        "protected_keep": sum(c["label"] == "PROTECTED_KEEP" for c in candidates),
                        "tracked_source_deleted": 0}}


def apply_safe(root: Path, *, allow_branch_main=False) -> dict:
    root = root.resolve()
    _require_worktree_root(root)
    if _production(root):
        raise Refused("PRODUCTION_CHECKOUT")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch == "main" and not allow_branch_main:
        raise Refused("MAIN_BRANCH")
    report = plan(root)
    tracked_set = tracked(root)
    deleted = []
    for item in report["artifacts"]:
        if _fingerprint(root) != report["worktree_fingerprint"]:
            raise Refused("WORKTREE_CHANGED_DURING_CLEANUP")
        rel = item["path"]
        try:
            guard(root, rel, tracked_set)  # re-check immediately before each deletion
            target = root / rel
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            item["action"] = "DELETED"
            deleted.append(rel)
        except Refused as error:
            item.update(action="REFUSED", reason=str(error))
        except OSError as error:  # in use (Windows) or vanished: skipped, never forced
            item.update(action="SKIPPED_IN_USE_OR_GONE", reason=type(error).__name__)
    report["summary"]["deleted"] = len(deleted)
    audit = root / "build" / "code-gate" / "cleanup-audit.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True)
    with audit.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "branch": branch,
                                 "head": report["worktree_fingerprint"].split("|")[0], "deleted": deleted}) + "\n")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply-safe", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = apply_safe(args.repo_root) if args.apply_safe else plan(args.repo_root)
        status = "APPLIED_SAFE" if args.apply_safe else "CHECK_ONLY"
    except Refused as error:
        print("SAFE_CLEANUP_REFUSED", error)
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    for item in report["refused"][:20]:
        print("REFUSED", item["reason"], item["path"])
    for item in report["delete_candidates"][:20]:
        print(item["label"], item["reason"], ", ".join(item["paths"]))
    print("SAFE_CLEANUP", status, json.dumps(s, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
