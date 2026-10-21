"""KATARINA causal structural SL/TP planning (research only).

Computes invalidation & first attainable structural target from CLOSED M5/M15/H1
candles. Output is a hypothetical plan, NOT an executable MT5 order or edge.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Sequence


@dataclass(frozen=True)
class StructuralExitPlan:
    direction: str
    approved_for_research: bool
    stop: float | None
    target: float | None
    risk_price: float | None
    reward_risk: float | None
    stop_basis: str
    target_basis: str
    blockers: tuple[str, ...]
    research_only: bool = True
    live_execution_authorized: bool = False


def _atr(bars: Sequence, n: int=14) -> float:
    changes = [
        max(b.high-b.low, abs(b.high-a.close), abs(b.low-a.close))
        for a, b in zip(bars[-n-1:-1], bars[-n:])
    ]
    return sum(changes)/len(changes) if len(changes)==n else 0.0


class StructuralExitPlanner:
    def __init__(self, min_rr: float=1.25, max_rr: float=3.5,
                 stop_buffer_atr: float=.15, max_stop_atr: float=4.0):
        if not 0<min_rr<max_rr or not 0<stop_buffer_atr<1 or max_stop_atr<=1:
            raise ValueError("invalid_structure_plan_parameters")
        self.min_rr=min_rr
        self.max_rr=max_rr
        self.stop_buffer_atr=stop_buffer_atr
        self.max_stop_atr=max_stop_atr

    def plan(self, *, side: str, m5:Sequence, m15:Sequence, h1:Sequence,
             expected_entry:float, spread:float, point:float,
             as_of_utc:datetime) -> StructuralExitPlan:
        if side not in ("BUY","SELL") or as_of_utc.tzinfo is None:
            raise ValueError("invalid_side_or_datetime")
        if any(len(b)<40 for b in (m5,m15,h1)):
            raise ValueError("insufficient_history")
        for bars in (m5,m15,h1):
            prev=None
            for b in bars:
                ts=b.closed_at_utc
                if ts.tzinfo is None or ts>as_of_utc or (prev and ts<=prev):
                    raise ValueError("future_or_unordered")
                prev=ts
                if not all(isfinite(v) and v>0 for v in (b.open,b.high,b.low,b.close)):
                    raise ValueError("invalid_prices")
                if b.high<max(b.open,b.close) or b.low>min(b.open,b.close):
                    raise ValueError("invalid_price_geometry")
        if not all(isfinite(x) and x>0 for x in (expected_entry,point)):
            raise ValueError("invalid_entry_or_point")
        if not isfinite(spread) or spread<0:
            raise ValueError("invalid_spread")
        atr=_atr(m5)
        if atr<=0:raise ValueError("invalid_atr")
        side_num=1 if side=="BUY" else -1
        buffer=max(self.stop_buffer_atr*atr,2*point)+spread
        local = m5[-10:]
        mid = m15[-6:]
        if side_num>0:
            local_stop=min(x.low for x in local)
            mid_stop=min(x.low for x in mid)
            if expected_entry-mid_stop<=2.5*atr and mid_stop<expected_entry:
                invalidation=min(local_stop,mid_stop)
                stop_basis="recent_M5_low_and_nearby_M15_demand"
            else:
                invalidation=local_stop
                stop_basis="recent_M5_low"
            stop=invalidation-buffer
            candidates=[
                ("recent_M15_resistance",max(x.high for x in m15[-21:-1])),
                ("recent_H1_resistance",max(x.high for x in h1[-21:-1])),
            ]
        else:
            local_stop=max(x.high for x in local)
            mid_stop=max(x.high for x in mid)
            if mid_stop-expected_entry<=2.5*atr and mid_stop>expected_entry:
                invalidation=max(local_stop,mid_stop)
                stop_basis="recent_M5_high_and_nearby_M15_supply"
            else:
                invalidation=local_stop
                stop_basis="recent_M5_high"
            stop=invalidation+buffer
            candidates=[
                ("recent_M15_support",min(x.low for x in m15[-21:-1])),
                ("recent_H1_support",min(x.low for x in h1[-21:-1])),
            ]
        risk=side_num*(expected_entry-stop)
        blockers=[]
        if risk<=max(3*spread,3*point):
            blockers.append("stop_too_tight_for_cost")
        if risk>self.max_stop_atr*atr:
            blockers.append("structure_stop_too_wide")
        if stop<=0:blockers.append("invalid_stop")
        possibilities=[]
        if risk>0:
            for basis, price in candidates:
                rr=side_num*(price-expected_entry)/risk
                if self.min_rr<=rr<=self.max_rr:
                    possibilities.append((rr,basis,price))
        if not possibilities:
            blockers.append("no_structural_target_within_rr_bounds")
            return StructuralExitPlan(side,False,round(stop,9) if stop>0 else None,
                None,round(risk,9) if risk>0 else None,None,stop_basis,"none",
                tuple(blockers))
        rr,basis,target=min(possibilities,key=lambda q:q[0])
        return StructuralExitPlan(side,not blockers,
            round(stop,9),round(target,9),round(risk,9),round(rr,4),
            stop_basis,basis,tuple(blockers))