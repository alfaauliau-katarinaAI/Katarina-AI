import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from katarina.intelligence.operations import observation_ledger as ledger

UTC = timezone.utc


class FakeTicks:
    """MT5 stand-in: deterministic EURUSD ticks every 10 s, optional missing hours."""
    COPY_TICKS_ALL = 1

    def __init__(self, unavailable_hours=(), empty=False):
        self.unavailable_hours = set(unavailable_hours)
        self.empty = empty
        self.calls = 0

    @staticmethod
    def price(msc):
        return round(1.1 + (msc // 10000 % 50) * 0.00001, 5)

    def copy_ticks_range(self, symbol, start, end, flag):
        self.calls += 1
        if start.hour in self.unavailable_hours:
            return None
        if self.empty:
            return []
        first = int(start.timestamp()) * 1000
        rows = []
        for msc in range(first, int(end.timestamp()) * 1000 + 1, 10000):
            bid = self.price(msc)
            rows.append({"time_msc": msc, "bid": bid, "ask": round(bid + 0.00012, 5), "flags": 6})
        return rows

    def symbol_info(self, symbol):
        return SimpleNamespace(point=0.00001, trade_tick_size=0.00001)


def snapshot(db, when, quotes, cards=None, shift=0):
    cards = cards or {symbol: {"action": "WAIT"} for symbol in quotes}
    return ledger.record_snapshot(db, observed_utc=when, clock_shift_hours=shift, cards=cards, quotes=quotes)


class ObservationLedgerTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_wait_cycles_store_bid_ask_spread_and_failures_keep_reason(self):
        when = datetime(2026, 10, 20, 10, 0, 30, tzinfo=UTC)
        cycle = snapshot(self.db, when, {"EURUSD": (1.1, 1.10012, when.timestamp() - 2)},
                         cards={"EURUSD": {"action": "WAIT"},
                                "XAUUSD": {"action": "WAIT", "sensor_reason": "no_past_broker_bidask_quote"}},shift=3)
        rows = self.db.execute("SELECT symbol, status, bid, ask, round(spread,5), reason FROM observer_quotes "
                               "ORDER BY symbol").fetchall()
        self.assertEqual(rows, [("EURUSD", "OK", 1.1, 1.10012, 0.00012, None),
                                ("XAUUSD", "FAILED", None, None, None, "no_past_broker_bidask_quote")])
        ledger.close_cycle(self.db, finished_utc=when + timedelta(seconds=5), cycle_id=cycle,
                           status="PARTIAL", reason="SOME_SYMBOLS_WITHOUT_QUOTE")
        self.assertEqual(self.db.execute("SELECT status, symbols_observed, symbols_with_quote, clock_shift_hours "
                                         "FROM observer_cycles").fetchone(), ("PARTIAL", 2, 1, 3.0))

    def test_duplicate_snapshot_for_same_cycle_is_rejected(self):
        when = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
        snapshot(self.db, when, {"EURUSD": (1.1, 1.1001, when.timestamp())})
        with self.assertRaises(sqlite3.IntegrityError):
            snapshot(self.db, when, {"EURUSD": (1.1, 1.1001, when.timestamp())})
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM observer_quotes").fetchone()[0], 1)

    def test_failed_iteration_without_snapshot_gets_reason_and_superseded_attempts(self):
        when = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
        stale = snapshot(self.db, when, {"EURUSD": (1.1, 1.1001, when.timestamp())})
        later = when + timedelta(seconds=20)
        good = snapshot(self.db, later, {"EURUSD": (1.1, 1.1001, later.timestamp())})
        ledger.close_cycle(self.db, finished_utc=later, cycle_id=good, status="OK")
        ledger.close_cycle(self.db, finished_utc=later + timedelta(minutes=1), status="FAILED",
                           reason="LOCAL_CONNECT_FAILED")
        states = dict(self.db.execute("SELECT cycle_id, status FROM observer_cycles"))
        self.assertEqual(states[stale], "ATTEMPT_FAILED")
        self.assertEqual(states[good], "OK")
        self.assertIn("FAILED", states.values())
        self.assertEqual(self.db.execute("SELECT reason FROM observer_cycles WHERE status='FAILED'").fetchone()[0],
                         "LOCAL_CONNECT_FAILED")

    def test_cycle_status_requires_quote_for_every_symbol(self):
        self.assertEqual(ledger.cycle_status({"observed_symbols": 3, "received_market_data_symbols": 3}), ("OK", None))
        self.assertEqual(ledger.cycle_status({"observed_symbols": 3, "received_market_data_symbols": 2})[0], "PARTIAL")
        self.assertEqual(ledger.cycle_status({"observed_symbols": 3, "received_market_data_symbols": 0})[0],
                         "NO_MARKET_DATA")

    def test_ticks_collected_only_for_completed_observed_days_and_reconciled(self):
        when = datetime(2026, 10, 20, 10, 0, 5, tzinfo=UTC)
        epoch = (int(when.timestamp()) // 10) * 10
        bid = FakeTicks.price(epoch * 1000)
        snapshot(self.db, when, {"EURUSD": (bid, round(bid + 0.00012, 5), float(epoch))})
        mt5 = FakeTicks()
        early = ledger.collect_tick_days(self.db, mt5, self.root, datetime(2026, 10, 21, 1, 0, tzinfo=UTC),server_shift_hours=0)
        self.assertEqual(early["collected"], [])
        self.assertEqual(mt5.calls, 0)
        result = ledger.collect_tick_days(self.db, mt5, self.root, datetime(2026, 10, 21, 3, 0, tzinfo=UTC),server_shift_hours=0)
        self.assertEqual(result["collected"][0]["status"], "STORED")
        row = self.db.execute("SELECT status, ticks, snapshots_checked, snapshots_matched, file, sha256 "
                              "FROM broker_tick_days").fetchone()
        self.assertEqual(row[:4], ("STORED", 8640, 1, 1))
        ticks = ledger.read_ticks(self.root / row[4])
        self.assertEqual(len(ticks), 8640)
        self.assertTrue(all(a[0] < b[0] for a, b in zip(ticks, ticks[1:])))
        again = ledger.collect_tick_days(self.db, mt5, self.root, datetime(2026, 10, 21, 4, 0, tzinfo=UTC),server_shift_hours=0)
        self.assertEqual(again["collected"], [])

    def test_unavailable_hours_are_recorded_as_gaps_not_interpolated(self):
        when = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
        snapshot(self.db, when, {"EURUSD": (1.1, 1.10012, when.timestamp())})
        ledger.collect_tick_days(self.db, FakeTicks(unavailable_hours={4, 5}), self.root,
                                 datetime(2026, 10, 21, 3, 0, tzinfo=UTC),server_shift_hours=0)
        status, ticks = self.db.execute("SELECT status, ticks FROM broker_tick_days").fetchone()
        self.assertEqual((status, ticks), ("STORED_WITH_GAPS", 8640 - 720))
        gaps = self.db.execute("SELECT start_utc, end_utc, reason FROM data_gaps ORDER BY start_utc").fetchall()
        self.assertEqual([g[2] for g in gaps], ["BROKER_HISTORY_UNAVAILABLE"] * 2)
        self.assertEqual(gaps[0][0], "2026-10-20T04:00:00+00:00")

    def test_mismatching_snapshot_is_not_reconciled(self):
        when = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
        snapshot(self.db, when, {"EURUSD": (1.2, 1.20012, when.timestamp())})
        ledger.collect_tick_days(self.db, FakeTicks(), self.root, datetime(2026, 10, 21, 3, 0, tzinfo=UTC),server_shift_hours=0)
        self.assertEqual(self.db.execute("SELECT snapshots_checked, snapshots_matched FROM broker_tick_days")
                         .fetchone(), (1, 0))

    def test_unavailable_history_retries_then_records_whole_day_gap(self):
        when = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
        snapshot(self.db, when, {"EURUSD": (1.1, 1.10012, when.timestamp())})
        mt5 = FakeTicks(unavailable_hours=set(range(24)))
        clock = datetime(2026, 10, 21, 3, 0, tzinfo=UTC)
        for attempt in range(1, 4):
            result = ledger.collect_tick_days(self.db, mt5, self.root, clock,server_shift_hours=0)
            self.assertEqual(len(result["collected"]), 1)
            immediate = ledger.collect_tick_days(self.db, mt5, self.root, clock + timedelta(minutes=1),server_shift_hours=0)
            self.assertEqual(immediate["collected"], [])
            clock += timedelta(hours=2)
        self.assertEqual(self.db.execute("SELECT status, attempts FROM broker_tick_days").fetchone(), ("GAP", 3))
        self.assertEqual(self.db.execute("SELECT reason FROM data_gaps").fetchone()[0],
                         "NO_BROKER_TICKS_FOR_OBSERVED_DAY")

    def test_tick_archive_is_byte_identical_for_identical_ticks(self):
        first = self.root / "a.csv.gz"
        second = self.root / "b.csv.gz"
        ticks = [(1000, 1.1, 1.1001, 6), (2000, 1.1001, 1.1002, 6)]
        self.assertEqual(ledger._write_ticks(first, ticks), ledger._write_ticks(second, ticks))
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_session_window_excludes_weekend_and_rollover(self):
        self.assertTrue(ledger.fx_session_open(datetime(2026, 10, 20, 10, 0, tzinfo=UTC)))
        self.assertFalse(ledger.fx_session_open(datetime(2026, 10, 20, 21, 0, tzinfo=UTC)))
        self.assertFalse(ledger.fx_session_open(datetime(2026, 10, 23, 20, 30, tzinfo=UTC)))
        self.assertFalse(ledger.fx_session_open(datetime(2026, 10, 24, 12, 0, tzinfo=UTC)))


if __name__ == "__main__":
    unittest.main()
