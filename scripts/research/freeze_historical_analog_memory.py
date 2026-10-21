"""Create immutable, symbol-isolated historical examples for FUTURE-only analysis.

No auto trading; trained on historically reused dates. The memory can only
answer new snapshots after the *whole archive* was built/frozen.
"""
import argparse,json
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path

from evaluate_regime_prediction_ml import select_samples
from katarina.intelligence.perception.historical_analog_memory import (
    fit_history,EMBARGO_SECONDS,FEATURE_LAYOUT)

FREEZE_TIME="2026-10-10T12:00:00+00:00"

def freeze(source,cutoff):
    if source.get("kind")!="causal_mtf_market_regime_diagnostics_v1" or (
        source.get("live_execution_enabled") is not False):
        raise ValueError("bad_regime_evidence")
    until=datetime.fromisoformat(cutoff).timestamp()
    out={}
    for sym in source["distinct_instruments"]:
        out[sym]={}
        for horizon in (1,4):
            rows=[x for x in select_samples(source,sym,horizon)
                 if x["label_end"]+EMBARGO_SECONDS<until]
            if len(rows)<100:
                out[sym][str(horizon)]=dict(status="NOT_ENOUGH_RESOLVED_SAMPLES")
                continue
            m=fit_history(rows,sym,horizon)
            examples=[]
            for i,x in enumerate(rows):
                examples.append(dict(time_utc=x["source"]["close_time_utc"],
                  outcome_resolved_utc=datetime.fromtimestamp(
                      x["label_end"],timezone.utc).isoformat(),
                  regime=x["regime"],outcome_future_close_up=int(x["y"]),
                  features=[float(v) for v in m["features"][i]]))
            out[sym][str(horizon)]=dict(status="REFERENCE_ONLY",
                family="per_symbol_causal_historical_analogs_v1",
                horizon_hours=horizon,n_samples=len(examples),
                earlier_train_prevalence=m["prevalence"],
                data_end_before_UTC=cutoff,
                examples=examples)
    return dict(kind="frozen_per_symbol_historical_analog_memory_v1",
        asof_utc=cutoff,
        prediction_cannot_be_backtested_with_this_frozen_full_index=True,
        analysis_only=True,fully_closed_outcomes=True,
        multi_market_model_sharing_forbidden=True,
        sample_feature_version=FEATURE_LAYOUT,
        criteria="Each historical future M5 close label resolved plus 4h embargo BEFORE memory cutoff",
        no_live_orders=True,model_promotion_allowed=False,
        source_study_was_previously_researched=True,
        by_symbol=out)

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source",required=True)
    a.add_argument("--output",required=True)
    args=a.parse_args()
    raw=Path(args.source).read_bytes()
    doc=freeze(json.loads(raw),FREEZE_TIME)
    doc["source_sha256"]=sha256(raw).hexdigest()
    out=Path(args.output)
    if out.exists():raise FileExistsError("immutable_frozen_memory")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({"symbol_horizon_memory_sizes":{
        sym:{h:record.get("n_samples",0) for h,record in banks.items()}
        for sym,banks in doc["by_symbol"].items()},
        "cutoff":FREEZE_TIME,"output":str(out)},indent=2))
if __name__=="__main__":
    main()
