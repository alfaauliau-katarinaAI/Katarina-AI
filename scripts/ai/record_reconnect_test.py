"""Record a deliberate MT5 disconnect test for Stage 0 (docs/ROADMAP.md, Tahap 0). No broker access.

Record the start, then disrupt MT5 (for example stop terminal64.exe); the observer must recover by
itself. `check_stage0_health.py` judges each test from the ledger: an OK cycle within 10 minutes.

  python scripts/ai/record_reconnect_test.py --state-dir DIR --method KILL_TERMINAL
  python scripts/ai/record_reconnect_test.py --state-dir DIR --method KILL_TERMINAL --started 2026-10-22T04:29:24+00:00
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.operations.observation_ledger import RECONNECT_METHODS, record_reconnect_test  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--method", required=True, choices=sorted(RECONNECT_METHODS))
    parser.add_argument("--started", help="ISO time with offset when the disruption began (default: now)")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)
    path = Path(args.state_dir) / "context.sqlite3"
    if not path.is_file():
        print("RECONNECT_TEST_REFUSED context.sqlite3 not found")
        return 1
    now = datetime.now(timezone.utc)
    started = datetime.fromisoformat(args.started) if args.started else now
    db = sqlite3.connect(path, timeout=30)
    try:
        added = record_reconnect_test(db, started_utc=started, method=args.method, now=now, note=args.note)
    finally:
        db.close()
    print("RECONNECT_TEST_RECORDED" if added else "RECONNECT_TEST_ALREADY_RECORDED", started.isoformat(), args.method)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
