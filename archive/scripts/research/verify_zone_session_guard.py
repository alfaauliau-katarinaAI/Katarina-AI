"""Execution-risk verification, not another strategy selection or promotion."""
import csv,io,json,shutil
from pathlib import Path
import run_zone_scalp_experiments as e

def main():
    e.ART=Path(r"C:\KatarinaDev\artifacts\mt5\zone-session-experiments")
    e.runner.ART=e.ART
    previous=json.loads((e.ROOT/"docs/validation/2026-10-10-fast-zone-scalp-results.json").read_text())
    manifest=json.loads((e.ROOT/"config/fast-zone-scalp-experiment-20261010.json").read_text())
    out=[]
    for side in ("BUY","SELL"):
        cid=f"zone_M5_M3_M1_{side}_confirm0"
        c=dict(next(r["candidate"] for r in previous["development"] if r["candidate"]["id"]==cid))
        c["id"]+="_session_guard"
        r=e.execute(c,manifest["train_from"],manifest["development_to"],"verification")
        rows=list(csv.DictReader(io.StringIO(e.read_text(r["zone_audit_path"])),delimiter=";"))
        if any(int(z["seconds_to_session_close"])<(int(z["max_hold_minutes"])+5)*60 for z in rows):
            raise ValueError("entry too close to session end")
        tag=Path(r["journal_path"]).stem.removeprefix("KatarinaFeatureJournal_")
        source=e.runner.COMMON/("KatarinaZoneSessions_"+tag+".csv")
        target=Path(r["journal_path"]).parent/source.name
        shutil.copy2(source,target)
        session_rows=list(csv.DictReader(io.StringIO(e.read_text(target)),delimiter=";"))
        summary=e.summarize(r,manifest)
        late=[]
        for row in csv.DictReader(io.StringIO(e.read_text(r["journal_path"])),delimiter=";"):
            duration=(e._clock(row["exit_time"],upper=True)-e._clock(row["entry_time"],upper=False))/60e9
            if duration>46:
                late.append({k:row[k] for k in ("entry_time","exit_time","net_profit","initial_risk_cash","exit_deal_reason")})
        out.append(dict(run=r,summary=summary,broker_sessions=session_rows,
            sessions_sha256=e.digest(target),entry_session_room_verified=True,
            late_exits=late,promotion="NO_TRADE"))
        print("SESSION_CHECK",json.dumps(dict(side=side,trades=r["report"]["trades"],net=r["report"]["net_profit"],late_exits=late)),flush=True)
    report=dict(checks=out,live_execution_enabled=False,validated_strategy=False,
        rationale="Session-room execution fix after a 138-minute position in 7.135; not reselected using new outcomes.",
        caveat="Current broker session metadata cannot guarantee historical schedules or unforeseen quote gaps.")
    (e.ROOT/"docs/validation/2026-10-10-zone-session-verification.json").write_text(json.dumps(report,indent=2)+"\n")

if __name__=="__main__": main()
