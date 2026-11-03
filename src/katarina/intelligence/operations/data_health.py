"""Stage 0 data-health checker: evaluates docs/ROADMAP.md "Tahap 0" exit criteria from the ledger.

Read-only. It reads the tables written by
:mod:`katarina.intelligence.operations.observation_ledger` and returns a deterministic report.
Each criterion is ``PASS``, ``NOT_MET`` (data exists but the bar is not reached yet) or
``NO_DATA``. A PASS here is evidence about data quality only — never trading clearance.
"""
from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone

from katarina.intelligence.operations.observation_ledger import (
    ROLLOVER_RULE_EFFECTIVE_UTC,
    fx_session_open,
    stage0_session_open,
)

MIN_TRADING_DAYS = 10
MIN_SUCCESS_RATE = 0.98
MIN_QUOTE_COVERAGE = 0.98
MIN_RECOVERIES = 3
RECOVERY_SECONDS = 600
DAY_COVERAGE = 0.90
DST_TOLERANCE_DAYS = 3
SETTLED_TICK_STATES = ("STORED", "STORED_WITH_GAPS", "GAP")
COUNTED = "status IN ('OK','PARTIAL','NO_MARKET_DATA','FAILED')"


def _criterion(name, status, **detail):
    return {"criterion": name, "status": status, **detail}


def _tables(db):
    return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _nth_sunday(year, month, nth):
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (nth - 1))


def _last_sunday(year, month):
    last = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def dst_transitions(year):
    """EU (last Sunday Mar/Oct) and US (2nd Sunday Mar, 1st Sunday Nov) clock changes."""
    return sorted({_last_sunday(year, 3), _last_sunday(year, 10),
                   _nth_sunday(year, 3, 2), _nth_sunday(year, 11, 1)})


def _near_dst(moment: datetime) -> bool:
    day = moment.date()
    return any(abs((day - change).days) <= DST_TOLERANCE_DAYS for change in dst_transitions(day.year))


def _day_coverage(day: date, stamps, window_seconds) -> float:
    """Share of the day's session minutes with a cycle in the preceding window."""
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    total = covered = 0
    for minute in range(24 * 60):
        moment = start + timedelta(minutes=minute)
        if not stage0_session_open(moment):
            continue
        total += 1
        point = moment.timestamp()
        index = bisect_right(stamps, point) - 1
        if index >= 0 and point - stamps[index] <= window_seconds:
            covered += 1
    return covered / total if total else 0.0


def _since_filter(column: str, since: datetime | None, now: datetime | None = None) -> tuple[str, tuple]:
    clauses = []
    params = []
    if since is not None:
        clauses.append(f"julianday({column}) >= julianday(?)")
        params.append(since.isoformat())
    if now is not None:
        clauses.append(f"julianday({column}) <= julianday(?)")
        params.append(now.isoformat())
    if clauses:
        return " AND " + " AND ".join(clauses), tuple(params)
    return "", ()


def _news_pipeline(db, since: datetime | None = None, now: datetime | None = None) -> dict:
    """WP3 informational diagnosis, never an exit criterion."""
    stats = dict(cycles_with_news_rows=0, cycles_without_verified_articles=0,
                 no_recent_release_cycles=0, retrieval_failed_cycles=0,
                 no_recent_release_percent=None, retrieval_failed_percent=None,
                 verdict_effect="NONE")
    if not {"observer_news", "observer_cycles"} <= _tables(db):
        return stats
    by_cycle = {}
    clause, params = _since_filter("c.observed_utc", since, now)
    for cycle, window, verified, failures_json in db.execute(
            "SELECT n.cycle_id,n.in_window,n.verified,n.failures_json "
            "FROM observer_news n JOIN observer_cycles c ON c.cycle_id=n.cycle_id "
            f"WHERE {COUNTED}{clause} ORDER BY n.cycle_id,n.source", params):
        item = by_cycle.setdefault(cycle, {"window": 0, "verified": 0, "failure": False})
        item["window"] += window
        item["verified"] += verified
        try:
            item["failure"] |= bool(json.loads(failures_json))
        except (TypeError, ValueError):
            item["failure"] = True
    stats["cycles_with_news_rows"] = len(by_cycle)
    absent = [r for r in by_cycle.values() if r["verified"] == 0]
    stats["cycles_without_verified_articles"] = len(absent)
    for row in absent:
        if row["failure"]:
            stats["retrieval_failed_cycles"] += 1
        elif row["window"] == 0:
            stats["no_recent_release_cycles"] += 1
    if absent:
        denominator = len(absent)
        stats["no_recent_release_percent"] = round(
            100 * stats["no_recent_release_cycles"] / denominator, 1)
        stats["retrieval_failed_percent"] = round(
            100 * stats["retrieval_failed_cycles"] / denominator, 1)
    return stats


def assess(db, now: datetime, *, interval_seconds: int = 60, since: datetime | None = None) -> dict:
    if now.tzinfo is None:
        raise ValueError("aware_clock_required")
    if type(interval_seconds) is not int or not 30 <= interval_seconds <= 3600:
        raise ValueError("invalid_interval")
    now = now.astimezone(timezone.utc)
    if since is not None:
        if not isinstance(since, datetime) or since.tzinfo is None or since > now:
            raise ValueError("since_requires_aware_datetime_not_in_future")
        since = since.astimezone(timezone.utc)

    clause, params = _since_filter("observed_utc", since, now)
    report = {"schema_version": 1, "stage": "TAHAP_0_OBSERVER_DATA", "as_of_utc": now.isoformat(),
              "interval_seconds": interval_seconds,
              "session_rule": "Mon 00:00 - Fri 20:00 UTC; before effective (or while disabled): exclude 20:45-21:15 UTC (legacy fx_session_open); on/after approved effective: exclude 17:00 America/New_York rollover [-15m, +30m), DST aware",
              "rollover_rule_effective_utc": ROLLOVER_RULE_EFFECTIVE_UTC,
              "live_execution_authorized": False, "criteria": []}
    if since is not None:
        report["since_utc"] = since.isoformat()
        report["partial_tick_day_excluded"] = (since.date().isoformat()
            if since != since.replace(hour=0, minute=0, second=0, microsecond=0) else None)

    criteria = report["criteria"]
    report["news_pipeline"] = _news_pipeline(db, since, now)
    if not {"observer_cycles", "observer_quotes"} <= _tables(db):
        criteria.append(_criterion("ledger_present", "NO_DATA", reason="OBSERVATION_LEDGER_MISSING"))
        return _finish(report)

    cycles = [(datetime.fromisoformat(stamp), status, reason, shift, orders)
              for stamp, status, reason, shift, orders in db.execute(
                  f"SELECT observed_utc, status, reason, clock_shift_hours, orders_submitted "
                  f"FROM observer_cycles WHERE {COUNTED}{clause} ORDER BY observed_utc", params)]
    session = [c for c in cycles if stage0_session_open(c[0])]
    report["cycles_total"] = len(cycles)
    report["cycles_in_session"] = len(session)
    report["first_cycle_utc"] = cycles[0][0].isoformat() if cycles else None
    report["last_cycle_utc"] = cycles[-1][0].isoformat() if cycles else None

    # 1. consecutive trading days with near-complete session coverage
    stamps = [c[0].timestamp() for c in cycles]
    streak = best = 0
    covered_days = []
    if cycles:
        first_full_day = (
            since.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            if since is not None and since != since.replace(hour=0, minute=0, second=0, microsecond=0)
            else since if since is not None else cycles[0][0]
        )
        start_date = first_full_day.date()
        day = max(cycles[0][0].date(), start_date)
        while day < now.date():
            if day.weekday() < 5:
                if _day_coverage(day, stamps, 3 * interval_seconds) >= DAY_COVERAGE:
                    streak += 1
                    covered_days.append(day.isoformat())
                else:
                    streak = 0
                best = max(best, streak)
            day += timedelta(days=1)
    criteria.append(_criterion(
        "consecutive_trading_days", "NO_DATA" if not cycles else "PASS" if best >= MIN_TRADING_DAYS else "NOT_MET",
        required=MIN_TRADING_DAYS, best_streak=best, current_streak=streak, covered_days=covered_days,
        day_coverage_required=DAY_COVERAGE))

    # 2. cycle success while the market is open; every failure has a reason
    ok = sum(1 for c in session if c[1] == "OK")
    unexplained = sum(1 for c in session if c[1] != "OK" and not c[2])
    rate = ok / len(session) if session else None
    reasons = {}
    for c in session:
        if c[1] != "OK":
            reasons[c[2] or "MISSING_REASON"] = reasons.get(c[2] or "MISSING_REASON", 0) + 1
    criteria.append(_criterion(
        "cycle_success_rate", "NO_DATA" if not session else
        "PASS" if rate >= MIN_SUCCESS_RATE and unexplained == 0 else "NOT_MET",
        required=MIN_SUCCESS_RATE, rate=None if rate is None else round(rate, 6), ok=ok,
        cycles=len(session), failures_without_reason=unexplained, failure_reasons=dict(sorted(reasons.items()))))

    # 3. no duplicates; monotonic timestamps per symbol
    duplicate_quotes = db.execute(
        f"SELECT COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM observer_quotes WHERE 1=1{clause} "
        "GROUP BY symbol, observed_utc HAVING n>1)", params).fetchone()[0]
    duplicate_cycles = db.execute(
        f"SELECT COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM observer_cycles WHERE {COUNTED}{clause} "
        "GROUP BY observed_utc HAVING n>1)", params).fetchone()[0]
    regressions = 0
    last = {}
    if since is not None:
        # Context from before the cutoff detects a regression at its boundary;
        # these rows never count as observations inside the requested period.
        for symbol, epoch in db.execute(
                "SELECT symbol,tick_epoch FROM observer_quotes WHERE status='OK' "
                "AND julianday(observed_utc)<julianday(?) ORDER BY julianday(observed_utc)",
                (since.isoformat(),)):
            last[symbol] = epoch
    for symbol, epoch in db.execute(
            f"SELECT symbol, tick_epoch FROM observer_quotes WHERE status='OK'{clause} ORDER BY symbol, observed_utc", params):
        if symbol in last and epoch < last[symbol]:
            regressions += 1
        last[symbol] = epoch
    quotes_total = db.execute(f"SELECT COUNT(*) FROM observer_quotes WHERE 1=1{clause}", params).fetchone()[0]
    criteria.append(_criterion(
        "no_duplicates_monotonic", "NO_DATA" if not quotes_total else
        "PASS" if duplicate_quotes == duplicate_cycles == regressions == 0 else "NOT_MET",
        duplicate_quote_rows=duplicate_quotes, duplicate_cycles=duplicate_cycles,
        tick_time_regressions=regressions))

    # 4. broker clock shift recorded and stable (changes only around DST)
    shifts = [(c[0], c[3]) for c in cycles if c[3] is not None]
    # A DST transition moves the broker clock by exactly one hour near a transition
    # date; a stale-quote vote (e.g. 2 -> -1 -> -8 on 30-31 Oct 2026) is not excused
    # merely because it happened in the same week as a DST change.
    changes = [{"at_utc": b[0].isoformat(), "from": a[1], "to": b[1], "near_dst": _near_dst(b[0]),
                "dst_plausible": _near_dst(b[0]) and abs(b[1] - a[1]) == 1}
               for a, b in zip(shifts, shifts[1:]) if a[1] != b[1]]
    missing_shift = sum(1 for c in cycles if c[1] in ("OK", "PARTIAL") and c[3] is None)
    criteria.append(_criterion(
        "clock_shift_stable", "NO_DATA" if not shifts else
        "PASS" if missing_shift == 0 and all(x["dst_plausible"] for x in changes) else "NOT_MET",
        shifts_seen=sorted({s for _, s in shifts}), changes=changes, cycles_without_shift=missing_shift))

    # 5. bid, ask and spread for every observed symbol in every cycle
    quote_clause, quote_params = _since_filter("q.observed_utc", since, now)
    cycle_clause, cycle_params = _since_filter("c.observed_utc", since, now)
    rows = [(datetime.fromisoformat(stamp), status, reason) for stamp, status, reason in db.execute(
        "SELECT q.observed_utc, q.status, q.reason FROM observer_quotes q JOIN observer_cycles c "
        f"ON c.cycle_id=q.cycle_id WHERE c.{COUNTED}{quote_clause}{cycle_clause}", quote_params + cycle_params)]
    rows = [r for r in rows if stage0_session_open(r[0])]
    with_quote = sum(1 for r in rows if r[1] == "OK")
    coverage = with_quote / len(rows) if rows else None
    no_reason = sum(1 for r in rows if r[1] != "OK" and not r[2])
    criteria.append(_criterion(
        "quote_every_cycle", "NO_DATA" if not rows else
        "PASS" if coverage >= MIN_QUOTE_COVERAGE and no_reason == 0 else "NOT_MET",
        required=MIN_QUOTE_COVERAGE, coverage=None if coverage is None else round(coverage, 6),
        symbol_rows=len(rows), missing_without_reason=no_reason))

    # 6. reconnect recoveries
    tests = []
    claimed_recoveries = set()
    if "reconnect_tests" in _tables(db):
        reconnect_clause, reconnect_params = _since_filter("started_utc", since, now)
        for started, method in db.execute(
                f"SELECT started_utc, method FROM reconnect_tests WHERE 1=1{reconnect_clause} ORDER BY started_utc", reconnect_params):
            begin = datetime.fromisoformat(started)
            after = [c for c in cycles if c[0] > begin]
            recovered = next((c for c in after if c[1] == "OK"), None)
            seconds = (recovered[0] - begin).total_seconds() if recovered else None
            recovery_id = recovered[0].isoformat() if recovered else None
            duplicate = recovery_id is not None and recovery_id in claimed_recoveries
            passed = seconds is not None and seconds <= RECOVERY_SECONDS and not duplicate
            if passed:
                claimed_recoveries.add(recovery_id)
            tests.append({"started_utc": begin.isoformat(), "method": method,
                          "recovered_utc": recovered[0].isoformat() if recovered else None,
                          "recovery_seconds": None if seconds is None else int(seconds),
                          "failed_cycles_before_recovery": sum(1 for c in after if recovered and c[0] < recovered[0]),
                          "duplicate_recovery": duplicate, "passed": passed})
    test_recoveries = {t["recovered_utc"] for t in tests if t["passed"]}
    spontaneous = 0
    failed_since = None
    prior = db.execute(
        f"SELECT status FROM observer_cycles WHERE {COUNTED} "
        "AND status IN ('OK','FAILED','NO_MARKET_DATA') AND julianday(observed_utc)<julianday(?) ORDER BY julianday(observed_utc) DESC LIMIT 1",
        (since.isoformat(),)).fetchone() if since else None
    ongoing_before_since = bool(prior and prior[0] in ("FAILED", "NO_MARKET_DATA"))
    for cycle in cycles:
        if cycle[1] in ("FAILED", "NO_MARKET_DATA") and failed_since is None and not ongoing_before_since:
            failed_since = cycle[0]
        elif cycle[1] == "OK":
            if (failed_since is not None and
                    0 < (cycle[0] - failed_since).total_seconds() <= RECOVERY_SECONDS and
                    cycle[0].isoformat() not in test_recoveries):
                spontaneous += 1
            failed_since = None
            ongoing_before_since = False
    passed_tests = sum(1 for t in tests if t["passed"])
    recoveries = passed_tests + spontaneous
    criteria.append(_criterion(
        "reconnect_recoveries", "NO_DATA" if not cycles else
        "PASS" if recoveries >= MIN_RECOVERIES and duplicate_quotes == duplicate_cycles == 0 else "NOT_MET",
        required=MIN_RECOVERIES, recoveries=recoveries, passed_tests=passed_tests,
        spontaneous_recoveries=spontaneous, tests=tests, recovery_limit_seconds=RECOVERY_SECONDS))

    outages = []
    for a, b in zip(cycles, cycles[1:]):
        gap = (b[0] - a[0]).total_seconds()
        if gap > 3 * interval_seconds and stage0_session_open(a[0] + timedelta(seconds=interval_seconds)):
            outages.append({"start_utc": a[0].isoformat(), "end_utc": b[0].isoformat(), "seconds": int(gap)})
    if since is not None and cycles:
        prior_cycle = db.execute(
            f"SELECT observed_utc FROM observer_cycles WHERE {COUNTED} "
            "AND julianday(observed_utc)<julianday(?) "
            "ORDER BY julianday(observed_utc) DESC LIMIT 1", (since.isoformat(),)).fetchone()
        if prior_cycle is not None:
            original_start = datetime.fromisoformat(prior_cycle[0])
            first = cycles[0][0]
            if ((first-original_start).total_seconds() > 3*interval_seconds
                    and first > since and stage0_session_open(since)):
                outages.insert(0, {"start_utc": since.isoformat(), "end_utc": first.isoformat(),
                                   "seconds": int((first-since).total_seconds()),
                                   "started_before_since": True})
    report["observer_outages"] = outages

    # 7. broker ticks stored (or gap recorded) for every completed observed day
    tables = _tables(db)
    observed_days = db.execute(
        f"SELECT DISTINCT symbol, substr(observed_utc,1,10) FROM observer_quotes WHERE status='OK'{clause}", params).fetchall()
    due = [(s, d) for s, d in observed_days
           if datetime.fromisoformat(d).replace(tzinfo=timezone.utc) + timedelta(days=1, hours=2) <= now]
    tick_rows = {}
    if "broker_tick_days" in tables:
        tick_rows = {(s, d): (status, checked, matched) for s, d, status, checked, matched in db.execute(
            "SELECT symbol, day, status, snapshots_checked, snapshots_matched FROM broker_tick_days")}
    if since is not None:
        first_full_day = since.replace(hour=0, minute=0, second=0, microsecond=0)
        if since != first_full_day:
            first_full_day += timedelta(days=1)
        tick_rows = {k: v for k, v in tick_rows.items() if k[1] >= first_full_day.date().isoformat()}
        due = [k for k in due if k[1] >= first_full_day.date().isoformat()]
    settled = [k for k in due if tick_rows.get(k, ("",))[0] in SETTLED_TICK_STATES]
    gap_clause, gap_params = _since_filter("end_utc", since, now)
    gap_count = db.execute(f"SELECT COUNT(*) FROM data_gaps WHERE 1=1{gap_clause}", gap_params).fetchone()[0] if "data_gaps" in tables else 0
    criteria.append(_criterion(
        "broker_ticks_per_day", "NO_DATA" if not due else "PASS" if len(settled) == len(due) else "NOT_MET",
        due_symbol_days=len(due), settled_symbol_days=len(settled),
        stored=sum(1 for k in settled if tick_rows[k][0] != "GAP"),
        gap_days=sum(1 for k in settled if tick_rows[k][0] == "GAP"), gaps_recorded=gap_count))

    # 8. stored ticks reconcile with the observer snapshots
    checked = sum(tick_rows[k][1] for k in settled)
    matched = sum(tick_rows[k][2] for k in settled)
    criteria.append(_criterion(
        "tick_snapshot_reconciliation", "NO_DATA" if not checked else "PASS" if matched == checked else "NOT_MET",
        snapshots_checked=checked, snapshots_matched=matched))

    # 9. zero orders
    orders = sum(int(c[4] or 0) for c in cycles)
    criteria.append(_criterion("zero_orders", "NO_DATA" if not cycles else "PASS" if orders == 0 else "NOT_MET",
                               orders_submitted=orders))
    return _finish(report)


def _finish(report):
    states = [c["status"] for c in report["criteria"]]
    report["verdict"] = ("PASS" if states and all(s == "PASS" for s in states) else
                         "NO_DATA" if all(s == "NO_DATA" for s in states) else "IN_PROGRESS")
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    report["report_sha256"] = hashlib.sha256(canonical.encode("ascii")).hexdigest()
    return report


def _wp14_audit_verdict(findings):
    """Return a fail-closed WP14 verdict; partial evidence is never PASS."""
    statuses = {item["status"] for item in findings}
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if not statuses or statuses == {"NO_DATA"}:
        return "NO_DATA"
    if statuses == {"PASS"}:
        return "PASS"
    return "IN_PROGRESS"


def audit(
    db,
    now: datetime,
    *,
    since: datetime | None = None,
    dataset_dir: str | None = None,
    interval_seconds: int = 60,
    state_dir: str | Path | None = None,
) -> dict:
    """WP14 read-only, deterministic data evidence audit (Tahap 0-1).

    Evaluates:
      - Cycles: status, reason, cycle gaps (outages).
      - Quotes: presence, quote_age, negative spread / inverted quote.
      - Daily clock shift: mixed shifts per day (excluding NO_MARKET_DATA).
      - Tick days: status, server_shift_hours, file sha256.
      - Data gaps: data_gaps table entries.
      - Reconciliation: snapshots_matched / snapshots_checked ratio.
      - Decision shadow: full rows per cycle x symbol for expected modes.
      - Optional dataset manifest: WP8a manifest hash, file sha256, chunk clock_evidence.

    Returns deterministic findings:
      {"check": str, "status": PASS|BLOCKED|NO_DATA, "reason": str|None, "source": {"table"|"file": ..., ...}}
    and summary per symbol x day: "layak" | "terbatas" | "karantina".
    Report contains a canonical report_sha256.
    """
    from pathlib import Path
    import re

    if now.tzinfo is None:
        raise ValueError("aware_clock_required")
    now = now.astimezone(timezone.utc)
    if since is not None:
        if not isinstance(since, datetime) or since.tzinfo is None or since > now:
            raise ValueError("since_requires_aware_datetime_not_in_future")
        since = since.astimezone(timezone.utc)

    tables = _tables(db)
    findings: list[dict] = []
    symbol_day_status: dict[tuple[str, str], str] = {}  # (symbol, day) -> "layak" | "terbatas" | "karantina"

    def _mark_symbol_day(sym: str, d: str, status: str):
        key = (sym, d)
        current = symbol_day_status.get(key, "layak")
        priority = {"karantina": 3, "terbatas": 2, "layak": 1}
        if priority.get(status, 1) > priority.get(current, 1):
            symbol_day_status[key] = status

    # 1. Base ledger presence
    if not {"observer_cycles", "observer_quotes"} <= tables:
        findings.append({
            "check": "ledger_present",
            "status": "NO_DATA",
            "reason": "OBSERVATION_LEDGER_MISSING",
            "source": {"table": "sqlite_master", "key": "observer_cycles"},
        })
        report = {
            "schema_version": 1,
            "stage": "WP14_DATA_EVIDENCE_AUDIT",
            "as_of_utc": now.isoformat(),
            "since_utc": since.isoformat() if since is not None else None,
            "dataset_dir": str(dataset_dir) if dataset_dir is not None else None,
            "live_execution_authorized": False,
            "findings": findings,
            "symbol_day_summary": {},
            "verdict": "NO_DATA",
        }
        canonical_str = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        report["report_sha256"] = hashlib.sha256(canonical_str.encode("ascii")).hexdigest()
        return report

    clause_cycles, params_cycles = _since_filter("observed_utc", since, now)

    # Fetch all cycles in window
    cycle_rows = db.execute(
        f"SELECT cycle_id, observed_utc, status, reason, clock_shift_hours, orders_submitted "
        f"FROM observer_cycles WHERE {COUNTED}{clause_cycles} ORDER BY observed_utc",
        params_cycles,
    ).fetchall()

    if not cycle_rows:
        findings.append({
            "check": "cycles_recorded",
            "status": "NO_DATA",
            "reason": "NO_CYCLES_IN_WINDOW",
            "source": {"table": "observer_cycles", "key": "observed_utc"},
        })

    # Group cycles by cycle_id
    cycles_by_id = {row[0]: row for row in cycle_rows}
    cycle_times = [datetime.fromisoformat(row[1]) for row in cycle_rows]

    # Audit cycle failures and reasons
    for cid, obs_utc, c_status, c_reason, shift, orders in cycle_rows:
        day_str = obs_utc[:10]
        if c_status != "OK":
            if not c_reason:
                findings.append({
                    "check": "cycle_failure_reason",
                    "status": "BLOCKED",
                    "reason": "CYCLE_FAILURE_WITHOUT_REASON",
                    "source": {"table": "observer_cycles", "key": cid},
                })
            else:
                findings.append({
                    "check": "cycle_status",
                    "status": "BLOCKED" if c_status == "FAILED" else "PASS",
                    "reason": c_reason,
                    "source": {"table": "observer_cycles", "key": cid},
                })

    # Cycle outages / gaps (gaps between cycles > 3 * interval_seconds in session)
    outages = []
    for a, b in zip(cycle_times, cycle_times[1:]):
        gap_sec = (b - a).total_seconds()
        if gap_sec > 3 * interval_seconds and stage0_session_open(a + timedelta(seconds=interval_seconds)):
            outages.append((a.isoformat(), b.isoformat(), int(gap_sec)))

    for start_gap, end_gap, gap_sec in outages:
        findings.append({
            "check": "cycle_continuity",
            "status": "BLOCKED",
            "reason": f"CYCLE_GAP_EXCEEDED_{gap_sec}S",
            "source": {"table": "observer_cycles", "key": f"{start_gap}/{end_gap}"},
        })

    # 2. Daily Clock Shift Check: mixed clock shift per day except when status == 'NO_MARKET_DATA'
    # Group non-null shift values per day
    shifts_per_day: dict[str, set[float]] = {}
    for cid, obs_utc, c_status, c_reason, shift, orders in cycle_rows:
        if c_status == "NO_MARKET_DATA":
            continue
        if shift is not None:
            shifts_per_day.setdefault(obs_utc[:10], set()).add(float(shift))

    for day_str, shifts in sorted(shifts_per_day.items()):
        if len(shifts) > 1:
            findings.append({
                "check": "daily_clock_shift_uniform",
                "status": "BLOCKED",
                "reason": f"MIXED_DAILY_CLOCK_SHIFTS_{sorted(shifts)}",
                "source": {"table": "observer_cycles", "key": day_str},
            })
            # Mark all symbols on this day as quarantined
            # We will mark symbols after fetching quotes
        else:
            findings.append({
                "check": "daily_clock_shift_uniform",
                "status": "PASS",
                "reason": None,
                "source": {"table": "observer_cycles", "key": day_str},
            })

    mixed_shift_days = {d for d, s in shifts_per_day.items() if len(s) > 1}

    # 3. Quotes Audit: presence, age, negative spread / inverted quote
    clause_quotes, params_quotes = _since_filter("observed_utc", since, now)
    quote_rows = db.execute(
        f"SELECT cycle_id, symbol, observed_utc, tick_epoch, bid, ask, spread, quote_age_seconds, status, reason "
        f"FROM observer_quotes WHERE 1=1{clause_quotes} ORDER BY observed_utc, symbol",
        params_quotes,
    ).fetchall()

    if not quote_rows and cycle_rows:
        findings.append({
            "check": "quotes_recorded",
            "status": "NO_DATA",
            "reason": "NO_QUOTES_IN_WINDOW",
            "source": {"table": "observer_quotes", "key": "observed_utc"},
        })

    MAX_ALLOWED_QUOTE_AGE_SECONDS = 300.0

    all_symbols = set()
    all_symbol_days = set()

    for cid, symbol, obs_utc, tick_epoch, bid, ask, spread, quote_age, q_status, q_reason in quote_rows:
        day_str = obs_utc[:10]
        key_id = f"{cid}:{symbol}"
        all_symbols.add(symbol)
        all_symbol_days.add((symbol, day_str))

        if day_str in mixed_shift_days:
            _mark_symbol_day(symbol, day_str, "karantina")

        if q_status != "OK":
            findings.append({
                "check": "quote_status",
                "status": "BLOCKED",
                "reason": q_reason or "QUOTE_NOT_OK",
                "source": {"table": "observer_quotes", "key": key_id},
            })
            _mark_symbol_day(symbol, day_str, "terbatas")
            continue

        # Inverted quote or negative spread
        is_negative_spread = False
        if bid is not None and ask is not None and (ask < bid or (spread is not None and spread < 0)):
            is_negative_spread = True
            findings.append({
                "check": "quote_spread_non_negative",
                "status": "BLOCKED",
                "reason": f"NEGATIVE_SPREAD_{spread}_BID_{bid}_ASK_{ask}",
                "source": {"table": "observer_quotes", "key": key_id},
            })
            _mark_symbol_day(symbol, day_str, "karantina")

        # Quote age excessive
        if quote_age is not None and quote_age > MAX_ALLOWED_QUOTE_AGE_SECONDS:
            findings.append({
                "check": "quote_freshness",
                "status": "BLOCKED",
                "reason": f"STALE_QUOTE_AGE_{quote_age}S",
                "source": {"table": "observer_quotes", "key": key_id},
            })
            _mark_symbol_day(symbol, day_str, "terbatas")

        if not is_negative_spread and (quote_age is None or quote_age <= MAX_ALLOWED_QUOTE_AGE_SECONDS):
            _mark_symbol_day(symbol, day_str, "layak")

    # 4. Tick Days Audit: status, server_shift_hours, file sha256
    if "broker_tick_days" in tables:
        has_server_shift = "server_shift_hours" in {row[1] for row in db.execute("PRAGMA table_info(broker_tick_days)")}
        shift_col = "server_shift_hours" if has_server_shift else "NULL"
        tick_day_rows = db.execute(
            f"SELECT symbol, day, status, sha256, file, snapshots_checked, snapshots_matched, {shift_col} "
            "FROM broker_tick_days ORDER BY day, symbol"
        ).fetchall()

        for symbol, day_str, t_status, t_sha256, t_file, sn_checked, sn_matched, s_shift in tick_day_rows:
            day_moment = datetime.fromisoformat(day_str).replace(tzinfo=timezone.utc)
            if since is not None and day_moment < since.replace(hour=0, minute=0, second=0, microsecond=0):
                continue
            if day_moment > now:
                continue

            all_symbols.add(symbol)
            all_symbol_days.add((symbol, day_str))
            key_id = f"{symbol}:{day_str}"

            # Check status
            if t_status not in SETTLED_TICK_STATES:
                findings.append({
                    "check": "tick_day_settled",
                    "status": "BLOCKED",
                    "reason": f"TICK_DAY_STATUS_{t_status}",
                    "source": {"table": "broker_tick_days", "key": key_id},
                })
                _mark_symbol_day(symbol, day_str, "terbatas")
            else:
                findings.append({
                    "check": "tick_day_settled",
                    "status": "PASS",
                    "reason": None,
                    "source": {"table": "broker_tick_days", "key": key_id},
                })

            # Check server_shift_hours
            if s_shift is None and t_status != "GAP":
                findings.append({
                    "check": "tick_day_server_shift",
                    "status": "BLOCKED",
                    "reason": "MISSING_SERVER_SHIFT_HOURS",
                    "source": {"table": "broker_tick_days", "key": key_id},
                })
                _mark_symbol_day(symbol, day_str, "karantina")
            elif s_shift is not None:
                findings.append({
                    "check": "tick_day_server_shift",
                    "status": "PASS",
                    "reason": None,
                    "source": {"table": "broker_tick_days", "key": key_id},
                })

            # Check tick file hash if file exists on disk
            if t_file and t_status != "GAP":
                f_path = Path(t_file)
                # The ledger stores tick files relative to the observer state directory.
                if not f_path.is_absolute() and state_dir is not None:
                    f_path = Path(state_dir) / f_path
                if f_path.is_file() and not t_sha256:
                    findings.append({
                        "check": "tick_file_hash",
                        "status": "BLOCKED",
                        "reason": "TICK_FILE_HASH_NOT_RECORDED",
                        "source": {"table": "broker_tick_days", "key": key_id},
                    })
                    _mark_symbol_day(symbol, day_str, "karantina")
                elif f_path.is_file():
                    with f_path.open("rb") as f_obj:
                        calc_sha = hashlib.file_digest(f_obj, "sha256").hexdigest()
                    if calc_sha != t_sha256:
                        findings.append({
                            "check": "tick_file_hash",
                            "status": "BLOCKED",
                            "reason": f"TICK_FILE_HASH_MISMATCH_{calc_sha}_EXPECTED_{t_sha256}",
                            "source": {"file": str(f_path), "sha256": calc_sha},
                        })
                        _mark_symbol_day(symbol, day_str, "karantina")
                    else:
                        findings.append({
                            "check": "tick_file_hash",
                            "status": "PASS",
                            "reason": None,
                            "source": {"file": str(f_path), "sha256": calc_sha},
                        })
                elif t_sha256:
                    findings.append({
                        "check": "tick_file_hash",
                        "status": "NO_DATA",
                        "reason": f"TICK_FILE_NOT_FOUND_ON_DISK_{t_file}",
                        "source": {"table": "broker_tick_days", "key": key_id},
                    })

            # Reconciliation ratio
            if sn_checked > 0:
                if sn_matched == sn_checked:
                    findings.append({
                        "check": "tick_snapshot_reconciliation",
                        "status": "PASS",
                        "reason": None,
                        "source": {"table": "broker_tick_days", "key": key_id},
                    })
                else:
                    findings.append({
                        "check": "tick_snapshot_reconciliation",
                        "status": "BLOCKED",
                        "reason": f"RECONCILIATION_MISMATCH_MATCHED_{sn_matched}_CHECKED_{sn_checked}",
                        "source": {"table": "broker_tick_days", "key": key_id},
                    })
                    _mark_symbol_day(symbol, day_str, "karantina")
            else:
                findings.append({
                    "check": "tick_snapshot_reconciliation",
                    "status": "NO_DATA",
                    "reason": "NO_SNAPSHOTS_CHECKED",
                    "source": {"table": "broker_tick_days", "key": key_id},
                })
    else:
        findings.append({
            "check": "broker_tick_days_table",
            "status": "NO_DATA",
            "reason": "BROKER_TICK_DAYS_TABLE_MISSING",
            "source": {"table": "sqlite_master", "key": "broker_tick_days"},
        })

    # 5. Data Gaps Audit
    if "data_gaps" in tables:
        gap_clause, gap_params = _since_filter("end_utc", since, now)
        gap_rows = db.execute(
            f"SELECT stream, symbol, start_utc, end_utc, reason FROM data_gaps WHERE 1=1{gap_clause} "
            "ORDER BY start_utc",
            gap_params,
        ).fetchall()
        for stream, sym, g_start, g_end, g_reason in gap_rows:
            day_str = g_start[:10]
            findings.append({
                "check": "data_gap_recorded",
                "status": "BLOCKED",
                "reason": f"DATA_GAP_{stream}_{g_reason}",
                "source": {"table": "data_gaps", "key": f"{stream}:{sym or '*'}:{g_start}:{g_end}"},
            })
            if sym:
                _mark_symbol_day(sym, day_str, "terbatas")
    else:
        findings.append({
            "check": "data_gaps_table",
            "status": "NO_DATA",
            "reason": "DATA_GAPS_TABLE_MISSING",
            "source": {"table": "sqlite_master", "key": "data_gaps"},
        })

    # 6. Decision Shadow Completeness Audit
    # Per cycle x symbol, check whether decision_shadow has both modes: legacy_fail_closed and measured_inputs
    if "decision_shadow" in tables:
        from katarina.intelligence.cognition.decision_inputs import VALID_MODES

        # Get all (cycle_id, symbol) observed in quotes for cycles in window
        quotes_by_cycle = {}
        for row in quote_rows:
            quotes_by_cycle.setdefault(row[0], set()).add(row[1])

        # Get all decision_shadow entries
        shadow_clause, shadow_params = _since_filter("c.observed_utc", since, now)
        shadow_rows = db.execute(
            "SELECT d.cycle_id, d.symbol, d.mode, d.action, d.conditional_side "
            "FROM decision_shadow d JOIN observer_cycles c ON c.cycle_id=d.cycle_id "
            f"WHERE {COUNTED}{shadow_clause} ORDER BY d.cycle_id, d.symbol, d.mode",
            shadow_params,
        ).fetchall()

        shadow_by_cycle_sym = {}
        for cid, sym, mode, act, side in shadow_rows:
            shadow_by_cycle_sym.setdefault((cid, sym), set()).add(mode)

        # Check completeness for each cycle with status OK
        for cid, c_row in cycles_by_id.items():
            if c_row[2] != "OK":
                continue  # only completed/OK cycles expect shadow records
            obs_utc = c_row[1]
            day_str = obs_utc[:10]
            syms_in_cycle = quotes_by_cycle.get(cid, set())
            for sym in sorted(syms_in_cycle):
                modes_present = shadow_by_cycle_sym.get((cid, sym), set())
                missing_modes = sorted(VALID_MODES - modes_present)
                key_id = f"{cid}:{sym}"
                if missing_modes:
                    findings.append({
                        "check": "decision_shadow_completeness",
                        "status": "BLOCKED",
                        "reason": f"MISSING_SHADOW_MODES_{missing_modes}",
                        "source": {"table": "decision_shadow", "key": key_id},
                    })
                    _mark_symbol_day(sym, day_str, "terbatas")
                else:
                    findings.append({
                        "check": "decision_shadow_completeness",
                        "status": "PASS",
                        "reason": None,
                        "source": {"table": "decision_shadow", "key": key_id},
                    })
    else:
        findings.append({
            "check": "decision_shadow_table",
            "status": "NO_DATA",
            "reason": "DECISION_SHADOW_TABLE_MISSING",
            "source": {"table": "sqlite_master", "key": "decision_shadow"},
        })

    # 7. Optional Dataset Manifest Check (WP8a dataset DIR)
    if dataset_dir is not None:
        d_path = Path(dataset_dir)
        manifest_path = d_path / "manifest.json"
        if not manifest_path.is_file():
            findings.append({
                "check": "dataset_manifest_exists",
                "status": "BLOCKED",
                "reason": "MANIFEST_FILE_NOT_FOUND",
                "source": {"file": str(manifest_path), "sha256": ""},
            })
        else:
            try:
                manifest_text = manifest_path.read_text(encoding="utf-8")
                manifest_data = json.loads(manifest_text)
                expected_sha = manifest_data.get("manifest_sha256")
                body = {k: v for k, v in manifest_data.items() if k != "manifest_sha256"}
                canonical_manifest = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                calc_manifest_sha = hashlib.sha256(canonical_manifest.encode("utf-8")).hexdigest()

                if calc_manifest_sha != expected_sha:
                    findings.append({
                        "check": "dataset_manifest_hash",
                        "status": "BLOCKED",
                        "reason": f"MANIFEST_HASH_MISMATCH_{calc_manifest_sha}_EXPECTED_{expected_sha}",
                        "source": {"file": str(manifest_path), "sha256": calc_manifest_sha},
                    })
                else:
                    findings.append({
                        "check": "dataset_manifest_hash",
                        "status": "PASS",
                        "reason": None,
                        "source": {"file": str(manifest_path), "sha256": calc_manifest_sha},
                    })

                # Check files and clock_evidence in manifest
                files = manifest_data.get("files", {})
                for f_rel, meta in sorted(files.items()):
                    f_file_path = d_path / f_rel
                    f_expected_sha = meta.get("sha256")
                    if not f_file_path.is_file():
                        findings.append({
                            "check": "dataset_file_exists",
                            "status": "BLOCKED",
                            "reason": f"DATASET_FILE_MISSING_{f_rel}",
                            "source": {"file": str(f_file_path), "sha256": ""},
                        })
                    else:
                        with f_file_path.open("rb") as f_in:
                            f_sha = hashlib.file_digest(f_in, "sha256").hexdigest()
                        if f_sha != f_expected_sha:
                            findings.append({
                                "check": "dataset_file_hash",
                                "status": "BLOCKED",
                                "reason": f"FILE_HASH_MISMATCH_{f_sha}_EXPECTED_{f_expected_sha}",
                                "source": {"file": str(f_file_path), "sha256": f_sha},
                            })
                        else:
                            findings.append({
                                "check": "dataset_file_hash",
                                "status": "PASS",
                                "reason": None,
                                "source": {"file": str(f_file_path), "sha256": f_sha},
                            })

                    # Verify clock_evidence
                    clock_evidence = meta.get("clock_evidence", [])
                    if not clock_evidence:
                        findings.append({
                            "check": "dataset_clock_evidence",
                            "status": "BLOCKED",
                            "reason": f"CLOCK_EVIDENCE_MISSING_FOR_{f_rel}",
                            "source": {"file": str(f_file_path), "sha256": f_expected_sha or ""},
                        })
                    else:
                        evidence_valid = True
                        for chunk in clock_evidence:
                            shift = chunk.get("shift_hours")
                            src_sha = chunk.get("source_sha256")
                            time_basis = chunk.get("time_basis")
                            if (type(shift) is not int or not -12 <= shift <= 14
                                    or time_basis != "INDEPENDENT_UTC"
                                    or not isinstance(src_sha, str)
                                    or not re.fullmatch(r"[a-fA-F0-9]{64}", src_sha)):
                                evidence_valid = False
                                break
                        if not evidence_valid:
                            findings.append({
                                "check": "dataset_clock_evidence",
                                "status": "BLOCKED",
                                "reason": f"INVALID_CLOCK_EVIDENCE_IN_{f_rel}",
                                "source": {"file": str(f_file_path), "sha256": f_expected_sha or ""},
                            })
                        else:
                            findings.append({
                                "check": "dataset_clock_evidence",
                                "status": "PASS",
                                "reason": None,
                                "source": {"file": str(f_file_path), "sha256": f_expected_sha or ""},
                            })
            except Exception as exc:
                findings.append({
                    "check": "dataset_manifest_readable",
                    "status": "BLOCKED",
                    "reason": f"MANIFEST_READ_ERROR_{type(exc).__name__}",
                    "source": {"file": str(manifest_path), "sha256": ""},
                })

    # Build summary per symbol x day: "layak" | "terbatas" | "karantina"
    summary_by_symbol_day = {}
    for (sym, d) in sorted(all_symbol_days):
        label = symbol_day_status.get((sym, d), "layak")
        summary_by_symbol_day[f"{sym}:{d}"] = label

    # Overall verdict: only an entirely PASS set may pass.
    overall_verdict = _wp14_audit_verdict(findings)

    report = {
        "schema_version": 1,
        "stage": "WP14_DATA_EVIDENCE_AUDIT",
        "as_of_utc": now.isoformat(),
        "since_utc": since.isoformat() if since is not None else None,
        "dataset_dir": str(dataset_dir) if dataset_dir is not None else None,
        "live_execution_authorized": False,
        "findings": sorted(findings, key=lambda x: (x["check"], x["status"], json.dumps(x["source"], sort_keys=True))),
        "symbol_day_summary": summary_by_symbol_day,
        "verdict": overall_verdict,
    }
    canonical_str = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    report["report_sha256"] = hashlib.sha256(canonical_str.encode("ascii")).hexdigest()
    return report
