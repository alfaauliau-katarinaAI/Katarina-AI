"""WP8b: read verified development-only bars and simulate a REGISTERED hypothesis.

Example: python scripts/research/simulate_setups.py --dataset D:/verified-dev \
 --workspace D:/hypothesis-work --hypothesis <sha256> \
 --out D:/hypothesis-work/trades.jsonl

No broker, MT5, network, holdout opening, orders, or automatic promotion.
To evaluate results, use the existing validate_strategy.py development CLI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from katarina.research.dev_dataset import load_dev_dataset, _validated_manifest
from katarina.research.setups.simulator import simulate, trade_to_dict, validate_registration
from katarina.research.validation import HypothesisRegistry, ValidationError, canonical


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-total-bars", type=int, default=100_000)
    args = parser.parse_args(argv)
    dataset = Path(args.dataset).resolve()
    out = Path(args.out).resolve()
    if out == dataset or dataset in out.parents:
        raise ValidationError("simulation_output_must_not_modify_frozen_dataset")
    if out.exists() or out.is_symlink():
        raise ValidationError("simulation_output_already_exists")
    registry = HypothesisRegistry(Path(args.workspace) / "registry.jsonl")
    entry = validate_registration(registry, args.hypothesis)
    spec = entry["spec"]
    root, manifest, _, _, symbols = _validated_manifest(dataset)
    if spec["symbol"] not in symbols:
        raise ValidationError("registered_symbol_not_in_dataset")
    bars = load_dev_dataset(root, max_total_bars=args.max_total_bars)
    key = spec["symbol"] + "/M5.csv.gz"
    point = manifest["files"][key]["point"]
    trades = simulate(bars[spec["symbol"]], spec, args.hypothesis, point=point)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(canonical(trade_to_dict(t)) + "\n" for t in trades)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"status": "DEVELOPMENT_RESEARCH_ONLY", "hypothesis_id": args.hypothesis,
                      "dataset_sha256": manifest["manifest_sha256"], "trades": len(trades),
                      "out": str(out), "live_execution_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
