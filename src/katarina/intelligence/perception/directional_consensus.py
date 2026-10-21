"""Causal, side-aware directional agreement diagnostic for native Brain V3.

Not a probability of price movement. It checks closed M5/M15/H1
momentum against a candidate side and records explicit contrary evidence.
Only a STRONG two-timeframe contradiction can veto a preexisting technical
signal in trend/pullback regimes. Reversal and range regimes are exempt:
countertrend activity may be their stated purpose.
No external API, ML fit, funding assumption, broker execution or risk override.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Mapping, Sequence

from katarina.intelligence.cognition.market_decision_pipeline import SensorCandle


@dataclass(frozen=True)
class DirectionAgreement:
    side:str
    regime:str
    verdict:str
    h1_momentum_atr:float
    m15_momentum_atr:float
    m5_rejection:bool
    veto_strong_contradiction:bool
    supports:tuple[str,...]
    challenges:tuple[str,...]
    not_a_win_probability:bool=True


def _atr(xs:Sequence[SensorCandle],window:int=14)->float:
    sample=xs[-window-1:]
    if len(sample)<window+1:
        raise ValueError("insufficient_atr")
    tr=[max(b.high-b.low,abs(b.high-a.close),abs(b.low-a.close))
        for a,b in zip(sample,sample[1:])]
    atr=sum(tr)/len(tr)
    if not isfinite(atr) or atr<=0:
        raise ValueError("invalid_atr")
    return atr


def assess_direction(*,candles:Mapping[str,Sequence[SensorCandle]],
                     as_of_utc:datetime,side:str,regime:str)->DirectionAgreement:
    """All momentum computed as of the latest COMPLETED broker bars."""
    if side not in ("BUY","SELL"):
        raise ValueError("direction_side_required")
    if as_of_utc.tzinfo is None:
        raise ValueError("timezone_aware_market_clock_required")
    cutoff=as_of_utc.astimezone(timezone.utc)
    for tf in ("M5","M15","H1"):
        bars=candles.get(tf,())
        if len(bars)<55:
            raise ValueError("insufficient_multitimeframe_data")
        if (bars[-1].closed_at_utc.tzinfo is None or
            bars[-1].closed_at_utc.astimezone(timezone.utc)>cutoff):
            raise ValueError("future_broker_bar")
    m5,m15,h1=(candles[k] for k in ("M5","M15","H1"))
    sign=1 if side=="BUY" else -1
    h1p=(h1[-1].close-h1[-8].close)/_atr(h1)
    m15p=(m15[-1].close-m15[-5].close)/_atr(m15)
    latest=m5[-1]
    m5_confirms=(latest.close>latest.open if sign>0
                 else latest.close<latest.open)
    supports=[];challenges=[]
    if sign*h1p>=.30:supports.append("H1_closed_structure_supports_"+side)
    elif sign*h1p<=-.50:challenges.append("H1_closed_structure_opposes_"+side)
    else:challenges.append("H1_direction_not_established")
    if sign*m15p>=.25:supports.append("M15_closed_momentum_supports_"+side)
    elif sign*m15p<=-.35:challenges.append("M15_closed_momentum_opposes_"+side)
    else:challenges.append("M15_momentum_unconfirmed")
    if m5_confirms:supports.append("M5_last_closed_candle_confirms_"+side)
    else:challenges.append("M5_last_candle_does_not_confirm_"+side)
    # Both higher frames demonstrably disagree in a trend or pullback
    # context: deterministic WAIT. Not a fitted profitable strategy rule.
    trend_or_pullback=regime in (
        "TREND_UP","TREND_DOWN","PULLBACK_UP","PULLBACK_DOWN")
    contradiction=(trend_or_pullback and
                   sign*h1p<=-.50 and sign*m15p<=-.35)
    if contradiction:
        verdict="H1_M15_STRONG_OPPOSITION_WAIT"
    elif sign*h1p>=.30 and sign*m15p>=.25 and m5_confirms:
        verdict="THREE_TIMEFRAME_AGREEMENT"
    elif "PULLBACK" in regime and sign*h1p>=.30:
        verdict="HTF_ALIGNED_PULLBACK_AWAIT_M5_M15_CONFIRMATION"
    elif "SIDEWAYS" in regime:
        verdict="RANGE_EDGE_MUST_BE_VALIDATED_SEPARATELY"
    elif "REVERSAL" in regime or "BREAKOUT" in regime:
        verdict="STRUCTURAL_TRANSITION_REQUIRES_CANDLE_CONFIRMATION"
    else:
        verdict="MIXED_EVIDENCE_CONDITIONAL"
    return DirectionAgreement(
        side=side,regime=regime,verdict=verdict,
        h1_momentum_atr=round(h1p,4),
        m15_momentum_atr=round(m15p,4),
        m5_rejection=m5_confirms,
        veto_strong_contradiction=bool(contradiction),
        supports=tuple(supports),challenges=tuple(challenges),
    )
