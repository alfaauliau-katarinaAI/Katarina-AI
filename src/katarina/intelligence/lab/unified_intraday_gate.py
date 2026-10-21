"""Point-in-time V6 scanner/Brain integration, pure cross-platform code.

No MetaTrader5 import, no order routing; suitable for Linux GitHub CI.
"""
from __future__ import annotations
from datetime import datetime,timezone
from math import isfinite
import numpy as np
from katarina.intelligence.lab.intraday_scalp_research import Candidate
from katarina.intelligence.cognition.market_decision_pipeline import (
    MarketDecisionPipeline,SensorCandle)
from katarina.intelligence.perception.semantic_setup_truth import CausalSetupValidator
from katarina.intelligence.perception.structural_entry_quality import StructuralEntryQuality

def _cut_end(t,cut,period):
    """The exclusive index of all bars FULLY CLOSED at the cut."""
    return int(np.searchsorted(t,cut-period,side="right"))

def _closed_sensors(bars,period):
    return [SensorCandle(
        datetime.fromtimestamp(int(row["time"])+period,timezone.utc),
        float(row["open"]),float(row["high"]),
        float(row["low"]),float(row["close"]),
        float(row["tick_volume"])) for row in bars]

def check_candidate(
    x:Candidate, m5,m15,h1,clocks,point:float,
    semantic:CausalSetupValidator,
    quality:StructuralEntryQuality,
    brain:MarketDecisionPipeline,
):
    """No future bars; requires all 3 independent entry checks at the cut."""
    cut=x.cut; frames={}
    for name,arr,secs in (("M5",m5,300),("M15",m15,900),("H1",h1,3600)):
        end=_cut_end(clocks[name],cut,secs)
        if end<90 or end>len(arr):
            return None,"missing_history"
        lastclose=int(clocks[name][end-1])+secs
        if lastclose>cut or cut-lastclose>2*secs:
            return None,"stale_or_future_context"
        frames[name]=_closed_sensors(arr[end-90:end],secs)
    at=datetime.fromtimestamp(cut,timezone.utc)
    if not isfinite(point) or point<=0:
        return None,"invalid_broker_point"
    spread=float(m5["spread"][x.idx])*point
    if spread<=0 or not isfinite(spread):
        return None,"missing_signal_spread"
    intended="TREND_PULLBACK" if x.mode=="INTRADAY" else "REVERSAL_RECLAIM"
    s=semantic.assess(side=x.side,playbook=intended,
        m5=frames["M5"],m15=frames["M15"],h1=frames["H1"],
        spread=spread,as_of_utc=at)
    if not s.pattern_confirmed:
        return None,"semantic_false_"+(s.blockers[0] if s.blockers else "unknown")
    q=quality.assess(side=x.side,playbook=intended,
        m5=frames["M5"],m15=frames["M15"],h1=frames["H1"],
        spread=spread,as_of_utc=at)
    if not q.eligible:
        return None,"quality_false_"+(q.blockers[0] if q.blockers else "unknown")
    decision=brain.evaluate(symbol=x.symbol,candles=frames,
        as_of_utc=at,actual_spread=spread,
        broker_session_open=True,data_fresh=True,
        news_blackout=False,news_context_verified=True,
        use_structural_entry_gate=True,
        use_semantic_setup_gate=True,
        instrument_point=point)
    if decision.action!=x.side:
        return None,"brain_no_matching_direction"
    if decision.playbook!=intended:
        return None,"brain_different_playbook"
    if (decision.entry_quality is None or not decision.entry_quality.eligible
          or decision.semantic_setup is None
          or not decision.semantic_setup.pattern_confirmed):
        return None,"brain_gate_rejected"
    return x,"pass"

def min_capital_for_broker(info,stop_distance,mode):
    """CURRENT broker tick value only; not independently verified history."""
    step=float(info.trade_tick_size)
    value=float(info.trade_tick_value_loss)
    volume=float(info.volume_min)
    risk=.0025 if mode=="INTRADAY" else .001
    if not all(isfinite(v) and v>0 for v in (step,value,volume,risk,stop_distance)):
        return None
    return (stop_distance/step*value*volume)/risk