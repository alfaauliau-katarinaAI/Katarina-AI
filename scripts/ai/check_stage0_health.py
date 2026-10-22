"""Stage 0 data-health report (docs/ROADMAP.md, Tahap 0). Read-only; never connects to MT5.

  python scripts/ai/check_stage0_health.py --state-dir C:\\Katarina\\state\\readonly-observer
  python scripts/ai/check_stage0_health.py --state-dir DIR --output build/stage0-health.json --require-pass
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.operations.data_health import assess  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True, help="Observer state directory (holds context.sqlite3)")
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--output", help="Write the JSON report here")
    parser.add_argument("--require-pass", action="store_true", help="Exit 1 unless every criterion passes")
    args = parser.parse_args(argv)
    path = Path(args.state_dir) / "context.sqlite3"
    if not path.is_file():
        print("STAGE0_HEALTH NO_DATA context.sqlite3 not found")
        return 1 if args.require_pass else 0
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        report = assess(db, datetime.now(timezone.utc), interval_seconds=args.interval_seconds)
    finally:
        db.close()
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    for item in report["criteria"]:
        print(f"{item['status']:8} {item['criterion']}")
    print("STAGE0_HEALTH", report["verdict"])
    return 1 if args.require_pass and report["verdict"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
