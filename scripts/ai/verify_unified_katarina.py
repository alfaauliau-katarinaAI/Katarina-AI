"""Single manual, no-orders acceptance view of the *existing* Katarina stack.

Does not start MT5, connect networks, create workers, place orders, alter
configurations, write data or authorize promotions. Intended for pinned
GitHub/VPS source synchronization and optional read-only shadow DB checking.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "src"))

# Logic lives in src (cleanup stage 6); names re-exported for existing callers.
from katarina.governance.unified_verification import build_stage3_evidence_backlog, verify  # noqa: E402,F401


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",type=Path,default=ROOT/"config/katarina_unified_v1.json")
    parser.add_argument("--shadow-db",type=Path,default=None)
    args=parser.parse_args()
    profile=json.loads(args.profile.read_text(encoding="utf-8"))
    print(json.dumps(verify(profile,shadow_db=args.shadow_db),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
