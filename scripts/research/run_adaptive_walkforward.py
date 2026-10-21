"""Run bounded, read-only adaptive research on tracked V6 paper outcomes.

No MT5 import, broker login, network fetch or orders. Intended for GitHub
Actions Ubuntu workers. Artifacts are diagnostic, never promotion evidence.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from katarina.intelligence.lab.adaptive_walkforward import PaperEvent, replay_walk_forward
from katarina.intelligence.broker.broker_scan_universe import resolve_broker_symbols

INPUT = ROOT / "docs/research/outputs/20261012/brain_unified_intraday_v6_trades.csv"
OUTPUT = ROOT / "artifacts/adaptive_walkforward"


def load_archived_v6(path: Path):
    if not path.is_file():
        raise FileNotFoundError("archived_v6_trade_data_unavailable")
    with path.open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    required = {"symbol", "mode", "side", "cut", "exit_time",
                "R", "score", "spread_atr"}
    if not records or not required.issubset(records[0]):
        raise ValueError("unexpected_v6_archive_schema")
    archive_symbols = sorted({row["symbol"] for row in records})
    selection = resolve_broker_symbols(
        [SimpleNamespace(name=s, trade_mode=4) for s in archive_symbols])
    wanted = set(selection.symbols)
    events = []
    counts = {"ignored_outside_scope": 0, "ignored_scalping": 0}
    for row in records:
        if row["symbol"] not in wanted:
            counts["ignored_outside_scope"] += 1
            continue
        if row["mode"] != "INTRADAY":
            counts["ignored_scalping"] += 1
            continue
        events.append(PaperEvent(
            symbol=row["symbol"], strategy_id="V6_INTRADAY_BRAIN_GATED",
            side=row["side"], cut=int(row["cut"]),
            exit_time=int(row["exit_time"]), modeled_r=float(row["R"]),
            score=float(row["score"]), spread_atr=float(row["spread_atr"])))
    return events, selection, counts, len(records)


def write_report(destination: Path, events, selection, excluded, original_count):
    destination.mkdir(parents=True, exist_ok=True)
    cases = {}
    for extra_cost in (0.0, .10, .20):
        case = replay_walk_forward(events, extra_cost_r=extra_cost)
        cases[f"extra_{extra_cost:.2f}R"] = case
        (destination / f"case_extra_{extra_cost:.2f}R.json").write_text(
            json.dumps(case, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8")
    current = cases["extra_0.00R"]
    with (destination / "decisions.csv").open("w", newline="", encoding="utf-8") as output:
        rows = current.get("decisions", [])
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    with (destination / "paper_trades.csv").open("w", newline="", encoding="utf-8") as output:
        rows = current.get("completed_paper_trades", [])
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "project": "KATARINA Adaptive Market Research",
        "source": INPUT.relative_to(ROOT).as_posix(),
        "source_rows_original": original_count,
        "source_rows_selected_17_market_scope": len(events),
        "selected_archive_symbol_mapping": selection.matches,
        "not_represented_in_archived_trade_rows": list(selection.unavailable),
        "ignored": excluded,
        "implementation": {
            "closed_paper_outcomes_only": True,
            "contextual_strategy_memory": True,
            "research_only_adaptive_selection": True,
            "separate_buy_sell_memory": True,
            "portfolio_cap_two": True,
            "risk_per_entry_ceiling": 0.0025,
            "risk_reduces_on_drawdown": True,
            "max_account_drawdown_stop": 0.08,
            "extra_cost_stress_tested": True,
            "multiple_strategies_with_matched_outcomes_in_archive": False,
            "actual_H1_market_regime_available": False,
        },
        "limitations": [
            "All V6 historical trades were already inspected in prior KATARINA research; this is NOT independent OOS",
            "Data contains previously V6-selected trades, not all original pre-ranking candidate opportunities",
            "Retrospective V6 shadow labels may be used once closed, including rejected adaptive admissions",
            "Alternative breakout/sweep/reversion strategies cannot be historically scored from this trade-only CSV",
            "Return and cost assumptions are hypothetical; commissions, broker fills, margin and swap not reconciled",
            "Historical broker timestamp zone/DST and point-in-time news veto remain unverified",
            "No live-order authorization; quantitative performance is not a projection of future P/L",
        ],
        "cases": {
            name: {
                "event_count": case.get("events"),
                "adaptive": case.get("adaptive"),
                "v6_conditional_benchmark": case.get("v6_conditional_benchmark"),
            } for name, case in cases.items()},
        "production_action": "WAIT",
        "live_execution_authorized": False,
        "orders_sent": 0,
    }
    (destination / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")
    lines = [
        "# KATARINA — Adaptive historical replay (research only)",
        "",
        "**Production: WAIT. This is a retrospective, previously inspected V6 sample, not independent OOS.**",
        "",
        f"Archived V6 rows: {original_count}; priority-scope rows: {len(events)}; "
        f"symbols represented: {len(selection.matches)}.",
        "",
        "| Extra cost per event | Adaptive trades | Adaptive return % | "
        "Adaptive max DD % | Conditional V6 return % |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, case in cases.items():
        a = case.get("adaptive", {})
        b = case.get("v6_conditional_benchmark", {})
        lines.append(
            f"| {key} | {a.get('trades',0)} | {a.get('return_pct','n/a')} | "
            f"{a.get('max_drawdown_pct','n/a')} | {b.get('return_pct','n/a')} |")
    lines.extend([
        "", "Data limitations: archived selected-paper outcomes only; no OHLC"
        " multi-strategy replay, historical news, tick fills, independently"
        " unseen holdout or verified account economics.",
        "",
        "BUY and SELL memory is separate. Context for archived records is a"
        " **spread/score proxy**, not a validated market regime.",
        "No production gate, account, position or live risk setting was modified.",
        "",
    ])
    markdown = "\n".join(lines)
    (destination / "SUMMARY.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({
        "scope_rows": len(events),
        "scope_symbols": len(selection.matches),
        "cases": {
            name: {"trades": case.get("adaptive",{}).get("trades"),
                   "return_pct": case.get("adaptive",{}).get("return_pct"),
                   "conditional_v6_return_pct":
                       case.get("v6_conditional_benchmark",{}).get("return_pct")}
            for name,case in cases.items()},
        "live_execution_authorized": False, "orders_sent": 0,
        "results": str(destination),
    }, ensure_ascii=False))
    return markdown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=INPUT)
    ap.add_argument("--output", type=Path, default=OUTPUT)
    args = ap.parse_args()
    events, selection, skipped, count = load_archived_v6(args.source)
    if not events:
        raise RuntimeError("no_eligible_v6_events_in_priority_universe")
    write_report(args.output, events, selection, skipped, count)


if __name__ == "__main__":
    main()
