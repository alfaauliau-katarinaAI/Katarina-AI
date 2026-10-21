"""Predeclared four UTC session blocks, historical 2025 to 2026.
No optimized time-zone cutoff; no model promotion or broker orders.
"""
import json
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
ROOT=Path(r"C:\KatarinaDev\artifacts\historical-brain")
r=json.loads((ROOT/"backtest_adaptive_brain_v2_from_2025.json").read_text(encoding="utf-8"))
quarters={0:"00-06_UTC",1:"06-12_UTC",2:"12-18_UTC",3:"18-24_UTC"}
full={}
for item in r["symbol_results"]:
  sym=item["symbol"]
  if "trades" not in item:continue
  buckets=defaultdict(list)
  modebuckets=defaultdict(list)
  for tr in item["trades"]:
    hour=datetime.fromtimestamp(tr["time"],tz=timezone.utc).hour
    block=quarters[hour//6]
    buckets[(tr["period"],block)].append(tr["R"])
    modebuckets[(tr["period"],block,tr["setup"])].append(tr["R"])
  full[sym]={
    "sessions":{str(y)+"|"+q:{"n":len(a),"mean_R":sum(a)/len(a)}
       for (y,q),a in sorted(buckets.items())},
    "playbooks":{str(y)+"|"+q+"|"+mode:{"n":len(a),"mean_R":sum(a)/len(a)}
       for (y,q,mode),a in sorted(modebuckets.items())},
  }
eligible=[]
for symbol,g in full.items():
  for session in quarters.values():
    for mode in ["TREND_PULLBACK","RANGE_FADE","BREAKOUT_RETEST"]:
      a=g["playbooks"].get("2025|"+session+"|"+mode)
      b=g["playbooks"].get("2026|"+session+"|"+mode)
      if a is not None and b is not None and a["n"]>=50 and b["n"]>=50:
         eligible.append({"symbol":symbol,"session":session,"mode":mode,
             "n_2025":a["n"],"mean_2025":a["mean_R"],
             "n_2026":b["n"],"mean_2026":b["mean_R"],
             "positive_both":a["mean_R"]>0 and b["mean_R"]>0})
dest=ROOT/"backtest_2025_2026_sessionality_audit.json"
out={"kind":"KATARINA_fixed_six_hour_UTC_time_of_day_diagnostic",
     "fixed_UTC_buckets":list(quarters.values()),
     "not_exchange_local_DaylightSavings_calibrated":True,
     "criteria":"at least 50 fills in each year and positive mean R both years",
     "eligible_pairs":len(eligible),"positive_both":sum(x["positive_both"] for x in eligible),
     "candidates":eligible,"by_symbol":full,
     "not_an_unseen_holdout":True,"model_promotion_allowed":False,
     "live_execution_enabled":False}
dest.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"eligible_cells":len(eligible),
  "positive_both":sum(x["positive_both"] for x in eligible),
  "positive_both_cells":[x for x in eligible if x["positive_both"]],
  "least_negative_2025":sorted(eligible,key=lambda x:x["mean_2025"],reverse=True)[:12],
  "output":str(dest)},indent=2))
