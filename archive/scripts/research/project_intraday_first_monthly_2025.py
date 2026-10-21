"""KATARINA intraday-first projection: actual minimum 0.01 lot, dynamic 1% risk.

Only research backtest, no broker orders. XAUUSD UTC06 OR breakout only:
other symbols and scalping playbooks have not passed research evidence, so
are kept NO_TRADE rather than being credited fabricated profit.

Tick replay reuses existing code but records each simulated fill into
account/capital timeline and checks minimum-lot affordability.
"""
from __future__ import annotations
import sys, json, math, hashlib
from datetime import datetime,timezone,timedelta
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_brain_v2_from_2025 import load_bars,aggregate,build_frames,frame_last,MT5PATH,AUDIT
from intraday_session_2025 import candidates,STOP_H1ATR
from xau_intraday_real_tick_path_2025 import replay_ticks
import MetaTrader5 as mt5

def assess_account(trades, starting, rr, slip, initial_fraction=.01):
  balance=starting; active=starting; reserve=0.;target=2*active
  volumes=[];equity_peak=balance;maxdd=0.;filtered=0;traded=0;weeks=defaultdict(float);months={}
  annual=defaultdict(lambda:{"trades":0,"skips":0,"net_usd":0.})
  series=[]
  for tr in trades:
    month=tr["month"];year=tr["year"]
    m=months.setdefault(month,{"start_balance":round(balance,2),"trades":0,
      "skipped_min_lot":0,"net_usd":0.,"reserve_added":0.})
    # Position sizing: stop-loss price from ATR and broker lot/contract terms,
    # round DOWN, never increase above configured risk.
    riskprice=tr["atr"]*STOP_H1ATR
    # Conservative per-unit risk: adverse 1/3 ticks on entry AND stop exit.
    effective_lossprice=riskprice+2*slip*tr["tick"]
    budget=.01*min(balance,active)
    singlelot_risk=effective_lossprice*tr["contract"]*tr["minlot"]
    lots=math.floor((budget/singlelot_risk+1e-10))*tr["minlot"] if singlelot_risk>0 else 0.
    lots=round(lots,8)
    if lots+1e-10<tr["minlot"]:
      filtered+=1;m["skipped_min_lot"]+=1;annual[year]["skips"]+=1
      series.append({"month":month,"date":tr["date"],"status":"SKIP_MIN_LOT",
             "bal":balance,"targetRisk":budget,"minlotRisk":singlelot_risk})
      continue
    if lots>tr["maxlot"]:lots=tr["maxlot"]
    realized=tr["R"]*riskprice*tr["contract"]*lots
    before=balance
    balance+=realized
    active+=realized
    annual[year]["trades"]+=1;annual[year]["net_usd"]+=realized
    week=tr["week"];weeks[week]+=realized
    m["trades"]+=1;m["net_usd"]+=realized
    traded+=1;volumes.append(lots)
    equity_peak=max(equity_peak,balance);maxdd=max(maxdd,(equity_peak-balance)/equity_peak)
    if balance>=target:
       newreserve=balance*.30
       reserve+=newreserve
       active=balance-reserve
       m["reserve_added"]+=newreserve
       target=active*2
    series.append({"month":month,"date":tr["date"],"status":"FILLED_SIMULATED",
              "bal":balance,"lots":lots,"pnl":realized,"risk_at_entry":budget})
  for m in months.values():
    m["end_balance"]=round(m["start_balance"]+m["net_usd"],2)
    m["net_usd"]=round(m["net_usd"],2)
    m["return_on_start_pct"]=round(100*m["net_usd"]/m["start_balance"],3)
    m["reserve_added"]=round(m["reserve_added"],2)
  # Include zero-trade calendar months (source ends Oct 2026, starts Jan2025)
  for yr in (2025,2026):
    for mm in range(1,(13 if yr==2025 else 11)):
      k=f"{yr}-{mm:02d}"
      if k not in months:
        # Fill zero only after replay, account balance would need reconstruction:
        months[k]={"status":"NO_TRADE_OR_MISSING_MARKET_DATA"}
  return {"starting_balance_usd":starting,"rr":rr,"slip_ticks_each_side":slip,
    "monthly":dict(sorted(months.items())),
    "end_balance_usd":round(balance,2),"active_balance_usd":round(active,2),
    "reserve_usd":round(reserve,2),"gain_usd":round(balance-starting,2),
    "gain_pct":round(100*(balance/starting-1),3),"max_observed_closed_balance_dd_fraction":round(maxdd,5),
    "trades_filled":traded,"skipped_min_lot":filtered,
    "median_lot":sorted(volumes)[len(volumes)//2] if volumes else None,
    "positive_active_weeks":sum(z>0 for z in weeks.values()),"active_weeks":len(weeks),
    "annual":{k:{key:round(val,4) if isinstance(val,float) else val for key,val in v.items()}
             for k,v in annual.items()}}

def main():
  symbol="XAUUSD.vx"
  risk=json.loads((ROOT/"config"/"risk_governor_v2.json").read_text(encoding="utf-8"))
  capital=json.loads((ROOT/"config"/"capital_compounding_v1.json").read_text(encoding="utf-8"))
  assert risk["per_trade_default_fraction"]==.01
  if not mt5.initialize(path=MT5PATH,timeout=15000):raise RuntimeError(mt5.last_error())
  alltrades=[]
  try:
   si=mt5.symbol_info(symbol)
   sp=(float(si.volume_min),float(si.volume_step),float(si.volume_max),float(si.trade_contract_size),float(si.trade_tick_size or si.point))
   print("BROKER_SPEC",sp,flush=True)
   bars,_=load_bars(symbol)
   h1=frame_last(build_frames(aggregate(bars,3600),3600))
   h4=frame_last(build_frames(aggregate(bars,14400),14400))
   events=[ev for ev in candidates(bars,h1,h4) if ev[2]=="OR_TREND_BREAK" and ev[3]==6]
   for j,side,mode,hh,atr in events:
     start=datetime.fromtimestamp(bars[j].time,tz=timezone.utc)
     stop=start+timedelta(hours=6)
     data=mt5.copy_ticks_range(symbol,start,stop,mt5.COPY_TICKS_ALL)
     for rr in (2.,3.):
      for cost,slip,fee in (("base",1,.03),("stress",3,.05)):
       result,reason=replay_ticks(symbol,data,int(start.timestamp()*1000),
          int(stop.timestamp()*1000),side,atr,sp[-1],rr,slip,fee)
       if reason:
          print("SKIP_BROKER_HISTORY",start.isoformat(),reason,flush=True)
          continue
       alltrades.append({"symbol":symbol,"date":start.strftime("%Y-%m-%d"),
          "month":start.strftime("%Y-%m"),"year":str(start.year),
          "week":f"{start.isocalendar().year}-W{start.isocalendar().week:02d}",
          "rr":rr,"cost":cost,"slip":slip,"tick":sp[-1],"minlot":sp[0],
          "maxlot":sp[2],"contract":sp[3],"atr":atr,
          "R":result["R"],"exit":result["reason"]})
     if len(alltrades)%100==0:print("EVENT_PROGRESS",len(alltrades),flush=True)
  finally:mt5.shutdown()
  reports=[]
  for rr in (2.,3.):
    for cost,slip in (("base",1),("stress",3)):
      subset=[x for x in alltrades if x["rr"]==rr and x["cost"]==cost]
      for initial in (100.,1000.,10000.):
       rep=assess_account(subset,initial,rr,slip)
       rep["scenario"]=cost
       reports.append(rep)
       print("ACCOUNT",initial,"RR",rr,cost,"end",rep["end_balance_usd"],"filled",rep["trades_filled"],
             "minlot_skip",rep["skipped_min_lot"],"maxdd",rep["max_observed_closed_balance_dd_fraction"],flush=True)
  report={"kind":"KATARINA_2025_2026_REAL_TICK_INTRADAY_FIRST_MONTHLY_ACCOUNT_PROJECTION",
     "research_only":True,"live_execution":False,"scalping_enabled_in_projection":False,
     "portfolio_other_symbols":"NO_TRADE for unvalidated playbooks",
     "time_span":"2025-01-01 through 2026-10-09, last month partial",
     "risk_governor_sha256":hashlib.sha256((ROOT/"config"/"risk_governor_v2.json").read_bytes()).hexdigest(),
     "risk_profile_unchanged":True,"risk_fraction_per_trade":.01,
     "capital_compounding_config_read":True,"broker_symbol":{"volume_min":sp[0],"volume_step":sp[1],
              "volume_max":sp[2],"contract_size":sp[3],"tick_size":sp[4]},
     "warnings":["profit projections are simulated, not proven forward performance",
       "tick-path close stops and adverse slippage approximation, fee R assumed",
       "2026 data already inspected, so scenario choice is selection-biased",
       "risk-based min-lot skip; do not force oversize to obtain every day",
       "maximum balance drawdown excludes adverse intratrade floating drawdown",
       "margin order rejection, funding/swap, lot rounding dependent on broker",
       "no market news release blackout; holidays and DST not adjusted",
       "not all account loss caps modelled as full broker execution event system",
       "risk governor/compounding unchanged in original configuration"],
     "simulated_events":len(alltrades),"month_scenarios":reports}
  out=AUDIT/"katarina_intraday_first_monthly_projection_2025_2026.json"
  out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
  print("FILE",str(out),flush=True)
if __name__=="__main__":main()
