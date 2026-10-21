"""Causal score/side eligibility for OFFLINE research, not live execution.

Only candidate-known quantities can enter this gate. It does not inspect a
candidate's future returns, news permission or broker execution readiness.
"""
from __future__ import annotations
from math import isfinite


def eligible_for_research(score: float, side: str, *,
                          minimum_score: float = 0.,
                          research_side: str = "BOTH") -> bool:
    if (not isinstance(score,(float,int)) or isinstance(score,bool) or
            not isfinite(score) or not 0<=score<=1):
        raise ValueError("invalid_candidate_score")
    if (not isinstance(minimum_score,(float,int)) or
            isinstance(minimum_score,bool) or not isfinite(minimum_score)
            or not 0<=minimum_score<=1):
        raise ValueError("invalid_research_floor")
    if side not in ("BUY","SELL") or research_side not in ("BOTH","BUY","SELL"):
        raise ValueError("invalid_research_side")
    return bool(score>=minimum_score and
                (research_side=="BOTH" or research_side==side))
