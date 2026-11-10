"""Closed BID candles built from the broker tick stream (D10-K23: structure and touch use BID).

A candle covers the half-open interval ``[start_ms, end_ms)`` (D10-K24), so a tick exactly at ``end_ms``
belongs to the next candle. A candle is *valid* only when it has ticks and no quote gap longer than the
dataset limit, measured inside official quote-session time, touches it ("candle hilang/gap bukan candle sah").
Scheduled closures (daily break, weekend) are not gaps: no candle is expected there.
With an unverified tick sequence, a first/last millisecond group whose BID values differ makes the candle
open/close ambiguous; signals that need that open/close are blocked instead of guessed.
"""
from __future__ import annotations

from dataclasses import dataclass

from .contract import TIMEFRAME_MS


@dataclass
class Bar:
    tf: str
    start_ms: int
    end_ms: int
    open: int
    high: int
    low: int
    close: int
    ticks: int
    last_spread: int
    valid: bool = True
    invalid_reason: str | None = None
    open_ambiguous: bool = False
    close_ambiguous: bool = False

    @property
    def bullish(self) -> bool:
        return self.close > self.open

    @property
    def bearish(self) -> bool:
        return self.close < self.open

    def ident(self) -> str:
        return f"{self.tf}@{self.start_ms}"


class BarBuilder:
    def __init__(self, tf: str, *, sequence_verified: bool):
        self.tf = tf
        self.length = TIMEFRAME_MS[tf]
        self.sequence_verified = sequence_verified
        self.current: Bar | None = None
        self._group_time = None
        self._group_bid = None
        self._group_ambiguous = False
        self._first_group = True

    def boundary_after(self, time_ms: int) -> int:
        return (time_ms // self.length + 1) * self.length

    def close_due(self, time_ms: int):
        """Return the finished candle if ``time_ms`` is at/after its end, else ``None``."""
        bar = self.current
        if bar is None or time_ms < bar.end_ms:
            return None
        if self._first_group:
            bar.open_ambiguous = self._group_ambiguous
        bar.close_ambiguous = self._group_ambiguous
        self.current = None
        return bar

    def add(self, tick):
        start = tick.time_ms // self.length * self.length
        bar = self.current
        if bar is None:
            self.current = Bar(self.tf, start, start + self.length, tick.bid, tick.bid, tick.bid, tick.bid, 1,
                               tick.ask - tick.bid)
            self._group_time, self._group_bid, self._group_ambiguous, self._first_group = (
                tick.time_ms, tick.bid, False, True)
            return
        if tick.time_ms == self._group_time:
            if tick.bid != self._group_bid and not self.sequence_verified:
                self._group_ambiguous = True
        else:
            if self._first_group:
                bar.open_ambiguous = self._group_ambiguous
            self._first_group = False
            self._group_time, self._group_bid, self._group_ambiguous = tick.time_ms, tick.bid, False
        bar.high = max(bar.high, tick.bid)
        bar.low = min(bar.low, tick.bid)
        bar.close = tick.bid
        bar.ticks += 1
        bar.last_spread = tick.ask - tick.bid

    def mark_gap(self, reason: str):
        if self.current is not None:
            self.current.valid, self.current.invalid_reason = False, reason
