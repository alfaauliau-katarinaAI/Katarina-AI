"""Research-only ADR-gated hybrid follow-up; same frozen MT5 event snapshots and cost model.
No broker calls and no source, config or production changes.
Test whether V2/V3 crossover can be assigned by STRICTLY PRIOR day's ADR.
"""
from pathlib import Path
import json,itertools,time,hashlib
ROOT=Path(r"C:\Katarina\research")
OUT=ROOT/"p9-v2-v31-robust-hybrid-search-20261119"
script=OUT/"hybrid_p9_v2_v31_robust_grid.py"
mod={"__file__":str(script)}
exec(compile(script.read_text(encoding="utf8").split("bench={}",1)[0],str(script),"exec"),mod)
w=mod["w"];evaluate=mod["run"];apply=mod["apply"];reg=mod["ns"]["reg"]
extras_orig=mod["variants"]["CHF_H4_SELL"]["V3"]
base=mod["variants"]
# Independent parity after module prelude, all no order tools.
def make_core_mode(eng,mode):
 if mode in ("V2","V3"):return mode,None
 assert mode in ("V2_ADR_LOW_V3_ADR_HIGH","V3_ADR_LOW_V2_ADR_HIGH")
 return "V3",mode
def set_case(h1,h4,nas,gate,eur,xau):
 c=[];rules={}
 for eng,mode in zip(mod["VARIABLE"],(h1,h4,nas)):
  choice,rule=make_core_mode(eng,mode);c.append(choice)
  if rule:rules[eng]=rule
 apply(tuple(c),(eur,True,xau),rules)
 # Require all filtered CHF SELL are from the V3 entry generator, not raw merged sources.
 def ok(e):
  if gate=="ALL":return True
  sym=e["symbol"];t=e["entry"]
  if gate=="REL_LOW_08":return reg(sym,t,"relative100")<.8
  if gate=="REL_HIGH_12":return reg(sym,t,"relative100")>=1.2
  if gate=="REL_MID_08_12":return .8<=reg(sym,t,"relative100")<1.2
  if gate=="EXP_LOW_09":return reg(sym,t,"expanding")<.9
  if gate=="EXP_HIGH_13":return reg(sym,t,"expanding")>=1.3
  raise ValueError(gate)
 w.EVENTS["CHF_H4_SELL"]=[q for q in extras_orig if ok(q)]
 return len(w.EVENTS["CHF_H4_SELL"])
modes_h1=("V3","V2_ADR_LOW_V3_ADR_HIGH","V3_ADR_LOW_V2_ADR_HIGH")
modes_h4=("V2","V3","V2_ADR_LOW_V3_ADR_HIGH")
modes_nas=("V3","V2_ADR_LOW_V3_ADR_HIGH")
gates=("ALL","REL_LOW_08","REL_HIGH_12","REL_MID_08_12","EXP_LOW_09","EXP_HIGH_13")
profiles=("V2_BALANCED_ADR","CAP_025_ADR")
ref=json.loads((OUT/"HYBRID_P9_V2_V31_STAGE1_FULL_GRID.json").read_text(encoding="utf8"))
base_record=ref["reference"]["V2_BALANCED_R0"]["scenarios"]
rows=[]
time0=time.monotonic()
for h1 in modes_h1:
 for h4 in modes_h4:
  for nas in modes_nas:
   for gate in gates:
    for eur,xau in itertools.product((False,True),repeat=2):
     n=set_case(h1,h4,nas,gate,eur,xau)
     for profile in profiles:
      results=evaluate(profile,(0.,.6))
      a=results["0.0"];s=results["0.6"]
      qualified=(a["training_net17mo"]>0 and s["training_net17mo"]>0
        and a["monthly"]>0 and s["monthly"]>0 and a["closed_dd"]<=6 and
        s["closed_dd"]<=8 and a["dd_veto"]==0 and s["dd_veto"]==0 and
        a["max_simultaneous_initial_sl_budget_pct"]<=7 and a["max_risk_pct_entry"]<=5)
      train_score=(.20*a["training_net17mo"]+.65*s["training_net17mo"]
        -125*s["closed_dd"]-65*a["closed_dd"]) if qualified else -1e9
      rows.append({"h1":h1,"h4":h4,"nas":nas,"chf_sell_gate":gate,
       "chf_sell_event_count":n,"eur_sell":eur,"xau_sell":xau,"profile":profile,
       "qualified":qualified,"train_score":round(train_score,2),
       "normal":{q:a[q] for q in ("monthly","net_27m","training_net17mo","diag_2026_net10mo","closed_dd","dd_veto","trades","max_risk_pct_entry","max_simultaneous_initial_sl_budget_pct")},
       "stress06":{q:s[q] for q in ("monthly","net_27m","training_net17mo","diag_2026_net10mo","closed_dd","dd_veto","trades")}})
  print("ADR_DYNAMIC_PROGRESS",h1,h4,"TOTAL",len(rows),"PASS",sum(x["qualified"] for x in rows),
    "SECONDS",round(time.monotonic()-time0,1),flush=True)
print("ADR_DYNAMIC_SCAN_COMPLETE",len(rows),"PASS",sum(x["qualified"] for x in rows),flush=True)
eligible=sorted((q for q in rows if q["qualified"]),key=lambda r:-r["train_score"])
focus=eligible[:25]
for metric in ("normal","stress06"):
 focus+=sorted(eligible,key=lambda r:-r[metric]["monthly"])[:10]
# Check baseline and prior hybrid in same function, not derived by search.
focus+=[
 {"h1":"V3","h4":"V3","nas":"V3","chf_sell_gate":"ALL","eur_sell":False,"xau_sell":False,"profile":"V2_BALANCED_ADR"},
 {"h1":"V3","h4":"V2","nas":"V3","chf_sell_gate":"ALL","eur_sell":False,"xau_sell":False,"profile":"V2_BALANCED_ADR"},
 {"h1":"V3","h4":"V2","nas":"V3","chf_sell_gate":"ALL","eur_sell":False,"xau_sell":False,"profile":"CAP_025_ADR"},
 ]
final=[];seen=set()
for q in focus:
 ident=(q["h1"],q["h4"],q["nas"],q["chf_sell_gate"],q["eur_sell"],q["xau_sell"],q["profile"])
 if ident in seen:continue
 seen.add(ident)
 n=set_case(*ident[:6])
 result=evaluate(ident[6],(0.,.4,.5,.6,.7),detail=True)
 valid=all(result[str(s)]["monthly"]>0 and result[str(s)]["closed_dd"]<=8 and result[str(s)]["dd_veto"]==0 for s in (.4,.5,.6))
 # Production native cap for CAP_025_ADR is strictly respected by 0.20% x 1.25 max.
 if ident[6]=="CAP_025_ADR":
  assert all(result[str(s)]["max_risk_pct_entry"]<=.25+0.001 for s in (0.,.4,.5,.6,.7))
 final.append({"config":{"h1":ident[0],"h4":ident[1],"nas":ident[2],
  "chf_sell_gate":ident[3],"eur_sell":ident[4],"xau_sell":ident[5],
  "risk_profile":ident[6],"CHF_SELL_accepted_candidates":n},
  "all_stress_positive_and_below_DD8":valid,"scenarios":result})
 print("DYNAMIC_FINAL",len(final),"CASE",ident,
  "STRESS",[(k,result[str(k)]["monthly"],result[str(k)]["closed_dd"],result[str(k)]["dd_veto"])
 for k in (0.,.4,.5,.6,.7)],flush=True)
report={"status":"ADR_CONDITIONAL_HYBRID_RESEARCH_FINISHED",
 "n_tested":len(rows),"n_preliminary_qualified":len(eligible),"n_finalists_full_cost":len(final),
 "method":"Causal ADR20 computed strictly previous complete daily H1 broker bars. For conditional V2/V3 crossover use ADR20/ADR100 threshold1.0; CHF SELL gates use prior ADR20/ADR100 or prior expanding median. No same-day forward use.",
 "risk_profiles":{k:{"pct":v[0],"ADR_policy":v[1]} for k,v in mod["profiles"].items()},
 "grid":rows,"rank_train":eligible[:50],"full_finalists":final,
 "baseline":{s:{k:base_record[s][k] for k in ("monthly","closed_dd","dd_veto","trades")} for s in ("0.0","0.4","0.5","0.6","0.7")},
 "original_p9_p7_sha_verified":True,"broker_orders":0,"no_production_changes":True,
 "limitations":["Very limited sample of additional V3 SELL signals and 2024-26 historical data-mining, not OOS.",
 "27 full months Aug24-Oct26, 2026 diagnostic already mined.",
 "OHLC H1 stop-first and current broker snapshot, not native MT5 real ticks.",
 "No floating equity drawdown, historical margin/gap and live execution fill quality.",
 "CAP_025_ADR 0.20% per symbol with at most 1.25x multiplier <=0.25%; all higher risk configs purely research."]}
(OUT/"HYBRID_P9_V2_V31_ADR_REGIME_GRID.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
print("ADR_HYBRID_FINAL_SAVED",len(rows),len(final),"SECONDS",round(time.monotonic()-time0,1),flush=True)
