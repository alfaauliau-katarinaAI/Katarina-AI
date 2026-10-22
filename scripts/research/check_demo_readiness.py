"""Read-only Stage 3 report from ONE private demo outbox; no MT5 connection or orders."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.research.demo_readiness import summarize_demo_outbox
from katarina.research.validation import write_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outbox", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--regimes", help="Private JSON object mapping intent IDs to regime labels")
    parser.add_argument("--decisions", help="Private JSON lines: decision_id, action, reasons")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    source, output = Path(args.outbox).resolve(), Path(args.output).resolve()
    inputs = [source] + [Path(p).resolve() for p in (args.regimes, args.decisions) if p]
    if output in inputs or (output.exists() and any(output.samefile(p) for p in inputs)):
        parser.error("output must not overwrite an input")
    regimes = json.loads(Path(args.regimes).read_text()) if args.regimes else {}
    decisions = [json.loads(line) for line in Path(args.decisions).read_text().splitlines() if line.strip()] if args.decisions else []
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        report = summarize_demo_outbox(db, currency=args.currency, regimes=regimes, decisions=decisions)
    digest = write_report(report, output)
    print("RECONCILIATION", report["reconciliation"]["status"], "CLOSED", report["performance"]["closed_trades"],
          "FILE_SHA256", digest, "LIVE_OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
