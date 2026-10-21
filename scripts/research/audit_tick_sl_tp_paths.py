"""Independent arithmetic, timestamp and coverage audit of TP/SL tick replay."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import sys

SCRIPTS=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPTS))
from replay_historical_tick_stops import CONFIG,FEE_STRESS_BPS,summarize

def epoch(v):
    dt=datetime.fromisoformat(v)
    if dt.tzinfo is None:
        raise ValueError("naive_time")
    return dt.timestamp()

def same_num(a,b):
    return (a is None and b is None) or (a is not None and b is not None and
       abs(float(a)-float(b))<=1e-8*max(1,abs(float(a)),abs(float(b))))

def inspect(result):
    if result.get("report_version")!="historical_ohlc_verified_bidask_tick_path_v1":
        raise ValueError("wrong_report_version")
    for key in ("live_execution_enabled","model_promotion_allowed",
                "strategy_approved"):
        if result.get(key) is not False:
            raise ValueError("risk_permission_changed")
    if result.get("true_broker_commissions_unknown") is not True:
        raise ValueError("broker_fees_not_calibrated")
    samples=result["scenario_records"]
    if len(samples)!=result["total_scenario_rows"]:
        raise ValueError("scenario_count_mismatch")
    recorded={}
    for family,paths in result["input_evidence"].items():
        for item in paths:
            path=Path(item["input_path"])
            if not path.is_file():
                raise ValueError("missing_source_archive")
            if sha256(path.read_bytes()).hexdigest()!=item["sha256"]:
                raise ValueError("altered_input_archive")
    counts=Counter()
    configurations=defaultdict(set)
    for x in samples:
        family=x["family"]
        if family not in ("M1_M5","M5_M15"):
            raise ValueError("unknown_family")
        if x.get("trade_filled") is not False or x.get("model_promotion_allowed") is not False:
            raise ValueError("wrong_simulation_label")
        tp,sl,extra=x["tp_atr"],x["sl_atr"],x["extra_cost_bps"]
        if (tp,sl) not in CONFIG or extra not in FEE_STRESS_BPS:
            raise ValueError("unapproved_scenario_grid")
        if x["side"] not in ("BUY","SELL"):
            raise ValueError("bad_side")
        if not 0<=x["entry_spread_atr"]<=.5:
            raise ValueError("ineligible_spread_sample")
        entry=epoch(x["entry_time_utc"])
        if not 0<=entry-epoch(x["signal_bar_close_utc"])<=90.002:
            raise ValueError("future_signal_or_bad_entry")
        key=(family,x["symbol"],x["entry_time_utc"])
        scenario=(tp,sl,extra)
        if scenario in configurations[key]:
            raise ValueError("duplicate_scenario")
        configurations[key].add(scenario)
        counts[x["status"]]+=1
        if x["status"]!="CLOSED":
            if "stressed_r" in x or "profit_factor" in x:
                raise ValueError("unmeasured_profit_assumed")
            continue
        if x.get("atr_verified_from_sha256") is not True:
            raise ValueError("ATR_not_verified")
        if not re.fullmatch("[0-9a-f]{64}",x.get("tick_path_sha256","")):
            raise ValueError("missing_tick_path_fingerprint")
        if x.get("tick_events_available",0)<2:
            raise ValueError("missing_tick_path")
        exit_time=epoch(x["close_time_utc"])
        if not 0<=exit_time-entry<=1890.002:
            raise ValueError("exit_after_deadline")
        if abs(x["hold_seconds"]-(exit_time-entry))>.002:
            raise ValueError("wrong_hold_time")
        bid,ask,xbid,xask=(float(x[k]) for k in (
           "entry_bid","entry_ask","exit_observed_bid","exit_observed_ask"))
        atr=float(x["atr_signal"])
        origin=ask if x["side"]=="BUY" else bid
        px=xbid if x["side"]=="BUY" else xask
        filled=x["actual_exit_price_assumed"]
        tp_px=origin+(tp*atr if x["side"]=="BUY" else -tp*atr)
        sl_px=origin+(-sl*atr if x["side"]=="BUY" else sl*atr)
        if not all(isfinite(v) and v>0 for v in (
            bid,ask,xbid,xask,atr,filled,tp_px,sl_px)):
            raise ValueError("invalid_prices")
        if ask<bid or xask<xbid or not same_num(
                (ask-bid)/atr,x["entry_spread_atr"]):
            raise ValueError("invalid_spread")
        if not same_num(tp_px,x["hypothetical_tp_price"]) or not same_num(
              sl_px,x["hypothetical_sl_price"]):
            raise ValueError("wrong_stop_target")
        why=x["exit_reason"]
        if why=="TP":
            if exit_time>=entry+1800:
                raise ValueError("post_deadline_tp")
            if x["side"]=="BUY":
                if px<tp_px or not same_num(filled,tp_px):
                    raise ValueError("favorable_buy_fill_not_capped")
            else:
                if px>tp_px or not same_num(filled,tp_px):
                    raise ValueError("favorable_sell_fill_not_capped")
        elif why=="SL":
            if exit_time>=entry+1800:
                raise ValueError("post_deadline_sl")
            if x["side"]=="BUY":
                if px>sl_px or not same_num(filled,px):
                    raise ValueError("bad_buy_stop_gap")
            else:
                if px<sl_px or not same_num(filled,px):
                    raise ValueError("bad_sell_stop_gap")
        elif why=="TIME":
            if exit_time<entry+1800 or not same_num(filled,px):
                raise ValueError("bad_time_exit")
        else:
            raise ValueError("unknown_exit_type")
        delta=filled-origin if x["side"]=="BUY" else origin-filled
        mid=(bid+ask)/2
        bp=delta/mid*10000
        expected_r=delta/(sl*atr)-extra*mid/(10000*sl*atr)
        if not all((same_num(bp,x["quoted_bps"]),
                    same_num(bp-extra,x["stressed_bps"]),
                    same_num(expected_r,x["stressed_r"]))):
            raise ValueError("replay_math_mismatch")
    expected_count=len(CONFIG)*len(FEE_STRESS_BPS)
    if any(len(value)!=expected_count for value in configurations.values()):
        raise ValueError("incomplete_scenario_grid")
    for aggregate in result["groups"]:
        cohort=[x for x in samples if x["family"]==aggregate["family"]
                and x["side"]==aggregate["side"]
                and x["entry_spread_atr"]<=aggregate["spread_atr_limit"]
                and x["tp_atr"]==aggregate["tp_atr"]
                and x["sl_atr"]==aggregate["sl_atr"]
                and x["extra_cost_bps"]==aggregate["extra_bps"]]
        expected=summarize(cohort)
        if (len(cohort)!=aggregate["n_candidates"] or
                expected["n_closed"]!=aggregate["n_closed"] or
                expected["missing"]!=aggregate["missing"]):
            raise ValueError("summary_coverage_mismatch")
        for metric in ("expectancy_r","profit_factor","win_fraction"):
            if not same_num(expected[metric],aggregate[metric]):
                raise ValueError("summary_math_mismatch")
        # Legacy empty summary groups omit an explicit promotion flag;
        # absence is not permission. Explicit true is always forbidden.
        if aggregate.get("model_promotion_allowed",False) is not False:
            raise ValueError("aggregation_cannot_promote")
    return dict(kind="replayed_bidask_tp_sl_integrity_audit",
        scenario_rows=len(samples),unique_quote_entry_candidates=len(configurations),
        status_count=dict(counts),aggregate_rows_checked=len(result["groups"]),
        source_files_verified=sum(len(v) for v in result["input_evidence"].values()),
        quote_path_hashes_present=True,
        historical_sl_tp_are_simulations_not_real_broker_fills=True,
        strategy_approved=False,live_execution_enabled=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    path=Path(a.output)
    if path.exists():raise FileExistsError("audit_output_exists")
    input_bytes=Path(a.report).read_bytes()
    result=inspect(json.loads(input_bytes))
    result["report_sha256"]=sha256(input_bytes).hexdigest()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
