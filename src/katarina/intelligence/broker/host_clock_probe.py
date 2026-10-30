"""Read-only, bounded Windows NTP status probe. Unknown evidence is untrusted.

This does not set the clock, resynchronize Windows, or grant trading permission.
The supported w32tm status format uses elapsed seconds to avoid guessing local
date formats. Other platforms/formats must supply a separately reviewed probe.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import platform
import re
import subprocess
import time


TRUSTED_SOURCES = frozenset({"time.windows.com", "time.nist.gov", "pool.ntp.org"})


@dataclass(frozen=True)
class HostClockProbe:
    trusted: bool
    reason: str
    observed_utc: datetime
    monotonic_seconds: float
    source: str | None = None
    stratum: int | None = None
    sync_age_seconds: float | None = None
    offset_seconds: float | None = None
    raw_sha256: str | None = None

    @property
    def last_sync_utc(self):
        if self.sync_age_seconds is None:
            return None
        return self.observed_utc - timedelta(seconds=self.sync_age_seconds)

    def current_at(self, now: datetime, monotonic_now: float, *, max_age=10.0) -> bool:
        if now.tzinfo is None or not math.isfinite(monotonic_now):
            return False
        elapsed = monotonic_now - self.monotonic_seconds
        utc_elapsed = (now - self.observed_utc).total_seconds()
        return (self.trusted and 0 <= elapsed <= max_age
                and abs(utc_elapsed - elapsed) <= 1.0)


def parse_w32tm_status(raw: str, now: datetime, monotonic_now: float, *,
                       max_sync_age_seconds=14400.0, max_offset_seconds=1.0,
                       trusted_sources=TRUSTED_SOURCES) -> HostClockProbe:
    """Require all trust fields once, with finite values and exact source match."""
    if now.tzinfo is None:
        raise ValueError("aware_clock_required")
    now = now.astimezone(timezone.utc)
    if (not math.isfinite(monotonic_now) or not 0 < max_sync_age_seconds <= 86400
            or not 0 < max_offset_seconds <= 15):
        raise ValueError("invalid_host_clock_budget")

    def blocked(reason):
        return HostClockProbe(False, reason, now, monotonic_now)

    if not isinstance(raw, str) or len(raw) > 32768:
        return blocked("NTP_STATUS_INVALID")
    fields = {}
    for line in raw.splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        if key in fields:
            return blocked("NTP_STATUS_DUPLICATE_FIELD")
        fields[key] = value.strip()
    required = ("Leap Indicator", "Stratum", "Source", "Phase Offset",
                "State Machine", "Last Sync Error", "Time since Last Good Sync Time")
    if any(key not in fields for key in required):
        return blocked("NTP_STATUS_FIELDS_MISSING")

    def integer(key):
        match = re.fullmatch(r"([0-9]+)(?:\s*\([^\r\n]*\))?", fields[key])
        if not match:
            raise ValueError("bad_integer")
        return int(match.group(1))

    def seconds(key):
        match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))s", fields[key])
        if not match:
            raise ValueError("bad_seconds")
        number = float(match.group(1))
        if not math.isfinite(number):
            raise ValueError("nonfinite")
        return number

    try:
        leap, stratum = integer("Leap Indicator"), integer("Stratum")
        state, error = integer("State Machine"), integer("Last Sync Error")
        age, offset = seconds("Time since Last Good Sync Time"), seconds("Phase Offset")
    except (ValueError, OverflowError):
        return blocked("NTP_STATUS_PARSE_FAILED")
    source = fields["Source"].lower()
    # w32tm may append client peer flags such as ,0x8; reject other suffixes.
    match = re.fullmatch(r"([a-z0-9.-]+)(?:,0x[0-9a-f]+)?", source)
    source = match.group(1) if match else ""
    if source not in trusted_sources:
        return blocked("NTP_SOURCE_NOT_TRUSTED")
    if leap != 0 or state != 2 or error != 0 or not 1 <= stratum <= 15:
        return blocked("NTP_NOT_SYNCHRONIZED")
    if not 0 <= age <= max_sync_age_seconds:
        return blocked("NTP_SYNC_STALE")
    if abs(offset) > max_offset_seconds:
        return blocked("NTP_OFFSET_EXCEEDED")
    from hashlib import sha256
    return HostClockProbe(True, "NTP_SYNCHRONIZED", now, monotonic_now,
                          source, stratum, age, offset,
                          sha256(raw.encode("utf-8")).hexdigest())


def inspect_windows_host_clock(*, max_sync_age_seconds=14400.0) -> HostClockProbe:
    """Query Windows only; a failed/unknown probe never synthesizes a sync."""
    before_utc, before_mono = datetime.now(timezone.utc), time.monotonic()
    def blocked(reason):
        return HostClockProbe(False, reason, before_utc, before_mono)
    if platform.system() != "Windows":
        return blocked("NTP_PLATFORM_UNSUPPORTED")
    try:
        result = subprocess.run(["w32tm", "/query", "/status", "/verbose"],
                                capture_output=True, text=True, timeout=3,
                                check=False)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return blocked("NTP_QUERY_FAILED")
    after_utc, after_mono = datetime.now(timezone.utc), time.monotonic()
    elapsed = after_mono - before_mono
    if (not 0 <= elapsed <= 4 or
            abs((after_utc - before_utc).total_seconds() - elapsed) > 1):
        return blocked("HOST_UTC_STEP_DETECTED")
    if result.returncode != 0:
        return blocked("NTP_QUERY_FAILED")
    return parse_w32tm_status(result.stdout, after_utc, after_mono,
                             max_sync_age_seconds=max_sync_age_seconds)
