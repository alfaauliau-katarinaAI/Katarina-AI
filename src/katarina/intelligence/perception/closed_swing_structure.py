"""Causal market structure from time-ordered CLOSED bars.

Only use price levels from bars strictly before the signal bar.
Neutral outputs are expected when history is incomplete.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from statistics import mean
from typing import Sequence

from katarina.intelligence.perception.adaptive_regime import StructuralEvidence


@dataclass(frozen=True)
class ClosedBar:
    closed_at_utc: datetime
    open: float
    high: float
    low: float
    close: float


class ClosedSwingStructure:
    def __init__(self, *, lookback: int = 20, atr_window: int = 14):
        if lookback < 10 or atr_window < 5:
            raise ValueError("insufficient structural history")
        self.lookback = lookback
        self.atr_window = atr_window

    def extract(self, bars: Sequence[ClosedBar], *, as_of_utc: datetime,
                spread: float) -> StructuralEvidence:
        if as_of_utc.tzinfo is None:
            raise ValueError("as_of must be timezone aware")
        if not isfinite(spread) or spread < 0:
            raise ValueError("invalid spread")
        count_needed = max(self.lookback + 2, self.atr_window * 2 + 2)
        if len(bars) < count_needed:
            raise ValueError("not enough closed bars")
        checked = []
        prev = None
        for bar in bars:
            t = bar.closed_at_utc
            if t.tzinfo is None or t.astimezone(timezone.utc) > as_of_utc.astimezone(timezone.utc):
                raise ValueError("future or naive bar")
            if prev is not None and t <= prev:
                raise ValueError("bars not strictly ordered")
            prev = t
            values=(bar.open,bar.high,bar.low,bar.close)
            if not all(isfinite(v) and v > 0 for v in values):
                raise ValueError("invalid bar values")
            if bar.high < max(bar.open,bar.close) or bar.low > min(bar.open,bar.close):
                raise ValueError("invalid OHLC geometry")
            checked.append(bar)
        latest=checked[-1]
        earlier=checked[-self.lookback-1:-1]
        highest=max(b.high for b in earlier)
        lowest=min(b.low for b in earlier)
        tr=[]
        for i in range(1,len(checked)):
            b=checked[i]
            pc=checked[i-1].close
            tr.append(max(b.high-b.low,abs(b.high-pc),abs(b.low-pc)))
        recent=mean(tr[-self.atr_window:])
        past=mean(tr[-2*self.atr_window:-self.atr_window])
        if recent <= 0 or past <= 0:
            raise ValueError("zero range history")
        ratio=recent/past
        # Confirm beyond PRIOR channel at a completed bar close.
        breakout=1 if latest.close > highest + .03*recent else (
                 -1 if latest.close < lowest - .03*recent else 0)
        # Sweep and reclaim against PRIOR liquidity; wick rejection must be real.
        body=abs(latest.close-latest.open)
        lower_wick=min(latest.open,latest.close)-latest.low
        upper_wick=latest.high-max(latest.open,latest.close)
        lower_reject=lower_wick >= max(.16*recent, 1.2*body)
        upper_reject=upper_wick >= max(.16*recent, 1.2*body)
        reclaim=1 if latest.low < lowest and latest.close > lowest and lower_reject else (
                -1 if latest.high > highest and latest.close < highest and upper_reject else 0)
        position=(latest.close-lowest)/max(1e-12,highest-lowest)
        return StructuralEvidence(swing_break=breakout,swing_reclaim=reclaim,
                 rejection_direction=reclaim,atr_ratio=ratio,
                 spread_to_atr=spread/recent,
                 channel_position=max(0.,min(1.,position)))
