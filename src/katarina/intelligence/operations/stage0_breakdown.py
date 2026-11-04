"""Stage 0 failure breakdown: why each counted cycle failed, by day, UTC hour, symbol and market phase.

Read-only and diagnostic. It never changes the official Stage 0 verdict, cutoff, denominator or the
classification stored in the ledger (``data_health.assess`` remains the only judge). Alternative
session views are labelled ``diagnostic_only`` and exist so the Owner can decide on a rule
prospectively; they are not criteria.

Market phase of a failure (DST aware, ``katarina.domain.market_calendar``):
- ``DAILY_BREAK_NY17``: within [-15 min, +60 min) of 17:00 America/New_York, the FX rollover when
  FX ticks thin out and the broker's metal/index CFDs pause (XAUUSD/NAS100 have no quote). That is
  21:45-22:00..23:00 UTC in US winter and 20:45..22:00 UTC in US summer.
- ``WEEK_EDGE``: Friday 19:00-20:00 UTC or Sunday/Monday before 01:00 UTC.
- ``SESSION``: anything else (connection, clock, program or broker problems during the session).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from katarina.domain.market_calendar import is_us_dst
from katarina.intelligence.operations.observation_ledger import fx_session_open, stage0_session_open

COUNTED = "status IN ('OK','PARTIAL','NO_MARKET_DATA','FAILED')"
BREAK_BEFORE_MINUTES = 15
BREAK_AFTER_MINUTES = 60
WP15_BEFORE_MINUTES = 15
WP15_AFTER_MINUTES = 30


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("aware_utc_datetime_required")
    return value.astimezone(timezone.utc)


def ny17_minutes_utc(moment: datetime) -> int:
    """17:00 New York expressed in UTC minutes of the same UTC day."""
    return (21 if is_us_dst(moment) else 22) * 60


def _in_ny17_window(moment: datetime, before: int, after: int) -> bool:
    roll = ny17_minutes_utc(moment)
    minute = moment.hour * 60 + moment.minute
    return roll - before <= minute < roll + after


def market_phase(moment: datetime) -> str:
    moment = _utc(moment)
    if _in_ny17_window(moment, BREAK_BEFORE_MINUTES, BREAK_AFTER_MINUTES):
        return "DAILY_BREAK_NY17"
    if (moment.weekday() == 4 and moment.hour == 19) or (moment.weekday() in (6, 0) and moment.hour < 1):
        return "WEEK_EDGE"
    return "SESSION"


def _week_open(moment: datetime) -> bool:
    return not (moment.weekday() > 4 or (moment.weekday() == 4 and moment.hour >= 20))


DIAGNOSTIC_VIEWS = {
    "official_stage0_session_open": stage0_session_open,
    "legacy_fx_session_open": fx_session_open,
    "wp15_ny17_-15_+30_if_activated": lambda m: _week_open(m) and not _in_ny17_window(
        m, WP15_BEFORE_MINUTES, WP15_AFTER_MINUTES),
    "diagnostic_ny17_-15_+60_daily_break": lambda m: _week_open(m) and not _in_ny17_window(
        m, BREAK_BEFORE_MINUTES, BREAK_AFTER_MINUTES),
}


def breakdown(db, now: datetime, *, since: datetime | None = None) -> dict:
    now = _utc(now)
    since = _utc(since) if since is not None else None
    clause, params = "", ()
    if since is not None:
        clause, params = " AND observed_utc >= ?", (since.isoformat(),)
    rows = [(cid, datetime.fromisoformat(stamp), status, reason) for cid, stamp, status, reason in db.execute(
        f"SELECT cycle_id, observed_utc, status, reason FROM observer_cycles WHERE {COUNTED}{clause} "
        f"AND observed_utc <= ? ORDER BY observed_utc", (*params, now.isoformat()))]
    counted = [r for r in rows if stage0_session_open(r[1])]
    failures = [r for r in counted if r[2] != "OK"]
    by_phase, by_reason, by_day, by_hour = Counter(), Counter(), defaultdict(Counter), defaultdict(Counter)
    phase_reason = defaultdict(Counter)
    for _, moment, status, reason in failures:
        phase = market_phase(moment)
        label = reason or status
        by_phase[phase] += 1
        by_reason[label] += 1
        phase_reason[phase][label] += 1
        by_day[moment.date().isoformat()][label] += 1
        by_hour[moment.strftime("%H")][label] += 1
    missing_symbols, missing_by_phase = Counter(), defaultdict(Counter)
    for cid, moment, status, _ in failures:
        if status != "PARTIAL":
            continue
        for symbol, quote_status, quote_reason in db.execute(
                "SELECT symbol, status, reason FROM observer_quotes WHERE cycle_id=?", (cid,)):
            if quote_status != "OK":
                missing_symbols[f"{symbol}|{quote_reason}"] += 1
                missing_by_phase[market_phase(moment)][symbol] += 1
    views = {}
    for name, rule in DIAGNOSTIC_VIEWS.items():
        selected = [r for r in rows if rule(r[1])]
        ok = sum(1 for r in selected if r[2] == "OK")
        views[name] = {"cycles": len(selected), "ok": ok,
                       "rate": round(ok / len(selected), 6) if selected else None,
                       "diagnostic_only": name != "official_stage0_session_open"}
    return {
        "schema_version": 1, "as_of_utc": now.isoformat(), "since_utc": since.isoformat() if since else None,
        "cycles_counted": len(counted), "failures": len(failures),
        "failures_by_market_phase": dict(by_phase),
        "failures_by_phase_and_reason": {k: dict(v) for k, v in phase_reason.items()},
        "failures_by_reason": dict(by_reason),
        "failures_by_day": {k: dict(v) for k, v in sorted(by_day.items())},
        "failures_by_utc_hour": {k: dict(v) for k, v in sorted(by_hour.items())},
        "partial_missing_symbol_reason": dict(missing_symbols),
        "partial_missing_symbol_by_phase": {k: dict(v) for k, v in missing_by_phase.items()},
        "session_views": views,
        "official_verdict_effect": "NONE",
        "note": "Diagnostic views never replace data_health.assess; a rule change needs an Owner decision "
                "with a prospective effective UTC (ROLLOVER_RULE_EFFECTIVE_UTC).",
        "live_execution_authorized": False,
    }


def first_break_window(day: datetime) -> tuple[datetime, datetime]:
    """UTC [start, end) of the DAILY_BREAK_NY17 window on ``day`` (for reports and tests)."""
    day = _utc(day).replace(hour=0, minute=0, second=0, microsecond=0)
    roll = day + timedelta(minutes=ny17_minutes_utc(day + timedelta(hours=12)))
    return roll - timedelta(minutes=BREAK_BEFORE_MINUTES), roll + timedelta(minutes=BREAK_AFTER_MINUTES)
