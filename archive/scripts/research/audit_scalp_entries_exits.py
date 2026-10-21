"""Descriptive audit only: excursions stop at actual exit, not counterfactual labels."""
import csv,io,json,sys,hashlib
from pathlib import Path
from statistics import mean,median
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from katarina.research.loss_diagnostics import read_text
ROOT=Path(__file__).resolve().parents[2]

def metrics(rows):
    winners=[r for r in rows if float(r["net_profit"])>0]
    losers=[r for r in rows if float(r["net_profit"])<0]
    def summary(group,key):
        a=[float(r[key]) for r in group if r.get(key) not in (None,"","NA","UNKNOWN")]
        return dict(count=len(a),mean=mean(a) if a else None,median=median(a) if a else None)
    return dict(trades=len(rows),net_usd=round(sum(float(r["net_profit"]) for r in rows),2),
        net_r=sum(float(r["net_profit"])/float(r["initial_risk_cash"]) for r in rows),
        winners=len(winners),losers=len(losers),
        exits=dict(Counter(r.get("exit_deal_reason") for r in rows)),
        loser_mfe=summary(losers,"mfe_r"),winner_mae=summary(winners,"mae_r"),
        loser_reached={str(level):sum(float(r["mfe_r"])>=level for r in losers) for level in (.25,.5,.75,1.,1.2)},
        winner_adverse={str(level):sum(float(r["mae_r"])>=level for r in winners) for level in (.25,.5,.75)},
        spread_atr=summary(rows,"spread_atr"))

def main():
    receipt=json.loads((ROOT/"docs/validation/2026-10-10-zone-session-buffer-verification.json").read_text())
    out=[]
    for check in receipt["checks"]:
        run=check["run"];p=Path(run["journal_path"])
        assert hashlib.sha256(p.read_bytes()).hexdigest()==run["journal_sha256"]
        rows=list(csv.DictReader(io.StringIO(read_text(p)),delimiter=";"))
        side=run["candidate"]["side"]
        groups={key:{v:metrics([r for r in rows if r.get(key)==v]) for v in sorted({r.get(key,"") for r in rows})}
                for key in ("context_regime","session")}
        periods={name:metrics([r for r in rows if a<=r["entry_time"]<b]) for name,a,b in
            (("Jan-Mar","2026.01.01","2026.04.01"),("Apr-Jun","2026.04.01","2026.07.01"))}
        out.append(dict(side=side,source_sha256=run["journal_sha256"],overall=metrics(rows),
                        periods=periods,groups=groups))
        print(side,json.dumps(out[-1]["overall"]),flush=True)

    result=dict(audits=out,selection_data="Jan-Jun reused development history",
        limitations=["MAE/MFE do not identify intratrade ordering of extrema.",
        "Excursions are censored at the existing exit; no inferred result for a different stop/target.",
        "Groups are descriptive and small; no regime filter is promoted from this audit."],
        live_execution_enabled=False)
    (ROOT/"docs/validation/2026-10-10-scalp-entry-exit-audit.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
