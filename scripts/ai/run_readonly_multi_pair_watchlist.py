"""One-off, broker-adaptive, read-only priority-market watchlist.

A plausible technical setup is NEVER an executable signal without verified
news + account-specific risk/quote checks. No orders or risk governor edits.
"""
from __future__ import annotations
import json,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
import MetaTrader5 as mt5
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from katarina.intelligence.cognition.market_decision_pipeline import MarketDecisionPipeline,SensorCandle
from katarina.intelligence.perception.structural_entry_quality import _atr
from katarina.intelligence.broker.broker_clock_alignment import infer_clock_shift
from katarina.intelligence.broker.broker_scan_universe import resolve_broker_symbols
from katarina.intelligence.perception.multi_pair_arbitrator import (
    Opportunity,select_at_checkpoint)
OUT=Path(r"C:\KatarinaDev\decision-backtest-20261012\synchronous_multi_pair_daily_v4")
TIMEFRAME={"M5":(mt5.TIMEFRAME_M5,300),"M15":(mt5.TIMEFRAME_M15,900),
           "H1":(mt5.TIMEFRAME_H1,3600)}
def main():
    if not mt5.initialize():raise RuntimeError("broker_unavailable")
    ti=mt5.terminal_info()
    if ti is None or ti.trade_allowed:
        mt5.shutdown();raise RuntimeError("refuse_live_enabled")
    now=datetime.now(timezone.utc)
    brain=MarketDecisionPipeline()
    catalog=mt5.symbols_get()
    if catalog is None:
        mt5.shutdown();raise RuntimeError("broker_catalog_unavailable")
    selection=resolve_broker_symbols(catalog)
    symbols=list(selection.symbols)
    # Broker in this VPS currently encodes market ticks around UTC+3.
    # Infer CURRENT displacement from a majority of independent fresh ticks;
    # never silently assume the historical DST schedule or enable execution.
    tick_clocks={}
    for symbol in symbols:
        mt5.symbol_select(symbol,True)
        q=mt5.symbol_info_tick(symbol)
        if q is not None and q.bid>0 and q.ask>=q.bid:
            tick_clocks[symbol]=int(q.time)
    clock=infer_clock_shift(tick_clocks,now.timestamp())
    if not clock.suitable_for_readonly_snapshot:
        mt5.shutdown()
        raise RuntimeError("unable_to_infer_consistent_current_broker_clock")
    raw_clock_shift_sec=clock.observed_hours_shift*3600
    opportunities=[];fail=[];reason_counts={};eligible_checks=0
    for symbol in symbols:
        mt5.symbol_select(symbol,True)
        info=mt5.symbol_info(symbol)
        tick=mt5.symbol_info_tick(symbol)
        if info is None or tick is None or tick.bid<=0 or tick.ask<tick.bid:
            fail.append({"symbol":symbol,"reason":"missing_broker_quote"});continue
        time_delta=(now-datetime.fromtimestamp(
            tick.time-raw_clock_shift_sec,timezone.utc)).total_seconds()
        if not -15<=time_delta<=180:
            fail.append({"symbol":symbol,"reason":"stale_tick"});continue
        spread=float(tick.ask-tick.bid)
        frames={};fresher=True
        for tf,(timeframe,secs) in TIMEFRAME.items():
            a=mt5.copy_rates_from_pos(symbol,timeframe,1,120)
            if a is None or len(a)<90:
                fresher=False;break
            from_timestamp=lambda t:datetime.fromtimestamp(
                int(t)+secs-raw_clock_shift_sec,timezone.utc)
            frames[tf]=[SensorCandle(from_timestamp(x["time"]),float(x["open"]),
                          float(x["high"]),float(x["low"]),float(x["close"]),
                          float(x["tick_volume"])) for x in a]
            if not (timedelta(seconds=-15)<=now-frames[tf][-1].closed_at_utc<=timedelta(seconds=secs*2)):
                fresher=False
        if not fresher:
            fail.append({"symbol":symbol,"reason":"incomplete_or_stale_frames"});continue
        eligible_checks+=1
        obs=brain.evaluate(symbol=symbol,candles=frames,
            as_of_utc=now,actual_spread=spread,broker_session_open=True,
            data_fresh=True,news_blackout=False,
            news_context_verified=True, # TECHNICAL WHAT-IF ONLY
            instrument_point=float(info.point))
        q=obs.entry_quality;s=obs.semantic_setup
        if obs.action not in ("BUY","SELL") or q is None or s is None:
            reason_counts["brain_WAIT"]=reason_counts.get("brain_WAIT",0)+1;continue
        if not q.eligible or not s.pattern_confirmed:
            reason_counts["entry_or_semantics_veto"]=reason_counts.get("entry_or_semantics_veto",0)+1
            continue
        atr=_atr(frames["M5"])
        if atr is None or atr<=0:continue
        opportunities.append(Opportunity(
            symbol=symbol,cut_utc=now,side=obs.action,
            playbook=obs.playbook,score=q.score,
            structural_rr=q.geometric_room_R or 0.,
            spread_atr=spread/atr,fresh=True,
            semantic_confirmed=True,quality_eligible=True,
            news_verified=False))
    mt5.shutdown()
    # Without a VERIFIED news provider, true actionable selection is ALWAYS NONE.
    real=select_at_checkpoint(opportunities,cut_utc=now)
    hypo=select_at_checkpoint(opportunities,cut_utc=now,hypothesis_news_clear=True)
    report=dict(kind="KATARINA_LIVE_READONLY_MULTI_PAIR_WATCHLIST",
        as_of_utc=now.isoformat(),symbols_scanned=len(symbols),
        broker_symbol_matches=selection.matches,
        unavailable_broker_symbols=list(selection.unavailable),
        broker_raw_clock_shift_hours=clock.observed_hours_shift,
        broker_clock_alignment_confirming_symbols=clock.confirming_symbols,
        broker_clock_historical_dst_verified=False,
        quote_and_frames_fresh=eligible_checks,
        data_skips=fail,decision_counts=reason_counts,
        technical_candidates=len(opportunities),
        hypothetical_top=[
          dict(symbol=x.symbol,side=x.side,playbook=x.playbook,
               score=x.score,structural_room_r=x.structural_rr,
               spread_to_atr=round(x.spread_atr,4))
          for x in hypo.valid[:10]],
        production_selection=real.selected.symbol if real.selected else None,
        production_action="WAIT",
        actual_verified_news=False,
        broker_orders_sent=0,live_execution_authorized=False,
        warnings=("Technical ranking assumes unverified news-clear condition",
                  "No position sizing/margin/portfolio live authority",
                  "No profit prediction or guarantee"))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"CURRENT_READONLY_WATCHLIST.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("WATCHLIST",json.dumps({
      "symbols":len(symbols),"quotes_fresh":eligible_checks,
      "technical_candidates":len(opportunities),
      "production_action":"WAIT","no_orders":True,
      "hypothetical_top":report["hypothetical_top"][:4]},ensure_ascii=False))
if __name__=="__main__":main()