"""Transparent, *non-selective* regime/method cost sensitivity of replay labels.

Every closed-bar candidate is included, winners and losers alike.
No hyperparameter search, deployment recommendation, or calibrated
confidence interval; unknown broker bid/ask makes all R proxy-only.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
from math import isfinite
from statistics import mean

COST_STRESS=(.05,.15,.30)


def describe_candidates(signals,splits,*,costs=COST_STRESS):
    if not costs or any(not isfinite(v) or v<0 or v>.5 for v in costs):
        raise ValueError("invalid_predeclared_cost_levels")
    labeled={}
    for group in ("train","validation","test"):
        for x in splits.get(group,[]):
            key=(x.symbol,x.strategy_id,x.side,x.cut)
            if key in labeled:
                raise ValueError("reused_signal_across_holdouts")
            labeled[key]=group
    buckets=defaultdict(list)
    for s in signals:
        key=(s["symbol"],s["method"],s["side"],s["signal_at"])
        phase=labeled.get(key,"purged_overlap_or_insufficient")
        # Purged candidates remain in the descriptive total. Never hide a
        # losing trade to enhance apparent performance.
        metadata=(s["symbol"],s["method"],s["side"],s["regime"])
        buckets[metadata].append((s["signal_at"],s["label_known_at"],
                                   s["proxy_gross_r"],phase))
    cohorts=[]
    all_values=[]
    for (symbol,method,side,regime),trades in sorted(buckets.items()):
        trades.sort(key=lambda x:x[0])
        vals=[x[2] for x in trades]
        all_values+=vals
        months={datetime.fromtimestamp(x[0],timezone.utc).strftime("%Y-%m")
                for x in trades}
        by_cost={}
        for cost in costs:
            profits=[v-cost for v in vals]
            gross=sum(p for p in profits if p>0)
            losses=-sum(p for p in profits if p<0)
            eq=0.;peak=0.;dd=0.
            for value in profits:
                eq+=value;peak=max(peak,eq);dd=max(dd,peak-eq)
            by_cost[str(cost)]={
                "mean_net_proxy_r":round(mean(profits),6) if profits else None,
                "profit_factor_proxy":round(gross/losses,5) if losses else None,
                "max_closed_drawdown_r_proxy":round(dd,6),
            }
        count={name:sum(t[3]==name for t in trades)
               for name in ("train","validation","test",
                            "purged_overlap_or_insufficient")}
        cohorts.append({
            "symbol":symbol,"method":method,"side":side,"regime":regime,
            "all_attempts_including_blocked":len(trades),
            "retrospective_month_count":len(months),
            "split_counts":count,
            "cost_scenarios_r":by_cost,
            "research_validation":"INSUFFICIENT_INDEPENDENT_EVIDENCE",
            "eligible_for_live":False,
        })
    return {
        "kind":"ASSUMED_SPREAD_OHLC_ALL_CANDIDATES_COST_STRESS",
        "cost_levels_r":list(costs),
        "candidate_total":len(all_values),
        "source_is_reused_historical_data":True,
        "not_independent_live_or_unseen_holdout":True,
        "selection_pre_registered":False,
        "validated_live_edge":False,
        "cohorts":cohorts,
    }
