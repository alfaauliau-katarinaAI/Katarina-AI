"""KATARINA KFEI: closed-bar Flow-Efficiency Index.

Use as research context to identify persistent directional motion vs chop.
NOT a win-rate forecast and not an authorization to place broker orders.
All inputs are known at the decision timestamp.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Sequence


@dataclass(frozen=True, slots=True)
class FlowEfficiency:
    directional_strength: float
    efficiency_ratio: float
    displacement_to_atr: float
    volatility_expansion: float
    spread_to_atr: float
    regime_hint: str
    research_only: bool = True
    live_execution_authorized: bool = False


class KatarinaFlowEfficiencyIndex:
    """KFEI combines THREE non-redundant dimensions without new veto indicators.

    Formula: sign(C_now-C_12) * ER12 * min(abs(C_now-C_12)/ATR14,3)
             * min(ATR14/upper_median(previous_50_ATRs),2)
    ER12 = abs(net change) / sum(abs(consecutive close changes)).
    Spread/ATR is exposed separately, rather than disguised as predictive edge.
    """

    def calculate(self, closed_prices: Sequence[float],
                  atr_values: Sequence[float], *, broker_spread: float) -> FlowEfficiency:
        if len(closed_prices)<13 or len(atr_values)<51:
            raise ValueError("KFEI requires 13 closed prices and 51 ATR values")
        closes=tuple(float(x) for x in closed_prices[-13:])
        recent_atr=tuple(float(x) for x in atr_values[-51:])
        if (not all(isfinite(x) and x>0 for x in closes) or
             not all(isfinite(x) and x>0 for x in recent_atr) or
             not isfinite(broker_spread) or broker_spread<0):
            raise ValueError("KFEI cannot use invalid/negative prices or ATR")
        displacement=closes[-1]-closes[0]
        traveled=sum(abs(closes[i]-closes[i-1]) for i in range(1,13))
        er=min(1.,abs(displacement)/traveled) if traveled>0 else 0.
        atr=recent_atr[-1]
        # Upper median of the 50 prior ATRs, matching the frozen KFEI audit.
        prior=sorted(recent_atr[:-1])
        ratio=atr/prior[len(prior)//2]
        normalized=abs(displacement)/atr
        sign=1 if displacement>0 else -1 if displacement<0 else 0
        strength=sign*er*min(normalized,3.)*min(ratio,2.)
        if ratio>=2.5:hint="VOLATILITY_SHOCK"
        elif er<.20:hint="SIDEWAYS_OR_NOISE"
        elif abs(strength)>.6:hint="DIRECTIONAL_DRIVE"
        else:hint="TRANSITION_OR_WEAK_DRIVE"
        return FlowEfficiency(round(strength,6),round(er,6),
           round(normalized,6),round(ratio,6),round(broker_spread/atr,6),hint)
