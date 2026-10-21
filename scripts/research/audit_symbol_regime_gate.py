"""Recompute fixed symbol-specific gates and summarize without profit cherry-picks."""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from compare_regime_gate_to_raw_setups import CONTRACT,gate,metric,MAX_AGE_SECONDS

def stamp(iso):
    x=datetime.fromisoformat(iso)
    if x.tzinfo is None:raise ValueError("missing_timestamp_timezone")
    return x.timestamp()

def audit(doc):
    if doc.get("kind")!="market_regime_predeclared_gate_trade_diagnostic_v1":
        raise ValueError("incorrect_gate_report")
    if doc.get("decision")!="NO_TRADE" or (
         doc.get("model_promotion_allowed") is not False or
         doc.get("live_execution_enabled") is not False):
        raise ValueError("gate_attempts_live_promotion")
    if doc.get("strategy_specific_gate")!=CONTRACT:
        raise ValueError("unregistered_gate_parameters")
    seen=set()
    buckets=defaultdict(list)
    symbols=defaultdict(list)
    for e in doc["matched_trials"]:
        sym=e["symbol"]
        if sym not in CONTRACT or e["family"]!=CONTRACT[sym]["family"]:
            raise ValueError("family_leak_from_other_symbol")
        if e.get("no_real_trade_executed") is not True or e["slippage_each_side_ticks"]!=1:
            raise ValueError("missing_broker_cost_scenario")
        clock=stamp(e["entry_signal_close_utc"])
        k=(sym,e["period"],clock)
        if k in seen:raise ValueError("duplicate_regime_entry")
        seen.add(k)
        state=e["regime_state"]
        prior=e["regime_observation_utc"]
        if state=="UNAVAILABLE":
            if prior is not None or e["regime_clock_age_seconds"] is not None:
                raise ValueError("missing_regime_with_fake_time")
            expected=False
        else:
            if prior is None:raise ValueError("unproven_prior_regime_time")
            age=clock-stamp(prior)
            if not 0<=age<=MAX_AGE_SECONDS+1e-7:
                raise ValueError("future_or_stale_market_regime")
            if abs(age-e["regime_clock_age_seconds"])>.01:
                raise ValueError("observation_age_mismatch")
            expected=state!="UNKNOWN" and gate(sym,e["side"],state)
        if expected!=e["gate_pass"]:
            raise ValueError("gate_not_predeclared")
        buckets[(sym,e["period"])].append(e)
        symbols[sym].append(e)
    if len(seen)!=doc.get("all_trades_scenarios"):
        raise ValueError("wrong_trade_count")
    indexed={(r["symbol"],r["period"]):r for r in doc["per_symbol_period"]}
    if len(indexed)!=len(doc["per_symbol_period"]) or set(indexed)!=set(buckets):
        raise ValueError("incomplete_period_metrics")
    for key,group in buckets.items():
        x=indexed[key]
        selected=[e for e in group if e["gate_pass"]]
        for field,values in (("original_all",group),("regime_gated",selected)):
            expected=metric(values);actual=x[field]
            for attr in ("n","mean_R","profit_factor","distinct_dates","percent_R_positive"):
                left,right=actual[attr],expected[attr]
                if left is None and right is None:continue
                if left is None or right is None or abs(left-right)>1e-9:
                    raise ValueError("gated_metric_recalculation_failed")
        if x.get("model_promotion_allowed") is not False:
            raise ValueError("period_promoted_without_validation")
    return dict(kind="broker_regime_gate_research_audit",
        rows_verified=len(seen),markets_verified=len(symbols),
        period_groups_verified=len(buckets),
        future_timestamp_leakage_checked=True,
        fixed_gate_rule_recomputed=True,
        broker_exit_marks_are_not_cash_deals=True,
        no_trading_promotion=True,
        model_promotion_allowed=False,live_execution_enabled=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    source=Path(a.report).read_bytes()
    doc=json.loads(source)
    result=audit(doc)
    result["source_report_sha256"]=sha256(source).hexdigest()
    target=Path(a.output)
    if target.exists():raise FileExistsError("immutable_audit_exists")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
