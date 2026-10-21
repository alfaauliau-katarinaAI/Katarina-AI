"""Katarina V2.6: research-only, fail-closed strategy selection guard.

Does not transmit orders or authorize LIVE trading.
Never use a review-period field to choose pair-level candidate configurations.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

MIN_TRADES_PER_DEV_YEAR = 20
MIN_MEAN_NET_R_PER_DEV_YEAR = 0.07


def _as_float(row, key):
    return float(row[key])


def choose_candidate(rows):
    """Choose using ONLY 2022/2023 columns. Fallback is shadow-only.

    Expected rows per pair: 144 separate strategies/thresholds/gates/exits.
    Changing 2024/25/26 outcomes, full-dataset n_exec, or future prices must
    never change the choice.
    """
    rows = list(rows)
    if not rows:
        raise ValueError("empty experiment grid")
    eligible = []
    for row in rows:
        n22 = int(row["n22"])
        n23 = int(row["n23"])
        mean22 = _as_float(row, "mean22")
        mean23 = _as_float(row, "mean23")
        record = {
            "setup": row["setup"],
            "threshold_scale": str(row["threshold_scale"]),
            "context_gate": row["context_gate"],
            "exit": row["exit"],
            "n22": n22,
            "n23": n23,
            "mean22": mean22,
            "mean23": mean23,
            "dev_floor": min(mean22, mean23),
        }
        enough = n22 >= MIN_TRADES_PER_DEV_YEAR and n23 >= MIN_TRADES_PER_DEV_YEAR
        record["dev_pass"] = (
            enough and mean22 > MIN_MEAN_NET_R_PER_DEV_YEAR
            and mean23 > MIN_MEAN_NET_R_PER_DEV_YEAR
        )
        record["enough_dev"] = enough
        eligible.append(record)

    passed = [x for x in eligible if x["dev_pass"]]
    sufficient = [x for x in eligible if x["enough_dev"]]
    if passed:
        pool = passed
        label = "DEV_SCREEN_ONLY_SHADOW"
    elif sufficient:
        pool = sufficient
        label = "ABSTAIN_SHADOW_DIAGNOSTIC"
    else:
        pool = eligible
        label = "ABSTAIN_INSUFFICIENT_SAMPLE"

    # No n_exec, n_complete, review-year counts, or review outcomes are used.
    def rank(x):
        score = x["dev_floor"] if x["enough_dev"] else float("-inf")
        return (
            score,
            x["n22"] + x["n23"],
            x["n22"],
            x["n23"],
            x["setup"],
            x["context_gate"],
            x["exit"],
            x["threshold_scale"],
        )

    chosen = max(pool, key=rank)
    return {
        "pair": rows[0]["pair"],
        "state": label,
        "n_nominal_dev_pass": len(passed),
        **chosen,
    }


def evidence_gate(nominal_dev_pass, dev_lower_2022, dev_lower_2023,
                  adverse_gap_dev_floor, verified_real_bidask,
                  clean_forward_holdout):
    """Eligibility for MORE testing; never production order permission."""
    checks = {
        "nominal_dev": bool(nominal_dev_pass),
        "dev_bootstrap_lower_2022_positive": dev_lower_2022 > 0,
        "dev_bootstrap_lower_2023_positive": dev_lower_2023 > 0,
        "gap_stress_development_positive": adverse_gap_dev_floor > 0,
        "real_bidask_reconciled": bool(verified_real_bidask),
        "clean_forward_holdout": bool(clean_forward_holdout),
    }
    return {
        "research_validation_eligible": all(checks.values()),
        "live_trading_authorized": False,
        "decision": "RESEARCH_ONLY" if all(checks.values()) else "ABSTAIN",
        "checks": checks,
    }


def select_from_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    grouped = {}
    for row in rows:
        grouped.setdefault(row["pair"], []).append(row)
    if any(len(v) != 144 for v in grouped.values()):
        raise ValueError("expected exactly 144 trials per pair")
    return [choose_candidate(v) for v in grouped.values()]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("dev_grid_csv")
    args = parser.parse_args()
    print(json.dumps(select_from_csv(args.dev_grid_csv), indent=2))
