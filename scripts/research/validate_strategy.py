"""Stage 1 validation CLI (docs/research/VALIDATION_PROTOCOL.md). No broker, no orders.

  # 1. register before testing (a changed definition is a new trial)
  python scripts/research/validate_strategy.py register --workspace W --spec spec.json
  # 2. development report (holdout trades are never read)
  python scripts/research/validate_strategy.py development --workspace W --hypothesis ID --trades trades.jsonl
  # 3. once, after the holdout ends: open the holdout and report
  python scripts/research/validate_strategy.py holdout --workspace W --hypothesis ID --trades trades.jsonl \
      --opened-by Owner --reason "final strategy"

The workspace holds ``split.json`` (periods and GAPs), ``costs.json`` (slippage/commission in price
units), ``registry.jsonl`` and ``holdout-openings.jsonl``; reports go to ``<workspace>/reports/``.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.research import validation as v  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("register", "development", "holdout"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--spec")
    parser.add_argument("--hypothesis")
    parser.add_argument("--trades", help="JSON lines, one trade per line (see katarina.research.validation.Trade)")
    parser.add_argument("--opened-by")
    parser.add_argument("--reason")
    parser.add_argument("--code-sha256", help="Hash of evaluated strategy code; must match the registered definition")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace)
    now = datetime.now(timezone.utc)
    registry = v.HypothesisRegistry(workspace / "registry.jsonl")
    if args.command == "register":
        entry = registry.register(load(args.spec), registered_utc=now)
        print("HYPOTHESIS", entry["hypothesis_id"], "trials", registry.trial_count())
        return 0
    split_raw = load(workspace / "split.json")
    split = v.DataSplit(split_raw["development_start"], split_raw["development_end"], split_raw["holdout_start"],
                        split_raw["holdout_end"], gaps=tuple(tuple(g) for g in split_raw.get("gaps", ())))
    costs = v.CostModel(**load(workspace / "costs.json"))
    def read_trades():
        lines = Path(args.trades).read_text(encoding="utf-8").splitlines()
        return [v.Trade.from_dict(json.loads(line)) for line in lines if line.strip()]

    # Holdout bytes must not be read until authorization checks and the opening receipt exist.
    vault = v.HoldoutVault(read_trades() if args.command == "development" else (), split, registry,
                          workspace / "holdout-openings.jsonl",
                          holdout_loader=read_trades if args.command == "holdout" else None)
    if args.command == "development":
        report = v.evaluate_development(vault, args.hypothesis, costs=costs, as_of=now,
                                        code_sha256=args.code_sha256)
    else:
        report = v.evaluate_holdout(vault, args.hypothesis, costs=costs, opened_by=args.opened_by or "",
                                    reason=args.reason or "", now=now, code_sha256=args.code_sha256)
    name = f"{args.command}-{args.hypothesis[:12]}-{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    digest = v.write_report(report, workspace / "reports" / name)
    print("VERDICT", report["verdict"], "trades", report["statistics"]["trades"],
          "expectancy_r", report["statistics"]["expectancy_r"], "file_sha256", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
