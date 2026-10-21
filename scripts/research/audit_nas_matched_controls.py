"""Independent audit of time/volatility/spread matched NAS placebo.

This test does not claim causal/randomized trial; validates fixed matching
contract only and the source archive hashes. No execution permissions.
"""
from __future__ import annotations
import argparse,json
from datetime import datetime
from hashlib import sha256
from math import isfinite
from pathlib import Path
from statistics import mean
import re
from nas_matched_controls import (ATR_TOLERANCE,COST_RATIO_TOLERANCE,
    DISTANCE_LIMIT,MIN_SEPARATION,CONTROLS_PER_ANCHOR,SEED,bootstrap_pair)
def audit(doc):
    if doc.get("kind")!="NAS100_matched_timestamp_random_control_v1":
        raise ValueError("invalid_study_version")
    if doc.get("live_execution_enabled") is not False or (
        doc.get("model_promotion_allowed") is not False) or doc["trade_decision"]!="NO_TRADE":
        raise ValueError("study_attempted_promotion")
    if doc["fixed_seed"]!=SEED:
        raise ValueError("seed_changed")
    original={}
    for item in doc["evidence_sources"]:
        path=Path(item["path"])
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=item["sha256"]:
            raise ValueError("original_source_changed")
        archive=json.loads(raw)
        for e in archive["trials"]:
            if e["symbol"]!="NAS100.vx" or e["slippage_each_side_ticks"]!=1:
                continue
            k=e["entry_signal_close_utc"]
            if k in original:
                raise ValueError("overlapping_original_signal")
            original[k]=e
    if doc["matched_entries"]!=len(doc["matched_pairs"]) or (
        doc["matched_entries"]>len(original)):
        raise ValueError("matched_entry_count_inconsistent")
    allcontrols=0
    for pair in doc["matched_pairs"]:
        signal=pair["signal_utc"]
        if signal not in original:
            raise ValueError("matched_unknown_signal")
        e=original[signal]
        if pair["phase"]!=e["research_window"] or pair["side"]!=e["side"]:
            raise ValueError("wrong_original_side_or_window")
        if abs(pair["original_R"]-e["R"])>1e-9:
            raise ValueError("original_trade_result_mismatch")
        controls=pair["controls"]
        if not 1<=len(controls)<=CONTROLS_PER_ANCHOR or len(controls)!=pair["controls_succeeded"]:
            raise ValueError("control_count_wrong")
        vals=[]
        times=set()
        for c in controls:
            stamp=datetime.fromisoformat(c["control_signal_utc"]).timestamp()
            prior=datetime.fromisoformat(signal).timestamp()
            diff=abs(stamp-prior)
            if not MIN_SEPARATION<=diff<=DISTANCE_LIMIT:
                raise ValueError("unmatched_session_clock")
            if c["control_signal_utc"][:10]!=signal[:10]:
                raise ValueError("different_UTC_date")
            if not abs(c["control_atr"]/e["signal_atr"]-1)<=ATR_TOLERANCE+1e-7:
                raise ValueError("control_ATR_out_of_tolerance")
            if abs(c["control_spread_ratio"]-e["entry_spread_div_atr"])>COST_RATIO_TOLERANCE+1e-7:
                raise ValueError("control_spread_not_matched")
            if not re.fullmatch("[0-9a-f]{64}",c["quote_sha256"]):
                raise ValueError("missing_broker_tick_sha256")
            if c["slippage_ticks_each_side"]!=1 or not isfinite(c["control_R"]):
                raise ValueError("bad_control_return")
            if stamp in times:raise ValueError("reused_matched_time_for_anchor")
            times.add(stamp)
            vals.append(c["control_R"])
        if abs(mean(vals)-pair["average_control_R"])>1e-9 or (
            abs(pair["original_R"]-mean(vals)-pair["lift_R"])>1e-9):
            raise ValueError("corrupt_paired_lift")
        allcontrols+=len(vals)
    if allcontrols!=doc["matched_control_positions"]:
        raise ValueError("total_control_count_wrong")
    if doc["matched_entries"]>0:
        for metric,key in (("average_original_R","original_R"),
                           ("average_control_R","average_control_R"),
                           ("matched_average_R_lift","lift_R")):
            if abs(mean(x[key] for x in doc["matched_pairs"])-doc[metric])>1e-9:
                raise ValueError("mean_math_mismatch_"+metric)
        if doc["day_block_bootstrap_95pct_lift"]!=bootstrap_pair(doc["matched_pairs"]):
            raise ValueError("confidence_interval_changed")
    return dict(kind="NAS100_matched_control_integrity_audit",
        source_files_sha_verified=len(doc["evidence_sources"]),
        matched_entries=doc["matched_entries"],
        matched_control_positions=allcontrols,
        matching_conditions_verified=True,
        covariance_control_not_independent_OOS=True,
        absolute_expectancy_validated=False,
        strategy_promotion_allowed=False,
        live_execution_enabled=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    blob=Path(a.report).read_bytes()
    result=audit(json.loads(blob))
    result["source_report_sha256"]=sha256(blob).hexdigest()
    target=Path(a.output)
    if target.exists():raise FileExistsError("immutable")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
