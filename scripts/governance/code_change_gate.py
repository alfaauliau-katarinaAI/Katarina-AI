"""Katarina coding gate KAT-CG-00..05: fail-fast checks that stop a bad change before merge/deploy.

Spec: docs/maintenance/AUTO_CLEANUP_CODING_GATE.md (Owner mandate, PR #278). Repo-native only: run
locally before a commit and by .github/workflows/katarina-body-ci.yml on push/PR. No scheduler, no
VPS, no broker, no auto-repair, no auto-commit. Existing tools are reused, never reimplemented:
audit_repo_hygiene, audit_dependency_links, promotion_gate, audit_constitution_guard, release_manifest.

  python scripts/governance/code_change_gate.py --quick           # KAT-CG-00 + 01 + safe_cleanup --check
  python scripts/governance/code_change_gate.py --gate KAT-CG-03  # one gate
  python scripts/governance/code_change_gate.py --full            # 00..03 locally (03 after 02)
  python scripts/governance/code_change_gate.py --gate KAT-CG-04 --sha <40-hex>   # CI on GitHub
  python scripts/governance/code_change_gate.py --record-root-cause <FP> --cause "..." --test tests/x.py

Every failure gets a stable fingerprint (gate + reason + file:line + test), an error id, a severity
and a status in a local ledger (default build/code-gate/failure-ledger.json, untracked). The same
fingerprint failing again on a different HEAD (i.e. after one fix attempt) is
REPEATED_FAILURE_NEEDS_ROOT_CAUSE: the gate stops (exit 3) until a root cause with a reproduction
test is recorded. The gate never edits tests, expectations, manifests or locks to turn GREEN.

Exit codes: 0 PASS, 1 FAIL, 2 BLOCKED (missing evidence), 3 REPEATED_FAILURE_NEEDS_ROOT_CAUSE.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
GATES = ("KAT-CG-00", "KAT-CG-01", "KAT-CG-02", "KAT-CG-03", "KAT-CG-04", "KAT-CG-05")
FAIL_STATUS = {
    "KAT-CG-00": "BLOCKED_BASELINE",
    "KAT-CG-01": "FAIL_SYNTAX_OR_DEPENDENCY",
    "KAT-CG-02": "FAIL_TEST",
    "KAT-CG-03": "FAIL_SAFETY_OR_MANIFEST",
    "KAT-CG-04": "BLOCKED_CI_OR_REVIEW",
    "KAT-CG-05": "BLOCKED_DEPLOY",
}
REPEATED = "REPEATED_FAILURE_NEEDS_ROOT_CAUSE"
# Contracts whose change must be visible in KAT-CG-00 (promotion_gate decides in KAT-CG-03).
PROTECTED_PREFIXES = ("config/promotion_lock.json", "config/repository_architecture.json", "protocol/",
                      "docs/governance/", "KATARINA_CONSTITUTION.md", "ops/deployment/release-manifest.json")
REQUIRED_CI_CHECKS = ("body", "Portable brain (ubuntu-latest)", "Portable brain (windows-latest)")
CONFLICT_RE = re.compile(r"^(<<<<<<< |>>>>>>> )", re.M)
SUITES = ("unit", "static", "integration")


@dataclass
class Finding:
    gate: str
    reason: str
    file: str = ""
    line: int = 0
    test: str = ""
    detail: str = ""
    severity: str = "P1"

    @property
    def fingerprint(self) -> str:
        key = "|".join((self.gate, self.reason, self.file, str(self.line), self.test))
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def as_dict(self) -> dict:
        data = asdict(self)
        data.update(fingerprint=self.fingerprint, error_id="KAT-ERR-" + self.fingerprint[:8],
                    location=f"{self.file}:{self.line}" if self.file else "")
        return data


@dataclass
class GateResult:
    gate: str
    status: str = "PASS"
    findings: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)


# ---------------------------------------------------------------- helpers

def _git(root: Path, *args: str, check=True) -> str:
    return subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, check=check, timeout=60).stdout


def _tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], stdout=subprocess.PIPE, check=True,
                         timeout=60).stdout
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def _run(root: Path, argv: list[str], *, env_extra=None, timeout=1800) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(root / "src"), str(root), env.get("PYTHONPATH")]))
    env.update(env_extra or {})
    return subprocess.run([sys.executable, *argv], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, env=env, timeout=timeout)


def _severity_for(path: str) -> str:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from reason_code_index import severity  # same area→P0/P1/P2 rule as REASON_CODE_INDEX.md
        return severity(path)
    except Exception:  # never let reporting break the gate
        return "P1"


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD", check=False).strip() or "UNKNOWN"


# ---------------------------------------------------------------- KAT-CG-00 baseline

def gate_00(root: Path, base: str | None) -> GateResult:
    r = GateResult("KAT-CG-00")
    if not (root / ".git").exists() and not _git(root, "rev-parse", "--git-dir", check=False).strip():
        r.findings.append(Finding(r.gate, "NOT_A_GIT_WORKTREE", severity="P0"))
        return r
    head = _head(root)
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip()
    r.evidence.update(head=head, branch=branch)
    for line in _git(root, "status", "--porcelain=v1", check=False).splitlines():
        code, path = line[:2], line[3:]
        if code in ("UU", "AA", "DD", "AU", "UA", "DU", "UD"):
            r.findings.append(Finding(r.gate, "UNMERGED_PATH", path, severity="P0"))
    changed = []
    if base:
        merge_base = _git(root, "merge-base", base, "HEAD", check=False).strip()
        if merge_base:
            changed = [p for p in _git(root, "diff", "--name-only", merge_base, "HEAD").splitlines() if p]
            r.evidence["base"] = base
        else:
            r.evidence["base"] = f"{base} (unavailable; only working tree checked)"
    changed += [l[3:] for l in _git(root, "status", "--porcelain=v1", check=False).splitlines() if l[3:]]
    changed = sorted(set(changed))
    r.evidence["changed_files"] = len(changed)
    r.evidence["protected_changed"] = [p for p in changed if p.startswith(PROTECTED_PREFIXES)]
    for path in changed:
        file = root / path
        if not file.is_file() or file.stat().st_size > 5_000_000:
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        match = CONFLICT_RE.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            r.findings.append(Finding(r.gate, "MERGE_CONFLICT_MARKER", path, line, severity="P0"))
    return r


# ---------------------------------------------------------------- KAT-CG-01 syntax / JSON / deps / hygiene

def gate_01(root: Path) -> GateResult:
    r = GateResult("KAT-CG-01")
    tracked = _tracked(root)
    py = json_files = 0
    for rel in tracked:
        path = root / rel
        if not path.is_file():
            continue
        if rel.endswith(".py"):
            py += 1
            try:
                ast.parse(path.read_bytes(), filename=rel)
            except SyntaxError as error:
                r.findings.append(Finding(r.gate, "PYTHON_SYNTAX_ERROR", rel, error.lineno or 0,
                                          detail=(error.msg or "")[:120], severity=_severity_for(rel)))
        elif rel.endswith(".json"):
            json_files += 1
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError as error:
                r.findings.append(Finding(r.gate, "JSON_INVALID", rel, error.lineno, detail=error.msg[:120],
                                          severity=_severity_for(rel)))
            except UnicodeDecodeError:
                r.findings.append(Finding(r.gate, "JSON_NOT_UTF8", rel, severity=_severity_for(rel)))
    r.evidence.update(python_files=py, json_files=json_files)
    out = root / "build" / "code-gate"
    deps = _run(root, ["scripts/governance/audit_dependency_links.py", "--repo-root", ".",
                       "--output", str(out / "dependency-links.json")], timeout=300)
    r.evidence["dependency_links"] = deps.stdout.splitlines()[0][:80] if deps.stdout else ""
    if deps.returncode:
        report = _load(out / "dependency-links.json")
        for category, items in (report.get("failures") or {}).items():
            for item in items:
                text = item if isinstance(item, str) else json.dumps(item, sort_keys=True)
                file, line = _split_location(text)
                r.findings.append(Finding(r.gate, "DEPENDENCY_" + category.upper(), file, line,
                                          detail=text[:160], severity=_severity_for(file)))
        if not report.get("failures"):
            r.findings.append(Finding(r.gate, "DEPENDENCY_AUDIT_ERROR", detail=_tail(deps.stdout)))
    hygiene = _run(root, ["scripts/governance/audit_repo_hygiene.py", "--repo-root", ".",
                          "--output", str(out / "repository-hygiene.json")], timeout=300)
    if hygiene.returncode:
        report = _load(out / "repository-hygiene.json")
        keys = {"accidental_tracked_files": "TRACKED_JUNK_OR_SECRET_NAME", "empty_executable_sources": "EMPTY_SOURCE",
                "forbidden_artifacts": "FORBIDDEN_ARTIFACT", "expired_or_invalid_requests": "INVALID_REQUEST"}
        for key, reason in keys.items():
            for item in report.get(key) or []:
                path = item["path"] if isinstance(item, dict) else item
                # Only the path is reported: a secret file's contents are never read or printed.
                r.findings.append(Finding(r.gate, reason, path, severity="P0" if "SECRET" in reason else "P1"))
        if not any(report.get(k) for k in keys):
            r.findings.append(Finding(r.gate, "HYGIENE_AUDIT_ERROR", detail=_tail(hygiene.stdout)))
    return r


def _split_location(text: str) -> tuple[str, int]:
    match = re.match(r"^\s*([\w./\\-]+\.\w+):(\d+)", text)
    if match:
        return match.group(1), int(match.group(2))
    match = re.match(r"^\s*([\w./\\-]+\.\w+)", text)
    return (match.group(1), 0) if match else ("", 0)


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _tail(text: str, n=400) -> str:
    return (text or "")[-n:]


# ---------------------------------------------------------------- KAT-CG-02 tests

_FAIL_RE = re.compile(r"^(FAIL|ERROR): (\w+) \(([\w.]+)\)", re.M)


def gate_02(root: Path, suites=SUITES) -> GateResult:
    r = GateResult("KAT-CG-02")
    for suite in suites:
        proc = _run(root, ["-m", "unittest", "discover", "-s", f"tests/{suite}", "-p", "test_*.py"], timeout=2400)
        summary = re.findall(r"^Ran (\d+) tests?.*$", proc.stdout, re.M)
        r.evidence[suite] = {"ran": int(summary[-1]) if summary else 0, "returncode": proc.returncode,
                             "skipped": sum(int(x) for x in re.findall(r"skipped=(\d+)", proc.stdout))}
        failed = _FAIL_RE.findall(proc.stdout)
        for kind, name, owner in failed:
            test_file = "tests/" + suite + "/" + owner.split(".")[-2].replace(".", "/") + ".py" \
                if owner.count(".") >= 1 else ""
            r.findings.append(Finding(r.gate, "TEST_" + kind, test_file, 0, f"{owner}.{name}",
                                      severity=_severity_for(test_file)))
        if proc.returncode and not failed:
            r.findings.append(Finding(r.gate, "TEST_RUNNER_ERROR", f"tests/{suite}", detail=_tail(proc.stdout)))
    return r


# ---------------------------------------------------------------- KAT-CG-03 safety / manifest

def gate_03(root: Path) -> GateResult:
    r = GateResult("KAT-CG-03")
    promo = _run(root, ["scripts/governance/promotion_gate.py", "--check"], timeout=300)
    r.evidence["promotion_gate"] = "PASS" if promo.returncode == 0 else "FAIL"
    for line in promo.stdout.splitlines():
        if line.startswith("PROMOTION_GATE_FAIL"):
            text = line.split(" ", 1)[1] if " " in line else line
            file, _ = _split_location(text)
            r.findings.append(Finding(r.gate, "PROMOTION_LOCK_VIOLATION", file, detail=text[:160], severity="P0"))
    if promo.returncode and not any(f.reason == "PROMOTION_LOCK_VIOLATION" for f in r.findings):
        r.findings.append(Finding(r.gate, "PROMOTION_GATE_ERROR", detail=_tail(promo.stdout), severity="P0"))
    out = root / "build" / "code-gate"
    guard = _run(root, ["scripts/governance/audit_constitution_guard.py", "--repo-root", ".",
                        "--output", str(out / "constitution_guard.json")], timeout=300)
    r.evidence["constitution_guard"] = "PASS" if guard.returncode == 0 else "FAIL"
    if guard.returncode:
        r.findings.append(Finding(r.gate, "CONSTITUTION_GUARD_FAIL", "KATARINA_CONSTITUTION.md",
                                  detail=_tail(guard.stdout, 200), severity="P0"))
    manifest = _run(root, ["scripts/deployment/release_manifest.py", "--manifest",
                           "ops/deployment/release-manifest.json"], timeout=300)
    try:
        report = json.loads(manifest.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        report = {"status": "UNREADABLE"}
    r.evidence["release_manifest"] = f"{report.get('status')} {report.get('checked', '')}".strip()
    if report.get("status") != "MATCH":
        for kind in ("missing", "changed", "extra"):
            for path in report.get(kind) or []:
                r.findings.append(Finding(r.gate, "MANIFEST_" + kind.upper(), path, severity="P1"))
        if not any(report.get(k) for k in ("missing", "changed", "extra")):
            r.findings.append(Finding(r.gate, "MANIFEST_UNREADABLE", "ops/deployment/release-manifest.json",
                                      detail=_tail(manifest.stdout, 200), severity="P1"))
    return r


# ---------------------------------------------------------------- KAT-CG-04 CI / review (GitHub)

def gate_04(root: Path, sha: str | None, repo: str | None) -> GateResult:
    r = GateResult("KAT-CG-04")
    sha = sha or _head(root)
    repo = repo or os.environ.get("GITHUB_REPOSITORY") or "alfaauliau-katarinaAI/Katarina-AI"
    r.evidence.update(sha=sha, repo=repo)
    runs = _github_json(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")
    if runs is None:
        r.findings.append(Finding(r.gate, "CI_STATUS_UNAVAILABLE", detail="GitHub API unreachable or no token"))
        return r
    latest = {}
    for run in runs.get("check_runs", []):
        name = run.get("name")
        if name not in latest or run.get("started_at", "") > latest[name].get("started_at", ""):
            latest[name] = run
    for name in REQUIRED_CI_CHECKS:
        run = latest.get(name)
        state = (run or {}).get("conclusion") or (run or {}).get("status") or "MISSING"
        r.evidence[name] = state
        if state != "success":
            r.findings.append(Finding(r.gate, "CI_CHECK_NOT_SUCCESS", test=name, detail=state, severity="P0"))
    return r


def _github_json(path: str):
    """Read actual GitHub check runs; public repositories need no local GitHub credentials.

    A failed HTTP request, malformed response, or missing check is never turned
    into success. For private repositories, the existing authenticated GH CLI
    fallback remains available. Never accept a caller-supplied URL/hostname.
    """
    if not re.fullmatch(
            r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/commits/[0-9a-fA-F]{40}/check-runs\\?per_page=100",
            path):
        return None
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    try:
        import urllib.request
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "Katarina-Code-Gate/1.0"}
        if token:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request("https://api.github.com/" + path, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        if isinstance(data, dict) and isinstance(data.get("check_runs"), list):
            return data
    except (OSError, ValueError, TypeError):  # fail closed; never use cached or synthetic CI results
        pass
    if token:  # a rejected explicit credential must not silently become anonymous success
        return None
    try:
        out = subprocess.run(["gh", "api", path], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, timeout=60)
        if out.returncode != 0:
            return None
        data = json.loads(out.stdout)
        return data if isinstance(data, dict) and isinstance(data.get("check_runs"), list) else None
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return None


# ---------------------------------------------------------------- KAT-CG-05 deploy preflight (no VPS access)

def gate_05(root: Path, sha: str | None, repo: str | None, receipt: Path | None) -> GateResult:
    """Checks a deploy receipt written by the operator; never connects to the VPS itself."""
    r = GateResult("KAT-CG-05")
    if receipt is None or not receipt.is_file():
        r.findings.append(Finding(r.gate, "DEPLOY_RECEIPT_MISSING",
                                  detail="--deploy-receipt JSON with target_sha/backup/rollback/owner_approval"))
        return r
    data = _load(receipt)
    target = data.get("target_sha", "")
    sha = sha or _head(root)
    checks = {
        "TARGET_SHA_MISMATCH": bool(re.fullmatch(r"[0-9a-f]{40}", target)) and target == sha,
        "BACKUP_NOT_VERIFIED": bool(data.get("backup_path")) and data.get("backup_integrity") == "ok",
        "ROLLBACK_PLAN_MISSING": bool(data.get("rollback_sha")) and bool(data.get("rollback_steps")),
        "OWNER_APPROVAL_MISSING": bool(data.get("owner_approval_ref")),
        "SMOKE_NOT_READONLY": data.get("smoke_orders_submitted") == 0 and data.get("live_execution") is False,
    }
    for reason, ok in checks.items():
        if not ok:
            r.findings.append(Finding(r.gate, reason, str(receipt.name), severity="P0"))
    for upstream in (gate_03(root), gate_04(root, sha, repo)):
        for finding in upstream.findings:
            r.findings.append(Finding(r.gate, "UPSTREAM_" + upstream.gate.replace("-", "_") + "_" + finding.reason,
                                      finding.file, finding.line, finding.test, severity="P0"))
    r.evidence.update(target_sha=target, receipt=str(receipt))
    return r


# ---------------------------------------------------------------- anti-repeat ledger

class FailureLedger:
    """fingerprint → attempts per HEAD. Same fingerprint on a new HEAD = a failed fix attempt."""

    def __init__(self, path: Path):
        self.path = path
        self.data = _load(path) or {"schema_version": 1, "entries": {}}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def blocked(self) -> list[dict]:
        return [dict(fingerprint=k, **v) for k, v in self.data["entries"].items() if v["status"] == REPEATED]

    def observe(self, results: list[GateResult], head: str, ran_gates: set[str]) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        seen = set()
        for result in results:
            for finding in result.findings:
                fp = finding.fingerprint
                seen.add(fp)
                entry = self.data["entries"].setdefault(fp, {
                    "error_id": "KAT-ERR-" + fp[:8], "gate": finding.gate, "reason": finding.reason,
                    "severity": finding.severity, "location": f"{finding.file}:{finding.line}",
                    "test": finding.test, "first_seen_utc": now, "heads": [], "status": "DETECTED",
                    "root_cause": None, "reproduction_test": None, "fix_commit": None})
                if head not in entry["heads"]:
                    entry["heads"].append(head)
                entry["last_seen_utc"] = now
                came_back = entry["status"] == "VERIFIED"  # fixed once, failing again
                if came_back or len(entry["heads"]) >= 2:
                    # One fix attempt (a new HEAD) did not remove it: stop and demand a new analysis.
                    if entry.get("root_cause"):
                        entry.setdefault("previous_root_causes", []).append(entry["root_cause"])
                    entry.update(status=REPEATED, root_cause=None, reproduction_test=None)
                elif entry.get("root_cause"):
                    entry["status"] = "ROOT_CAUSE_IDENTIFIED"
        for fp, entry in self.data["entries"].items():
            if fp not in seen and entry["gate"] in ran_gates and entry["status"] not in ("VERIFIED",):
                entry.update(status="VERIFIED", fix_commit=head, verified_utc=now)
        return [dict(fingerprint=k, **v) for k, v in self.data["entries"].items() if k in seen]

    def record_root_cause(self, fingerprint: str, cause: str, test: str) -> dict:
        entry = self.data["entries"].get(fingerprint)
        if entry is None:
            raise SystemExit(f"UNKNOWN_FINGERPRINT {fingerprint}")
        if not cause.strip() or not test.strip():
            raise SystemExit("ROOT_CAUSE_AND_REPRODUCTION_TEST_REQUIRED")
        entry.update(root_cause=cause.strip(), reproduction_test=test.strip(), status="ROOT_CAUSE_IDENTIFIED",
                     heads=entry["heads"][-1:])  # next fix attempt is measured from here
        return entry


# ---------------------------------------------------------------- orchestration

def run(root: Path, gates: list[str], *, base=None, sha=None, repo=None, receipt=None, suites=SUITES,
        ledger_path: Path | None = None, cleanup_check=False) -> dict:
    root = root.resolve()
    head = _head(root)
    ledger = FailureLedger(ledger_path or root / "build" / "code-gate" / "failure-ledger.json")
    stop = ledger.blocked()
    if stop:
        report = {"result": REPEATED, "head": head, "gates": [], "repeated": stop,
                  "message": "STOP: same fingerprint failed after a fix attempt; record root cause with "
                             "--record-root-cause FP --cause ... --test ... before running the gate again"}
        return report
    runners = {"KAT-CG-00": lambda: gate_00(root, base), "KAT-CG-01": lambda: gate_01(root),
               "KAT-CG-02": lambda: gate_02(root, suites), "KAT-CG-03": lambda: gate_03(root),
               "KAT-CG-04": lambda: gate_04(root, sha, repo), "KAT-CG-05": lambda: gate_05(root, sha, repo, receipt)}
    results, ran = [], set()
    for gate in gates:
        result = runners[gate]()
        ran.add(gate)
        if result.findings:
            result.status = FAIL_STATUS[gate]
        results.append(result)
        if result.findings:  # fail-fast: an expensive later gate never runs on a broken change
            break
    cleanup = None
    if cleanup_check:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import safe_cleanup
        cleanup = safe_cleanup.plan(root)["summary"]
    entries = ledger.observe(results, head, ran)
    ledger.save()
    repeated = [e for e in entries if e["status"] == REPEATED]
    failed = [r for r in results if r.findings]
    if repeated:
        verdict = REPEATED
    elif not failed:
        verdict = "PASS"
    else:
        verdict = failed[0].status
    return {"result": verdict, "head": head, "generated_utc": datetime.now(timezone.utc).isoformat(),
            "gates": [{"gate": r.gate, "status": r.status, "evidence": r.evidence,
                       "findings": [f.as_dict() for f in r.findings]} for r in results],
            "not_run": [g for g in gates if g not in ran], "ledger": entries, "cleanup_check": cleanup,
            "live_execution_authorized": False, "orders_submitted": 0}


def exit_code(result: str) -> int:
    if result == "PASS":
        return 0
    if result == REPEATED:
        return 3
    if result.startswith("BLOCKED"):
        return 2
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--quick", action="store_true", help="KAT-CG-00 + 01 + safe_cleanup --check")
    mode.add_argument("--full", action="store_true", help="KAT-CG-00..03")
    mode.add_argument("--gate", action="append", choices=GATES)
    mode.add_argument("--record-root-cause", metavar="FINGERPRINT")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--base", help="base ref for the changed-file baseline (default origin/main if present)")
    parser.add_argument("--sha", help="commit for KAT-CG-04/05 (default HEAD)")
    parser.add_argument("--repo", help="owner/name for KAT-CG-04 (default $GITHUB_REPOSITORY)")
    parser.add_argument("--deploy-receipt", type=Path)
    parser.add_argument("--suites", default=",".join(SUITES))
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cause")
    parser.add_argument("--test")
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    ledger_path = args.ledger or root / "build" / "code-gate" / "failure-ledger.json"
    if args.record_root_cause:
        ledger = FailureLedger(ledger_path)
        entry = ledger.record_root_cause(args.record_root_cause, args.cause or "", args.test or "")
        ledger.save()
        print(json.dumps({"fingerprint": args.record_root_cause, **entry}, indent=2))
        return 0
    base = args.base
    if base is None and _git(root, "rev-parse", "--verify", "-q", "origin/main", check=False).strip():
        base = "origin/main"
    gates = (["KAT-CG-00", "KAT-CG-01"] if args.quick else
             ["KAT-CG-00", "KAT-CG-01", "KAT-CG-02", "KAT-CG-03"] if args.full else args.gate)
    suites = tuple(s for s in args.suites.split(",") if s in SUITES)
    report = run(root, gates, base=base, sha=args.sha, repo=args.repo, receipt=args.deploy_receipt,
                 suites=suites, ledger_path=ledger_path, cleanup_check=args.quick)
    out = args.output or root / "build" / "code-gate" / "code-change-gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for gate in report["gates"]:
        print(f"{gate['gate']} {gate['status']}")
        for f in gate["findings"][:25]:
            print(f"  {f['error_id']} {f['severity']} {f['reason']} {f['location']} {f['test']} {f['detail'][:100]}".rstrip())
    if report["result"] == REPEATED:
        for entry in report.get("repeated") or [e for e in report["ledger"] if e["status"] == REPEATED]:
            print(f"  STOP {entry['error_id']} fingerprint={entry['fingerprint']} {entry['reason']} {entry['location']}")
    print("KAT_CODE_CHANGE_GATE", report["result"])
    return exit_code(report["result"])


if __name__ == "__main__":
    sys.exit(main())
