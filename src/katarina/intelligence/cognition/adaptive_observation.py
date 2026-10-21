"""Composable Brain V2 research observer: frames + real closed OHLC + seasonality.

Not registered as a live MT5 execution engine; no order submit capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from katarina.engines.adaptive_scalper import (
    AdaptiveScalpRouter, ClosedPriceContext, ResearchEntryPlan)
from katarina.intelligence.perception.adaptive_regime import (
    AdaptiveRegimeEngine, ClosedFrame, MarketRead)
from katarina.intelligence.perception.causal_seasonality import (
    CausalSeasonality, SeasonalEstimate)
from katarina.intelligence.perception.closed_swing_structure import (
    ClosedBar, ClosedSwingStructure)


@dataclass(frozen=True)
class BrainV2Observation:
    regime: MarketRead
    proposal: ResearchEntryPlan
    seasonal_context: SeasonalEstimate | None
    research_only: bool = True
    live_risk_authorized: bool = False


class KatarinaAdaptiveBrainV2:
    def __init__(self):
        self._swing = ClosedSwingStructure()
        self._regime = AdaptiveRegimeEngine()
        self._scalper = AdaptiveScalpRouter()

    def observe(self, *, symbol: str, frames: Mapping[str, ClosedFrame],
                closed_bars: Sequence[ClosedBar], as_of_utc: datetime,
                actual_spread: float, broker_session_open: bool, data_fresh: bool,
                news_blackout: bool,
                seasonality: CausalSeasonality | None = None) -> BrainV2Observation:
        """No order path; supply already-validated and strictly closed sensor data.

        Structural data are computed only from bars before or at as_of; channel
        extrema EXCLUDE signal bar, so its break cannot repaint history.
        """
        structure = self._swing.extract(closed_bars,as_of_utc=as_of_utc,
                                        spread=actual_spread)
        regime = self._regime.assess(frames=frames,as_of_utc=as_of_utc,
                                     structure=structure)
        price = closed_bars[-1]
        prior = closed_bars[-21:-1]
        channel_h=max(x.high for x in prior)
        channel_l=min(x.low for x in prior)
        if frames["M5"].closed_at_utc != price.closed_at_utc:
            raise ValueError("M5 summary and signal bar timestamps differ")
        seasonal = (seasonality.estimate(symbol,as_of_utc=as_of_utc)
                    if seasonality is not None else None)
        candle = ClosedPriceContext(
            price.open,price.high,price.low,price.close,
            closed_bars[-2].close,channel_h,channel_l,
            frames["M5"].atr,structure.spread_to_atr,
            data_fresh,broker_session_open,news_blackout)
        plan = self._scalper.plan(
            symbol, regime, candle,
            seasonality_tilt=seasonal.directional_tilt if seasonal else 0.0)
        return BrainV2Observation(regime,plan,seasonal)
