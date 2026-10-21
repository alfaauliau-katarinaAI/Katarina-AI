"""Precommitted alternative setup research; NOT a live KATARINA brain.

Frozen engineering hypotheses before requesting historical Aug-2026 bars:
1) M5 range sweep/reclaim -> midpoint of PRECEDING range
2) H1/M15 aligned, genuine M5 correction -> prior H1 liquidity
3) previous breakout + M5 retest -> 0.8x measured prior range

All timestamp/geometry checks use only closed bars as of signal epoch.
No optimization, broker execution or learned parameters. Price labels
are separate hypothetical next M5 bar entry using the existing
conservative STOP-FIRST OHLC proxy. Never route output as trading signal.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter,defaultdict
from datetime import datetime
from math import isfinite
from statistics import mean
from typing import Mapping,Sequence

from katarina.intelligence.causal_market_replay import (
    stamp,validate_bars,simulate_ohlc_proxy,
)
from katarina.intelligence.market_decision_pipeline import SensorCandle

FROZEN_RULE_VERSION="ALT_SETUP_AUG_2026_PRECOMMITTED_V1"
METHODS=("RANGE_SWEEP_RECLAIM","TREND_PULLBACK_RESUME","BREAKOUT_RETEST_LEVEL")
HORIZON_BARS=24
MIN_NET_RR=1.25
MAX_SPREAD_RISK=.20
MAX_SPREAD_M5_ATR=.35
ATR_BARS=14


def _atr(rows):
    last=rows[-ATR_BARS-1:]
    if len(last)!=ATR_BARS+1:raise ValueError("atr_warmup_insufficient")
    x=[max(b.high-b.low,abs(b.high-a.close),abs(b.low-a.close))
       for a,b in zip(last,last[1:])]
    v=mean(x)
    if not isfinite(v) or v<=0:raise ValueError("invalid_atr")
    return v


def _propose(frame, spread):
    """Frozen closed candle views (M5/M15/H1). No future bar accepted."""
    m5,m15,h1=(frame[t] for t in ("M5","M15","H1"))
    if any(len(rows)<60 for rows in (m5,m15,h1)):return []
    now=m5[-1].closed_at_utc
    if any(rows[-1].closed_at_utc>now for rows in (m5,m15,h1)):
        raise ValueError("future_bar_leak")
    atr5=_atr(m5);atr15=_atr(m15)
    if (not isfinite(spread) or spread<=0 or spread>MAX_SPREAD_M5_ATR*atr5):
        return []
    c=m5[-1]
    # All structures exclude the signal candle.
    previous20=m5[-21:-1]
    ceiling=max(x.high for x in previous20)
    floor=min(x.low for x in previous20)
    width=ceiling-floor
    if width<=atr5:return []
    out=[]

    def add(method,side,stop,target,trigger):
        p=c.close
        # Signal-bar spread is a PROXY for next-open unknown spread.
        entry=p+spread if side=="BUY" else p
        risk=entry-stop if side=="BUY" else stop-entry
        reward=target-entry if side=="BUY" else entry-target
        if not all(isfinite(v) for v in (entry,stop,target,risk,reward)):
            return
        if risk<=max(spread,1e-10) or reward/risk<MIN_NET_RR:
            return
        if spread/risk>MAX_SPREAD_RISK:return
        out.append({
            "method":method,"side":side,"stop":round(stop,10),
            "target":round(target,10),"signal_epoch":stamp(now),
            "spread_price":round(spread,10),
            "risk_signal_proxy":round(risk,10),
            "rr_signal_proxy":round(reward/risk,6),
            "evidence":trigger,
            "frozen_rule_version":FROZEN_RULE_VERSION,
            "source":"MT5_CLOSED_M5_M15_H1_PLUS_PRIOR_M5_SPREAD",
            "broker_execution_allowed":False,
        })

    # A real sweep must breach and reclaim THE PRIOR channel in one M5
    # close, with a rejection wick; direction-independent geometry.
    midpoint=(ceiling+floor)/2
    h1_delta=abs(h1[-1].close-h1[-8].close)
    # Do not fade a powerful H1 directional impulse.
    if h1_delta<=1.5*atr15:
        rng=max(c.high-c.low,1e-10)
        buy_wick=min(c.open,c.close)-c.low
        sell_wick=c.high-max(c.open,c.close)
        if (c.low<floor-.05*atr5 and
            c.close>floor+.05*atr5 and c.close>c.open and
            buy_wick>=.35*rng):
            add("RANGE_SWEEP_RECLAIM","BUY",
                c.low-.15*atr5,midpoint,"PRIOR_RANGE_LOW_SWEEP_AND_M5_RECLAIM")
        if (c.high>ceiling+.05*atr5 and
            c.close<ceiling-.05*atr5 and c.close<c.open and
            sell_wick>=.35*rng):
            add("RANGE_SWEEP_RECLAIM","SELL",
                c.high+.15*atr5,midpoint,"PRIOR_RANGE_HIGH_SWEEP_AND_M5_RECLAIM")

    # H1/M15 momentum and actual corrective candles BEFORE M5
    # resumption. Previous H1 liquidity target required, no ATR TP
    # invented if structure is on the wrong side.
    h1_move=h1[-1].close-h1[-8].close
    m15_move=m15[-1].close-m15[-9].close
    for side,sign in (("BUY",1),("SELL",-1)):
        correction=m5[-7:-1]
        counter=sum(sign*(x.close-x.open)<0 for x in correction)
        last=c
        previous=m5[-2]
        if not(sign*h1_move>=1.0*atr15 and sign*m15_move>=.4*atr15
               and counter>=2 and sign*(last.close-last.open)>0
               and sign*(last.close-previous.close)>.05*atr5):
            continue
        ext=(min(x.low for x in correction) if sign>0
             else max(x.high for x in correction))
        # Corrective swing must be visible, not a fake colored bar.
        if sign>0:
            if ext>=max(x.high for x in m5[-15:-7])-.22*atr5:continue
            stop=ext-.15*atr5
            higher=[x.high for x in h1[-32:-1] if x.high>last.close]
            if not higher:continue
            target=min(higher)
        else:
            if ext<=min(x.low for x in m5[-15:-7])+.22*atr5:continue
            stop=ext+.15*atr5
            lower=[x.low for x in h1[-32:-1] if x.low<last.close]
            if not lower:continue
            target=max(lower)
        add("TREND_PULLBACK_RESUME",side,stop,target,
            "HTF_ALIGNED_REAL_CORRECTION_AND_M5_RESUMPTION")

    # Historical channel EXCLUDES both breakout bar and retest bar.
    top=max(x.high for x in m5[-22:-2])
    bottom=min(x.low for x in m5[-22:-2])
    width=top-bottom
    b=m5[-2]
    if width>=atr5:
        if (b.close>top+.10*atr5 and c.low<=top+.15*atr5 and
            c.close>top+.05*atr5 and c.close>c.open):
            add("BREAKOUT_RETEST_LEVEL","BUY",
                min(c.low,b.low)-.15*atr5,
                top+.8*width,"PREVIOUS_CLOSE_BREAKOUT_CURRENT_HOLDING_RETEST")
        if (b.close<bottom-.10*atr5 and c.high>=bottom-.15*atr5 and
            c.close<bottom-.05*atr5 and c.close<c.open):
            add("BREAKOUT_RETEST_LEVEL","SELL",
                max(c.high,b.high)+.15*atr5,
                bottom-.8*width,"PREVIOUS_CLOSE_BREAKDOWN_CURRENT_HOLDING_RETEST")
    return out


def _metrics(rows,cost):
    values=[v["gross_proxy_r"]-cost for v in rows]
    profits=sum(max(v,0) for v in values)
    losses=-sum(min(v,0) for v in values)
    return {
        "n":len(rows),
        "positive":sum(v>0 for v in values),
        "negative":sum(v<0 for v in values),
        "mean_net_assumed_r":round(mean(values),6) if values else None,
        "profit_factor_assumed":round(profits/losses,6) if losses else None,
        "exit_reasons":dict(Counter(v["exit_reason"] for v in rows)),
        "no_real_broker_commission_or_fill_proof":True,
    }


def research_alternatives(frames_by_symbol:Mapping[str,Mapping[str,Sequence[SensorCandle]]],
                          spread_by_symbol:Mapping[str,Mapping[int,float]],
                          *,window_start:datetime,window_end:datetime,
                          max_cuts_per_symbol:int=2300):
    if (window_start.tzinfo is None or window_end.tzinfo is None or
        not window_start<window_end or
        (window_end-window_start).days>16 or
        not 100<=max_cuts_per_symbol<=3000):
        raise ValueError("invalid_precommitted_history_bounds")
    if not 1<=len(frames_by_symbol)<=5:
        raise ValueError("bounded_broker_symbol_research_only")
    start=stamp(window_start);end=stamp(window_end)
    outcomes=[];proposals=[];counts=Counter()
    for sym,raw in sorted(frames_by_symbol.items()):
        v=validate_bars(raw)
        m5=v["M5"]
        if len(m5)<200:continue
        timeline={tf:[stamp(c.closed_at_utc) for c in v[tf]]
                  for tf in ("M5","M15","H1")}
        recent=[i for i,t in enumerate(timeline["M5"])
                if start<=t<=end and i>=130 and i<len(m5)-1]
        if len(recent)>max_cuts_per_symbol:
            raise ValueError("historical_window_exceeds_bounded_memory_cut_count")
        next_open_by_method=defaultdict(int)
        for i in recent:
            now=timeline["M5"][i]
            high={tf:bisect_right(timeline[tf],now) for tf in ("M15","H1")}
            if any(high[tf]<60 for tf in high):
                counts["insufficient_past_M15_H1"]+=1;continue
            if (now-timeline["M15"][high["M15"]-1]>1800 or
                now-timeline["H1"][high["H1"]-1]>7200):
                counts["stale_higher_tf"]+=1;continue
            spread=spread_by_symbol.get(sym,{}).get(now)
            if spread is None or spread<=0 or not isfinite(spread):
                counts["missing_real_signal_spread"]+=1;continue
            closed={tf:(v[tf][max(0,i-129):i+1] if tf=="M5"
                        else v[tf][max(0,high[tf]-130):high[tf]])
                    for tf in ("M5","M15","H1")}
            for item in _propose(closed,spread):
                k=(sym,item["method"])
                if now<next_open_by_method[k]:
                    counts["same_symbol_method_overlapping_hypothesis"]+=1
                    continue
                item["symbol"]=sym
                proposals.append(item)
                raw_out=simulate_ohlc_proxy(m5,i,item["side"],item["stop"],
                                             item["target"],spread)
                if raw_out is None:
                    counts["censored_future_or_entry_geometry"]+=1
                    # no future outcome: reject, don't fabricate label
                    continue
                gross,done,why=raw_out
                row={**item,"exit_epoch":done,"gross_proxy_r":gross,
                     "exit_reason":why,"not_an_actual_tick_fill":True}
                outcomes.append(row)
                next_open_by_method[k]=done+300
                counts["proxy_resolved"]+=1
            counts["market_clocks"]+=1
    metrics=[]
    for method in METHODS:
        for side in ("BUY","SELL"):
            rows=[x for x in outcomes
                  if x["method"]==method and x["side"]==side]
            metrics.append({"method":method,"side":side,
                            "plus_0_15R_assumed":_metrics(rows,.15),
                            "plus_0_30R_assumed":_metrics(rows,.30)})
    return {
        "status":"PRECOMMITTED_ALTERNATIVES_RESEARCH_ONLY",
        "frozen_rule_version":FROZEN_RULE_VERSION,
        "window_start_utc":window_start.isoformat(),
        "window_end_utc":window_end.isoformat(),
        "broker_symbols":sorted(frames_by_symbol),
        "counters":dict(counts),
        "technical_proposals":len(proposals),
        "all_proposals_frozen_before_future_outcome":proposals,
        "simulated_outcomes":len(outcomes),
        "all_proxy_outcomes":outcomes,
        "by_method_side":metrics,
        "all_plus_0_15R_assumed":_metrics(outcomes,.15),
        "all_plus_0_30R_assumed":_metrics(outcomes,.30),
        "real_entry_bidask_verified":False,
        "real_broker_commission_verified":False,
        "no_untouched_OOS_claim_without_prior_data_provenance":True,
        "portfolio_drawdown_not_available_from_independent_signal_lists":True,
        "live_execution_authorized":False,"orders_sent":0,
    }
