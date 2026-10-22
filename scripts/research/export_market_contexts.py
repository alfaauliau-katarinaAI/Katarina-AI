"""Export Stage 2 development contexts from Stage 0 broker tick files (read-only; no broker, no orders).

  python scripts/research/export_market_contexts.py --state-dir C:\\Katarina\\state\\readonly-observer \
      --workspace W --symbol XAUUSD --trades development.jsonl --lookback-minutes 60 --bar-minutes 5 \
      --atr-bars 6 --output contexts.jsonl

``--workspace`` is the Stage 1 workspace (``split.json``). Writes the context rows (JSON lines, the
``validate_strategy.py market-filter --contexts`` input) and ``<output>.manifest.json`` listing the tick
files used and every signal that got no context, with its reason.
"""
from contextlib import closing
from pathlib import Path
import argparse
import json
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.research import validation as v  # noqa: E402
from katarina.research.context_export import export_contexts  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True, help="Observer state directory (context.sqlite3, broker-ticks/)")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trades", required=True, help="Development signals, JSON lines (validation.Trade)")
    parser.add_argument("--lookback-minutes", type=int, required=True)
    parser.add_argument("--bar-minutes", type=int, required=True)
    parser.add_argument("--atr-bars", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    state, output = Path(args.state_dir).resolve(), Path(args.output).resolve()
    if state in output.parents:
        parser.error("output must be outside the observer state directory")
    raw = json.loads((Path(args.workspace) / "split.json").read_text(encoding="utf-8"))
    split = v.DataSplit(raw["development_start"], raw["development_end"], raw["holdout_start"],
                        raw["holdout_end"], gaps=tuple(tuple(g) for g in raw.get("gaps", ())))
    lines = Path(args.trades).read_text(encoding="utf-8").splitlines()
    signals = [v.Trade.from_dict(json.loads(line)) for line in lines if line.strip()]
    with closing(sqlite3.connect((state / "context.sqlite3").as_uri() + "?mode=ro", uri=True, timeout=10)) as db:
        db.execute("PRAGMA query_only=ON")
        rows, manifest = export_contexts(db, state, signals, symbol=args.symbol, split=split,
                                         lookback_minutes=args.lookback_minutes, bar_minutes=args.bar_minutes,
                                         atr_bars=args.atr_bars)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    v.write_report(manifest, output.with_name(output.name + ".manifest.json"))
    print("CONTEXTS", manifest["contexts"], "of", manifest["signals"], "missing", manifest["missing_reasons"],
          "manifest_sha256", manifest["manifest_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
