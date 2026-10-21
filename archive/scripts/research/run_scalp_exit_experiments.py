"""Freeze four exit profiles; execute each and later audit fixed side choices."""
import csv,io,json,shutil,math
from pathlib import Path
import run_zone_scalp_experiments as e
from katarina.intelligence.strategy_selector import stats

ROOT=e.ROOT
ART=Path(r"C:\KatarinaDev\artifacts\mt5\scalp-exit-experiments")
e.ART=ART
e.runner.ART=ART
MANIFEST=ROOT/"config/scalp-exit-experiment-20261010.json"

def freeze():
    previous=json.loads((ROOT/"config/fast-zone-scalp-experiment-20261010.json").read_text())
    m={k:v for k,v in previous.items() if k!="candidates"}
    candidates=[]
    for side in ("BUY","SELL"):
        base=next(c for c in previous["candidates"] if c["id"]==f"zone_M5_M3_M1_{side}_confirm0")
        for profile,rr,hold,lock in (("baseline",1.5,45,False),("near_target",1.1,45,False),
                                   ("profit_lock",1.5,45,True),("fast_timeout",1.5,15,False)):
            c=json.loads(json.dumps(base))
            c.update(id=f"scalp_exit_{side}_{profile}",rr=rr,profile=profile)
            c["settings"].update(InpZoneMaxHoldMinutes=hold,InpZoneSessionBufferMinutes=105-hold,
                InpZoneEnableProfitLock=str(lock).lower(),InpZoneLockTriggerR=.75,InpZoneLockR=.05)
            candidates.append(c)
    m.update(candidates=candidates,additional_profiles_per_side=3,
        search_note="8 profiles including 2 reproductions; follows the 20 zone candidates and earlier research.",
        fixed_session_room_minutes=105,
        later_audit_policy="At most one per side: best eligible; if none, best sufficiently sampled failed profile for diagnostic only. Never promotes without development and later passes.",
        audit_rank="Maximize weaker-quarter stressed expectancy; candidate id tie-break",
        unchanged_entry=True,live_execution_enabled=False)
    return m

def audit_lock_rows(rows):
    for r in rows:
        side=int(r["side"])
        vals=[float(r[k]) for k in ("entry","initial_risk","bid","ask","old_sl","new_sl","trigger_r","lock_r")]
        if not all(math.isfinite(x) for x in vals): raise ValueError("nonfinite lock evidence")
        entry,risk,bid,ask,old,new,trigger,lock=vals
        if side not in (-1,1) or risk<=0 or bid<=0 or ask<bid or not 0<=lock<trigger:
            raise ValueError("invalid lock economics")
        liquidation=bid if side>0 else ask
        if side*(liquidation-entry)/risk+1e-6<trigger: raise ValueError("lock fired before trigger")
        if side*(new-old)<=0 or side*(liquidation-new)<=0: raise ValueError("stop worsened or crossed quote")
        realized=side*(new-entry)/risk
        if realized<0 or realized>lock+1e-6: raise ValueError("lock outside declared target")
    return dict(modifications=len(rows),causal_trigger_verified=True,monotonic_stop_verified=True)

def execute(c,start,end,phase):
    r=e.execute(c,start,end,phase)
    tag=Path(r["journal_path"]).stem.removeprefix("KatarinaFeatureJournal_")
    z=list(csv.DictReader(io.StringIO(e.read_text(r["zone_audit_path"])),delimiter=";"))
    if any(int(x["seconds_to_session_close"])<105*60 for x in z):
        raise ValueError("changed session entry eligibility")
    source=e.runner.COMMON/("KatarinaExitChanges_"+tag+".csv")
    rows=[]
    if source.exists():
        dest=Path(r["journal_path"]).parent/source.name
        shutil.copy2(source,dest)
        rows=list(csv.DictReader(io.StringIO(e.read_text(dest)),delimiter=";"))
        if any(x["run_tag"]!=tag for x in rows): raise ValueError("wrong lock audit run")
        r["lock_audit_path"]=str(dest);r["lock_audit_sha256"]=e.digest(dest)
    r["lock_integrity"]=audit_lock_rows(rows)
    if c["profile"]!="profit_lock" and rows: raise ValueError("unrequested stop modification")
    if c["profile"]=="profit_lock" and r["report"]["trades"] and not rows:
        raise ValueError("profit-lock candidate never exercised; investigate")
    (ART/phase/c["id"]/"result.json").write_text(json.dumps(r,indent=2)+"\n")
    return r

def main():
    if MANIFEST.exists(): raise ValueError("do not overwrite frozen experiment")
    MANIFEST.write_text(json.dumps(freeze(),indent=2)+"\n")
    m=json.loads(MANIFEST.read_text())
    development=[]
    for c in m["candidates"]:
        r=execute(c,m["train_from"],m["development_to"],"development")
        if c["profile"]=="baseline":
            expected=(64,"8.34") if c["side"]=="BUY" else (63,"31.66")
            if (r["report"]["trades"],r["report"]["net_profit"])!=expected:
                raise ValueError("baseline changed; stop before interpreting exit experiments")
        development.append(r)
        (ART/"development-results.json").write_text(json.dumps(development,indent=2)+"\n")
    if len({r["expert_sha256"] for r in development})!=1: raise ValueError("mixed binaries")
    summaries=[e.summarize(r,m) for r in development]
    choices=[]
    for side in ("BUY","SELL"):
        group=[s for s in summaries if s["side"]==side]
        eligible=[s for s in group if s["eligible"]]
        pool=eligible or [s for s in group if s["training"]["trades"]>=m["min_train"] and s["selection"]["trades"]>=m["min_selection"]]
        pool.sort(key=lambda s:(-min(s["training"]["expectancy_r"],s["selection"]["expectancy_r"]),s["candidate"]))
        if pool:
            choices.append(dict(side=side,candidate=pool[0]["candidate"],development_pass=pool[0]["eligible"],
                purpose="validation_candidate" if pool[0]["eligible"] else "rejected_candidate_diagnostic"))
    policy=dict(choices=choices,summaries=summaries,manifest_sha256=e.digest(MANIFEST),
        source_sha256=e.digest(Path(__file__)),live_execution_enabled=False)
    frozen=ROOT/"docs/validation/2026-10-10-scalp-exit-selection.json"
    if frozen.exists(): raise ValueError("existing policy")
    frozen.write_text(json.dumps(policy,indent=2)+"\n")
    print("FROZEN_EXIT_CHOICES",json.dumps(choices),flush=True)
    final=[]
    for choice in choices:
        c=next(c for c in m["candidates"] if c["id"]==choice["candidate"])
        r=execute(c,m["final_from"],m["final_to"],"later")
        met=stats(e.trade_rows(r),m["stress_r"])
        passed=met["trades"]>=m["min_selection"] and met["days"]>=m["min_days_per_window"] and met["net_r"]>0 and met["profit_factor"] is not None and met["profit_factor"]>=m["min_pf"]
        final.append(dict(choice=choice,run=r,stressed_metrics=met,later_pass=passed,
            decision="PAPER_RESEARCH_ONLY" if choice["development_pass"] and passed else "NO_TRADE"))
    out=dict(manifest_sha256=e.digest(MANIFEST),development=development,summaries=summaries,
        final=final,decision="PAPER_RESEARCH_ONLY" if any(x["decision"]=="PAPER_RESEARCH_ONLY" for x in final) else "NO_TRADE",
        live_execution_enabled=False,validated_strategy=False,october_data_used=False,
        limitations=["Jan-Jun development history reused extensively.","Jul-Sep was partly inspected in earlier research; not pristine unseen evidence.",
        "Rejected-development candidates remain rejected even if later audit is positive.","No combined BUY/SELL performance inferred from separate runs."])
    (ROOT/"docs/validation/2026-10-10-scalp-exit-results.json").write_text(json.dumps(out,indent=2)+"\n")
    print("EXIT_EXPERIMENT_COMPLETE",json.dumps(dict(final=[dict(side=x["choice"]["side"],profile=x["run"]["candidate"]["profile"],net=x["run"]["report"]["net_profit"],decision=x["decision"]) for x in final])),flush=True)

if __name__=="__main__": main()
