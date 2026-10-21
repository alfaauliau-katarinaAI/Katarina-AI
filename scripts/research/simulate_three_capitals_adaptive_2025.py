"""Read-only three-capital projection for frozen XAU ADX20 intraday candidate.

Input: historical broker Bid/Ask tick-path outcomes already computed.
Sizing: opt-in KATARINA Adaptive RiskGovernor, existing CapitalCompoundingEngine,
frozen native-currency trade risk, round lot DOWN including cost/stop buffer.
Compare native Valetax standard XAU (100oz/lot) vs ILLUSTRATIVE cent XAU
(1oz/lot) using SAME Valetax quote data; cent spreads not verified.
No broker orders; no actual account balance changes.
"""
from __future__ import annotations
import sys,math,json,hashlib
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.engines.risk import RiskGovernor,RiskRequest,RiskAction
from katarina.engines.capital import CapitalCompoundingEngine
AUDIT=Path(r"C:\KatarinaDev\artifacts\historical-brain")
INPUT=AUDIT/"katarina_xau_method_tick_ablation_2025_2026.json"
SOURCE=json.loads(INPUT.read_text(encoding="utf-8"))
PARAMS={"RR":2.0,"filter":"ADX20","stop_mult_H1_ATR":.55,"hold_hours":6}
COSTS=(("BASE",1,.03),("STRESS_3_TICKS",3,.05))
ACCOUNTS=(
 ("USD100_STANDARD",100.,"USD",100.,.01,.01,50.),
 ("USD100_CENT_PROXY",100.,"USC",1.,.01,.01,50.),
 ("USD1000_STANDARD",1000.,"USD",100.,.01,.01,50.),
 ("USD1000_CENT_PROXY",1000.,"USC",1.,.01,.01,50.),
 ("USD10000_STANDARD",10000.,"USD",100.,.01,.01,50.),
 ("USD10000_CENT_PROXY",10000.,"USC",1.,.01,.01,50.),
)
def dollar(v,scale):return v/scale

def simulate(source,initial_usd,currency,contract_oz,minlot,step,maxlot,cost_name,slip,fee):
  governor=RiskGovernor.from_config(ROOT/"config"/"risk_governor_v2.json")
  units=1. if currency=="USD" else 100.
  capital=CapitalCompoundingEngine()
  native_balance=initial_usd*units
  capital.observe_balance(native_balance)
  peak=native_balance
  closed_dd=0.;max_dd=0.;executed=0;skipped=0;blocked=0
  monthly={}; weeks=defaultdict(float);volumes=[]
  for x in source:
    if x["rr"]!=PARAMS["RR"] or x["cost"]!=cost_name or PARAMS["filter"] not in x["filters"]:continue
    month=x["month"];year=x["year"];date=str(x["time"])
    row=monthly.setdefault(month,{"month_start_usd":round(dollar(native_balance,units),4),
                      "trades":0,"skipped_minimum_volume":0,
                      "blocked_risk":0,"net_usd":0.,"reserve_usd":0.})
    current=capital.snapshot()
    cap=current.effective_risk_capital(equity=native_balance)
    riskreq=RiskRequest(requested_fraction=None,open_risk_fraction=0.0,
       drawdown_fraction=max(0.,closed_dd),uncertainty=.10,expected_rr=PARAMS["RR"],
       health_ok=True,reconciled=True,daily_drawdown_fraction=0.0,
       risk_capital=cap,risk_reference_capital=max(cap,peak),
       account_currency=currency)
    approved=governor.evaluate(riskreq)
    if approved.action not in (RiskAction.APPROVE,RiskAction.REDUCE):
       row["blocked_risk"]+=1;blocked+=1;continue
    price_risk=float(x["atr"])*PARAMS["stop_mult_H1_ATR"]
    tick=.01
    # A small additional charge to ensure the modeled worst-case cash risk
    # budget covers plausible 1R stop plus entry+exit adverse tick+R fee.
    worstprice=price_risk*(1+fee)+2*slip*tick
    budget=approved.approved_fraction*cap
    worstcash_perlot=worstprice*contract_oz*units
    raw_volume=budget/worstcash_perlot if worstcash_perlot>0 else 0
    volume=min(maxlot,math.floor((raw_volume+1e-12)/step)*step)
    volume=round(volume,8)
    if volume+1e-10<minlot:
       row["skipped_minimum_volume"]+=1;skipped+=1;continue
    exposure_risk=volume*worstcash_perlot
    if exposure_risk>budget+1e-7:
       raise AssertionError("lot_overapproved")
    pnl_native=x["R"]*price_risk*contract_oz*volume*units
    prior_reserve=current.reserve_balance
    native_balance+=pnl_native
    if native_balance<=0:raise AssertionError("balance_negative")
    capital.observe_balance(native_balance)
    next_snapshot=capital.snapshot()
    added=next_snapshot.reserve_balance-prior_reserve
    peak=max(peak,native_balance)
    closed_dd=max(0,(peak-native_balance)/peak)
    max_dd=max(max_dd,closed_dd)
    cash_usd=dollar(pnl_native,units)
    weeks[x["week"]]+=cash_usd
    row["trades"]+=1;row["net_usd"]+=cash_usd;row["reserve_usd"]+=dollar(added,units)
    executed+=1;volumes.append(volume)
  for k,rec in monthly.items():
     rec["net_usd"]=round(rec["net_usd"],4)
     rec["reserve_usd"]=round(rec["reserve_usd"],4)
     rec["month_end_usd"]=round(rec["month_start_usd"]+rec["net_usd"],4)
     rec["return_pct"]=round(100*rec["net_usd"]/rec["month_start_usd"],4) if rec["month_start_usd"]>0 else None
  snap=capital.snapshot()
  return {"starting_usd":initial_usd,"account_model":"STANDARD_VALETAX_SPEC" if currency=="USD" else "CENT_1OZ_PER_LOT_UNVERIFIED_PROXY",
     "currency":currency,"contract_oz_per_lot":contract_oz,"min_lot":minlot,
     "cost_scenario":cost_name,
     "start_capital":initial_usd,
     "end_balance_usd":round(dollar(native_balance,units),2),
     "net_usd":round(dollar(native_balance,units)-initial_usd,2),
     "pct":round(100*(native_balance/initial_usd/units-1),3),
     "active_usd":round(dollar(snap.active_balance,units),2),
     "reserve_usd":round(dollar(snap.reserve_balance,units),2),
     "compounding_milestones":snap.milestone_count,
     "peak_to_valley_realized_balance_dd_pct":round(100*max_dd,3),
     "positive_active_weeks":sum(v>0 for v in weeks.values()),
     "weeks_with_trades":len(weeks),
     "executed":executed,"skipped_minimum_volume":skipped,"blocked_by_governor":blocked,
     "median_lot":sorted(volumes)[len(volumes)//2] if volumes else None,
     "monthly":dict(sorted(monthly.items()))}
def main():
 samples=[x for x in SOURCE["individual_event_outcomes"] if x["rr"]==2 and "ADX20" in x["filters"]]
 assert len(samples)==198,len(samples)
 results=[]
 for name,balance,cur,contract,minlot,step,maxlot in ACCOUNTS:
  for cost,slip,fee in COSTS:
    group=[x for x in samples if x["cost"]==cost]
    result=simulate(group,balance,cur,contract,minlot,step,maxlot,cost,slip,fee)
    result["scenario_id"]=name
    results.append(result)
    print("ACCOUNT",name,cost,"end",result["end_balance_usd"],
      "PCT",result["pct"],"trades",result["executed"],
      "skipped",result["skipped_minimum_volume"],"dd_pct",result["peak_to_valley_realized_balance_dd_pct"],flush=True)
 r={"kind":"KATARINA_ADAPTIVE_INTRADAY_THREE_CAPITAL_RISK_PROJECTION_2025_2026",
   "source_sha256":hashlib.sha256(INPUT.read_bytes()).hexdigest(),
   "method":PARAMS,"three_capitals_usd":[100,1000,10000],
   "uses_actual_adaptive_governor_module":True,"risk_governor_config_read_only":True,
   "cent_contract_and_spread_are_not_broker_verified":True,
   "cent_quote_costs_are_transferred_from_valetax_standard":True,
   "does_not_claim_real_tradeability_of_cent":True,
   "broker_cash_margins_swaps_ignored":True,
   "drawdown_closed_balance_not_intratrade_floating":True,
   "2026_was_already_studied":True,
   "not_clean_OOS":True,"orders_sent":0,"promoted_to_live":False,
   "model_results":results}
 out=AUDIT/"katarina_intraday_three_capitals_adaptive_2025_2026.json"
 out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
 print("FILE",str(out),flush=True)
if __name__=="__main__":main()
