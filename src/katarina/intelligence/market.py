from __future__ import annotations
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Sequence

@dataclass(frozen=True, slots=True)
class MarketIntelligence:
    returns: tuple[float, ...]
    momentum: float
    volatility: float
    zscore: float
    spread_bps: float
    sufficient: bool

class MarketIntelligenceEngine:
    def analyze(self, closes: Sequence[float], *, bid: float | None = None, ask: float | None = None) -> MarketIntelligence:
        if len(closes) < 3 or any(x <= 0 for x in closes):
            return MarketIntelligence((), 0.0, 0.0, 0.0, 0.0, False)
        rets=tuple((closes[i]/closes[i-1])-1.0 for i in range(1,len(closes)))
        vol=pstdev(rets) if len(rets)>1 else 0.0
        mom=closes[-1]/closes[0]-1.0
        sigma=pstdev(closes)
        z=0.0 if sigma==0 else (closes[-1]-mean(closes))/sigma
        spread=0.0
        if bid is not None and ask is not None and bid>0 and ask>=bid:
            mid=(bid+ask)/2.0
            spread=(ask-bid)/mid*10000.0
        return MarketIntelligence(rets,mom,vol,z,spread,True)
