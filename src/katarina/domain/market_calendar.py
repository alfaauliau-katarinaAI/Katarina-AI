"""US/EU daylight-saving calendar in UTC, standard library only.

One source for the DST rules used by Stage 0 session windows, data-health shift checks,
bar clock evidence, validation rollover and research playbooks. No timezone database is
needed (the Windows Server 2012 VPS has no reliable tzdata).

- US: 2nd Sunday of March 07:00 UTC (02:00 EST) until 1st Sunday of November 06:00 UTC.
- EU/UK: last Sunday of March 01:00 UTC until last Sunday of October 01:00 UTC.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

__all__ = ["nth_sunday", "last_sunday", "dst_transitions", "is_us_dst", "is_eu_dst"]


def nth_sunday(year: int, month: int, nth: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (nth - 1))


def last_sunday(year: int, month: int) -> date:
    last = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def dst_transitions(year: int) -> list[date]:
    """EU (last Sunday Mar/Oct) and US (2nd Sunday Mar, 1st Sunday Nov) clock-change dates."""
    return sorted({last_sunday(year, 3), last_sunday(year, 10),
                   nth_sunday(year, 3, 2), nth_sunday(year, 11, 1)})


def _aware_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("aware_utc_datetime_required")
    return moment.astimezone(timezone.utc)


def _at(day: date, hour: int) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)


def is_us_dst(moment: datetime) -> bool:
    moment = _aware_utc(moment)
    year = moment.year
    return _at(nth_sunday(year, 3, 2), 7) <= moment < _at(nth_sunday(year, 11, 1), 6)


def is_eu_dst(moment: datetime) -> bool:
    moment = _aware_utc(moment)
    year = moment.year
    return _at(last_sunday(year, 3), 1) <= moment < _at(last_sunday(year, 10), 1)
