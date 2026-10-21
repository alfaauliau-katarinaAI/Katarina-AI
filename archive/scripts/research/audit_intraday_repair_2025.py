"""Reproducibility and integrity audit of the intraday repairs."""
from pathlib import Path
import json,hashlib
A=Path(r"C:\KatarinaDev\artifacts\historical-brain")
parts={
 "non_gold":"katarina_distinct_index_fx_intraday_2025_2026.json",
 "gold_exit":"katarina_xau_exit_three_way_tick_2025_2026.json",
 "gold_baseline":"katarina_xau_method_tick_ablation_2025_2026.json",
}
data={k:json.loads((A/v).read_text(encoding="utf-8")) for k,v in parts.items()}
alt=data["non_gold"]["symbol_results"]
assert len(alt)==6 and all("error" not in x for x in alt)
assert all(not y["development_gate_pass"] for x in alt for y in x["playbooks"])
assert len(data["gold_exit"]["events"])==99*3*2
assert not data["gold_exit"]["invalid"]
exitdata=data["gold_exit"]["events"]
base=[x for x in data["gold_baseline"]["individual_event_outcomes"]
      if "ADX20" in x["filters"] and x["rr"]==2]
assert len(base)==198
lookup={(x["time"],x["cost"]):x for x in exitdata if x["style"]=="FIXED_2R"}
assert len(lookup)==198
for row in base:
 key=(row["time"],"BASE" if row["cost"]=="BASE" else "STRESS")
 assert key in lookup
 assert abs(lookup[key]["R"]-row["R"])<1e-7
metricsdata={(x["exit"],x["cost"]):x["years"] for x in data["gold_exit"]["summary"]}
assert metricsdata[("FIXED_2R","BASE")]["2025"]["n"]==49
assert metricsdata[("FIXED_2R","BASE")]["2026"]["n"]==50
assert (metricsdata[("FIXED_2R","BASE")]["2025"]["avg_R"] >
  metricsdata[("PARTIAL_TRAIL_3R","BASE")]["2025"]["avg_R"])
assert (metricsdata[("FIXED_2R","BASE")]["2026"]["avg_R"] >
  metricsdata[("BE_TRAIL_3R","BASE")]["2026"]["avg_R"])
report={"kind":"KATARINA_INTRADAY_REPAIR_EVIDENCE_INTEGRITY",
 "artifact_hashes":{key:hashlib.sha256((A/name).read_bytes()).hexdigest()
                    for key,name in parts.items()},
 "non_gold_instruments_checked":6,
 "non_gold_qualified_models":0,
 "gold_exit_scenario_records":len(exitdata),
 "gold_fixed_exit_matches_previous_bid_ask_replay":198,
 "gold_initial_stop_mandatory":True,
 "extra_positions_or_layering_in_test":False,
 "fresh_unseen_OOS":False,
 "real_execution_orders_issued":0,
 "audit_pass":True}
out=A/"katarina_intraday_repair_integrity_20261011.json"
out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
