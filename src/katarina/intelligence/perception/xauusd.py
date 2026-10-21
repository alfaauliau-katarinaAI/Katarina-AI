from __future__ import annotations
from dataclasses import dataclass
from .regime import Regime, RegimeAssessment

@dataclass(frozen=True, slots=True)
class XauusdAssessment:
    bias: int
    score: float
    reasons: tuple[str, ...]
    uncertainty: float
    valid_domain: bool

class XauusdSpecialistV1:
    symbol="XAUUSD"
    def assess(self, *, regime: RegimeAssessment, momentum: float, spread_bps: float, session: str, data_fresh: bool=True) -> XauusdAssessment:
        reasons=[]
        if not data_fresh or regime.out_of_distribution or regime.regime in {Regime.UNKNOWN,Regime.HIGH_VOL}:
            return XauusdAssessment(0,0.0,("unsafe_or_unknown_domain",),1.0,False)
        if spread_bps>8.0:
            return XauusdAssessment(0,0.0,("spread_too_wide",),0.9,True)
        bias=1 if regime.regime is Regime.TREND_UP else -1 if regime.regime is Regime.TREND_DOWN else 0
        if bias and momentum*bias>0: reasons.append("regime_momentum_alignment")
        if session.upper() in {"LONDON","NEW_YORK","OVERLAP"}: reasons.append("liquid_session")
        score=min(1.0, regime.confidence*0.65 + min(abs(momentum)*20.0,0.25) + (0.1 if "liquid_session" in reasons else 0.0))
        uncertainty=max(0.0,1.0-score)
        if bias==0: reasons.append("range_no_directional_edge")
        return XauusdAssessment(bias,score,tuple(reasons),uncertainty,True)
