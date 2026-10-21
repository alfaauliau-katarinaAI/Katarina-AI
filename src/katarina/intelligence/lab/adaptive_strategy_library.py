"""Four closed-candle strategy *hypotheses*, separate from production gates.

Only proposes research candidates. Requires real OHLC and broker point/spread.
No backtest performance can be inferred from these pattern definitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import mean


@dataclass(frozen=True)
class ClosedBar:
    """time is bar CLOSE time in verified, monotonically ordered clock."""
    time: int
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self):
        if not isinstance(self.time, int) or self.time <= 0:
            raise ValueError("invalid_candle_time")
        if not all(isfinite(x) and x > 0 for x in (
                self.open, self.high, self.low, self.close)):
            raise ValueError("invalid_price")
        if self.high < max(self.open, self.close, self.low) or (
                self.low > min(self.open, self.close)):
            raise ValueError("invalid_ohlc")


@dataclass(frozen=True)
class StrategyHypothesis:
    symbol: str
    strategy_id: str
    side: str
    regime: str
    signal_at: int
    stop: float
    target: float
    reference_close: float
    score: float
    research_only: bool = True
    live_execution_authorized: bool = False


def _validate(bars: tuple[ClosedBar, ...], now: int, min_len: int):
    if len(bars) < min_len:
        return False
    times = [b.time for b in bars]
    if times != sorted(set(times)) or times[-1] > now:
        raise ValueError("noncausal_bar_input")
    return True


def _atr(bars: tuple[ClosedBar, ...], n=14):
    if len(bars) < n+1:
        return None
    tr = [
        max(b.high-b.low, abs(b.high-bars[i-1].close),
            abs(b.low-bars[i-1].close))
        for i,b in enumerate(bars) if i
    ]
    return mean(tr[-n:])


def classify_closed_regime(m5: tuple[ClosedBar, ...],
                           h1: tuple[ClosedBar, ...],
                           *, now: int) -> str:
    """H1 slope / range diagnostic, never a calibrated market forecast."""
    if not _validate(m5, now, 30) or not _validate(h1, now, 16):
        return "UNKNOWN"
    volatility = _atr(h1)
    if not volatility or volatility <= 0:
        return "UNKNOWN"
    slope = (h1[-1].close - h1[-7].close) / volatility
    if slope >= 1.3:
        return "TREND_UP"
    if slope <= -1.3:
        return "TREND_DOWN"
    return "RANGE_OR_MIXED"


def propose_closed_candle_strategies(symbol: str,
                                      m5: tuple[ClosedBar, ...],
                                      h1: tuple[ClosedBar, ...],
                                      *, now: int,
                                      spread: float,
                                      point: float) -> tuple[StrategyHypothesis, ...]:
    if not symbol or not isfinite(point) or point <= 0:
        raise ValueError("invalid_broker_symbol_point")
    if not isfinite(spread) or spread < 0:
        raise ValueError("invalid_broker_spread")
    if not _validate(m5, now, 30) or not _validate(h1, now, 16):
        return ()
    atr = _atr(m5)
    if not atr or atr <= 0 or spread / atr > .20:
        return ()
    state = classify_closed_regime(m5, h1, now=now)
    latest, prev = m5[-1], m5[-2]
    old = m5[-22:-2]
    prev_hi = max(x.high for x in old)
    prev_lo = min(x.low for x in old)
    candles = m5[-8:-1]
    down_correction = sum(x.close < x.open for x in candles) >= 2
    up_correction = sum(x.close > x.open for x in candles) >= 2
    signal = latest.close
    hypotheses = []

    def add(name: str, side: str, stop: float, score: float):
        risk = signal-stop if side == "BUY" else stop-signal
        if risk <= max(3*point, spread*2) or risk > 4*atr:
            return
        target = signal + (1.6*risk if side == "BUY" else -1.6*risk)
        hypotheses.append(StrategyHypothesis(
            symbol, name, side, state, latest.time, round(stop, 8),
            round(target, 8), signal, score))

    # Trend continuation: a correction followed by a decisive closed bar.
    if state == "TREND_UP" and down_correction and (
            latest.close > prev.close and latest.close-latest.open >= .35*atr):
        add("TREND_PULLBACK", "BUY", min(x.low for x in m5[-8:]), .70)
    if state == "TREND_DOWN" and up_correction and (
            latest.close < prev.close and latest.open-latest.close >= .35*atr):
        add("TREND_PULLBACK", "SELL", max(x.high for x in m5[-8:]), .70)

    # Closed breakout on the previous bar, followed by retest/rejection now.
    if (state == "TREND_UP" and prev.close > prev_hi+.1*atr and
            latest.low <= prev_hi and latest.close > prev_hi and
            latest.close > latest.open):
        add("BREAKOUT_RETEST", "BUY", min(latest.low, prev.low)-.1*atr, .66)
    if (state == "TREND_DOWN" and prev.close < prev_lo-.1*atr and
            latest.high >= prev_lo and latest.close < prev_lo and
            latest.close < latest.open):
        add("BREAKOUT_RETEST", "SELL", max(latest.high, prev.high)+.1*atr, .66)

    # Sweep reversal deliberately separate for BUY and SELL.
    if state == "RANGE_OR_MIXED":
        lower_wick = min(latest.open, latest.close)-latest.low
        upper_wick = latest.high-max(latest.open, latest.close)
        if (latest.low < prev_lo-.08*atr and latest.close > prev_lo
                and lower_wick >= .4*atr):
            add("LIQUIDITY_SWEEP_RECLAIM", "BUY", latest.low-.1*atr, .62)
        if (latest.high > prev_hi+.08*atr and latest.close < prev_hi
                and upper_wick >= .4*atr):
            add("LIQUIDITY_SWEEP_RECLAIM", "SELL", latest.high+.1*atr, .62)

        # Lower conviction candidate in ranges: reversal near established edge.
        if (latest.close < prev_lo+.3*atr and latest.close > latest.open
                and prev.close < prev.open):
            add("RANGE_MEAN_REVERSION", "BUY", min(latest.low, prev.low)-.1*atr, .55)
        if (latest.close > prev_hi-.3*atr and latest.close < latest.open
                and prev.close > prev.open):
            add("RANGE_MEAN_REVERSION", "SELL", max(latest.high, prev.high)+.1*atr, .55)
    return tuple(hypotheses)
