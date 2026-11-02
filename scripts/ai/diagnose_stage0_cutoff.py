"""Read-only Stage0 root-cause triage; NEVER a promotion/Stage0 PASS decision.

Usage (research host or explicitly authorized read-only run):
  python scripts/ai/diagnose_stage0_cutoff.py --state-dir PATH
  python scripts/ai/diagnose_stage0_cutoff.py --state-dir PATH --as-of 2026-11-03T00:00:00+00:00

The original WP12 clock-repair cutoff is 2026-10-28T16:57:00Z.
No MT5 import, no broker login, no file writes, and no change to the ledger.
Historical data before the cutoff remains visible as an EXCLUDED diagnostic
instead of silently contaminating the current Stage0 sample.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.operations.data_health import _day_coverage, DAY_COVERAGE
from katarina.intelligence.operations.observation_ledger import stage0_session_open

CUTOFF = datetime(2026, 10, 28, 16, 57, tzinfo=timezone.utc)
COUNTED = frozenset(("OK", "PARTIAL", "NO_MARKET_DATA", "FAILED"))
SETTLED_TICKS = frozenset(("STORED", "STORED_WITH_GAPS"))


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("UTC_AWARE_TIME_REQUIRED")
    return value.astimezone(timezone.utc)


def summarize(db: sqlite3.Connection, *, since: datetime = CUTOFF,
              as_of: datetime) -> dict:
    """Return evidence-oriented aggregate counts; never change the assessment rules."""
    since, as_of = _utc(since), _utc(as_of)
    if as_of <= since:
        raise ValueError("AS_OF_MUST_BE_AFTER_CUTOFF")
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"observer_cycles", "broker_tick_days"} <= tables:
        return {"verdict": "NO_DATA", "missing_tables":
                sorted({"observer_cycles", "broker_tick_days"} - tables)}

    raw = db.execute(
        "SELECT observed_utc, status, reason, clock_shift_hours FROM observer_cycles "
        "WHERE julianday(observed_utc)>=julianday(?) "
        "AND julianday(observed_utc)<=julianday(?) ORDER BY julianday(observed_utc)",
        (since.isoformat(), as_of.isoformat())).fetchall()
    cycles = []
    for stamp, status, reason, shift in raw:
        when = _utc(datetime.fromisoformat(stamp))
        if status in COUNTED:
            cycles.append((when, status, reason, shift))
    session = [c for c in cycles if stage0_session_open(c[0])]
    day_rows = defaultdict(list)
    for item in cycles:
        day_rows[item[0].date()].append(item)
    daily = []
    for day in sorted(day_rows):
        all_rows = day_rows[day]
        eligible = [row for row in all_rows if stage0_session_open(row[0])]
        reasons = Counter((row[2] or "UNKNOWN") for row in eligible if row[1] != "OK")
        # Dominant IN-SESSION OK shift is a diagnostic comparator, not proof of UTC.
        trusted_candidates = [row[3] for row in eligible
                              if row[1] == "OK" and row[3] is not None]
        dominant = Counter(trusted_candidates).most_common(1)
        baseline = dominant[0][0] if dominant else None
        out_of_session_shift_conflicts = [
            row[0].isoformat() for row in all_rows
            if not stage0_session_open(row[0]) and row[3] is not None
            and baseline is not None and row[3] != baseline
        ]
        daily.append({
            "utc_day": day.isoformat(),
            "total_cycles": len(all_rows),
            "session_cycles": len(eligible),
            "session_ok": sum(row[1] == "OK" for row in eligible),
            "session_failure_reasons": dict(sorted(reasons.items())),
            "in_session_modal_shift_unverified": baseline,
            "out_of_session_shift_conflicts": out_of_session_shift_conflicts,
        })

    # Partial cutoff day must never be called one full successful day.
    first_full = since.date() + timedelta(days=1) if since.time() else since.date()
    stamps = sorted(row[0].timestamp() for row in cycles)
    complete_days = []
    current = first_full
    while current < as_of.date():
        if current.weekday() < 5:
            coverage = _day_coverage(current, stamps, 180)
            complete_days.append({"utc_day": current.isoformat(),
                                  "cycle_coverage": round(coverage, 6),
                                  "coverage_90pct": coverage >= DAY_COVERAGE})
        current += timedelta(days=1)

    tick_rows = db.execute(
        "SELECT symbol,day,status,snapshots_checked,snapshots_matched,reason "
        "FROM broker_tick_days ORDER BY day,symbol").fetchall()
    excluded = [x for x in tick_rows if x[1] < first_full.isoformat()]
    within = [x for x in tick_rows if first_full.isoformat() <= x[1] < as_of.date().isoformat()]
    def totals(rows):
        return {"checked": sum(int(x[3] or 0) for x in rows),
                "matched": sum(int(x[4] or 0) for x in rows),
                "mismatches": sum(max(0, int(x[3] or 0) - int(x[4] or 0)) for x in rows)}
    gaps = [{"utc_day": day, "symbol": symbol, "reason": reason}
            for symbol, day, status, _, _, reason in within if status == "GAP"]
    failures = Counter((c[2] or "UNKNOWN") for c in session if c[1] != "OK")
    # Drill down to symbols whose real broker quote was missing; do not invent
    # an acceptable market session or rewrite failed quote statuses.
    quote_failure_counts = Counter()
    if "observer_quotes" in tables:
        for stamp, symbol, reason in db.execute(
            "SELECT observed_utc,symbol,reason FROM observer_quotes "
            "WHERE status='FAILED' AND julianday(observed_utc)>=julianday(?) "
            "AND julianday(observed_utc)<=julianday(?)",
            (since.isoformat(), as_of.isoformat())
        ):
            if stage0_session_open(_utc(datetime.fromisoformat(stamp))):
                quote_failure_counts[(symbol, reason or "UNKNOWN")] += 1
    quote_failure_summary = [
        {"symbol": symbol, "reason": reason, "count": count}
        for (symbol, reason), count in sorted(quote_failure_counts.items(),
                                            key=lambda entry: (-entry[1], entry[0]))
    ]
    return {
        "type": "STAGE0_READ_ONLY_TRIAGE",
        "verdict": "DIAGNOSTIC_ONLY_NOT_STAGE0_PASS",
        "since_utc": since.isoformat(), "as_of_utc": as_of.isoformat(),
        "first_full_day_utc": first_full.isoformat(),
        "session_cycles": len(session),
        "session_ok": sum(c[1] == "OK" for c in session),
        "session_success_rate": (round(sum(c[1] == "OK" for c in session) / len(session), 6)
                                 if session else None),
        "session_failure_reasons": dict(sorted(failures.items())),
        "session_quote_failure_reasons": quote_failure_summary,
        "daily": daily,
        "complete_trading_days": complete_days,
        "tick_reconciliation_pre_cutoff_or_partial_day_EXCLUDED": totals(excluded),
        "tick_reconciliation_completed_days_after_cutoff": totals(within),
        "broker_tick_days_incomplete_GAP": gaps,
        "note": "Coverage is evidence, not automatic success; trading and restart gates unchanged.",
        "live_execution_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--since", default=CUTOFF.isoformat())
    parser.add_argument("--as-of", help="Explicit UTC-aware ISO8601 timestamp for reproducible results")
    args = parser.parse_args(argv)
    try:
        since = _utc(datetime.fromisoformat(args.since))
        now = _utc(datetime.fromisoformat(args.as_of)) if args.as_of else datetime.now(timezone.utc)
    except ValueError as ex:
        parser.error(f"Timezone-aware times required: {ex}")
    db_path = Path(args.state_dir) / "context.sqlite3"
    if not db_path.is_file():
        print(json.dumps({"verdict": "NO_DATA", "reason": "CONTEXT_DB_NOT_FOUND"}))
        return 1
    db = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        db.execute("PRAGMA query_only=ON")
        result = summarize(db, since=since, as_of=now)
    finally:
        db.close()
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["verdict"] != "NO_DATA" else 1


if __name__ == "__main__":
    raise SystemExit(main())
