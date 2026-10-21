"""Exploratory follow-up: smaller zones under unchanged entry/risk/validation rules."""
import json
from pathlib import Path
import run_zone_scalp_experiments as experiment
from katarina.intelligence.strategy_selector import stats

ROOT=experiment.ROOT
ART=Path(r"C:\KatarinaDev\artifacts\mt5\fast-zone-scalp-experiments")
MANIFEST=ROOT/"config/fast-zone-scalp-experiment-20261010.json"
experiment.ART=ART
experiment.runner.ART=ART

def freeze():
    m=experiment.freeze()
    template=m["candidates"][:4]
    candidates=[]
    for label,zone,confirm in (("M15_M5_M1",15,5),("M5_M3_M1",5,3)):
        for source in template:
            c=json.loads(json.dumps(source))
            flag=int(c["settings"]["InpZoneUseConfirmation"]=="true")
            c["id"]=f'zone_{label}_{c["side"]}_confirm{flag}'
            c["period"]="M1"
            c["settings"]["InpZoneTF"]=zone
            c["settings"]["InpZoneConfirmTF"]=confirm
            candidates.append(c)
    m["candidates"]=candidates
    m["hypothesis"]="Smaller zone timeframe improves opportunity coverage at unchanged scalping risk limits."
    m["prior_attempts"]=12
    m["selection_bias_note"]="Follow-up designed after sparse Jan-Jun results from 12 larger-timeframe candidates; development data reused. Total search is 20 candidates."
    return m

def main():
    if MANIFEST.exists(): raise ValueError("experiment already frozen")
    MANIFEST.write_text(json.dumps(freeze(),indent=2)+"\n")
    m=json.loads(MANIFEST.read_text())
    runs=[]
    for c in m["candidates"]:
        runs.append(experiment.execute(c,m["train_from"],m["development_to"],"development"))
        (ART/"development-results.json").write_text(json.dumps(runs,indent=2)+"\n")
    if len({r["expert_sha256"] for r in runs})!=1: raise ValueError("mixed binaries")
    summaries=[experiment.summarize(r,m) for r in runs]
    choices=[]
    for side in ("BUY","SELL"):
        eligible=[s for s in summaries if s["side"]==side and s["eligible"]]
        eligible.sort(key=lambda s:(-min(s["training"]["expectancy_r"],s["selection"]["expectancy_r"]),s["candidate"]))
        if eligible: choices.append(eligible[0]["candidate"])
    policy=dict(choices=choices,summaries=summaries,manifest_sha256=experiment.digest(MANIFEST),
        source_sha256=experiment.digest(Path(__file__)),live_execution_enabled=False,
        total_candidates_including_prior=20)
    frozen=ROOT/"docs/validation/2026-10-10-fast-zone-scalp-selection.json"
    if frozen.exists(): raise ValueError("existing frozen policy")
    frozen.write_text(json.dumps(policy,indent=2)+"\n")
    print("FAST_FROZEN_CHOICES",json.dumps(choices),flush=True)
    later=[]
    for cid in choices:
        c=next(c for c in m["candidates"] if c["id"]==cid)
        r=experiment.execute(c,m["final_from"],m["final_to"],"final")
        met=stats(experiment.trade_rows(r),m["stress_r"])
        passed=met["trades"]>=m["min_selection"] and met["days"]>=m["min_days_per_window"] and met["net_r"]>0 and met["profit_factor"] is not None and met["profit_factor"]>=m["min_pf"]
        later.append(dict(run=r,stressed_metrics=met,decision="PAPER_RESEARCH_ONLY" if passed else "NO_TRADE"))
    out=dict(manifest_sha256=experiment.digest(MANIFEST),development=runs,summaries=summaries,
        choices=choices,final=later,decision="PAPER_RESEARCH_ONLY" if any(x["decision"]=="PAPER_RESEARCH_ONLY" for x in later) else "NO_TRADE",
        live_execution_enabled=False,validated_strategy=False,october_data_used=False,
        total_candidates_including_prior=20,selection_bias_note=m["selection_bias_note"])
    (ROOT/"docs/validation/2026-10-10-fast-zone-scalp-results.json").write_text(json.dumps(out,indent=2)+"\n")
    print("FAST_COMPLETE",json.dumps(dict(choices=choices,decision=out["decision"])),flush=True)

if __name__=="__main__": main()
