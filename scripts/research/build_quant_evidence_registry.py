"""Decision registry for KATARINA quant reference screening.

Retain protocols, not external proprietary hedge fund signals. No
strategy promotion until unseen broker-net expectancy exists.
"""
from __future__ import annotations
import json,argparse
from pathlib import Path
from hashlib import sha256

SOURCES=[
dict(id="aqr_century_trend",
 institution="AQR / Hurst, Ooi, Pedersen",
 url="https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing",
 concept="Time-series momentum, trend strength and multi-asset diversification",
 decision="RETAIN_RESEARCH_HYPOTHESIS",
 warning="Monthly/long-term futures evidence does not prove minute-level CFD scalping"),
dict(id="man_ahl_trend_speed",
 institution="Man AHL / Man Group",
 url="https://www.man.com/insights/need-for-speed-trend-following",
 concept="Separate fast and slow trends, explicitly measure responsiveness",
 decision="RETAIN_RESEARCH_HYPOTHESIS",
 warning="Speed-specific trend behavior is not an intraday signal or proof of profit"),
dict(id="lopez_de_prado_purging",
 institution="Marcos Lopez de Prado / AFML",
 url="https://python.financial/concepts/purged-cross-validation/",
 concept="Chronological label-interval purging and embargo; evaluate leakage",
 decision="RETAIN_VALIDATION_PROTOCOL",
 warning="Chronological evaluation on previously researched periods is not pristine prospective OOS"),
dict(id="hudson_thames_triple_barrier",
 institution="Hudson and Thames / MlFinLab",
 url="https://hudsonthames.org/mlfinlab/",
 concept="Event-based sampling, triple barrier and meta-labeling research",
 decision="RETAIN_VALIDATION_PROTOCOL",
 warning="Do not conflate research marks with actual bid/ask fills or broker commissions"),
dict(id="microsoft_qlib_architecture",
 institution="Microsoft Research / Qlib",
 url="https://github.com/microsoft/qlib",
 concept="Structured feature store, experiment tracking and reproducible evaluations",
 decision="RETAIN_ENGINEERING_REFERENCE_ONLY",
 warning="Existing Windows Server 2012 VPS is not assumed compatible with Qlib production stack"),
dict(id="quantconnect_lean_engineering",
 institution="QuantConnect / LEAN",
 url="https://github.com/QuantConnect/Lean",
 concept="Independent event-driven backtest engineering and transaction-level audits",
 decision="RETAIN_ENGINEERING_REFERENCE_ONLY",
 warning="Do not introduce large infrastructure without reproducible gain"),
dict(id="purgedcv_github",
 institution="eslazarev / purged-cross-validation",
 url="https://github.com/eslazarev/purged-cross-validation",
 concept="Independent open-source reference for purging, embargo, walk-forward and CPCV",
 decision="RETAIN_VALIDATION_PROTOCOL",
 warning="Reference only; no vendor module installed or source code copied"),
]

def registry(ml,gate,ml4=None):
    if ml.get("decision")!="NO_TRADE" or gate.get("decision")!="NO_TRADE":
        raise ValueError("do_not_register_live_predictions")
    models=("prevalence","technical","regime_only","technical_plus_regime")
    folds=ml["fold_results"]
    result={}
    for kind in models:
        wins=sum(f["metric"][kind]["brier"] < f["metric"]["prevalence"]["brier"]-1e-9 for f in folds) if kind!="prevalence" else None
        weighted=sum(f["metric"][kind]["brier"]*f["test_count"] for f in folds)/sum(f["test_count"] for f in folds)
        result[kind]=dict(weighted_out_of_fold_brier=weighted,
             folds_with_lower_brier_than_baseline=wins,
             fold_total=len(folds))
    fourhour=None
    if ml4 is not None:
        if ml4.get("decision")!="NO_TRADE" or ml4.get("target_horizon_hours")!=4:
            raise ValueError("untrusted_four_hour_study")
        fourhour={}
        longer=ml4["fold_results"]
        for kind in models:
            wins=sum(f["metric"][kind]["brier"] <
                     f["metric"]["prevalence"]["brier"]-1e-9
                     for f in longer) if kind!="prevalence" else None
            fourhour[kind]=dict(weighted_out_of_fold_brier=
               sum(f["metric"][kind]["brier"]*f["test_count"] for f in longer)/
               sum(f["test_count"] for f in longer),
               folds_with_lower_brier_than_baseline=wins,
               fold_total=len(longer))
    per_symbol={}
    for symbol in sorted({f["symbol"] for f in folds}):
        subs=[f for f in folds if f["symbol"]==symbol]
        improvement=all(f["metric"]["technical_plus_regime"]["brier"]+
                        1e-8<f["metric"]["prevalence"]["brier"] for f in subs)
        per_symbol[symbol]=dict(eligible_folds=len(subs),
              predictive_regime_model_retain=False,
              positive_brier_lift_in_every_fold=improvement,
              decision="DO_NOT_PROMOTE_ML_MODEL")
    gate_res={}
    for rec in gate["per_symbol"]:
        symbol=rec["symbol"]
        g=rec["gated"]
        gate_res[symbol]=dict(all_entry_count=rec["all"]["n"],
             gated_entry_count=g["n"],
             gated_average_R=g["mean_R"],
             original_average_R=rec["all"]["mean_R"],
             sufficient_evidence=rec["sample_sufficient"],
             decision="KEEP_AS_OBSERVABLE_FEATURE_DO_NOT_ENABLE_AS_ENTRY_GATE")
    methodology=[
      dict(method="per_symbol_closed_bar_regime_monitor",
           status="KEEP_RESEARCH_OBSERVER",reason="causal H1 M15 M5, no live risk"),
      dict(method="regularized_logistic_1h_direction_prediction",
           status="REJECT_PRODUCTION",reason="out-of-fold Brier generally worse than train-only prevalence"),
      dict(method="regime_only_logistic_prediction",
           status="REJECT_PRODUCTION",reason="no consistent gain by symbol across chronological splits"),
      dict(method="regime_predeclared_tick_entry_filter",
           status="REJECT_PRODUCTION",reason="too few matched broker-exit samples"),
      dict(method="per_symbol_broker_cost_and_tick_replay",
           status="KEEP_RESEARCH_INFRASTRUCTURE",reason="immutable original bid/ask entry/exit evidence"),
      dict(method="purged_chronological_probabilistic_scoring",
           status="KEEP_VALIDATION_INFRASTRUCTURE",reason="training labels resolved before evaluation and embargo applied"),
      dict(method="macro_news_vintage_model",
           status="DEFER_UNTIL_VINTAGE_DATA",reason="archival at-time news available to trader not verified"),
      dict(method="order_flow_footprint_and_CVD",
           status="DEFER_UNTIL_TRUE_TRADE_VOLUME",reason="MT5 tick_volume is not executed futures aggressor volume"),
      dict(method="live_autonomous_scalping",
           status="FORBIDDEN_UNTIL_POSITIVE_BROKER_NET_OOS",reason="no verified profitable and statistically reliable strategy"),
    ]
    return dict(kind="katarina_quant_evidence_decision_registry_v1",
        report_date="2026-10-11",
        policy="REJECT_PRODUCTION_BY_DEFAULT",
        raw_references=SOURCES,
        research_methodology_decisions=methodology,
        brier_comparison=result,
        four_hour_brier_comparison=fourhour,
        by_symbol_prediction=per_symbol,
        by_symbol_regime_gate=gate_res,
        risk_status="NO_TRADE",
        claims_not_made=[
          "No access to proprietary hedge-fund execution signals",
          "No proof public GitHub repos are profitable",
          "No new genuinely unseen holdout in these reused research archives",
          "No actual broker slippage/commission calibration",
          "No high-confidence calibrated 1h direction probability"],
        model_promotion_allowed=False,live_execution_enabled=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--prediction",required=True)
    p.add_argument("--gates",required=True)
    p.add_argument("--prediction-four-hour")
    p.add_argument("--output",required=True)
    a=p.parse_args()
    out=Path(a.output)
    if out.exists():raise FileExistsError("never_overwrite_decision_register")
    raw1=Path(a.prediction).read_bytes()
    raw2=Path(a.gates).read_bytes()
    raw4=Path(a.prediction_four_hour).read_bytes() if a.prediction_four_hour else None
    result=registry(json.loads(raw1),json.loads(raw2),
                    json.loads(raw4) if raw4 else None)
    result["source_digests"]=dict(predict=sha256(raw1).hexdigest(),
         gate=sha256(raw2).hexdigest(),
         prediction_4h=sha256(raw4).hexdigest() if raw4 else None)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("Brier score summary",json.dumps(result["brier_comparison"]),flush=True)
    print("Four hour summary",json.dumps(result["four_hour_brier_comparison"]))
    print("Validated symbol with 2-fold uplift",
          [s for s,x in result["by_symbol_prediction"].items()
           if x["positive_brier_lift_in_every_fold"]],flush=True)
    print("OUTPUT",out)
if __name__=="__main__":
    main()
