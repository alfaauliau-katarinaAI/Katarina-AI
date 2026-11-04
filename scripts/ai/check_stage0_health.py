"""Stage 0 data-health report (docs/ROADMAP.md, Tahap 0). Read-only; never connects to MT5.

  python scripts/ai/check_stage0_health.py --state-dir C:\\Katarina\\state\\readonly-observer
  python scripts/ai/check_stage0_health.py --state-dir DIR --output build/stage0-health.json --require-pass
  python scripts/ai/check_stage0_health.py --state-dir DIR --since ISO --breakdown   # diagnostic failure breakdown
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.operations.data_health import assess, audit  # noqa: E402
from katarina.intelligence.operations.stage0_breakdown import breakdown  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True, help="Observer state directory (holds context.sqlite3)")
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--since", help="Inclusive ISO-8601 UTC boundary with explicit timezone, or 'official' "
                                        "for the Owner-approved Stage 0 count start (STAGE0_COUNT_SINCE_UTC)")
    parser.add_argument("--output", help="Write the JSON report here")
    parser.add_argument("--require-pass", action="store_true", help="Exit 1 unless every criterion passes")
    parser.add_argument("--audit", action="store_true", help="Run WP14 read-only data evidence audit")
    parser.add_argument("--dataset", help="Optional path to WP8a development dataset directory")
    parser.add_argument("--breakdown", action="store_true",
                        help="Diagnostic failure breakdown by day/hour/symbol/market phase (never the verdict)")
    args = parser.parse_args(argv)

    since = None
    if args.since == "official":
        from katarina.intelligence.operations.observation_ledger import STAGE0_COUNT_SINCE_UTC
        args.since = STAGE0_COUNT_SINCE_UTC
    if args.since is not None:
        try:
            since = datetime.fromisoformat(args.since)
            if since.tzinfo is None or since > datetime.now(timezone.utc):
                raise ValueError()
        except ValueError:
            parser.error("--since requires an explicit timezone and cannot be in the future")

    path = Path(args.state_dir) / "context.sqlite3"
    if not path.is_file():
        tag = "STAGE0_AUDIT" if args.audit else "STAGE0_HEALTH"
        print(f"{tag} NO_DATA context.sqlite3 not found")
        return 1 if args.require_pass else 0
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        db.execute("PRAGMA query_only = ON")
        if args.breakdown:
            report = breakdown(db, datetime.now(timezone.utc), since=since)
        elif args.audit:
            report = audit(
                db,
                datetime.now(timezone.utc),
                since=since,
                dataset_dir=args.dataset,
                interval_seconds=args.interval_seconds,
                state_dir=args.state_dir,
            )
        else:
            report = assess(db, datetime.now(timezone.utc), interval_seconds=args.interval_seconds, since=since)
    finally:
        db.close()
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    if args.breakdown:
        for phase, count in sorted(report["failures_by_market_phase"].items()):
            print(f"{count:6} {phase} {report['failures_by_phase_and_reason'][phase]}")
        for name, view in report["session_views"].items():
            print(f"VIEW {name} rate={view['rate']} cycles={view['cycles']} diagnostic_only={view['diagnostic_only']}")
        print("STAGE0_BREAKDOWN", report["failures"], "failures; official_verdict_effect=NONE")
        return 0
    if args.audit:
        for item in report.get("findings", []):
            reason_str = f" ({item['reason']})" if item.get("reason") else ""
            print(f"{item['status']:8} {item['check']}{reason_str}")
        print("STAGE0_AUDIT", report["verdict"])
    else:
        for item in report.get("criteria", []):
            print(f"{item['status']:8} {item['criterion']}")
        print("STAGE0_HEALTH", report["verdict"])
    return 1 if args.require_pass and report["verdict"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
