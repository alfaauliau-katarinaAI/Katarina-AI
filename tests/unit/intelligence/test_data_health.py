import sqlite3
import unittest
from unittest.mock import patch
from datetime import date, datetime, timedelta, timezone

from katarina.intelligence.operations import data_health
from katarina.intelligence.operations import observation_ledger as ledger

UTC = timezone.utc


def fill(db, start, days, *, every=300, fail_every=None, shift=3, shift_change=None):
    """Simulate observer cycles every ``every`` seconds across whole days."""
    moment = start
    end = start + timedelta(days=days)
    index = 0
    while moment < end:
        if fail_every and index % fail_every == 0:
            ledger.close_cycle(db, finished_utc=moment, status="FAILED", reason="LOCAL_CONNECT_FAILED")
        else:
            current = shift_change[1] if shift_change and moment >= shift_change[0] else shift
            cycle = ledger.record_snapshot(db, observed_utc=moment, clock_shift_hours=current,
                                           cards={"EURUSD": {}}, quotes={"EURUSD": (1.1, 1.1001, moment.timestamp() - 1)})
            ledger.close_cycle(db, finished_utc=moment, cycle_id=cycle, status="OK")
        moment += timedelta(seconds=every)
        index += 1


def by_name(report):
    return {c["criterion"]: c for c in report["criteria"]}


class DataHealthTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_empty_database_reports_no_data(self):
        report = data_health.assess(self.db, datetime(2026, 10, 22, tzinfo=UTC))
        self.assertEqual(report["verdict"], "NO_DATA")
        self.assertFalse(report["live_execution_authorized"])

    def test_two_weeks_of_clean_cycles_pass_cycle_criteria_but_wait_for_ticks(self):
        start = datetime(2026, 11, 9, tzinfo=UTC)  # Monday, away from DST changes
        fill(self.db, start, 14, every=300, fail_every=400)
        report = data_health.assess(self.db, start + timedelta(days=14, hours=1), interval_seconds=300)
        criteria = by_name(report)
        self.assertEqual(criteria["consecutive_trading_days"]["status"], "PASS")
        self.assertEqual(criteria["consecutive_trading_days"]["best_streak"], 10)
        self.assertEqual(criteria["cycle_success_rate"]["status"], "PASS")
        self.assertEqual(criteria["no_duplicates_monotonic"]["status"], "PASS")
        self.assertEqual(criteria["clock_shift_stable"]["status"], "PASS")
        self.assertEqual(criteria["quote_every_cycle"]["status"], "PASS")
        self.assertEqual(criteria["reconnect_recoveries"]["status"], "PASS")
        self.assertEqual(criteria["zero_orders"]["status"], "PASS")
        self.assertEqual(criteria["broker_ticks_per_day"]["status"], "NOT_MET")
        self.assertEqual(report["verdict"], "IN_PROGRESS")

    def test_cycle_runtime_longer_than_interval_still_covers_the_day(self):
        start = datetime(2026, 11, 9, tzinfo=UTC)
        fill(self.db, start, 1, every=85)
        criteria = by_name(data_health.assess(self.db, start + timedelta(days=1, hours=1), interval_seconds=60))
        self.assertEqual(criteria["consecutive_trading_days"]["covered_days"], ["2026-11-09"])

    def test_long_outage_breaks_day_coverage(self):
        start = datetime(2026, 11, 9, tzinfo=UTC)
        fill(self.db, start, 1, every=60)
        self.db.execute("DELETE FROM observer_cycles WHERE observed_utc BETWEEN '2026-11-09T06' AND '2026-11-09T09'")
        criteria = by_name(data_health.assess(self.db, start + timedelta(days=1, hours=1), interval_seconds=60))
        self.assertEqual(criteria["consecutive_trading_days"]["covered_days"], [])

    def test_recorded_disconnect_tests_count_when_observer_recovers_in_time(self):
        start = datetime(2026, 11, 9, 8, tzinfo=UTC)
        fill(self.db, start, 1, every=60)
        for minutes, method in ((60, "KILL_TERMINAL"), (120, "KILL_TERMINAL_MID_CYCLE"), (180, "KILL_TERMINAL")):
            ledger.record_reconnect_test(self.db, started_utc=start + timedelta(minutes=minutes, seconds=5),
                                         method=method, now=start + timedelta(days=1))
        criteria = by_name(data_health.assess(self.db, start + timedelta(days=1)))
        recon = criteria["reconnect_recoveries"]
        self.assertEqual((recon["status"], recon["passed_tests"]), ("PASS", 3))
        self.assertTrue(all(t["recovery_seconds"] <= 60 for t in recon["tests"]))

    def test_disconnect_without_recovery_does_not_pass(self):
        start = datetime(2026, 11, 9, 8, tzinfo=UTC)
        fill(self.db, start, 0.1, every=60)
        ledger.record_reconnect_test(self.db, started_utc=start + timedelta(hours=3), method="KILL_TERMINAL",
                                     now=start + timedelta(hours=4))
        recon = by_name(data_health.assess(self.db, start + timedelta(hours=4)))["reconnect_recoveries"]
        self.assertEqual(recon["passed_tests"], 0)
        self.assertFalse(recon["tests"][0]["passed"])

    def test_overlapping_test_records_count_one_recovery(self):
        start = datetime(2026, 11, 9, 8, tzinfo=UTC)
        fill(self.db, start, 0.1, every=60)
        for seconds in (5, 10, 15):
            ledger.record_reconnect_test(self.db, started_utc=start + timedelta(seconds=seconds),
                                         method="KILL_TERMINAL", now=start + timedelta(hours=4))
        recon = by_name(data_health.assess(self.db, start + timedelta(hours=4)))["reconnect_recoveries"]
        self.assertEqual(recon["recoveries"], 1)
        self.assertEqual(recon["status"], "NOT_MET")
        self.assertEqual(sum(t["duplicate_recovery"] for t in recon["tests"]), 2)

    def test_long_outage_with_late_retry_is_not_fast_recovery(self):
        start = datetime(2026, 11, 9, 8, tzinfo=UTC)
        for minutes in (0, 59):
            ledger.close_cycle(self.db, finished_utc=start + timedelta(minutes=minutes),
                               status="FAILED", reason="LOCAL_CONNECT_FAILED")
        fill(self.db, start + timedelta(hours=1), 0.01, every=60)
        recon = by_name(data_health.assess(self.db, start + timedelta(hours=2)))["reconnect_recoveries"]
        self.assertEqual(recon["spontaneous_recoveries"], 0)

    def test_reconnect_test_rejects_unknown_method_and_future_start(self):
        now = datetime(2026, 11, 9, tzinfo=UTC)
        with self.assertRaises(ValueError):
            ledger.record_reconnect_test(self.db, started_utc=now, method="PULL_PLUG", now=now)
        with self.assertRaises(ValueError):
            ledger.record_reconnect_test(self.db, started_utc=now + timedelta(hours=1), method="KILL_TERMINAL",
                                         now=now)

    def test_frequent_failures_do_not_meet_success_rate(self):
        start = datetime(2026, 11, 9, tzinfo=UTC)
        fill(self.db, start, 2, every=300, fail_every=10)
        criteria = by_name(data_health.assess(self.db, start + timedelta(days=2), interval_seconds=300))
        self.assertEqual(criteria["cycle_success_rate"]["status"], "NOT_MET")
        self.assertLess(criteria["cycle_success_rate"]["rate"], 0.98)
        self.assertEqual(list(criteria["cycle_success_rate"]["failure_reasons"]), ["LOCAL_CONNECT_FAILED"])

    def test_clock_shift_change_outside_dst_is_flagged(self):
        start = datetime(2026, 11, 16, tzinfo=UTC)
        fill(self.db, start, 2, every=600, shift_change=(start + timedelta(days=1), 2))
        criteria = by_name(data_health.assess(self.db, start + timedelta(days=2), interval_seconds=600))
        self.assertEqual(criteria["clock_shift_stable"]["status"], "NOT_MET")
        self.assertFalse(criteria["clock_shift_stable"]["changes"][0]["near_dst"])

    def test_clock_shift_change_at_us_dst_end_is_accepted(self):
        start = datetime(2026, 10, 29, tzinfo=UTC)
        fill(self.db, start, 5, every=900, shift_change=(datetime(2026, 11, 2, tzinfo=UTC), 2))
        criteria = by_name(data_health.assess(self.db, start + timedelta(days=5), interval_seconds=900))
        self.assertEqual(criteria["clock_shift_stable"]["status"], "PASS")

    def test_dst_transitions_2026(self):
        self.assertEqual(data_health.dst_transitions(2026),
                         [date(2026, 3, 8), date(2026, 3, 29), date(2026, 10, 25), date(2026, 11, 1)])

    def test_report_hash_is_deterministic(self):
        start = datetime(2026, 11, 9, tzinfo=UTC)
        fill(self.db, start, 1, every=900)
        now = start + timedelta(days=1)
        first = data_health.assess(self.db, now, interval_seconds=900)
        second = data_health.assess(self.db, now, interval_seconds=900)
        self.assertEqual(first["report_sha256"], second["report_sha256"])

    def test_orders_fail_the_zero_order_criterion(self):
        when = datetime(2026, 11, 10, 9, tzinfo=UTC)
        cycle = ledger.record_snapshot(self.db, observed_utc=when, clock_shift_hours=2,
                                       cards={"EURUSD": {}}, quotes={"EURUSD": (1.1, 1.1001, when.timestamp())})
        ledger.close_cycle(self.db, finished_utc=when, cycle_id=cycle, status="OK", orders_submitted=1)
        criteria = by_name(data_health.assess(self.db, when + timedelta(hours=1)))
        self.assertEqual(criteria["zero_orders"]["status"], "NOT_MET")

    def test_data_health_exposes_both_rules_with_activation_disabled(self):
        when = datetime(2026, 11, 10, 9, tzinfo=UTC)
        cycle = ledger.record_snapshot(self.db, observed_utc=when, clock_shift_hours=2,
                                       cards={"EURUSD": {}}, quotes={"EURUSD": (1.1, 1.1001, when.timestamp())})
        ledger.close_cycle(self.db, finished_utc=when, cycle_id=cycle, status="OK")
        report = data_health.assess(self.db, when + timedelta(hours=1))
        self.assertIn("20:45-21:15 UTC", report["session_rule"])
        self.assertIn("17:00 America/New_York", report["session_rule"])
        self.assertIsNone(report["rollover_rule_effective_utc"])
        self.assertFalse(report["live_execution_authorized"])

    def test_post_dst_rollover_failure_excluded_only_after_approved_cutoff(self):
        when_open = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
        when_rollover = datetime(2026, 11, 2, 22, 5, tzinfo=UTC)
        cycle = ledger.record_snapshot(self.db, observed_utc=when_open, clock_shift_hours=2,
                                       cards={"EURUSD": {}}, quotes={"EURUSD": (1.1, 1.1001, when_open.timestamp())})
        ledger.close_cycle(self.db, finished_utc=when_open, cycle_id=cycle, status="OK")
        ledger.close_cycle(self.db, finished_utc=when_rollover, status="FAILED", reason="STALE_QUOTES")

        original = data_health.assess(self.db, when_rollover + timedelta(hours=1))
        self.assertEqual(original["cycles_in_session"], 2)
        self.assertEqual(by_name(original)["cycle_success_rate"]["status"], "NOT_MET")

        cutoff = "2026-11-02T00:00:00+00:00"
        with patch.object(ledger, "ROLLOVER_RULE_EFFECTIVE_UTC", cutoff), \
             patch.object(data_health, "ROLLOVER_RULE_EFFECTIVE_UTC", cutoff):
            updated = data_health.assess(self.db, when_rollover + timedelta(hours=1))
        self.assertEqual(updated["cycles_total"], 2)
        self.assertEqual(updated["cycles_in_session"], 1)
        self.assertEqual(by_name(updated)["cycle_success_rate"]["status"], "PASS")
        self.assertEqual(updated["rollover_rule_effective_utc"], cutoff)

    def test_rollover_cutoff_ledger_denominator_nonretroactive(self):
        times = (
            (datetime(2026, 11, 2, 20, 50, tzinfo=UTC), "OK"),
            (datetime(2026, 11, 2, 22, 5, tzinfo=UTC), "FAILED"),
            (datetime(2026, 11, 2, 22, 11, tzinfo=UTC), "FAILED"),
            (datetime(2026, 11, 2, 23, 0, tzinfo=UTC), "OK"),
        )
        for when, state in times:
            if state == "OK":
                cycle = ledger.record_snapshot(self.db, observed_utc=when, clock_shift_hours=2,
                                               cards={"EURUSD": {}}, quotes={"EURUSD": (1.1, 1.1001, when.timestamp())})
                ledger.close_cycle(self.db, finished_utc=when, cycle_id=cycle, status="OK")
            else:
                ledger.close_cycle(self.db, finished_utc=when, status="FAILED", reason="STALE_QUOTES")
        cutoff = "2026-11-02T22:10:00+00:00"
        with patch.object(ledger, "ROLLOVER_RULE_EFFECTIVE_UTC", cutoff), \
             patch.object(data_health, "ROLLOVER_RULE_EFFECTIVE_UTC", cutoff):
            report = data_health.assess(self.db, datetime(2026, 11, 3, tzinfo=UTC))
        self.assertEqual(report["cycles_total"], 4)
        self.assertEqual(report["cycles_in_session"], 2)
        criterion = by_name(report)["cycle_success_rate"]
        self.assertEqual((criterion["ok"], criterion["cycles"]), (1, 2))
        self.assertEqual(criterion["failure_reasons"], {"STALE_QUOTES": 1})
        self.assertFalse(report["live_execution_authorized"])



if __name__ == "__main__":
    unittest.main()
