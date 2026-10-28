"""WP13 time selection must not authorize evidence from before the boundary."""
from datetime import datetime,timedelta,timezone
import sqlite3
import unittest
from katarina.intelligence.operations import observation_ledger as ledger, data_health
from tests.unit.intelligence.test_data_health import by_name

UTC=timezone.utc
START=datetime(2026,11,9,12,tzinfo=UTC)


class SinceTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close)
        ledger.setup(self.db)

    def cycle(self,when,orders=0):
        key=ledger.record_snapshot(self.db,observed_utc=when,clock_shift_hours=3,
            cards={'EURUSD':{}},quotes={'EURUSD':(1.,1.1,when.timestamp()-1)})
        ledger.close_cycle(self.db,finished_utc=when,cycle_id=key,status='OK',orders_submitted=orders)
        return key

    def test_old_orders_quotes_and_reconnects_do_not_enter_selected_period(self):
        self.cycle(START-timedelta(days=1),orders=1)
        self.cycle(START)
        ledger.record_reconnect_test(self.db,started_utc=START-timedelta(seconds=10),
            method='KILL_TERMINAL',now=START)
        before=self.db.total_changes
        report=data_health.assess(self.db,START+timedelta(days=2),since=START)
        criteria=by_name(report)
        self.assertEqual(report['cycles_total'],1)
        self.assertEqual(report['first_cycle_utc'],START.isoformat())
        self.assertEqual(criteria['zero_orders']['orders_submitted'],0)
        self.assertEqual(criteria['reconnect_recoveries']['tests'],[])
        self.assertEqual(criteria['broker_ticks_per_day']['due_symbol_days'],1)
        self.assertEqual(self.db.total_changes,before)

    def test_partial_day_aggregate_cannot_claim_post_since_reconciliation(self):
        self.cycle(START)
        self.db.execute("INSERT INTO broker_tick_days(symbol,day,status,snapshots_checked,snapshots_matched) VALUES('EURUSD','2026-11-09','STORED',500,500)")
        report=data_health.assess(self.db,START+timedelta(days=2),since=START)
        self.assertEqual(by_name(report)['tick_snapshot_reconciliation']['status'],'NO_DATA')
        self.assertEqual(by_name(report)['broker_ticks_per_day']['status'],'NOT_MET')

    def test_since_none_is_identical_and_invalid_boundaries_rejected(self):
        self.cycle(START)
        now=START+timedelta(hours=1)
        self.assertEqual(data_health.assess(self.db,now),data_health.assess(self.db,now,since=None))
        for since in (START.replace(tzinfo=None),now+timedelta(seconds=1),'2026-11-09'):
            with self.subTest(since=since),self.assertRaises(ValueError):
                data_health.assess(self.db,now,since=since)

    def test_explicit_timezone_selects_the_same_instant(self):
        self.cycle(START)
        now=START+timedelta(days=1)
        self.assertEqual(data_health.assess(self.db,now,since=START),data_health.assess(
            self.db,now,since=START.astimezone(timezone(timedelta(hours=7)))))

    def test_outage_crossing_boundary_is_not_a_new_recovery(self):
        for seconds, status in ((-3600,'FAILED'),(-1,'PARTIAL'),(1,'FAILED'),(2,'OK')):
            key=self.cycle(START+timedelta(seconds=seconds))
            self.db.execute("UPDATE observer_cycles SET status=?,reason='fixture' WHERE cycle_id=?", (status,key))
        report=data_health.assess(self.db,START+timedelta(hours=1),since=START)
        self.assertEqual(by_name(report)['reconnect_recoveries']['spontaneous_recoveries'],0)
