"""Audit broker-aware research outputs independently of its cached summaries."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from benchmark_broker_scalp_setups import (
    FAMILIES,PERIODS,EXITS,ADVERSE_TICK_PER_SIDE,make_summary)

def epoch(s):
    d=datetime.fromisoformat(s)
    if d.tzinfo is None:raise ValueError("naive_timestamp")
    return d.timestamp()

def check(doc):
    if doc.get("report_version")!="broker_aware_independent_strategy_tick_study_v1":
        raise ValueError("wrong_report_kind")
    if doc.get("live_execution_enabled") is not False or (
       doc.get("model_promotion_allowed") is not False):
        raise ValueError("unauthorized_trading_status")
    events=doc["trials"]
    if doc.get("result_count")!=len(events):
        raise ValueError("wrong_report_count")
    records=defaultdict(dict)
    checked=defaultdict(list)
    for e in events:
        if e.get("trade_filled") is not False or e.get("strategy_live_authorized") is not False:
            raise ValueError("false_trade_claim")
        if e["family"] not in FAMILIES or e["phase"] not in [r[0] for r in PERIODS]:
            raise ValueError("unknown_rule")
        if e["side"] not in ("BUY","SELL"):
            raise ValueError("unknown_side")
        scenario=(e["tp_atr"],e["sl_atr"],e["adverse_slippage_each_side_ticks"])
        if (e["tp_atr"],e["sl_atr"]) not in EXITS or scenario[2] not in ADVERSE_TICK_PER_SIDE:
            raise ValueError("invalid_grid")
        k=(e["phase"],e["symbol"],e["family"],e["side"],e["entry_time_utc"])
        if scenario in records[k]:
            raise ValueError("duplicate_entry_scenario")
        records[k][scenario]=e
        close=epoch(e["signal_close_utc"])
        entry=epoch(e["entry_time_utc"])
        if not .249<=entry-close<=30.251:
            raise ValueError("entry_timing")
        atr=e["signal_atr"]
        tick=e["current_tick_size"]
        spread=e["entry_ask"]-e["entry_bid"]
        if not all(isfinite(float(x)) for x in (
          atr,tick,e["entry_bid"],e["entry_ask"],e["entry_spread_div_atr"]
        )) or atr<=0 or tick<=0 or spread<0 or abs(spread/atr-e["entry_spread_div_atr"])>1e-7:
            raise ValueError("invalid_symbol_price")
        if e["sl_atr"]*atr<=e["broker_min_stop_price"]+tick:
            raise ValueError("broker_stop_distance_not_verified")
        if not 0<=e["entry_spread_div_atr"]<=.5:
            raise ValueError("candidate_spread_over_limit")
        if not isinstance(e["tick_path_sha256"],str) or len(e["tick_path_sha256"])!=64:
            raise ValueError("missing_historical_ticks_hash")
        if e["status"]=="CLOSED":
            if not isfinite(e["R"]):
                raise ValueError("invalid_R")
            t=epoch(e["exit_time_utc"])
            if not 0<=t-entry<=1890:
                raise ValueError("invalid_exit_time")
            if e["exit_reason"] not in ("TP","SL","TIME"):
                raise ValueError("invalid_exit_reason")
            opened=(e["entry_ask"]+tick*scenario[2] if e["side"]=="BUY"
                   else e["entry_bid"]-tick*scenario[2])
            delta=e["exit_assumed_price"]-opened
            if e["side"]=="SELL":delta=-delta
            derived=delta/(e["sl_atr"]*atr)
            if abs(derived-e["R"])>1e-6:
                raise ValueError("risk_ratio_wrong")
            if e["currency_profit"]=="USD" and e["usd_minlot"] is not None:
                usd_calc=delta*e["current_broker_contract_size"]*e["current_min_lot"]
                if abs(usd_calc-e["usd_minlot"])>max(.03,abs(usd_calc)*.01):
                    raise ValueError("USD_contract_profit_disagrees")
        else:
            if e["R"] is not None or e["usd_minlot"] is not None:
                raise ValueError("missing_outcome_invented")
        cohort=(e["phase"],e["symbol"],e["family"],e["side"],
                e["tp_atr"],e["sl_atr"],scenario[2])
        checked[cohort].append(e)
    for key,scenarios in records.items():
        if len(scenarios)!=len(EXITS)*len(ADVERSE_TICK_PER_SIDE):
            raise ValueError("missing_scenario")
    original={}
    for s in doc["summaries"]:
        k=(s["phase"],s["symbol"],s["family"],s["side"],s["tp_atr"],
           s["sl_atr"],s["adverse_slippage_each_side_ticks"])
        if k in original:raise ValueError("duplicate_summary")
        original[k]=s
        expected=make_summary(checked[k])
        for x in ("candidates","closed","missing"):
            if s[x]!=expected[x]:
                raise ValueError("summary_mismatch_"+x)
        for x in ("mean_r","profit_factor","win_fraction",
                  "largest_peak_to_trough_r","sum_nominal_minlot_usd"):
            a,b=s[x],expected[x]
            if a is None and b is None:continue
            if a is None or b is None or abs(a-b)>1e-7*max(1,abs(a),abs(b)):
                raise ValueError("summary_mismatch_"+x)
    return dict(kind="broker_aware_scalp_output_audit",
        price_math_verified=True,current_contract_minlot_checked=True,
        no_real_orders=True,live_execution_enabled=False,
        scenario_rows=len(events),distinct_simulated_entries=len(records),
        completed_scenario_rows=sum(e["status"]=="CLOSED" for e in events),
        cohorts_checked=len(doc["summaries"]),
        phase_entry_counts={p:sum(k[0]==p for k in records)
                           for p,_,_ in PERIODS})
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",required=True)
    parser.add_argument("--output",required=True)
    a=parser.parse_args()
    raw=Path(a.report).read_bytes()
    summary=check(json.loads(raw))
    summary["source_sha256"]=sha256(raw).hexdigest()
    out=Path(a.output)
    if out.exists():raise FileExistsError("immutable_audit_exists")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":
    main()
