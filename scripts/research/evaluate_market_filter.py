"""Stage 2 market-filter CLI (docs/ROADMAP.md, Tahap 2). Development data only; no broker, no orders.

  # 1. register the filter before evaluating it (it is a trial in the Stage 1 registry)
  python scripts/research/evaluate_market_filter.py register --workspace W --base-spec base.json --params f.json --name NAME
  # 2. development report (holdout trades are never read)
  python scripts/research/evaluate_market_filter.py evaluate --workspace W --filter ID --trades trades.jsonl \
      --contexts contexts.jsonl

The workspace is the Stage 1 workspace (``split.json``, ``costs.json``, ``registry.jsonl``). Context
rows follow :class:`katarina.research.market_filter.MarketContext`; reports go to ``<workspace>/reports/``.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.research import market_filter as mf  # noqa: E402
from katarina.research import validation as v  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("register", "evaluate"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--base-spec")
    parser.add_argument("--params", help="JSON object of filter thresholds (see market_filter.CONDITIONS)")
    parser.add_argument("--name")
    parser.add_argument("--filter")
    parser.add_argument("--trades")
    parser.add_argument("--contexts")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace)
    now = datetime.now(timezone.utc)
    registry = v.HypothesisRegistry(workspace / "registry.jsonl")
    if args.command == "register":
        spec = mf.filter_spec(name=args.name or "", base_spec=load(args.base_spec), parameters=load(args.params))
        entry = registry.register(spec, registered_utc=now)
        print("FILTER", entry["hypothesis_id"], "trials", registry.trial_count())
        return 0
    split_raw = load(workspace / "split.json")
    split = v.DataSplit(split_raw["development_start"], split_raw["development_end"], split_raw["holdout_start"],
                        split_raw["holdout_end"], gaps=tuple(tuple(g) for g in split_raw.get("gaps", ())))
    costs = v.CostModel(**load(workspace / "costs.json"))
    trades = [v.Trade.from_dict(row) for row in rows(args.trades)]
    contexts = {c.trade_id: c for c in (mf.MarketContext.from_dict(row) for row in rows(args.contexts))}
    vault = v.HoldoutVault(trades, split, registry, workspace / "holdout-openings.jsonl")
    report = mf.evaluate_filter(vault, args.filter, contexts, costs=costs, as_of=now)
    name = f"filter-{args.filter[:12]}-{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    digest = v.write_report(report, workspace / "reports" / name)
    ratio = report["median_cost_to_favorable_move"]
    print("VERDICT", report["verdict"], "passed", report["passed"], "of", report["signals"],
          "cost_to_move", ratio["unfiltered"], "->", ratio["filtered"], "file_sha256", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
