"""D9 per-symbol quote/trade sessions. Evidence-only, never an execution gate.

The broker's weekly wall-clock schedule does not establish its UTC offset,
holiday exceptions or validity period. All three need explicit evidence.
No DST rule is inferred from New York, Europe or a previous observed offset.
This module is used only by the read-only preview CLI; D8 remains official.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import math
import re


def _utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("D9_AWARE_TIME_REQUIRED")
    return value.astimezone(timezone.utc)


def _digest(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("D9_EVIDENCE_HASH_REQUIRED")
    return value


class BrokerSessions:
    """Validate a schedule and independently evidenced half-open UTC clock windows.

    ``verified_broker_dates`` means exceptions/holidays were checked for those
    broker-local dates; a missing weekday or null entry means unavailable, not
    closed. Session pairs are integer seconds since broker midnight, [start,end).
    End may exceed 86400 for an explicitly documented overnight session.
    """

    def __init__(self, schedule: dict, clock_proof: dict):
        if (not isinstance(schedule, dict) or not isinstance(clock_proof, dict)
                or type(schedule.get("schema_version")) is not int or schedule["schema_version"] != 1
                or type(clock_proof.get("schema_version")) is not int or clock_proof["schema_version"] != 1):
            raise ValueError("D9_SCHEMA_INVALID")
        self.server = _digest(schedule["broker_server_sha256"])
        self.source = _digest(schedule["source_sha256"])
        self.captured = _utc(schedule["captured_at_utc"])
        self.valid_from = _utc(schedule["valid_from_utc"]) if schedule.get("valid_from_utc") else None
        self.valid_until = _utc(schedule["valid_until_utc"]) if schedule.get("valid_until_utc") else None
        if (self.valid_from and self.valid_from < self.captured) or (
                self.valid_from and self.valid_until and self.valid_until <= self.valid_from):
            raise ValueError("D9_SCHEDULE_VALIDITY_INVALID")
        if not isinstance(schedule["verified_broker_dates"], list):
            raise ValueError("D9_VERIFIED_DATES_INVALID")
        self.dates = frozenset(date.fromisoformat(d) for d in schedule["verified_broker_dates"])
        self.symbols = deepcopy(schedule["symbols"])
        if not isinstance(self.symbols, dict) or not self.symbols:
            raise ValueError("D9_SYMBOLS_REQUIRED")
        for symbol, kinds in self.symbols.items():
            if not isinstance(symbol, str) or not symbol or not isinstance(kinds, dict):
                raise ValueError("D9_SYMBOL_INVALID")
            for kind, week in kinds.items():
                if kind not in ("quote", "trade") or not isinstance(week, dict):
                    raise ValueError("D9_SESSION_KIND_INVALID")
                for weekday, sessions in week.items():
                    if weekday not in tuple(str(d) for d in range(7)):
                        raise ValueError("D9_WEEKDAY_INVALID")
                    if sessions is None:
                        continue
                    if not isinstance(sessions, list):
                        raise ValueError("D9_INTERVAL_INVALID")
                    last_end = -1
                    for pair in sessions:
                        if (not isinstance(pair, list) or len(pair) != 2
                                or any(type(s) is not int for s in pair)
                                or not 0 <= pair[0] < 86400 or not pair[0] < pair[1] <= 172800
                                or pair[0] < last_end):
                            raise ValueError("D9_INTERVAL_INVALID")
                        last_end = pair[1]
        self.clock_server = _digest(clock_proof["broker_server_sha256"])
        self.clock = []
        if not isinstance(clock_proof["intervals"], list):
            raise ValueError("D9_CLOCK_INTERVAL_INVALID")
        for item in clock_proof["intervals"]:
            if not isinstance(item, dict):
                raise ValueError("D9_CLOCK_INTERVAL_INVALID")
            start, end = _utc(item["start_utc"]), _utc(item["end_utc"])
            offset = item["offset_seconds"]
            if (start >= end or type(offset) is not int or not -14 * 3600 <= offset <= 14 * 3600
                    or item["reason"] != "LIVE_FEED_CLOCK_VERIFIED"):
                raise ValueError("D9_CLOCK_INTERVAL_INVALID")
            _digest(item["evidence_sha256"])
            self.clock.append((start, end, offset))
        self.clock.sort()
        if any(a[1] > b[0] for a, b in zip(self.clock, self.clock[1:])):
            raise ValueError("D9_CLOCK_INTERVAL_OVERLAP")

    def classify(self, moment: datetime, symbol: str, *, kind: str = "quote",
                 observed_shift_hours=None) -> dict:
        moment = _utc(moment)
        if kind not in ("quote", "trade"):
            raise ValueError("D9_SESSION_KIND_INVALID")

        def result(state, reason, **details):
            return {"state": state, "reason": reason, **details}

        if self.clock_server != self.server:
            return result("UNVERIFIED", "D9_SERVER_MISMATCH")
        if symbol not in self.symbols or kind not in self.symbols[symbol]:
            return result("UNVERIFIED", "D9_SYMBOL_SESSION_MISSING")
        if moment < self.captured:
            return result("UNVERIFIED", "D9_BEFORE_CAPTURE")
        if not self.valid_from or not self.valid_until:
            return result("UNVERIFIED", "D9_SCHEDULE_VALIDITY_MISSING")
        if not self.valid_from <= moment < self.valid_until:
            return result("UNVERIFIED", "D9_OUTSIDE_SCHEDULE_VALIDITY")
        clock = next((r for r in self.clock if r[0] <= moment < r[1]), None)
        if clock is None:
            return result("UNVERIFIED", "D9_CLOCK_EVIDENCE_MISSING")
        if (type(observed_shift_hours) not in (int, float) or not math.isfinite(observed_shift_hours)
                or observed_shift_hours * 3600 != clock[2]):
            return result("UNVERIFIED", "D9_CYCLE_CLOCK_MISMATCH")
        broker = moment + timedelta(seconds=clock[2])
        day = broker.date()
        week = self.symbols[symbol][kind]
        sessions = week.get(str(day.weekday()))
        if day not in self.dates:
            return result("UNVERIFIED", "D9_DATE_NOT_VERIFIED")
        if sessions is None:
            return result("UNVERIFIED", "D9_DAY_SESSION_UNAVAILABLE")
        second = broker.hour * 3600 + broker.minute * 60 + broker.second + broker.microsecond / 1e6
        if any(start <= second < end for start, end in sessions):
            return result("OPEN", "D9_SCHEDULED_OPEN")
        # An explicit overnight session belongs to its starting broker date.
        previous = day - timedelta(days=1)
        previous_sessions = week.get(str(previous.weekday()))
        if previous_sessions is None:
            return result("UNVERIFIED", "D9_PREVIOUS_DAY_UNAVAILABLE")
        carry = any(start <= second + 86400 < end for start, end in previous_sessions)
        if carry:
            if previous not in self.dates:
                return result("UNVERIFIED", "D9_DATE_NOT_VERIFIED")
            return result("OPEN", "D9_OVERNIGHT_OPEN")
        return result("CLOSED", "D9_SCHEDULED_CLOSED")


def preview(db, now: datetime, sessions: BrokerSessions, *, required_symbols,
            since: datetime | None = None) -> dict:
    """Read ledger quotes without rewriting statuses, criteria, cutoff or denominator.

    Reports quote readiness separately from system failures. A clock/connection
    failure is never excused by a scheduled quote closure. Required symbols
    come from an independent universe, never from the schedule being checked.
    Missing/extra schedule symbols block readiness. No PASS verdict.
    """
    now = _utc(now)
    since = _utc(since) if since is not None else None
    if since is not None and since > now:
        raise ValueError("D9_SINCE_IN_FUTURE")
    if (not isinstance(required_symbols, (list, tuple)) or not required_symbols
            or any(not isinstance(s, str) or not s.strip() for s in required_symbols)
            or len(set(required_symbols)) != len(required_symbols)):
        raise ValueError("D9_REQUIRED_UNIVERSE_INVALID")
    required = set(required_symbols)
    declared = set(sessions.symbols)
    universe_matches = required == declared
    counts, reasons = Counter(), Counter()
    by_symbol = {symbol: Counter() for symbol in sorted(required)}
    clause, params = "", []
    if since is not None:
        clause = " AND julianday(observed_utc)>=julianday(?)"
        params.append(since.isoformat())
    params.append(now.isoformat())
    cycles = db.execute(
        "SELECT cycle_id,observed_utc,status,reason,clock_shift_hours,orders_submitted "
        "FROM observer_cycles WHERE status IN ('OK','PARTIAL','NO_MARKET_DATA','FAILED')"
        + clause + " AND julianday(observed_utc)<=julianday(?) ORDER BY julianday(observed_utc)", params)
    for cid, stamp, status, reason, shift, orders in cycles:
        moment = _utc(stamp)
        quotes = {}
        for symbol, qstatus, bid, ask, tick in db.execute(
                "SELECT symbol,status,bid,ask,tick_epoch FROM observer_quotes WHERE cycle_id=?", (cid,)):
            quotes.setdefault(symbol, []).append((qstatus, bid, ask, tick))
        states = []
        missing_open = False
        for symbol in by_symbol:
            decision = sessions.classify(moment, symbol, observed_shift_hours=shift)
            state = decision["state"]
            states.append(state)
            reasons[decision["reason"]] += 1
            by_symbol[symbol][state] += 1
            if state == "OPEN":
                rows = quotes.get(symbol, [])
                valid = len(rows) == 1 and rows[0][0] == "OK"
                if valid:
                    _, bid, ask, tick = rows[0]
                    valid = (all(type(v) in (int, float) and math.isfinite(v) for v in (bid, ask, tick))
                             and bid > 0 and ask >= bid and 0 <= moment.timestamp() - tick <= 90)
                by_symbol[symbol]["quotes_available" if valid else "quotes_missing_or_invalid"] += 1
                missing_open |= not valid
        if not universe_matches:
            reasons["D9_UNIVERSE_MISMATCH"] += 1
        if orders != 0 or status not in ("OK", "PARTIAL") or (
                status == "PARTIAL" and reason != "SOME_SYMBOLS_WITHOUT_QUOTE"):
            label = "SYSTEM_FAILURE_RETAINED"
        elif not universe_matches or "UNVERIFIED" in states:
            label = "UNVERIFIED"
        elif missing_open:
            label = "MISSING_OPEN_QUOTES"
        elif "OPEN" not in states:
            label = "NO_QUOTES_EXPECTED"
        else:
            label = "QUOTE_READY_ONLY"
        counts[label] += 1
    return {"schema_version": 1, "diagnostic_only": True, "official_verdict_effect": "NONE",
            "activation_effective_utc": None, "live_execution_authorized": False,
            "as_of_utc": now.isoformat(), "since_utc": since.isoformat() if since else None,
            "broker_server_sha256": sessions.server, "schedule_source_sha256": sessions.source,
            "required_symbols": sorted(required), "declared_symbols": sorted(declared),
            "universe_matches": universe_matches,
            "missing_schedule_symbols": sorted(required - declared),
            "unexpected_schedule_symbols": sorted(declared - required),
            "cycles": sum(counts.values()), "cycle_categories": dict(sorted(counts.items())),
            "session_reasons": dict(sorted(reasons.items())),
            "symbols": {s: dict(sorted(v.items())) for s, v in by_symbol.items()}}
