"""D9 read-only per-symbol session preview. Never changes the official Stage 0 report.

Requires scoped schedule and clock evidence JSON; missing evidence stays UNVERIFIED.
There is no activation, effective-date override, MT5 connection or order path.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.operations.broker_sessions import BrokerSessions, preview  # noqa: E402
from katarina.intelligence.operations.observation_ledger import STAGE0_COUNT_SINCE_UTC  # noqa: E402

UNIVERSE_PATH = Path(__file__).resolve().parents[2] / "config" / "observer_universe.json"
OUTPUT_ROOT = Path(__file__).resolve().parents[2] / "build" / "validation"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--clock-proof", required=True)
    parser.add_argument("--since", default="official")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        since = datetime.fromisoformat(STAGE0_COUNT_SINCE_UTC if args.since == "official" else args.since)
        if since.tzinfo is None or since > now:
            raise ValueError("D9_SINCE_INVALID")
        schedule_raw = Path(args.schedule).read_bytes()
        clock_raw = Path(args.clock_proof).read_bytes()
        policy = BrokerSessions(json.loads(schedule_raw), json.loads(clock_raw))
        universe_raw = UNIVERSE_PATH.read_bytes()
        required_symbols = json.loads(universe_raw)["core"]
        db_path = Path(args.state_dir) / "context.sqlite3"
        if not db_path.is_file():
            raise ValueError("D9_LEDGER_MISSING")
        if args.output:
            requested = Path(args.output)
            if requested.is_symlink():
                raise ValueError("D9_OUTPUT_SYMLINK_FORBIDDEN")
            output = requested.resolve()
            protected = {db_path.resolve(), Path(args.schedule).resolve(), Path(args.clock_proof).resolve(),
                         UNIVERSE_PATH.resolve()}
            protected.update(Path(str(db_path.resolve()) + suffix) for suffix in ("-wal", "-shm", "-journal"))
            if output in protected or (output.exists() and any(
                    p.exists() and output.samefile(p) for p in protected)):
                raise ValueError("D9_OUTPUT_OVERWRITES_INPUT")
            if OUTPUT_ROOT.is_symlink() or OUTPUT_ROOT.parent.is_symlink():
                raise ValueError("D9_OUTPUT_ROOT_SYMLINK_FORBIDDEN")
            safe_root = OUTPUT_ROOT.resolve()
            if output == safe_root or not output.is_relative_to(safe_root):
                raise ValueError("D9_OUTPUT_PATH_NOT_ALLOWED")
            if output.exists():
                raise ValueError("D9_OUTPUT_EXISTS")
        db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")  # One consistent read snapshot across cycles and quote rows.
            report = preview(db, now, policy, required_symbols=required_symbols, since=since)
        finally:
            db.close()
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
        detail = str(error) if isinstance(error, ValueError) and str(error).startswith("D9_") else type(error).__name__
        print("D9_SESSION_PREVIEW BLOCKED", detail)
        return 2
    report["schedule_file_sha256"] = hashlib.sha256(schedule_raw).hexdigest()
    report["clock_proof_file_sha256"] = hashlib.sha256(clock_raw).hexdigest()
    report["universe_file_sha256"] = hashlib.sha256(universe_raw).hexdigest()
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as target:
            target.write(text)
    else:
        print(text, end="")
    if not report["universe_matches"]:
        print("D9_SESSION_PREVIEW BLOCKED D9_UNIVERSE_MISMATCH official_verdict_effect=NONE")
        return 2
    print("D9_SESSION_PREVIEW DIAGNOSTIC_ONLY official_verdict_effect=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
