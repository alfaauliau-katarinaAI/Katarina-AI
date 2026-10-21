"""Synchronous 55-asset intraday opportunity test; read-only MT5 broker candles.

At encoded broker-clock 06:00 / 12:00 / 18:00, every symbol is evaluated using
only M5/M15/H1 candles CLOSED before the same checkpoint. Highest currently
ranked valid signal gets one risk-budgeted paper position per day.
There is NO peek at later opportunities during that day.

Research counterfactual: old historical news is not archived/verified.
Backtests are previously studied 2025/26 data, NOT independent OOS,
and M5 OHLC + historical spread are not executable tick prices.
"""
from __future__ import annotations
import csv, json, sys, time
from collections import defaultdict,Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import (
    OUT,TIMEFRAME,get_bars,sensors,bisected_indices,
    true_range_at,hypothetic_fill,stats,split)
from katarina.intelligence.market_decision_pipeline import MarketDecisionPipeline
from katarina.intelligence.multi_pair_arbitrator import (
    Opportunity,RiskLimits,portfolio_replay)
from katarina.intelligence.structural_entry_quality import _atr
SLOTS_BROKER_CLOCK=(6,12,18)
TARGET=OUT/"synchronous_multi_pair_daily_v4"
TARGET.mkdir(exist_ok=True,parents=True)

def checkpoints(a):
    """Candidate days determined from price history only, not trade outcomes."""
    first=datetime.fromtimestamp(int(a["time"][0]),timezone.utc).date()
    last=datetime.fromtimestamp(int(a["time"][-1]),timezone.utc).date()
    current=first
    while current<=last:
        for hour in SLOTS_BROKER_CLOCK:
            yield int(datetime(current.year,current.month,current.day,hour,
                               tzinfo=timezone.utc).timestamp())
        current+=timedelta(days=1)

def main():
    start=time.perf_counter()
    if not mt5.initialize():raise RuntimeError("MT5 initialization failed")
    ti=mt5.terminal_info()
    if ti is None or ti.trade_allowed:
        mt5.shutdown()
        raise RuntimeError("Refuse to run paper replay with live trading enabled")
    source=sorted(OUT.glob("*_vx.json"))
    symbols=[json.loads(p.read_text(encoding="utf-8"))["symbol"]
             for p in source if json.loads(p.read_text(encoding="utf-8")).get("status")=="OK"]
    if len(symbols)!=55:raise RuntimeError("Expected all 55 historical symbol reports")
    pipeline=MarketDecisionPipeline()
    pools=defaultdict(list)
    coverage=Counter();veto=Counter();diagnostics=Counter()
    outcomes={};per_symbol=[]
    for i,symbol in enumerate(symbols):
        mt5.symbol_select(symbol,True)
        info=mt5.symbol_info(symbol)
        if info is None:raise RuntimeError("Missing broker symbol information "+symbol)
        point=float(info.point)
        a_by_tf={};hist={}
        for tf,(frame,sec,n) in TIMEFRAME.items():
            data=get_bars(symbol,frame,n)
            if data is None:raise RuntimeError("Missing candles: "+symbol+" "+tf)
            a_by_tf[tf]=data;hist[tf]=data["time"].astype(np.int64)
        m5=a_by_tf["M5"]
        c=Counter();valid=0
        for cut in checkpoints(m5):
            index=int(np.searchsorted(hist["M5"],cut,side="left"))
            if index>=len(m5) or index<120 or int(hist["M5"][index])!=cut:
                c["no_next_entry_bar_at_checkpoint"]+=1;continue
            if int(hist["M5"][index-1])!=cut-300:
                c["missing_previous_closed_M5"]+=1;continue
            parts={}
            for tf,(frame,sec,n) in TIMEFRAME.items():
                end=bisected_indices(hist[tf],cut,sec)
                if end<90 or end>len(a_by_tf[tf]):
                    c["short_MTF_"+tf]+=1;break
                lastclose=int(hist[tf][end-1])+sec
                if cut-lastclose>2*sec or lastclose>cut:
                    c["stale_MTF_"+tf]+=1;break
                parts[tf]=sensors(a_by_tf[tf][end-90:end],sec)
            if len(parts)<3:continue
            spread=float(m5["spread"][index-1])*point
            if spread<=0:
                c["unobserved_spread"]+=1;continue
            dt=datetime.fromtimestamp(cut,timezone.utc)
            coverage[cut]+=1
            valid+=1
            obs=pipeline.evaluate(symbol=symbol,candles=parts,
                as_of_utc=dt,actual_spread=spread,
                broker_session_open=True,data_fresh=True,
                news_blackout=False,news_context_verified=True,
                use_structural_entry_gate=False,
                use_semantic_setup_gate=False,
                instrument_point=point)
            if obs.action not in ("BUY","SELL"):
                c["brain_WAIT"]+=1;continue
            q=obs.entry_quality;s=obs.semantic_setup
            if q is None or s is None:
                c["missing_evidence"]+=1;continue
            c["raw_technical_candidates"]+=1
            if not q.eligible:
                c["quality_reject"]+=1;continue
            if not s.pattern_confirmed:
                c["semantics_reject"]+=1;continue
            recent_atr=_atr(parts["M5"])
            if not recent_atr or recent_atr<=0:
                c["atr_missing"]+=1;continue
            candidate=Opportunity(
                symbol=symbol,cut_utc=dt,side=obs.action,
                playbook=obs.playbook,score=q.score,
                structural_rr=q.geometric_room_R or 0.,
                spread_atr=spread/recent_atr,
                semantic_confirmed=True,quality_eligible=True,
                fresh=True,news_verified=False)
            pools[cut].append(candidate)
            c["strict_candidates"]+=1
            atr=true_range_at(m5,index-1)
            if atr is not None and atr>0:
                side=1 if obs.action=="BUY" else -1
                tr=hypothetic_fill(m5,index-1,side,point,atr)
                if tr is not None:
                    outcomes[(symbol,cut)]=dict(tr,symbol=symbol,
                                                 playbook=obs.playbook,side=obs.action)
                else:c["fill_model_unavailable"]+=1
            else:c["atr_at_signal_invalid"]+=1
        per_symbol.append(dict(symbol=symbol,
             from_m5=datetime.fromtimestamp(int(m5["time"][0]),timezone.utc).isoformat(),
             through_m5=datetime.fromtimestamp(int(m5["time"][-1]),timezone.utc).isoformat(),
             valid_checkpoints=valid,counts=dict(c)))
        diagnostics.update(c)
        print("PAIR",i+1,"/55",symbol,"checks",valid,
              "raw",c["raw_technical_candidates"],
              "strict",c["strict_candidates"],
              "time",round(time.perf_counter()-start,1),flush=True)
        del a_by_tf,hist,m5
    mt5.shutdown()
    slots=sorted((datetime.fromtimestamp(cut,timezone.utc),tuple(items))
                 for cut,items in pools.items())
    # Union of actually observed market-session dates: includes NO SIGNAL dates.
    scan_slots=sorted((datetime.fromtimestamp(cut,timezone.utc),pools.get(cut,()))
                      for cut in coverage.keys())
    risk=RiskLimits(risk_fraction=.0025,max_trades_per_day=1,
                    max_portfolio_exposure=1,daily_loss_limit_fraction=.005)
    ranked=portfolio_replay(scan_slots,outcomes,risk,hypothesis_news_clear=True)
    blind_slots=[]
    from dataclasses import replace
    for dt,items in scan_slots:
        # Control picks symbol alphabetically at same checkpoint, not by score.
        blind_slots.append((dt,tuple(replace(x,score=.75,
                   structural_rr=1.5,spread_atr=.10) for x in items)))
    blind=portfolio_replay(blind_slots,outcomes,risk,hypothesis_news_clear=True)
    def performance(run):
        ts=run["trades"];r=stats(ts)
        day_r=defaultdict(float)
        monthly=defaultdict(list)
        for t in ts:
            day_r[t["day"]]+=t["R"]
            monthly[t["day"][:7]].append(t)
        dates={datetime.fromtimestamp(cut,timezone.utc).date().isoformat()
               for cut in coverage}
        dsets={datetime.fromtimestamp(cut,timezone.utc).date().isoformat()
               for cut,items in pools.items() if items}
        return dict(
            **{k:v for k,v in run.items() if k!="trades"},
            trade_stats=r,
            trade_days=len(day_r),day_with_at_least_one_valid_signal=len(dsets),
            days_no_trade=len(dates-set(day_r)),
            positive_trade_days=sum(x>0 for x in day_r.values()),
            negative_trade_days=sum(x<0 for x in day_r.values()),
            positive_day_pct_of_observed=round(100*sum(x>0 for x in day_r.values())/
                                                max(1,len(dates)),2),
            positive_pct_of_traded_days=round(100*sum(x>0 for x in day_r.values())/
                                               max(1,len(day_r)),2),
            monthly={k:stats(v) for k,v in sorted(monthly.items())},
            by_period={label:stats([t for t in ts
                           if split(int(datetime.fromisoformat(t["checkpoint_utc"]).timestamp()))==label])
                 for label in ("2025_available","2026_Jan_May","2026_Jun_Oct")},
            trades=ts)
    report={
        "kind":"KATARINA_SYNCHRONOUS_MULTI_ASSET_RANK_55_READ_ONLY",
        "rules_frozen_before_run":{
          "checkpoints_broker_encoded_hours":SLOTS_BROKER_CLOCK,
          "candidate":"MarketDecisionPipeline BUY/SELL; StructuralEntryQuality eligible AND real semantic price event",
          "rank":"higher q.score, then higher geometric_room_R up to 3.5, then cheaper spread_to_ATR",
          "trade_limit":"max one paper entry per UTC day, max one concurrent position, 0.25% fractional risk",
          "real_time":"ranking from simultaneous closed candles only; no lookahead to later signals",
          "news":"ALL HISTORICAL news assumed clear only for technical diagnostic; not verified",
          "exit":"original M5 next-open, 1.2 ATR stop, 1.8R TP, max 24 bars, modeled costs 0.03R",
        },
        "broker_live_order_sent":0,"live_execution_authorized":False,
        "independent_out_of_sample":False,
        "number_of_symbols":len(symbols),
        "historical_time_series_coverage":{
          "valid_symbol_session_checks":sum(coverage.values()),
          "unique_checkpoints":len(coverage),
          "days_with_any_market_checkpoint":len({datetime.fromtimestamp(c,timezone.utc).date()
                                     for c in coverage}),
          "avg_symbols_scanned_per_checkpoint":round(sum(coverage.values())/max(1,len(coverage)),2),
          "checkpoints_with_20_plus_symbols":sum(n>=20 for n in coverage.values()),
          "simultaneous_multi_candidate_sessions":sum(len(v)>1 for v in pools.values()),
          "max_simultaneous_candidates":max((len(v) for v in pools.values()),default=0),
        },
        "diagnostics":dict(diagnostics),
        "ranked_policy":performance(ranked),
        "alphabetical_control":performance(blind),
        "per_symbol":per_symbol,
        "limitations":[
          "Historical price series and playbooks already inspected: no independent OOS",
          "Only three fixed UTC snapshots daily, NOT 288 M5 bars nor all intraday signals",
          "Date/time uses MT5 bar timestamp; broker UTC/DST not fully reconciled",
          "No verified historical news, scheduled macro blackout, or broker tick execution",
          "No margin usage, position-size rounding, instrument leverage or inter-market gap risk",
          "Fixed-fraction R equity approximates closed-trade outcomes, no daily floating MTM",
          "News unverified means actual safe production decision remains WAIT",
          "If zero or too few valid setups, correct action is NO TRADE; profit every day cannot be guaranteed",
        ],
        "elapsed_sec":round(time.perf_counter()-start,1)
    }
    (TARGET/"FINAL_DAILY_RANK_55.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    with (TARGET/"ranked_trades.csv").open("w",newline="",encoding="utf-8") as f:
        if ranked["trades"]:
            writer=csv.DictWriter(f,fieldnames=list(ranked["trades"][0]));writer.writeheader();writer.writerows(ranked["trades"])
    print("FINAL",json.dumps({
        "symbols":len(symbols),"coverage":report["historical_time_series_coverage"],
        "diagnostics":report["diagnostics"],
        "ranked":{k:v for k,v in report["ranked_policy"].items() if k not in ("trades","monthly")},
        "alphabetical":{k:v for k,v in report["alphabetical_control"].items() if k not in ("trades","monthly")},
        "elapsed":report["elapsed_sec"]},ensure_ascii=False),flush=True)

if __name__=="__main__":main()