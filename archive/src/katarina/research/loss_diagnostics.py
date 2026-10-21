"""Descriptive journal/report audit. No counterfactual profitability claims."""
import csv
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path

def read_text(path):
    raw=Path(path).read_bytes()
    return raw.decode("utf-16" if raw[:2] in (b"\xff\xfe",b"\xfe\xff") else "utf-8-sig")

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=="tr": self.row=[]
        if tag in ("td","th") and self.row is not None: self.cell=""
    def handle_data(self,data):
        if self.cell is not None: self.cell+=data
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None:
            self.row.append(self.cell.strip()); self.cell=None
        if tag=="tr" and self.row is not None:
            self.rows.append(self.row); self.row=None

def report_stats(path):
    p=TableParser(); p.feed(read_text(path))
    fields={}
    for row in p.rows:
        for i,x in enumerate(row[:-1]):
            if x.endswith(":"): fields[x[:-1]]=row[i+1]
    deal_rows=[r for r in p.rows if len(r)==13 and r[4] in ("in","out","in/out","out by")]
    def total(i): return str(sum((Decimal(r[i].replace(" ","")) for r in deal_rows),Decimal(0)))
    return {"trades":int(fields["Total Trades"].replace(" ","")),
            "net_profit":fields["Total Net Profit"].replace(" ",""),
            "history_quality":fields.get("History Quality"),"cash_profit_factor":fields.get("Profit Factor"),
            "equity_drawdown":fields.get("Equity Drawdown Maximal"),
            "deal_commission":total(8),"deal_swap":total(9),"deal_profit":total(10),
            "exit_comments":dict(__import__("collections").Counter(
                "SL" if r[12].startswith("sl ") else "TP" if r[12].startswith("tp ") else "OTHER"
                for r in deal_rows if r[4] in ("out","out by"))),
            "report_sha256":sha256(Path(path).read_bytes()).hexdigest()}

def summary(rows):
    pnl=[Decimal(r["net_profit"]) for r in rows]
    positive=[p for p in pnl if p>0]; negative=[p for p in pnl if p<0]
    avg_win=sum(positive)/len(positive) if positive else None
    avg_loss=-sum(negative)/len(negative) if negative else None
    risk=[float(r["net_profit"])/float(r["initial_risk_cash"]) for r in rows]
    out={"trades":len(rows),"net_usd":str(sum(pnl,Decimal(0))),
         "win_rate":len(positive)/len(rows) if rows else None,
         "mean_win_usd":str(avg_win) if avg_win is not None else None,
         "mean_loss_usd":str(avg_loss) if avg_loss is not None else None,
         "realized_breakeven_win_rate":float(avg_loss/(avg_win+avg_loss)) if avg_win and avg_loss else None,
         "expectancy_r":sum(risk)/len(risk) if risk else None}
    if rows:
        out["mean_holding_minutes"]=sum((datetime.strptime(r["exit_time"],"%Y.%m.%d %H:%M")-
             datetime.strptime(r["entry_time"],"%Y.%m.%d %H:%M")).total_seconds()/60 for r in rows)/len(rows)
        out["mean_spread_to_initial_risk"]=sum(float(r["spread_atr"])/1.3 for r in rows)/len(rows)
    if rows and "mae_r" in rows[0]:
        losing=[r for r in rows if Decimal(r["net_profit"])<0]
        out["losers_reached_1r_count"]=sum(float(r["mfe_r"])>=1 for r in losing)
        out["losers_count"]=len(losing)
        out["mean_mae_r"]=sum(float(r["mae_r"]) for r in rows)/len(rows)
        out["mean_mfe_r"]=sum(float(r["mfe_r"]) for r in rows)/len(rows)
    return out

def audit(journal,report):
    rows=list(csv.DictReader(StringIO(read_text(journal)),delimiter=";"))
    stats=report_stats(report)
    if len(rows)!=stats["trades"] or abs(sum(Decimal(r["net_profit"]) for r in rows)-Decimal(stats["net_profit"]))>Decimal(".005")*len(rows):
        raise ValueError("journal/report reconciliation failed")
    groups={}
    for field in ("side","reason","session","htf_regime","context_regime"):
        grouped=defaultdict(list)
        for r in rows: grouped[r[field]].append(r)
        groups[field]={k:summary(v) for k,v in sorted(grouped.items())}
    return dict(report=stats,overall=summary(rows),groups=groups,
       journal_sha256=sha256(Path(journal).read_bytes()).hexdigest(),
       limitations=["Descriptive partitions; do not select a strategy from these inspected outcomes.",
       "Spread/risk proxy assumes baseline 1.3 ATR stop; spread is already reflected in fills.",
       "MAE/MFE while position exists cannot infer post-stop recovery.",
       "No claim that wider stops or lower targets work without a new execution backtest."])

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("journal");p.add_argument("report");p.add_argument("output")
    a=p.parse_args();result=audit(a.journal,a.report)
    Path(a.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"overall":result["overall"],"side":result["groups"]["side"],"report":result["report"]},indent=2))
