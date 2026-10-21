"""Tick-by-tick hypothetical SL/TP from existing immutable broker observations.

READ ONLY. Strictly no real fills, trained prediction, news backfill,
broker commissions or trading activation. True bid/ask quotes, no OHLC
interpolation, and unverified/missing tick paths invalidate observations.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from statistics import mean
import sys

SCRIPT_DIR=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPT_DIR))
sys.path.insert(0,str(SCRIPT_DIR.parents[1]/"src"))
from historical_shadow_ticks import bars,snapshot_hash
from historical_cost_sensitivity import load

UTC=timezone.utc
TIMEFRAMES={"M1_M5":(60,"m1_evidence_sha256"),"M5_M15":(300,"m5_evidence_sha256")}
CONFIG=((1.0,1.0),(1.5,1.0),(2.0,1.0),(2.0,1.5))
COST_CEILINGS=(.15,.25,.35,.50)
FEE_STRESS_BPS=(0.,2.,5.)
MAX_HOLD_SECONDS=1800
MAX_TICK_GAP_SECONDS=180
MAX_EXIT_DELAY_SECONDS=90

def stamp(iso):
    val=datetime.fromisoformat(iso)
    if val.tzinfo is None:raise ValueError("timestamp_without_timezone")
    return val.timestamp()

def recovered_atr(rates,signal_time,seconds,expected_hash):
    """Verify exactly the original last 120 causal bars before recovering ATR."""
    closes=[int(r["time"]+seconds) for r in rates]
    index=bisect_left(closes,int(signal_time))
    if index>=len(rates) or closes[index]!=round(signal_time) or index<119:
        return None,"missing_closed_signal_bar"
    view=rates[index-119:index+1]
    if snapshot_hash(view)!=expected_hash:
        return None,"history_fingerprint_mismatch"
    gaps=[b["time"]-a["time"] for a,b in zip(view[:-1],view[1:])]
    if any(not 0<g<=seconds*2 for g in gaps):
        return None,"causal_bar_gap"
    closes=[float(r["close"]) for r in view]
    ranges=[max(float(r["high"])-float(r["low"]),
                abs(float(r["high"])-closes[i-1]),
                abs(float(r["low"])-closes[i-1]))
            for i,r in enumerate(view) if i]
    atr=mean(ranges[-14:])
    return (atr,None) if isfinite(atr) and atr>0 else (None,"invalid_recovered_atr")

def valid(tick):
    return (len(tick)==3 and all(isfinite(v) and v>0 for v in tick[1:]) and
            tick[2]>=tick[1] and isfinite(tick[0]))

def normalized_ticks(raw):
    """Unchanged MT5 quotes only; no forward-fill; sorted tie timestamps."""
    result=[]
    prev=float("-inf")
    for x in raw:
        v=(float(x["time_msc"])/1000,float(x["bid"]),float(x["ask"]))
        if not isfinite(v[0]) or v[0]<prev:
            return [],"unsorted_tick_data"
        prev=v[0]
        if not valid(v):
            return [],"invalid_tick_quote"
        result.append(v)
    return result,None

def historical_path(mt5,symbol,signal):
    """Ensure copied sequence begins at source entry quote, not a guessed fill."""
    entry_time=stamp(signal["entry_tick_utc"])
    stop=entry_time+MAX_HOLD_SECONDS+MAX_EXIT_DELAY_SECONDS
    raw=mt5.copy_ticks_range(symbol,datetime.fromtimestamp(entry_time,UTC),
               datetime.fromtimestamp(stop,UTC),mt5.COPY_TICKS_ALL)
    if raw is None:
        return None,"tick_history_api_failed"
    values,error=normalized_ticks(raw)
    if error:return None,error
    if not values:return None,"no_tick_history"
    # MT5 range query can include ticks within first millisecond; align
    # to the one actually recorded by the original prospective quote.
    first=next((i for i,v in enumerate(values)
        if abs(v[0]-entry_time)<.002 and
           abs(v[1]-signal["entry_bid"])<1e-7 and
           abs(v[2]-signal["entry_ask"])<1e-7),None)
    if first is None:
        return None,"entry_quote_not_reproduced"
    # A price crossing TP or SL before a history cut-off remains observable.
    # A missing final time-stop quote is handled by simulate, not assumed.
    aligned=values[first:]
    return aligned,None

def simulate(ticks,side,atr,tp_multiple,sl_multiple,
             extra_cost_bps=0.,max_hold=MAX_HOLD_SECONDS):
    """Conservative first-hit bid/ask outcomes. Never invent a fill.

    Exits at favorable TP are capped at TP price; adverse SL gaps use the
    actual worse quote. Incomplete intratrade tick gap => cannot price.
    """
    if (side not in ("BUY","SELL") or not isfinite(atr) or atr<=0 or
        min(tp_multiple,sl_multiple)<=0 or
        not isfinite(extra_cost_bps) or extra_cost_bps<0):
        raise ValueError("invalid_simulation_params")
    if not ticks:
        return dict(status="MISSING_TICKS")
    if not all(valid(t) for t in ticks):
        return dict(status="BAD_TICK")
    opened,bid,ask=ticks[0]
    origin=ask if side=="BUY" else bid
    take=(origin+tp_multiple*atr if side=="BUY" else origin-tp_multiple*atr)
    stop=(origin-sl_multiple*atr if side=="BUY" else origin+sl_multiple*atr)
    base_mid=(bid+ask)/2
    horizon=opened+max_hold
    previous=opened
    for t,xbid,xask in ticks:
        if t<opened or t<previous:
            return dict(status="UNSORTED_TICKS")
        if t-previous>MAX_TICK_GAP_SECONDS:
            return dict(status="DATA_GAP",gap_seconds=t-previous)
        previous=t
        # First valid quote at/after maximum duration is a mandatory exit.
        if t>horizon+MAX_EXIT_DELAY_SECONDS:
            return dict(status="TIME_QUOTE_MISSING")
        px=xbid if side=="BUY" else xask
        # At/after the 30-minute deadline, the fixed-horizon exit takes
        # precedence. Never label a post-deadline price move as a TP.
        if t>=horizon:
            why="TIME"
            filled=px
        elif side=="BUY" and px<=stop or side=="SELL" and px>=stop:
            why="SL"
            filled=px # stop gap is never assumed filled at stop boundary
        elif side=="BUY" and px>=take or side=="SELL" and px<=take:
            why="TP"
            filled=min(px,take) if side=="BUY" else max(px,take)
        else:
            continue
        raw=(filled-origin) if side=="BUY" else (origin-filled)
        quote_bps=raw/base_mid*10000
        stressed_bps=quote_bps-extra_cost_bps
        nominal_risk=sl_multiple*atr
        stressed_r=raw/nominal_risk-extra_cost_bps*base_mid/(10000*nominal_risk)
        return dict(status="CLOSED",exit_reason=why,
            close_time_utc=datetime.fromtimestamp(t,UTC).isoformat(),
            hold_seconds=round(t-opened,3),quoted_delta=raw,
            quoted_bps=quote_bps,stressed_bps=stressed_bps,
            stressed_r=stressed_r,
            atr_signal=atr,entry_bid=bid,entry_ask=ask,
            exit_observed_bid=xbid,exit_observed_ask=xask,
            actual_exit_price_assumed=filled,
            hypothetical_tp_price=take,hypothetical_sl_price=stop,
            stop_distance_price=nominal_risk,
            favorable_target_capped_at_limit=True,
            adverse_stop_gap_uses_actual_bid_ask=True)
    return dict(status="TIME_QUOTE_MISSING")

def summarize(rows):
    done=[x for x in rows if x["status"]=="CLOSED"]
    rejected=Counter(x["status"] for x in rows if x["status"]!="CLOSED")
    if not done:
        return dict(n_candidates=len(rows),n_closed=0,missing=dict(rejected),
                    expectancy_r=None,profit_factor=None,win_fraction=None,
                    status="INSUFFICIENT_EVIDENCE")
    r=[x["stressed_r"] for x in done]
    win=sum(x>0 for x in r)
    positive=sum(x for x in r if x>0)
    negative=-sum(x for x in r if x<0)
    pf=positive/negative if negative else None
    days={x["signal_bar_close_utc"][:10] for x in done}
    coverage=len(done)/len(rows) if rows else 0
    return dict(n_candidates=len(rows),n_closed=len(done),missing=dict(rejected),
        outcome_coverage_fraction=coverage,
        distinct_utc_days=len(days),n_profitable=win,
        win_fraction=win/len(done),expectancy_r=mean(r),
        profit_factor=pf,extra_cost_bps=done[0]["extra_cost_bps"],
        exits=dict(Counter(x["exit_reason"] for x in done)),
        status="DESCRIPTIVE_ONLY" if (len(done)>=30 and len(days)>=10
            and coverage>=0.8) else "INSUFFICIENT_EVIDENCE",
        model_promotion_allowed=False)

def replay(mt5, inputs, symbols=None):
    archive={}
    source_manifest={}
    for family,paths in inputs.items():
        entries,provenance=load(paths,family)
        source_manifest[family]=provenance
        for e in entries:
            if float(e["entry_spread_atr"])>.50:
                continue
            if symbols and e["symbol"] not in symbols:
                continue
            archive.setdefault((family,e["symbol"],e["signal_bar_close_utc"][:7]),[]).append(e)
    detail=[]
    diagnostics=Counter()
    last_until_by_symbol_family={}
    def record_event(base,status,atr_verified=False):
        for tp,sl in CONFIG:
            for extra in FEE_STRESS_BPS:
                detail.append(dict(status=status, symbol=base["symbol"],
                    side=base["side"],family=base["family"],month=base["month"],
                    tp_atr=tp,sl_atr=sl,extra_cost_bps=extra,
                    signal_bar_close_utc=base["signal_bar_close_utc"],
                    entry_time_utc=base["entry_time_utc"],
                    entry_spread_atr=base["entry_spread_atr"],
                    atr_verified_from_sha256=atr_verified,
                    trade_filled=False,model_promotion_allowed=False))
    for (family,symbol,month),candidate in sorted(archive.items()):
        seconds,key=TIMEFRAMES[family]
        if not mt5.symbol_select(symbol,True):
            diagnostics["symbol_select_failed"]+=len(candidate)
            for e in candidate:
                record_event(dict(symbol=symbol,side=e["side"],family=family,month=month,
                    signal_bar_close_utc=e["signal_bar_close_utc"],
                    entry_time_utc=e["entry_tick_utc"],
                    entry_spread_atr=e["entry_spread_atr"]),"SYMBOL_SELECT_FAILED")
            continue
        begin=datetime.fromtimestamp(min(stamp(e["signal_bar_close_utc"]) for e in candidate),UTC)-timedelta(days=3 if seconds==60 else 6)
        end=datetime.fromtimestamp(max(stamp(e["signal_bar_close_utc"]) for e in candidate),UTC)+timedelta(minutes=2)
        tf=mt5.TIMEFRAME_M1 if seconds==60 else mt5.TIMEFRAME_M5
        rates=mt5.copy_rates_range(symbol,tf,begin,end)
        if rates is None:
            diagnostics["bar_api_failure"]+=len(candidate)
            for e in candidate:
                record_event(dict(symbol=symbol,side=e["side"],family=family,month=month,
                    signal_bar_close_utc=e["signal_bar_close_utc"],
                    entry_time_utc=e["entry_tick_utc"],
                    entry_spread_atr=e["entry_spread_atr"]),"BAR_API_FAILURE")
            continue
        candles=bars(rates)
        lock=(family,symbol)
        for e in sorted(candidate,key=lambda x:stamp(x["entry_tick_utc"])):
            event_time=stamp(e["signal_bar_close_utc"])
            entry_time=stamp(e["entry_tick_utc"])
            base=dict(symbol=symbol,side=e["side"],family=family,month=month,
                signal_bar_close_utc=e["signal_bar_close_utc"],
                entry_time_utc=e["entry_tick_utc"],
                entry_spread_atr=e["entry_spread_atr"])
            if entry_time<last_until_by_symbol_family.get(lock,float("-inf")):
                diagnostics["overlapping_30min_simulation"]+=1
                record_event(base,"OVERLAP_EXCLUDED")
                continue
            atr,error=recovered_atr(candles,event_time,seconds,e[key])
            if error:
                diagnostics[error]+=1
                record_event(base,error.upper())
                continue
            if abs((e["entry_ask"]-e["entry_bid"])/atr-e["entry_spread_atr"])>1e-7:
                diagnostics["ATR_ratio_inconsistent"]+=1
                record_event(base,"ATR_RATIO_INCONSISTENT",True)
                continue
            quotes,error=historical_path(mt5,symbol,e)
            if error:
                diagnostics[error]+=1
                record_event(base,error.upper(),True)
                continue
            last_until_by_symbol_family[lock]=entry_time+MAX_HOLD_SECONDS
            digest=sha256(json.dumps(quotes,separators=(",",":"),allow_nan=False).encode()).hexdigest()
            for tp,sl in CONFIG:
                for extra in FEE_STRESS_BPS:
                    x=simulate(quotes,e["side"],atr,tp,sl,extra)
                    x.update(dict(symbol=symbol,side=e["side"],family=family,
                       tick_path_sha256=digest,tick_events_available=len(quotes),
                       month=month,tp_atr=tp,sl_atr=sl,
                       extra_cost_bps=extra,signal_bar_close_utc=e["signal_bar_close_utc"],
                       entry_time_utc=e["entry_tick_utc"],
                       entry_spread_atr=e["entry_spread_atr"],
                       atr_verified_from_sha256=True,
                       trade_filled=False,model_promotion_allowed=False))
                    detail.append(x)
            diagnostics["candidate_paths_processed"]+=1
        print(json.dumps(dict(family=family,symbol=symbol,month=month,
            candidates=len(candidate),paths=diagnostics["candidate_paths_processed"])),flush=True)
    aggregate=[]
    for family in TIMEFRAMES:
        for ceiling in COST_CEILINGS:
            for tp,sl in CONFIG:
                for extra in FEE_STRESS_BPS:
                    for side in ("BUY","SELL"):
                        rows=[x for x in detail if x["family"]==family and
                           x["side"]==side and x["entry_spread_atr"]<=ceiling and
                           x["tp_atr"]==tp and x["sl_atr"]==sl and
                           x["extra_cost_bps"]==extra]
                        result=summarize(rows)
                        aggregate.append(dict(family=family,spread_atr_limit=ceiling,
                             tp_atr=tp,sl_atr=sl,side=side,extra_bps=extra,**result))
    return dict(report_version="historical_ohlc_verified_bidask_tick_path_v1",
        study_kind="EXPLORATORY_REUSED_HISTORICAL_PRICES",
        entry_rule="reused_frozen_M1_M5_or_M5_M15_proposals",
        strategy_approved=False,live_execution_enabled=False,
        model_promotion_allowed=False,
        sl_tp_is_hypothetical_not_realized_account_pnl=True,
        ATR_recovered_from_immutable_closed_bar_sha256=True,
        historical_tick_quote_replay=True,
        position_sizing="fixed_nominal_ATR_stop_R_not_account_dollars",
        profit_target_execution="capped_at_target_price",
        stop_execution="actual_observed_quoted_gap_price",
        max_hold_seconds=MAX_HOLD_SECONDS,
        data_gap_reject_seconds=MAX_TICK_GAP_SECONDS,
        additional_fees_and_slippage_are_stress_not_broker_actual=list(FEE_STRESS_BPS),
        true_broker_commissions_unknown=True,broker_historical_session_unknown=True,
        calendar_vintages_unknown=True,
        tick_limitations="A first matching quote is not proof of an executable fill.",
        input_evidence=source_manifest,diagnostics=dict(diagnostics),
        total_scenario_rows=len(detail),groups=aggregate,
        scenario_records=detail,
    )

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--terminal",default=r"C:\Program Files\MetaTrader 5 ALFA\terminal64.exe")
    p.add_argument("--m1-report",nargs="+",required=True)
    p.add_argument("--m5-report",nargs="+",required=True)
    p.add_argument("--symbols",default="all",help="Comma-separated exact broker symbols, or all")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    target=Path(args.output)
    if target.exists(): raise FileExistsError("immutable_output_exists")
    import MetaTrader5 as mt5
    if not mt5.initialize(args.terminal,timeout=20000):
        raise RuntimeError("research_mt5_terminal_unavailable "+str(mt5.last_error()))
    try:
        symbols=None if args.symbols=="all" else set(args.symbols.split(","))
        result=replay(mt5,{"M1_M5":args.m1_report,"M5_M15":args.m5_report},symbols)
    finally:
        mt5.shutdown()
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("REPORT "+str(target),flush=True)
    print("DIAGNOSTICS "+json.dumps(result["diagnostics"]),flush=True)
    for g in result["groups"]:
        if g["spread_atr_limit"]==.35 and g["tp_atr"]==2 and g["sl_atr"]==1 and g["extra_bps"] in (0,2):
            print("SUMMARY "+json.dumps(g),flush=True)

if __name__=="__main__":
    main()
