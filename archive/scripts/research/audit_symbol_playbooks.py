"""Audit each unique broker-symbol playbook and every quoted exit calculation."""
from __future__ import annotations
import argparse,json,re
from collections import defaultdict
from datetime import datetime,timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from statistics import mean
import sys
from katarina.intelligence.symbol_playbooks import SYMBOLS
from katarina.intelligence.alternative_symbol_playbooks import SYMBOLS as ALT_SYMBOLS
from replay_symbol_playbooks import STRESSES,group_report

def seconds(value):
    dt=datetime.fromisoformat(value)
    if dt.tzinfo is None:raise ValueError("naive_clock")
    return dt.timestamp()

def audit(doc):
    if doc.get("kind")!="distinct_per_symbol_research_playbooks_v1" or (
        doc.get("live_execution_enabled") is not False or
        doc.get("model_promotion_allowed") is not False):
        raise ValueError("wrong_research_only_report")
    symbols=doc["symbol_strategies"]
    registry=(ALT_SYMBOLS if doc.get("research_playbook_arm")=="alternatives"
              else SYMBOLS)
    if any(registry.get(s)!=name for s,name in symbols.items()):
        raise ValueError("symbol_strategy_contamination")
    groups=defaultdict(dict)
    seen_window=set()
    for x in doc["trials"]:
        sym=x["symbol"]
        if x.get("can_trade_live") is not False or x.get("production_orders_enabled") is not False:
            raise ValueError("live_risk_not_disabled")
        if sym not in symbols or x["family"]!=symbols[sym]:
            raise ValueError("wrong_playbook_for_broker_symbol")
        if x["slippage_each_side_ticks"] not in STRESSES:
            raise ValueError("invalid_slippage_stress")
        close=seconds(x["entry_signal_close_utc"])
        entry=seconds(x["quote_entry_utc"])
        if not .245<=entry-close<=30.255:
            raise ValueError("entry_not_after_closed_signal")
        s=x["slippage_each_side_ticks"];bid=x["broker_quote_entry_bid"]
        ask=x["broker_quote_entry_ask"];stop=x["stop_price"];target=x["target_price"]
        risk=ask-stop if x["side"]=="BUY" else stop-bid
        reward=target-ask if x["side"]=="BUY" else bid-target
        if risk<=x["current_broker_stop_minimum"]+x["current_broker_tick_size"]*4 or (
            reward<=0):
            raise ValueError("invalid_stop_target_broker")
        if not all(isfinite(v) and v>0 for v in (
            bid,ask,stop,target,x["signal_atr"],x["current_broker_tick_size"])):
            raise ValueError("non_finite_symbol_quote")
        if not (bid<=ask and abs((ask-bid)/x["signal_atr"]-
            x["entry_spread_div_atr"])<1e-7 and abs(
            (ask-bid)/reward-x["spread_target_fraction"])<1e-7):
            raise ValueError("spread_or_reward_arithmetic")
        key=(sym,x["research_window"],x["quote_entry_utc"])
        if s in groups[key]:raise ValueError("duplicate_stress_on_same_entry")
        groups[key][s]=x
        if x.get("historical_tick_count",0)<1 or not re.fullmatch(
            "[0-9a-f]{64}",x.get("historical_quote_sha256","")):
            raise ValueError("missing_source_tick_evidence")
        if x["status"]=="CLOSED":
            time=seconds(x["close_time_utc"])
            if not 0<=time-entry<=x["max_hold_seconds"]+90.01:
                raise ValueError("exit_missing_or_late")
            if x["exit_reason"] not in ("TP","SL","TIME"):
                raise ValueError("invalid_exit_cause")
            base=(ask+s*x["current_broker_tick_size"] if x["side"]=="BUY"
                  else bid-s*x["current_broker_tick_size"])
            if abs(x["entry_hypothetical_price"]-base)>1e-7:
                raise ValueError("slippage_entry_math")
            rr=base-stop if x["side"]=="BUY" else stop-base
            delta=(x["exit_hypothetical_price"]-base if x["side"]=="BUY"
                   else base-x["exit_hypothetical_price"])
            if not (isfinite(x["R"]) and rr>0 and
                    abs(x["R"]-delta/rr)<1e-7):
                raise ValueError("incorrect_position_return")
            if x["mfe_R"]<0 or x["mae_R"]>0:
                raise ValueError("invalid_path_excursion")
        else:
            if "R" in x or "exit_reason" in x:
                raise ValueError("fabricated_missing_trade_result")
    for key,slips in groups.items():
        if set(slips)!=set(STRESSES):
            raise ValueError("incomplete_slippage_grid")
        for slp,x in slips.items():
            if x["status"]!="CLOSED":continue
            if x["exit_reason"]=="TP" and seconds(x["close_time_utc"])>=(
                 seconds(x["quote_entry_utc"])+x["max_hold_seconds"]):
                raise ValueError("TP_after_mandatory_time_exit")
    expected=group_report(doc["trials"],registry)
    lookup=lambda arr:{(g["symbol"],g["phase"],g["slippage_ticks_each_side"]):g
                       for g in arr}
    actual=lookup(doc["groups"])
    want=lookup(expected)
    if set(actual)!=set(want):
        raise ValueError("group_keys_not_equal")
    for key,row in want.items():
        one=actual[key]
        for col in ("entries","complete","exits","missing","UTC_days","family"):
            if row[col]!=one[col]:raise ValueError("group_mismatch_"+col)
        for col in ("mean_R","profit_factor","avg_MFE_R","avg_MAE_R","success_rate"):
            a,b=row[col],one[col]
            if a is None and b is None:continue
            if a is None or b is None or abs(a-b)>1e-7:
                raise ValueError("group_arithmetic_mismatch_"+col)
    return dict(kind="symbol_specific_tick_path_integrity_audit",
        unique_entry_paths=len(groups),scenario_rows=len(doc["trials"]),
        separately_registered_playbooks=len(set(symbols.values())),
        groups_checked=len(expected),
        completed=sum(x["status"]=="CLOSED" for x in doc["trials"]),
        no_cross_symbol_model_reuse=True,no_real_order_permissions=True,
        live_execution_enabled=False,model_promotion_allowed=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    source=Path(args.report).read_bytes()
    answer=audit(json.loads(source))
    answer["source_sha256"]=sha256(source).hexdigest()
    path=Path(args.output)
    if path.exists():raise FileExistsError("immutable_integrity_report")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(answer,indent=2)+"\n")
    print(json.dumps(answer,indent=2))
if __name__=="__main__":
    main()
