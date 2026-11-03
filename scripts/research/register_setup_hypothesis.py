"""Register WP8b research hypotheses with the max-five-per-symbol/side gate.

Usage: python scripts/research/register_setup_hypothesis.py \
 --workspace D:/workspace --spec D:/setup-spec.json

Only the existing HypothesisRegistry may write the hypothesis ledger.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from katarina.research.setups.simulator import METHODS
from katarina.research.validation import HypothesisRegistry, ValidationError


def register_setup(registry, spec, *, registered_utc):
    if not isinstance(spec, dict) or spec.get("playbook") not in METHODS:
        raise ValidationError("unsupported_registered_setup")
    if spec.get("side") not in ("BUY", "SELL"):
        raise ValidationError("setup_side_invalid")
    hid = registry.hypothesis_id(spec)  # validates required fields and JSON
    entries = registry.ledger.entries()  # verifies existing chained hash
    if any(e["hypothesis_id"] == hid for e in entries):
        return registry.get(hid)  # idempotent, no new trial
    key = spec["symbol"], spec["side"]
    if sum(1 for e in entries if (e["spec"]["symbol"], e["spec"]["side"]) == key) >= 5:
        raise ValidationError("too_many_hypotheses_per_symbol_side")
    return registry.register(spec, registered_utc=registered_utc)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", required=True)
    p.add_argument("--spec", required=True)
    args=p.parse_args(argv)
    raw=json.loads(Path(args.spec).read_text(encoding="utf-8"))
    registry=HypothesisRegistry(Path(args.workspace)/"registry.jsonl")
    entry=register_setup(registry,raw,registered_utc=datetime.now(timezone.utc))
    print(json.dumps({"status":"REGISTERED_DEVELOPMENT_ONLY",
                      "hypothesis_id":entry["hypothesis_id"],
                      "trial_count":registry.trial_count(),
                      "live_execution_authorized":False},sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
