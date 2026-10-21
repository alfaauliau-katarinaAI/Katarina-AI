"""Risk-governor sweep across 55 independently TRAIN-selected setups.
Inputs are MT5-private local NPZ; exports summary only, no broker data.
Not a broker execution backtest. Strictly research-only.
"""
import sys,json,csv,heapq,itertools,hashlib
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import mega_multi_asset_v2 as R
OUT=R.OUT
def month(t):return datetime.fromtimestamp(int(t),timezone.utc).strftime("%Y-%m")
def cat(s):
 s=s.upper()
 if s.startswith(("XAU","XAG","XPD","XPT")):return "METALS"
 if s.startswith(("BTC","ETH","BCH","DOGE","XRP","LTC")):return "CRYPTO"
 if s.startswith(("XBR","XTI","XNG")):return "ENERGY"
 if s.startswith(("NAS","SP","US30","DAX","JPN","UK1","FRA","EU50","HK","AUS2")):return "INDEX"
 if s.startswith("DXY"):return "DOLLAR_INDEX"
 return "FOREX"
def derive_entries(p):
 x=p.get("selected")
 if not x:return []
 sym=p["symbol"];fp=R.HISTORY/(sym.replace(".","_")+".npz")
 if not fp.exists():return []
 data=np.load(fp);bars=data["bars"];point=float(p["point"])
 mult=1 if x["timeframe"]=="M15" else 2 if x["timeframe"]=="M30" else 4 if x["timeframe"]=="H1" else 16
 b=R.tf(bars,mult);t=b["time"].astype(np.int64)
 atr,fam,conf,_=R.signal_data(b,point)
 bu,se=fam[x["family"]];cb,cs=conf[x["candle"]]
 session=np.ones(len(t),bool) if x["session"]=="ALL" else (((t//3600)%24)>=6)&(((t//3600)%24)<=20)
 eligible=(np.arange(len(t))>=240)&(np.arange(len(t))<len(t)-36)&(t>=1735689600)&(t<R.END)&np.isfinite(atr)&(atr>point)&(b["spread"]*point<=.22*atr)
 B=bu&cb&session&eligible;S=se&cs&session&eligible
 if x["direction"]=="BUY":S[:]=False
 if x["direction"]=="SELL":B[:]=False
 ii=np.flatnonzero(B^S);side=np.where(B[ii],1,-1)
 ii=ii[ii+x["hold"]<len(b)];side=side[:len(ii)]
 if not len(ii):return []
 values,ex=R.simulate(b,ii,side,atr,point,x["stop_atr"],x["rr"],x["hold"])
 keep=np.zeros(len(ii),bool);last=-1
 for j in range(len(ii)):
  if ii[j]>last:keep[j]=True;last=int(ex[j])
 out=[]
 for j,ext,sd,val in zip(ii[keep],ex[keep],side[keep],values[keep]):
  enter=int(t[j+1]);exit=int(t[ext])
  window="train" if enter<R.CUT1 and exit<R.CUT1 else "validation" if enter>=R.CUT1 and exit<R.CUT2 else "diagnostic" if enter>=R.CUT2 and exit<R.END else "boundary"
  if window!="boundary":
   out.append(dict(symbol=sym,category=cat(sym),entry=enter,exit=exit,side=int(sd),R=round(float(val),6),
                   window=window))
 return out
def portfolio(events,risk=.0025,slots=2,daystop=.01,maxdd=.08,losestreak=4,groupcap=1,extra_cost=.15,start=0,end=1<<40):
 sample=[e for e in events if e["entry"]>=start and e["exit"]<end]
 sample.sort(key=lambda x:(x["entry"],x["symbol"]))
 eq=10000.;peak=eq;worst=0.;active=[];group_counts=Counter()
 active_sym=set();settled=0;losses=0;guard_stop=False;stops=Counter()
 daily_start=eq;day0=-1;week0=-1;months=defaultdict(lambda:dict(n=0,profit=0.,sumR=0.,wins=0,losses=0))
 def settle(ts):
  nonlocal eq,peak,worst,settled,losses
  while active and active[0][0]<=ts:
   _t,_i,e,stake=heapq.heappop(active)
   name=e["symbol"];grp=e["category"];active_sym.discard(name);group_counts[grp]-=1
   rr=e["R"]-extra_cost
   profit=stake*rr;eq+=profit;settled+=1
   losses=losses+1 if rr<0 else 0
   peak=max(peak,eq)
   worst=max(worst,(peak-eq)/peak)
   k=month(_t);months[k]["n"]+=1;months[k]["profit"]+=profit;months[k]["sumR"]+=rr
   months[k]["wins"]+=int(rr>0);months[k]["losses"]+=int(rr<0)
 for i,e in enumerate(sample):
  ts=e["entry"];settle(ts)
  if guard_stop:stops["halted"]+=1;continue
  current_day=ts//86400
  current_week=ts//604800
  if current_day!=day0:
   day0=current_day;daily_start=eq
  if current_week!=week0:
   week0=current_week;losses=0
  if eq<=peak*(1-maxdd) or eq<=0:
   guard_stop=True;stops["global_halt"]+=1;continue
  if losses>=losestreak:stops["weekly_loss_cooldown"]+=1;continue
  if eq<daily_start*(1-daystop):stops["daily_limit"]+=1;continue
  if len(active)>=slots:stops["slots"]+=1;continue
  if e["symbol"] in active_sym:stops["pair_limit"]+=1;continue
  if group_counts[e["category"]]>=groupcap:stops["group_limit"]+=1;continue
  heapq.heappush(active,(e["exit"],i,e,eq*risk))
  active_sym.add(e["symbol"]);group_counts[e["category"]]+=1
 settle(1<<43)
 months_json=[]
 for k,v in sorted(months.items()):
  months_json.append(dict(month=k,trades=v["n"],pnl=round(v["profit"],2),sumR=round(v["sumR"],3),
                          win_rate_pct=round(100*v["wins"]/v["n"],2) if v["n"] else 0))
 return dict(risk_pct=round(risk*100,3),slots=slots,day_limit_pct=round(daystop*100,2),
  max_dd_guard_pct=round(maxdd*100,2),max_loss_streak=losestreak,group_cap=groupcap,
  extra_cost_R=extra_cost,closed_return_pct=round((eq/10000-1)*100,3),
  max_closed_dd_pct=round(worst*100,3),closed_trades=settled,
  guard_halted=guard_stop,events_seen=len(sample),skips=dict(stops),monthly=months_json)
def main():
 inputs=[p for p in OUT.glob("*.json") if p.name.endswith(".vx.json") or p.name.endswith("_vx.json")]
 # filenames are XAUUSD_vx.json
 inputs=sorted(OUT.glob("*_vx.json"))
 records=[];error=[];events=[]
 for path in inputs:
  d=json.loads(path.read_text(encoding="utf-8"));records.append(d)
  try:events+=derive_entries(d)
  except Exception as exc:error.append(dict(symbol=d["symbol"],error=str(exc)))
 if not records:raise RuntimeError("No completed pair studies found")
 all_syms={p["symbol"] for p in records}
 selected=[p for p in records if p.get("selected")]
 passed=[]
 for p in selected:
  a=p["selected"];v=a["validation"];dg=a["diagnostic"]
  if v["n"]>=12 and dg["n"]>=12 and a["validation_stress_meanR"]>0 and a["diagnostic_stress_meanR"]>0:
   passed.append(p["symbol"])
 attempt=sum(x["counts"]["theoretical"] for p in records for x in p.get("timeframes",{}).values())
 evaluated=sum(x["counts"]["evaluated"] for p in records for x in p.get("timeframes",{}).values())
 qualified=sum(x["counts"]["qualified"] for p in records for x in p.get("timeframes",{}).values())
 events.sort(key=lambda e:(e["entry"],e["symbol"]))
 horizons=[("train",0,R.CUT1),("validation",R.CUT1,R.CUT2),("diagnostic",R.CUT2,R.END)]
 risks=[]
 for risk,slots,day,dd,streak,group in itertools.product((.001,.0025,.005,.01),(1,2,3),(.01,.02),(.06,.1,.15),(3,5),(1,2)):
  cfg=dict(risk=risk,slots=slots,daystop=day,maxdd=dd,losestreak=streak,groupcap=group)
  x=dict(config={k:(int(v) if k in ("slots","losestreak","groupcap") else v) for k,v in cfg.items()},
         splits={key:portfolio(events,**cfg,extra_cost=.15,start=start,end=end) for key,start,end in horizons})
  risks.append(x)
 # Rank by train only; no selection using validation.
 acceptable=[x for x in risks if x["splits"]["train"]["closed_trades"]>=35 and x["splits"]["train"]["closed_return_pct"]>0
  and not x["splits"]["train"]["guard_halted"]]
 acceptable.sort(key=lambda x:(x["splits"]["train"]["closed_return_pct"]-2*x["splits"]["train"]["max_closed_dd_pct"]),reverse=True)
 best=acceptable[0] if acceptable else None
 baseline=next((x for x in risks if x["config"]==dict(risk=.0025,slots=1,daystop=.01,maxdd=.06,losestreak=3,groupcap=1)),None)
 bymonth=defaultdict(lambda:dict(n=0,sumR=0.,stressR=0.,pairs=set()))
 for e in events:
  v=bymonth[month(e["entry"])]
  v["n"]+=1;v["sumR"]+=e["R"];v["stressR"]+=e["R"]-.15;v["pairs"].add(e["symbol"])
 monthly=[dict(month=k,n=v["n"],sum_R=round(v["sumR"],3),stress_sum_R=round(v["stressR"],3),unique_pairs=len(v["pairs"]))
          for k,v in sorted(bymonth.items())]
 pair_results=[]
 for p in records:
  w=p.get("selected")
  item=dict(symbol=p["symbol"],M15_bars=p.get("n_m15",0),
            start=datetime.fromtimestamp(p["history_start"],timezone.utc).strftime("%Y-%m-%d") if "history_start" in p else "?",
            timeframes=list(p.get("timeframes",{})),pass_stress=p["symbol"] in passed)
  if w:item.update(timeframe=w["timeframe"],family=w["family"],candle=w["candle"],session=w["session"],
      direction=w["direction"],stop_atr=w["stop_atr"],rr=w["rr"],hold=w["hold"],
      train_n=w["train"]["n"],train_meanR=w["train"]["meanR"],train_DD_R=w["train"]["DD"],
      validation_n=w["validation"]["n"],validation_meanR=w["validation"]["meanR"],
      diagnostic_n=w["diagnostic"]["n"],diagnostic_meanR=w["diagnostic"]["meanR"],
      stress_val_meanR=w["validation_stress_meanR"],stress_diag_meanR=w["diagnostic_stress_meanR"])
  pair_results.append(item)
 report=dict(research="KATARINA massive 55-pair v2 read-only",
  generated_utc=datetime.now(timezone.utc).isoformat(),completed_pairs=len(records),symbols=sorted(all_syms),
  n_selected=len(selected),n_pass_stress=len(passed),passed_symbols=passed,
  theoretical_grid=int(attempt),evaluated_configs=int(evaluated),train_min_count_configs=int(qualified),
  strategy_families=list(R.FAMS),candle_confirmations=list(R.CFMS),timeframes=["M15","M30","H1","H4"],
  stops=list(R.STOPS),RRs=list(R.RRS),time_exits=list(R.HOLDS),
  selection="score and 28+ trades in >=4 distinct months BEFORE 2026-01-01; validation and diagnostics never used for selection",
  windows_utc=dict(train="2025 available",validation="2026-01 to 2026-05",diagnostic="2026-06 to 2026-10-09"),
  caveats=["Periods are PREVIOUSLY RESEARCHED, not truly unseen independent OOS","No true-tick replay; MT5 M15 bid bars, ask modeled from bar spread",
           "Bar SL-first, stop adverse open gap modeled; slippage tail and limit fills unverified",
           "Synthetic .05R cost plus .15R stress; swaps, real commission, margin, lot size, cross currency conversion not simulated",
           "Multiple testing inflates selected 2025 performance","Portfolio risk is virtual and uses closed equity only, not intratrade floating DD",
           "Some instruments start partway through 2025; do not treat them as full-year histories",
           "No strategy may go live before independent forward demo with preregistered parameters"],
  per_pair=pair_results,monthly_all_selected_events=monthly,
  risk_grid_attempted=len(risks),risk_2025_choice=best,risk_baseline=baseline,
  risk_models=risks,errors=error,live_execution_authorized=False,broker_orders_submitted=0,
  private_bars_included=False,source_hash=hashlib.sha256(HERE.joinpath("mega_multi_asset_v2.py").read_bytes()).hexdigest())
 (OUT/"FINAL_REPORT.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
 with (OUT/"per_pair.csv").open("w",newline="",encoding="utf-8") as f:
  fs=sorted(set().union(*(x.keys() for x in pair_results)))
  w=csv.DictWriter(f,fieldnames=fs);w.writeheader()
  for row in pair_results:
   row=dict(row);row["timeframes"]=",".join(row["timeframes"]);w.writerow(row)
 with (OUT/"monthly.csv").open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=list(monthly[0]) if monthly else ["month","n","sum_R","stress_sum_R","unique_pairs"]);w.writeheader();w.writerows(monthly)
 with (OUT/"risk_sweep.csv").open("w",newline="",encoding="utf-8") as f:
  fields=["risk_pct","slots","day_pct","max_dd_pct","streak","groupcap","train_return","train_dd","val_return","val_dd","diag_return","diag_dd","train_halt","val_halt","diag_halt"]
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for x in risks:
   v=x["config"];a=x["splits"]["train"];b=x["splits"]["validation"];c=x["splits"]["diagnostic"]
   w.writerow(dict(zip(fields,[100*v["risk"],v["slots"],100*v["daystop"],100*v["maxdd"],v["losestreak"],v["groupcap"],
      a["closed_return_pct"],a["max_closed_dd_pct"],b["closed_return_pct"],b["max_closed_dd_pct"],c["closed_return_pct"],c["max_closed_dd_pct"],
      a["guard_halted"],b["guard_halted"],c["guard_halted"]])))
 print("FINAL",json.dumps(dict(pairs=len(records),selected=len(selected),passed=passed,theoretical=attempt,
  evaluated=evaluated,qualified=qualified,events=len(events),risk_trials=len(risks),risktrain_best=best["config"] if best else None,
  risktrain_perf=best["splits"] if best else None,baseline=baseline["splits"] if baseline else None,errors=error),ensure_ascii=False),flush=True)
if __name__=="__main__":main()