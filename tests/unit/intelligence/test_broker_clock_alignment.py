import unittest
from datetime import datetime, timedelta, timezone
from katarina.intelligence.broker.broker_clock_alignment import (
    infer_clock_shift, capture_time_reference, normalize_incoming_time,
)

class TestClockAlignment(unittest.TestCase):
    def test_three_hour_broker_clock_detected_only_for_research(self):
        now=1_800_000_000.0
        ticks={"EURUSD":int(now+10800-2),"XAUUSD":int(now+10800-1),
               "US30":int(now+10800-3),"BTCUSD":int(now+10800-2)}
        v=infer_clock_shift(ticks,now)
        self.assertEqual(v.observed_hours_shift,3)
        self.assertTrue(v.suitable_for_readonly_snapshot)
        self.assertFalse(v.historical_dst_verified)
        self.assertFalse(v.live_execution_authorized)
    def test_utc_server_clock(self):
        now=1_800_000_000.0
        ticks={x:int(now-1) for x in ("EURUSD","XAUUSD","US30")}
        self.assertEqual(infer_clock_shift(ticks,now).observed_hours_shift,0)
    def test_weekend_stale_ticks_are_not_faked_fresh(self):
        now=1_800_000_000.0
        ticks={x:int(now-3600*48) for x in ("EURUSD","XAUUSD","US30")}
        self.assertFalse(infer_clock_shift(ticks,now).suitable_for_readonly_snapshot)
    def test_disagreeing_quotes_do_not_get_offset(self):
        now=1_800_000_000.0
        ticks={"A":int(now+10800),"B":int(now+10800),
               "C":int(now-7200),"D":int(now-7200)}
        self.assertFalse(infer_clock_shift(ticks,now).suitable_for_readonly_snapshot)
    def test_cannot_accept_only_one_symbol(self):
        now=1_800_000_000.0
        self.assertFalse(infer_clock_shift({"A":int(now+10800)},now).suitable_for_readonly_snapshot)


class TestIncomingTimeNormalization(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)
        ticks = {s: int(self.now.timestamp()) + 10800 - 2
                 for s in ("XAUUSD", "EURUSD", "GBPUSD")}
        self.clock = capture_time_reference(infer_clock_shift(ticks, self.now.timestamp()), self.now)

    def test_snapshot_saves_current_offset_and_utc_authority(self):
        evidence = self.clock.as_dict()
        self.assertEqual(evidence["broker_server_shift_minutes"], 180)
        self.assertEqual(evidence["canonical_market_clock"], "MT5_COPY_TICKS_RANGE_TIME_MSC_UTC")
        self.assertFalse(evidence["historical_dst_verified"])
        self.assertFalse(evidence["live_execution_authorized"])

    def test_mt5_tick_milliseconds_are_primary_decision_timestamp(self):
        epoch_msec = int(self.now.timestamp() * 1000) - 2750
        event = normalize_incoming_time(
            epoch_msec, source="MT5_TICK_TIME_MSC_UTC", reference=self.clock)
        self.assertTrue(event.authoritative_market_event)
        self.assertEqual(event.utc, self.now - timedelta(milliseconds=2750))
        self.assertEqual(event.server_wall_display_only,
                         datetime(2026, 10, 15, 8, 59, 57, 250000))

    def test_external_timestamp_with_timezone_normalizes_to_mt5_utc(self):
        incoming = normalize_incoming_time(
            "2026-10-15T13:00:00+07:00", source="EXPLICIT_OFFSET",
            reference=self.clock)
        self.assertEqual(incoming.utc, self.now)
        self.assertFalse(incoming.authoritative_market_event)
        self.assertEqual(incoming.server_wall_display_only.hour, 9)

    def test_archived_aware_data_converts_utc_without_guessing_broker_dst(self):
        result = normalize_incoming_time(
            "2026-01-15T12:00:00+07:00", source="EXPLICIT_OFFSET",
            reference=self.clock)
        self.assertEqual(result.utc, datetime(2026, 1, 15, 5, tzinfo=timezone.utc))
        self.assertIsNone(result.server_wall_display_only)
        self.assertFalse(result.authoritative_market_event)

    def test_current_broker_local_stamp_uses_captured_offset(self):
        result = normalize_incoming_time(
            "2026-10-15T08:59:30", source="BROKER_WALL_CURRENT",
            reference=self.clock, received_at_utc=self.now + timedelta(seconds=15))
        self.assertEqual(result.utc, self.now - timedelta(seconds=30))
        self.assertFalse(result.authoritative_market_event)

    def test_reject_naive_external_and_ambiguous_sources(self):
        for value in ("2026-10-15T06:00:00", datetime(2026, 10, 15, 6)):
            with self.assertRaises(ValueError):
                normalize_incoming_time(value, source="EXPLICIT_OFFSET")
        with self.assertRaises(ValueError):
            normalize_incoming_time("2026-10-15T09:00:00",
                                    source="BROKER_SERVER_HISTORICAL", reference=self.clock)
        with self.assertRaises(ValueError):
            normalize_incoming_time(123, source="MT5_TICK_TIME_MSC_UTC")

    def test_expired_or_future_broker_offset_is_not_reused(self):
        for received in (self.now - timedelta(seconds=1),
                         self.now + timedelta(seconds=181)):
            with self.assertRaisesRegex(ValueError, "broker_clock_evidence_expired"):
                normalize_incoming_time(
                    "2026-10-15T09:00:00", source="BROKER_WALL_CURRENT",
                    reference=self.clock, received_at_utc=received)
        for local in ("2026-10-15T09:00:30", "2026-10-15T08:55:00"):
            with self.assertRaisesRegex(ValueError, "broker_wall_outside"):
                normalize_incoming_time(
                    local, source="BROKER_WALL_CURRENT", reference=self.clock,
                    received_at_utc=self.now)

    def test_cannot_reinterpret_past_dst_data_using_todays_offset(self):
        with self.assertRaisesRegex(ValueError, "broker_wall_outside"):
            normalize_incoming_time(
                "2026-03-29T02:30:00", source="BROKER_WALL_CURRENT",
                reference=self.clock, received_at_utc=self.now)

    def test_unverified_broker_clock_has_no_reference(self):
        invalid = infer_clock_shift({"EURUSD": int(self.now.timestamp())},
                                    self.now.timestamp())
        with self.assertRaisesRegex(ValueError, "broker_clock_not_verified"):
            capture_time_reference(invalid, self.now)
        with self.assertRaises(ValueError):
            capture_time_reference(infer_clock_shift(
                {s:int(self.now.timestamp()) for s in ("EURUSD","XAUUSD","US30")},
                self.now.timestamp()), self.now.replace(tzinfo=None))

if __name__=="__main__":unittest.main()