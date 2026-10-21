"""Aggregate every forensic outcome across 17 MT5 symbols and two windows.

NO cherry-picking profitable trades. Four disjoint 3-5-symbol private
batch reports per month must cover all 17 symbols. Reuse one audited
failure statistic implementation from closed_bar_failure_forensics.
No broker connections, trade gateway, parameter optimization, or
automated promotion to paper/live policies.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from datetime import datetime,timezone
import argparse
import json
from pathlib import Path

from katarina.intelligence.lab.closed_bar_failure_forensics import _summarize


def aggregate(september,october):
    if len(september)!=4 or len(october)!=4:
        raise ValueError("four_disjoint_batches_each_period_required")
    all_cases=[]
    groups=defaultdict(list)
    symbols=defaultdict(list)
    periods=[]
    totals=Counter()
    signal_ids=set()
    for month,batches in (("2026-09",september),("2026-10",october)):
        owned=set()
        cases=[]
        counts=Counter()
        for report in batches:
            if (report.get("read_only") is not True or
                report.get("orders_sent") != 0 or
                report.get("live_execution_authorized") is not False or
                report.get("spread_source")!="BROKER_M5_CLOSED_BAR_SPREAD_POINTS" or
                report.get("actual_historical_entry_bidask_verified") is not False):
                raise ValueError("unverifiable_or_not_research_only_provenance")
            local=report["symbols_requested"]
            if len(local)!=len(set(local)) or owned.intersection(local):
                raise ValueError("duplicate_symbol_same_calendar_period")
            owned.update(local)
            stats=report["entry_failure_diagnostics"]
            rows=stats["all_candidate_records"]
            if len(rows)!=stats["totals"]["n"] or len(rows)!=report["counters"]["proxy_completed"]:
                raise ValueError("missing_broker_replay_failure_outcomes")
            if (stats.get("live_execution_authorized") is not False or
                stats.get("orders_sent")!=0):
                raise ValueError("invalid_root_cause_source")
            for x in rows:
                if x["symbol"] not in local or x["signal_month"]!=month:
                    raise ValueError("wrong_historical_symbol_or_month")
                sid=(month,x["symbol"],x["signal_epoch"])
                if sid in signal_ids:
                    raise ValueError("duplicate_historical_market_entry")
                signal_ids.add(sid)
                cases.append(x)
                groups[(x["method"],x["side"])].append(x)
                symbols[x["symbol"]].append(x)
            for key in ("evaluated","technical_wait","invalid_rr_or_stop",
                        "quote_path_unavailable","spread_unavailable"):
                counts[key]+=report["counters"].get(key,0)
            counts["adaptively_selected_independent_batch"]+=(
                report.get("adapted_replay",{}).get("adaptive",{}).get("trades",0) or 0)
            counts["prelabel_technical_proposals"]+=len(
                rows)+report["counters"].get("quote_path_unavailable",0)
        if len(owned)!=17:
            raise ValueError("expected_complete_17_MT5_broker_symbols")
        periods.append({"month":month,"instrument_count":len(owned),
                        "counters":dict(counts),**_summarize(cases)})
        totals.update(counts)
        all_cases+=cases
    cohort=[]
    for (method,side),rows in sorted(groups.items()):
        a=[x for x in rows if x["signal_month"]=="2026-09"]
        b=[x for x in rows if x["signal_month"]=="2026-10"]
        left=_summarize(a);right=_summarize(b)
        cohort.append({
            "method":method,"side":side,
            "both_inspected_windows_negative":bool(
                a and b and left["mean_net_proxy_r"]<0
                and right["mean_net_proxy_r"]<0),
            "september":left,"october":right,
            "both":_summarize(rows),
            "live_edge_or_alpha_validated":False,
        })
    return {
        "status":"EX_POST_TWO_WINDOW_ROOT_CAUSE_DIAGNOSTICS_COMPLETE",
        "months":periods,"counters":dict(totals),
        "all":_summarize(all_cases),
        "methods":cohort,
        "instruments":[{"symbol":sym,**_summarize(rows)}
                       for sym,rows in sorted(symbols.items())],
        "number_of_negative_method_side_groups_in_both_windows":sum(
            x["both_inspected_windows_negative"] for x in cohort),
        "spread_risk_ratio_from_assumed_NEXT_open_bidask":True,
        "historical_trade_costs_0_15R_are_ASSUMED":True,
        "M5_OHLC_intrabar_price_order_is_unknown":True,
        "data_are_retrospective_NOT_fresh_independent_OOS":True,
        "profit_claims_and_live_promotion_forbidden":True,
        "orders_sent":0,"live_execution_authorized":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--september",nargs=4,required=True)
    p.add_argument("--october",nargs=4,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    def load(xs):
        return [json.loads(Path(x).read_text(encoding="utf-8")) for x in xs]
    r=aggregate(load(a.september),load(a.october))
    r["audited_utc"]=datetime.now(timezone.utc).isoformat()
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(r,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
                   encoding="utf-8")
    tmp.replace(dest)
    print("KATARINA_FAILURE_DIAGNOSIS",json.dumps({
        "evaluated":r["counters"]["evaluated"],
        "candidates":r["all"]["n"],
        "stop":r["all"]["exit_causes"].get("STOP",0),
        "target":r["all"]["exit_causes"].get("TARGET",0),
        "time":r["all"]["exit_causes"].get("TIME",0),
        "first_15m_stop":r["all"]["early_stop_within_15m_count"],
        "median_spread_to_risk":r["all"]["median_pre_entry_spread_to_risk"],
        "negative_in_both_windows":r["number_of_negative_method_side_groups_in_both_windows"],
        "orders_sent":0,"live":False
    },ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
