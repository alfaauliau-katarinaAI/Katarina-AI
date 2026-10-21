"""Final, frozen V9 XAUUSD SELL tick audit. Research-only, no orders.

This is NOT a new strategy version. Traces 2 V9 SELL hypotheses without
altering their signals, SL/TP or time limit. Missing tick paths stay missing.
Reads MT5 broker rates/ticks only, prints aggregate JSON, writes nothing.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib import import_module
from math import isfinite
from statistics import mean
from types import SimpleNamespace
from urllib.request import urlopen
import json

UTC=timezone.utc
SYMBOL="XAUUSD.vx"
METHODS=("TREND_EXPANSION_V9","SWEEP_2C_CONFIRM_V9")
FROZEN_CODE="0b300ca86ec8d14d5bb2a175939404cefb8f733f"
PINNED_URL=("https://raw.githubusercontent.com/alfaauliau-katarinaAI/"
           "Katarina-AI/"+FROZEN_CODE+"/scripts/research/broker_entry_diagnostics_v9.py")
START=datetime(2026,9,15,tzinfo=UTC)
END=datetime(2026,10,10,tzinfo=UTC)
HOLD_SECONDS=7200
MAX_ENTRY_DELAY=90
MAX_EXIT_DELAY=90
MAX_TICK_GAP=180
FEE_R=.03
STRESS_R=.10


def original_v9():
    """Prefer already available research code; VPS loads immutable SHA in RAM."""
    try:
        return import_module("broker_entry_diagnostics_v9")
    except ModuleNotFoundError:
        with urlopen(PINNED_URL,timeout=35) as response:
            content=response.read(100000)
        space={"__name__":"katarina_frozen_v9_module"}
        exec(compile(content,"frozen_v9_research.py","exec"),space)
        return SimpleNamespace(**space)


def score(returns):
    if not returns:
        return dict(n=0,mean_r=None,pf=None,win_pct=None)
    positive=sum(x for x in returns if x>0)
    negative=-sum(x for x in returns if x<0)
    return dict(n=len(returns),mean_r=round(mean(returns),6),
                pf=round(positive/negative,5) if negative else None,
                win_pct=round(100*sum(x>0 for x in returns)/len(returns),2))


def valid_quote(row):
    bid,ask=float(row["bid"]),float(row["ask"])
    t=int(row["time_msc"])/1000
    return isfinite(t) and isfinite(bid) and isfinite(ask) and 0<bid<=ask


def replay_short(quotes,stop,target,tick_size,signal_time,bar_spread):
    """SELL from first bid quote after signal; exit on actual ASK ticks.

    SL and TP translated by reference model's *entry M5 spread* to
    maintain V9's frozen stop/target convention. Never optimize on ticks.
    Time exit uses first tick at/after 2h, no more than 90s late.
    """
    if not len(quotes):return dict(status="TICKS_MISSING")
    first=None
    for i,row in enumerate(quotes):
        ts=int(row["time_msc"])/1000
        if ts<signal_time:continue
        if ts>signal_time+MAX_ENTRY_DELAY:break
        if valid_quote(row):
            first=i
            break
    if first is None:return dict(status="ENTRY_QUOTE_UNAVAILABLE")
    opened=quotes[first]
    at=int(opened["time_msc"])/1000
    bid=float(opened["bid"])
    ask=float(opened["ask"])
    entry=bid-tick_size
    effective_stop=stop+bar_spread
    effective_target=target+bar_spread
    risk=effective_stop-entry
    reward=entry-effective_target
    if risk<=max(3*tick_size,2*(ask-bid)) or reward/risk<.60:
        return dict(status="BAD_ENTRY_GEOMETRY")
    horizon=at+HOLD_SECONDS
    prev=at
    for row in quotes[first:]:
        if not valid_quote(row):return dict(status="INVALID_QUOTE")
        tick_at=int(row["time_msc"])/1000
        if tick_at<prev:return dict(status="UNSORTED_TICKS")
        if tick_at-prev>MAX_TICK_GAP:return dict(status="GAPPED_TICKS")
        prev=tick_at
        exit_ask=float(row["ask"])
        if tick_at>horizon+MAX_EXIT_DELAY:
            return dict(status="TIME_EXIT_QUOTE_MISSING")
        if tick_at>=horizon:
            label="TIME"
            filled=exit_ask+tick_size
        elif exit_ask>=effective_stop:
            label="SL"
            filled=max(exit_ask,effective_stop)+tick_size
        elif exit_ask<=effective_target:
            label="TP"
            filled=max(exit_ask,effective_target)+tick_size
        else:
            continue
        r=(entry-filled)/risk-FEE_R
        return dict(status="CLOSED",exit_reason=label,
                    base_r=round(r,7),stressed_r=round(r-STRESS_R,7),
                    exit_at=tick_at,entry_quote_spread=round(ask-bid,6))
    return dict(status="TIME_EXIT_QUOTE_MISSING")


def checked_v9_signals(mt5,v9):
    # June-Aug training months excluded, freeze V9 logic from immutable SHA.
    raw=mt5.copy_rates_range(SYMBOL,mt5.TIMEFRAME_M5,
         datetime(2026,9,10,tzinfo=UTC),END)
    if raw is None or len(raw)<1000:
        raise RuntimeError("INSUFFICIENT_M5_FOR_CAUSAL_REPLAY")
    bars=[v9.B(int(x["time"])+300,float(x["open"]),float(x["high"]),
               float(x["low"]),float(x["close"]),int(x["spread"])) for x in raw]
    h1=v9.to_h1(bars)
    clock=[x.time for x in h1]
    info=mt5.symbol_info(SYMBOL)
    if info is None:raise RuntimeError("NO_BROKER_SYMBOL")
    point=float(info.point)
    tick_size=float(info.trade_tick_size or info.point)
    counters=Counter()
    found=[]
    active_until={}
    for i in range(29,len(bars)-1):
        b=bars[i]
        if b.time<START.timestamp() or b.time>=END.timestamp():continue
        history=bars[i-29:i+1]
        if any(history[j].time-history[j-1].time!=300 for j in range(1,30)):
            counters["closed_bar_gap"]+=1
            continue
        j=bisect_right(clock,b.time)
        if j<16 or bars[i+1].time!=b.time+300:
            counters["H1_unavailable_or_no_next_M5"]+=1
            continue
        for item in v9.proposals(history,h1[j-16:j],point,
                                  max(0,b.spread)*point):
            family,side,_,_,_=item
            if (family,side) not in [(x,"SELL") for x in METHODS]:
                continue
            counters[family+"_signals"]+=1
            if active_until.get(family,0)>b.time:
                counters["overlap_excluded"]+=1
                continue
            model=v9.fill(item,bars[i+1],bars[i+1:i+1+v9.HOLD],
                          point,tick_size)
            if model is None:
                counters["V9_entry_geometry_invalid"]+=1
                continue
            # The decision to include a signal is independent of future
            # tick prices. Fixed 2h blackout eliminates overlapping hypotheses.
            active_until[family]=b.time+HOLD_SECONDS
            found.append((item,b.time,bars[i+1],model))
    return found,counters,point,tick_size


def run():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("MT5_UNAVAILABLE")
    try:
        terminal=mt5.terminal_info()
        if terminal is None or terminal.trade_allowed:
            raise RuntimeError("FAIL_CLOSED_TRADING_MUST_BE_DISABLED")
        v9=original_v9()
        events,counts,point,tick_size=checked_v9_signals(mt5,v9)
        grouped=defaultdict(list)
        missing=defaultdict(Counter)
        modeled=defaultdict(list)
        per_month=defaultdict(lambda:defaultdict(list))
        for idx,(opportunity,t,entrybar,model) in enumerate(events,1):
            family=opportunity[0]
            month=datetime.fromtimestamp(t,UTC).strftime("%Y-%m")
            modeled[family].append(model[0]-.10)
            ticks=mt5.copy_ticks_range(
                SYMBOL,datetime.fromtimestamp(t,UTC),
                datetime.fromtimestamp(t+HOLD_SECONDS+2*MAX_EXIT_DELAY,UTC),
                mt5.COPY_TICKS_ALL)
            if ticks is None:
                missing[family]["TICK_API_FAILED"]+=1
                continue
            result=replay_short(ticks,opportunity[2],opportunity[3],
                                tick_size,t,max(0,entrybar.spread)*point)
            if result["status"]!="CLOSED":
                missing[family][result["status"]]+=1
                continue
            grouped[family].append(result["stressed_r"])
            per_month[family][month].append(result["stressed_r"])
            counts["completed_tick_trade"]+=1
            if idx%10==0:
                print("AUDIT_PROGRESS",json.dumps({"checked":idx,
                    "planned":len(events),"tick_closed":counts["completed_tick_trade"]}),
                    flush=True)
        result={
            "audit":"V9_FROZEN_XAUUSD_SELL_TICK_FINAL_VERDICT",
            "v9_code_sha":FROZEN_CODE,
            "period_utc":[START.isoformat(),END.isoformat()],
            "methods":list(METHODS),
            "orders_sent":0,"production":"WAIT",
            "broker_trade_allowed":False,
            "research_only":True,
            "independent_unseen_OOS":False,
            "source":"demo MT5 M5 broker BID bars and actual historical bid/ask ticks",
            "tick_completeness_demanded":True,
            "actual_trade_fills_verified":False,
            "actual_commission_verified":False,
            "modeled_fee_r":FEE_R,
            "extra_cost_stress_r":STRESS_R,
            "counters":dict(counts),
            "per_method":{}}
        for family in METHODS:
            original=modeled[family]
            real=grouped[family]
            n_candidates=sum(op[0][0]==family for op in events)
            accepted=(len(real)/n_candidates) if n_candidates else 0
            months={mon:score(per_month[family][mon])
                    for mon in ("2026-09","2026-10")}
            # Do not turn any untrusted tiny sample into execution.
            result["per_method"][family]=dict(
                signals_with_M5_model=n_candidates,
                candle_model_after_stress=score(original),
                genuine_tick_bid_ask_paths_complete=len(real),
                coverage=round(accepted,5),
                rejected_tick_paths=dict(missing[family]),
                tick_after_stress=score(real),
                tick_by_month=months,
                proof_gate_passed=False,
                action="REJECT_FOR_PRODUCTION_NO_INDEPENDENT_HOLDOUT")
        result["decision"]="NO_GO_LIVE"
        print("FROZEN_XAU_TICK_VERDICT",json.dumps(result,separators=(",",":"),
                allow_nan=False),flush=True)
    finally:
        mt5.shutdown()


def self_test():
    tick_size=.01
    def raw(time,bid,ask):
        return {"time_msc":int(time*1000),"bid":bid,"ask":ask}
    # Stop and take inside same 1s quote: stop first by actual quote path.
    a=[raw(1000,100,100.30),raw(1001,99,102)]
    out=replay_short(a,101.0,98.0,tick_size,1000,.30)
    assert out["status"]=="CLOSED" and out["exit_reason"]=="SL"
    # Missing mid-trade price history MUST fail, not magically skip ahead.
    a=[raw(1000,100,100.30),raw(1400,99,99.30)]
    assert replay_short(a,101,98,.01,1000,.30)["status"]=="GAPPED_TICKS"
    assert score([])["n"]==0
    assert score([-1,1])["mean_r"]==0
    print("FROZEN_XAU_TICK_AUDIT_SELF_TEST_PASS",flush=True)


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--self-test",action="store_true")
    o=args.parse_args()
    if o.self_test:self_test()
    else:run()


if __name__=="__main__":
    main()
