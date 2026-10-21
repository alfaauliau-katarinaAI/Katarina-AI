"""Two explicitly defined entry families; equal cash-risk ceiling and exit rules."""
import csv,io,json,shutil,math
from pathlib import Path
import run_zone_scalp_experiments as e
from katarina.intelligence.strategy_selector import stats

ROOT=e.ROOT
ART=Path(r"C:\KatarinaDev\artifacts\mt5\scalp-entry-comparison")
e.runner.ART=ART
MANIFEST=ROOT/"config/scalp-entry-comparison-20261010.json"

def freeze():
    m=e.freeze()
    candidates=[]
    for family,method in (("trend_reclaim",8),("range_sweep",9)):
        for side in ("BUY","SELL"):
            candidates.append(dict(id=f"m5_{family}_{side}",family=family,side=side,
                method=method,min_adx=0,sl_atr=1.3,rr=1.5,period="M1",
                settings=dict(InpFastEMA=20,InpContextTF=5,InpContextFastEMA=20,
                    InpContextSlowEMA=50,InpContextADXPeriod=14,
                    InpZoneRiskCash=10,InpZoneMaxHoldMinutes=45,InpZoneSessionBufferMinutes=60,
                    InpZoneEnableProfitLock="false",InpZoneUseConfirmation="false")))
    m.update(candidates=candidates,
        rationale="Zone entry remained weak under three separate exit changes. Compare trend-following reclaim and low-ADX range sweep.",
        additional_search_candidates=4,
        context="Closed M5 EMA20/EMA50 and ADX14; trend ADX>=20, range ADX<=20.",
        entry="M1 EMA20 reclaim through preceding candle high/low, or bounded 20-bar liquidity sweep.",
        selection_bias_note="Designed after earlier zone/exit research; development history reused.",
        later_audit="Best eligible per side, else best sufficiently sampled failed candidate for diagnostic only.",
        live_execution_enabled=False)
    return m

def audit_fills(rows,trade_count,method):
    if len(rows)!=trade_count: raise ValueError("fill count mismatch")
    for r in rows:
        side=int(r["side"]);entry_time=int(r["entry_time"]);signal=int(r["signal_time"]);known=int(r["context_known"])
        if not 0<signal<entry_time or not 0<known<=entry_time: raise ValueError("future context or incomplete entry bar")
        if int(r["method"])!=method or r["context_tf"]!="PERIOD_M5": raise ValueError("wrong strategy context")
        risk,budget,entry,sl,atr,adx=(float(r[k]) for k in ("initial_risk_cash","risk_budget","entry","sl","atr","context_adx"))
        if not all(math.isfinite(x) for x in (risk,budget,entry,sl,atr,adx)): raise ValueError("nonfinite fill")
        if side not in (-1,1) or not 0<risk<=budget+.02 or atr<=0 or side*(entry-sl)<=0:
            raise ValueError("invalid risk")
        if abs(abs(entry-sl)/atr-1.3)>.02: raise ValueError("wrong initial stop distance")
        if int(r["seconds_to_session_close"])<105*60: raise ValueError("insufficient session room")
        if method==8 and (adx<20 or r["context_regime"]!=("UP" if side>0 else "DOWN")):
            raise ValueError("trend gate violated")
        if method==9 and not 0<=adx<=20: raise ValueError("range gate violated")
    return dict(trades=trade_count,causal_context=True,risk_verified=True,regime_verified=True)

def execute(c,start,end,phase):
    r=e.runner.run(c,start,end,phase)
    tag=Path(r["journal_path"]).stem.removeprefix("KatarinaFeatureJournal_")
    source=e.runner.COMMON/("KatarinaScalpAudit_"+tag+".csv")
    rows=[]
    if source.exists():
        target=Path(r["journal_path"]).parent/source.name
        shutil.copy2(source,target)
        rows=list(csv.DictReader(io.StringIO(e.read_text(target)),delimiter=";"))
        if any(x["run_tag"]!=tag for x in rows): raise ValueError("wrong fill tag")
        r["fill_audit_path"]=str(target);r["fill_audit_sha256"]=e.digest(target)
    r["fill_integrity"]=audit_fills(rows,r["report"]["trades"],c["method"])
    (ART/phase/c["id"]/"result.json").write_text(json.dumps(r,indent=2)+"\n")
    return r

def main():
    if MANIFEST.exists(): raise ValueError("existing frozen experiment")
    MANIFEST.write_text(json.dumps(freeze(),indent=2)+"\n")
    m=json.loads(MANIFEST.read_text())
    development=[]
    for c in m["candidates"]:
        development.append(execute(c,m["train_from"],m["development_to"],"development"))
        (ART/"development-results.json").write_text(json.dumps(development,indent=2)+"\n")
    summaries=[e.summarize(r,m) for r in development]
    choices=[]
    for side in ("BUY","SELL"):
        group=[s for s in summaries if s["side"]==side]
        eligible=[s for s in group if s["eligible"]]
        pool=eligible or [s for s in group if s["training"]["trades"]>=m["min_train"] and s["selection"]["trades"]>=m["min_selection"]]
        pool.sort(key=lambda s:(-min(s["training"]["expectancy_r"],s["selection"]["expectancy_r"]),s["candidate"]))
        if pool: choices.append(dict(side=side,candidate=pool[0]["candidate"],development_pass=pool[0]["eligible"],
            purpose="validation_candidate" if pool[0]["eligible"] else "rejected_candidate_diagnostic"))
    policy=dict(choices=choices,summaries=summaries,manifest_sha256=e.digest(MANIFEST),
        source_sha256=e.digest(Path(__file__)),live_execution_enabled=False)
    frozen=ROOT/"docs/validation/2026-10-10-scalp-entry-selection.json"
    if frozen.exists(): raise ValueError("existing frozen choices")
    frozen.write_text(json.dumps(policy,indent=2)+"\n")
    print("ENTRY_FROZEN_CHOICES",json.dumps(choices),flush=True)
    final=[]
    for choice in choices:
        c=next(c for c in m["candidates"] if c["id"]==choice["candidate"])
        r=execute(c,m["final_from"],m["final_to"],"later")
        met=stats(e.trade_rows(r),m["stress_r"])
        passed=met["trades"]>=m["min_selection"] and met["days"]>=m["min_days_per_window"] and met["net_r"]>0 and met["profit_factor"] is not None and met["profit_factor"]>=m["min_pf"]
        final.append(dict(choice=choice,run=r,stressed_metrics=met,later_pass=passed,
            decision="PAPER_RESEARCH_ONLY" if choice["development_pass"] and passed else "NO_TRADE"))
    out=dict(manifest_sha256=e.digest(MANIFEST),development=development,summaries=summaries,final=final,
        decision="PAPER_RESEARCH_ONLY" if any(x["decision"]=="PAPER_RESEARCH_ONLY" for x in final) else "NO_TRADE",
        live_execution_enabled=False,validated_strategy=False,october_data_used=False,
        limitation="Reused historical development and partly inspected later period; no prospective proof.")
    (ROOT/"docs/validation/2026-10-10-scalp-entry-results.json").write_text(json.dumps(out,indent=2)+"\n")
    print("ENTRY_COMPARISON_COMPLETE",json.dumps(dict(final=[dict(side=x["choice"]["side"],candidate=x["choice"]["candidate"],net=x["run"]["report"]["net_profit"],decision=x["decision"]) for x in final])),flush=True)

if __name__=="__main__":main()
