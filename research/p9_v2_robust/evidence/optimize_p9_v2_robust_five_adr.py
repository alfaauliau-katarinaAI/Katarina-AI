"""P9 V2 FIVE-ENGINE core + V3 causal Growth/Defensive routing (ROBUST, no opposite methods).
Optimize with causal ADR risk filters vs matched-static P9 V2 five original.
NO broker orders; original P9 V2 and P7 SHA locked and unchanged.
2024-2025 was mined repeatedly, 2026 has been seen (not untouched OOS).
"""
from pathlib import Path
from collections import Counter
import itertools,hashlib,json
ROOT=Path(r"C:\Katarina\research")
OUT=ROOT/"p9-v2-robust-max-integration-20261118";OUT.mkdir(exist_ok=True)
ref=ROOT/"p9-v31-adr-risk-optimization-20261118"/"optimize_ADR_conditional_risk.py"
namespace={"__file__":str(ref)}
exec(compile(ref.read_text(encoding="utf8").split("# Two-stage: scan higher risk envelope",1)[0],str(ref),"exec"),namespace)
ev=namespace["evaluate"];w=namespace["w"];policy=namespace["policy_map"];KEYS=namespace["KEYS"]
CORE=("XAU_H1_BUY","XAU_H4_BUY","NAS_H4_SELL","EUR_H4_BUY","CHF_H4_BUY")
assert set(CORE).issubset(KEYS)
w.PREFIX=CORE
# Exact 5-engine scope: no EUR SELL, CHF SELL, XAU SELL, NAS BUY.
assert list(w.PREFIX)==list(CORE)
# Compare raw P9 V2 original 5 vs V2-derived robust adaptive core (V3 variant selectors)
raw=json.loads((ROOT/"backtest_20240101_20261118"/"FRESH_REBUILT_P9_V3_V31_EVENTS.json").read_text(encoding="utf8"))["events"]
from datetime import datetime,timezone
def historical_overnight(start,end,sym):
 if end<=start:return 0
 triple=int(w.base.ex.SPEC[sym]["swap_rollover3days"])
 units=0
 for t in range((int(start)//86400+1)*86400,int(end),86400):
  weekday=datetime.fromtimestamp(t,timezone.utc).weekday()
  prev=(weekday-1)%7
  if prev<5:units+=3 if (prev+1)%7==triple else 1
 return units

original={k:w.EVENTS[k] for k in CORE}
def variants(original_variant):
 for k in CORE:
  if original_variant:
   w.EVENTS[k]=[{**z,"baseR":float(z["R"]),"overnight_units":historical_overnight(z["entry"],z["exit"],z["symbol"])} for z in raw[k]["P9_V2"] if z["entry"]>=1722470400]
  else:w.EVENTS[k]=original[k]
# Native risk 0.25% per entry, max2 groups
portfolio_ref={}
for label,orig in (("V2_FIVE_ORIGINAL",True),("V2_DERIVED_ROBUST_FIVE",False)):
 variants(orig)
 portfolio_ref[label]=ev((.25,)*4,"STATIC",(0.,.4,.5,.6),full=True)
 print("FIVE_REF",label,[(s,portfolio_ref[label][str(s)]["monthly"],portfolio_ref[label][str(s)]["closed_dd"],
 portfolio_ref[label][str(s)]["trades"]) for s in (0.,.4,.5,.6)],flush=True)
variants(False)
# Moderate ranges through higher-risk stress for research only.
X=[.25,.5,.75,1.,1.5,2.]
N=[.25,.5,1.,1.5,2.,3.,4.]
E=[.25,.5,1.]
C=[.25,.5,1.]
weights=list(itertools.product(X,N,E,C))
policies=["STATIC","CUT_LOW_50","CUT_LOW_50_HIGH125","CUT_LOW_75_HIGH125",
 "CUT_LOW_50_HIGH150","CUT_LOW_75_HIGH150","NAS_LOW_50_ONLY","NAS_LOW_50_HIGH150",
 "XAU_LOW_50_ONLY","ABS_EXP_LOW_50_HIGH125","ABS_EXP_LOW_75_HIGH125",
 "ABS_EXP_LOW_50_HIGH150","ABS_EXP_LOW_75_HIGH150",
 "ABS_EXP_NAS_LOW50_HIGH150","LOW_CUT_50_HIGH075"]
records=[]
for i,pol in enumerate(policies):
 for weight in weights:
  r=ev(weight,pol,(0.,.6))
  a=r["0.0"];s=r["0.6"]
  feasible=(a["training_net17mo"]>0 and s["training_net17mo"]>0 and
      s["monthly"]>0 and a["closed_dd"]<=6 and s["closed_dd"]<=8
      and a["dd_veto"]==0 and s["dd_veto"]==0 and a["trades"]>=120
      and a["max_simultaneous_initial_sl_budget_pct"]<=6.5
      and a["max_risk_pct_entry"]<=5)
  score=(.35*a["training_net17mo"]+.65*s["training_net17mo"]-
         100*s["closed_dd"]-50*a["closed_dd"]) if feasible else -1e9
  records.append({"risk_pct":list(weight),"adr_policy":pol,"feasible_pre":feasible,
   "train_score":round(score,2),"normal":a,"stress06":s})
 if (i+1)%3==0:
  print("FIVE_GRID_PROGRESS",i+1,"of",len(policies),
    "tested",len(records),"feasible",sum(z["feasible_pre"] for z in records),flush=True)
  (OUT/"PARTIAL_SCAN.json").write_text(json.dumps({"scanned":len(records),
    "feasible":sum(z["feasible_pre"] for z in records)},ensure_ascii=False)+"\n",encoding="utf8")
eligible=[r for r in records if r["feasible_pre"]]
# Check all costs for provisional; robust original spec must pass 4 scenarios
rank=[]
for j,z in enumerate(eligible):
 r=ev(z["risk_pct"],z["adr_policy"],(.4,.5))
 x=r["0.4"];y=r["0.5"];a=z["normal"];s=z["stress06"]
 strict=(x["monthly"]>0 and y["monthly"]>0 and
  x["closed_dd"]<=8 and y["closed_dd"]<=8 and
  x["dd_veto"]==0 and y["dd_veto"]==0)
 row={**z,"stress04":x,"stress05":y,"strict":strict}
 if strict:rank.append(row)
 if (j+1)%80==0:print("FIVE_STRESS_AUDIT_PROGRESS",j+1,"of",len(eligible),flush=True)
rank.sort(key=lambda z:-z["train_score"])
print("FIVE_GRID_COMPLETE",len(records),"pre",len(eligible),"strict",len(rank),flush=True)
for label,zs in (("TRAIN_TOP",rank),("NORMAL_TOP",sorted(rank,key=lambda z:-z["normal"]["monthly"])),
                 ("STRESS_TOP",sorted(rank,key=lambda z:-z["stress06"]["monthly"]))):
 for i,z in enumerate(zs[:12],1):
  print(label,i,z["adr_policy"],z["risk_pct"],"train_score",z["train_score"],
  "normal",z["normal"]["monthly"],"DD",z["normal"]["closed_dd"],
  "minus04",z["stress04"]["monthly"],"minus05",z["stress05"]["monthly"],
  "minus06",z["stress06"]["monthly"],"DD06",z["stress06"]["closed_dd"],
  "2026normal",z["normal"]["diag_2026_net10mo"],flush=True)
short={}
focus=rank[:15]+sorted(rank,key=lambda z:-z["normal"]["monthly"])[:5]+sorted(rank,key=lambda z:-z["stress06"]["monthly"])[:5]
focus +=[{"adr_policy":"STATIC","risk_pct":[.25,.25,.25,.25]},
         {"adr_policy":"STATIC","risk_pct":[.75,3.,.25,.5]},
         {"adr_policy":"STATIC","risk_pct":[.5,3.,.25,.25]}]
seen=set()
for z in focus:
 key=(z["adr_policy"],tuple(z["risk_pct"]))
 if key in seen:continue
 seen.add(key)
 short[z["adr_policy"]+"|"+",".join(map(str,z["risk_pct"]))]=ev(z["risk_pct"],z["adr_policy"],(0.,.4,.5,.6,.7),full=True)
# Analyze P9 original and V2-derived robust at exact matched weights without ADR
for lab,orig in (("ORIGINAL",True),("ROBUST",False)):
 variants(orig)
 short["EQUAL_025_"+lab]=ev((.25,)*4,"STATIC",(0.,.4,.5,.6,.7),full=True)
variants(False)
lock=json.loads((ROOT/"p9-opposite-challenger-20261117"/"FROZEN_P9_V2"/"P9_V2_LOCK.json").read_text(encoding="utf8"))
assert all(hashlib.sha256((ROOT/"p9-hybrid-optimization-20261117"/f).read_bytes()).hexdigest()==h for f,h in lock["sha256"].items())
p7=json.loads((ROOT/"p9-hybrid-optimization-20261117"/"P7_FROZEN_REFERENCE"/"P7_LOCKED_FORMAT.json").read_text(encoding="utf8"))
assert all(hashlib.sha256((ROOT/"p7-fixed-risk-strategy-20261117"/f).read_bytes()).hexdigest()==h for f,h in p7["files_sha256"].items())
report={"status":"P9_V2_ROBUST_FIVE_ADR_RISK_RESEARCH_COMPLETE",
  "scope":{"original_five_engines":list(CORE),"entry_variant":"V3_ROUTED_V2_GROWTH_DEFENSIVE_NO_OPPOSITES",
  "historical_months_full":27,"initial_usd":10000,"max_open":2,
  "trading_allowed":False,"live_risk_cap_pct":.25},
  "reference_cap025":portfolio_ref,
  "scan":{"ADR_policies":policies,"risk_vectors":len(weights),
   "configurations":len(records),"initial_qualified":len(eligible),"all_cost_qualified":len(rank)},
  "candidate_rank_train":rank[:60],
  "candidate_rank_normal":sorted(rank,key=lambda z:-z["normal"]["monthly"])[:25],
  "candidate_rank_stress":sorted(rank,key=lambda z:-z["stress06"]["monthly"])[:25],
  "all_grid":records,"full_shortlist":short,
  "warnings":["The V2-derived V3 routing is not the locked original V2 algorithm; remains a challenger",
    "Aug2024–Oct2026 retrospectively mined; not independent 2026 OOS",
    "ADR from H1 strictly previous completed trading days; session-time alignment pending broker verification",
    "Current margin snapshot; historical Bid/Ask H1 first-touch, not native MT5 Every tick based on real ticks",
    "Closed DD not intrabar floating equity; gaps and slippage not fully simulated",
    "All >0.25% risks are deliberately research-only. Zero broker trades."],
  "P9_locked":True,"P7_locked":True,"production_change":False,"broker_orders":0}
(OUT/"P9_V2_ROBUST_FIVE_ADR_RISK_SCAN.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
print("P9_V2_ROBUST_RESEARCH_SAVED",len(records),len(rank),len(short),flush=True)
