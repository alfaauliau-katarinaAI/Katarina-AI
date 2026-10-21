"""Causal Market Brain V3 replay on historical closed M5/M15/H1 bars.

REUSES native MarketDecisionBrain and adaptive_walkforward; it does NOT
introduce another live strategy selector. Labels are explicitly OHLC bid
proxies with *assumed* bid/ask spread and cost stress, never actual tick
fills, broker commissions, or independent OOS.

Any bar later than as_of is excluded *before* feeding native Brain.
Validation windows purge crossing outcomes and apply a fixed embargo.
No news history is invented: card is evaluated with unverified news,
and technical signals are hypothetical RESEARCH CANDIDATES ONLY.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timezone
from math import isfinite
from typing import Mapping, Sequence

from katarina.intelligence.market_decision_pipeline import SensorCandle
from katarina.intelligence.market_decision_brain_v3 import MarketDecisionBrain
from katarina.intelligence.adaptive_walkforward import PaperEvent, replay_walk_forward

UTC=timezone.utc
HORIZON_M5=24
EMBARGO_SECONDS=2*3600
REPLAY_START_M5=60
MAX_EVALUATIONS=12000


def stamp(d:datetime)->int:
    if not isinstance(d,datetime) or d.tzinfo is None:
        raise ValueError("market_replay_requires_timezone_aware_clock")
    return int(d.astimezone(UTC).timestamp())


def validate_bars(frames:Mapping[str,Sequence[SensorCandle]]):
    """Fail closed on duplicates, future-looking OHLC, or inconsistent clocks."""
    out={}
    for tf in ("M5","M15","H1"):
        if tf not in frames:
            raise ValueError("missing_closed_"+tf)
        seq=tuple(frames[tf])
        last=0
        for c in seq:
            t=stamp(c.closed_at_utc)
            if t<=last:raise ValueError("non_monotonic_"+tf)
            last=t
            if not all(isfinite(v) for v in (c.open,c.high,c.low,c.close)):
                raise ValueError("nonfinite_"+tf)
            if c.low<=0 or c.high<max(c.open,c.close) or c.low>min(c.open,c.close):
                raise ValueError("invalid_ohlc_"+tf)
        out[tf]=seq
    return out


def simulate_ohlc_proxy(m5,signal_index,side,stop,target,spread):
    """Causal label for a prior decision; NOT a broker trade.

    Entry next M5 bid open. Ask is bid+historical *ASSUMED* spread.
    Both-hit same bar => STOP first; better-than-target fills forbidden.
    Gaps at future bar open can worsen stop. Future missing -> no label.
    """
    if signal_index+1>=len(m5):
        return None
    a=m5[signal_index+1]
    entry=a.open+spread if side=="BUY" else a.open
    risk=(entry-stop) if side=="BUY" else (stop-entry)
    reward=(target-entry) if side=="BUY" else (entry-target)
    if risk<=max(spread,1e-8) or reward/risk<1.0:
        return None
    end=min(len(m5)-1,signal_index+HORIZON_M5)
    if end<signal_index+1:return None  # first future bar may hit SL or TP
    # The replay cannot know whether a missing series contains
    # unobserved intrabar spikes or broker gaps. Reject time gaps.
    prev_time=stamp(m5[signal_index].closed_at_utc)
    for j in range(signal_index+1,end+1):
        c=m5[j]
        t=stamp(c.closed_at_utc)
        if t-prev_time!=300:
            return None
        prev_time=t
        if side=="BUY":
            stopped=c.low<=stop
            reached=c.high>=target
            if stopped:
                # stop-first and adverse opening gap price
                exit_price=min(stop,c.open)
                why="STOP_FIRST_BID_OHLC_PROXY"
            elif reached:
                exit_price=target
                why="TARGET_BID_OHLC_PROXY"
        else:
            stopped=c.high+spread>=stop
            reached=c.low+spread<=target
            if stopped:
                exit_price=max(stop,c.open+spread)
                why="STOP_FIRST_ASK_ESTIMATE_OHLC_PROXY"
            elif reached:
                exit_price=target
                why="TARGET_ASK_ESTIMATE_OHLC_PROXY"
        if stopped or reached:
            gross=(exit_price-entry)/risk if side=="BUY" else (entry-exit_price)/risk
            return round(gross,7),t,why
    # A terminal/history cutoff before the full 2h holding window is
    # CENSORED, never invent an earlier profitable or losing time exit.
    if end<signal_index+HORIZON_M5:
        return None
    c=m5[end]
    exit_price=c.close if side=="BUY" else c.close+spread
    gross=(exit_price-entry)/risk if side=="BUY" else (entry-exit_price)/risk
    return round(gross,7),stamp(c.closed_at_utc),"TIMESTOP_OHLC_PROXY"


def replay_native_brain(
    symbol_frames:Mapping[str,Mapping[str,Sequence[SensorCandle]]],
    *, assumed_spread_to_m15_atr:float=.04,
    additional_cost_r:float=.15,
    max_m5_cuts_per_symbol:int=1300,
    historical_m5_spread_by_symbol:Mapping[str,Mapping[int,float]]|None=None,
):
    """Produces native-brain causal candidate events and historical diagnostics.

    If verified M5 closed-bar spread snapshots exist, use the spread
    observed at the signal time instead of a guessed ATR fraction.
    This is NOT the executable ASK at the *next bar open*. Never use a
    future candle's spread for the current Brain decision. No optimizer.
    """
    if not 0<=assumed_spread_to_m15_atr<=.25 or not 0<=additional_cost_r<=.5:
        raise ValueError("invalid_predeclared_proxy_cost_assumption")
    if not 120<=max_m5_cuts_per_symbol<=3000:
        raise ValueError("unbounded_replay_workload")
    brain=MarketDecisionBrain()
    events=[]
    details=[]
    all_technical_proposals=[]
    counters={"evaluated":0,"technical_wait":0,"no_causal_timeframe":0,
              "stale_regime_bars":0,"quote_path_unavailable":0,
              "invalid_rr_or_stop":0,"proxy_completed":0,
              "missing_data":0,"spread_unavailable":0}
    for symbol,frames in sorted(symbol_frames.items()):
        valid=validate_bars(frames)
        m5=valid["M5"];m15=valid["M15"];h1=valid["H1"]
        if min(len(m5),len(m15),len(h1))<60:
            counters["missing_data"]+=1
            continue
        times={tf:[stamp(c.closed_at_utc) for c in rows] for tf,rows in valid.items()}
        selected_idx=list(range(max(60,len(m5)-max_m5_cuts_per_symbol),len(m5)-1))
        next_available=0
        for idx in selected_idx:
            if idx<next_available:continue
            now=times["M5"][idx]
            # No current/live quote or future candle may leak into this decision.
            hi={tf:bisect_right(times[tf],now) for tf in ("M15","H1")}
            if any(hi[tf]<60 for tf in ("M15","H1")):
                counters["no_causal_timeframe"]+=1
                continue
            if ((now-times["M15"][hi["M15"]-1])>900*2 or
                    (now-times["H1"][hi["H1"]-1])>3600*2):
                counters["stale_regime_bars"]+=1
                continue
            view={
                "M5":m5[max(0,idx-129):idx+1],
                "M15":m15[max(0,hi["M15"]-130):hi["M15"]],
                "H1":h1[max(0,hi["H1"]-130):hi["H1"]],
            }
            atr=brain._atr(view["M15"])
            if not isfinite(atr) or atr<=0:
                counters["missing_data"]+=1
                continue
            if historical_m5_spread_by_symbol is not None:
                spread=historical_m5_spread_by_symbol.get(symbol,{}).get(now)
                if (spread is None or not isinstance(spread,(float,int)) or
                    not isfinite(spread) or spread<=0):
                    counters["spread_unavailable"]+=1
                    continue
                source="BROKER_M5_CLOSED_BAR_SPREAD_POINTS"
            else:
                spread=atr*assumed_spread_to_m15_atr
                source="ASSUMED_M15_ATR_SPREAD"
            ratio=spread/atr
            card=brain.evaluate(
                symbol=symbol,candles=view,
                as_of_utc=datetime.fromtimestamp(now,UTC),
                actual_spread=spread,
                broker_session_open=True,data_fresh=True,
                news_blackout=False,
                news_context_verified=False,
                strategy_evidence=None,
                risk_approved_for_paper=False,
            )
            counters["evaluated"]+=1
            if card.technical_signal not in ("BUY","SELL"):
                counters["technical_wait"]+=1
                continue
            if (card.rr_after_spread_estimate is None or
                card.rr_after_spread_estimate<1.25 or
                card.invalidation_level is None or card.primary_target is None or
                card.strategy=="OBSERVE"):
                counters["invalid_rr_or_stop"]+=1
                continue
            # Freeze every technically admissible setup BEFORE inspecting
            # future bars. Tick auditing must NOT sample only candidates
            # whose future OHLC proxy happened to resolve cleanly.
            all_technical_proposals.append({
                "symbol":symbol,"signal_at":now,
                "method":card.strategy,"side":card.technical_signal,
                "regime":card.market_state,
                "technical_score":card.evidence_score,
                "rr_estimate":card.rr_after_spread_estimate,
                "sl":card.invalidation_level,"tp":card.primary_target,
                "known_from_closed_bars_only":True,
                "observed_spread_price":round(spread,10),
                "spread_to_m15_atr":round(ratio,8),
                "m15_atr_price":round(atr,10),
                "spread_source":source,
                "directional_alignment":getattr(card,"directional_alignment",
                                                 "UNASSESSED"),
                "directional_observations":list(
                    getattr(card,"directional_observations",())),
            })
            outcome=simulate_ohlc_proxy(
                m5,idx,card.technical_signal,
                card.invalidation_level,card.primary_target,spread,
            )
            if outcome is None:
                counters["quote_path_unavailable"]+=1
                continue
            gross_r,exit_time,exit_reason=outcome
            # The simulated outcome becomes known strictly AFTER signal.
            if exit_time<=now:
                raise AssertionError("future_label_not_after_signal")
            events.append(PaperEvent(
                symbol=symbol,strategy_id=card.strategy,
                side=card.technical_signal,cut=now,exit_time=exit_time,
                modeled_r=gross_r,score=card.evidence_score,
                spread_atr=ratio,
                market_regime=card.market_state))
            details.append({
                "symbol":symbol,"signal_at":now,"label_known_at":exit_time,
                "method":card.strategy,"side":card.technical_signal,
                "regime":card.market_state,"technical_score":card.evidence_score,
                "rr_estimate":card.rr_after_spread_estimate,
                "sl":card.invalidation_level,"tp":card.primary_target,
                "proxy_gross_r":gross_r,"proxy_exit_reason":exit_reason,
                "observed_spread_price":round(spread,10),
                "spread_to_m15_atr":round(ratio,8),
                "m15_atr_price":round(atr,10),
                "spread_source":source,
                "directional_alignment":getattr(card,"directional_alignment",
                                                 "UNASSESSED"),
                "current_news_context_known":False,
                "live_execution_authorized":False,
            })
            counters["proxy_completed"]+=1
            # No overlapping virtual trade on the SAME symbol.
            next_available=bisect_right(times["M5"],exit_time)
            if counters["evaluated"]>=MAX_EVALUATIONS:
                raise ValueError("replay_evaluation_limit")
    # Time-first for cross-symbol causal portfolio decisions.
    historical=replay_walk_forward(events,extra_cost_r=additional_cost_r)
    return {
        "status":"HISTORICAL_NATIVE_BRAIN_REPLAY_COMPLETE",
        "market_brain_reused":"MarketDecisionBrain.evaluate",
        "memory_engine_reused":"adaptive_walkforward.replay_walk_forward",
        "symbol_count":len(symbol_frames),
        "counters":counters,
        "data_type":("MT5_M5_BID_OHLC_AND_SIGNAL_BAR_BROKER_SPREAD_PROXY_NOT_TICKS"
                     if historical_m5_spread_by_symbol is not None else
                     "M5_BID_OHLC_WITH_ASSUMED_M15_ATR_SPREAD_NOT_TICKS"),
        "historical_spread_factual":historical_m5_spread_by_symbol is not None,
        "next_entry_actual_bidask_verified":False,
        "historical_news_point_in_time_coverage":False,
        "broker_commission_and_slippage_reconciled":False,
        "independent_unseen_holdout":False,
        "chronological_completed_only_memory":True,
        "signals":details,
        "all_technical_proposals":all_technical_proposals,
        "proposals_are_selected_before_future_outcomes":True,
        "adaptive_summary":historical,
        "orders_sent":0,
        "live_execution_authorized":False,
    }


def purged_chronological_splits(events,*,train_fraction=.6,validation_fraction=.2,
                                embargo_seconds=EMBARGO_SECONDS):
    """Partition on SIGNAL chronology; drop training/validation labels
    overlapping the subsequent window, rather than count them OOS.
    """
    if not .4<=train_fraction<=.8 or not .1<=validation_fraction<=.3 or train_fraction+validation_fraction>=.95:
        raise ValueError("bad_training_partition")
    if embargo_seconds<MAX_HOLD_SEC():
        raise ValueError("embargo_shorter_than_position_horizon")
    xs=sorted(events,key=lambda e:(e.cut,e.symbol,e.side))
    if len(xs)<10:return {"train":[],"validation":[],"test":[],"purged":len(xs)}
    b1=xs[int(len(xs)*train_fraction)].cut
    b2=xs[int(len(xs)*(train_fraction+validation_fraction))].cut
    train=[x for x in xs if x.cut<b1 and x.exit_time<b1-embargo_seconds]
    validation=[x for x in xs if b1<=x.cut<b2 and x.exit_time<b2-embargo_seconds]
    test=[x for x in xs if x.cut>=b2]
    return {"train":train,"validation":validation,"test":test,
            "purged":len(xs)-len(train)-len(validation)-len(test),
            "embargo_sec":embargo_seconds}


def MAX_HOLD_SEC():return 300*HORIZON_M5
