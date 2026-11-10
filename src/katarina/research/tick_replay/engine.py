"""Chronological tick-replay simulator for the six XAUUSD candidates (research only; never sends orders).

Event order for each tick, following D10-K23/K24 and the contract in
docs/research/SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md:

1. Quote-gap check against official quote-session time (a gap invalidates the candles it touches).
2. Candles whose ``end_ms <= tick.time`` close (H1, then M15, then M5 at the same instant). Market structure
   is updated first, then each candidate evaluates its closed-candle rule. Signals and bar-count exits created
   here are *intents* that may only fill on a later tick than the one that revealed the close.
3. The tick itself: open positions are checked for SL/TP first (an earlier SL/TP wins), then UTC-deadline and
   pre-close exits, then pending exit/entry intents, then BID first-touch/breach of H1 zones.
4. The tick is added to the candles it belongs to (half-open intervals).

Fills happen only on real, executable quotes inside the official trade session: BUY enters at ASK and exits
at BID, SELL enters at BID and exits at ASK. When several ticks share a millisecond, the source order is
unverified and the outcome depends on the order, the affected candidate/zone is ``BLOCKED_INTRABAR_ORDER``.
There is no OHLC fallback and no invented price. Each candidate is an isolated experiment with at most one
position. The ledger is deterministic: same inputs and code give the same ``ledger_sha256``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .bars import BarBuilder
from .contract import (SIX_CANDIDATES, TIMEFRAME_MS, CandidateSpec, CostSpec, DatasetEvidence, ReplayInputError,
                       SessionEvidence, SymbolContract, canonical_sha256, validate_ticks)
from .structure import MarketStructure, buffer_ticks

TF_ORDER = {"H1": 0, "M15": 1, "M5": 2}
ENGINE_VERSION = "tick-replay-engine-v1"


@dataclass
class Intent:
    kind: str                # ENTRY | EXIT
    created_seq: int
    decided_at_ms: int
    reason: str
    stop: int | None = None
    source_id: str | None = None
    signal_bar: str | None = None
    gap_since: bool = False
    pending_reported: bool = False


@dataclass
class Position:
    position_id: str
    side: str
    entry_ms: int
    entry_price: int
    entry_spread: int
    stop: int
    target: int
    target_id: str
    source_id: str
    utc_deadline_ms: int
    preclose_deadline_ms: int
    bars_after_fill: int = 0


@dataclass
class CandidateState:
    spec: CandidateSpec
    position: Position | None = None
    entry_intent: Intent | None = None
    exit_intent: Intent | None = None
    used_sources: set = field(default_factory=set)
    trades: list = field(default_factory=list)
    positions_opened: int = 0


class TickReplay:
    def __init__(self, ticks, *, contract: SymbolContract, dataset: DatasetEvidence, costs: CostSpec,
                 sessions: SessionEvidence | None, candidates=None):
        if dataset.symbol != contract.symbol:
            raise ReplayInputError("SYMBOL_MISMATCH", f"{dataset.symbol} != {contract.symbol}")
        self.ticks = validate_ticks(list(ticks), contract)
        self.contract, self.dataset, self.costs, self.sessions = contract, dataset, costs, sessions
        specs = list(candidates if candidates is not None else SIX_CANDIDATES.values())
        if len({s.candidate_id for s in specs}) != len(specs):
            raise ReplayInputError("CANDIDATE_SPEC_INVALID", "duplicate candidate_id")
        self.candidates = {s.candidate_id: CandidateState(s) for s in specs}
        self.verified = dataset.sequence_evidence == "VERIFIED_SOURCE_ORDER"
        self.events: list[dict] = []
        self.input_hashes = {
            "symbol_contract": canonical_sha256(contract.__dict__),
            "dataset": canonical_sha256(dataset.__dict__),
            "costs": canonical_sha256(costs.__dict__),
            "sessions": canonical_sha256(sessions.__dict__) if sessions is not None else None,
            "engine_version": ENGINE_VERSION,
        }
        self.structure = MarketStructure(specs[0] if specs else SIX_CANDIDATES["B1"], emit=self._market_event,
                                         sessions=sessions)
        self.builders = {tf: BarBuilder(tf, sequence_verified=self.verified) for tf in TIMEFRAME_MS}
        self._ran = False

    # ---------------------------------------------------------------- events
    def _event(self, event_type, *, candidate=None, **fields):
        record = {"n": len(self.events), "event_type": event_type,
                  "candidate_id": candidate.spec.candidate_id if candidate else "MARKET"}
        if candidate is not None:
            record["hypothesis_spec_sha256"] = candidate.spec.spec_sha256
        record.update(fields)
        self.events.append(record)
        return record

    def _market_event(self, event_type, **fields):
        self._event(event_type, **fields)

    def _px(self, ticks):
        return self.contract.price(ticks) if ticks is not None else None

    # ---------------------------------------------------------------- main loop
    def run(self) -> dict:
        if self._ran:
            raise RuntimeError("TickReplay.run() may only be called once")
        self._ran = True
        ticks, index, previous = self.ticks, 0, None
        while index < len(ticks):
            end = index + 1
            while end < len(ticks) and ticks[end].time_ms == ticks[index].time_ms:
                end += 1
            group = ticks[index:end]
            gap = self._gap_check(previous, group[0])
            self._close_bars(group[0])
            ambiguous = (not self.verified and len(group) > 1
                         and len({(t.bid, t.ask) for t in group}) > 1)
            if ambiguous:
                self._ambiguous_group(group)
            else:
                for tick in group:
                    self._on_tick(tick)
            for tick in group:
                for builder in self.builders.values():
                    builder.add(tick)
            if gap:
                # the candle that now holds the post-gap tick is also touched if quote time is missing
                for builder in self.builders.values():
                    bar = builder.current
                    if self._quote_ms(max(previous.time_ms, bar.start_ms), group[0].time_ms) > 0:
                        builder.mark_gap("QUOTE_GAP_INSIDE_SESSION")
            previous = group[-1]
            index = end
        self._finish(previous)
        return self.result()

    def _quote_ms(self, start_ms, end_ms):
        """Quote-session milliseconds in [start, end); without session evidence all time counts (fail closed)."""
        if end_ms <= start_ms:
            return 0
        if self.sessions is None:
            return end_ms - start_ms
        return self.sessions.quote_overlap_ms(start_ms, end_ms)

    def _gap_check(self, previous, tick) -> bool:
        if previous is None:
            return False
        span = self._quote_ms(previous.time_ms, tick.time_ms)
        if span <= self.dataset.max_quote_gap_ms:
            return False
        self._event("DATA_GAP", at_ms=tick.time_ms, gap_from_ms=previous.time_ms, gap_to_ms=tick.time_ms,
                    quote_session_ms=span, reason_code="DATA_GAP_UNVERIFIED")
        for builder in self.builders.values():
            bar = builder.current
            if bar is not None and self._quote_ms(previous.time_ms, min(tick.time_ms, bar.end_ms)) > 0:
                builder.mark_gap("QUOTE_GAP_INSIDE_SESSION")
        for c in self.candidates.values():
            if c.entry_intent is not None:
                c.entry_intent.gap_since = True
        return True

    def _close_bars(self, tick):
        due = [b for b in (builder.close_due(tick.time_ms) for builder in self.builders.values()) if b]
        if not due:
            return
        due.sort(key=lambda b: (b.end_ms, TF_ORDER[b.tf]))
        for bar in due:
            self.structure.on_bar(bar)
        for bar in due:
            self._event("BAR_CLOSED", at_ms=bar.end_ms, bar=bar.ident(), valid=bar.valid,
                        invalid_reason=bar.invalid_reason, known_at_tick_seq=tick.seq)
            for c in self.candidates.values():
                self._on_candidate_bar(c, bar, tick)

    # ---------------------------------------------------------------- closed-candle rules
    def _on_candidate_bar(self, c, bar, boundary_tick):
        spec = c.spec
        if c.position is not None and bar.tf == spec.entry_tf and bar.valid and bar.start_ms >= c.position.entry_ms:
            c.position.bars_after_fill += 1
            if c.position.bars_after_fill >= spec.time_exit_bars and c.exit_intent is None:
                c.exit_intent = Intent("EXIT", boundary_tick.seq, bar.end_ms, "TIME_EXIT_BARS")
                self._event("EXIT_INTENT", candidate=c, position_id=c.position.position_id, at_ms=bar.end_ms,
                            intended_exit_reason="TIME_EXIT_BARS", bars=c.position.bars_after_fill)
        if spec.setup == "SWEEP_RECLAIM" and bar.tf == "M5":
            self._sweep(c, bar, boundary_tick)
        elif spec.setup == "ZONE_PULLBACK" and bar.tf == "M15":
            self._zone_confirm(c, bar, boundary_tick)
        elif spec.setup == "BREAKOUT_RETEST" and bar.tf == "M5":
            self._retest(c, bar, boundary_tick)

    def _signal(self, c, bar, boundary_tick, *, source_id, structure_stop, atr_tf, reason):
        spec = c.spec
        common = {"at_ms": bar.end_ms, "source_id": source_id, "source_bar_tf": bar.tf,
                  "bar_closed_at_ms": bar.end_ms, "signal_known_at_ms": bar.end_ms, "signal_bar": bar.ident()}
        if c.position is not None or c.entry_intent is not None:
            # one position per candidate; the structure is spent even though the signal is skipped
            c.used_sources.add(source_id)
            self._event("SIGNAL_SKIPPED", candidate=c, reason_code="WAIT:POSITION_ACTIVE", **common)
            return
        if source_id in c.used_sources:
            self._event("SIGNAL_SKIPPED", candidate=c, reason_code="WAIT:SOURCE_ALREADY_USED", **common)
            return
        c.used_sources.add(source_id)
        if bar.open_ambiguous or bar.close_ambiguous:
            self._event("SIGNAL_BLOCKED", candidate=c, reason_code="BLOCKED_INTRABAR_ORDER", **common)
            return
        buf = buffer_ticks(bar.last_spread, self.structure.tf[atr_tf].atr.value, spec.atr_buffer_fraction)
        if buf is None:
            self._event("SIGNAL_SKIPPED", candidate=c, reason_code="WAIT:ATR_WARMUP", **common)
            return
        stop = structure_stop - buf if spec.direction > 0 else structure_stop + buf
        c.entry_intent = Intent("ENTRY", boundary_tick.seq, bar.end_ms, reason, stop=stop, source_id=source_id,
                                signal_bar=bar.ident())
        self._event("ENTRY_INTENT", candidate=c, reason_code=reason, stop=self._px(stop), buffer_ticks=buf,
                    structure_extreme=self._px(structure_stop), **common)

    def _sweep(self, c, bar, boundary_tick):
        if not bar.valid:
            return
        d = c.spec.direction
        swing = self.structure.latest_swing("M15", "LOW" if d > 0 else "HIGH", known_before_ms=bar.start_ms,
                                            at_ms=bar.end_ms)
        if swing is None:
            return
        pen = c.spec.min_penetration_ticks
        if d > 0:
            pierced = bar.low <= swing.level - pen
            reclaimed = bar.close > swing.level and bar.bullish
            extreme = bar.low
        else:
            pierced = bar.high >= swing.level + pen
            reclaimed = bar.close < swing.level and bar.bearish
            extreme = bar.high
        if not pierced:
            return
        if not reclaimed and not (bar.open_ambiguous or bar.close_ambiguous):
            return
        self._signal(c, bar, boundary_tick, source_id=swing.swing_id, structure_stop=extreme, atr_tf="M5",
                     reason="SWEEP_RECLAIM")

    def _zone_confirm(self, c, bar, boundary_tick):
        d = c.spec.direction
        kind = "DEMAND" if d > 0 else "SUPPLY"
        pending = [z for z in self.structure.zones if z.kind == kind and z.status == "FIRST_VISIT_PENDING_M15"
                   and z.touch_m15_start_ms == bar.start_ms]
        for zone in sorted(pending, key=lambda z: z.touch_event_id):
            zone.status = "CONSUMED"
            if not bar.valid:
                zone.reason = "BLOCKED_DATA_GAP"
            elif d > 0 and not (bar.bullish and bar.close > zone.high):
                zone.reason = "FIRST_VISIT_NOT_CONFIRMED"
            elif d < 0 and not (bar.bearish and bar.close < zone.low):
                zone.reason = "FIRST_VISIT_NOT_CONFIRMED"
            elif self.structure.trend(bar.end_ms) != d:
                zone.reason = "WAIT:H1_TREND_NOT_ALIGNED"
            else:
                zone.reason = "FIRST_VISIT_CONFIRMED"
            ambiguous = bar.open_ambiguous or bar.close_ambiguous
            if ambiguous and zone.reason != "BLOCKED_DATA_GAP":
                zone.reason = "BLOCKED_INTRABAR_ORDER"
            self._event("ZONE_STATE", at_ms=bar.end_ms, zone_id=zone.zone_id, status=zone.status,
                        reason=zone.reason, candidate_scope=c.spec.candidate_id)
            if zone.reason in ("FIRST_VISIT_CONFIRMED", "BLOCKED_INTRABAR_ORDER"):
                self._signal(c, bar, boundary_tick, source_id=zone.zone_id, structure_stop=zone.distal,
                             atr_tf="M15", reason="ZONE_FIRST_VISIT")

    def _retest(self, c, bar, boundary_tick):
        d = c.spec.direction
        for b in self.structure.breakouts:
            if b.status != "ARMED" or b.direction != d or bar.start_ms < b.armed_from_ms:
                continue
            if not bar.valid:
                b.status = "BLOCKED"
                self._event("BREAKOUT_SETUP_CLOSED", at_ms=bar.end_ms, setup_id=b.setup_id,
                            reason="BLOCKED_DATA_GAP")
                continue
            b.m5_seen += 1
            if d > 0:
                touched, held = bar.low <= b.level, bar.close > b.level and bar.bullish
                extreme = bar.low
            else:
                touched, held = bar.high >= b.level, bar.close < b.level and bar.bearish
                extreme = bar.high
            if touched and (held or bar.open_ambiguous or bar.close_ambiguous):
                b.status = "USED"
                self._signal(c, bar, boundary_tick, source_id=b.setup_id, structure_stop=extreme, atr_tf="M5",
                             reason="BREAKOUT_RETEST")
            elif b.m5_seen >= c.spec.retest_max_m5:
                b.status = "TIMEOUT"
                self._event("BREAKOUT_SETUP_CLOSED", at_ms=bar.end_ms, setup_id=b.setup_id,
                            reason="WAIT:RETEST_TIMEOUT")

    # ---------------------------------------------------------------- per tick
    def _in_trade(self, time_ms):
        return self.sessions.trade_span(time_ms) if self.sessions is not None else None

    def _on_tick(self, tick):
        for c in self.candidates.values():
            self._manage_position(c, tick)
            self._try_entry(c, tick)
        self._zones(tick)

    def _exit_price(self, c, tick):
        return tick.bid if c.spec.direction > 0 else tick.ask

    def _manage_position(self, c, tick):
        pos = c.position
        if pos is None:
            return
        if c.exit_intent is None:
            for deadline, reason in ((pos.utc_deadline_ms, "TIME_EXIT_UTC"),
                                     (pos.preclose_deadline_ms, "TIME_EXIT_PRECLOSE")):
                if tick.time_ms >= deadline:
                    # time exits are known from the clock, so the first tick at/after the deadline may fill
                    c.exit_intent = Intent("EXIT", tick.seq - 1, deadline, reason)
                    self._event("EXIT_INTENT", candidate=c, position_id=pos.position_id, at_ms=tick.time_ms,
                                intended_exit_reason=reason, deadline_ms=deadline)
                    break
        span = self._in_trade(tick.time_ms)
        if span is None:
            if c.exit_intent is not None and not c.exit_intent.pending_reported:
                c.exit_intent.pending_reported = True
                self._event("EXIT_PENDING_NO_QUOTE", candidate=c, position_id=pos.position_id, at_ms=tick.time_ms,
                            source_tick_seq=tick.seq, reason_code="TRADE_SESSION_CLOSED")
            return
        price = self._exit_price(c, tick)
        d = c.spec.direction
        if (price - pos.stop) * d <= 0:
            return self._close(c, tick, "STOP_LOSS")
        if (price - pos.target) * d >= 0:
            return self._close(c, tick, "TAKE_PROFIT")
        if c.exit_intent is not None and tick.seq > c.exit_intent.created_seq:
            self._close(c, tick, c.exit_intent.reason)

    def _close(self, c, tick, reason):
        pos = c.position
        price = self._exit_price(c, tick)
        d = c.spec.direction
        gross_ticks = (price - pos.entry_price) * d
        level = pos.stop if reason == "STOP_LOSS" else pos.target if reason == "TAKE_PROFIT" else None
        slipped = level is not None and (price - level) * d < 0 if reason == "STOP_LOSS" else False
        nights = self.costs.swap_nights(pos.entry_ms, tick.time_ms)
        swap = nights * (self.costs.swap_long_per_lot_night if d > 0 else self.costs.swap_short_per_lot_night)
        trade = {
            "position_id": pos.position_id, "candidate_id": c.spec.candidate_id, "side": c.spec.side,
            "source_id": pos.source_id, "entry_ms": pos.entry_ms, "exit_ms": tick.time_ms,
            "entry_price": self._px(pos.entry_price), "exit_price": self._px(price),
            "stop": self._px(pos.stop), "target": self._px(pos.target), "target_id": pos.target_id,
            "exit_reason": reason, "gross_ticks": gross_ticks,
            "entry_spread_ticks": pos.entry_spread, "exit_spread_ticks": tick.ask - tick.bid,
            "fill_beyond_stop": bool(slipped), "swap_nights": nights,
            "commission_per_lot": self.costs.commission_per_lot_round_trip, "swap_per_lot": round(swap, 6),
            "cost_snapshot_sha256": self.input_hashes["costs"],
        }
        c.trades.append(trade)
        self._event("EXIT_FILLED", candidate=c, position_id=pos.position_id, at_ms=tick.time_ms,
                    source_tick_seq=tick.seq, bid=self._px(tick.bid), ask=self._px(tick.ask),
                    fill_price=self._px(price), intended_exit_reason=reason, gross_ticks=gross_ticks,
                    fill_beyond_stop=bool(slipped))
        c.position, c.exit_intent = None, None

    def _try_entry(self, c, tick):
        intent = c.entry_intent
        if intent is None or tick.seq <= intent.created_seq:
            return
        c.entry_intent = None
        spec, d = c.spec, c.spec.direction
        base = {"at_ms": tick.time_ms, "source_tick_seq": tick.seq, "source_id": intent.source_id,
                "bid": self._px(tick.bid), "ask": self._px(tick.ask),
                "session_evidence_sha256": self.input_hashes["sessions"]}
        if intent.gap_since:
            return self._event("ENTRY_BLOCKED", candidate=c, reason_code="BLOCKED_DATA_GAP", **base)
        if self.sessions is None:
            return self._event("ENTRY_BLOCKED", candidate=c, reason_code="BLOCKED_SESSION_EVIDENCE", **base)
        span = self.sessions.trade_span(tick.time_ms)
        if span is None:
            return self._event("ENTRY_BLOCKED", candidate=c, reason_code="WAIT:TRADE_SESSION_CLOSED", **base)
        preclose = span[1] - spec.preclose_minutes * 60_000
        if tick.time_ms >= preclose:
            return self._event("ENTRY_BLOCKED", candidate=c, reason_code="WAIT:PRECLOSE_ENTRY_BLOCK", **base)
        fill = tick.ask if d > 0 else tick.bid
        reference = tick.bid if d > 0 else tick.ask      # MT5 checks BUY stops vs BID, SELL stops vs ASK
        stops = self.contract.stops_level_ticks
        target = self.structure.targets(spec.target_tf, d, fill, tick.time_ms,
                                        include_zones=spec.setup == "ZONE_PULLBACK")
        if target is None:
            return self._event("ENTRY_BLOCKED", candidate=c, reason_code="WAIT:NO_VALID_STRUCTURAL_TARGET", **base)
        if (reference - intent.stop) * d < max(stops, 1) or (target["level"] - reference) * d < max(stops, 1):
            return self._event("ENTRY_BLOCKED", candidate=c, reason_code="WAIT:INVALID_BROKER_STOP_GEOMETRY",
                               stop=self._px(intent.stop), target=self._px(target["level"]), **base)
        c.positions_opened += 1
        position_id = f"{spec.candidate_id}-{c.positions_opened:05d}"
        c.position = Position(position_id, spec.side, tick.time_ms, fill, tick.ask - tick.bid, intent.stop,
                              target["level"], target["target_id"], intent.source_id,
                              tick.time_ms + spec.time_exit_minutes * 60_000, preclose)
        self._event("ENTRY_FILLED", candidate=c, position_id=position_id, fill_price=self._px(fill),
                    stop=self._px(intent.stop), target=self._px(target["level"]), target_id=target["target_id"],
                    utc_deadline_ms=c.position.utc_deadline_ms, preclose_deadline_ms=preclose, **base)

    def _m15_buffer(self, tick):
        spec = next((c.spec for c in self.candidates.values() if c.spec.setup == "ZONE_PULLBACK"),
                    SIX_CANDIDATES["B2"])
        return buffer_ticks(tick.ask - tick.bid, self.structure.tf["M15"].atr.value, spec.atr_buffer_fraction)

    def _zones(self, tick):
        if not self.structure.zones:
            return
        m15 = tick.time_ms // TIMEFRAME_MS["M15"] * TIMEFRAME_MS["M15"]
        self.structure.apply_zone_tick(tick, m15, self._m15_buffer(tick), event_id=f"T{tick.seq}")

    # ---------------------------------------------------------------- same-millisecond ambiguity
    def _would_trigger(self, c, tick):
        pos = c.position
        if pos is not None and self._in_trade(tick.time_ms) is not None:
            price, d = self._exit_price(c, tick), c.spec.direction
            if (price - pos.stop) * d <= 0 or (price - pos.target) * d >= 0:
                return True
            if c.exit_intent is not None or tick.time_ms >= min(pos.utc_deadline_ms, pos.preclose_deadline_ms):
                return True
        return c.entry_intent is not None and tick.seq > c.entry_intent.created_seq

    def _ambiguous_group(self, group):
        for c in self.candidates.values():
            if not any(self._would_trigger(c, t) for t in group):
                continue
            first = group[0]
            if c.position is not None:
                self._event("POSITION_BLOCKED", candidate=c, position_id=c.position.position_id,
                            at_ms=first.time_ms, source_tick_seq=first.seq, reason_code="BLOCKED_INTRABAR_ORDER",
                            group_size=len(group))
                c.position, c.exit_intent = None, None
            if c.entry_intent is not None and first.seq > c.entry_intent.created_seq:
                self._event("ENTRY_BLOCKED", candidate=c, at_ms=first.time_ms, source_tick_seq=first.seq,
                            source_id=c.entry_intent.source_id, reason_code="BLOCKED_INTRABAR_ORDER",
                            group_size=len(group))
                c.entry_intent = None
        touched = {}
        for t in group:
            buf = self._m15_buffer(t)
            for z in self.structure.zone_touch_candidates(t.bid, t.time_ms) + \
                    self.structure.zone_breach_candidates(t.bid, t.time_ms, buf):
                touched[z.zone_id] = z
        if touched:
            self.structure.block_zones([touched[k] for k in sorted(touched)], group[0].time_ms,
                                       "BLOCKED_INTRABAR_ORDER")

    # ---------------------------------------------------------------- end
    def _finish(self, last):
        for c in self.candidates.values():
            if c.position is not None:
                self._event("OPEN_AT_DATA_END", candidate=c, position_id=c.position.position_id,
                            at_ms=last.time_ms, reason_code="OPEN_AT_DATA_END")
            if c.entry_intent is not None:
                self._event("ENTRY_BLOCKED", candidate=c, at_ms=last.time_ms, source_id=c.entry_intent.source_id,
                            reason_code="UNFILLED_AT_DATA_END")

    def result(self) -> dict:
        per_candidate = {}
        for cid, c in self.candidates.items():
            counts = {}
            for e in self.events:
                if e["candidate_id"] == cid:
                    key = e["event_type"] + (":" + e["reason_code"] if "reason_code" in e else "")
                    counts[key] = counts.get(key, 0) + 1
            per_candidate[cid] = {"hypothesis_spec_sha256": c.spec.spec_sha256, "event_counts": counts,
                                  "trades": list(c.trades),
                                  "open_at_data_end": c.position is not None}
        return {"engine_version": ENGINE_VERSION, "input_hashes": self.input_hashes,
                "event_count": len(self.events), "ledger_sha256": canonical_sha256(self.events),
                "candidates": per_candidate, "live_execution_authorized": False, "orders_sent": 0}
