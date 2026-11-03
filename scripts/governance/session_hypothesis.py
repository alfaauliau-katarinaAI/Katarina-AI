"""Diagnostic-only broker quote-session scenario. Never connected to Stage0 scoring.

Requires explicit UTC windows, not inferred from absent broker ticks. A candidate
window is a *hypothesis*, not evidence or authorization to exclude failures.
"""
from datetime import datetime, timezone


def _utc(value):
    if not isinstance(value, str):
        raise ValueError("UTC_ISO_STRING_REQUIRED")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("INVALID_UTC_TIMESTAMP") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("AWARE_UTC_REQUIRED")
    return dt.astimezone(timezone.utc)


def validate_hypothesis(policy):
    """Fail closed for ambiguous, retroactive, overlapping, or unbounded windows."""
    if not isinstance(policy, dict):
        raise ValueError("INVALID_POLICY")
    if policy.get("schema_version") != 1 or policy.get("status") != "HYPOTHESIS_ONLY":
        raise ValueError("NO_AUTHORIZED_SESSION_POLICY")
    start = _utc(policy.get("future_effective_utc"))
    end = _utc(policy.get("expiry_utc"))
    if end <= start or (end - start).total_seconds() > 14 * 86400:
        raise ValueError("UNSAFE_VALIDITY_INTERVAL")
    windows = policy.get("candidate_closed_windows_utc")
    if not isinstance(windows, dict) or not windows or len(windows) > 25:
        raise ValueError("MISSING_SYMBOL_WINDOWS")
    validated = {}
    for symbol, intervals in windows.items():
        if not isinstance(symbol, str) or not symbol or not isinstance(intervals, list) or len(intervals) > 100:
            raise ValueError("INVALID_SYMBOL_WINDOWS")
        prev_end = None
        checked = []
        for interval in intervals:
            if not isinstance(interval, list) or len(interval) != 2:
                raise ValueError("INVALID_INTERVAL")
            a, b = map(_utc, interval)
            if a < start or b > end or a >= b or (b - a).total_seconds() > 2 * 3600:
                raise ValueError("UNSAFE_CLOSED_WINDOW")
            if prev_end is not None and a < prev_end:
                raise ValueError("OVERLAPPING_OR_UNSORTED_WINDOWS")
            prev_end = b
            checked.append((a, b))
        validated[symbol] = tuple(checked)
    return start, end, validated


def classify_hypothesis(symbol, observed_utc, policy):
    """Returns HYPOTHETICAL_CLOSED or UNVERIFIED, never a production PASS."""
    start, end, closed = validate_hypothesis(policy)
    t = _utc(observed_utc)
    if t < start or t >= end or symbol not in closed:
        return "UNVERIFIED"
    if any(a <= t < b for a, b in closed[symbol]):
        return "HYPOTHETICAL_CLOSED"
    return "UNVERIFIED"


if __name__ == "__main__":
    raise SystemExit(
        "This module is test-only. It has no CLI to alter Stage0 or submit orders."
    )
