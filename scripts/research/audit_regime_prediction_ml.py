"""Integrity audit of per-symbol chronological prediction experiments.

Verifies source row labels/time ordering, score math, model/baseline
disjoint test intervals, and frozen training-only prevalence.
Does not claim independent forward OOS or executed trading expectancy.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from statistics import mean
from evaluate_regime_prediction_ml import (
    scores,FOLDS,EMBARGO_SECONDS,select_samples,CLAMP)

def stamp(value):
    dt=datetime.fromisoformat(value)
    if dt.tzinfo is None:raise ValueError("no_timezone")
    return dt.timestamp()

def audit(ml,source):
    if ml.get("kind")!="per_symbol_purged_directional_prediction_study_v1":
        raise ValueError("wrong_study_kind")
    if ml.get("decision")!="NO_TRADE" or (
         ml.get("live_execution_enabled") is not False or
         ml.get("model_promotion_allowed") is not False):
        raise ValueError("risk_permission_mutated")
    if ml.get("source_historical_windows_reused") is not True or (
        ml.get("no_new_unseen_prospective_holdout") is not True):
        raise ValueError("unverifiable_oos_promotion")
    if source.get("kind")!="causal_mtf_market_regime_diagnostics_v1":
        raise ValueError("wrong_regime_source")
    horizon=ml.get("target_horizon_hours",1)
    if horizon not in (1,4):raise ValueError("invalid_target_horizon")
    all_source={sym:select_samples(source,sym,horizon) for sym in source["distinct_instruments"]}
    if len(ml["fold_results"])!=len({(r["symbol"],r["fold"]) for r in ml["fold_results"]}):
        raise ValueError("duplicate_symbol_fold")
    rowmap=defaultdict(list)
    for r in ml["scored_test_rows"]:
        key=(r["symbol"],r["fold"])
        rowmap[key].append(r)
        if r.get("not_executed_trade") is not True:
            raise ValueError("predictions_conflated_with_orders")
        for k in ("p_prevalence","p_technical","p_regime_only",
                  "p_technical_plus_regime"):
            if not CLAMP-1e-8<=r[k]<=1-CLAMP+1e-8:
                raise ValueError("probabilities_outside_declared_bounds")
    checked=0
    for item in ml["fold_results"]:
        symbol=item["symbol"]
        name=item["fold"]
        contract=next((f for f in FOLDS if f[0]==name),None)
        if contract is None:raise ValueError("unknown_folds")
        historical=all_source[symbol]
        test=[x for x in historical if x["period"]==contract[2]]
        start=min(x["signal_time"] for x in test)
        train=[x for x in historical if x["period"] in contract[1]
               and x["label_end"]+EMBARGO_SECONDS<start]
        if len(train)!=item["train_count"] or len(test)!=item["test_count"]:
            raise ValueError("source_split_not_reproducible")
        if max(x["label_end"] for x in train)+EMBARGO_SECONDS>=start:
            raise ValueError("train_label_future_leakage")
        prior=min(max(mean(x["y"] for x in train),CLAMP),1-CLAMP)
        if abs(prior-item["training_class_prevalence"])>1e-10:
            raise ValueError("baseline_fit_on_test_data")
        got=sorted(rowmap[(symbol,name)],key=lambda e:e["time_utc"])
        if len(got)!=len(test):raise ValueError("prediction_count_wrong")
        for predicted,original in zip(got,test):
            if abs(stamp(predicted["time_utc"])-original["signal_time"])>.1 or (
               predicted.get("y_actual_horizon_positive",predicted.get("y_actual_one_hour_positive"))!=original["y"]):
                raise ValueError("prediction_label_source_mismatch")
            if abs(stamp(predicted["label_end_utc"])-original["label_end"])>.1:
                raise ValueError("future_label_resolution_mismatch")
            if abs(predicted["p_prevalence"]-prior)>1e-10:
                raise ValueError("prior_not_frozen_training_only")
        labels=[x["y"] for x in test]
        for method in ("prevalence","technical","regime_only",
                       "technical_plus_regime"):
            expected=scores([v["p_"+method] for v in got],labels)
            actual=item["metric"][method]
            for metric in ("n","brier","log_loss","accuracy","positive_prevalence"):
                if abs(expected[metric]-actual[metric])>1e-9:
                    raise ValueError("metric_mismatch_"+method+"_"+metric)
        checked+=len(got)
    if checked!=len(ml["scored_test_rows"]):
        raise ValueError("unaccounted_predictions")
    return dict(kind="per_symbol_purged_model_integrity_audit",
      fold_count=len(ml["fold_results"]),outcomes_verified=checked,
      source_labels_and_folds_verified=True,
      train_test_purging_verified=True,
      fixed_baseline_train_only_verified=True,
      individual_scored_probabilities_verified=True,
      warning="This does not independently reconstruct model coefficients or future real trading edge",
      strategy_validated=False,live_execution_enabled=False,
      model_promotion_allowed=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    original=Path(a.report).read_bytes()
    raw=Path(a.source).read_bytes()
    ml=json.loads(original)
    source=json.loads(raw)
    if ml.get("source_sha256")!=sha256(raw).hexdigest():
        raise ValueError("source_sha256_mismatch")
    result=audit(ml,source)
    result["report_sha256"]=sha256(original).hexdigest()
    out=Path(a.output)
    if out.exists():raise FileExistsError("immutable")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
