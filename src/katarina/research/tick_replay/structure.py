"""Causal market structure shared by the six candidates (no candidate can influence it).

* ATR14 Wilder per timeframe from valid closed candles only.
* Confirmed swings: pivot 2 left + 2 right, known only after the second right candle closes; TTL in valid
  closed candles of the origin timeframe (M15 96, H1 72; D10-K21); invalidated by a closed candle beyond the
  level by one tick; any data gap after confirmation expires the swing (fail closed).
* H1 break of structure (BOS): closed H1 beyond a valid H1 swing by >= 1 tick, with the swing confirmed before
  the BOS candle started. The broken swing becomes BROKEN (no longer a target); the newest broken swing is the
  BOS source for B3/S3 retests and B2/S2 zone creation.
* H1 demand/supply zones (D10-K22/K24/K25/K9/K10) and B3/S3 breakout-retest setups.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .contract import TIMEFRAME_MS


@dataclass
class Swing:
    swing_id: str
    tf: str
    kind: str          # HIGH | LOW
    level: int
    bar_start_ms: int
    confirmed_at_ms: int
    status: str = "VALID"   # VALID | INVALIDATED | BROKEN | EXPIRED_TTL | EXPIRED_GAP
    age_bars: int = 0
    status_at_ms: int | None = None

    def usable(self, at_ms: int, ttl) -> bool:
        return (self.status == "VALID" and self.confirmed_at_ms <= at_ms
                and (ttl is None or self.age_bars <= ttl))


@dataclass
class Zone:
    zone_id: str
    kind: str          # DEMAND | SUPPLY
    low: int
    high: int
    confirmed_at_ms: int
    origin_bar_start_ms: int
    bos_swing_id: str
    status: str = "FRESH"   # FRESH | FIRST_VISIT_PENDING_M15 | BREACH_LOCKED | CONSUMED | INVALID | EXPIRED | BLOCKED
    age_h1: int = 0
    touch_m15_start_ms: int | None = None
    touch_event_id: str | None = None
    reason: str | None = None

    @property
    def proximal(self) -> int:
        return self.high if self.kind == "DEMAND" else self.low

    @property
    def distal(self) -> int:
        return self.low if self.kind == "DEMAND" else self.high


@dataclass
class Breakout:
    setup_id: str
    direction: int     # +1 breakout up (B3), -1 breakdown (S3)
    level: int
    armed_from_ms: int
    swing_id: str
    m5_seen: int = 0
    status: str = "ARMED"   # ARMED | USED | TIMEOUT | INVALIDATED | SUPERSEDED | BLOCKED


class Atr:
    """Wilder ATR: first value = mean of the first ``period`` true ranges, then (prev*(n-1)+TR)/n."""

    def __init__(self, period: int):
        self.period, self.prev_close, self.trs, self.value = period, None, [], None

    def update(self, bar):
        if self.prev_close is None:
            self.prev_close = bar.close
            return
        tr = max(bar.high - bar.low, abs(bar.high - self.prev_close), abs(bar.low - self.prev_close))
        self.prev_close = bar.close
        if self.value is None:
            self.trs.append(tr)
            if len(self.trs) == self.period:
                self.value = sum(self.trs) / self.period
        else:
            self.value = (self.value * (self.period - 1) + tr) / self.period

    def reset(self):
        self.prev_close, self.trs, self.value = None, [], None


@dataclass
class TimeframeState:
    tf: str
    ttl: int | None
    atr: Atr
    history: list = field(default_factory=list)     # valid closed bars, oldest first
    swings: list = field(default_factory=list)
    last_bar_end_ms: int | None = None

    def contiguous_tail(self, count: int, contiguous):
        """The last ``count`` bars if all are valid and consecutive (only scheduled closures between)."""
        if len(self.history) < count:
            return None
        tail = self.history[-count:]
        if any(not b.valid for b in tail) or any(not contiguous(a, b) for a, b in zip(tail, tail[1:])):
            return None
        return tail


def buffer_ticks(spread_ticks: int, atr_value, fraction: float) -> int | None:
    """``ceil_to_tick(max(tick_size, spread_at_decision, 0.10 x ATR14))`` in ticks; None during ATR warm-up."""
    if atr_value is None:
        return None
    return max(1, spread_ticks, math.ceil(fraction * atr_value - 1e-9))


class MarketStructure:
    def __init__(self, spec_defaults, *, emit, sessions):
        self.p = spec_defaults
        self.emit = emit
        self.sessions = sessions
        ttl = spec_defaults.swing_ttl_bars
        self.tf = {tf: TimeframeState(tf, ttl.get(tf), Atr(spec_defaults.atr_period)) for tf in TIMEFRAME_MS}
        self.zones: list[Zone] = []
        self.breakouts: list[Breakout] = []
        self.bos_events: list[dict] = []

    # ---------------------------------------------------------------- candle close
    def on_bar(self, bar):
        state = self.tf[bar.tf]
        if not bar.valid:
            state.atr.reset()           # TR across a gap would mix discontinuous prices
            for swing in state.swings:
                if swing.status == "VALID":
                    swing.status, swing.status_at_ms = "EXPIRED_GAP", bar.end_ms
            state.history.append(bar)   # kept so contiguity checks see the hole
            del state.history[:-600]
            if bar.tf == "H1":
                self._zones_on_invalid_h1(bar)
            return
        state.atr.update(bar)
        for swing in state.swings:
            if swing.status != "VALID":
                continue
            swing.age_bars += 1
            if state.ttl is not None and swing.age_bars > state.ttl:
                swing.status, swing.status_at_ms = "EXPIRED_TTL", bar.end_ms
        broken = []
        for swing in state.swings:
            if swing.status != "VALID" or swing.confirmed_at_ms > bar.start_ms:
                continue
            if swing.kind == "HIGH" and bar.close >= swing.level + 1:
                broken.append(swing)
            elif swing.kind == "LOW" and bar.close <= swing.level - 1:
                broken.append(swing)
        for swing in broken:
            swing.status, swing.status_at_ms = ("BROKEN" if bar.tf == "H1" else "INVALIDATED"), bar.end_ms
        state.history.append(bar)
        del state.history[:-600]
        self._confirm_pivot(state)
        if bar.tf == "H1":
            self._zones_on_h1(bar)
            for kind in ("HIGH", "LOW"):
                source = [s for s in broken if s.kind == kind]
                if source:
                    newest = max(source, key=lambda s: (s.confirmed_at_ms, s.swing_id))
                    self._on_bos(bar, newest)
            self._breakouts_on_h1(bar)

    def contiguous(self, a, b) -> bool:
        """Back-to-back candles, or only scheduled (non-quote) time between them."""
        if b.start_ms == a.end_ms:
            return True
        return self.sessions is not None and self.sessions.quote_overlap_ms(a.end_ms, b.start_ms) == 0

    def _confirm_pivot(self, state):
        left, right = self.p.pivot_left, self.p.pivot_right
        window = state.contiguous_tail(left + right + 1, self.contiguous)
        if window is None:
            return
        center = window[left]
        lows, highs = [b.low for b in window], [b.high for b in window]
        # LEFT_STRICT_RIGHT_NONSTRICT: among equal extremes the earliest candle is the pivot (deterministic).
        if all(center.high > highs[i] for i in range(left)) and all(center.high >= highs[i]
                                                                   for i in range(left + 1, len(window))):
            self._add_swing(state, "HIGH", center.high, center, window[-1].end_ms)
        if all(center.low < lows[i] for i in range(left)) and all(center.low <= lows[i]
                                                                 for i in range(left + 1, len(window))):
            self._add_swing(state, "LOW", center.low, center, window[-1].end_ms)

    def _add_swing(self, state, kind, level, center, confirmed_at):
        swing = Swing(f"{state.tf}:{kind}:{center.start_ms}", state.tf, kind, level, center.start_ms, confirmed_at)
        state.swings.append(swing)
        del state.swings[:-400]
        self.emit("SWING_CONFIRMED", at_ms=confirmed_at, swing_id=swing.swing_id, level=level, tf=state.tf)

    # ---------------------------------------------------------------- selection helpers
    def latest_swing(self, tf, kind, *, known_before_ms, at_ms):
        state = self.tf[tf]
        usable = [s for s in state.swings if s.kind == kind and s.confirmed_at_ms <= known_before_ms
                  and s.usable(at_ms, state.ttl)]
        return max(usable, key=lambda s: (s.confirmed_at_ms, s.swing_id)) if usable else None

    def last_two_pivots(self, tf, kind, at_ms):
        known = [s for s in self.tf[tf].swings if s.kind == kind and s.confirmed_at_ms <= at_ms]
        known.sort(key=lambda s: (s.confirmed_at_ms, s.swing_id))
        return known[-2:] if len(known) >= 2 else None

    def trend(self, at_ms) -> int:
        """+1 HH+HL, -1 LH+LL on the last two confirmed H1 pivots of each kind, 0 otherwise."""
        highs, lows = self.last_two_pivots("H1", "HIGH", at_ms), self.last_two_pivots("H1", "LOW", at_ms)
        if not highs or not lows:
            return 0
        if highs[1].level > highs[0].level and lows[1].level > lows[0].level:
            return 1
        if highs[1].level < highs[0].level and lows[1].level < lows[0].level:
            return -1
        return 0

    def targets(self, tf, direction, fill, at_ms, *, include_zones):
        """Valid structural targets strictly on the profit side of ``fill`` (no minimum RR)."""
        state = self.tf[tf]
        kind = "HIGH" if direction > 0 else "LOW"
        found = []
        for s in state.swings:
            if s.kind == kind and s.usable(at_ms, state.ttl) and (s.level - fill) * direction > 0:
                found.append((abs(s.level - fill), -s.confirmed_at_ms, s.swing_id, s.level))
        if include_zones:
            zone_kind = "SUPPLY" if direction > 0 else "DEMAND"
            for z in self.zones:
                if z.kind == zone_kind and z.status == "FRESH" and z.confirmed_at_ms <= at_ms \
                        and (z.proximal - fill) * direction > 0:
                    found.append((abs(z.proximal - fill), -z.confirmed_at_ms, z.zone_id, z.proximal))
        if not found:
            return None
        found.sort()
        return {"level": found[0][3], "target_id": found[0][2]}

    # ---------------------------------------------------------------- BOS, zones, breakouts
    def _on_bos(self, bar, swing):
        direction = 1 if swing.kind == "HIGH" else -1
        event = {"bos_bar_start_ms": bar.start_ms, "closed_at_ms": bar.end_ms, "direction": direction,
                 "swing_id": swing.swing_id, "level": swing.level}
        self.bos_events.append(event)
        self.emit("H1_BOS", at_ms=bar.end_ms, swing_id=swing.swing_id, level=swing.level, direction=direction)
        for b in self.breakouts:
            if b.status == "ARMED" and b.direction == direction:
                b.status = "SUPERSEDED"
                self.emit("BREAKOUT_SETUP_CLOSED", at_ms=bar.end_ms, setup_id=b.setup_id, reason="SUPERSEDED")
        self.breakouts.append(Breakout(f"BRK:{direction}:{bar.start_ms}", direction, swing.level, bar.end_ms,
                                       swing.swing_id))
        del self.breakouts[:-50]
        self._create_zone(bar, swing, direction)

    def _create_zone(self, bos_bar, swing, direction):
        lookback = self.p.zone_origin_lookback_h1
        state = self.tf["H1"]
        prior = state.history[:-1]       # candles strictly before the BOS candle
        tail = prior[-lookback:]
        kind = "DEMAND" if direction > 0 else "SUPPLY"
        contiguous = (len(tail) == lookback and all(b.valid for b in tail)
                      and all(self.contiguous(a, b) for a, b in zip(tail, tail[1:]))
                      and self.contiguous(tail[-1], bos_bar))
        if not contiguous:
            self.emit("ZONE_NOT_CREATED", at_ms=bos_bar.end_ms, kind=kind, reason="WAIT:ZONE_ORIGIN_DATA_GAP")
            return
        wanted = (lambda b: b.bearish) if direction > 0 else (lambda b: b.bullish)
        origin = next((b for b in reversed(tail) if wanted(b)), None)
        if origin is None or origin.open_ambiguous or origin.close_ambiguous:
            reason = "WAIT:NO_VALID_ZONE_ORIGIN" if origin is None else "BLOCKED_INTRABAR_ORDER"
            self.emit("ZONE_NOT_CREATED", at_ms=bos_bar.end_ms, kind=kind, reason=reason)
            return
        zone = Zone(f"{kind}:{bos_bar.start_ms}", kind, origin.low, origin.high, bos_bar.end_ms, origin.start_ms,
                    swing.swing_id)
        self.zones.append(zone)
        del self.zones[:-200]
        self.emit("ZONE_CREATED", at_ms=bos_bar.end_ms, zone_id=zone.zone_id, low=zone.low, high=zone.high)

    def _zones_on_h1(self, bar):
        for z in self.zones:
            if z.status in ("FRESH", "FIRST_VISIT_PENDING_M15", "BREACH_LOCKED") and z.confirmed_at_ms < bar.end_ms:
                outside = bar.close < z.low if z.kind == "DEMAND" else bar.close > z.high
                if z.status == "BREACH_LOCKED":
                    z.status = "INVALID" if outside else "CONSUMED"
                    z.reason = "H1_CLOSE_OUTSIDE_DISTAL" if outside else "H1_CLOSE_BACK_INSIDE_AFTER_BREACH"
                    self.emit("ZONE_STATE", at_ms=bar.end_ms, zone_id=z.zone_id, status=z.status, reason=z.reason)
                    continue
                if outside:
                    z.status, z.reason = "INVALID", "H1_CLOSE_OUTSIDE_DISTAL"
                    self.emit("ZONE_STATE", at_ms=bar.end_ms, zone_id=z.zone_id, status=z.status, reason=z.reason)
                    continue
                if z.status == "FRESH":
                    z.age_h1 += 1
                    if z.age_h1 > self.p.zone_ttl_h1:
                        z.status, z.reason = "EXPIRED", "ZONE_TTL_48_H1"
                        self.emit("ZONE_STATE", at_ms=bar.end_ms, zone_id=z.zone_id, status=z.status,
                                  reason=z.reason)

    def _zones_on_invalid_h1(self, bar):
        for z in self.zones:
            if z.status == "FRESH":
                z.status, z.reason = "EXPIRED", "H1_DATA_GAP_FAIL_CLOSED"
                self.emit("ZONE_STATE", at_ms=bar.end_ms, zone_id=z.zone_id, status=z.status, reason=z.reason)

    def _breakouts_on_h1(self, bar):
        for b in self.breakouts:
            if b.status != "ARMED" or b.armed_from_ms >= bar.end_ms:
                continue
            failed = bar.close <= b.level - 1 if b.direction > 0 else bar.close >= b.level + 1
            if failed:
                b.status = "INVALIDATED"
                self.emit("BREAKOUT_SETUP_CLOSED", at_ms=bar.end_ms, setup_id=b.setup_id,
                          reason="WAIT:BREAKOUT_INVALIDATED")

    # ---------------------------------------------------------------- BID touches (intrabar)
    def zone_touch_candidates(self, bid, time_ms):
        """FRESH zones touched by this BID tick (proximal crossed); pure, no state change."""
        touched = []
        for z in self.zones:
            if z.status == "FRESH" and z.confirmed_at_ms <= time_ms:
                if (z.kind == "DEMAND" and bid <= z.high) or (z.kind == "SUPPLY" and bid >= z.low):
                    touched.append(z)
        return touched

    def zone_breach_candidates(self, bid, time_ms, buffer):
        if buffer is None:
            return []
        hits = []
        for z in self.zones:
            if z.status in ("FRESH", "FIRST_VISIT_PENDING_M15") and z.confirmed_at_ms <= time_ms:
                if (z.kind == "DEMAND" and bid < z.low - buffer) or (z.kind == "SUPPLY" and bid > z.high + buffer):
                    hits.append(z)
        return hits

    def apply_zone_tick(self, tick, m15_start_ms, buffer, *, event_id):
        """First touch with the D10-K24/K25 priority rule, then distal+buffer breach locks."""
        for kind in ("DEMAND", "SUPPLY"):
            touched = [z for z in self.zone_touch_candidates(tick.bid, tick.time_ms) if z.kind == kind]
            if touched:
                touched.sort(key=lambda z: (abs(tick.bid - z.proximal), -z.confirmed_at_ms, z.zone_id))
                selected = touched[0]
                selected.status, selected.touch_m15_start_ms, selected.touch_event_id = (
                    "FIRST_VISIT_PENDING_M15", m15_start_ms, event_id)
                for other in touched[1:]:
                    other.status, other.reason = "CONSUMED", "CONSUMED_OVERLAP_NOT_SELECTED"
                self.emit("ZONE_FIRST_TOUCH", at_ms=tick.time_ms, source_tick_seq=tick.seq, bid=tick.bid,
                          touch_event_id=event_id, selected_zone_id=selected.zone_id,
                          all_touched_zone_ids=[z.zone_id for z in touched],
                          consumed_zone_ids=[z.zone_id for z in touched[1:]])
        for z in self.zone_breach_candidates(tick.bid, tick.time_ms, buffer):
            z.status, z.reason = "BREACH_LOCKED", "INTRABAR_DISTAL_PLUS_BUFFER_BREACH"
            self.emit("ZONE_STATE", at_ms=tick.time_ms, source_tick_seq=tick.seq, zone_id=z.zone_id,
                      status=z.status, reason=z.reason, bid=tick.bid)

    def block_zones(self, zones, time_ms, reason):
        for z in zones:
            if z.status in ("FRESH", "FIRST_VISIT_PENDING_M15"):
                z.status, z.reason = "BLOCKED", reason
                self.emit("ZONE_STATE", at_ms=time_ms, zone_id=z.zone_id, status=z.status, reason=reason)
