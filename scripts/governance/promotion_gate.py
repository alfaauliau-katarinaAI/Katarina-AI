"""CLI for the promotion gate (docs/ROADMAP.md, "Gerbang promosi").

  python scripts/governance/promotion_gate.py --check
  python scripts/governance/promotion_gate.py --hashes            # print current hashes of locked files
  python scripts/governance/promotion_gate.py --write-lock docs/governance/promotions/P-0001-....json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from katarina.governance.promotion_gate import LOCK_PATH, check, current_hashes, load_json, write_lock  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--hashes", action="store_true")
    group.add_argument("--write-lock", metavar="RECORD")
    args = parser.parse_args()
    if args.check:
        violations = check(ROOT)
        for line in violations:
            print("PROMOTION_GATE_FAIL", line)
        if not violations:
            print("PASS_PROMOTION_GATE")
        return 1 if violations else 0
    if args.hashes:
        files = load_json(ROOT / LOCK_PATH)["files"]
        print(json.dumps(current_hashes(ROOT, files), indent=2))
        return 0
    write_lock(ROOT, args.write_lock)
    print("PROMOTION_LOCK_WRITTEN", args.write_lock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
