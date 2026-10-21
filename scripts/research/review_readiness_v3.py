"""Freeze and grade 55-pair semantic study; no cherry-picked profitable subset."""
from __future__ import annotations
import json,csv,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.intelligence.lab.research_readiness_gate import Evidence,evaluate_readiness
BASE=Path(r"C:\KatarinaDev\decision-backtest-20261012")
OUT=BASE/"semantic_v3_full_55"
def main():
    x=json.loads((OUT/"RESULT.json").read_text(encoding="utf-8"))
    control=json.loads((BASE/"root_cause_v3"/"ROOT_CAUSE_DIAGNOSTIC.json").read_text(encoding="utf-8"))
    by_pair=[]
    reasons=Counter()
    for p in x["per_pair"]:
        data=Evidence(
            symbol=p["symbol"],trades=int(p["combined_count"]),
            mean_r=p["combined_mean_R"],profit_factor=p["combined_PF"],
            cost_stress_mean_r=p["combined_stress_0_1_mean_R"],
            segment_mean_r=(p["combined_2025_mean_R"],
              p["combined_2026_Jan_May_mean_R"],
              p["combined_2026_Jun_Oct_mean_R"]),
            unseen_holdout=False,broker_costs_reconciled=False,
            historical_news_verified=False,full_chronological_replay=False,
            causal_inputs_verified=True)
        grade=evaluate_readiness(data)
        reasons.update(grade.reasons)
        by_pair.append({
            "symbol":p["symbol"],
            "candidate_signals":p["combined_count"],
            "mean_R":p["combined_mean_R"],
            "PF":p["combined_PF"],
            "cost_stress_mean_R":p["combined_stress_0_1_mean_R"],
            "status":grade.status,
            "paper_candidate":grade.candidate_for_paper,
            "reasons":list(grade.reasons),
        })
    report={
        "created_for":"KATARINA_V3_RESEARCH_READINESS",
        "symbol_count":len(by_pair),
        "paper_candidates":sum(bool(p["paper_candidate"]) for p in by_pair),
        "validated_live_strategies":0,
        "reason_counts":dict(reasons),
        "before_trades":x["totals"]["baseline"]["n"],
        "after_strict_structure_trades":x["totals"]["both"]["n"],
        "before_mean_R":x["totals"]["baseline"]["avg_R"],
        "after_mean_R":x["totals"]["both"]["avg_R"],
        "after_PF":x["totals"]["both"]["PF"],
        "initial_breakout_labels":x["strategies"]["BREAKOUT_RETEST"]["original"],
        "real_breakout_retests":x["strategies"]["BREAKOUT_RETEST"]["true_semantic"],
        "breakout_retets_and_quality_pass":x["strategies"]["BREAKOUT_RETEST"]["both"],
        "directional_control":{
            k:{"original_mean_R":v["baseline"]["avg_R"],
               "opposite_mean_R":v["same_time_reverse_side"]["avg_R"],
               "direction_delta_R":v["paired_delta_R"]}
            for k,v in control["per_pair"].items()
        },
        "per_pair":by_pair,
        "limitations":[
          "2025-2026 data have repeatedly been seen, so this is not a genuine unseen holdout",
          "Only 1 of every 36 M5 samples considered, not a full bar-by-bar replay",
          "Historical news blackout unverified and broker tick/commission not reconciled",
          "Unseen future observations and portfolio equity execution are not tested",
          "Status remains UNVALIDATED regardless of positive small historical subsets",
          "No live MT5 execution performed or authorized",
        ]}
    (OUT/"READINESS_V3.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    with (OUT/"readiness_55.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=("symbol","candidate_signals","mean_R","PF","cost_stress_mean_R","status","paper_candidate","reasons"))
        writer.writeheader()
        for p in by_pair:writer.writerow({**p,"reasons":";".join(p["reasons"])})
    print("READINESS",json.dumps({k:report[k] for k in ("symbol_count","paper_candidates",
        "validated_live_strategies","before_trades","after_strict_structure_trades",
        "before_mean_R","after_mean_R","after_PF","initial_breakout_labels",
        "real_breakout_retests","directional_control")},ensure_ascii=False))
if __name__=="__main__":main()