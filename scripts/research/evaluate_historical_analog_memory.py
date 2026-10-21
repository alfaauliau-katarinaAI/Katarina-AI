"""KATARINA causal historical-sample analog backtest.

Uses only the earlier chronological training windows of each separate
symbol. Compares analog memory to frozen past-only prevalence baseline
and the already audited logistic + regime predictions.
"""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path

from evaluate_regime_prediction_ml import (
    FOLDS,chronological_split,select_samples,scores)
from katarina.intelligence.historical_analog_memory import (
    fit_history,score_rows,ANALOG_K,PRIOR_PSEUDOCOUNT,EMBARGO_SECONDS)

def run(source,logistic,horizon):
    if source.get("kind")!="causal_mtf_market_regime_diagnostics_v1":
        raise ValueError("invalid_historical_regime_samples")
    if source.get("live_execution_enabled") is not False:
        raise ValueError("untrusted_training_source")
    if logistic.get("kind")!="per_symbol_purged_directional_prediction_study_v1" or (
        logistic.get("target_horizon_hours",1)!=horizon):
        raise ValueError("wrong_frozen_logistic_control")
    controls={(x["symbol"],x["fold"],x["time_utc"]):x
              for x in logistic["scored_test_rows"]}
    folded=[];trials=[]
    for symbol in source["distinct_instruments"]:
        samples=select_samples(source,symbol,horizon)
        for fold,train_periods,test_period in FOLDS:
            train,test=chronological_split(samples,train_periods,test_period)
            if len(train)<90 or len(test)<50:continue
            bank=fit_history(train,symbol,horizon)
            estimates=score_rows(bank,test)
            prior=bank["prevalence"]
            y=[e["y"] for e in test]
            local=[e["p_up"] for e in estimates]
            baseline=[prior]*len(test)
            original=[]
            for item in test:
                key=(symbol,fold,item["source"]["close_time_utc"])
                if key not in controls:raise ValueError("missing_original_control")
                row=controls[key]
                if row.get("y_actual_horizon_positive",row.get("y_actual_one_hour_positive"))!=item["y"]:
                    raise ValueError("mismatch_existing_training_label")
                original.append(row["p_technical_plus_regime"])
            metrics=dict(prevalence=scores(baseline,y),
                         previous_logistic=scores(original,y),
                         historical_analogs=scores(local,y))
            foldrow=dict(symbol=symbol,fold=fold,horizon_hours=horizon,
                train_count=len(train),test_count=len(test),
                training_prevalence=prior,
                training_end_utc=datetime.fromtimestamp(max(x["label_end"] for x in train),timezone.utc).isoformat(),
                test_start_utc=datetime.fromtimestamp(min(x["signal_time"] for x in test),timezone.utc).isoformat(),
                historical_memory_size=bank["n_train"],
                abstain_weak_or_missing=sum(v["status"]!="CANDIDATE" for v in estimates),
                analog_candidates=sum(v["status"]=="CANDIDATE" for v in estimates),
                metrics=metrics,any_model_promoted=False)
            folded.append(foldrow)
            for sample,estimate in zip(test,estimates):
                trial=dict(symbol=symbol,fold=fold,horizon_hours=horizon,
                    time_utc=sample["source"]["close_time_utc"],
                    label_resolution_utc=datetime.fromtimestamp(sample["label_end"],timezone.utc).isoformat(),
                    target_future_M5_close_up=sample["y"],
                    observed_regime=sample["regime"],
                    p_training_prior=float(prior),
                    p_historical_analogs=estimate["p_up"],
                    analog_status=estimate["status"],
                    analog_estimate_is_calibrated=False,
                    effective_similar_examples=estimate["effective_neighbors"],
                    empirical_local_direction_fraction=estimate["empirical_similar_up_rate"],
                    nearest_normalized_distance=estimate.get("nearest_distance"),
                    resolved_history_available=estimate.get("eligible_resolved_samples",0),
                    three_nearest_historical_samples=estimate["neighbors"],
                    decision="RESEARCH_ONLY")
                trials.append(trial)
    totals={}
    for method in ("prevalence","previous_logistic","historical_analogs"):
        if not folded:continue
        total=sum(f["test_count"] for f in folded)
        totals[method]=dict(weighted_brier=sum(
             f["test_count"]*f["metrics"][method]["brier"] for f in folded)/total,
            weighted_accuracy=sum(f["test_count"]*f["metrics"][method]["accuracy"]
             for f in folded)/total,
            folds_better_than_prevalence=(
                sum(f["metrics"][method]["brier"]<
                    f["metrics"]["prevalence"]["brier"]-1e-9 for f in folded)
                 if method!="prevalence" else None),
            test_rows=total,folds=len(folded))
    return dict(kind="causal_same_symbol_historical_analog_retrieval_study_v1",
      goal="evaluate_scenario_similarity_vs_prior_and_previous_model",
      horizon_hours=horizon,nearest_neighbors=ANALOG_K,
      prior_smoothing_pseudocount=PRIOR_PSEUDOCOUNT,
      embargo_seconds=EMBARGO_SECONDS,
      training_periods_are_not_pristine_out_of_sample=True,
      eval_data_reused_and_model_design_not_pristine=True,
      shows_actual_historical_analog_timestamps=True,
      no_transaction_costs_in_direction_probabilities=True,
      no_statistically_proven_profitability=True,
      model_promotion_allowed=False,live_execution_enabled=False,
      decision="NO_TRADE",
      aggregated=totals,by_symbol_fold=folded,
      prediction_count=len(trials),predictions=trials)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--previous",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--horizon",type=int,choices=(1,4),required=True)
    a=p.parse_args()
    source_bytes=Path(a.source).read_bytes()
    control_bytes=Path(a.previous).read_bytes()
    output=run(json.loads(source_bytes),json.loads(control_bytes),a.horizon)
    output["source_sha256"]=sha256(source_bytes).hexdigest()
    output["previous_model_sha256"]=sha256(control_bytes).hexdigest()
    target=Path(a.output)
    if target.exists():raise FileExistsError("immutable_research_output")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    for method,row in output["aggregated"].items():
        print("TOTAL",method,json.dumps(row),flush=True)
    for fold in output["by_symbol_fold"]:
        print("FOLD",fold["symbol"],fold["fold"],fold["test_count"],
             "baseline",round(fold["metrics"]["prevalence"]["brier"],5),
             "analog",round(fold["metrics"]["historical_analogs"]["brier"],5),
             "candidate",fold["analog_candidates"],flush=True)
    print("OUTPUT",target)
if __name__=="__main__":
    main()
