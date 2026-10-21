"""V6: independent fast scanner -> causal Brain -> cross-pair rank, read-only.

Every available closed M5 bar is scanned. A trend-pullback V5 technical
candidate must meet an actual closed-candle semantic pullback and entry-quality
gate *before* full Explainable Market Brain evaluation. The production
Brain must agree on side, playbook and eligibility. Only then is the rank calculated across the selected broker-supported
priority markets (the original 55-symbol V6 output remains historical).

No future trade R is examined by selector; the outcome is filled separately.
Historical macro-news is ASSUMED verified only for paper counterfactual.
This is NOT independent OOS; the 2025/26 price tape was already inspected.
"""
from __future__ import annotations
import argparse,csv,json,sys,time,math
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import OUT,get_bars,TIMEFRAME
from backtest_full_m5_intraday_scalp_v5 import replay
from katarina.intelligence.cognition.market_decision_pipeline import MarketDecisionPipeline
from katarina.intelligence.broker.broker_scan_universe import resolve_broker_symbols
from katarina.intelligence.lab.research_signal_ablation import eligible_for_research
from katarina.intelligence.perception.semantic_setup_truth import CausalSetupValidator
from katarina.intelligence.perception.structural_entry_quality import StructuralEntryQuality
from katarina.intelligence.perception.calendar_history import load_calendar_history
from katarina.intelligence.lab.intraday_scalp_research import vector_prefilter,fill_next_open

DEST=OUT/"intraday_brain_integrated_v6"
DEST.mkdir(parents=True,exist_ok=True)
RISK=.0025

from katarina.intelligence.lab.unified_intraday_gate import (check_candidate, min_capital_for_broker)

def main():
    global DEST
    ap=argparse.ArgumentParser()
    ap.add_argument("--symbols",default="")
    ap.add_argument("--bars",type=int,default=90000)
    ap.add_argument('--start-date',help='Inclusive UTC calendar date; monthly history instead of last-N bars')
    ap.add_argument('--end-date',help='Exclusive UTC calendar date; current partial day is capped at now')
    ap.add_argument("--allow-scalp-research",action="store_true")
    ap.add_argument("--minimum-signal-score",type=float,default=0.0,
                    help="Research-only causal candidate floor; default preserves V6")
    ap.add_argument("--research-side",choices=("BOTH","BUY","SELL"),default="BOTH",
                    help="Research-only side ablation; default preserves V6")
    ap.add_argument("--output-dir",type=Path,default=None,
                    help="Isolated research output: avoid overwriting earlier receipts")
    args=ap.parse_args()
    if bool(args.start_date)!=bool(args.end_date):
        ap.error('start-date and end-date must be supplied together')
    start=end=None
    if args.start_date:
        start=datetime.strptime(args.start_date,'%Y-%m-%d').replace(tzinfo=timezone.utc)
        end=datetime.strptime(args.end_date,'%Y-%m-%d').replace(tzinfo=timezone.utc)
        if not 0<(end-start).days<=730 or start>=datetime.now(timezone.utc):
            ap.error('historical range must be 1..730 days and start in the past')
    if not math.isfinite(args.minimum_signal_score) or not 0<=args.minimum_signal_score<=1:
        raise ValueError("invalid_research_signal_floor")
    if args.output_dir is not None:
        DEST=args.output_dir.resolve()
        DEST.mkdir(parents=True,exist_ok=True)
    if not 500<=args.bars<=90000:raise ValueError("invalid_bar_count")
    if not mt5.initialize():raise RuntimeError("mt5_unavailable")
    if mt5.terminal_info() is None or mt5.terminal_info().trade_allowed:
        mt5.shutdown();raise RuntimeError("live_trading_must_be_disabled")
    paths=sorted(OUT.glob("*_vx.json"))
    symbols=[json.loads(p.read_text(encoding="utf-8"))["symbol"] for p in paths
             if json.loads(p.read_text(encoding="utf-8")).get("status")=="OK"]
    if args.symbols:
        wanted=[x.strip() for x in args.symbols.split(",") if x.strip()]
        if any(k not in symbols for k in wanted):raise ValueError("unknown_archived_symbol")
        # Explicit research replay override; never a live-trading approval.
        symbols=wanted
    else:
        catalog=mt5.symbols_get()
        if catalog is None:
            mt5.shutdown();raise RuntimeError("broker_catalog_unavailable")
        selection=resolve_broker_symbols(catalog)
        archive=set(symbols)
        symbols=[s for s in selection.symbols if s in archive]
        if not symbols:
            mt5.shutdown();raise RuntimeError("no_priority_symbol_with_archived_data")
    sem=CausalSetupValidator()
    quality=StructuralEntryQuality()
    brain=MarketDecisionPipeline()
    pools=defaultdict(list)
    outcomes={};coverage=Counter()
    specs={};feasible={};counts=Counter();per=[]
    started=time.perf_counter();lastdata=None
    for n,sym in enumerate(symbols):
        mt5.symbol_select(sym,True)
        info=mt5.symbol_info(sym)
        if info is None:raise RuntimeError("symbol_info_missing_"+sym)
        point=float(info.point)
        frame={}
        history_coverage={}
        for k,(tf,sec,count) in TIMEFRAME.items():
            if start is not None:
                a,history_coverage[k]=load_calendar_history(mt5.copy_rates_range,sym,tf,sec,start,end)
            else:
                a=get_bars(sym,tf,min(count,args.bars) if k=="M5" else count)
            if a is None:raise RuntimeError("missing_"+k+"_"+sym)
            frame[k]=a
        picks,scan=vector_prefilter(sym,frame["M5"],frame["M15"],frame["H1"],point)
        clocks={k:a["time"].astype(np.int64) for k,a in frame.items()}
        for day,count in zip(*np.unique(clocks["M5"]//86400,return_counts=True)):
            if count>=60:coverage[int(day)]+=1
        local=Counter()
        for x in picks:
            counts["all_fast_candidates"]+=1
            if x.mode=="SCALP_EXTREME" and not args.allow_scalp_research:
                counts["scalp_disabled"]+=1
                continue
            # Causal research-only gates; applied BEFORE semantic / risk /
            # future outcome scoring and before the cross-symbol ranking.
            if not eligible_for_research(
                    x.score,x.side,minimum_score=args.minimum_signal_score,
                    research_side=args.research_side):
                counts["research_score_or_side_rejected"]+=1
                local["research_score_or_side_rejected"]+=1
                continue
            candidate,why=check_candidate(x,frame["M5"],frame["M15"],frame["H1"],
                clocks,point,sem,quality,brain)
            local[why]+=1
            counts[why]+=1
            if candidate is None:continue
            # The fill model can later reject a trade. This future information
            # NEVER changes ranking; it is consulted only after top choice.
            pools[x.cut].append(x)
            filled=fill_next_open(frame["M5"],x,point)
            if filled:
                key=(x.symbol,x.cut,x.mode,x.side)
                outcomes[key]=filled
                m=min_capital_for_broker(info,float(filled["risk_price"]),x.mode)
                feasible[key]=m
                local["fillable"]+=1
            else:local["not_fillable"]+=1
        specs[sym]=dict(point=point,volume_min=float(info.volume_min),
             volume_step=float(info.volume_step),
             tick_size=float(info.trade_tick_size),
             tick_loss_value=float(info.trade_tick_value_loss),
             stop_level=float(info.trade_stops_level))
        per.append(dict(symbol=sym,candles=len(frame["M5"]),calendar_history_coverage=history_coverage,
             first_timestamp=int(clocks["M5"][0]),
             last_timestamp=int(clocks["M5"][-1]),
             fast_scan=scan,pass_counts=dict(local)))
        print("PAIR",n+1,"/",len(symbols),sym,
              "fast_intraday",scan["intraday"],"passed",local["pass"],
              "sec",round(time.perf_counter()-started,1),flush=True)
        del frame
    mt5.shutdown()
    eligible_days={datetime.fromtimestamp(int(day)*86400,timezone.utc).date().isoformat()
         for day,count in coverage.items() if count>=min(20,len(symbols))}
    pools={cut:items for cut,items in pools.items()
           if datetime.fromtimestamp(cut,timezone.utc).date().isoformat() in eligible_days}
    variants={}
    def run_variant(label,policy="INTRADAY_ONLY",capital=None,extra_cost=0.):
        if capital is None:
            sub=pools
        else:
            # Current broker minimum contract feasibility. Drop candidates
            # based on *signal-known stop geometry*, but V5 filled stop risk
            # can depend on next candle open. Mark as scenario-only and never
            # interpret as point-in-time investable portfolio validation.
            sub={t:[x for x in ps
                 if ((x.symbol,x.cut,x.mode,x.side) in feasible and
                     feasible[(x.symbol,x.cut,x.mode,x.side)] is not None and
                     feasible[(x.symbol,x.cut,x.mode,x.side)]<=capital)]
                 for t,ps in pools.items()}
        run=replay(sub,outcomes,eligible_days,policy,additional_cost=extra_cost)
        variants[label]={k:v for k,v in run.items() if k!="trades"}
        return run
    primary=run_variant("BRAIN_INTRADAY_0_EXTRA_COST")
    stressed=run_variant("BRAIN_INTRADAY_PLUS_0_10R",extra_cost=.10)
    stressed2=run_variant("BRAIN_INTRADAY_PLUS_0_20R",extra_cost=.20)
    control=run_variant("BRAIN_ALPHABETICAL_CONTROL",policy="ALPHABETICAL_MATCHED")
    risk1000=run_variant("BROKER_MIN_LOT_SCENARIO_1000USD",capital=1000)
    risk5000=run_variant("BROKER_MIN_LOT_SCENARIO_5000USD",capital=5000)
    if args.allow_scalp_research:
        combined=run_variant("BRAIN_INTRADAY_FIRST_SCALP_EXPERIMENT",
                             policy="INTRADAY_FIRST_SCALP_EXTREME")
        scalp=run_variant("BRAIN_SCALP_ONLY",policy="SCALP_EXTREME_ONLY")
    else:
        combined=scalp=None
    full=dict(
        kind="KATARINA_V6_CAUSAL_BRAIN_GATED_FULL_M5_PORTFOLIO",
        requested_start_date=args.start_date,requested_end_date_exclusive=args.end_date,
        calendar_history_mode=start is not None,
        experimental_minimum_signal_score=args.minimum_signal_score,
        experimental_research_side=args.research_side,
        experimental_research_gate_only=True,
        research_only_no_live_model_change=True,
        scan_symbols=len(symbols),M5_closed_bars_scanned=sum(p["fast_scan"]["closed_bars_considered"] for p in per),
        raw_intraday_candidate_count=sum(p["fast_scan"]["intraday"] for p in per),
        raw_scalp_candidate_count=sum(p["fast_scan"]["scalp_extreme"] for p in per),
        passes=sum(v for k,v in counts.items() if k=="pass"),
        rejections=dict(counts),matched_opportunity_windows=len(pools),
        modeled_fills=len(outcomes),market_coverage_days=len(eligible_days),
        methodology=[
           "All available M5 closed bars scanned with a vectorized initial technical prefilter",
           "V6 requires original ExplainableMarketDecisionPipeline matching BUY/SELL and playbook",
           "CausalSetupValidator and StructuralEntryQuality must both agree before portfolio ranking",
           "Only then choose top at exact shared broker-coded timestamp, WITHOUT reading future R",
           "News assumed verified hypothetically because point-in-time archive unavailable; actual trades WAIT",
           "Score/side gates use only candidate-known values before future return is examined; any tuning on these previously inspected dates is not unseen OOS",
           "Exit uses V5 M5 OHLC next-open model, spread, one adverse point each side and .03R fee",
           "Fee stress +.10/.20R; actual broker commission and historical bid/ask intrabar not reconciled",
           "Scalping disabled unless explicitly requested separately; never live",
           "Hypothetical $1000/$5000 minimum contract constraints use CURRENT broker symbol tick values and retrospective entry stop distances",
        ],
        results=variants,per_symbol=per,
        limitations=[
          "Same previously inspected 2025-2026 data => NOT independent unseen OOS",
          "A V5 fast signal filtered by the old Brain is NOT an unbiased evaluation of all original Brain signals",
          "Current symbol conversion, minimum lot, and margin may have differed in historical periods",
          "For modeled position sizing, future entry open can shift stop size; scenario minimum-lot feasibility is after-fill diagnostic, NOT exact causal risk policy",
          "Historical tick fills and broker commission archive not fully available",
          "Volatility gap and historical news veto unverified",
          "Broker historical UTC/DST not reconciled, dates are broker coded",
          "Modeled return is not real money and does not guarantee positive days",
        ],
        news_history_verified=False,independent_oos=False,
        execution_authorized=False,orders_sent=0,
        elapsed_seconds=round(time.perf_counter()-started,1))
    suffix="ALL_55" if len(symbols)==55 else "PILOT"
    (DEST/(suffix+"_RESULT.json")).write_text(
         json.dumps(full,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    with (DEST/(suffix+"_BRAIN_TRADES.csv")).open("w",newline="",encoding="utf-8") as f:
        if primary["trades"]:
            fields=list(primary["trades"][0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            w.writerows(primary["trades"])
    print("FINAL",json.dumps({"symbols":len(symbols),
        "raw_intraday":full["raw_intraday_candidate_count"],
        "passed":full["passes"],"days":len(eligible_days),
        "variants":{k:{"trade_count":v["n"],
          "meanR":v["trade_stats"]["avg_R"],
          "PF":v["trade_stats"]["PF"],
          "model_return_pct":v["return_model_pct"],
          "drawdown_pct":v["max_drawdown_pct"],
          "positive_days":v["positive_trade_days"],
          "days_traded":v["days_traded"]}
         for k,v in variants.items()},
        "rejections":dict(counts),"elapsed":full["elapsed_seconds"]},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
