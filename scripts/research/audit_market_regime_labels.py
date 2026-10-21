"""Audit forward-time leakage, broker-specific registry and diagnostic arithmetic.

Validates recorded *regime labels* and future closed-price study; it
cannot establish indicator parity with MetaTrader terminal buffers.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from datetime import datetime
from hashlib import sha256
from math import isfinite
from pathlib import Path
from katarina.intelligence.market_regime_intelligence import STATES,PROFILES
from backtest_market_regime_labels import groups,EVAL_HOURS

def time(iso):
    d=datetime.fromisoformat(iso)
    if d.tzinfo is None: raise ValueError("timezone_missing")
    return d.timestamp()

def audit(doc):
    if doc.get("kind")!="causal_mtf_market_regime_diagnostics_v1":
        raise ValueError("wrong_regime_report")
    if (doc.get("live_execution_enabled") is not False or
         doc.get("model_promotion_allowed") is not False or
         doc.get("decision")!="NO_TRADE"):
        raise ValueError("trade_authorization_mutated")
    rows=doc["classified_observations"]
    if doc["trials_count"]!=len(rows):
        raise ValueError("observation_count_inconsistent")
    windows={x[0]:(time(x[1]+"T00:00:00+00:00"),
                    time(x[2]+"T00:00:00+00:00"))
            for x in doc["periods_utc"]}
    repeated=set()
    counts=Counter()
    forward=Counter()
    for e in rows:
        sym=e["symbol"]
        if sym not in PROFILES or e["regime"] not in STATES:
            raise ValueError("unregistered_symbol_or_state")
        if e["regime"]!="UNKNOWN" and e["direction"] not in ("UP","DOWN","NONE"):
            raise ValueError("invalid_state_direction")
        if e["evidence_is_profit_probability"] is not False or e.get("promoted_to_live") is not False:
            raise ValueError("calibration_false_claim")
        if e["study_period"] not in windows:
            raise ValueError("unexpected_window")
        begin,end=windows[e["study_period"]]
        clock=time(e["close_time_utc"])
        if not begin<=clock<end or int(clock)%1800!=0:
            raise ValueError("lookahead_label_clock")
        unique=(sym,e["study_period"],clock)
        if unique in repeated:raise ValueError("duplicate_signal_clock")
        repeated.add(unique)
        score=e["evidence_score_0_100"]
        if e["regime"] in ("UNKNOWN","TRANSITION") and score is not None:
            raise ValueError("uncalibrated_transition_score")
        if score is not None and (not isfinite(score) or not 0<=score<=100):
            raise ValueError("bad_strength_score")
        if e["regime"]=="UNKNOWN" and e["frames"]:
            raise ValueError("unknown_regime_has_unvalidated_frames")
        for frame,detail in e["frames"].items():
            if frame not in ("M5","M15","H1"):
                raise ValueError("unexpected_evidence_frame")
            if detail["adx14"]<0 or detail["adx14"]>100 or detail["close_age_seconds"]<0:
                raise ValueError("invalid_frame_strength")
            if not 0<=detail["efficiency"]<=1.0001:
                raise ValueError("invalid_frame_efficiency")
        for hours in EVAL_HOURS:
            outcome=e["future_close_displacement"].get(str(hours)+"h")
            if outcome is None:continue
            moment=time(outcome["close_time_utc"])
            if moment<clock+hours*3600-300 or moment>clock+hours*3600 or moment>=end:
                raise ValueError("future_clock_wrong")
            x=outcome["signed_directional_displacement_ATR"]
            if not isfinite(x) or abs(abs(x)-outcome["absolute_displacement_ATR"])>1e-8:
                raise ValueError("future_return_decomposition")
            if outcome["is_transaction_profit"] is not False:
                raise ValueError("markout_looks_like_PnL")
            if e["regime"].endswith("_UP"):
                expected=x>0
            elif e["regime"].endswith("_DOWN"):
                expected=x<0
            else: expected=None
            if outcome["aligned_with_state"]!=expected:
                raise ValueError("wrong_directional_label")
            forward[(sym,str(hours)+"h")]+=1
        counts[e["regime"]]+=1
    aggregate=groups(rows)
    original={(x["symbol"],x["period"],x["regime"]):x
              for x in doc["by_symbol_regime_period"]}
    if len(original)!=len(doc["by_symbol_regime_period"]) or len(original)!=len(aggregate):
        raise ValueError("summary_keys_incomplete")
    for expect in aggregate:
        key=(expect["symbol"],expect["period"],expect["regime"])
        actual=original.get(key)
        if actual is None:raise ValueError("missing_regime_cohort")
        if (actual["n_observations"]!=expect["n_observations"] or
             actual["distinct_UTC_days"]!=expect["distinct_UTC_days"] or
             actual["model_validated"] is not False):
            raise ValueError("summary_group_mismatch")
        for hours in EVAL_HOURS:
            a=actual["future_close_diagnostics"][str(hours)+"h"]
            b=expect["future_close_diagnostics"][str(hours)+"h"]
            if a["measured"]!=b["measured"] or (
                a["no_execution_costs_included"] is not True):
                raise ValueError("future_horizon_summary_mismatch")
            for key2 in ("mean_abs_close_displacement_ATR",
                          "mean_signed_close_displacement_ATR",
                          "directional_consistency"):
                if a[key2] is None and b[key2] is None:continue
                if a[key2] is None or b[key2] is None or abs(a[key2]-b[key2])>1e-8:
                    raise ValueError("future_markout_summary_mismatch")
    return dict(report_kind="mtf_market_regime_integrity_audit",
       observations_verified=len(rows),regime_groups_verified=len(aggregate),
       state_counts=dict(counts),
       prices_are_closed_M5_not_real_trade_fills=True,
       no_profit_probabilities_claimed=True,
       no_unseen_holdout_claimed=True,
       live_execution_enabled=False,model_promotion_allowed=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    content=Path(a.report).read_bytes()
    result=audit(json.loads(content))
    result["source_sha256"]=sha256(content).hexdigest()
    target=Path(a.output)
    if target.exists():raise FileExistsError("immutable_audit")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
