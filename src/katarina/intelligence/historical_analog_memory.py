"""KATARINA historical-market analog engine (read-only research).

A market snapshot is compared only to *previously resolved samples of
the SAME broker symbol*. Neighbors are retrieved from past features,
never from future outcomes or another symbol. Predictions are smoothed
empirical frequencies of subsequent +1h/+4h M5-close direction; they
are NOT probabilities of profitable executable broker trades.

Fixed hyperparameters chosen before seeing this research output.
"""
from __future__ import annotations
from datetime import datetime
from statistics import mean
import numpy as np

from katarina.intelligence.analog_feature_schema import make_features,CLAMP

ANALOG_K=25
PRIOR_PSEUDOCOUNT=35.0
DISTANCE_TEMP=9.0
MIN_EFFECTIVE_NEIGHBORS=12.0
MIN_PREDICTION_LIFT=.10
MAX_NEAREST_DISTANCE=3.25
EMBARGO_SECONDS=4*3600
FEATURE_LAYOUT="causal_mtf_14plus_regime7_v1"
ANALOG_WEIGHTS=np.array([.8,.6,.55,.7,
                      1.0,.7,.7,.9,
                      .85,.65,.65,.8,
                      .5,.5,
                      .65,.65,.65,.65,.5,.5,.65],dtype=float)

def _stamp(iso):
    d=datetime.fromisoformat(iso)
    if d.tzinfo is None:raise ValueError("timezone_required")
    return d.timestamp()

def fit_history(rows,symbol,horizon_hours):
    if symbol is None or horizon_hours not in (1,4):
        raise ValueError("registered_symbol_and_horizon_required")
    if not rows or any(r.get("symbol")!=symbol for r in rows):
        raise ValueError("cross_symbol_or_empty_analog_memory")
    X=np.array([make_features(r["source"],"technical_plus_regime") for r in rows],
               dtype=np.float64)
    if X.ndim!=2 or not np.all(np.isfinite(X)):
        raise ValueError("invalid_historical_feature_memory")
    y=np.array([r["y"] for r in rows],dtype=np.float64)
    if not np.all((y==0)|(y==1)):raise ValueError("not_binary_target")
    start=np.array([r["signal_time"] for r in rows],dtype=np.float64)
    ends=np.array([r["label_end"] for r in rows],dtype=np.float64)
    if np.any(ends<=start) or np.any(ends-start>horizon_hours*3600+1):
        raise ValueError("invalid_resolved_horizon")
    center=X.mean(axis=0)
    scale=X.std(axis=0)
    scale[scale<.15]=.15  # do not exaggerate nearly constant features
    # Recent price-pattern behavior is heterogeneous across timeframes.
    # Cap standard deviations, use H1 and M15 more than M5 by design.
    weights=ANALOG_WEIGHTS.copy()
    if X.shape[1]!=len(weights):
        raise ValueError("causal_market_feature_version_changed")
    return dict(symbol=symbol,horizon_hours=horizon_hours,
        features=X,targets=y,signal_times=start,label_end=ends,
        sample_dates=[r["source"]["close_time_utc"] for r in rows],
        sample_regimes=[r["regime"] for r in rows],
        center=center,scale=scale,weights=weights,
        prevalence=float(mean(y)),
        n_train=len(rows),memory_version=FEATURE_LAYOUT)

def query_analogs(memory,source_row,now,return_neighbors=3):
    """Use only neighbors whose label *ended* before now-embargo.

    For held-out evaluation also run on the frozen train-only set.
    """
    if memory["memory_version"]!=FEATURE_LAYOUT:
        raise ValueError("memory_schema_mismatch")
    if source_row.get("symbol")!=memory["symbol"]:
        raise ValueError("cross_symbol_prediction_forbidden")
    clock=_stamp(source_row["close_time_utc"])
    if clock>now+.01 or now-clock>1800:
        raise ValueError("stale_or_future_prediction_snapshot")
    if source_row.get("regime")=="UNKNOWN":
        return dict(status="ABSTAIN_UNKNOWN",p_up=None,
            empirical_similar_up_rate=None,effective_neighbors=0,
            confidence_calibrated=False,neighbors=[])
    x=np.array(make_features(source_row,"technical_plus_regime"),dtype=float)
    valid=np.flatnonzero(memory["label_end"]+EMBARGO_SECONDS<clock)
    if len(valid)==0:return dict(status="ABSTAIN_NO_RESOLVED_ANALOGS",
        p_up=None,empirical_similar_up_rate=None,
        effective_neighbors=0,confidence_calibrated=False,neighbors=[])
    Z=(memory["features"][valid]-x)/memory["scale"]
    squared=np.sum((Z*memory["weights"])**2,axis=1)
    order=np.argsort(squared,kind="stable")[:ANALOG_K]
    ids=valid[order]
    d=np.sqrt(squared[order])
    weights=np.exp(-squared[order]/(2*DISTANCE_TEMP))
    total=float(weights.sum())
    effective=float(total*total/float(np.dot(weights,weights))) if total else 0.
    local_rate=float(np.dot(weights,memory["targets"][ids])/total) if total else None
    # Pull estimates towards train-only unconditional baseline when analogs
    # are noisy, and cap confidence under distribution shift.
    posterior=float((float(np.dot(weights,memory["targets"][ids]))+
        PRIOR_PSEUDOCOUNT*memory["prevalence"])/(total+PRIOR_PSEUDOCOUNT))
    posterior=max(CLAMP,min(1-CLAMP,posterior))
    nearest=float(d[0])
    status=("CANDIDATE" if effective>=MIN_EFFECTIVE_NEIGHBORS
        and nearest<=MAX_NEAREST_DISTANCE
        and abs(posterior-memory["prevalence"])>=MIN_PREDICTION_LIFT
        else "ABSTAIN_WEAK_ANALOG_SIGNAL")
    explain=[dict(sample_time_utc=memory["sample_dates"][int(i)],
          sample_regime=memory["sample_regimes"][int(i)],
          resolved_target_up=bool(memory["targets"][int(i)]),
          label_resolved_before_prediction=bool(
             memory["label_end"][int(i)]+EMBARGO_SECONDS<clock),
          similarity_distance=float(dis)) for i,dis in
             zip(ids[:return_neighbors],d[:return_neighbors])]
    return dict(status=status,p_up=posterior,
        baseline_prior=memory["prevalence"],
        empirical_similar_up_rate=local_rate,
        effective_neighbors=effective,nearest_distance=nearest,
        memory_samples_total=memory["n_train"],
        eligible_resolved_samples=int(len(valid)),
        prediction_snapshot_utc=source_row["close_time_utc"],
        symbol=memory["symbol"],horizon_hours=memory["horizon_hours"],
        confidence_calibrated=False,
        is_executable_trading_probability=False,
        model_promotion_allowed=False,neighbors=explain)

def load_frozen_symbol_memory(frozen,symbol,horizon,asof):
    """Read immutable historical sample index, enforce future-only usage."""
    if frozen.get("kind")!="frozen_per_symbol_historical_analog_memory_v1" or (
       frozen.get("no_live_orders") is not True or
       frozen.get("model_promotion_allowed") is not False):
        raise ValueError("untrusted_memory_for_trading")
    if frozen.get("sample_feature_version")!=FEATURE_LAYOUT:
        raise ValueError("memory_feature_schema_change")
    cutoff=_stamp(frozen["asof_utc"])
    if asof<=cutoff:
        raise ValueError("frozen_memory_cannot_predict_past_training_period")
    bank=frozen["by_symbol"].get(symbol,{}).get(str(horizon))
    if bank is None or bank.get("status")!="REFERENCE_ONLY":
        raise ValueError("missing_separate_symbol_horizon_memory")
    samples=bank["examples"]
    if len(samples)!=bank["n_samples"]:
        raise ValueError("memory_example_count_mismatch")
    X=np.array([s["features"] for s in samples],dtype=np.float64)
    y=np.array([s["outcome_future_close_up"] for s in samples],dtype=float)
    ends=np.array([_stamp(s["outcome_resolved_utc"]) for s in samples],dtype=float)
    start=np.array([_stamp(s["time_utc"]) for s in samples],dtype=float)
    if (X.ndim!=2 or X.shape[1]!=len(ANALOG_WEIGHTS)
        or not np.all(np.isfinite(X)) or
        np.any(ends+EMBARGO_SECONDS>=cutoff) or
        np.any(start>=ends) or not np.all((y==0)|(y==1))):
        raise ValueError("bad_frozen_past_only_bank")
    mean_prior=float(y.mean())
    if abs(mean_prior-bank["earlier_train_prevalence"])>1e-10:
        raise ValueError("frozen_label_prevalence_changed")
    scale=X.std(axis=0)
    scale[scale<.15]=.15
    return dict(symbol=symbol,horizon_hours=horizon,
        features=X,targets=y,signal_times=start,label_end=ends,
        sample_dates=[s["time_utc"] for s in samples],
        sample_regimes=[s["regime"] for s in samples],
        center=X.mean(axis=0),scale=scale,weights=ANALOG_WEIGHTS.copy(),
        prevalence=mean_prior,n_train=len(samples),
        memory_version=FEATURE_LAYOUT,freeze_utc=frozen["asof_utc"])


def score_rows(memory,rows):
    outputs=[]
    for row in rows:
        result=query_analogs(memory,row["source"],row["signal_time"])
        if result.get("p_up") is None:
            # Keep full coverage via the train-only baseline;
            # uncertainty/abstention remains explicit.
            result["p_up"]=memory["prevalence"]
        outputs.append(result)
    return outputs
