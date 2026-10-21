"""Research-only causal candidate checks for the owner's strategy selection.

This is NOT an Elliott-wave classifier, backtest or trade permission. Inputs
must originate from timestamped, independently reviewed historical evidence.
No broker access or order interface is imported.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from string import hexdigits


@dataclass(frozen=True, slots=True)
class StructuralCandidate:
    symbol: str
    side: str
    evidence_sha256: str
    zone_born_ns: int
    structure_break_closed_ns: int
    signal_closed_ns: int
    decision_ns: int
    wave_pivot_times_ns: tuple[int, ...]
    wave_pivot_prices: tuple[float, ...]
    structure_break_level: float
    structure_break_close: float
    zone_low: float
    zone_high: float
    zone_fresh: bool
    entry: float
    stop_loss: float
    target: float
    estimated_cost_price: float


@dataclass(frozen=True, slots=True)
class ResearchCandidateDecision:
    eligible_for_offline_research: bool
    blockers: tuple[str, ...]
    live_execution_authorized: bool = False


def evaluate_structural_candidate(x: StructuralCandidate) -> ResearchCandidateDecision:
    """Validate causal geometry only; never infer profit, edge or live readiness."""
    blockers: list[str] = []
    if not isinstance(x.symbol, str) or not x.symbol.strip() or x.side not in ("BUY", "SELL"):
        blockers.append("invalid_symbol_or_direction")
    digest=x.evidence_sha256
    if not (isinstance(digest,str) and len(digest)==64
            and all(char in hexdigits for char in digest)):
        blockers.append("unverifiable_source_digest")
    t=(x.zone_born_ns,x.structure_break_closed_ns,x.signal_closed_ns,x.decision_ns)
    if any(type(v) is not int for v in t) or not (0<t[0]<=t[1]<=t[2]<=t[3]):
        blockers.append("causal_timestamps_invalid")

    wt=x.wave_pivot_times_ns
    wp=x.wave_pivot_prices
    if (len(wt)!=6 or any(type(v) is not int or v<=0 for v in wt)
            or any(a>=b for a,b in zip(wt,wt[1:]))
            or not isinstance(x.signal_closed_ns,int) or wt[-1]>x.signal_closed_ns):
        blockers.append("wave_pivots_not_causal")
    fields=(x.structure_break_level,x.structure_break_close,
            x.zone_low,x.zone_high,x.entry,x.stop_loss,x.target,
            x.estimated_cost_price)+tuple(wp)
    if (len(wp)!=6 or any(type(v) not in (int,float) or not isfinite(v) for v in fields)
            or any(v<=0 for v in fields[:-1] if v is not x.estimated_cost_price)):
        blockers.append("invalid_price_evidence")
        return ResearchCandidateDecision(False,tuple(blockers))
    if not 0<=x.estimated_cost_price:
        blockers.append("invalid_cost")
    if not x.zone_low<x.zone_high or x.zone_fresh is not True:
        blockers.append("supply_demand_zone_not_fresh")
    if not x.zone_low<=x.entry<=x.zone_high:
        blockers.append("entry_not_at_zone")

    if x.side in ("BUY","SELL"):
        sign=1 if x.side=="BUY" else -1
        if sign*(x.structure_break_close-x.structure_break_level)<=0:
            blockers.append("market_structure_break_unconfirmed")
        if not (sign*(x.entry-x.stop_loss)>0 and sign*(x.target-x.entry)>0):
            blockers.append("stop_or_target_on_wrong_side")
        # Strict impulse hypothesis: wave 2 does not invalidate wave 1,
        # wave 3 exceeds wave 1, wave 4 does not overlap wave 1,
        # wave 5 extends in trend direction, and wave 3 is not shortest.
        p=tuple(sign*v for v in wp)
        w1=p[1]-p[0]
        w3=p[3]-p[2]
        w5=p[5]-p[4]
        impulse=(p[0]<p[1] and p[0]<p[2]<p[1]
                 and p[1]<p[3] and p[1]<p[4]<p[3]
                 and p[3]<p[5] and min(w1,w3,w5)>0
                 and w3>=min(w1,w5))
        if not impulse:
            blockers.append("elliott_impulse_hypothesis_unconfirmed")
        risk=sign*(x.entry-x.stop_loss)+x.estimated_cost_price
        reward=sign*(x.target-x.entry)-x.estimated_cost_price
        if risk<=0 or reward<=0 or reward/risk<1.5:
            blockers.append("insufficient_cost_adjusted_reward")
    return ResearchCandidateDecision(not blockers,tuple(blockers))
