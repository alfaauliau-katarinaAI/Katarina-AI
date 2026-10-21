"""Bounded, chronological fixed-journal screening. Never authorizes trading."""
from __future__ import annotations
import csv
import itertools
import json
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from io import StringIO
from math import isfinite
from pathlib import Path
from .mt5_journal import load_journal, _clock

FAMILIES = ("supply_demand", "support_resistance", "adx", "fibonacci",
            "candle_pressure", "adr", "relative_volume", "chart_pattern", "candle_pattern")

def number(row, key):
    value = row.get(key, "")
    if value == "":
        return None
    value = float(value)
    if not isfinite(value):
        raise ValueError("nonfinite feature: " + key)
    return value

def flags(row):
    buy = row["side"] == "BUY"
    sign = 1 if buy else -1
    near = lambda x: None if x is None else 0 <= x <= .5
    between = lambda x, lo, hi: None if x is None else lo <= x <= hi
    pressure = number(row, "candle_pressure")
    pattern = number(row, "chart_breakout")
    candle = number(row, "candle_pattern")
    return {
        "supply_demand": near(number(row, "demand_dist_atr" if buy else "supply_dist_atr")),
        "support_resistance": near(number(row, "support_dist_atr" if buy else "resistance_dist_atr")),
        "adx": between(number(row, "adx"), 20, 35),
        "fibonacci": between(number(row, "fib_retrace"), .382, .618),
        "candle_pressure": None if pressure is None else sign * pressure >= .2,
        "adr": between(number(row, "previous_day_adr_ratio"), .5, 1.5),
        "relative_volume": between(number(row, "relative_tick_volume"), 1.2, 10),
        "chart_pattern": None if pattern is None else sign * pattern > 0,
        "candle_pattern": None if candle is None else sign * candle > 0,
    }

@dataclass(frozen=True)
class Observation:
    entry: int
    known: int
    side: str
    pnl: Decimal
    risk: Decimal
    features: dict

def load(path, expected_trades, expected_net):
    validated = load_journal(Path(path), expected_trades=expected_trades,
                             expected_net_profit=Decimal(expected_net))
    raw = Path(path).read_bytes()
    text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    rows = list(csv.DictReader(StringIO(text), delimiter=";"))
    out = []
    for row in rows:
        risk = Decimal(row["initial_risk_cash"])
        if not risk.is_finite() or risk <= 0:
            raise ValueError("positive initial risk required")
        out.append(Observation(_clock(row["entry_time"], upper=False),
                               _clock(row["exit_time"], upper=True),
                               row["side"], Decimal(row["net_profit"]), risk, flags(row)))
    return sorted(out, key=lambda r: r.entry), validated.source_sha256

def metrics(rows, extra_cost_r=0.0):
    values = [float(r.pnl / r.risk) - extra_cost_r for r in rows]
    gains = sum(x for x in values if x > 0)
    losses = -sum(x for x in values if x < 0)
    equity = peak = dd = 0.
    for x in values:
        equity += x
        peak = max(peak, equity)
        dd = max(dd, peak-equity)
    return dict(trades=len(values), net_r=sum(values),
                expectancy_r=sum(values)/len(values) if values else None,
                profit_factor=gains/losses if losses else None,
                win_rate=sum(x > 0 for x in values)/len(values) if values else None,
                closed_trade_drawdown_r=dd,
                journal_net_profit=str(sum((r.pnl for r in rows), Decimal(0))))

def subset(rows, combo):
    return [r for r in rows if all(r.features.get(f) is True for f in combo)]

def choose(development, side):
    """Selection sees development only; deduplicate identical retained trades."""
    rows = [r for r in development if r.side == side]
    available = [f for f in FAMILIES if any(r.features.get(f) is not None for r in rows)]
    missing = [f for f in FAMILIES if f not in available]
    trials = []; masks = set(); duplicates = 0
    for size in range(1, len(available)+1):
        for combo in itertools.combinations(available, size):
            mask = tuple(i for i, r in enumerate(rows) if all(r.features[f] is True for f in combo))
            if mask in masks:
                duplicates += 1
                continue
            masks.add(mask)
            picked = [rows[i] for i in mask]
            stat = metrics(picked)
            # Two chronological development subwindows; no crossing labels.
            cutoff = rows[len(rows)//2].entry if rows else 0
            folds = [metrics([r for r in picked if r.entry < cutoff and r.known < cutoff], .1),
                     metrics([r for r in picked if r.entry >= cutoff], .1)]
            valid = (len(picked) >= 30 and all(f["trades"] >= 10 and f["net_r"] > 0 for f in folds)
                     and metrics(picked, .1)["net_r"] > 0)
            trials.append(dict(combination=list(combo), development=stat, folds=folds, eligible=valid))
    eligible = [t for t in trials if t["eligible"]]
    eligible.sort(key=lambda t: (-(t["development"]["expectancy_r"] or 0),
                                len(t["combination"]), t["combination"]))
    return (eligible[0]["combination"] if eligible else None), dict(
        available=available, missing=missing, nominal_combinations=2**len(available)-1,
        duplicate_masks_removed=duplicates, unique_candidates=len(trials),
        eligible_candidates=len(eligible), trials=trials)

def screen(rows):
    if len(rows) < 60 or any(a.entry > b.entry for a,b in zip(rows, rows[1:])):
        raise ValueError("at least 60 chronological observations required")
    # Fixed final 25%; purged development. Previously inspected history remains retrospective.
    cutoff = rows[3*len(rows)//4].entry
    development = [r for r in rows if r.entry < cutoff and r.known < cutoff]
    final = [r for r in rows if r.entry >= cutoff]
    results = {}
    for side in ("BUY", "SELL"):
        combo, details = choose(development, side)
        details["selected"] = combo
        if combo is not None:
            selected = subset([r for r in final if r.side == side], combo)
            details["final"] = metrics(selected)
            details["final_stress_0_1r"] = metrics(selected, .1)
            details["ablation_development"] = {
                f: metrics(subset([r for r in development if r.side == side],
                                  [x for x in combo if x != f])) for f in combo}
            details["screen_pass"] = (len(selected) >= 20 and metrics(selected,.1)["net_r"] > 0)
        else:
            details["screen_pass"] = False
        results[side] = details
    return dict(schema_version=1, research_only=True, strategy_validated=False,
                live_execution_enabled=False, final_cutoff_ns=cutoff,
                total_rows=len(rows), development_rows=len(development), final_rows=len(final),
                purged_rows=len(rows)-len(development)-len(final), baseline=metrics(rows), sides=results,
                limitations=["Fixed-journal filter diagnostic, not a new execution backtest.",
                  "Previously inspected history is not prospective unseen validation.",
                  "Large multiple-testing risk; no statistical significance claim.",
                  "Missing features never count as passing; baseline trades only, not all market bars.",
                  "0.1R extra cost is a stress scenario, not measured broker costs.",
                  "Drawdown is closed-trade R drawdown, not floating equity drawdown.",
                  "No production feature deletion or strategy promotion from this report."])

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--journal", required=True)
    p.add_argument("--expected-trades", type=int, required=True)
    p.add_argument("--expected-net", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    rows, digest = load(args.journal, args.expected_trades, args.expected_net)
    result = screen(rows)
    result["source_sha256"] = digest
    result["policy_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("total_rows","development_rows","final_rows","baseline")}))
    for side, r in result["sides"].items():
        print(side, json.dumps({k:r[k] for k in ("nominal_combinations","duplicate_masks_removed",
              "unique_candidates","eligible_candidates","selected","missing","screen_pass")}))
if __name__ == "__main__":
    main()
