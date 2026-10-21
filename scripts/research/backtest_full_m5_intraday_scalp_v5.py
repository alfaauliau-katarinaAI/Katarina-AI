"""Full M5 bar-by-bar 55-pair causal research: intraday vs extreme scalp.

Never submits an MT5 trade. Runs all 55 sequentially to fit a 2GB VPS.
All events are discovered *without* reading their later returns. Portfolio
ranking uses only observed closed bar features at each timestamp.
"""
from __future__ import annotations
import argparse,csv,json,time,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import OUT,get_bars,TIMEFRAME,stats
from katarina.intelligence.intraday_scalp_research import (
    Candidate,vector_prefilter,fill_next_open)

DEST=OUT/"intraday_scalp_full_m5_v5"
DEST.mkdir(exist_ok=True,parents=True)
POLICIES=("INTRADAY_ONLY","INTRADAY_FIRST_SCALP_EXTREME",
          "SCALP_EXTREME_ONLY","ALPHABETICAL_MATCHED")
INTRADAY_RISK=.0025
SCALP_RISK=.0010
MAX_TRADES_DAY=2
DAILY_RISK_CAP=.0050

def _rank(c:Candidate,policy):
    if policy=="ALPHABETICAL_MATCHED":
        return (0 if c.mode=="INTRADAY" else 1,c.symbol,c.side)
    return (0 if c.mode=="INTRADAY" else 1,
           -c.score,c.spread_atr,c.symbol,c.side)

def replay(pools,outcomes,days,policy,additional_cost=.0):
    equity=1.0;peak=1.0;maxdd=0.;drawdown_money=0.
    daily=defaultdict(lambda:dict(n=0,net=0.,positive=0))
    selected=[];blocked=Counter();last_exit=None
    pending=None;date=None;n_today=0;risk_committed=0.
    for cut in sorted(pools):
        ds=datetime.fromtimestamp(cut,timezone.utc).date().isoformat()
        if pending and pending["exit_time"]<=cut:
            # Only realize P&L when its modeled exit has actually occurred.
            pnl=equity*pending["fraction"]*(pending["R"]-additional_cost)
            equity+=pnl
            if equity<=0:raise RuntimeError("bankruptcy")
            peak=max(peak,equity);maxdd=max(maxdd,1-equity/peak)
            daily[pending["day"]]["net"]+=pnl
            pending=None
        if ds!=date:
            date=ds;n_today=0;risk_committed=0.
        if pending is not None or (last_exit is not None and cut<last_exit):
            blocked["already_in_position"]+=1;continue
        if n_today>=MAX_TRADES_DAY or risk_committed>=DAILY_RISK_CAP:
            blocked["daily_capacity"]+=1;continue
        eligible=[x for x in pools[cut]
                  if (policy not in ("INTRADAY_ONLY","SCALP_EXTREME_ONLY") or
                      x.mode==("INTRADAY" if policy=="INTRADAY_ONLY" else "SCALP_EXTREME"))]
        if not eligible:continue
        ranked=sorted(eligible,key=lambda x:_rank(x,policy))
        best=ranked[0]       # Selected BEFORE outcome lookup
        result=outcomes.get((best.symbol,best.cut,best.mode,best.side))
        if result is None:
            blocked["no_next_open_or_safe_risk"]+=1;continue
        fraction=INTRADAY_RISK if best.mode=="INTRADAY" else SCALP_RISK
        if risk_committed+fraction>DAILY_RISK_CAP:
            blocked["risk_budget"]+=1;continue
        n_today+=1;risk_committed+=fraction
        daily[ds]["n"]+=1
        last_exit=result["exit_time"]
        pending=dict(result,day=ds,fraction=fraction)
        selected.append(dict(result,policy=policy,risk_fraction=fraction,
                             selected_from_same_time=len(eligible)))
    # settle final known simulated exit, not earlier than its timestamp
    if pending is not None:
        pnl=equity*pending["fraction"]*(pending["R"]-additional_cost)
        equity+=pnl;peak=max(peak,equity);maxdd=max(maxdd,1-equity/peak)
        daily[pending["day"]]["net"]+=pnl
    r=[{**x,"R":x["R"]-additional_cost} for x in selected]
    rstats=stats(r)
    positive=sum(x["net"]>0 for x in daily.values())
    negative=sum(x["net"]<0 for x in daily.values())
    monthly=defaultdict(list)
    per_mode=defaultdict(list)
    for x in r:
        mon=datetime.fromtimestamp(x["cut"],timezone.utc).strftime("%Y-%m")
        monthly[mon].append(x);per_mode[x["mode"]].append(x)
    return dict(
        policy=policy,modeled_extra_fee_R=additional_cost,
        n=len(r),return_model_pct=round((equity-1)*100,4),
        max_drawdown_pct=round(maxdd*100,4),
        trade_stats=rstats,
        eligible_market_days=len(days),
        positive_trade_days=positive,negative_trade_days=negative,
        flat_trade_days=len(daily)-positive-negative,
        days_traded=len(daily),
        no_trade_market_days=len(set(days)-set(daily)),
        positive_pct_market_days=round(100*positive/max(1,len(days)),2),
        positive_pct_traded_days=round(100*positive/max(1,len(daily)),2),
        by_month={x:stats(k) for x,k in sorted(monthly.items())},
        by_mode={x:stats(k) for x,k in sorted(per_mode.items())},
        decision_rejections=dict(blocked),
        trades=selected)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--symbols",default="")
    ap.add_argument("--bars",type=int,default=90000)
    args=ap.parse_args()
    requested=args.symbols.split(",") if args.symbols else None
    if args.bars<500 or args.bars>90000:raise ValueError("invalid_bar_count")
    if not mt5.initialize():raise RuntimeError("MT5 unavailable")
    term=mt5.terminal_info()
    if term is None or term.trade_allowed:
        mt5.shutdown()
        raise RuntimeError("live_trading_must_be_disabled")
    old=sorted(OUT.glob("*_vx.json"))
    symbols=[json.loads(p.read_text(encoding="utf-8"))["symbol"]
             for p in old if json.loads(p.read_text(encoding="utf-8")).get("status")=="OK"]
    if requested:
        if any(x not in symbols for x in requested):raise ValueError("unknown symbol")
        symbols=requested
    per=[];outcomes={};pools=defaultdict(list)
    coverage=Counter();failures=[]
    start=time.perf_counter()
    for n,symbol in enumerate(symbols):
        mt5.symbol_select(symbol,True)
        info=mt5.symbol_info(symbol)
        if info is None:
            failures.append({"symbol":symbol,"error":"missing_symbol_spec"});continue
        point=float(info.point)
        frame={}
        for k,(tf,sec,count) in TIMEFRAME.items():
            a=get_bars(symbol,tf,min(args.bars if k=="M5" else count,count))
            if a is None:
                failures.append({"symbol":symbol,"error":"missing_frame_"+k});break
            frame[k]=a
        if len(frame)!=3:continue
        m5=frame["M5"]
        picks,log=vector_prefilter(symbol,m5,frame["M15"],frame["H1"],point)
        spread=m5["spread"].astype(float)*point
        tr=np.maximum.reduce((m5["high"]-m5["low"],
            abs(m5["high"]-np.r_[m5["close"][0],m5["close"][:-1]]),
            abs(m5["low"]-np.r_[m5["close"][0],m5["close"][:-1]])))
        historical=np.asarray(spread[np.isfinite(spread)&(spread>0)])
        for day,num in zip(*np.unique(m5["time"].astype(np.int64)//86400,
                                     return_counts=True)):
            if num>=60:coverage[int(day)]+=1
        model_accept=Counter()
        for x in picks:
            pools[x.cut].append(x)
            fill=fill_next_open(m5,x,point)
            if fill is not None:
                outcomes[(x.symbol,x.cut,x.mode,x.side)]=fill
                model_accept[x.mode]+=1
            else:model_accept["no_safe_fill"]+=1
        detail=dict(symbol=symbol,point=point,
          bars=len(m5),first_bar=int(m5["time"][0]),
          last_bar=int(m5["time"][-1]),
          candidate_summary=log,modeled_fills=dict(model_accept),
          broker_spec={"trade_tick_size":float(info.trade_tick_size),
            "trade_tick_value":float(info.trade_tick_value),
            "contract_size":float(info.trade_contract_size),
            "minimum_lot":float(info.volume_min),
            "lot_step":float(info.volume_step),
            "profit_currency":str(info.currency_profit),
            "commission_per_lot_round_trip":"UNKNOWN_NOT_IN_SYMBOL_INFO"},
          spread_price_quantiles={
            "p10":round(float(np.quantile(historical,.10)),9) if len(historical) else None,
            "p50":round(float(np.quantile(historical,.5)),9) if len(historical) else None,
            "p90":round(float(np.quantile(historical,.9)),9) if len(historical) else None,
          })
        per.append(detail)
        print("PAIR",n+1,"/",len(symbols),symbol,"M5",len(m5),
            "i",log["intraday"],"s",log["scalp_extreme"],
            "safe_fill",len(outcomes),
            "sec",round(time.perf_counter()-start,1),flush=True)
        del m5,frame
    mt5.shutdown()
    if failures:
        print("PARTIAL_FAILS",json.dumps(failures),flush=True)
    # At least 20 markets each with >5h of data for a comparable multi-pair day.
    min_cover=min(20,len(symbols))
    days={datetime.fromtimestamp(k*86400,timezone.utc).date().isoformat()
          for k,v in coverage.items() if v>=min_cover}
    pools={cut:pool for cut,pool in pools.items()
           if datetime.fromtimestamp(cut,timezone.utc).date().isoformat() in days}
    summary={}
    chosen=[]
    for name in POLICIES:
        run=replay(pools,outcomes,days,name)
        chosen+=run["trades"] if name=="INTRADAY_FIRST_SCALP_EXTREME" else []
        summary[name]={k:v for k,v in run.items() if k!="trades"}
        print("POLICY",name,run["trade_stats"],
              "portfolio_pct",run["return_model_pct"],
              "dd",run["max_drawdown_pct"],
              "positive_days",run["positive_trade_days"],
              "days_traded",run["days_traded"],flush=True)
    stress={}
    for extra in (.10,.20):
        stress[str(extra)]={}
        for name in POLICIES[:2]:
            run=replay(pools,outcomes,days,name,extra)
            stress[str(extra)][name]={
                "trades":run["n"],"mean_R":run["trade_stats"]["avg_R"],
                "PF":run["trade_stats"]["PF"],
                "return_pct":run["return_model_pct"],
                "max_dd_pct":run["max_drawdown_pct"]}
    report={
        "kind":"KATARINA_FULL_M5_INTRADAY_FIRST_SCALPING_EXTREME_V5",
        "model_provenance":"New precommitted research hypotheses, NOT trained AI",
        "date_created_utc":datetime.now(timezone.utc).isoformat(),
        "full_M5_bars_evaluated":sum(p["candidate_summary"]["closed_bars_considered"] for p in per),
        "number_symbols_requested":len(symbols),
        "number_symbols_fetched":len(per),
        "sum_bars":sum(p["bars"] for p in per),
        "eligible_20_symbol_days":len(days) if len(symbols)==55 else None,
        "comparable_days":len(days),
        "candidate_windows":len(pools),
        "total_candidates":sum(len(q) for q in pools.values()),
        "model_fill_outcomes":len(outcomes),
        "failures":failures,
        "risk_policy":{"intraday_risk_pct":INTRADAY_RISK*100,
          "extreme_scalp_risk_pct":SCALP_RISK*100,
          "max_day_trades":MAX_TRADES_DAY,
          "max_daily_allocated_risk_pct":DAILY_RISK_CAP*100,
          "max_concurrent":1},
        "frozen_rules":{
          "intraday":"M5 trend-pullback + closed M15/H1 alignment, >2 prior corrective bars, displacement>=0.42 ATR, spread<=0.22 ATR",
          "extreme_scalping":"fresh 20-M5 bar sweep and reclaim, >=0.45 ATR wick, >1.25x broker tick volume, spread<=0.12 ATR and H1 aligned",
          "priority":"intraday first at same timestamp, extreme scalp only if no intraday there",
          "entry_exit":"next M5 open + adverse 1 broker point each side, OHLC conservative SL-first, intraday max 48 M5, scalp max 8 M5",
          "targets":"intraday 1.8R, scalp 1.3R; structural stop within ATR risk envelope",
          "fees":"historical bar-based spread + 0.03R intraday / 0.06R scalp add-on; +0.10R and +0.20R independent cost stress",
          "timestamps":"broker encoded epoch; historic timezone/DST UNVERIFIED",
        },
        "policies":summary,"cost_stress":stress,
        "per_symbol":per,
        "warnings":[
          "Fully scanned every available CLOSED M5 bar, but fast prefilter is a NEW rule-based candidate generator rather than every-candle heavy MarketDecisionPipeline",
          "Prior historical 2025-2026 market data have been inspected in other experiments: NO independent holdout",
          "Historical news releases and session/encoded broker clocks not point-in-time verified",
          "Bid/Ask spreads are per-M5 fields, NOT tick reconstruction; additional slippage and commissions are uncalibrated assumptions",
          "No minimum-lot feasibility, margin or correlated portfolio risk stress; modeled fixed fractional risk only",
          "Daily calendar based on broker encoded epoch; not guaranteed local Indonesia calendar",
          "Never trade live based solely on retrospective results",
          "Modeled risk and compounding do not imply steady daily profit"],
        "orders_sent":0,"live_execution_authorized":False,
        "elapsed_seconds":round(time.perf_counter()-start,1)
    }
    target=DEST/("FULL_M5_55_FINAL.json" if not requested else "FULL_M5_3PAIR_PILOT.json")
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    if not requested:
        csvpath=DEST/"COMBINED_POLICY_TRADES.csv"
        with csvpath.open("w",newline="",encoding="utf-8") as f:
            if chosen:
                w=csv.DictWriter(f,fieldnames=list(chosen[0]));w.writeheader();w.writerows(chosen)
    print("FINAL",json.dumps({"symbols":len(per),"full_M5":report["full_M5_bars_evaluated"],
        "days":len(days),"candidate_windows":len(pools),
        "total_candidates":report["total_candidates"],
        "policies":{k:{"trades":v["n"],"PF":v["trade_stats"]["PF"],
            "avgR":v["trade_stats"]["avg_R"],
            "positive_days":v["positive_trade_days"],
            "days_traded":v["days_traded"],
            "growth_pct":v["return_model_pct"],
            "maxdd_pct":v["max_drawdown_pct"]}
        for k,v in summary.items()},
        "extra_cost_stress":stress,"failures":failures,
        "duration":report["elapsed_seconds"]},ensure_ascii=False),flush=True)

if __name__=="__main__":main()