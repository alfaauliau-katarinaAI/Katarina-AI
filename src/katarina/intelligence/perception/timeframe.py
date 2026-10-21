from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True, slots=True)
class TimeframeView:
    timeframe: str
    direction: int
    strength: float
    fresh: bool=True

@dataclass(frozen=True, slots=True)
class MultiTimeframeAssessment:
    alignment: float
    dominant_direction: int
    conflicts: int
    ready: bool

class MultiTimeframeEngine:
    def assess(self, views: Mapping[str, TimeframeView]) -> MultiTimeframeAssessment:
        if not views or any(not v.fresh for v in views.values()):
            return MultiTimeframeAssessment(0.0,0,0,False)
        weighted=0.0; weight=0.0; conflicts=0
        dirs=[]
        for v in views.values():
            s=max(0.0,min(1.0,float(v.strength)))
            weighted += (1 if v.direction>0 else -1 if v.direction<0 else 0)*s
            weight += s
            if v.direction: dirs.append(1 if v.direction>0 else -1)
        if weight==0: return MultiTimeframeAssessment(0.0,0,0,True)
        dom=1 if weighted>0 else -1 if weighted<0 else 0
        conflicts=sum(1 for d in dirs if dom and d!=dom)
        return MultiTimeframeAssessment(abs(weighted)/weight,dom,conflicts,True)
