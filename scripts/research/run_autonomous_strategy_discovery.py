"""GitHub-hosted causal strategy discovery on synthetic fixture or supplied OHLC.

No broker connection. No generated source execution. Results cannot promote
strategies and do not establish independent forward alpha.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from math import sin
from pathlib import Path

from katarina.intelligence.lab.autonomous_strategy_discovery import Candle, discover


def deterministic_fixture(count=930) -> tuple[Candle, ...]:
    """Explicitly FABRICATED data with known, changing oscillatory regimes."""
    t=int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp())
    price=2200.
    result=[]
    for i in range(count):
        opening=price
        change=.32*sin(i*.27)+.16*sin(i*.079)+(
            .09 if (i//28)%2 == 0 else -.09)
        price=opening+change
        extra=.12+.04*abs(sin(i*.33))
        result.append(Candle(t+3600*(i+1),opening,
                             max(opening,price)+extra,
                             min(opening,price)-extra,price))
    return tuple(result)


def load_closed_ohlc_csv(path: Path) -> tuple[Candle,...]:
    """Require explicit point-in-time UTC closed bars (no lookahead labels)."""
    if not path.is_file() or path.suffix.lower() != ".csv":
        raise ValueError("csv_ohlc_file_required")
    if path.stat().st_size > 3_000_000:
        raise ValueError("csv_data_too_large")
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader=csv.DictReader(source)
        required={"close_at_utc","open","high","low","close"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("csv_columns_required:"+",".join(sorted(required)))
        bars=[]
        for line in reader:
            timestamp=datetime.fromisoformat(line["close_at_utc"].replace("Z","+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("explicit_utc_offset_required")
            if timestamp.utcoffset().total_seconds()!=0:
                raise ValueError("utc_only_not_local_broker_clock")
            bars.append(Candle(
                int(timestamp.timestamp()),float(line["open"]),
                float(line["high"]),float(line["low"]),float(line["close"])))
    return tuple(bars)


def run_cli() -> None:
    parser=argparse.ArgumentParser()
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--synthetic", action="store_true")
    inputs.add_argument("--bars",type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--summary",required=True,type=Path)
    parser.add_argument("--seed",type=int,default=77)
    parser.add_argument("--population",type=int,default=16)
    parser.add_argument("--generations",type=int,default=3)
    opts=parser.parse_args()
    if opts.synthetic:
        bars=deterministic_fixture()
        source="SYNTHETIC_FABRICATED_HOURLY_FIXTURE"
    else:
        bars=load_closed_ohlc_csv(opts.bars)
        source="USER_SUPPLIED_UNVERIFIED_CLOSED_OHLC"
    result=discover(bars,seed=opts.seed,population=opts.population,
                    generations=opts.generations)
    result["data_origin"]=source
    result["number_of_realized_broker_orders"]=0
    result["broker_costs_calibrated"]=False
    result["independent_live_forward_evidence"]=False
    assert result["orders_sent"]==0
    assert result["production_action"]=="WAIT"
    assert result["live_execution_authorized"] is False
    assert result["held_out_was_used_in_selection"] is False
    assert result["model_promotion_permitted"] is False
    assert result["code_rewrite_permitted"] is False
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    opts.output.write_text(json.dumps(result,indent=2,sort_keys=True,
                                      allow_nan=False)+"\n",encoding="utf-8")
    rows=[
        "# Katarina autonomous rule discovery — OFFLINE ONLY",
        "",
        f"Source: **{source}**. No verified broker executions.",
        "",
        f"Newly explored rule combinations: **{result['candidate_trials']}**.",
        "Evolved rules use chronological train (60%), validation (20%) and",
        "untouched diagnostic holdout (20%). No holdout-driven selection.",
        "",
        "| Candidate | Side | Conditions | Training | Validation | Holdout | Status |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for r in result["candidate_rules"]:
        spec=r["genome"]
        expr=" AND ".join(c["feature"]+c["op"]+str(c["level"])
                          for c in spec["conditions"])
        rows.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            r["candidate_id"],spec["side"],expr,
            r["train"]["trades"],r["validation"]["trades"],
            r["held_out"]["trades"],r["research_status"]))
    rows+=["","**Production action: WAIT.** No code deployment, no orders,",
           "no proven forward alpha. Real data and broker fills require",
           "separate validation and governance.",]
    opts.summary.parent.mkdir(parents=True,exist_ok=True)
    opts.summary.write_text("\n".join(rows)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":"DISCOVERY_COMPLETED_RESEARCH_ONLY",
        "data_origin":source,
        "trials":result["candidate_trials"],
        "shortlisted":len(result["candidate_rules"]),
        "production_action":result["production_action"]},sort_keys=True))

if __name__=="__main__":
    run_cli()
