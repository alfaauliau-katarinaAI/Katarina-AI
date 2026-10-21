"""Aggregate four bounded precommitted Aug-2026 broker research batches.

All fixed-rule proposals and all failed tick paths contribute to the
denominators. Quote results are a NON-RANDOM small subset; cannot
validate profit of every proxy label or brokerage cost.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean
import argparse,json

from katarina.intelligence.lab.precommitted_setup_research import (
    FROZEN_RULE_VERSION,_metrics,
)


def aggregate(batches):
    if len(batches)!=4:raise ValueError("four_bounded_batches_required")
    symbols=set()
    technical=[]
    outcomes=[]
    ticks=[]
    counts=Counter()
    seen=set()
    coverage={}
    for batch in batches:
        if (batch.get("read_only") is not True or
            batch.get("live_execution_authorized") is not False or
            batch.get("orders_sent")!=0 or
            batch.get("frozen_rule_version")!=FROZEN_RULE_VERSION or
            batch.get("actual_account_commission_schedule_verified") is not False or
            batch.get("real_entry_bidask_verified") is not False):
            raise ValueError("input_not_read_only_frozen_research")
        names=batch["broker_symbols"]
        if not names or len(set(names))!=len(names) or symbols.intersection(names):
            raise ValueError("duplicate_or_missing_broker_symbols")
        symbols.update(names)
        coverage.update(batch["broker_data_coverage"])
        for k,v in batch["counters"].items():
            if isinstance(v,int):counts[k]+=v
        for signal in batch["all_proposals_frozen_before_future_outcome"]:
            key=(signal["symbol"],signal["method"],
                 signal["side"],signal["signal_epoch"])
            if key in seen:raise ValueError("duplicate_precommitted_signal")
            seen.add(key)
            technical.append(signal)
        outcomes.extend(batch["all_proxy_outcomes"])
        ticks.extend(batch["tick_audit_records"])
    if len(symbols)!=17:
        raise ValueError("expected_17_canonical_broker_markets")
    if len(technical)!=sum(
            b["technical_proposals"] for b in batches):
        raise ValueError("missing_technical_proposals")
    if len(outcomes)!=sum(
            b["simulated_outcomes"] for b in batches):
        raise ValueError("missing_simulated_outcomes")
    if len(technical)!=len(outcomes)+counts["censored_future_or_entry_geometry"]:
        raise ValueError("candidate_label_denominator_mismatch")
    outcomes_by_key={
        (v["symbol"],v["method"],v["side"],v["signal_epoch"]):v
        for v in outcomes
    }
    if len(outcomes_by_key)!=len(outcomes):
        raise ValueError("duplicated_outcome_identity")
    t_status=Counter()
    validated=[]
    paired=[]
    for item in ticks:
        signal=item["signal"];o=item["outcome"]
        key=(signal["symbol"],signal["method"],
             signal["side"],signal["signal_at"])
        if key not in seen:
            raise ValueError("sample_not_from_precommitted_candidates")
        t_status[o["status"]]+=1
        if o["status"]=="CLOSED_QUOTE_SIMULATION_ONLY":
            if o.get("broker_fills_verified") is not False or o.get(
                    "real_commission_verified") is not False:
                raise ValueError("invalid_quote_simulation_provenance")
            validated.append(o["net_assumed_cost_r"])
            earlier=outcomes_by_key.get(key)
            paired.append({
                "symbol":signal["symbol"],"method":signal["method"],
                "side":signal["side"],"signal_epoch":signal["signal_at"],
                "tick_net_assumed_r":o["net_assumed_cost_r"],
                "ohlc_net_assumed_r":(earlier["gross_proxy_r"]-.15)
                                      if earlier else None,
                "tick_exit_reason":o["exit_reason"],
                "ohlc_exit_reason":earlier["exit_reason"] if earlier else None,
                "tick_quote_no_broker_fill_proof":True,
            })
    def score(key,condition):
        rows=[v for v in outcomes if condition(v)]
        return {"label":key,
                "at_plus_0_15_r":_metrics(rows,.15),
                "at_plus_0_30_r":_metrics(rows,.30)}
    methods=[]
    for name in ("RANGE_SWEEP_RECLAIM","TREND_PULLBACK_RESUME",
                 "BREAKOUT_RETEST_LEVEL"):
        for side in ("BUY","SELL"):
            methods.append(score(name+":"+side,
                    lambda v,n=name,s=side:v["method"]==n and v["side"]==s))
    tick_pos=sum(max(v,0) for v in validated)
    tick_neg=-sum(min(v,0) for v in validated)
    return {
        "status":"FROZEN_AUG_2026_READ_ONLY_RESEARCH_COMBINED",
        "frozen_version":FROZEN_RULE_VERSION,
        "window":"AUG10_TO_AUG21_PAST_ONLY_NOT_PREVIOUS_SEPT_OCT_REPLAY",
        "symbols":sorted(symbols),
        "broker_source_coverage":coverage,
        "counters":dict(counts),
        "pre_outcome_proposals":len(technical),
        "OHLC_completed_outcomes":len(outcomes),
        "OHLC_censored":counts["censored_future_or_entry_geometry"],
        "all_proxy_0_15":_metrics(outcomes,.15),
        "all_proxy_0_30":_metrics(outcomes,.30),
        "methods_and_sides":methods,
        "tick_audit_count":len(ticks),
        "tick_statuses":dict(t_status),
        "tick_quote_complete":len(validated),
        "tick_quote_mean_assumed_r":round(mean(validated),6) if validated else None,
        "tick_quote_profit_factor_assumed":(
            round(tick_pos/tick_neg,6) if tick_neg>0 else None),
        "tick_sample_is_not_representative_of_all_historical_entries":True,
        "tick_paired_sample_with_ohlc":paired,
        "precommitted_rules_commercially_viable_verified":False,
        "tick_reconciliation_is_not_real_broker_fill_history":True,
        "historical_broker_DTS_year_round_validated":False,
        "actual_commission_swaps_slippage_verified":False,
        "independent_forward_profit_claimed":False,
        "no_portfolio_equity_drawdown_claim_from_overlapping_methods":True,
        "action":"WAIT","orders_sent":0,"live_execution_authorized":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--inputs",nargs=4,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    inputs=[json.loads(Path(name).read_text(encoding="utf-8"))
            for name in a.inputs]
    result=aggregate(inputs)
    result["aggregated_utc"]=datetime.now(timezone.utc).isoformat()
    dst=Path(a.output)
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
                   encoding="utf-8")
    tmp.replace(dst)
    print("PRECOMMITTED_AUG_RESEARCH_COMBINED",json.dumps({
        "symbols":len(result["symbols"]),
        "market_clocks":result["counters"]["market_clocks"],
        "proposals":result["pre_outcome_proposals"],
        "proxy_labels":result["OHLC_completed_outcomes"],
        "censored":result["OHLC_censored"],
        "mean_r_0_15":result["all_proxy_0_15"]["mean_net_assumed_r"],
        "tick_completed":result["tick_quote_complete"],
        "tick_checked":result["tick_audit_count"],
        "tick_mean_r":result["tick_quote_mean_assumed_r"],
        "by_method_side":[{"name":r["label"],
            "n":r["at_plus_0_15_r"]["n"],
            "mean":r["at_plus_0_15_r"]["mean_net_assumed_r"]}
            for r in result["methods_and_sides"]],
        "live":False,"orders":0
    },allow_nan=False),flush=True)


if __name__=="__main__":
    main()
