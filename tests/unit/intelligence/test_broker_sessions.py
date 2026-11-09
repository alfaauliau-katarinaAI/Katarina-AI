"""D9 synthetic evidence tests; these do not certify any real broker dates/DST."""
import copy
from datetime import date, datetime, timedelta, timezone
import sqlite3
import unittest

from katarina.intelligence.operations.broker_sessions import BrokerSessions, preview
from katarina.intelligence.operations import data_health, observation_ledger

U = timezone.utc


def fixture():
    def week(start, end):
        return {str(d): [[start, end]] if d < 5 else [] for d in range(7)}
    schedule = {
        "schema_version": 1, "broker_server_sha256": "a" * 64, "source_sha256": "b" * 64,
        "captured_at_utc": "2026-01-01T00:00:00Z", "valid_from_utc": "2026-01-01T00:00:00Z",
        "valid_until_utc": "2027-01-01T00:00:00Z",
        "verified_broker_dates": [(date(2026, 1, 1) + timedelta(days=d)).isoformat() for d in range(365)],
        "symbols": {
            "XAUUSD.vx": {"quote": week(3600, 86100), "trade": week(3900, 86100)},
            "NAS100.vx": {"quote": week(3600, 86400), "trade": week(3900, 86400)},
            "EURUSD.vx": {"quote": week(0, 86100), "trade": week(300, 86100)},
        },
    }
    clock = {"schema_version": 1, "broker_server_sha256": "a" * 64, "intervals": [{
        "start_utc": "2026-01-01T00:00:00Z", "end_utc": "2027-01-01T00:00:00Z",
        "offset_seconds": 7200, "reason": "LIVE_FEED_CLOCK_VERIFIED", "evidence_sha256": "c" * 64}]}
    return schedule, clock


def classify(policy, iso, symbol="XAUUSD.vx", **kwargs):
    return policy.classify(datetime.fromisoformat(iso), symbol, observed_shift_hours=kwargs.pop("shift", 2),
                           **kwargs)["state"]


class BrokerSessionTests(unittest.TestCase):
    def test_quote_trade_and_half_open_reopening(self):
        policy = BrokerSessions(*fixture())
        self.assertEqual(classify(policy, "2026-11-09T22:59:59.999999Z"), "CLOSED")
        self.assertEqual(classify(policy, "2026-11-09T23:00:00Z"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-09T23:00:00Z", kind="trade"), "CLOSED")
        self.assertEqual(classify(policy, "2026-11-09T23:04:59Z", kind="trade"), "CLOSED")
        self.assertEqual(classify(policy, "2026-11-09T23:05:00Z", kind="trade"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-09T21:54:59Z"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-09T21:55:00Z"), "CLOSED")

    def test_24_hour_endpoint_and_fx_still_open_when_cfd_closed(self):
        policy = BrokerSessions(*fixture())
        self.assertEqual(classify(policy, "2026-11-09T21:59:59Z", "NAS100.vx"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-09T22:00:00Z", "NAS100.vx"), "CLOSED")
        self.assertEqual(classify(policy, "2026-11-09T22:30:00Z", "EURUSD.vx"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-09T22:30:00Z"), "CLOSED")

    def test_weekly_open_uses_broker_date_not_utc_weekday(self):
        policy = BrokerSessions(*fixture())
        self.assertEqual(classify(policy, "2026-11-08T22:00:00Z", "EURUSD.vx"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-08T22:59:59Z"), "CLOSED")
        self.assertEqual(classify(policy, "2026-11-08T23:00:00Z"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-06T23:00:00Z"), "CLOSED")

    def test_verified_overnight_carry_when_next_day_schedule_unavailable(self):
        schedule, clock = fixture()
        schedule["symbols"]["XAUUSD.vx"]["quote"]["4"] = [[82800, 90000]]
        schedule["symbols"]["XAUUSD.vx"]["quote"]["5"] = None
        policy = BrokerSessions(schedule, clock)
        self.assertEqual(classify(policy, "2026-11-06T22:30:00Z"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-06T23:00:00Z"), "UNVERIFIED")

    def test_missing_evidence_never_means_closed(self):
        schedule, clock = fixture()
        cases = []
        for key in ("valid_from_utc", "valid_until_utc"):
            changed = copy.deepcopy(schedule); changed[key] = None
            cases.append((changed, clock))
        changed = copy.deepcopy(schedule); changed["verified_broker_dates"] = []
        cases.append((changed, clock))
        changed = copy.deepcopy(schedule); changed["symbols"]["XAUUSD.vx"]["quote"]["1"] = None
        cases.append((changed, clock))
        changed_clock = copy.deepcopy(clock); changed_clock["intervals"] = []
        cases.append((schedule, changed_clock))
        changed_clock = copy.deepcopy(clock); changed_clock["broker_server_sha256"] = "d" * 64
        cases.append((schedule, changed_clock))
        for s, c in cases:
            with self.subTest(schedule=s, clock=c):
                self.assertEqual(classify(BrokerSessions(s, c), "2026-11-09T22:30:00Z"), "UNVERIFIED")
        policy = BrokerSessions(schedule, clock)
        self.assertEqual(classify(policy, "2026-11-09T22:30:00Z", shift=None), "UNVERIFIED")
        self.assertEqual(classify(policy, "2026-11-09T22:30:00Z", shift=3), "UNVERIFIED")
        self.assertEqual(classify(policy, "2026-11-09T22:30:00Z", "UNKNOWN.vx"), "UNVERIFIED")

    def test_capture_validity_and_clock_windows_are_not_extrapolated(self):
        schedule, clock = fixture()
        schedule["captured_at_utc"] = schedule["valid_from_utc"] = "2026-11-09T16:00:00Z"
        schedule["valid_until_utc"] = "2026-11-10T00:00:00Z"
        clock["intervals"][0]["start_utc"] = "2026-11-09T16:00:00Z"
        clock["intervals"][0]["end_utc"] = "2026-11-09T23:30:00Z"
        policy = BrokerSessions(schedule, clock)
        self.assertEqual(classify(policy, "2026-11-04T22:30:00Z"), "UNVERIFIED")
        self.assertEqual(classify(policy, "2026-11-09T15:59:59Z"), "UNVERIFIED")
        self.assertEqual(classify(policy, "2026-11-09T16:00:00Z"), "OPEN")
        self.assertEqual(classify(policy, "2026-11-09T23:30:00Z"), "UNVERIFIED")
        self.assertEqual(classify(policy, "2026-11-10T00:00:00Z"), "UNVERIFIED")

    def test_dst_requires_explicit_piecewise_offset_proof_for_each_transition(self):
        # US/EU transitions differ. These invented proof windows test mapping;
        # they do not assert the real broker follows either calendar.
        for boundary in ("2026-03-08T07:00:00Z", "2026-03-29T01:00:00Z",
                         "2026-10-25T01:00:00Z", "2026-11-01T06:00:00Z"):
            for before, after in ((7200, 10800), (10800, 7200)):
                with self.subTest(boundary=boundary, before=before):
                    schedule, clock = fixture()
                    # Sunday is explicitly open in this synthetic fixture.
                    schedule["symbols"]["XAUUSD.vx"]["quote"]["6"] = [[0, 86400]]
                    first = clock["intervals"][0]; first["end_utc"] = boundary; first["offset_seconds"] = before
                    second = copy.deepcopy(first); second["start_utc"] = boundary
                    second["end_utc"] = "2027-01-01T00:00:00Z"; second["offset_seconds"] = after
                    clock["intervals"].append(second)
                    policy = BrokerSessions(schedule, clock)
                    moment = datetime.fromisoformat(boundary)
                    self.assertEqual(policy.classify(moment-timedelta(microseconds=1), "XAUUSD.vx",
                                                     observed_shift_hours=before/3600)["state"], "OPEN")
                    self.assertEqual(classify(policy, boundary, shift=after/3600), "OPEN")
                    self.assertEqual(classify(policy, boundary, shift=before/3600), "UNVERIFIED")
                    clock["intervals"].pop()
                    self.assertEqual(classify(BrokerSessions(schedule, clock), boundary,
                                              shift=after/3600), "UNVERIFIED")

    def test_holiday_and_overnight_need_explicit_date_evidence(self):
        schedule, clock = fixture()
        schedule["symbols"]["XAUUSD.vx"]["quote"]["4"] = [[82800, 90000]]
        self.assertEqual(classify(BrokerSessions(schedule, clock), "2026-11-06T22:30:00Z"), "OPEN")
        schedule["verified_broker_dates"].remove("2026-11-06")
        self.assertEqual(classify(BrokerSessions(schedule, clock), "2026-11-06T22:30:00Z"), "UNVERIFIED")
        schedule["verified_broker_dates"].remove("2026-11-26")
        self.assertEqual(classify(BrokerSessions(schedule, clock), "2026-11-26T20:30:00Z"), "UNVERIFIED")

    def test_invalid_interval_clock_provenance_and_naive_time_are_rejected(self):
        schedule, clock = fixture()
        for intervals in ([[0, 0]], [[0, 86401], [3600, 7200]], [[True, 86400]], [[-1, 50]]):
            s = copy.deepcopy(schedule); s["symbols"]["XAUUSD.vx"]["quote"]["0"] = intervals
            with self.subTest(intervals=intervals), self.assertRaises(ValueError):
                BrokerSessions(s, clock)
        c = copy.deepcopy(clock); c["intervals"].append(c["intervals"][0])
        with self.assertRaisesRegex(ValueError, "D9_CLOCK_INTERVAL_OVERLAP"):
            BrokerSessions(schedule, c)
        c = copy.deepcopy(clock); c["intervals"][0]["reason"] = "DST_PLAUSIBLE"
        with self.assertRaisesRegex(ValueError, "D9_CLOCK_INTERVAL_INVALID"):
            BrokerSessions(schedule, c)
        s = copy.deepcopy(schedule); s["source_sha256"] = "missing"
        with self.assertRaisesRegex(ValueError, "D9_EVIDENCE_HASH_REQUIRED"):
            BrokerSessions(s, clock)
        with self.assertRaises(ValueError):
            BrokerSessions(schedule, clock).classify(datetime(2026, 11, 9), "XAUUSD.vx")


class BrokerSessionLedgerTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        observation_ledger.setup(self.db)
        self.policy = BrokerSessions(*fixture())
        self.required = tuple(self.policy.symbols)

    def tearDown(self):
        self.db.close()

    def cycle(self, stamp, *, missing=(), failed=None, duplicate=False, bad_tick=False):
        moment = datetime.fromisoformat(stamp)
        symbols = self.policy.symbols
        cards = {s: {"sensor_reason": "no_past_broker_bidask_quote"} for s in symbols}
        quotes = {s: (1.0, 1.1, moment.timestamp() + (1 if bad_tick else 0)) for s in symbols if s not in missing}
        cid = observation_ledger.record_snapshot(self.db, observed_utc=moment, clock_shift_hours=2,
                                                  cards=cards, quotes=quotes)
        observation_ledger.close_cycle(self.db, cycle_id=cid, finished_utc=moment,
            status="FAILED" if failed else "PARTIAL" if missing else "OK",
            reason=failed or ("SOME_SYMBOLS_WITHOUT_QUOTE" if missing else None))
        if duplicate:
            # Normal ledger schema forbids duplicates. Simulate an imported,
            # damaged table without that constraint to exercise the reader.
            self.db.execute("ALTER TABLE observer_quotes RENAME TO fixture_quotes")
            self.db.execute("CREATE TABLE observer_quotes AS SELECT * FROM fixture_quotes")
            self.db.execute("INSERT INTO observer_quotes SELECT * FROM fixture_quotes "
                            "WHERE cycle_id=? AND symbol='EURUSD.vx'", (cid,))
        return cid

    def test_closed_cfd_does_not_excuse_open_fx_or_rewrite_official_report(self):
        self.cycle("2026-11-09T22:30:00Z", missing=("XAUUSD.vx", "NAS100.vx"))
        self.cycle("2026-11-09T22:31:00Z", missing=("XAUUSD.vx", "NAS100.vx", "EURUSD.vx"))
        now = datetime(2026, 11, 10, tzinfo=U)
        before = data_health.assess(self.db, now)
        total_changes = self.db.total_changes
        report = preview(self.db, now, self.policy, required_symbols=self.required)
        self.assertEqual(report["cycle_categories"], {"MISSING_OPEN_QUOTES": 1, "QUOTE_READY_ONLY": 1})
        self.assertEqual(self.db.total_changes, total_changes)
        self.assertEqual(data_health.assess(self.db, now), before)
        self.assertEqual(report["official_verdict_effect"], "NONE")
        self.assertIsNone(report["activation_effective_utc"])
        self.assertNotIn("verdict", report)

    def test_in_session_feed_failure_at_empirical_gap_is_not_excluded(self):
        self.cycle("2026-11-09T21:57:00Z", missing=("NAS100.vx",))
        report = preview(self.db, datetime(2026, 11, 10, tzinfo=U), self.policy, required_symbols=self.required)
        self.assertEqual(report["cycle_categories"], {"MISSING_OPEN_QUOTES": 1})
        self.assertEqual(report["symbols"]["NAS100.vx"]["OPEN"], 1)

    def test_connection_clock_and_no_market_data_failures_are_retained(self):
        for minute, reason in enumerate(("LOCAL_CONNECT_FAILED", "STALE_QUOTES", "BROKER_CLOCK_NOT_VERIFIED")):
            self.cycle(f"2026-11-09T21:5{5+minute}:00Z", failed=reason)
        report = preview(self.db, datetime(2026, 11, 10, tzinfo=U), self.policy, required_symbols=self.required)
        self.assertEqual(report["cycle_categories"], {"SYSTEM_FAILURE_RETAINED": 3})

    def test_missing_row_duplicate_and_future_quote_fail_closed(self):
        cid = self.cycle("2026-11-09T22:30:00Z")
        self.db.execute("DELETE FROM observer_quotes WHERE cycle_id=? AND symbol='EURUSD.vx'", (cid,))
        self.cycle("2026-11-09T22:31:00Z", duplicate=True)
        self.cycle("2026-11-09T22:32:00Z", bad_tick=True)
        report = preview(self.db, datetime(2026, 11, 10, tzinfo=U), self.policy, required_symbols=self.required)
        self.assertEqual(report["cycle_categories"], {"MISSING_OPEN_QUOTES": 3})

    def test_utc_equivalent_cutoff_and_as_of_bound_preview(self):
        self.cycle("2026-11-09T20:00:00+00:00")
        self.cycle("2026-11-09T20:01:00+00:00")
        self.cycle("2026-11-09T20:02:00+00:00")
        report = preview(self.db, datetime.fromisoformat("2026-11-09T22:01:00+02:00"), self.policy, required_symbols=self.required,
                         since=datetime.fromisoformat("2026-11-09T22:01:00+02:00"))
        self.assertEqual(report["cycles"], 1)

    def test_reduced_or_expanded_schedule_cannot_hide_missing_required_quotes(self):
        self.cycle("2026-11-09T20:00:00Z", missing=("XAUUSD.vx", "NAS100.vx"))
        now = datetime(2026, 11, 10, tzinfo=U)
        for change in ("remove", "add"):
            schedule, clock = fixture()
            if change == "remove":
                del schedule["symbols"]["XAUUSD.vx"]
                del schedule["symbols"]["NAS100.vx"]
            else:
                schedule["symbols"]["UNKNOWN.vx"] = copy.deepcopy(schedule["symbols"]["EURUSD.vx"])
            with self.subTest(change=change):
                report = preview(self.db, now, BrokerSessions(schedule, clock), required_symbols=self.required)
                self.assertFalse(report["universe_matches"])
                self.assertEqual(report["cycle_categories"], {"UNVERIFIED": 1})
                self.assertEqual(set(report["symbols"]), set(self.required))
                self.assertEqual(report["session_reasons"]["D9_UNIVERSE_MISMATCH"], 1)

    def test_required_universe_is_explicit_nonempty_unique_and_independent_of_schedule(self):
        now = datetime(2026, 11, 10, tzinfo=U)
        with self.assertRaises(TypeError):
            preview(self.db, now, self.policy)
        for required in (None, [], "EURUSD.vx", [""], [False], ["EURUSD.vx", "EURUSD.vx"]):
            with self.subTest(required=required), self.assertRaisesRegex(ValueError, "D9_REQUIRED_UNIVERSE_INVALID"):
                preview(self.db, now, self.policy, required_symbols=required)


if __name__ == "__main__":
    unittest.main()
