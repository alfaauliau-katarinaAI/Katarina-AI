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

from katarina.intelligence.operations.observation_ledger import fx_session_open

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
        if not fx_session_open(moment):
            continue
        total += 1
        point = moment.timestamp()
        index = bisect_right(stamps, point) - 1
        if index >= 0 and point - stamps[index] <= window_seconds:
            covered += 1
    return covered / total if total else 0.0


def _news_pipeline(db, since=None) -> dict:
    """WP3 informational diagnosis, never an exit criterion."""
    stats=dict(cycles_with_news_rows=0, cycles_without_verified_articles=0,
               no_recent_release_cycles=0, retrieval_failed_cycles=0,
               no_recent_release_percent=None, retrieval_failed_percent=None,
               verdict_effect="NONE")
    if not {"observer_news","observer_cycles"} <= _tables(db):
        return stats
    by_cycle={}
    clause, params = _since_filter("c.observed_utc", since)
    for cycle,window,verified,failures_json in db.execute(
            "SELECT n.cycle_id,n.in_window,n.verified,n.failures_json "
            "FROM observer_news n JOIN observer_cycles c ON c.cycle_id=n.cycle_id "
            f"WHERE {COUNTED}{clause} ORDER BY n.cycle_id,n.source", params):
        item=by_cycle.setdefault(cycle,{"window":0,"verified":0,"failure":False})
        item["window"]+=window
        item["verified"]+=verified
        try:
            item["failure"]|=bool(json.loads(failures_json))
        except (TypeError,ValueError):
            item["failure"]=True
    stats["cycles_with_news_rows"]=len(by_cycle)
    absent=[r for r in by_cycle.values() if r["verified"]==0]
    stats["cycles_without_verified_articles"]=len(absent)
    for row in absent:
        if row["failure"]:
            stats["retrieval_failed_cycles"]+=1
        elif row["window"]==0:
            stats["no_recent_release_cycles"]+=1
    if absent:
        denominator=len(absent)
        stats["no_recent_release_percent"]=round(
            100*stats["no_recent_release_cycles"]/denominator,1)
        stats["retrieval_failed_percent"]=round(
            100*stats["retrieval_failed_cycles"]/denominator,1)
    return stats


def _since_filter(column, since):
    # Column names are internal constants; boundary values stay SQL parameters.
    return (f" AND julianday({column}) >= julianday(?)", (since.isoformat(),)) if since else ("", ())


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
    clause, params = _since_filter("observed_utc", since)
    report = {"schema_version": 1, "stage": "TAHAP_0_OBSERVER_DATA", "as_of_utc": now.isoformat(),
              "interval_seconds": interval_seconds,
              "session_rule": "Mon 00:00 - Fri 20:00 UTC, excluding 20:45-21:15 UTC rollover",
              "live_execution_authorized": False, "criteria": []}
    if since is not None:
        report["since_utc"] = since.isoformat()
        report["partial_tick_day_excluded"] = (since.date().isoformat()
            if since != since.replace(hour=0, minute=0, second=0, microsecond=0) else None)
    criteria = report["criteria"]
    report["news_pipeline"] = _news_pipeline(db, since)
    if not {"observer_cycles", "observer_quotes"} <= _tables(db):
        criteria.append(_criterion("ledger_present", "NO_DATA", reason="OBSERVATION_LEDGER_MISSING"))
        return _finish(report)

    cycles = [(datetime.fromisoformat(stamp), status, reason, shift, orders)
              for stamp, status, reason, shift, orders in db.execute(
                  f"SELECT observed_utc, status, reason, clock_shift_hours, orders_submitted "
                  f"FROM observer_cycles WHERE {COUNTED}{clause} ORDER BY observed_utc", params)]
    session = [c for c in cycles if fx_session_open(c[0])]
    report["cycles_total"] = len(cycles)
    report["cycles_in_session"] = len(session)
    report["first_cycle_utc"] = cycles[0][0].isoformat() if cycles else None
    report["last_cycle_utc"] = cycles[-1][0].isoformat() if cycles else None

    # 1. consecutive trading days with near-complete session coverage: a session minute is covered
    #    when a counted cycle happened within the previous 3 intervals (cycle time + idle varies).
    stamps = [c[0].timestamp() for c in cycles]
    streak = best = 0
    covered_days = []
    if cycles:
        day = cycles[0][0].date()
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
    changes = [{"at_utc": b[0].isoformat(), "from": a[1], "to": b[1], "near_dst": _near_dst(b[0])}
               for a, b in zip(shifts, shifts[1:]) if a[1] != b[1]]
    missing_shift = sum(1 for c in cycles if c[1] in ("OK", "PARTIAL") and c[3] is None)
    criteria.append(_criterion(
        "clock_shift_stable", "NO_DATA" if not shifts else
        "PASS" if missing_shift == 0 and all(x["near_dst"] for x in changes) else "NOT_MET",
        shifts_seen=sorted({s for _, s in shifts}), changes=changes, cycles_without_shift=missing_shift))

    # 5. bid, ask and spread for every observed symbol in every cycle
    quote_clause, quote_params = _since_filter("q.observed_utc", since)
    cycle_clause, cycle_params = _since_filter("c.observed_utc", since)
    rows = [(datetime.fromisoformat(stamp), status, reason) for stamp, status, reason in db.execute(
        "SELECT q.observed_utc, q.status, q.reason FROM observer_quotes q JOIN observer_cycles c "
        f"ON c.cycle_id=q.cycle_id WHERE c.{COUNTED}{quote_clause}{cycle_clause}", quote_params + cycle_params)]
    rows = [r for r in rows if fx_session_open(r[0])]
    with_quote = sum(1 for r in rows if r[1] == "OK")
    coverage = with_quote / len(rows) if rows else None
    no_reason = sum(1 for r in rows if r[1] != "OK" and not r[2])
    criteria.append(_criterion(
        "quote_every_cycle", "NO_DATA" if not rows else
        "PASS" if coverage >= MIN_QUOTE_COVERAGE and no_reason == 0 else "NOT_MET",
        required=MIN_QUOTE_COVERAGE, coverage=None if coverage is None else round(coverage, 6),
        symbol_rows=len(rows), missing_without_reason=no_reason))

    # 6. reconnect recoveries: deliberate disconnect tests that recovered on their own within
    #    RECOVERY_SECONDS, plus spontaneous failed stretches followed by an OK cycle.
    tests = []
    claimed_recoveries = set()
    if "reconnect_tests" in _tables(db):
        reconnect_clause, reconnect_params = _since_filter("started_utc", since)
        for started, method in db.execute(f"SELECT started_utc, method FROM reconnect_tests WHERE 1=1{reconnect_clause} ORDER BY started_utc", reconnect_params):
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
    # Time from the FIRST failure, not the last retry; a long outage is not a fast recovery.
    spontaneous = 0
    failed_since = None
    # An outage already in progress at the boundary is not a new fast recovery.
    prior = db.execute(f"SELECT status FROM observer_cycles WHERE {COUNTED} "
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

    # observer outages inside the session (reported, never filled)
    outages = []
    for a, b in zip(cycles, cycles[1:]):
        gap = (b[0] - a[0]).total_seconds()
        if gap > 3 * interval_seconds and fx_session_open(a[0] + timedelta(seconds=interval_seconds)):
            outages.append({"start_utc": a[0].isoformat(), "end_utc": b[0].isoformat(), "seconds": int(gap)})
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
        # Daily aggregates cannot be split honestly using a partial-day boundary.
        first_full_day = since.replace(hour=0, minute=0, second=0, microsecond=0)
        if since != first_full_day:
            first_full_day += timedelta(days=1)
        tick_rows = {k:v for k,v in tick_rows.items() if k[1] >= first_full_day.date().isoformat()}
    settled = [k for k in due if tick_rows.get(k, ("",))[0] in SETTLED_TICK_STATES]
    gap_clause, gap_params = _since_filter("end_utc", since)
    gap_count = db.execute(f"SELECT COUNT(*) FROM data_gaps WHERE 1=1{gap_clause}", gap_params).fetchone()[0] if "data_gaps" in tables else 0
    criteria.append(_criterion(
        "broker_ticks_per_day", "NO_DATA" if not due else "PASS" if len(settled) == len(due) else "NOT_MET",
        due_symbol_days=len(due), settled_symbol_days=len(settled),
        stored=sum(1 for k in settled if tick_rows[k][0] != "GAP"),
        gap_days=sum(1 for k in settled if tick_rows[k][0] == "GAP"), gaps_recorded=gap_count))

    # 8. stored ticks reconcile with the observer snapshots (within one tick size)
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
