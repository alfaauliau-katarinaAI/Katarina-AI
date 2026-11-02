"""Offline replay of technical signals from verified development bars (WP4).

Diagnosis tool for T6 (docs/ROADMAP.md WP4):
Replays MarketDecisionBrain across historical verified closed bars exported by WP8a.
Tallies BUY/SELL/WAIT frequencies per symbol, playbook/method, and regime.
Avoids future candle lookahead: for every step as_of, only candles closed at or before as_of are provided.
Outputs JSON report under build/ (or specified --output).

Read-only: orders_submitted is strictly 0, does not place orders or touch holdout.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from katarina.intelligence.cognition.market_decision import MarketDecisionBrain
from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle
from katarina.research.dev_dataset import load_dev_dataset


def to_sensor_candle(row: Mapping[str, Any]) -> SensorCandle:
    closed_at = datetime.fromisoformat(row["closed_at_utc"])
    if closed_at.tzinfo is None:
        closed_at = closed_at.replace(tzinfo=timezone.utc)
    return SensorCandle(
        closed_at_utc=closed_at,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        tick_volume=float(row.get("tick_volume", 0)),
    )


def replay_dataset(
    dataset: Mapping[str, Mapping[str, List[Mapping[str, Any]]]],
    *,
    symbols: List[str] | None = None,
    min_m5_bars: int = 20,
    step_bars: int = 1,
) -> Dict[str, Any]:
    brain = MarketDecisionBrain()
    target_symbols = symbols or sorted(dataset.keys())

    summary: Dict[str, Any] = {
        "orders_submitted": 0,
        "live_execution_authorized": False,
        "total_evaluations": 0,
        "signals": Counter(),
        "by_symbol": defaultdict(lambda: {"total": 0, "signals": Counter(), "by_regime": Counter(), "by_playbook": Counter()}),
        "by_regime": Counter(),
        "by_playbook": Counter(),
        "by_symbol_signal": Counter(),
    }

    for symbol in target_symbols:
        symbol_data = dataset.get(symbol)
        if not symbol_data:
            continue
        m5_rows = symbol_data.get("M5", [])
        m15_rows = symbol_data.get("M15", [])
        h1_rows = symbol_data.get("H1", [])
        h4_rows = symbol_data.get("H4", [])

        if len(m5_rows) < min_m5_bars:
            continue

        # Pre-convert all rows into SensorCandle lists
        m5_candles = [to_sensor_candle(r) for r in m5_rows]
        m15_candles = [to_sensor_candle(r) for r in m15_rows]
        h1_candles = [to_sensor_candle(r) for r in h1_rows]
        h4_candles = [to_sensor_candle(r) for r in h4_rows]

        # Monotonic time pointers for M15, H1, H4
        idx_15 = 0
        idx_60 = 0
        idx_240 = 0

        sym_stats = summary["by_symbol"][symbol]

        for i in range(min_m5_bars - 1, len(m5_candles), step_bars):
            current_m5 = m5_candles[: i + 1]
            as_of = current_m5[-1].closed_at_utc

            while idx_15 < len(m15_candles) and m15_candles[idx_15].closed_at_utc <= as_of:
                idx_15 += 1
            while idx_60 < len(h1_candles) and h1_candles[idx_60].closed_at_utc <= as_of:
                idx_60 += 1
            while idx_240 < len(h4_candles) and h4_candles[idx_240].closed_at_utc <= as_of:
                idx_240 += 1

            current_m15 = m15_candles[:idx_15]
            current_h1 = h1_candles[:idx_60]
            current_h4 = h4_candles[:idx_240]

            # In dev_dataset, row spread is in points or spread units
            raw_spread = float(m5_rows[i].get("spread", 10))
            point = float(symbol_data.get("M5_metadata", {}).get("point", 0.00001) if "M5_metadata" in symbol_data else 0.00001)
            spread_val = max(1e-5, raw_spread * point if raw_spread > 0 else 0.0001)

            card = brain.evaluate(
                symbol=symbol,
                candles={"M5": current_m5, "M15": current_m15, "H1": current_h1, "H4": current_h4},
                as_of_utc=as_of,
                actual_spread=spread_val,
                broker_session_open=True,
                data_fresh=True,
                news_blackout=False,
                news_context_verified=True,
                strategy_evidence=None,
                risk_approved_for_paper=False,
            )

            signal = card.technical_signal or "WAIT"
            regime = card.market_state or "UNKNOWN"
            playbook = card.strategy or "UNKNOWN"

            summary["total_evaluations"] += 1
            summary["signals"][signal] += 1
            summary["by_regime"][regime] += 1
            summary["by_playbook"][playbook] += 1
            summary["by_symbol_signal"][f"{symbol}:{signal}"] += 1

            sym_stats["total"] += 1
            sym_stats["signals"][signal] += 1
            sym_stats["by_regime"][regime] += 1
            sym_stats["by_playbook"][playbook] += 1

    # Convert Counters to standard dicts for JSON serialization
    serialized_by_sym = {}
    for s, data in summary["by_symbol"].items():
        serialized_by_sym[s] = {
            "total": data["total"],
            "signals": dict(data["signals"]),
            "by_regime": dict(data["by_regime"]),
            "by_playbook": dict(data["by_playbook"]),
        }

    return {
        "orders_submitted": 0,
        "live_execution_authorized": False,
        "total_evaluations": summary["total_evaluations"],
        "signals": dict(summary["signals"]),
        "by_symbol": serialized_by_sym,
        "by_regime": dict(summary["by_regime"]),
        "by_playbook": dict(summary["by_playbook"]),
        "by_symbol_signal": dict(summary["by_symbol_signal"]),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars-dir", required=True, help="Directory of verified dev dataset bars")
    parser.add_argument("--output", default="build/research/replay_technical_signals.json", help="Output JSON path")
    parser.add_argument("--symbols", nargs="*", default=None, help="Optional subset of symbols to evaluate")
    parser.add_argument("--step-bars", type=int, default=1, help="Step between M5 evaluations (default 1)")
    args = parser.parse_args(argv)

    dataset = load_dev_dataset(args.bars_dir)
    result = replay_dataset(dataset, symbols=args.symbols, step_bars=args.step_bars)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Replay complete: {result['total_evaluations']} evaluations. Results saved to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
