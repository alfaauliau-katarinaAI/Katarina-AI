"""Day-block bootstrap for analog Brier uplift over past-only baseline.

Day resampling partially accounts for overlapping 30-minute snapshots,
but does NOT account for model selection/multiple tests. Not trading PNL.
"""
from __future__ import annotations
import argparse,json,random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from hashlib import sha256

REPS=2000
SEED=20261011

def summarize(docs):
    combined=[]
    for h,doc in docs:
        if doc.get("decision")!="NO_TRADE" or (
            doc.get("horizon_hours")!=h or doc.get("live_execution_enabled") is not False):
            raise ValueError("archive_not_safe_to_score")
        for symbol in sorted({x["symbol"] for x in doc["predictions"]}):
            rows=[r for r in doc["predictions"] if r["symbol"]==symbol]
            if not rows:continue
            deltas=[(r["p_training_prior"]-r["target_future_M5_close_up"])**2-
                    (r["p_historical_analogs"]-r["target_future_M5_close_up"])**2
                    for r in rows]
            rng=random.Random(SEED+h*10+sum(ord(c) for c in symbol))
            byfold=defaultdict(lambda:defaultdict(list))
            for r,delta in zip(rows,deltas):
                byfold[r["fold"]][r["time_utc"][:10]].append(delta)
            boots=[]
            for rep in range(REPS):
                total=[]
                for fold,days in sorted(byfold.items()):
                    keys=sorted(days)
                    for _ in keys:
                        total.extend(days[rng.choice(keys)])
                boots.append(mean(total))
            boots.sort()
            lower=boots[int((REPS-1)*.025)]
            upper=boots[int((REPS-1)*.975)]
            fold_results={}
            for fold,days in sorted(byfold.items()):
                values=[v for arr in days.values() for v in arr]
                fold_results[fold]=dict(n=len(values),mean_brier_reduction=mean(values))
            combined.append(dict(symbol=symbol,horizon_hours=h,
                scored_rows=len(rows),distinct_dates=len(set(r["time_utc"][:10] for r in rows)),
                mean_brier_reduction_over_prior=mean(deltas),
                approximate_day_block_bootstrap_95pct_CI=[lower,upper],
                both_chronological_evaluations_positive=all(
                   v["mean_brier_reduction"]>0 for v in fold_results.values()),
                fold_results=fold_results,
                multiple_testing_adjusted=False,unseen_future_validated=False))
    return dict(kind="historical_analog_dayblock_uncertainty_v1",
        horizon_scopes=[1,4],no_live_trading=True,
        no_broker_costs_in_future_close_labels=True,
        repeated_observations_are_not_independent_trades=True,
        confidence_intervals_uncorrected_for_multiple_search=True,
        model_promotion_allowed=False,live_execution_enabled=False,
        by_symbol=combined)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--one-hour",required=True)
    p.add_argument("--four-hour",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    raw1=Path(a.one_hour).read_bytes()
    raw4=Path(a.four_hour).read_bytes()
    data=summarize([(1,json.loads(raw1)),(4,json.loads(raw4))])
    data["source_sha256"]=dict(one_hour=sha256(raw1).hexdigest(),
                 four_hour=sha256(raw4).hexdigest())
    output=Path(a.output)
    if output.exists():raise FileExistsError("immutable")
    output.write_text(json.dumps(data,indent=2)+"\n")
    for r in data["by_symbol"]:
        print(r["symbol"],str(r["horizon_hours"])+"h",
            "lift",round(r["mean_brier_reduction_over_prior"],6),
            "CI",r["approximate_day_block_bootstrap_95pct_CI"],
            "both_folds",r["both_chronological_evaluations_positive"],flush=True)
    print("OUTPUT",output)
if __name__=="__main__":
    main()
