"""Prospective contextual memory audit, **not** evidence of real broker P&L.

Uses only *already finalized* quote-sampled virtual outcomes, aligned by
symbol/method/side/market state and actual close time. No fabricated fills,
no historic replay as forward data, no strategy auto-promotion.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt
from statistics import mean, stdev

MIN_CASES=30
MIN_DAYS=10
MIN_MONTHS=3
MAX_MISSING=.2


def summarize(db,as_of_utc):
    if as_of_utc.tzinfo is None:
        raise ValueError("asof_must_be_timezone_aware")
    now=as_of_utc.astimezone(timezone.utc).timestamp()
    groups=defaultdict(list)
    for sym,method,side,regime,opened,ended,status,value in db.execute(
        """SELECT symbol,method,side,regime,observed_at,exit_at,
                  state,virtual_net_r FROM prospective_shadow
           WHERE observed_at<=? ORDER BY observed_at,id""",(now,)):
        if status not in ("VIRTUAL_QUOTED","UNCERTAIN_GAP","OPEN"):
            continue
        key=(sym,method,side,regime)
        if status=="VIRTUAL_QUOTED" and (ended is None or ended>now or value is None):
            continue  # future outcome cannot leak into current decision
        if status=="UNCERTAIN_GAP" and ended is not None and ended>now:
            continue
        groups[key].append((opened,ended,status,value))
    rows=[]
    for (symbol,method,side,regime),records in sorted(groups.items()):
        complete=[x for x in records if x[2]=="VIRTUAL_QUOTED"]
        missed=[x for x in records if x[2]=="UNCERTAIN_GAP"]
        pending=[x for x in records if x[2]=="OPEN"]
        values=[float(x[3]) for x in complete]
        positive=sum(x for x in values if x>0)
        negative=-sum(x for x in values if x<0)
        days={datetime.fromtimestamp(x[0],timezone.utc).date().isoformat() for x in complete}
        months={d[:7] for d in days}
        coverage=len(complete)/(len(complete)+len(missed)) if (complete or missed) else None
        m=mean(values) if values else None
        lo=(m-1.96*stdev(values)/sqrt(len(values))) if len(values)>1 else None
        pf=positive/negative if negative>0 else None
        enough=(len(values)>=MIN_CASES and len(days)>=MIN_DAYS and
                len(months)>=MIN_MONTHS and coverage is not None and
                coverage>=1-MAX_MISSING)
        if not enough:
            status="INSUFFICIENT_SAMPLE"
        elif m is None or m<=0 or lo is None or lo<=0 or pf is None or pf<=1.20:
            status="NEGATIVE_OR_UNSTABLE_QUOTE_EVIDENCE"
        else:
            status="POSITIVE_VIRTUAL_QUOTE_DIAGNOSTIC_ONLY"
        rows.append({
            "symbol":symbol,"method":method,"side":side,"regime":regime,
            "complete":len(complete),"gapped":len(missed),"pending":len(pending),
            "distinct_days":len(days),"distinct_months":len(months),
            "coverage":round(coverage,5) if coverage is not None else None,
            "mean_modeled_r":round(m,6) if m is not None else None,
            "naive_mean_lower_bound_r":round(lo,6) if lo is not None else None,
            "virtual_profit_factor":round(pf,5) if pf is not None else None,
            "diagnostic_status":status,
            "is_verified_broker_result":False,"may_authorize_live":False,
        })
    return {
        "kind":"PROSPECTIVE_SAMPLED_BID_ASK_VIRTUAL_MEMORY",
        "as_of_utc":as_of_utc.astimezone(timezone.utc).isoformat(),
        "minimum_complete":MIN_CASES,"minimum_distinct_days":MIN_DAYS,
        "minimum_distinct_months":MIN_MONTHS,"maximum_missing_fraction":MAX_MISSING,
        "fee_is_modeled_not_broker_reconciled":True,
        "cannot_authorize_real_execution":True,
        "cannot_convert_into_verified_ResolvedExperience":True,
        "groups":rows,
    }


def pause_due_to_losses(db,*,symbol,method,side,regime,at_utc):
    """Only a reversible, 24-hour virtual-research caution guard.

    Exactly five latest closed outcomes are already known before this
    decision, all negative and occurring in last 24h. No future data.
    """
    if at_utc.tzinfo is None:raise ValueError("aware clock required")
    now=at_utc.astimezone(timezone.utc).timestamp()
    rows=db.execute("""SELECT virtual_net_r FROM prospective_shadow
        WHERE symbol=? AND method=? AND side=? AND regime=?
        AND state='VIRTUAL_QUOTED' AND exit_at<=? AND exit_at>=?
        ORDER BY exit_at DESC,id DESC LIMIT 5""",
        (symbol,method,side,regime,now,now-24*3600)).fetchall()
    return len(rows)==5 and all(x[0] is not None and x[0]<0 for x in rows)
