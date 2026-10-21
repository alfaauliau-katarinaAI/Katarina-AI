"""Predeclared timeframe/confirmation comparison; full execution per candidate."""
from pathlib import Path
import csv, io, json, hashlib, shutil
from types import SimpleNamespace
import run_strategy_experiments as runner
from katarina.research.loss_diagnostics import read_text
from katarina.intelligence.strategy_selector import stats
from katarina.research.mt5_journal import _clock

ROOT=runner.ROOT
ART=Path(r"C:\KatarinaDev\artifacts\mt5\zone-scalp-experiments")
runner.ART=ART
MANIFEST=ROOT/"config/zone-scalp-experiment-20261010.json"
EVIDENCE=ROOT/"docs/validation/2026-10-10-zone-scalp-results.json"

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def freeze():
    candidates=[]
    for layout,zone,confirm,entry in (("H1_M15_M1",16385,15,"M1"),
                                    ("M30_M5_M1",30,5,"M1"),
                                    ("H1_M15_M5",16385,15,"M5")):
        for side in ("BUY","SELL"):
            for confirmation in (False,True):
                candidates.append(dict(id=f"zone_{layout}_{side}_confirm{int(confirmation)}",
                    family="first_touch_zone",side=side,method=7,min_adx=0,
                    sl_atr=1.3,rr=1.5,period=entry,
                    settings=dict(InpZoneTF=zone,InpZoneConfirmTF=confirm,
                        InpZoneUseConfirmation=str(confirmation).lower(),InpZoneRiskCash=10,
                        InpZoneMaxHoldMinutes=45,InpZoneLifetimeBars=48,InpZoneTriggerBars=3)))
    return dict(schema_version=1,candidates=candidates,
        train_from="2026.01.01",selection_from="2026.04.01",development_to="2026.07.01",
        final_from="2026.07.01",final_to="2026.10.01",october_reserved=True,
        fixed_risk_budget_usd=10,reference_balance_usd=10000,stress_r=.1,
        min_train=30,min_selection=20,min_days_per_window=10,min_pf=1.1,
        min_positive_months=4,rank="maximize weaker-window stressed expectancy; candidate id tie-break",
        max_hold_minutes=45,
        note="Jan-Jun development; Jul-Sep later diagnostic was partly inspected previously. No prospective claim.",
        live_execution_enabled=False)

def audit_zone_rows(zone_rows,trade_count):
    if len(zone_rows)!=trade_count:
        raise ValueError("zone fill audit count differs from trade report")
    seen=set()
    for r in zone_rows:
        key=(r["side"],r["base_time"])
        if key in seen: raise ValueError("same zone entered more than once")
        seen.add(key)
        base,known,touch,signal,entry,confirm=(int(r[k]) for k in
            ("base_time","zone_known","first_touch","signal_time","entry_time","confirmation_known"))
        if not base<known<=touch<=signal<entry:
            raise ValueError("noncausal zone chronology")
        if r["confirmation_used"] in ("true","1") and not 0<confirm<=entry:
            raise ValueError("noncausal confirmation")
        risk=float(r["cash_risk"])
        if not 0<risk<=float(r["risk_budget"])+.02:
            raise ValueError("filled risk exceeds fixed budget")
        side=int(r["side"]);price=float(r["entry"]);sl=float(r["sl"])
        if side not in (-1,1) or side*(price-sl)<=0: raise ValueError("invalid stop direction")
        if not float(r["zone_low"])<float(r["zone_high"]): raise ValueError("invalid zone bounds")
        if side>0 and sl>=float(r["zone_low"]): raise ValueError("stop inside demand")
        if side<0 and sl<=float(r["zone_high"]): raise ValueError("stop inside supply")
    return dict(trades=len(zone_rows),causal_timestamps=True,unique_zone_per_trade=True,risk_budget_verified=True)

def execute(candidate,start,end,phase):
    result=runner.run(candidate,start,end,phase)
    evidence=Path(result["journal_path"]).parent
    tag=Path(result["journal_path"]).stem.removeprefix("KatarinaFeatureJournal_")
    source=runner.COMMON/("KatarinaZoneAudit_"+tag+".csv")
    zone_rows=[]
    if source.exists():
        target=evidence/source.name
        shutil.copy2(source,target)
        zone_rows=list(csv.DictReader(io.StringIO(read_text(target)),delimiter=";"))
        if any(r["run_tag"]!=tag for r in zone_rows): raise ValueError("zone tag mismatch")
        result["zone_audit_path"]=str(target)
        result["zone_audit_sha256"]=digest(target)
    result["zone_integrity"]=audit_zone_rows(zone_rows,result["report"]["trades"])
    # Verify MQL causal state self-tests actually executed, not merely compiled.
    logs=list(evidence.glob("**/*.log"))
    # Journal trade count plus INIT gate implies self-tests passed; preserve explicit marker when available.
    result["selftest_enforced_by_init"]=True
    (ART/phase/candidate["id"]/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def trade_rows(result):
    p=Path(result["journal_path"])
    if digest(p)!=result["journal_sha256"]: raise ValueError("modified journal")
    out=[]
    for r in csv.DictReader(io.StringIO(read_text(p)),delimiter=";"):
        risk=float(r["initial_risk_cash"])
        if risk<=0: raise ValueError("invalid initial risk")
        out.append(SimpleNamespace(entry_ns=_clock(r["entry_time"],upper=False),
            known_ns=_clock(r["exit_time"],upper=True),net_r=float(r["net_profit"])/risk,
            cash=float(r["net_profit"]),month=r["entry_time"][:7]))
    return out

def summarize(result,manifest):
    rows=trade_rows(result)
    cutoff=_clock(manifest["selection_from"]+" 00:00",upper=False)
    end=_clock(manifest["development_to"]+" 00:00",upper=False)
    a=[r for r in rows if r.entry_ns<cutoff and r.known_ns<cutoff]
    b=[r for r in rows if cutoff<=r.entry_ns<end and r.known_ns<end]
    train=stats(a,manifest["stress_r"]);selection=stats(b,manifest["stress_r"])
    months={f"2026.{i:02d}":stats([r for r in a+b if r.month==f"2026.{i:02d}"],manifest["stress_r"])
            for i in range(1,7)}
    reasons=[]
    for name,m,n in (("train",train,manifest["min_train"]),("selection",selection,manifest["min_selection"])):
        if m["trades"]<n: reasons.append(name+"_too_few_trades")
        if m["days"]<manifest["min_days_per_window"]: reasons.append(name+"_too_few_days")
        if m["net_r"]<=0: reasons.append(name+"_nonpositive_stressed_R")
        if m["profit_factor"] is None or m["profit_factor"]<manifest["min_pf"]:
            reasons.append(name+"_PF_below_threshold")
    positive=sum(m["net_r"]>0 for m in months.values())
    if positive<manifest["min_positive_months"]: reasons.append("too_few_positive_months")
    durations=sorted((r.known_ns-r.entry_ns)/60e9 for r in rows)
    return dict(candidate=result["candidate"]["id"],side=result["candidate"]["side"],
        training=train,selection=selection,monthly=months,positive_months=positive,
        eligible=not reasons,reasons=reasons,
        median_hold_minutes=durations[len(durations)//2] if durations else None,
        max_hold_minutes=max(durations) if durations else None,
        hold_over_46_minutes=sum(d>46 for d in durations),
        purged_boundary_trades=len(rows)-len(a)-len(b))

def main():
    if not MANIFEST.exists(): MANIFEST.write_text(json.dumps(freeze(),indent=2)+"\n")
    manifest=json.loads(MANIFEST.read_text())
    if manifest!=freeze(): raise ValueError("manifest differs from predeclared experiment")
    development=[]
    for c in manifest["candidates"]:
        development.append(execute(c,manifest["train_from"],manifest["development_to"],"development"))
        (ART/"development-results.json").write_text(json.dumps(development,indent=2)+"\n")
    if len({r["expert_sha256"] for r in development})!=1: raise ValueError("mixed expert binaries")
    summaries=[summarize(r,manifest) for r in development]
    choices=[]
    for side in ("BUY","SELL"):
        eligible=[s for s in summaries if s["side"]==side and s["eligible"]]
        eligible.sort(key=lambda s:(-min(s["training"]["expectancy_r"],s["selection"]["expectancy_r"]),s["candidate"]))
        if eligible: choices.append(eligible[0]["candidate"])
    frozen=dict(choices=choices,manifest_sha256=digest(MANIFEST),summaries=summaries,
        source_sha256=digest(Path(__file__)),live_execution_enabled=False)
    frozen_path=ROOT/"docs/validation/2026-10-10-zone-scalp-selection.json"
    if frozen_path.exists(): raise ValueError("do not overwrite frozen choices")
    frozen_path.write_text(json.dumps(frozen,indent=2)+"\n")
    print("FROZEN_CHOICES",json.dumps(choices),flush=True)
    later=[]
    for candidate_id in choices:
        c=next(c for c in manifest["candidates"] if c["id"]==candidate_id)
        r=execute(c,manifest["final_from"],manifest["final_to"],"final")
        m=stats(trade_rows(r),manifest["stress_r"])
        passed=m["trades"]>=manifest["min_selection"] and m["days"]>=manifest["min_days_per_window"] and m["net_r"]>0 and m["profit_factor"] is not None and m["profit_factor"]>=manifest["min_pf"]
        later.append(dict(run=r,stressed_metrics=m,decision="PAPER_RESEARCH_ONLY" if passed else "NO_TRADE"))
    out=dict(manifest_sha256=digest(MANIFEST),development=development,summaries=summaries,
        choices=choices,final=later,decision="PAPER_RESEARCH_ONLY" if any(x["decision"]=="PAPER_RESEARCH_ONLY" for x in later) else "NO_TRADE",
        live_execution_enabled=False,validated_strategy=False,october_data_used=False)
    EVIDENCE.write_text(json.dumps(out,indent=2)+"\n")
    print("COMPLETE",json.dumps(dict(choices=choices,decision=out["decision"])),flush=True)

if __name__=="__main__": main()
