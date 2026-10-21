"""A conservative audit gate for research strategy readiness.

A profitable-looking historical subset alone cannot authorize paper or live
trading. This pure module never calls MT5 or places orders.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class Evidence:
    symbol:str
    trades:int
    mean_r:float|None
    profit_factor:float|None
    cost_stress_mean_r:float|None
    segment_mean_r:tuple[float|None,...]
    unseen_holdout:bool=False
    broker_costs_reconciled:bool=False
    historical_news_verified:bool=False
    full_chronological_replay:bool=False
    causal_inputs_verified:bool=False

@dataclass(frozen=True)
class ResearchReadiness:
    status:str
    reasons:tuple[str,...]
    candidate_for_paper:bool
    live_execution_authorized:bool=False

def evaluate_readiness(x:Evidence)->ResearchReadiness:
    if (type(x.symbol) is not str or not x.symbol.strip()
            or type(x.trades) is not int or x.trades<0):
        raise ValueError("invalid_identity_or_count")
    if type(x.segment_mean_r) is not tuple:
        raise ValueError("invalid_segment_metrics")
    for v in (x.mean_r,x.profit_factor,x.cost_stress_mean_r,*x.segment_mean_r):
        if v is not None:
            if type(v) not in (int,float):
                raise ValueError("invalid_metric_type")
            try:
                finite=isfinite(v)
            except OverflowError:
                finite=False
            if not finite:
                raise ValueError("nonfinite_metrics")
    reasons=[]
    if x.trades<150:reasons.append("not_enough_observations")
    if x.mean_r is None or x.mean_r<=0:
        reasons.append("nonpositive_expectancy")
    if x.profit_factor is None or x.profit_factor<1.20:
        reasons.append("profit_factor_insufficient")
    if x.cost_stress_mean_r is None or x.cost_stress_mean_r<.05:
        reasons.append("edge_disappears_under_cost_stress")
    if len(x.segment_mean_r)<3 or any(v is None or v<=0 for v in x.segment_mean_r):
        reasons.append("unstable_chronological_segments")
    checks=[
        (x.unseen_holdout,"historical_period_previously_inspected"),
        (x.broker_costs_reconciled,"broker_costs_unreconciled"),
        (x.historical_news_verified,"historical_news_unverified"),
        (x.full_chronological_replay,"sampling_not_full_replay"),
        (x.causal_inputs_verified,"point_in_time_causality_unverified"),
    ]
    reasons.extend(reason for good,reason in checks if good is not True)
    return ResearchReadiness(
        "PAPER_RESEARCH_CANDIDATE" if not reasons else "UNVALIDATED",
        tuple(reasons),not reasons)