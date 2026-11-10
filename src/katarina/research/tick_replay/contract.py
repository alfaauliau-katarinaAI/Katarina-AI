"""Input contracts for the six-candidate XAUUSD tick-replay simulator (research only, no orders).

Rules come from the Owner decisions D10-K1..K27 (docs/research/SIX_CANDIDATE_PREREGISTRATION_SPEC_20261104.md
and SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md). Every input that the simulator relies on must
be explicit and hashed; anything missing or unverifiable is refused (fail closed) instead of being guessed.

Prices are handled as integer multiples of the broker tick size so that "one tick" comparisons are exact.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field

from katarina.research.dev_dataset import DEV_CUTOFF_UTC

TIMEFRAME_MS = {"M5": 5 * 60_000, "M15": 15 * 60_000, "H1": 60 * 60_000}
DEV_CUTOFF_MS = int(DEV_CUTOFF_UTC.timestamp() * 1000)
SEQUENCE_EVIDENCE = ("VERIFIED_SOURCE_ORDER", "UNVERIFIED")
SPEC_VERSION = "D10-K1..K27/tick-replay-v1"


class ReplayInputError(ValueError):
    """Input the simulator must refuse; ``reason`` is a stable reason code."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def canonical_sha256(value) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _require(condition: bool, reason: str, detail: str = ""):
    if not condition:
        raise ReplayInputError(reason, detail)


def _sha(value: str, reason: str):
    _require(isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
             reason, "64 lowercase hex characters required")


@dataclass(frozen=True)
class Tick:
    """One broker quote. ``bid``/``ask`` are integer tick counts (price / tick_size)."""
    seq: int
    time_ms: int
    bid: int
    ask: int


@dataclass(frozen=True)
class SymbolContract:
    symbol: str
    digits: int
    point: float
    tick_size: float
    stops_level_points: int
    freeze_level_points: int
    contract_size: float
    evidence_sha256: str

    def __post_init__(self):
        _require(bool(self.symbol), "SYMBOL_CONTRACT_INVALID", "symbol")
        _require(isinstance(self.digits, int) and 0 <= self.digits <= 8, "SYMBOL_CONTRACT_INVALID", "digits")
        for name in ("point", "tick_size", "contract_size"):
            value = getattr(self, name)
            _require(isinstance(value, (int, float)) and math.isfinite(value) and value > 0,
                     "SYMBOL_CONTRACT_INVALID", name)
        ratio = self.tick_size / self.point
        _require(abs(ratio - round(ratio)) < 1e-9 and round(ratio) >= 1, "SYMBOL_CONTRACT_INVALID",
                 "tick_size must be a whole number of points")
        for name in ("stops_level_points", "freeze_level_points"):
            value = getattr(self, name)
            _require(isinstance(value, int) and value >= 0, "SYMBOL_CONTRACT_INVALID", name)
        _sha(self.evidence_sha256, "SYMBOL_CONTRACT_EVIDENCE_MISSING")

    def to_ticks(self, price: float) -> int:
        """Exact grid conversion; a price off the broker tick grid is refused, never rounded silently."""
        value = price / self.tick_size
        ticks = round(value)
        _require(math.isfinite(price) and abs(value - ticks) < 1e-6, "PRICE_OFF_TICK_GRID", repr(price))
        return ticks

    def price(self, ticks: int) -> float:
        return round(ticks * self.tick_size, self.digits)

    @property
    def stops_level_ticks(self) -> int:
        return math.ceil(self.stops_level_points * self.point / self.tick_size - 1e-9)


@dataclass(frozen=True)
class SessionEvidence:
    """Official broker sessions as UTC ``[start_ms, end_ms)`` intervals (SymbolInfoSessionQuote/Trade).

    The intervals must already be converted from server time with verified clock evidence; tick gaps are
    never accepted as a session schedule.
    """
    quote: tuple
    trade: tuple
    source: str
    evidence_sha256: str

    def __post_init__(self):
        _require(bool(self.source), "SESSION_EVIDENCE_MISSING", "source")
        _sha(self.evidence_sha256, "SESSION_EVIDENCE_MISSING")
        for name in ("quote", "trade"):
            spans = getattr(self, name)
            _require(isinstance(spans, tuple) and len(spans) > 0, "SESSION_EVIDENCE_MISSING", name)
            previous_end = None
            for span in spans:
                _require(isinstance(span, tuple) and len(span) == 2 and all(isinstance(x, int) for x in span)
                         and span[0] < span[1], "SESSION_EVIDENCE_INVALID", f"{name} {span!r}")
                _require(previous_end is None or span[0] >= previous_end, "SESSION_EVIDENCE_INVALID",
                         f"{name} intervals must be sorted and disjoint")
                previous_end = span[1]

    @staticmethod
    def _find(spans, time_ms):
        for start, end in spans:
            if start <= time_ms < end:
                return start, end
            if start > time_ms:
                return None
        return None

    def quote_span(self, time_ms: int):
        return self._find(self.quote, time_ms)

    def trade_span(self, time_ms: int):
        return self._find(self.trade, time_ms)

    def quote_overlap_ms(self, start_ms: int, end_ms: int) -> int:
        """Milliseconds of ``[start_ms, end_ms)`` during which the broker publishes quotes."""
        total = 0
        for start, end in self.quote:
            if start >= end_ms:
                break
            total += max(0, min(end, end_ms) - max(start, start_ms))
        return total


@dataclass(frozen=True)
class CostSpec:
    """Broker cost inputs registered before testing; recorded per trade, never tuned on results."""
    currency: str
    commission_per_lot_round_trip: float
    swap_long_per_lot_night: float
    swap_short_per_lot_night: float
    rollover_utc_minute: int
    triple_swap_weekday: int
    evidence_sha256: str

    def __post_init__(self):
        _require(bool(self.currency), "COST_SPEC_INVALID", "currency")
        _require(math.isfinite(self.commission_per_lot_round_trip) and self.commission_per_lot_round_trip >= 0,
                 "COST_SPEC_INVALID", "commission")
        for name in ("swap_long_per_lot_night", "swap_short_per_lot_night"):
            _require(math.isfinite(getattr(self, name)), "COST_SPEC_INVALID", name)
        _require(isinstance(self.rollover_utc_minute, int) and 0 <= self.rollover_utc_minute < 1440,
                 "COST_SPEC_INVALID", "rollover_utc_minute")
        _require(isinstance(self.triple_swap_weekday, int) and 0 <= self.triple_swap_weekday <= 6,
                 "COST_SPEC_INVALID", "triple_swap_weekday")
        _sha(self.evidence_sha256, "COST_EVIDENCE_MISSING")

    def swap_nights(self, open_ms: int, close_ms: int) -> int:
        """Rollover instants crossed while open; the triple-swap weekday counts three nights."""
        day = 86_400_000
        first = (open_ms // day) * day + self.rollover_utc_minute * 60_000
        if first <= open_ms:
            first += day
        nights, t = 0, first
        while t <= close_ms:
            weekday = ((t // day) + 3) % 7  # 1970-01-01 was a Thursday (weekday 3)
            nights += 3 if weekday == self.triple_swap_weekday else 1
            t += day
        return nights


@dataclass(frozen=True)
class DatasetEvidence:
    """Provenance of one development tick file; every field is mandatory."""
    symbol: str
    server: str
    tick_file_sha256: str
    clock_evidence_sha256: str
    sequence_evidence: str
    max_quote_gap_ms: int

    def __post_init__(self):
        _require(bool(self.symbol) and bool(self.server), "DATASET_EVIDENCE_MISSING", "symbol/server")
        _sha(self.tick_file_sha256, "DATASET_EVIDENCE_MISSING")
        _sha(self.clock_evidence_sha256, "CLOCK_EVIDENCE_MISSING")
        _require(self.sequence_evidence in SEQUENCE_EVIDENCE, "SEQUENCE_EVIDENCE_INVALID", self.sequence_evidence)
        _require(isinstance(self.max_quote_gap_ms, int) and self.max_quote_gap_ms > 0,
                 "DATASET_EVIDENCE_MISSING", "max_quote_gap_ms")


@dataclass(frozen=True)
class CandidateSpec:
    """One of the six independent hypotheses; any change is a new hypothesis (new ``spec_sha256``)."""
    candidate_id: str
    side: str
    setup: str
    entry_tf: str
    structure_tf: str
    target_tf: str
    time_exit_bars: int
    time_exit_minutes: int
    preclose_minutes: int
    pivot_left: int = 2
    pivot_right: int = 2
    pivot_tie_rule: str = "LEFT_STRICT_RIGHT_NONSTRICT"
    swing_ttl_bars: dict = field(default_factory=lambda: {"M15": 96, "H1": 72})
    zone_ttl_h1: int = 48
    zone_origin_lookback_h1: int = 12
    retest_max_m5: int = 6
    atr_period: int = 14
    atr_buffer_fraction: float = 0.10
    min_penetration_ticks: int = 1
    spec_version: str = SPEC_VERSION

    def __post_init__(self):
        _require(self.side in ("BUY", "SELL"), "CANDIDATE_SPEC_INVALID", "side")
        _require(self.setup in ("SWEEP_RECLAIM", "ZONE_PULLBACK", "BREAKOUT_RETEST"), "CANDIDATE_SPEC_INVALID",
                 "setup")
        for tf in (self.entry_tf, self.structure_tf, self.target_tf):
            _require(tf in TIMEFRAME_MS, "CANDIDATE_SPEC_INVALID", tf)
        for name in ("time_exit_bars", "time_exit_minutes", "preclose_minutes"):
            _require(isinstance(getattr(self, name), int) and getattr(self, name) > 0, "CANDIDATE_SPEC_INVALID",
                     name)

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def spec_sha256(self) -> str:
        return canonical_sha256(self.as_dict())

    @property
    def direction(self) -> int:
        return 1 if self.side == "BUY" else -1


def _candidate(cid, side, setup, entry_tf, structure_tf, target_tf, bars, minutes, preclose):
    return CandidateSpec(cid, side, setup, entry_tf, structure_tf, target_tf, bars, minutes, preclose)


# Owner-approved table (D10-K11/K14 time exits, D10-K19..K25 rules). Do not edit after seeing results.
SIX_CANDIDATES = {
    "B1": _candidate("B1", "BUY", "SWEEP_RECLAIM", "M5", "M15", "M15", 12, 90, 15),
    "S1": _candidate("S1", "SELL", "SWEEP_RECLAIM", "M5", "M15", "M15", 12, 90, 15),
    "B2": _candidate("B2", "BUY", "ZONE_PULLBACK", "M15", "H1", "H1", 12, 240, 30),
    "S2": _candidate("S2", "SELL", "ZONE_PULLBACK", "M15", "H1", "H1", 12, 240, 30),
    "B3": _candidate("B3", "BUY", "BREAKOUT_RETEST", "M5", "H1", "H1", 24, 180, 20),
    "S3": _candidate("S3", "SELL", "BREAKOUT_RETEST", "M5", "H1", "H1", 24, 180, 20),
}


def validate_ticks(ticks, contract: SymbolContract):
    """Refuse incomplete or unverifiable tick data before any calculation (D10-K23)."""
    _require(len(ticks) > 0, "TICK_DATA_EMPTY")
    previous = None
    for index, tick in enumerate(ticks):
        _require(isinstance(tick, Tick), "TICK_INVALID", f"index {index}")
        _require(tick.time_ms < DEV_CUTOFF_MS, "HOLDOUT_DATA_FORBIDDEN",
                 f"tick at index {index} is not before the 2026-10-13 development cutoff")
        _require(tick.bid > 0 and tick.ask > tick.bid, "QUOTE_INVALID", f"index {index} bid/ask")
        if previous is not None:
            _require(tick.seq > previous.seq, "TICK_SEQUENCE_INVALID", f"index {index} seq not increasing")
            _require(tick.time_ms >= previous.time_ms, "TICK_OUT_OF_ORDER", f"index {index}")
        previous = tick
    return ticks
