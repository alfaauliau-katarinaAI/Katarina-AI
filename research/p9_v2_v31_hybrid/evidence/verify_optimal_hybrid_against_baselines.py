"""Final matched-basis audit of chosen hybrid vs V2 Balanced and V3 Robust.
Includes legal max0.25% risk candidates, stress costs and exact monthly reports.
No live changes, no repo changes, no trading.
"""
from pathlib import Path
import json,csv,datetime,hashlib,subprocess,time
BASE=Path(r"C:\Katarina\research")
OUT=BASE/"p9-v2-v31-robust-hybrid-search-20261119"
s=OUT/"test_causal_adr_gated_hybrid.py"
n={"__file__":str(s)}
exec(compile(s.read_text(encoding="utf8").split("modes_h1=",1)[0],str(s),"exec"),n)
run=n["evaluate"];set_case=n["set_case"];apply=n["apply"];w=n["w"]
reference=json.loads((OUT/"HYBRID_P9_V2_V31_ADR_REGIME_GRID.json").read_text(encoding="utf8"))
selected=next(q for q in reference["full_finalists"] if
 q["config"]["h1"]=="V3" and q["config"]["h4"]=="V2" and q["config"]["nas"]=="V3"
 and q["config"]["chf_sell_gate"]=="REL_MID_08_12"
 and q["config"]["eur_sell"] is False and q["config"]["xau_sell"] is False
 and q["config"]["risk_profile"]=="V2_BALANCED_ADR")
assert selected["config"]["CHF_SELL_accepted_candidates"]==12
baseline=reference["baseline"]
def standard(mode):
 if mode=="V2_BALANCED":
  apply(("V3","V3","V3"),(False,False,False))
  return "V2_BALANCED_ADR"
 if mode=="V3_ROBUST":
  apply(("V3","V3","V3"),(True,True,True))
  return "V3_ROBUST_ADR"
 if mode=="HYBRID":
  assert set_case("V3","V2","V3","REL_MID_08_12",False,False)==12
  return "V2_BALANCED_ADR"
 raise ValueError(mode)
cases={}
for mode in ("V2_BALANCED","V3_ROBUST","HYBRID"):
 profile=standard(mode)
 cases[mode]=run(profile,(0.,.4,.5,.6,.7,1.0),detail=True)
 print("CHECKED",mode,[(str(k),cases[mode][str(k)]["monthly"],
  cases[mode][str(k)]["closed_dd"],cases[mode][str(k)]["dd_veto"])
  for k in (0.,.4,.5,.6,.7,1.)],flush=True)
assert cases["HYBRID"]["0.0"]["monthly"]==1349.21
assert cases["HYBRID"]["0.6"]["monthly"]==121.78
assert cases["V2_BALANCED"]["0.0"]["monthly"]==1293.84
assert cases["V2_BALANCED"]["0.6"]["monthly"]==99.88
assert cases["V3_ROBUST"]["0.0"]["monthly"]==1373.05
baseline_normal=cases["V2_BALANCED"]["0.0"]
hybrid_normal=cases["HYBRID"]["0.0"]
with (OUT/"HYBRID_OPTIMAL_MONTHLY_V2_V3_COMPARISON.csv").open("w",newline="",encoding="utf8") as f:
 writer=csv.writer(f)
 writer.writerow(["month","v2_balanced_normal_USD","v3_robust_normal_USD","hybrid_normal_USD",
    "v2_balanced_extra_minus_0p6R","v3_robust_extra_minus_0p6R","hybrid_extra_minus_0p6R"])
 for i,row in enumerate(hybrid_normal["monthly_detail"]):
  assert all(cases[m]["0.0"]["monthly_detail"][i]["month"]==row["month"] for m in cases)
  writer.writerow([row["month"]]+[cases[m]["0.0"]["monthly_detail"][i]["net"] for m in cases]
   +[cases[m]["0.6"]["monthly_detail"][i]["net"] for m in cases])
print("HYBRID_BYPAIR",hybrid_normal.get("by_pair"),flush=True)
print("HYBRID_YEARS",hybrid_normal["year"],"TRAIN",hybrid_normal["training_net17mo"],
 "DIAG2026",hybrid_normal["diag_2026_net10mo"],flush=True)
# Test strictly at or below 0.25% MAX pre-ADR sizing (no production changes).
CAP={
 "STRICT_FLAT":((.05,.25,.05,.05),"STATIC"),
 "STRICT_ADR":((.04,.20,.04,.04),"ABS_EXP_LOW_75_HIGH125"),
 "MODERATE_FLAT":((.15,.25,.10,.10),"STATIC"),
 "MODERATE_ADR":((.12,.20,.08,.08),"ABS_EXP_LOW_75_HIGH125"),
 "LOW_FX_FLAT":((.10,.25,.05,.05),"STATIC"),
 "FULL_CAP_FLAT":((.25,.25,.25,.25),"STATIC")
}
for name,q in CAP.items():n["mod"]["profiles"]["LEGAL_"+name]=q
capcases={}
for mode in ("V2_BALANCED","V3_ROBUST","HYBRID"):
 standard(mode)
 for capname in CAP:
  key="LEGAL_"+capname
  results=run(key,(0.,.4,.5,.6,.7),detail=False)
  assert max(v["max_risk_pct_entry"] for v in results.values())<=.25+1e-8
  capcases[mode+"|"+capname]={p:{
   k:z[k] for k in ("monthly","net_27m","training_net17mo","diag_2026_net10mo","closed_dd","dd_veto","trades","max_risk_pct_entry")
  } for p,z in results.items()}
  print("LEGAL_CAP",mode,capname,
   "NORMAL",results["0.0"]["monthly"],"STRESS06",results["0.6"]["monthly"],
   "DD06",results["0.6"]["closed_dd"],"TRADES",results["0.0"]["trades"],flush=True)
# Choose only with pre-2026 stressed >0 and future-seen period not a deciding weight.
capeligible=[]
for name,result in capcases.items():
 a=result["0.0"];c=result["0.6"]
 if a["training_net17mo"]>0 and c["training_net17mo"]>0 and c["monthly"]>0 and c["dd_veto"]==0:
  capeligible.append((name,result))
print("CAP_ELIGIBLE",len(capeligible),flush=True)
for name,q in sorted(capeligible,key=lambda t:-t[1]["0.6"]["training_net17mo"])[:10]:
 print("CAP_RANK",name,q["0.0"]["monthly"],q["0.6"]["monthly"],q["0.6"]["closed_dd"],q["0.6"]["training_net17mo"],flush=True)
# Immutable source proof (repo and locks)
repo=Path(r"C:\Katarina\code")
git=subprocess.run(["git","status","--porcelain"],cwd=repo,capture_output=True,text=True,timeout=20)
assert git.returncode==0 and not git.stdout.strip()
for name,lock,dir,field in (
 ("P9_V2",BASE/"p9-opposite-challenger-20261117"/"FROZEN_P9_V2"/"P9_V2_LOCK.json",BASE/"p9-hybrid-optimization-20261117","sha256"),
 ("P7",BASE/"p9-hybrid-optimization-20261117"/"P7_FROZEN_REFERENCE"/"P7_LOCKED_FORMAT.json",BASE/"p7-fixed-risk-strategy-20261117","files_sha256")):
 src=json.loads(lock.read_text(encoding="utf8"))
 assert all(hashlib.sha256((dir/k).read_bytes()).hexdigest()==v for k,v in src[field].items())
print("REPO_CLEAN_ORIGINAL_LOCKS_VALID",flush=True)
report={
 "status":"MATCHED_HYBRID_VALIDATION_COMPLETE_RESEARCH_ONLY",
 "selected_hybrid":selected["config"],"full_scenarios":cases,
 "native_cap_profiles":{k:{"base_percent":v[0],"ADR_policy":v[1]} for k,v in CAP.items()},
 "native_cap_comparisons":capcases,"native_cap_eligible":len(capeligible),
 "selected_reason":"Highest pre-2026 training normal/-0.6R robustness score among additional causal ADR-gated V2/V3 mixtures tested while preserving V2 Balanced risk policy, with 0 DD veto through -0.6R, normalDD <=6 and stressDD<=8.",
 "trade_policy":"Research only; V2 Frozen and P7 unchanged; native live max risk 0.25% unchanged.",
 "warnings":["Repeated 2024/2025/2026 history mining and modest CHF SELL sample 12 candidates; not independent OOS",
 "No claim real tick MT5 backtest or independent prospective signal quality",
 "At -0.7R severe penalties most high risk settings breach DD guard and blocked entries",
 "Closed balance drawdown only, float equity liquidation and historical margin unmeasured",
 "No production config, MT5 EA, broker order or GitHub changes."],
 "broker_orders_sent":0,"production_changed":False,
 "repo_clean":True,
 "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
(OUT/"FINAL_HYBRID_MATCHED_SCENARIOS_AND_CAP025.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
print("FULL_COMPARISON_REPORT_SAVED",len(capcases),flush=True)
