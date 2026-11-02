"""WP4 T6: replay the ORIGINAL MarketDecisionPipeline on frozen DEV-only bars.

Source --bars-dir must be a WP8a archive with manifest+SHA256+independent
broker clock evidence (verified by dev_dataset.load_dev_dataset). Never
uses raw arbitrary OHLC, MT5, broker connection, future or holdout data.
Usage: python scripts/research/replay_technical_signals.py --bars-dir X --out build/replay.json
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.research.dev_dataset import load_dev_dataset, _validated_manifest  # noqa: E402
from katarina.research.validation import ValidationError, canonical, sha256_text  # noqa: E402
from katarina.intelligence.cognition.market_decision_pipeline import (  # noqa: E402
    MarketDecisionPipeline, SensorCandle,
)

TF = {"M5": 5, "M15": 15, "H1": 60, "H4": 240}


def replay_symbol(bars_by_tf, symbol, *, point: float, pipeline=None, max_cycles=1200):
    """At each M5 close, call original evaluator with only previously CLOSED bars."""
    if type(max_cycles) is not int or max_cycles < 1 or max_cycles > 10000:
        raise ValidationError("replay_cycles_limit_invalid")
    if isinstance(point, bool) or not isinstance(point, (int, float)) or not math.isfinite(point) or point <= 0:
        raise ValidationError("replay_point_missing_or_invalid")
    pipeline = pipeline or MarketDecisionPipeline()
    moments = {}
    for tf in TF:
        rows = bars_by_tf.get(tf)
        if not isinstance(rows, (list, tuple)):
            raise ValidationError("replay_timeframe_missing:" + tf)
        moments[tf] = [
            (datetime.fromisoformat(r["closed_at_utc"]).astimezone(timezone.utc),
             SensorCandle(
                 datetime.fromisoformat(r["closed_at_utc"]).astimezone(timezone.utc),
                 float(r["open"]), float(r["high"]), float(r["low"]),
                 float(r["close"]), float(r["tick_volume"])),
             float(r["spread"]))
            for r in rows
        ]
    count, counts, inspected = 0, Counter(), 0
    pointers = {tf: 0 for tf in TF}
    # The precommitted dataset itself was validated and ends before cutoff.
    for as_of, row, spread in moments["M5"]:
        if inspected >= max_cycles:
            break
        inspected += 1
        for tf in TF:
            while (pointers[tf] < len(moments[tf])
                   and moments[tf][pointers[tf]][0] <= as_of):
                pointers[tf] += 1
        if any(pointers[tf] < 55 for tf in TF):
            continue
        candles = {tf: [x[1] for x in moments[tf][max(0,pointers[tf]-70):pointers[tf]]]
                   for tf in TF}
        for tf in TF:
            if candles[tf][-1].closed_at_utc > as_of:
                raise ValidationError("REPLAY_LOOKAHEAD_FORBIDDEN")
        result = pipeline.evaluate(
            symbol=symbol, candles=candles, as_of_utc=as_of,
            actual_spread=spread * point, broker_session_open=True, data_fresh=False,
            news_blackout=False, news_context_verified=False)
        detail = getattr(result, "decision_detail", None)
        technical = getattr(detail, "technical_signal", "WAIT") if detail is not None else "WAIT"
        if technical not in ("BUY", "SELL", "WAIT"):
            raise ValidationError("REPLAY_SIGNAL_INVALID")
        counts[(technical, result.market_state, result.playbook)] += 1
        count += 1
    return {"symbol": symbol, "evaluated": count, "rows_seen": inspected,
            "signals": [{"technical_signal": signal, "regime": state,
                         "playbook": method, "count": number}
                        for (signal, state, method), number in sorted(counts.items())]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bars-dir", required=True)
    p.add_argument("--out", default="build/replay_technical_signals.json")
    p.add_argument("--max-cycles", type=int, default=1200)
    p.add_argument("--max-total-bars", type=int, default=100000)
    args = p.parse_args(argv)
    source, out = Path(args.bars_dir).resolve(), Path(args.out).resolve()
    if out == source or source in out.parents or out.exists() or out.is_symlink():
        raise ValidationError("replay_output_must_be_new_outside_frozen_dataset")
    _, manifest, _, _, _ = _validated_manifest(source)
    data = load_dev_dataset(source, max_total_bars=args.max_total_bars)
    results = [replay_symbol(
        data[symbol], symbol,
        point=manifest["files"][symbol + "/M5.csv.gz"]["point"],
        max_cycles=args.max_cycles)
        for symbol in sorted(data)]
    report = {"stage": "DEVELOPMENT_RESEARCH_ONLY",
              "method": "ORIGINAL_MARKET_DECISION_PIPELINE",
              "data_provenance": "WP8A_HASH_AND_INDEPENDENT_CLOCK_REQUIRED",
              "results": results, "live_execution_authorized": False}
    report["report_sha256"] = sha256_text(canonical(report))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True)+"\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["stage"], "sha256": report["report_sha256"],
                      "symbols": len(results), "live_execution_authorized": False},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
