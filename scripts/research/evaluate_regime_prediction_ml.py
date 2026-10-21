"""Time-purged, per-symbol directional prediction baseline v1.

Purpose: test whether causal M5/M15/H1 features and regime context improve
1h FUTURE M5 closing-price direction vs a training-only prevalence baseline.
This is not an executable trade strategy and has NO broker transaction
costs / fill model. Research periods were previously studied: folds are
chronological diagnostics, not pristine OOS evidence.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime,timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from statistics import mean
import numpy as np

TARGET_HOURS=1
EMBARGO_SECONDS=4*3600
MIN_TRAIN=90
MIN_TEST=50
L2=4.0
CLAMP=0.025
FEATURE_VERSION="per_symbol_price_context_regime_v1"
FOLDS=(
 ("august_to_september",("august",),"september"),
 ("august_september_to_october",("august","september"),"october_diagnostic")
)
FRAME_LABELS=("M5","M15","H1")
PERIOD_ORDER={"august":0,"september":1,"october_diagnostic":2}

def stamp(iso):
    x=datetime.fromisoformat(iso)
    if x.tzinfo is None:raise ValueError("no_timezone")
    return x.timestamp()

from katarina.intelligence.analog_feature_schema import make_features

def select_samples(report,symbol,horizon_hours=1):
    rows=[]
    for x in report["classified_observations"]:
        if x["symbol"]!=symbol or x["regime"]=="UNKNOWN":continue
        out=x["future_close_displacement"].get(str(horizon_hours)+"h")
        if out is None:continue
        value=float(out["signed_directional_displacement_ATR"])
        if not isfinite(value):continue
        if any(k not in x["frames"] for k in FRAME_LABELS):continue
        t=stamp(x["close_time_utc"])
        e=stamp(out["close_time_utc"])
        if not t+horizon_hours*3600-300<=e<=t+horizon_hours*3600:
            raise ValueError("unexpected_label_end")
        rows.append(dict(symbol=symbol,period=x["study_period"],
            signal_time=t,label_end=e,y=int(value>0),
            regime=x["regime"],source=x))
    return sorted(rows,key=lambda r:r["signal_time"])

def train_logistic(rows,kind):
    X=np.array([make_features(e["source"],kind) for e in rows],dtype=float)
    y=np.array([e["y"] for e in rows],dtype=float)
    average=X.mean(axis=0)
    scale=X.std(axis=0)
    scale[scale<1e-8]=1.
    design=np.column_stack([np.ones(len(X)),(X-average)/scale])
    w=np.zeros(design.shape[1])
    prior=float(y.mean())
    w[0]=np.log(max(.01,prior)/max(.01,1-prior))
    penalty=np.eye(len(w))*L2
    penalty[0,0]=0.
    # Batch Newton updates. All standardization statistics, prevalence,
    # features and coefficients are fit solely on *training* rows.
    for i in range(30):
        raw=np.clip(design@w,-30,30)
        pred=1/(1+np.exp(-raw))
        grad=design.T@(pred-y)+penalty@w
        curvature=pred*(1-pred)
        hess=design.T@(design*curvature[:,None])+penalty+np.eye(len(w))*1e-6
        step=np.linalg.solve(hess,grad)
        w-=np.clip(step,-2,2)
        if np.max(np.abs(step))<1e-7:break
    return dict(kind=kind,avg=average,scale=scale,weights=w,
         mean_prior=prior,train_samples=len(rows),iterations=i+1)

def predict(model, rows):
    X=np.array([make_features(e["source"],model["kind"]) for e in rows],dtype=float)
    z=np.column_stack([np.ones(len(X)),(X-model["avg"])/model["scale"]])
    output=1/(1+np.exp(-np.clip(z@model["weights"],-30,30)))
    return [float(np.clip(v,CLAMP,1-CLAMP)) for v in output]

def scores(pred,true):
    if not pred:return dict(n=0,brier=None,log_loss=None,
                            accuracy=None,positive_prevalence=None)
    p=np.array(pred,dtype=float);y=np.array(true,dtype=float)
    if len(p)!=len(y) or not np.all(np.isfinite(p)):
        raise ValueError("invalid_predictions")
    return dict(n=len(y),
        brier=float(np.mean((p-y)**2)),
        log_loss=float(-np.mean(y*np.log(p)+(1-y)*np.log(1-p))),
        accuracy=float(np.mean((p>=.5)==y)),
        positive_prevalence=float(np.mean(y)))

def chronological_split(rows,train_periods,test_period):
    """Enforce label-resolution chronology plus fixed 4h pre-test embargo."""
    test=[x for x in rows if x["period"]==test_period]
    if not test:return [],[]
    test_start=min(x["signal_time"] for x in test)
    train=[x for x in rows if x["period"] in train_periods
           and x["label_end"]+EMBARGO_SECONDS<test_start]
    if any(x["label_end"]+EMBARGO_SECONDS>=test_start for x in train):
        raise ValueError("train_target_leaked")
    return train,test

def run(report,horizon_hours=1):
    if report.get("kind")!="causal_mtf_market_regime_diagnostics_v1" or (
        report.get("live_execution_enabled") is not False or
        report.get("model_promotion_allowed") is not False):
        raise ValueError("wrong_or_untrusted_historical_dataset")
    results=[]
    trials=[]
    excluded=defaultdict(int)
    for symbol in report["distinct_instruments"]:
        rows=select_samples(report,symbol,horizon_hours)
        for label,train_periods,test_period in FOLDS:
            train,test=chronological_split(rows,train_periods,test_period)
            if not test:
                excluded[symbol+"|"+label]="no_test";continue
            test_start=min(x["signal_time"] for x in test)
            if len(train)<MIN_TRAIN or len(test)<MIN_TEST:
                excluded[symbol+"|"+label]=dict(train=len(train),test=len(test),
                    reason="insufficient_training_or_evaluation")
                continue
            if len(set(x["y"] for x in train))<2:
                excluded[symbol+"|"+label]="single_train_class";continue
            y=[x["y"] for x in test]
            base=np.clip(mean(x["y"] for x in train),CLAMP,1-CLAMP)
            probs={"prevalence":[float(base)]*len(test)}
            model_digest={}
            for name in ("technical","regime_only","technical_plus_regime"):
                m=train_logistic(train,name)
                probs[name]=predict(m,test)
                model_digest[name]=sha256(json.dumps(
                    dict(avg=m["avg"].tolist(),scale=m["scale"].tolist(),
                         weights=m["weights"].tolist()),sort_keys=True).encode()).hexdigest()
            stats={k:scores(v,y) for k,v in probs.items()}
            result=dict(symbol=symbol,fold=label,
              train_periods=train_periods,test_period=test_period,
              train_count=len(train),test_count=len(test),
              train_max_label_end_utc=datetime.fromtimestamp(
                  max(v["label_end"] for v in train),timezone.utc).isoformat(),
              test_start_utc=datetime.fromtimestamp(test_start,timezone.utc).isoformat(),
              purge_embargo_seconds=EMBARGO_SECONDS,
              all_train_labels_before_test=True,
              training_class_prevalence=float(base),
              model_coefficients_sha256=model_digest,
              metric=stats,model_promotion_allowed=False)
            results.append(result)
            for i,item in enumerate(test):
                trials.append(dict(symbol=symbol,fold=label,
                  time_utc=item["source"]["close_time_utc"],
                  observed_regime=item["regime"],
                  y_actual_horizon_positive=item["y"],
                  label_end_utc=datetime.fromtimestamp(
                       item["label_end"],timezone.utc).isoformat(),
                  **{"p_"+key:v[i] for key,v in probs.items()},
                  not_executed_trade=True))
    return dict(kind="per_symbol_purged_directional_prediction_study_v1",
       purpose="compare_direction_calibration_for_future_{}_hour_M5_close_only".format(horizon_hours),
       target_horizon_hours=horizon_hours,
       source_report_version=report["kind"],
       source_historical_windows_reused=True,
       train_only_on_past_completed_labels=True,
       purge_embargo_seconds=EMBARGO_SECONDS,
       timeseries_train_test_splits=list(FOLDS),
       not_broker_net_executable_PNL=True,
       future_return_is_not_market_regime_ground_truth=True,
       no_new_unseen_prospective_holdout=True,
       no_model_auto_promotion=True,model_promotion_allowed=False,
       live_execution_enabled=False,decision="NO_TRADE",
       model_methods=["training_only_prevalence","regularized_logistic_closed_indicator",
                      "regularized_logistic_regime_only",
                      "regularized_logistic_closed_indicator_plus_regime"],
       default_hyperparameters=dict(L2=L2,clip=CLAMP,minimum_train=MIN_TRAIN,
                minimum_test=MIN_TEST),
       excluded=dict(excluded),fold_results=results,scored_test_rows=trials)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--horizon-hours",type=int,choices=(1,4),default=1)
    a=p.parse_args()
    source=Path(a.report).read_bytes()
    report=json.loads(source)
    result=run(report,horizon_hours=a.horizon_hours)
    result["source_sha256"]=sha256(source).hexdigest()
    target=Path(a.output)
    if target.exists():raise FileExistsError("immutable_prediction_report")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    for f in result["fold_results"]:
        print(json.dumps(dict(symbol=f["symbol"],fold=f["fold"],
          train=f["train_count"],test=f["test_count"],
          brier={k:round(v["brier"],5) for k,v in f["metric"].items()},
          accuracy={k:round(v["accuracy"],3) for k,v in f["metric"].items()})),flush=True)
    print("REPORT",str(target),"folds",len(result["fold_results"]),
          "rows",len(result["scored_test_rows"]))
if __name__=="__main__":
    main()
