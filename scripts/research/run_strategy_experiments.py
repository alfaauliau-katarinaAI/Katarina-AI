"""Serial bounded MT5 experiments; reconcile every run and preserve provenance."""
from pathlib import Path
import csv, io, json, shutil, subprocess, hashlib, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from katarina.research.loss_diagnostics import read_text, report_stats, audit
from katarina.research.mt5_journal import load_journal
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[2]
ART=Path(r"C:\KatarinaDev\artifacts\mt5\brain-experiments")
DATA=Path(r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\2698BCED53B80670A80FF375C9E8D6A1")
COMMON=DATA.parent/"Common"/"Files"
TERMINAL=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe"

def freeze():
    candidates=[]
    for family,method,adx in (("pullback",0,20),("sr_rejection",5,0),("breakout_retest",6,20)):
        for side in ("BUY","SELL"):
            for profile,sl,rr in (("baseline",1.3,2.2),("wider_stop",2.,2.2),("nearer_target",1.3,1.5)):
                candidates.append(dict(id=f"{family}_{side}_{profile}",family=family,side=side,
                                       method=method,min_adx=adx,sl_atr=sl,rr=rr))
    return dict(schema_version=1,candidates=candidates,
        development_from="2026.06.01",development_to="2026.08.01",
        selection_cutoff="2026.07.01",final_from="2026.08.01",final_to="2026.10.01",
        forward_reserve_from="2026.10.01",forward_reserve_to="2026.10.10",
        note="Final Aug/Sep history was previously inspected. October remains unused.",
        risk=dict(lot=.01,deposit=10000,leverage=100,max_spread_atr=.12),
        selection=dict(min_train=30,min_selection=20,stress_r=.1,min_selection_pf=1.1),
        live_execution_enabled=False)

def run(candidate,start,end,phase):
    runroot=ART/phase/candidate["id"]
    if runroot.exists():
        raise RuntimeError("Do not overwrite or silently resume experiment "+str(runroot))
    runroot.mkdir(parents=True)
    settings=dict(line.split("=",1) for line in (ROOT/"config/mt5-research-baseline.set").read_text().splitlines() if "=" in line)
    settings.update(InpBuyMethod=str(candidate["method"]),InpSellMethod=str(candidate["method"]),
        InpEnableBuy=str(candidate["side"] in ("BUY","BOTH")).lower(),
        InpEnableSell=str(candidate["side"] in ("SELL","BOTH")).lower(),
        InpBuySLATR=str(candidate["sl_atr"]),InpSellSLATR=str(candidate["sl_atr"]),
        InpBuyRR=str(candidate["rr"]),InpSellRR=str(candidate["rr"]),
        InpMinADX=str(candidate["min_adx"]),InpEnableOpportunityJournal="true",
        InpResearchContextGate=candidate.get("context_gate",""))
    settings.update({k:str(v) for k,v in candidate.get("settings",{}).items()})
    preset=runroot/"parameters.set"
    preset.write_text("".join(k+"="+v+"\n" for k,v in settings.items()))
    before=set(COMMON.glob("KatarinaFeatureJournal_*.csv"))
    opp_before=set(COMMON.glob("KatarinaOpportunity_*.csv"))
    command=["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",
        str(ROOT/"scripts/stage35/Run-KatarinaStage35Tester.ps1"),
        "-TerminalPath",TERMINAL,"-ExistingTerminalDataPath",str(DATA),
        "-Expert",r"KatarinaBrainResearch20261010\KatarinaResearchScalperEA",
        "-Symbol","XAUUSD.vx","-Period",candidate.get("period","M1"),"-FromDate",start,"-ToDate",end,
        "-ParametersPath",str(preset),"-OutputRoot",str(runroot),"-TimeoutSeconds","600"]
    completed=subprocess.run(command,capture_output=True,text=True,timeout=660)
    (runroot/"runner.log").write_text(completed.stdout+completed.stderr)
    if completed.returncode:
        raise RuntimeError("tester failed: "+str(runroot))
    receipts=list(runroot.glob("*/evidence/stage35-tester-evidence.json"))
    if len(receipts)!=1: raise RuntimeError("ambiguous tester receipt")
    evidence=receipts[0].parent
    receipt=json.loads(receipts[0].read_text(encoding="utf-8-sig"))
    if receipt["result"]!="PASS_STAGE35_TESTER_INFRASTRUCTURE": raise RuntimeError("failed run")
    stat=report_stats(evidence/"tester-report.htm")
    if stat["history_quality"]!="100% real ticks": raise RuntimeError("incomplete real tick history")
    journals=set(COMMON.glob("KatarinaFeatureJournal_*.csv"))-before
    if len(journals)!=1: raise RuntimeError("ambiguous new journal")
    journal=journals.pop()
    tag=journal.stem.removeprefix("KatarinaFeatureJournal_")
    opp=COMMON/("KatarinaOpportunity_"+tag+".csv")
    if not opp.exists() or opp in opp_before: raise RuntimeError("missing matching opportunity journal")
    shutil.copy2(journal,evidence/journal.name);shutil.copy2(opp,evidence/opp.name)
    journal=evidence/journal.name
    if stat["trades"]>0:
        load_journal(journal,expected_trades=stat["trades"],expected_net_profit=Decimal(stat["net_profit"]))
    rows=list(csv.DictReader(io.StringIO(read_text(journal)),delimiter=";"))
    if any(r["run_tag"]!=tag for r in rows): raise RuntimeError("journal tag mismatch")
    opportunities=list(csv.DictReader(io.StringIO(read_text(opp)),delimiter=";"))
    if any(r["run_tag"]!=tag for r in opportunities): raise RuntimeError("opportunity tag mismatch")
    out=dict(candidate=candidate,phase=phase,from_date=start,to_date=end,report=stat,
             run_id=receipt["run_id"],expert_sha256=receipt["expert_sha256"],
             parameters_sha256=receipt["parameters_sha256"],
             journal_path=str(journal),journal_sha256=hashlib.sha256(journal.read_bytes()).hexdigest(),
             opportunity_path=str(evidence/opp.name),
             opportunity_sha256=hashlib.sha256(opp.read_bytes()).hexdigest(),
             opportunity_rows=len(opportunities),
             occupied_rows=sum(r["occupied"] in ("true","1") for r in opportunities),
             strategy_validated=False,live_execution_enabled=False)
    (runroot/"result.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"id":candidate["id"],"phase":phase,"trades":stat["trades"],
                      "net":stat["net_profit"],"bars":len(opportunities)}),flush=True)
    return out

def main():
    ART.mkdir(parents=True,exist_ok=True)
    manifest_path=ROOT/"config/brain-experiment-20261010.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(freeze(),indent=2)+"\n")
    manifest=json.loads(manifest_path.read_text())
    results=[]
    # Reproduction checks telemetry/cost-accounting changes against the prior baseline.
    baseline=dict(id="hybrid_reproduction",family="hybrid",side="BOTH",method=3,min_adx=20,sl_atr=1.3,rr=2.2)
    result=run(baseline,"2026.08.01","2026.10.01","baseline")
    if result["report"]["trades"]!=264 or Decimal(result["report"]["net_profit"])!=Decimal("-165.32"):
        raise RuntimeError("baseline changed: inspect before strategy research")
    report=Path(result["journal_path"]).parent/"tester-report.htm"
    (ROOT/"docs/validation/2026-10-10-baseline-excursion-audit.json").write_text(
        json.dumps(audit(result["journal_path"],report),indent=2)+"\n")
    for candidate in manifest["candidates"]:
        results.append(run(candidate,manifest["development_from"],manifest["development_to"],"development"))
        (ART/"development-results.json").write_text(json.dumps(results,indent=2)+"\n")
    print("DEVELOPMENT_COMPLETE",flush=True)

if __name__=="__main__": main()
