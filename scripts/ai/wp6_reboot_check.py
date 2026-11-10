"""WP6 reboot evidence: record a baseline before a planned reboot, then check readiness after it.

Read-only towards the observer, MT5 and the Stage 0 ledger (SQLite ``mode=ro``). Never reboots, never starts
or stops a task or process, never touches autologon or credentials. Windows host only (wmic, PowerShell 4).

  # before the Owner-approved reboot (optionally with an online DB backup into a new folder)
  python scripts/ai/wp6_reboot_check.py baseline --output C:\\Katarina\\state\\wp6\\baseline.json
      [--backup-dir C:\\Katarina\\backups\\wp6-reboot-<UTC>]
  # after the reboot
  python scripts/ai/wp6_reboot_check.py check --baseline C:\\Katarina\\state\\wp6\\baseline.json
      --output C:\\Katarina\\state\\wp6\\post-reboot.json

``check`` exits 0 only for READY_AFTER_REBOOT. Without a reboot after the baseline it reports NOT_TESTED.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.operations import post_reboot  # noqa: E402

TASK = "Katarina-Readonly-Observer"
LAUNCHER = Path(r"C:\Katarina\run-observer.ps1")
DB = Path(r"C:\Katarina\state\readonly-observer\context.sqlite3")


def _run(args):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=60).stdout


def _wmic(args):
    raw = _run(["wmic", *args, "/format:list"])
    return raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("mbcs", "replace")


def live_facts():
    boot = post_reboot.parse_wmic_list(_wmic(["os", "get", "LastBootUpTime"]))[0]["LastBootUpTime"]
    rows = post_reboot.parse_wmic_list(_wmic(["process", "where", "name='python.exe' or name='terminal64.exe'",
                                              "get", "ProcessId,ParentProcessId,SessionId,Name,ExecutablePath,"
                                              "CommandLine"]))
    observers, mt5 = post_reboot.classify_processes(rows)
    task_xml = _run(["schtasks", "/query", "/tn", TASK, "/xml"])
    import hashlib
    return {"boot_utc": post_reboot.parse_wmi_datetime(boot), "observers": observers, "mt5": mt5,
            "task_xml_sha256": hashlib.sha256(task_xml).hexdigest(),
            "launcher_sha256": post_reboot.file_sha256(LAUNCHER)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("baseline")
    b.add_argument("--output", type=Path, required=True)
    b.add_argument("--backup-dir", type=Path)
    c = sub.add_parser("check")
    c.add_argument("--baseline", type=Path, required=True)
    c.add_argument("--output", type=Path, required=True)
    for p in (b, c):
        p.add_argument("--db", type=Path, default=DB)
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    facts = live_facts()
    ledger = post_reboot.read_ledger(args.db, facts["boot_utc"])
    if args.mode == "baseline":
        if args.output.exists():
            parser.error(f"{args.output} exists; a baseline is never overwritten")
        backup = post_reboot.backup_database(args.db, args.backup_dir) if args.backup_dir else None
        report = post_reboot.baseline(boot_utc=facts["boot_utc"], now_utc=now, task_xml_sha256=facts["task_xml_sha256"],
                                      launcher_sha256=facts["launcher_sha256"], observers=facts["observers"],
                                      mt5=facts["mt5"], ledger=ledger, backup=backup)
        verdict = "BASELINE_RECORDED"
    else:
        base = json.loads(args.baseline.read_text(encoding="utf-8"))
        report = post_reboot.assess(base=base, boot_utc=facts["boot_utc"], now_utc=now, observers=facts["observers"],
                                    mt5=facts["mt5"], ledger=ledger, task_xml_sha256=facts["task_xml_sha256"],
                                    launcher_sha256=facts["launcher_sha256"])
        verdict = report["verdict"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    for item in report.get("findings", []):
        print(f"{item['severity']} {item['reason']} {item['detail']}".rstrip())
    print("WP6_REBOOT", verdict)
    return 0 if verdict in ("BASELINE_RECORDED", "READY_AFTER_REBOOT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
