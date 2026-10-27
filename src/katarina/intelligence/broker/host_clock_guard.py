"""Portable, fail-closed host UTC synchronization preflight for real MT5 reads.

The host's local timezone is never treated as the clock source. Inability to
prove OS time synchronization blocks broker observation, not trading permission.
No clock adjustment, networking, MT5 login, or order is performed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import subprocess
import sys


@dataclass(frozen=True)
class HostClockStatus:
    synchronized: bool
    source: str
    reason: str
    live_authorized: bool = False


def assess_windows_status(output: str, *, now_local: datetime | None = None) -> HostClockStatus:
    """Conservative Windows Time status parser; unknown locale fails closed."""
    source = re.search(r"(?im)^\s*Source\s*:\s*(.+?)\s*$", output or "")
    leap = re.search(r"(?im)^\s*Leap Indicator\s*:\s*(\d+)", output or "")
    stratum = re.search(r"(?im)^\s*Stratum\s*:\s*(\d+)", output or "")
    last = re.search(r"(?im)^\s*Last Successful Sync Time\s*:\s*(.+?)\s*$", output or "")
    label = source.group(1).strip() if source else "UNKNOWN"
    if (not source or not leap or not stratum or not last):
        return HostClockStatus(False, label, "HOST_CLOCK_STATUS_UNVERIFIABLE")
    if ("local cmos" in label.lower() or "free-running" in label.lower()
            or "unspecified" in last.group(1).lower()
            or int(leap.group(1)) != 0 or int(stratum.group(1)) == 0):
        return HostClockStatus(False, label, "HOST_UTC_NOT_SYNCHRONIZED")
    # Windows Time prints the last successful sync in *host local time*.
    # Both operands below are local only for freshness comparison; market event
    # timestamps elsewhere stay UTC. Unknown locale / stale NTP fails closed.
    now = now_local if now_local is not None else datetime.now()
    if not isinstance(now, datetime) or now.tzinfo is not None:
        return HostClockStatus(False, label, "HOST_CLOCK_STATUS_UNVERIFIABLE")
    candidates = []
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %I:%M:%S %p",
                "%Y-%m-%d %H:%M:%S"):
        try:
            candidates.append(datetime.strptime(last.group(1).strip(), fmt))
        except ValueError:
            continue
    if not candidates:
        return HostClockStatus(False, label, "HOST_CLOCK_LAST_SYNC_UNPARSEABLE")
    # For ambiguous month/day locales, accept only a candidate inside
    # the narrow freshness window. Never guess one when neither fits.
    if not any(-60 <= (now - when).total_seconds() <= 7200 for when in candidates):
        return HostClockStatus(False, label, "HOST_CLOCK_LAST_SYNC_STALE")
    return HostClockStatus(True, label, "HOST_OS_TIME_SYNC_REPORTED")


def inspect_host_clock(*, platform: str | None = None, run=None) -> HostClockStatus:
    """Check OS-reported sync state, never assume device timezone is UTC.

    This is a necessary operational guard, not independent proof of true UTC.
    NTP peers/source must also be reviewed during device migration.
    """
    platform = platform or sys.platform
    run = run or subprocess.run
    command = (["w32tm", "/query", "/status"] if platform == "win32" else
               ["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    try:
        result = run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return HostClockStatus(False, "UNKNOWN", "HOST_CLOCK_STATUS_UNAVAILABLE")
    if result.returncode != 0:
        return HostClockStatus(False, "UNKNOWN", "HOST_CLOCK_STATUS_UNAVAILABLE")
    if platform == "win32":
        return assess_windows_status(result.stdout)
    line = result.stdout.strip().lower()
    return (HostClockStatus(True, "SYSTEM_NTP_SYNC", "HOST_OS_TIME_SYNC_REPORTED")
            if line == "yes" else
            HostClockStatus(False, "UNKNOWN", "HOST_UTC_NOT_SYNCHRONIZED"))


def require_host_clock(*, platform: str | None = None, run=None) -> HostClockStatus:
    state = inspect_host_clock(platform=platform, run=run)
    if not state.synchronized:
        raise RuntimeError(state.reason)
    return state
