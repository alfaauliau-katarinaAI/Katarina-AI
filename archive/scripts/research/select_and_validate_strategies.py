"""Freeze an expected-R selector, then test only selected families on later data."""
from pathlib import Path
import csv,io,json,sys,hashlib
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from katarina.research.loss_diagnostics import read_text
from katarina.research.mt5_journal import load_journal,_clock
from katarina.intelligence.brain import KatarinaAIBrain
from katarina.intelligence.strategy_selector import StrategyObservation
from run_strategy_experiments import ROOT,ART,run

def observations(result):
    path=Path(result["journal_path"])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=result["journal_sha256"]:
        raise ValueError("journal changed")
    if result["report"]["trades"]:
        load_journal(path,expected_trades=result["report"]["trades"],
                     expected_net_profit=Decimal(result["report"]["net_profit"]))
    rows=list(csv.DictReader(io.StringIO(read_text(path)),delimiter=";"))
    candidate=result["candidate"]["id"]
    out=[]
    for i,r in enumerate(rows):
        if r["context_regime"] not in ("UP","DOWN","MIXED"):
            continue # Explicit unavailable context: no model admission.
        out.append(StrategyObservation(candidate+":"+r["run_tag"]+":"+str(i),candidate,r["side"],
            r["context_regime"],_clock(r["entry_time"],upper=False),_clock(r["exit_time"],upper=True),
            float(r["net_profit"])/float(r["initial_risk_cash"])))
    return out

def main():
    manifest=json.loads((ROOT/"config/brain-experiment-20261010.json").read_text())
    results=json.loads((ART/"development-results.json").read_text())
    expected={c["id"] for c in manifest["candidates"]}
    if {r["candidate"]["id"] for r in results}!=expected or len(results)!=len(expected):
        raise ValueError("development matrix is incomplete")
    if len({r["expert_sha256"] for r in results})!=1:
        raise ValueError("different expert versions in development")
    rows=[r for result in results for r in observations(result)]
    cutoff=_clock(manifest["selection_cutoff"]+" 00:00",upper=False)
    end=_clock(manifest["development_to"]+" 00:00",upper=False)
    selector,policy=KatarinaAIBrain().train_strategy_selector(rows,train_cutoff_ns=cutoff,selection_end_ns=end)
    policy["manifest_sha256"]=hashlib.sha256((ROOT/"config/brain-experiment-20261010.json").read_bytes()).hexdigest()
    policy["source_code_sha256"]=hashlib.sha256((ROOT/"src/katarina/intelligence/strategy_selector.py").read_bytes()).hexdigest()
    policy["development_runs"]=results
    policy["label"]= "DEVELOPMENT_SELECTION_NOT_LIVE_APPROVAL"
    frozen=ROOT/"docs/validation/2026-10-10-strategy-selection.json"
    if frozen.exists(): raise ValueError("policy already frozen; do not silently reselect")
    frozen.write_text(json.dumps(policy,indent=2,allow_nan=False)+"\n")
    ids=sorted({c["candidate"] for c in policy["choices"]})
    print("FROZEN_CHOICES",json.dumps(policy["choices"]),flush=True)
    later=[]
    for candidate_id in ids:
        c=next(c for c in manifest["candidates"] if c["id"]==candidate_id)
        result=run(c,manifest["final_from"],manifest["final_to"],"final")
        later.append(result)
    final_rows=[r for result in later for r in observations(result)]
    audit=selector.audit_final(final_rows,final_start_ns=end,
                              final_end_ns=_clock(manifest["final_to"]+" 00:00",upper=False))
    audit["runs"]=later
    audit["limitations"]=["Aug/Sep market history was previously inspected in other research.",
       "Per-regime journal filtering is diagnostic: combined strategy router needs its own execution rerun.",
       "October remains untouched; no prospective demo or live promotion."]
    (ROOT/"docs/validation/2026-10-10-strategy-final-audit.json").write_text(
        json.dumps(audit,indent=2,allow_nan=False)+"\n")
    print("FINAL_AUDIT",json.dumps(audit["cells"]),flush=True)

if __name__=="__main__": main()
