"""Fail-closed descriptive validation of prospective shadow quote outcomes.

Only 15-minute pre-registered horizons are considered. Non-overlapping
observations mitigate serial dependence but do not imply independent trades.
No SL/TP path, fills, commission, or slippage is present in this dataset.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from statistics import mean, median
import json

FAMILY = "trend_impulse_break_v1"
HORIZON = 900
MIN_OBSERVED = 30
MIN_DAYS = 10
MAX_MISSING_RATIO = 0.20


def evaluate(db):
    sql = """SELECT observation_id,symbol,side,entry_time,due_time,context,
                    status,markout_bps,midpoint_bps
             FROM forward_markouts WHERE horizon=?
             ORDER BY symbol,side,entry_time,observation_id"""
    matched = {}
    for oid,symbol,side,entry,due,raw,status,markout,midpoint in db.execute(sql,(HORIZON,)):
        context = json.loads(raw)
        signals = context.get("shadow_hypotheses") or []
        if not any(isinstance(h,dict) and h.get("family")==FAMILY and
                   h.get("side")==side and h.get("research_only") is True and
                   h.get("live_risk_authorized") is False for h in signals):
            continue
        # Evaluate news-readiness strata separately, never retrospectively
        # remove the candidates blocked by the news gate.
        ready = bool((context.get("context") or {}).get("ready"))
        regime = context.get("regime_detail") or "UNKNOWN"
        key = (symbol, side, ready, regime)
        matched.setdefault(key,[]).append(
            (oid,entry,due,status,markout,midpoint))

    groups = []
    for (symbol,side,ready,regime),rows in sorted(matched.items()):
        chosen = []
        overlap_skipped = 0
        last_due = float("-inf")
        for item in rows:
            oid,entry,due,status,markout,midpoint = item
            if not all(isfinite(x) for x in (entry,due)) or due < entry+HORIZON:
                raise ValueError("invalid_forward_interval")
            if entry < last_due:
                overlap_skipped += 1
                continue
            chosen.append(item)
            last_due = due

        measured = [r for r in chosen if r[3]=="OBSERVED"]
        pending = sum(r[3]=="PENDING" for r in chosen)
        missing = sum(r[3]=="MISSING_EXIT" for r in chosen)
        if any(r[3] not in ("PENDING","MISSING_EXIT","OBSERVED") for r in chosen):
            raise ValueError("invalid_outcome_status")
        if any(r[4] is None or r[5] is None or not
               all(isfinite(v) for v in (r[4],r[5])) for r in measured):
            raise ValueError("invalid_observed_markout")
        values = [r[4] for r in measured]
        days = set(datetime.fromtimestamp(r[1],timezone.utc).date().isoformat()
                   for r in measured)
        # Pending horizons are right-censored, not failed exits. A running
        # observer normally has recent pending rows on every report.
        matured = len(measured)+missing
        missing_ratio = missing/matured if matured else 0
        adequate = (len(measured)>=MIN_OBSERVED and len(days)>=MIN_DAYS and
                    missing_ratio <= MAX_MISSING_RATIO)
        mean_bps = mean(values) if values else None
        daily = {}
        for item in measured:
            key = datetime.fromtimestamp(item[1],timezone.utc).date().isoformat()
            daily.setdefault(key,[]).append(item[4])
        positive_days = sum(mean(vals)>0 for vals in daily.values())
        groups.append(dict(
            symbol=symbol, side=side, family=FAMILY, horizon_seconds=HORIZON,
            entry_context_ready=ready, regime=regime,
            nonoverlap_observations=len(chosen), observed=len(measured),
            pending=pending, missing_exit=missing,
            overlap_excluded=overlap_skipped, distinct_utc_days=len(days),
            spread_included=True, commission_slippage_included=False,
            mean_markout_bps=mean_bps,
            median_markout_bps=median(values) if values else None,
            mean_midpoint_bps=mean(r[5] for r in measured) if measured else None,
            positive_days=positive_days,
            positive_days_fraction=positive_days/len(days) if days else None,
            indicative_positive_quoted_markout=(
                bool(adequate and mean_bps > 0 and
                     positive_days/len(days)>=0.60)),
            evidence_status="DESCRIPTIVE_SUFFICIENT" if adequate
                else "INSUFFICIENT_FORWARD_EVIDENCE",
            promotion_allowed=False))
    return dict(kind="prospective_shadow_quote_diagnostic",
                family=FAMILY,horizon_seconds=HORIZON,
                minimum_observed=MIN_OBSERVED,minimum_distinct_days=MIN_DAYS,
                maximum_missing_fraction=MAX_MISSING_RATIO,
                cannot_reconstruct_predeployment_signals=True,
                commission_slippage_calibrated=False,
                is_realized_strategy_pnl=False,
                model_promotion_allowed=False,groups=groups)
