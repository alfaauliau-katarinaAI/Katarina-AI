"""Synthetic tick fixtures for the tick-replay simulator tests.

Technical fixtures only (Owner order K1): these paths exist to exercise rules, never to measure performance.
Prices are integer tick offsets around ``BASE`` (tick size 0.01 => 400000 = 4000.00).
"""
from __future__ import annotations

from datetime import datetime, timezone

from katarina.research.tick_replay import (CostSpec, DatasetEvidence, SessionEvidence, SymbolContract, Tick,
                                           TickReplay)

BASE = 400_000
SPREAD = 20
MIN = 60_000
M5, M15, H1 = 5 * MIN, 15 * MIN, 60 * MIN
DAY0 = int(datetime(2026, 6, 8, tzinfo=timezone.utc).timestamp() * 1000)   # Monday, before the 2026-10-13 cutoff
SHA = "a" * 64

CONTRACT = SymbolContract("XAUUSD.vx", 2, 0.01, 0.01, 31, 0, 100.0, SHA)
COSTS = CostSpec("USD", 7.0, -30.0, 10.0, 21 * 60, 2, SHA)


def dataset(sequence="UNVERIFIED", max_gap_ms=30 * MIN):
    return DatasetEvidence("XAUUSD.vx", "fixture-server", SHA, SHA, sequence, max_gap_ms)


def sessions(trade_end_ms=None, *, trade=None, quote=None):
    week = (DAY0, DAY0 + 7 * 86_400_000)
    if trade is None:
        trade = ((DAY0, trade_end_ms),) if trade_end_ms is not None else (week,)
    return SessionEvidence(quote or (week,), trade, "fixture SymbolInfoSession*", SHA)


class Path:
    """Builds an ordered list of (time_ms, bid_offset) points and turns it into ``Tick`` objects."""

    def __init__(self, start_ms=DAY0):
        self.start = start_ms
        self.points: list[tuple[int, int]] = []

    def bar(self, tf_ms, o, h, l, c, index):
        """One candle with ticks in four sub-intervals: open, first extreme, second extreme, close."""
        t0 = self.start + index * tf_ms
        first, second = (l, h) if c >= o else (h, l)
        q = tf_ms // 4
        self.points += [(t0 + 1_000, o), (t0 + q + 1_000, first), (t0 + 2 * q + 1_000, second),
                        (t0 + tf_ms - 1_000, c)]
        return self

    def bars(self, tf_ms, rows, first_index=0):
        for i, row in enumerate(rows):
            self.bar(tf_ms, *row, first_index + i)
        return self

    def at(self, time_ms, bid):
        self.points.append((time_ms, bid))
        return self

    def ticks(self, *, mirror=False, spread=SPREAD):
        out = []
        for seq, (t, off) in enumerate(self.points):
            bid = BASE - off if mirror else BASE + off
            out.append(Tick(seq, t, bid, bid + spread))
        return out


# M15 rows: swing HIGH 1500 at bar 2 (confirmed end of bar 4), swing LOW 500 at bar 5 (confirmed end of bar 7).
B1_M15 = [(1000, 1100, 900, 1000), (1000, 1200, 950, 1100), (1100, 1500, 1050, 1400), (1400, 1450, 1000, 1050),
          (1050, 1100, 700, 800), (800, 900, 500, 850), (850, 1000, 600, 950), (950, 1050, 800, 1000)]
B1_SWEEP_START = DAY0 + 8 * M15


def b1_path():
    """Sweep of the M15 low (500) by one M5 candle that closes back above it, bullish."""
    p = Path().bars(M15, B1_M15)
    t = B1_SWEEP_START
    p.at(t + 1_000, 560).at(t + 2 * MIN, 490).at(t + 5 * MIN - 1_000, 600)
    p.at(t + 5 * MIN + 1_000, 610)          # boundary tick that reveals the close: must not fill
    p.at(t + 5 * MIN + 2_000, 600)          # first fill opportunity
    return p


# H1 rows: highs 1200 -> 1500 (HH), lows 800 -> 1000 (HL); bar 12 closes above 1500 (BOS), DEMAND zone = bar 9.
H1_TREND_UP = [(900, 1000, 850, 950), (950, 1100, 900, 1050), (1050, 1200, 1000, 1150), (1150, 1150, 900, 950),
               (950, 1000, 800, 900), (900, 1050, 850, 1000), (1000, 1300, 950, 1250), (1250, 1500, 1200, 1450),
               (1450, 1450, 1100, 1150), (1150, 1200, 1000, 1100), (1100, 1250, 1050, 1200),
               (1200, 1400, 1150, 1350), (1350, 1700, 1300, 1600), (1600, 1650, 1450, 1500),
               (1500, 1550, 1300, 1350)]


def b2_path():
    p = Path().bars(H1, H1_TREND_UP)
    t = DAY0 + 15 * H1
    p.at(t + 1_000, 1350).at(t + 10 * MIN, 1300)                                         # M15 #0: no touch
    p.at(t + 15 * MIN + 1_000, 1250).at(t + 20 * MIN, 1190).at(t + 29 * MIN, 1260)       # M15 #1: touch + bullish
    p.at(t + 30 * MIN + 1_000, 1265).at(t + 30 * MIN + 2_000, 1265)                      # boundary, then fill
    return p


def b3_rows():
    rows = list(H1_TREND_UP[:13])
    rows[2] = (1050, 2000, 1000, 1150)      # a higher swing HIGH (2000) that stays valid as the B3 target
    return rows


def b3_path():
    p = Path().bars(H1, b3_rows())
    t = DAY0 + 13 * H1
    p.at(t + 1_000, 1520).at(t + 2 * MIN, 1495).at(t + 4 * MIN, 1560)    # M5 retest of 1500, bullish close above
    p.at(t + 5 * MIN + 1_000, 1560).at(t + 5 * MIN + 2_000, 1560)
    return p


def run(ticks, *, sess="default", seq="UNVERIFIED", max_gap_ms=30 * MIN, contract=CONTRACT, candidates=None):
    s = sessions() if sess == "default" else sess
    replay = TickReplay(ticks, contract=contract, dataset=dataset(seq, max_gap_ms), costs=COSTS, sessions=s,
                        candidates=candidates)
    return replay, replay.run()


def events(replay, candidate_id, event_type=None):
    return [e for e in replay.events if e["candidate_id"] == candidate_id
            and (event_type is None or e["event_type"] == event_type)]
