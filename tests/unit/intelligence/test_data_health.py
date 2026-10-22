import sqlite3
import unittest
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


if __name__ == "__main__":
    unittest.main()
