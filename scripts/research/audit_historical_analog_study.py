"""Independent analog backtest audit: provenance, timestamps, labels, scores."""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from evaluate_regime_prediction_ml import (
    select_samples,chronological_split,FOLDS,scores,EMBARGO_SECONDS)
from katarina.intelligence.perception.historical_analog_memory import (
    fit_history,query_analogs)

def clock(text):
    d=datetime.fromisoformat(text)
    if d.tzinfo is None:raise ValueError("timezone_required")
    return d.timestamp()

def audit(analog,regime,previous):
    if analog.get("kind")!="causal_same_symbol_historical_analog_retrieval_study_v1" or (
        analog.get("decision")!="NO_TRADE" or analog.get("live_execution_enabled") is not False or
        analog.get("model_promotion_allowed") is not False):
        raise ValueError("unauthorized_analog_archive")
    horizon=analog["horizon_hours"]
    if horizon not in (1,4):raise ValueError("invalid_horizon")
    folds={(e["symbol"],e["fold"]):e for e in analog["by_symbol_fold"]}
    original={(r["symbol"],r["fold"],r["time_utc"]):r
              for r in previous["scored_test_rows"]}
    tests=defaultdict(list)
    for e in analog["predictions"]:
        tests[(e["symbol"],e["fold"])].append(e)
    n=0;neighbors=0
    if len(folds)!=len(tests):raise ValueError("incomplete_folds")
    for sym in regime["distinct_instruments"]:
        original_samples=select_samples(regime,sym,horizon)
        for fold,train_periods,test_period in FOLDS:
            if (sym,fold) not in folds:continue
            train,test=chronological_split(original_samples,train_periods,test_period)
            record=folds[(sym,fold)]
            if len(train)!=record["train_count"] or len(test)!=record["test_count"]:
                raise ValueError("broken_chronological_split")
            if max(x["label_end"] for x in train)+EMBARGO_SECONDS>=min(x["signal_time"] for x in test):
                raise ValueError("future_label_leaked_into_train")
            bank=fit_history(train,sym,horizon)
            allowed={x["source"]["close_time_utc"]:(x["y"],x["label_end"])
                     for x in train}
            entries=sorted(tests[(sym,fold)],key=lambda e:e["time_utc"])
            if len(entries)!=len(test):raise ValueError("test_rows_incomplete")
            y=[];ps=[];bases=[];logits=[]
            for idx,(observed,sample) in enumerate(zip(entries,test)):
                if observed["symbol"]!=sym or observed["time_utc"]!=sample["source"]["close_time_utc"]:
                    raise ValueError("wrong_market_sample_or_time")
                if observed["target_future_M5_close_up"]!=sample["y"] or (
                  abs(clock(observed["label_resolution_utc"])-sample["label_end"])>.01):
                    raise ValueError("outcome_or_horizon_tampering")
                if abs(observed["p_training_prior"]-bank["prevalence"])>1e-10:
                    raise ValueError("future_baseline_prevalence_leak")
                reference=original.get((sym,fold,observed["time_utc"]))
                if reference is None:
                    raise ValueError("missing_prior_model_comparison")
                ps.append(observed["p_historical_analogs"])
                bases.append(observed["p_training_prior"])
                logits.append(reference["p_technical_plus_regime"])
                y.append(observed["target_future_M5_close_up"])
                if observed["analog_estimate_is_calibrated"] is not False:
                    raise ValueError("false_probability_calibration")
                for neighbor in observed["three_nearest_historical_samples"]:
                    key=neighbor["sample_time_utc"]
                    if key not in allowed or not (
                            allowed[key][1]+EMBARGO_SECONDS<sample["signal_time"]):
                        raise ValueError("future_or_cross_train_analog")
                    if neighbor["resolved_target_up"]!=bool(allowed[key][0]) or (
                        neighbor["label_resolved_before_prediction"] is not True):
                        raise ValueError("historical_neighbor_label_forged")
                    neighbors+=1
                if idx in (0,len(test)//2,len(test)-1):
                    result=query_analogs(bank,sample["source"],sample["signal_time"])
                    predicted=result["p_up"] if result["p_up"] is not None else bank["prevalence"]
                    if abs(predicted-observed["p_historical_analogs"])>1e-9 or (
                        result["status"]!=observed["analog_status"]):
                        raise ValueError("sampled_prediction_not_reproducible")
            for method,values in (("historical_analogs",ps),("prevalence",bases),
                     ("previous_logistic",logits)):
                recalculated=scores(values,y)
                stored=record["metrics"][method]
                for key in ("n","brier","log_loss","accuracy"):
                    if abs(recalculated[key]-stored[key])>1e-9:
                        raise ValueError("stored_forecast_score_is_wrong")
            n+=len(test)
    if analog["prediction_count"]!=n:
        raise ValueError("missing_prediction_rows")
    return dict(kind="historical_analogs_audit",
        horizon_hours=horizon,
        original_labeled_snapshots_verified=n,
        nearest_neighbor_evidence_links_verified=neighbors,
        future_data_leak_checks_passed=True,
        symbol_separation_verified=True,
        predictions_recomputed_per_fold=True,
        Brier_and_logloss_recomputed=True,
        truly_unseen_profitability_proven=False,
        live_execution_enabled=False,model_promotion_allowed=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--previous",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    files=[Path(x).read_bytes() for x in (a.report,a.source,a.previous)]
    doc,src,old=map(json.loads,files)
    if doc["source_sha256"]!=sha256(files[1]).hexdigest() or (
        doc["previous_model_sha256"]!=sha256(files[2]).hexdigest()):
        raise ValueError("evidence_source_hash_failed")
    result=audit(doc,src,old)
    result["report_sha256"]=sha256(files[0]).hexdigest()
    output=Path(a.output)
    if output.exists():raise FileExistsError("immutable_analog_audit")
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2),flush=True)
if __name__=="__main__":
    main()
