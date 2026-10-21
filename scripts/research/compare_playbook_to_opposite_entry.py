"""Direction placebo: re-price same historical tick path in opposite side.

This is a paired direction baseline, not a trade recommendation. Both sides
use the same price-unit risk and reward distance (normalized to their own
executable bid/ask), and one adverse broker tick at entry and exit.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict,Counter
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from random import Random
from statistics import mean
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from replay_symbol_playbooks import simulate_structure,tick_series
UTC=timezone.utc
RISK_STRESS=1

def clock(t):
    dt=datetime.fromisoformat(t)
    if dt.tzinfo is None:raise ValueError("naive_time")
    return dt.timestamp()

def extract(paths):
    source=[];candidates=[]
    seen=set()
    for path in paths:
        raw=Path(path).read_bytes()
        obj=json.loads(raw)
        if obj.get("kind")!="distinct_per_symbol_research_playbooks_v1" or (
           obj.get("live_execution_enabled") is not False or
           obj.get("model_promotion_allowed") is not False):
            raise ValueError("untrusted_or_trading_enabled_archive")
        source.append(dict(path=str(path),sha256=sha256(raw).hexdigest()))
        for x in obj["trials"]:
            if x["slippage_each_side_ticks"]!=1:continue
            key=(x["symbol"],x["research_window"],x["quote_entry_utc"])
            if key in seen:raise ValueError("duplicated_source_entry")
            seen.add(key)
            candidates.append(x)
    return source,candidates

def paired_comparison(mt5,events):
    pairs=[]
    errors=Counter()
    for original in sorted(events,key=lambda e:(e["symbol"],e["quote_entry_utc"])):
        symbol=original["symbol"]
        if not mt5.symbol_select(symbol,True):
            errors["symbol_select_failed"]+=1;continue
        entry=dict(time=clock(original["quote_entry_utc"]),
            bid=original["broker_quote_entry_bid"],
            ask=original["broker_quote_entry_ask"])
        seq,err=tick_series(mt5,symbol,entry,original["max_hold_seconds"])
        if err:
            errors[err]+=1;continue
        if sha256(json.dumps(seq,separators=(",",":"),allow_nan=False).encode()).hexdigest()!=(
            original["historical_quote_sha256"]):
            errors["historical_tick_sequence_changed"]+=1;continue
        side=original["side"]
        true=simulate_structure(seq,side,original["stop_price"],
             original["target_price"],original["max_hold_seconds"],
             original["current_broker_tick_size"],RISK_STRESS)
        if true["status"]!="CLOSED" or original["status"]!="CLOSED":
            errors["original_outcome_not_closed"]+=1;continue
        if abs(true["R"]-original["R"])>1e-8:
            errors["original_replay_mismatch"]+=1;continue
        no_slip_entry=entry["ask"] if side=="BUY" else entry["bid"]
        risk=(no_slip_entry-original["stop_price"] if side=="BUY" else
              original["stop_price"]-no_slip_entry)
        reward=(original["target_price"]-no_slip_entry if side=="BUY" else
                no_slip_entry-original["target_price"])
        if risk<=0 or reward<=0:
            errors["invalid_original_risk_geometry"]+=1;continue
        reverse="SELL" if side=="BUY" else "BUY"
        reversed_base=entry["bid"] if reverse=="SELL" else entry["ask"]
        reverse_stop=reversed_base+risk if reverse=="SELL" else reversed_base-risk
        reverse_target=reversed_base-reward if reverse=="SELL" else reversed_base+reward
        control=simulate_structure(seq,reverse,reverse_stop,reverse_target,
                 original["max_hold_seconds"],original["current_broker_tick_size"],
                 RISK_STRESS)
        if control["status"]!="CLOSED":
            errors["mirror_"+control["status"]]+=1;continue
        pairs.append(dict(symbol=symbol,family=original["family"],
             period=original["research_window"],
             signal_close_utc=original["entry_signal_close_utc"],
             entry_quote_utc=original["quote_entry_utc"],
             original_side=side,mirror_side=reverse,
             original_R=true["R"],mirror_R=control["R"],
             delta_original_minus_mirror_R=true["R"]-control["R"],
             original_exit=true["exit_reason"],mirror_exit=control["exit_reason"],
             original_mfe_R=true["mfe_R"],original_mae_R=true["mae_R"],
             mirror_mfe_R=control["mfe_R"],mirror_mae_R=control["mae_R"],
             symmetric_price_distance_stop=risk,
             symmetric_price_distance_target=reward,
             historical_tick_sequence_verified=True,
             strategy_validated=False))
    return pairs,dict(errors)

def paired_mean_block_ci(items,iterations=600,seed=20261011):
    if not items:return None
    by_day=defaultdict(list)
    for x in items:
        by_day[x["signal_close_utc"][:10]].append(x["delta_original_minus_mirror_R"])
    rng=Random(seed)
    keys=sorted(by_day)
    vals=[]
    for _ in range(iterations):
        picked=[key for key in (rng.choice(keys) for __ in keys)]
        flat=[v for day in picked for v in by_day[day]]
        vals.append(mean(flat))
    vals.sort()
    return [vals[int(.025*(iterations-1))],vals[int(.975*(iterations-1))]]

def results(pairs):
    cohorts=[]
    for symbol in sorted({e["symbol"] for e in pairs}):
        sample=[e for e in pairs if e["symbol"]==symbol]
        differences=[e["delta_original_minus_mirror_R"] for e in sample]
        intervals=paired_mean_block_ci(sample)
        cohorts.append(dict(symbol=symbol,paired_count=len(sample),
           distinct_days=len({e["signal_close_utc"][:10] for e in sample}),
           average_original_R=mean(e["original_R"] for e in sample),
           average_opposite_R=mean(e["mirror_R"] for e in sample),
           average_R_lift=mean(differences),
           day_bootstrap_95pct_CI_R_lift=intervals,
           original_positive_fraction=sum(x["original_R"]>0 for x in sample)/len(sample),
           control_positive_fraction=sum(x["mirror_R"]>0 for x in sample)/len(sample),
           enough_independent_evidence=False,
           is_realized_profit=False))
    return cohorts

def main():
    import MetaTrader5 as mt5
    p=argparse.ArgumentParser()
    p.add_argument("--report",nargs="+",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--terminal",default=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe")
    a=p.parse_args()
    output=Path(a.output)
    if output.exists():raise FileExistsError("immutable_mirror_output_exists")
    manifest,signals=extract(a.report)
    if not mt5.initialize(a.terminal,timeout=20000):
        raise RuntimeError("research_terminal_not_connected")
    try:
        pairs,errors=paired_comparison(mt5,signals)
    finally:
        mt5.shutdown()
    doc=dict(kind="same_tick_opposite_direction_placebo_v1",
       input_evidence=manifest,original_signals=len(signals),
       completed_pairs=len(pairs),missing_or_changed=dict(errors),
       original_and_opposite_are_broker_bid_ask_stressed=True,
       exploratory_reused_history_not_future_holdout=True,
       within_symbol_family_only=True,
       is_random_baseline=False,
       baseline_definition="same UTC entry tick, mirror side, same absolute stop/target distance",
       slippage_adverse_ticks_each_side=RISK_STRESS,
       broker_fees_verified=False,live_execution_enabled=False,
       strategy_validated=False,model_promotion_allowed=False,
       groups=results(pairs),pairs=pairs)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(doc,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({k:doc[k] for k in (
        "original_signals","completed_pairs","missing_or_changed","groups")},indent=2))
    print("REPORT "+str(output))
if __name__=="__main__":
    main()
