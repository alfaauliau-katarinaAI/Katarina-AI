from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Regime(str, Enum):
    TREND_UP="TREND_UP"; TREND_DOWN="TREND_DOWN"; RANGE="RANGE"; HIGH_VOL="HIGH_VOL"; UNKNOWN="UNKNOWN"

@dataclass(frozen=True, slots=True)
class RegimeAssessment:
    regime: Regime
    confidence: float
    out_of_distribution: bool

class MarketRegimeEngine:
    def classify(self, *, momentum: float, volatility: float, alignment: float, history_ok: bool=True) -> RegimeAssessment:
        if not history_ok or volatility < 0 or alignment < 0 or alignment > 1:
            return RegimeAssessment(Regime.UNKNOWN,0.0,True)
        if volatility > 0.02:
            return RegimeAssessment(Regime.HIGH_VOL,min(1.0,volatility/0.04),volatility>0.05)
        threshold=max(0.001,volatility*1.5)
        if alignment>=0.55 and momentum>threshold:
            return RegimeAssessment(Regime.TREND_UP,min(1.0,alignment+abs(momentum)),False)
        if alignment>=0.55 and momentum<-threshold:
            return RegimeAssessment(Regime.TREND_DOWN,min(1.0,alignment+abs(momentum)),False)
        return RegimeAssessment(Regime.RANGE,max(0.25,1.0-alignment),False)
