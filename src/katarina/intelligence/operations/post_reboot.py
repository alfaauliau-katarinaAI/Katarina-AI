"""WP6 reboot evidence: pre-reboot baseline, optional DB backup and the post-reboot readiness verdict.

Read-only towards the observer: the Stage 0 database is opened with ``mode=ro`` (``PRAGMA query_only``) and
is never written. The optional backup uses SQLite's online backup API into a *new* file outside the
checkout and checks the copy, not the live database.

``READY_AFTER_REBOOT`` is only issued from evidence collected **after a real reboot** that happened later
than a recorded baseline: one observer, one MT5 terminal in the same interactive session, a healthy first
cycle after boot, the reboot gap visible (no backfill), a readable database and zero orders. Configuration
checks before a reboot can at most say ``READY_FOR_REBOOT_TEST`` (see ``startup_task.analyze``).
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

OBSERVER_SCRIPT = "run_contextual_market_observer.py"
MT5_EXE = "terminal64.exe"
FIRST_CYCLE_DEADLINE = timedelta(minutes=20)    # boot -> autologon (+1 min task delay) -> MT5 -> first cycle
OUTAGE_MIN_SECONDS = 180                         # 3 x 60 s interval, same rule as data_health outages


def _utc(text):
    if text is None:
        return None
    value = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _finding(reason, severity, detail=""):
    return {"reason": reason, "severity": severity, "detail": detail}


def file_sha256(path: Path) -> str | None:
    path = Path(path)
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_ledger(db_path: Path, boot_utc: datetime) -> dict:
    """Read-only facts from the Stage 0 database around ``boot_utc``."""
    db_path = Path(db_path)
    if not db_path.exists():
        return {"exists": False}
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        db.execute("PRAGMA query_only = ON")
        quick = db.execute("PRAGMA quick_check").fetchone()[0]
        boot = boot_utc.isoformat()
        before = db.execute("SELECT max(observed_utc) FROM observer_cycles WHERE observed_utc < ?", (boot,)).fetchone()
        after = db.execute("SELECT cycle_id, observed_utc, status, reason, clock_shift_hours FROM observer_cycles "
                           "WHERE observed_utc >= ? ORDER BY observed_utc LIMIT 1", (boot,)).fetchone()
        first_ok = db.execute("SELECT observed_utc FROM observer_cycles WHERE observed_utc >= ? AND status = 'OK' "
                              "AND clock_shift_hours IS NOT NULL ORDER BY observed_utc LIMIT 1", (boot,)).fetchone()
        after_count = db.execute("SELECT count(*) FROM observer_cycles WHERE observed_utc >= ?", (boot,)).fetchone()[0]
        orders = db.execute("SELECT coalesce(sum(orders_submitted), 0) FROM observer_cycles").fetchone()[0]
        duplicates = db.execute("SELECT count(*) FROM (SELECT observed_utc FROM observer_cycles WHERE observed_utc >= ? "
                                "GROUP BY observed_utc HAVING count(*) > 1)", (boot,)).fetchone()[0]
    finally:
        db.close()
    return {"exists": True, "quick_check": quick, "last_cycle_before_boot_utc": before[0] if before else None,
            "first_cycle_after_boot": None if after is None else
            {"cycle_id": after[0], "observed_utc": after[1], "status": after[2], "reason": after[3],
             "clock_shift_hours": after[4]},
            "first_ok_cycle_after_boot_utc": first_ok[0] if first_ok else None,
            "cycles_after_boot": after_count, "duplicate_cycle_timestamps_after_boot": duplicates,
            "orders_submitted_total": int(orders)}


def backup_database(db_path: Path, backup_dir: Path) -> dict:
    """Online SQLite backup into a new file, then ``integrity_check`` on the copy (never on the live DB)."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / (Path(db_path).stem + ".backup.sqlite3")
    if target.exists():
        raise FileExistsError(f"WP6_BACKUP_EXISTS {target}")
    source = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    copy = sqlite3.connect(target)
    try:
        source.backup(copy, pages=1024, sleep=0.05)    # small steps keep observer I/O responsive
    finally:
        source.close()
    try:
        integrity = copy.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        copy.close()
    return {"backup": str(target), "integrity_check": integrity, "sha256": file_sha256(target),
            "bytes": target.stat().st_size}


def baseline(*, boot_utc: datetime, now_utc: datetime, task_xml_sha256: str | None, launcher_sha256: str | None,
             observers: list, mt5: list, ledger: dict, backup: dict | None = None) -> dict:
    return {"kind": "WP6_PRE_REBOOT_BASELINE", "recorded_utc": now_utc.isoformat(), "boot_utc": boot_utc.isoformat(),
            "task_xml_sha256": task_xml_sha256, "launcher_sha256": launcher_sha256,
            "observer_processes": len(observers), "mt5_processes": len(mt5),
            "orders_submitted_total": ledger.get("orders_submitted_total"), "quick_check": ledger.get("quick_check"),
            "backup": backup, "live_execution_authorized": False}


def assess(*, base: dict | None, boot_utc: datetime, now_utc: datetime, observers: list, mt5: list, ledger: dict,
           task_xml_sha256: str | None = None, launcher_sha256: str | None = None) -> dict:
    """Post-reboot verdict. ``observers``/``mt5`` are dicts with ``pid`` and ``session_id``."""
    findings = []
    if base is None:
        findings.append(_finding("WP6_NO_BASELINE", "P0", "record a pre-reboot baseline first"))
        rebooted = False
    else:
        rebooted = boot_utc > _utc(base["boot_utc"]) + timedelta(seconds=30)
        if not rebooted:
            findings.append(_finding("WP6_NO_REBOOT_SINCE_BASELINE", "P0", base["boot_utc"]))
        if task_xml_sha256 and base.get("task_xml_sha256") and task_xml_sha256 != base["task_xml_sha256"]:
            findings.append(_finding("WP6_TASK_DEFINITION_CHANGED", "P1", "task XML differs from the baseline"))
        if launcher_sha256 and base.get("launcher_sha256") and launcher_sha256 != base["launcher_sha256"]:
            findings.append(_finding("WP6_LAUNCHER_CHANGED", "P1", "launcher differs from the baseline"))
    if len(observers) != 1:
        findings.append(_finding("WP6_OBSERVER_COUNT", "P0", f"{len(observers)} observer processes"))
    if len(mt5) != 1:
        findings.append(_finding("WP6_MT5_COUNT", "P0", f"{len(mt5)} MT5 terminals"))
    sessions = {p.get("session_id") for p in observers + mt5}
    if observers and mt5 and (len(sessions) != 1 or 0 in sessions):
        findings.append(_finding("WP6_NOT_SAME_INTERACTIVE_SESSION", "P0", f"sessions={sorted(map(str, sessions))}"))
    if not ledger.get("exists"):
        findings.append(_finding("WP6_LEDGER_MISSING", "P0"))
    else:
        if ledger.get("quick_check") != "ok":
            findings.append(_finding("WP6_DB_QUICK_CHECK_FAILED", "P0", str(ledger.get("quick_check"))))
        if ledger.get("orders_submitted_total") != 0:
            findings.append(_finding("WP6_ORDERS_RECORDED", "P0", str(ledger.get("orders_submitted_total"))))
        first_ok = _utc(ledger.get("first_ok_cycle_after_boot_utc"))
        if first_ok is None:
            findings.append(_finding("WP6_NO_OK_CYCLE_AFTER_BOOT", "P0"))
        elif first_ok - boot_utc > FIRST_CYCLE_DEADLINE:
            findings.append(_finding("WP6_FIRST_CYCLE_LATE", "P1", f"{(first_ok - boot_utc).total_seconds():.0f}s"))
        before = _utc(ledger.get("last_cycle_before_boot_utc"))
        first = ledger.get("first_cycle_after_boot")
        if before is not None and first is not None:
            gap = (_utc(first["observed_utc"]) - before).total_seconds()
            if gap < OUTAGE_MIN_SECONDS:
                findings.append(_finding("WP6_REBOOT_GAP_NOT_VISIBLE", "P0", f"gap {gap:.0f}s: backfill suspected"))
        if ledger.get("duplicate_cycle_timestamps_after_boot"):
            findings.append(_finding("WP6_DUPLICATE_CYCLES", "P0", str(ledger["duplicate_cycle_timestamps_after_boot"])))
    blocking = [f for f in findings if f["severity"] in ("P0", "P1")]
    if base is None or not rebooted:
        verdict = "NOT_TESTED"
    else:
        verdict = "NOT_READY" if blocking else "READY_AFTER_REBOOT"
    return {"kind": "WP6_POST_REBOOT_CHECK", "verdict": verdict, "checked_utc": now_utc.isoformat(),
            "boot_utc": boot_utc.isoformat(), "findings": findings, "ledger": ledger,
            "observer_processes": observers, "mt5_processes": mt5, "orders_submitted": 0,
            "live_execution_authorized": False}


def parse_wmic_list(text: str) -> list[dict]:
    """Parse ``wmic ... /format:list`` output (blank-line separated ``Key=Value`` blocks)."""
    items, current = [], {}
    for line in text.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            if current:
                items.append(current)
                current = {}
            continue
        key, _, value = line.partition("=")
        current[key] = value
    if current:
        items.append(current)
    return items


def classify_processes(rows: list[dict]) -> tuple[list, list]:
    """Logical observer instances and MT5 terminals.

    A Python 3.12 venv on Windows starts ``Scripts\\python.exe`` as a redirector that runs the base
    interpreter as its child with the same arguments, so one observer shows up as two processes. Only the
    root of each observer process chain counts as an instance.
    """
    observers, mt5 = [], []
    for row in rows:
        cmd = (row.get("CommandLine") or "").lower()
        exe = (row.get("ExecutablePath") or "").lower()
        item = {"pid": int(row.get("ProcessId") or 0), "parent_pid": int(row.get("ParentProcessId") or 0),
                "session_id": int(row.get("SessionId") or -1)}
        if OBSERVER_SCRIPT in cmd and "python" in (exe + cmd):
            observers.append(item)
        elif exe.endswith(MT5_EXE) or (row.get("Name") or "").lower() == MT5_EXE:
            mt5.append(item)
    pids = {o["pid"] for o in observers}
    roots = [o for o in observers if o["parent_pid"] not in pids]
    for root in roots:
        root["child_pids"] = sorted(o["pid"] for o in observers if o["parent_pid"] == root["pid"])
    return roots, mt5


def parse_wmi_datetime(value: str) -> datetime:
    """``20261004093015.500000+420`` (local time + offset in minutes) -> aware UTC datetime."""
    value = value.strip()
    base = datetime.strptime(value[:14], "%Y%m%d%H%M%S")
    sign = -1 if value[21] == "-" else 1
    offset = timedelta(minutes=sign * int(value[22:25]))
    return (base - offset).replace(tzinfo=timezone.utc)
