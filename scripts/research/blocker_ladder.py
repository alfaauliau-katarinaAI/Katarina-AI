"""WP9a: deterministic read-only diagnosis of observer WAIT blockers.

Example:
  python scripts/research/blocker_ladder.py --state-dir STATE \
      --since 2026-10-22T00:00:00Z --output build/research/blocker_ladder.json

Only writes the requested report, never alters the observer database or orders.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from katarina.research.blocker_ladder import read_blocker_ladder  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--since", help="Optional inclusive timestamp, aware UTC ISO-8601")
    parser.add_argument("--output", default="build/research/blocker_ladder.json")
    args = parser.parse_args(argv)
    state = Path(args.state_dir).resolve()
    output = Path(args.output).resolve()
    if output == state or state in output.parents:
        parser.error("output_must_be_outside_observer_state")
    report = read_blocker_ladder(state, since=args.since)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    try:
        temp.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    print(json.dumps({"status": "DIAGNOSTIC_ONLY",
                      "cards": report["total"]["cards"],
                      "report_sha256": report["report_sha256"],
                      "output": str(output),
                      "live_execution_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
