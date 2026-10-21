from __future__ import annotations
from dataclasses import dataclass
from statistics import mean

@dataclass(frozen=True, slots=True)
class DriftAssessment:
    detected: bool
    baseline_mean: float
    recent_mean: float
    delta: float
    action: str

class LearningEngine:
    def detect_drift(self, baseline: list[float], recent: list[float], *, threshold: float) -> DriftAssessment:
        if not baseline or not recent: return DriftAssessment(True,0.0,0.0,0.0,"RESEARCH_ONLY")
        b=mean(baseline); r=mean(recent); d=abs(r-b)
        return DriftAssessment(d>=threshold,b,r,d,"CREATE_CANDIDATE" if d>=threshold else "NO_CHANGE")
    def production_mutation_allowed(self) -> bool:
        return False
