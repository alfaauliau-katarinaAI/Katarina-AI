"""Fixed-rule playbook retrospective evidence across distinct archive windows.

Day-block bootstrap prevents treating every trade on same day as iid. No
multiple-testing adjustment, no broker fill study, no risk activation.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict,Counter
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from random import Random
from statistics import mean

def bootstrap_days(rows,seed=11062026,repetitions=2000):
    if not rows:return None
    groups=defaultdict(list)
    for item in rows:
        groups[item["entry_signal_close_utc"][:10]].append(item["R"])
    days=sorted(groups)
    rand=Random(seed)
    values=[]
    for i in range(repetitions):
        sample=[v for _ in days for v in groups[rand.choice(days)]]
        values.append(mean(sample))
    values.sort()
    return [values[int(.025*(repetitions-1))],values[int(.975*(repetitions-1))]]

def summarize(paths):
    manifest=[]
    all_rows=[]
    seen=set()
    diagnostics=defaultdict(Counter)
    for path in paths:
        raw=Path(path).read_bytes()
        obj=json.loads(raw)
        if obj.get("kind")!="distinct_per_symbol_research_playbooks_v1" or (
                obj.get("live_execution_enabled") is not False or
                obj.get("model_promotion_allowed") is not False):
            raise ValueError("bad_source")
        manifest.append(dict(path=str(path),sha256=sha256(raw).hexdigest()))
        for key,err in obj["diagnostics"].items():
            if isinstance(err,dict):
                for name,count in err.items():
                    if isinstance(count,int):diagnostics[key][name]+=count
        for x in obj["trials"]:
            if x["slippage_each_side_ticks"]!=1:continue
            key=(x["symbol"],x["research_window"],x["quote_entry_utc"])
            if key in seen:raise ValueError("duplicate_trade")
            seen.add(key)
            all_rows.append(x)
    symbols=sorted({x["symbol"] for x in all_rows})
    report={}
    for symbol in symbols:
        group=[e for e in all_rows if e["symbol"]==symbol]
        windows={}
        for name in sorted({e["research_window"] for e in group}):
            subset=[e for e in group if e["research_window"]==name]
            windows[name]=dict(n=len(subset),n_closed=sum(x["status"]=="CLOSED" for x in subset),
                 mean_R=mean(x["R"] for x in subset if x["status"]=="CLOSED") if (
                   any(x["status"]=="CLOSED" for x in subset)) else None)
        complete=[e for e in group if e["status"]=="CLOSED"]
        r=[e["R"] for e in complete]
        pos=sum(x for x in r if x>0)
        neg=-sum(x for x in r if x<0)
        report[symbol]=dict(family=complete[0]["family"] if complete else None,
            candidate_paths=len(group),completed=len(complete),
            missing=Counter(x["status"] for x in group if x["status"]!="CLOSED"),
            UTC_days=len(set(e["entry_signal_close_utc"][:10] for e in complete)),
            mean_R=mean(r) if r else None,
            day_block_bootstrap_95pct_CI_R=bootstrap_days(complete),
            profit_factor=pos/neg if neg else None,
            pct_profitable=sum(x>0 for x in r)/len(r) if r else None,
            mean_MFE_R=mean(e["mfe_R"] for e in complete) if complete else None,
            mean_MAE_R=mean(e["mae_R"] for e in complete) if complete else None,
            monthly=windows,model_promotion_allowed=False)
    return dict(kind="locked_symbol_specific_retrospective_summary",
      input_sha256=manifest,
      analysis_note="Bootstrap CI excludes multiple-testing and prior research reuse",
      old_history_not_true_prospective_out_of_sample=True,
      reestimated_parameters=False,
      untried_instruments_not_inferred_from_other_symbols=True,
      fee_schedule_not_realized_fills=True,
      execute_live=False,model_promotion_allowed=False,
      by_symbol=report,per_window_diagnostics={k:dict(v) for k,v in diagnostics.items()})

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",nargs="+",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    out=Path(args.output)
    if out.exists():raise FileExistsError("immutable")
    response=summarize(args.report)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(response,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    for symbol,v in response["by_symbol"].items():
        print(symbol,"n",v["completed"],"mean_R",v["mean_R"],
            "CI_95",v["day_block_bootstrap_95pct_CI_R"],
            "PF",v["profit_factor"],"windows",v["monthly"])
    print("REPORT",out)
if __name__=="__main__":
    main()
