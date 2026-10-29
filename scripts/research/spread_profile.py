"""WP10a: CLI script for generating descriptive broker spread profile from verified tick files.

Example:
  python scripts/research/spread_profile.py --state-dir DIR \
      --since 2026-10-22 --until 2026-10-28 --output build/research/spread_profile.json

Only writes the requested descriptive profile report, never alters the observer database or orders.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from katarina.research.spread_profile import build_spread_profile  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, help="Observer state directory holding context.sqlite3")
    parser.add_argument("--since", required=True, help="Start date inclusive (YYYY-MM-DD)")
    parser.add_argument("--until", required=True, help="End date inclusive (YYYY-MM-DD)")
    parser.add_argument("--output", default="build/research/spread_profile.json", help="Output JSON path")
    args = parser.parse_args(argv)

    state = Path(args.state_dir).resolve()
    output = Path(args.output).resolve()
    if output == state or state in output.parents:
        parser.error("output_must_be_outside_observer_state")

    report = build_spread_profile(state, since=args.since, until=args.until)

    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    try:
        temp.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)

    print(json.dumps({
        "status": "DESCRIPTIVE_PROFILE_GENERATED",
        "usage": report["usage"],
        "symbols": list(report["symbols"].keys()),
        "output": str(output),
        "live_execution_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
