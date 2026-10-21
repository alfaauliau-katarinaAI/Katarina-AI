"""Execute frozen selected context gates; never choose a replacement on final data."""
import json
from pathlib import Path
from select_and_validate_strategies import observations
from run_strategy_experiments import ROOT,ART,run
from katarina.intelligence.strategy_selector import stats

def main():
    policy=json.loads((ROOT/"docs/validation/2026-10-10-strategy-selection.json").read_text())
    manifest=json.loads((ROOT/"config/brain-experiment-20261010.json").read_text())
    reports=[]
    for cell in policy["choices"]:
        candidate=dict(next(c for c in manifest["candidates"] if c["id"]==cell["candidate"]))
        candidate["id"]+="_gate_"+cell["regime"]
        candidate["context_gate"]=cell["regime"]
        result=run(candidate,manifest["final_from"],manifest["final_to"],"frozen-router")
        rows=observations(result)
        if any(r.regime!=cell["regime"] or r.side!=cell["side"] for r in rows):
            raise ValueError("actual execution violated frozen routing gate")
        m=stats(rows,manifest["selection"]["stress_r"])
        passed=(m["trades"]>=manifest["selection"]["min_selection"] and m["days"]>=5
                and m["net_r"]>0 and m["profit_factor"] is not None
                and m["profit_factor"]>=manifest["selection"]["min_selection_pf"])
        reports.append(dict(side=cell["side"],regime=cell["regime"],candidate=cell["candidate"],
                            run=result,stressed_metrics=m,
                            decision="PAPER_RESEARCH_ONLY" if passed else "NO_TRADE",
                            research_pass=passed,live_risk_authorized=False))
    out=dict(policy_sha256=policy["policy_sha256"],cells=reports,
             live_execution_enabled=False,validated_strategy=False,
             october_data_used=False,retuning_on_final_data=False,
             limitation="Historical Aug/Sep was previously inspected. This is a frozen execution audit, not prospective proof.")
    (ROOT/"docs/validation/2026-10-10-frozen-router-audit.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2),flush=True)

if __name__=="__main__": main()
