"""Hybrid P9 V2 Balanced + P9 V3.1 Robust systematic historical replay.
Offline 27-month replay. All knobs optimised on PRE-2026 training only; 2026
is already-mined historical diagnostic, NOT valid untouched hold-out.
No MT5 orders or production/repo writes. Closed DD not intra-position equity.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,itertools,hashlib,time,csv,statistics,collections
BASE=Path(r"C:\Katarina\research")
OUT=BASE/"p9-v2-v31-robust-hybrid-search-20261119";OUT.mkdir(exist_ok=True)
src=BASE/"p9-v31-adr-risk-optimization-20261118"/"optimize_ADR_conditional_risk.py"
ns={"__file__":str(src)}
exec(compile(src.read_text(encoding="utf8").split("# Two-stage: scan higher risk envelope",1)[0],str(src),"exec"),ns)
w=ns["w"];ev=ns["evaluate"]
raw=json.loads((BASE/"backtest_20240101_20261118"/"FRESH_REBUILT_P9_V3_V31_EVENTS.json").read_text(encoding="utf8"))["events"]
CORE=("XAU_H1_BUY","XAU_H4_BUY","NAS_H4_SELL","EUR_H4_BUY","CHF_H4_BUY")
VARIABLE=CORE[:3]
EXTRA=("EUR_H1_SELL","CHF_H4_SELL","XAU_H1_SELL")
EIGHT=CORE+EXTRA
assert set(EIGHT)==set(ns["KEYS"]) and len(EIGHT)==8
assert all(w.GROUPS[k]==("XAU" if k.startswith("XAU") else "NAS" if k.startswith("NAS") else "EUR" if k.startswith("EUR") else "CHF") for k in EIGHT)
def overnight(start,end,sym):
 # Prior validated independent frozen-V2 replay cost convention.
 if end<=start:return 0
 triple=int(w.base.ex.SPEC[sym]["swap_rollover3days"])
 units=0
 for t in range((int(start)//86400+1)*86400,int(end),86400):
  weekday=datetime.fromtimestamp(t,timezone.utc).weekday()
  prev=(weekday-1)%7
  if prev<5:units+=3 if (prev+1)%7==triple else 1
 return units
variants={}
cutoff=1722470400
for k in CORE:
 v2=[{**e,"baseR":float(e["R"]),"overnight_units":overnight(e["entry"],e["exit"],e["symbol"])}
     for e in raw[k]["P9_V2"] if int(e["entry"])>=cutoff]
 v3=[dict(e) for e in w.EVENTS[k]]
 assert all("baseR" in e and "overnight_units" in e for e in v2+v3)
 assert all(e["key"]==k for e in v2+v3)
 variants[k]={"V2":v2,"V3":v3}
 for p,pol in ns["policy_map"].items():
  dr=ns["regimes"][p]
  for e in v2:
   key=(e["symbol"],e["entry"])
   if key not in dr:dr[key]=ns["reg"](e["symbol"],e["entry"],pol["measure"])
for k in EXTRA:
 variants[k]={"V3":[dict(e) for e in w.EVENTS[k]]}
# Input audit and locked references
for name,lock,dir,field in (
 ("P9_V2",BASE/"p9-opposite-challenger-20261117"/"FROZEN_P9_V2"/"P9_V2_LOCK.json",
  BASE/"p9-hybrid-optimization-20261117","sha256"),
 ("P7",BASE/"p9-hybrid-optimization-20261117"/"P7_FROZEN_REFERENCE"/"P7_LOCKED_FORMAT.json",
  BASE/"p7-fixed-risk-strategy-20261117","files_sha256")):
 data=json.loads(lock.read_text(encoding="utf8"))
 assert all((dir/f).is_file() and hashlib.sha256((dir/f).read_bytes()).hexdigest()==sha for f,sha in data[field].items())
 print("FROZEN_SHA_PASS",name,len(data[field]),flush=True)
def apply(core,extras,regime_rules=None):
 assert len(core)==3 and len(extras)==3
 included=list(CORE)+[k for k,use in zip(EXTRA,extras) if use]
 w.PREFIX=tuple(included)
 rules=regime_rules or {}
 for k in CORE:
  which=core[VARIABLE.index(k)] if k in VARIABLE else "V3"
  a=variants[k]["V2"] if which=="V2" else variants[k]["V3"]
  if k in rules:
   mode=rules[k]
   if mode=="UNION_V2_PRIORITY":
    seen=set();items=[]
    for e in variants[k]["V2"]+variants[k]["V3"]:
     if e["entry"] in seen:continue
     seen.add(e["entry"]);items.append(e)
    a=items
   elif mode=="INTERSECTION":
    other={e["entry"] for e in variants[k]["V3"]}
    a=[e for e in variants[k]["V2"] if e["entry"] in other]
   elif mode in ("V2_ADR_LOW_V3_ADR_HIGH","V3_ADR_LOW_V2_ADR_HIGH"):
    ix={e["entry"]:e for e in variants[k]["V2"]}
    jx={e["entry"]:e for e in variants[k]["V3"]}
    arr=[]
    for t in sorted(ix.keys()|jx.keys()):
     e=ix.get(t,jx.get(t))
     ratio=ns["reg"](e["symbol"],t,"relative100")
     prefer_v2=(ratio<1.) if mode=="V2_ADR_LOW_V3_ADR_HIGH" else (ratio>=1.)
     cand=(ix.get(t) if prefer_v2 else jx.get(t))
     if cand is not None:arr.append(cand)
    a=arr
   elif mode=="V2_IF_ADR_LOW" or mode=="V3_IF_ADR_HIGH":
    lookup=variants[k]["V2"] if mode=="V2_IF_ADR_LOW" else variants[k]["V3"]
    a=[q for q in lookup if
       (ns["reg"](q["symbol"],q["entry"],"relative100")<.9 if mode=="V2_IF_ADR_LOW" else
        ns["reg"](q["symbol"],q["entry"],"relative100")>=1.2)]
   else:raise ValueError(mode)
  w.EVENTS[k]=a
 for k,use in zip(EXTRA,extras):
  if use:w.EVENTS[k]=variants[k]["V3"]
 # The same symbol family can have at most 1 position even with opposing methods.
 return len(included)
profiles={
 "V2_BALANCED_ADR":((.75,3.,.5,.5),"ABS_EXP_LOW_75_HIGH125"),
 "V3_ROBUST_ADR":((.75,3.,.25,.25),"ABS_EXP_NAS_LOW50_HIGH150"),
 "V3_STRESS_ADR":((.5,3.,.25,.25),"ABS_EXP_LOW_50_HIGH150"),
 "CAP_025_FLAT":((.25,.25,.25,.25),"STATIC"),
 "CAP_025_ADR":((.20,.20,.20,.20),"ABS_EXP_LOW_75_HIGH125")
}
def run(profile,costs=(0.,.6),detail=False):
 weight,policy=profiles[profile]
 return ev(weight,policy,costs,full=detail)
def summarize(q):
 return {k:q[k] for k in ("monthly","net_27m","training_net17mo","diag_2026_net10mo",
  "closed_dd","dd_veto","trades","max_risk_pct_entry","max_simultaneous_initial_sl_budget_pct")}
bench={}
cases={
 "V2_BALANCED_R0":(("V3","V3","V3"),(False,False,False),"V2_BALANCED_ADR"),
 "V3_ROBUST_R0":(("V3","V3","V3"),(True,True,True),"V3_ROBUST_ADR"),
 "V3_STRESS_R0":(("V3","V3","V3"),(True,True,True),"V3_STRESS_ADR"),
 "CAP25_V2":(("V3","V3","V3"),(False,False,False),"CAP_025_FLAT"),
 "CAP25_V3":(("V3","V3","V3"),(True,True,True),"CAP_025_FLAT")
}
for label,(core,extra,profile) in cases.items():
 apply(core,extra)
 q=run(profile,(0.,.4,.5,.6,.7),detail=True)
 bench[label]={"core_versions":core,"v3_extras":extra,"profile":profile,"scenarios":q}
 print("BENCHMARK",label,[(cost,q[str(cost)]["monthly"],q[str(cost)]["closed_dd"],
 q[str(cost)]["dd_veto"],q[str(cost)]["trades"]) for cost in (0.,.4,.5,.6,.7)],flush=True)
# Baseline regression parity to previously verified research.
assert bench["V2_BALANCED_R0"]["scenarios"]["0.0"]["monthly"]==1293.84
assert bench["V2_BALANCED_R0"]["scenarios"]["0.6"]["monthly"]==99.88
assert bench["V3_ROBUST_R0"]["scenarios"]["0.0"]["monthly"]==1373.05
assert bench["V3_ROBUST_R0"]["scenarios"]["0.6"]["monthly"]==131.49
print("BASELINE_PARITY_PASS",flush=True)
search=[]
start=time.monotonic()
for bits in itertools.product(("V2","V3"),repeat=3):
 for e in itertools.product((False,True),repeat=3):
  apply(bits,e)
  for profile in profiles:
   z=run(profile,(0.,.6))
   a=z["0.0"];c=z["0.6"]
   # Normal and severe cost BOTH positive training; closed DD guard and max 2 families.
   qualified=(a["training_net17mo"]>0 and c["training_net17mo"]>0
    and a["monthly"]>0 and c["monthly"]>0
    and a["closed_dd"]<=6. and c["closed_dd"]<=8.
    and a["dd_veto"]==0 and c["dd_veto"]==0 and
    a["max_simultaneous_initial_sl_budget_pct"]<=7 and
    a["max_risk_pct_entry"]<=5)
   # Only PRE-2026 dollars for selection; penalty includes DD calculated over 2024-26 (non-OOS).
   train_score=(.20*a["training_net17mo"]+.65*c["training_net17mo"]
    -125*c["closed_dd"]-65*a["closed_dd"]) if qualified else -1e9
   search.append({"core_versions":list(bits),"v3_extras":list(e),
      "profile":profile,"eligible_pre":qualified,"train_score":round(train_score,2),
      "normal":summarize(a),"stress06":summarize(c)})
 print("GRID_PROGRESS",bits,"TESTED",len(search),
   "QUALIFIED",sum(q["eligible_pre"] for q in search),"SECONDS",round(time.monotonic()-start,2),flush=True)
valid=sorted([r for r in search if r["eligible_pre"]],key=lambda r:-r["train_score"])
# Retest finalists at additional costs.
focus=valid[:40]
for metric in ("normal","stress06"):
 focus+=sorted(valid,key=lambda r:-r[metric]["monthly"])[:15]
focus+=[{"core_versions":list(c),"v3_extras":list(x),"profile":p}
 for c,x,p in cases.values()]
short={}
done=set()
for q in focus:
 key=(tuple(q["core_versions"]),tuple(q["v3_extras"]),q["profile"])
 if key in done:continue
 done.add(key)
 apply(*key[:2])
 data=run(q["profile"],(0.,.4,.5,.6,.7),detail=True)
 short[str(key)]={"core_versions":list(key[0]),"v3_extras":list(key[1]),
  "profile":key[2],"results":data}
 print("FINALIST",len(short),"CASE",key,"PERF",[(k,data[str(k)]["monthly"],data[str(k)]["closed_dd"],data[str(k)]["dd_veto"]) for k in (0.,.4,.5,.6,.7)],flush=True)
# Save raw, no changes to repo, configs, broker, or strategies.
result={"status":"HISTORICAL_HYBRID_GRID_RESEARCH_COMPLETE",
 "tested":len(search),"eligible_normal_06":len(valid),
 "n_finalists_full_cost":len(short),"candidate_core_versions":list(VARIABLE),
 "core_remainder":[k for k in CORE if k not in VARIABLE],
 "v3_optional_engines":list(EXTRA),
 "risk_profiles":{key:{"base_risk_pct":list(v[0]),"ADR_policy":v[1]} for key,v in profiles.items()},
 "reference":bench,"search":search,"rank_pre2026":valid[:100],
 "full_cost_finalists":short,
 "criteria":"2024-25 training normal/stress -0.6R positive, monthly normal/stress -0.6R positive, closedDD <=6% normal and <=8% -0.6R, no DD veto, initial risk heat<=7, entry risk <=5. More severe penalties in stage2.",
 "warning":["Repeated 2024-26 historical optimization, not valid untouched OOS.",
 "V2 frozen original vs V3 Growth/Defensive rule only differs on 3 core engines.",
 "At most 2 symbol-family slots, no hedges; closing sequence at exit timestamp, not intrabar float.",
 "Valetax H1 Bid/Ask stop-first replay, not MT5 real tick Strategy Tester",
 "Broker cost and margin synthetic and current broker snapshot.",
 "Unapproved research profiles exceed production 0.25% per entry.",
 "No live or demo orders and no production config modification."],
 "orders_submitted":0,"live_risk_changed":False,"repo_modified":False}
(OUT/"HYBRID_P9_V2_V31_STAGE1_FULL_GRID.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
print("HYBRID_SCAN_SAVED",len(search),len(valid),len(short),"SECONDS",round(time.monotonic()-start,1),flush=True)
for key in ("normal","stress06"):
 print("RANK",key,[(r["core_versions"],r["v3_extras"],r["profile"],r[key]["monthly"],
 r["normal"]["closed_dd"],r["stress06"]["closed_dd"]) for r in sorted(valid,key=lambda x:-x[key]["monthly"])[:10]],flush=True)
