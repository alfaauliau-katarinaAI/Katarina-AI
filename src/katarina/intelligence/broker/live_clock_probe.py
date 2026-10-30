"""Current live-feed offset verification; never evidence for historical DST.

Two actual tick snapshots must progress against a trusted host clock. This is
part of the canonical observer, not a worker or a trading permission.
"""
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from math import isfinite

from katarina.intelligence.broker.broker_clock_alignment import ClockFinding, HostClockTrust, infer_clock_shift


def tick_sample(ticks):
    """Require MT5 milliseconds consistent with seconds and valid bid/ask."""
    result = {}
    for symbol, tick in ticks.items():
        if tick is None:
            continue
        stamp, second = getattr(tick, "time_msc", None), getattr(tick, "time", None)
        bid, ask = getattr(tick, "bid", None), getattr(tick, "ask", None)
        if (type(stamp) is not int or type(second) is not int or stamp <= 0
                or not second * 1000 <= stamp < (second + 1) * 1000
                or type(bid) not in (int, float) or type(ask) not in (int, float)
                or not isfinite(bid) or not isfinite(ask) or not 0 < bid <= ask):
            continue
        result[symbol] = stamp
    return result


def verify_live_feed_clock(first, second, *, first_utc: datetime, second_utc: datetime,
                           first_mono: float, second_mono: float, host_trust,
                           broker_server: str | None, state: dict):
    """Return a finding and redacted audit. Offset jumps require a new cycle."""
    audit = {"time_basis": "LIVE_FEED_CLOCK", "historical_dst_verified": False,
             "observed_at_utc": second_utc.isoformat(), "live_execution_authorized": False,
             "orders_submitted": 0}
    def rejected(reason):
        audit["reason"] = reason
        return ClockFinding(None, len(second), 0, 0., False, reason=reason), audit
    if not isinstance(broker_server, str) or not broker_server.strip():
        return rejected("CLOCK_BROKER_IDENTITY_MISSING")
    identity = sha256(broker_server.encode("utf-8")).hexdigest()
    audit["broker_server_sha256"] = identity
    elapsed = second_mono - first_mono
    wall_elapsed = (second_utc - first_utc).total_seconds()
    if not isfinite(elapsed) or not .05 <= elapsed <= 5 or abs(elapsed - wall_elapsed) > 1:
        return rejected("HOST_UTC_STEP_DETECTED")
    audit["sample_elapsed_seconds"] = round(elapsed, 6)
    progressed = {s: ts for s, ts in second.items() if s in first
                  and 0 < ts - first[s] <= (elapsed + 5) * 1000}
    audit["progressing_symbols"] = sorted(progressed)
    audit["nonprogressing_symbols"] = sorted(set(second) - set(progressed))
    if not isinstance(host_trust, HostClockTrust):
        return rejected("NO_TRUSTED_HOST_CLOCK")
    if host_trust is not None:
        audit["host_clock_reason"] = host_trust.reason
        audit["ntp_source"] = host_trust.source
        audit["ntp_stratum"] = host_trust.stratum
        audit["ntp_status_sha256"] = host_trust.source_sha256
        audit["ntp_offset_seconds"] = (host_trust.skew_seconds
                                       if isfinite(host_trust.skew_seconds) else None)
        audit["ntp_last_sync_utc"] = (host_trust.last_sync_utc.isoformat()
                                      if host_trust.last_sync_utc else None)
        # Real OS probes always bind their measurement to monotonic + UTC time.
        if host_trust.observed_at_utc is not None:
            import time
            age = time.monotonic() - host_trust.monotonic_seconds
            utc_age = (second_utc - host_trust.observed_at_utc).total_seconds()
            if not 0 <= age <= 10 or abs(utc_age - age) > 1:
                return rejected("HOST_UTC_STEP_DETECTED")
    finding = infer_clock_shift({s: ts // 1000 for s, ts in progressed.items()},
                                second_utc.timestamp(), host_trust=host_trust,
                                require_host_trust=True, broker_server=broker_server)
    audit.update(reason=finding.reason, confirming_symbols=finding.confirming_symbols,
                 confidence_fraction=finding.confidence_fraction,
                 stale_symbols=list(finding.stale_symbols),
                 observed_shift_hours=finding.observed_hours_shift)
    if not finding.suitable_for_readonly_snapshot:
        if finding.reason == "INSUFFICIENT_FRESH_QUOTES" and len(progressed) < 3:
            return rejected("STALE_QUOTES")
        return finding, audit
    if len(progressed) < 3:
        return rejected("STALE_QUOTES")
    # A new broker cannot inherit an earlier broker's accepted offset.
    if state.get("server") != identity:
        state.clear()
        state["server"] = identity
    shift = finding.observed_hours_shift
    if state.get("shift") is not None and state["shift"] != shift:
        pending = state.get("pending")
        if pending != shift:
            state.update(pending=shift, pending_since=second_mono)
            return rejected("QUARANTINED_UNEXPLAINED_SHIFT_JUMP")
        if second_mono - state["pending_since"] < 30:
            return rejected("QUARANTINED_UNEXPLAINED_SHIFT_JUMP")
        audit["shift_reconfirmed_after_quarantine"] = True
    state.update(shift=shift)
    state.pop("pending", None)
    state.pop("pending_since", None)
    audit["reason"] = "LIVE_FEED_CLOCK_VERIFIED"
    return replace(finding, reason="LIVE_FEED_CLOCK_VERIFIED"), audit
