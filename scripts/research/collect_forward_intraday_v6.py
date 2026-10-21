"""Forward paper snapshot collector after V6 model freeze, read-only.

Records causal M5 technical candidates and checked Brain vetoes AFTER freeze.
Does not simulate real P/L until future M5 candles actually close.
Historical broker clock and news costs remain unverified.
"""
from __future__ import annotations
import json,sys
from datetime import datetime,timezone
from pathlib import Path
import MetaTrader5 as mt5

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import OUT,get_bars,TIMEFRAME
from backtest_unified_intraday_brain_v6 import check_candidate
from katarina.intelligence.broker.broker_clock_alignment import infer_clock_shift
from katarina.intelligence.broker.broker_scan_universe import resolve_broker_symbols
from katarina.intelligence.lab.intraday_scalp_research import vector_prefilter
from katarina.intelligence.cognition.market_decision_pipeline import MarketDecisionPipeline
from katarina.intelligence.perception.structural_entry_quality import StructuralEntryQuality
from katarina.intelligence.perception.semantic_setup_truth import CausalSetupValidator
from collections import Counter

DIR=OUT/"intraday_brain_integrated_v6"/"prospective"
DIR.mkdir(exist_ok=True,parents=True)
FREEZE=DIR/"FREEZE_CONTRACT.json"
JOURNAL=DIR/"FORWARD_SNAPSHOTS.jsonl"

def main():
    now=datetime.now(timezone.utc)
    if not FREEZE.exists():
        freeze=dict(version="INTRADAY_BRAIN_V6",
            created_utc=now.isoformat(),
            never_pretend_previously_inspected_data_are_oos=True,
            evaluation="no-order paper only; full M5, Brain+Semantics+Quality",
            minimum_future_observations_before_decision=150,
            independent_unseen_holdout_ready=False)
        FREEZE.write_text(json.dumps(freeze,indent=2),encoding="utf-8")
    freeze=json.loads(FREEZE.read_text(encoding="utf-8"))
    if not mt5.initialize():raise RuntimeError("broker_unavailable")
    term=mt5.terminal_info()
    if term is None or term.trade_allowed:
        mt5.shutdown();raise RuntimeError("refuse_trading_enabled")
    catalog=mt5.symbols_get()
    if catalog is None:
        mt5.shutdown();raise RuntimeError("broker_catalog_unavailable")
    selection=resolve_broker_symbols(catalog)
    symbols=list(selection.symbols)
    ticks={}
    for s in symbols:
        mt5.symbol_select(s,True)
        quote=mt5.symbol_info_tick(s)
        if quote and quote.bid>0 and quote.ask>=quote.bid:
            ticks[s]=int(quote.time)
    clock=infer_clock_shift(ticks,now.timestamp())
    if not clock.suitable_for_readonly_snapshot:
        mt5.shutdown();raise RuntimeError("unreliable_broker_clock")
    broker_now=now.timestamp()+3600*clock.observed_hours_shift
    brain=MarketDecisionPipeline()
    q=StructuralEntryQuality(); sem=CausalSetupValidator()
    checked=Counter();candidate_rows=[]
    for symbol in symbols:
        tick=mt5.symbol_info_tick(symbol)
        info=mt5.symbol_info(symbol)
        if tick is None or info is None or tick.bid<=0 or tick.ask<=tick.bid:
            checked["bad_quote"]+=1;continue
        if not -15<broker_now-int(tick.time)<180:
            checked["quote_stale"]+=1;continue
        bars={}
        for frame in ("M5","M15","H1"):
            tf,sec,_=TIMEFRAME[frame]
            b=get_bars(symbol,tf,360 if frame=="M5" else 135)
            if b is None or len(b)<95:
                checked["frame_missing"]+=1;break
            bars[frame]=b
        if len(bars)!=3:continue
        m5=bars["M5"]
        last_close=int(m5["time"][-1])+300
        if not 0<=broker_now-last_close<=600:
            checked["last_M5_stale"]+=1;continue
        picks,_=vector_prefilter(symbol,m5,bars["M15"],bars["H1"],
                      float(info.point),allow_unresolved_latest=True)
        now_candidates=[x for x in picks if x.idx==len(m5)-1 and x.mode=="INTRADAY"]
        checked["fresh_market_evaluated"]+=1
        if not now_candidates:continue
        clocks={k:v["time"] for k,v in bars.items()}
        for x in now_candidates:
            accepted,why=check_candidate(x,bars["M5"],bars["M15"],bars["H1"],
                  clocks,float(info.point),sem,q,brain)
            checked[why]+=1
            candidate_rows.append({
                "symbol":symbol,"raw_broker_candle_cut":x.cut,
                "approx_cut_utc":datetime.fromtimestamp(
                   x.cut-3600*clock.observed_hours_shift,timezone.utc).isoformat(),
                "mode":x.mode,"side":x.side,
                "scanner_score":x.score,
                "brain_approved_for_research":accepted is not None,
                "veto_reason":why,"actual_news_verified":False,
                "execution_authorized":False})
    mt5.shutdown()
    # We only start OOS accounting with observations after model freeze.
    # No unverifiable historical P/L is appended as forward performance.
    report=dict(as_of_utc=now.isoformat(),freeze_utc=freeze["created_utc"],
        symbol_count=len(symbols),scanned=dict(checked),
        broker_symbol_matches=selection.matches,
        unavailable_broker_symbols=list(selection.unavailable),
        broker_current_clock_hours=clock.observed_hours_shift,
        tick_consensus=clock.confirming_symbols,
        technical_candidates_at_latest_m5=candidate_rows,
        actual_action="WAIT",news_context_verified=False,
        new_closed_trade_outcomes=0,
        independent_holdout_mature=False,
        orders_sent=0)
    with JOURNAL.open("a",encoding="utf-8") as f:
        f.write(json.dumps(report,ensure_ascii=False)+"\n")
    (DIR/"LATEST_FORWARD_STATUS.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("FORWARD",json.dumps({
      "symbols":len(symbols),"fresh_checked":checked["fresh_market_evaluated"],
      "candidate_at_latest":len(candidate_rows),
      "brain_approved":sum(x["brain_approved_for_research"] for x in candidate_rows),
      "oos_closed_trades":0,"production":"WAIT","orders_sent":0,
    },ensure_ascii=False),flush=True)
if __name__=="__main__":main()