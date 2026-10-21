"""Read-only replay of 2026 closed-frame history using KATARINA regime v2.

Run with: python scripts/research/audit_adaptive_regime_v2.py <archive-folder>
Does not place orders, optimize thresholds against evaluation labels, or touch risk.
"""
from __future__ import annotations
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from katarina.intelligence.perception.adaptive_regime import (
    AdaptiveRegimeEngine, MarketState, from_archived_frames)
from katarina.intelligence.perception.causal_seasonality import (
    CausalSeasonality, HistoricalOutcome)

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main(folder: Path):
    regime_source=folder/"market-regime-seven-symbols-mtf-final-v2.json"
    predictions_source=folder/"regime-prediction-purged-seven-symbols-v1.json"
    rows=load(regime_source)["classified_observations"]
    model_rows=load(predictions_source)["scored_test_rows"]
    engine=AdaptiveRegimeEngine()
    old=Counter()
    new=Counter()
    comparison=defaultdict(lambda: [0,0])
    labels={MarketState.TREND_UP:1, MarketState.TREND_DOWN:0,
       MarketState.PULLBACK_UP:1,MarketState.PULLBACK_DOWN:0,
       MarketState.BREAKOUT_UP:1,MarketState.BREAKOUT_DOWN:0,
       MarketState.REVERSAL_UP:1,MarketState.REVERSAL_DOWN:0}
    periods=defaultdict(lambda: [0,0])
    errors=Counter()
    records=[]
    for r in rows:
        old[r["regime"]]+=1
        symbol=r["symbol"]
        try:
            frames, asof=from_archived_frames(symbol,r["frames"],r["close_time_utc"])
            assessment=engine.assess(frames=frames,as_of_utc=asof)
        except (KeyError, ValueError,TypeError) as ex:
            errors[type(ex).__name__]+=1
            new["UNKNOWN"] += 1  # Archived incomplete frames are explicitly UNKNOWN.
            continue
        new[assessment.state.value]+=1
        period=r["study_period"]
        periods[period][0]+=1
        if assessment.state is MarketState.TRANSITION: periods[period][1]+=1
        # Only *future displacement diagnostics*, never broker-trade P&L.
        actual=r.get("future_close_displacement",{}).get("1h")
        if actual is not None and assessment.state in labels:
            direction=1 if actual["signed_directional_displacement_ATR"]>0 else 0
            key=(symbol,period)
            comparison[key][0]+=1
            comparison[key][1]+=int(labels[assessment.state]==direction)
        records.append((symbol,period,assessment.state.value))
    # Closed future 1h labels are known only after their label_end_utc.
    cutoff=datetime(2026,10,1,tzinfo=timezone.utc)
    historical=[]
    test=[]
    for row in model_rows:
        symbol=row["symbol"]
        seen=datetime.fromisoformat(row["time_utc"].replace("Z","+00:00"))
        known=datetime.fromisoformat(row["label_end_utc"].replace("Z","+00:00"))
        actual=bool(row["y_actual_one_hour_positive"])
        if row["fold"]=="august_to_september":
            historical.append(HistoricalOutcome(symbol,seen,known,actual))
        if row["fold"]=="august_september_to_october":
            test.append(row)
    season=CausalSeasonality(min_bin_samples=20,prior_weight=75)
    trained=season.train(historical,cutoff_utc=cutoff)
    context_n=0
    brier_base=0.
    brier_season=0.
    seasonal_by_symbol=defaultdict(lambda:[0,0.,0.])
    for row in test:
        asof=datetime.fromisoformat(row["time_utc"].replace("Z","+00:00"))
        context=season.estimate(row["symbol"],as_of_utc=asof)
        base=context.baseline_up_rate
        p=max(.01,min(.99,base+context.directional_tilt))
        y=row["y_actual_one_hour_positive"]
        brier_base+=(base-y)**2
        brier_season+=(p-y)**2
        context_n+=1
        stat=seasonal_by_symbol[row["symbol"]]
        stat[0]+=1
        stat[1]+=(base-y)**2
        stat[2]+=(p-y)**2
    result={
       "kind":"adaptive_regime_v2_retrospective_shadow_audit",
       "generated":"2026-10-11",
       "assumptions":["Archived MTF frames reflect values at each closed diagnostic observation",
           "No swing reclaim/breakout inferred without OHLC; these states deliberately absent here",
           "Historical periods have been inspected previously: October NOT unseen prospective test",
           "Directional displacement is NOT executable net return",
           "Seasonality based on September labeled outcomes; October diagnostic only",
           "UTC hour seasonality not exchange-local DST-adjusted session profiles"],
       "method":"frozen v2 rules + fixed per-symbol causal seasonality shrinkage; no hyperparameter search here",
       "source_sha256":{"regime":sha256(regime_source.read_bytes()).hexdigest(),
                        "prediction":sha256(predictions_source.read_bytes()).hexdigest()},
       "historical_observations":len(rows),"processed":sum(new.values()),
       "errors":dict(errors),"old_states":dict(old),"v2_states":dict(new),
       "transition_share_old":old["TRANSITION"]/len(rows),
       "transition_share_v2":new["TRANSITION"]/max(1,sum(new.values())),
       "transition_by_period":{k:{"total":v[0],"transition":v[1]} for k,v in periods.items()},
       "regime_direction_diagnostic_per_symbol_period":[
           {"symbol":k[0],"period":k[1],"n":v[0],"direction_hit_fraction":v[1]/v[0]}
            for k,v in sorted(comparison.items()) if v[0]>=1],
       "seasonality":{"train_label_count":trained,"diagnostic_october_count":context_n,
            "baseline_brier":brier_base/context_n,
            "hour_weekday_context_brier":brier_season/context_n,
            "seasonality_improves_brier":brier_season<brier_base,
            "per_symbol":{k:{"n":v[0],"baseline_brier":v[1]/v[0],
                 "seasonal_brier":v[2]/v[0]} for k,v in sorted(seasonal_by_symbol.items())}},
       "live_risk_authorized":False, "model_promotion_allowed":False,
       "next_required":"broker net-cost simulator and new chronological evaluation; structural OHLC feed"}
    dest=folder/"adaptive-regime-v2-shadow-audit-20261011.json"
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"observations":result["processed"],
         "old_states":result["old_states"],"new_states":result["v2_states"],
         "transition_old":result["transition_share_old"],"transition_new":result["transition_share_v2"],
         "seasonality":result["seasonality"],
         "direction":result["regime_direction_diagnostic_per_symbol_period"],
         "report":str(dest)},indent=2))
    return 0
if __name__=="__main__":
    if len(sys.argv)!=2:
        sys.exit("usage: python audit_adaptive_regime_v2.py <archive-folder>")
    raise SystemExit(main(Path(sys.argv[1])))
