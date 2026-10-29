"""Deterministic unit tests for WP8c independent bar clock evidence."""
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.research.bar_clock_evidence import (
    BarClockEvidenceAdapter,
    build_evidence_report,
    is_eu_dst,
    is_us_dst,
    load_evidence_report,
    release_shift,
    shift_timeline,
)
from katarina.research.dev_dataset import export_dev_bars
from katarina.research.validation import ValidationError


class DummyBroker:
    def __init__(self):
        self.TIMEFRAME_M5 = "M5"
        self.TIMEFRAME_M15 = "M15"
        self.TIMEFRAME_H1 = "H1"
        self.TIMEFRAME_H4 = "H4"

    def symbol_info(self, symbol):
        class Info:
            point = 0.00001
            trade_tick_size = 0.00001
            trade_contract_size = 100000.0
        return Info()

    def copy_rates_range(self, symbol, timeframe, start, end):
        # Returns one bar at start
        t_epoch = int(start.timestamp())
        return [{
            "time": t_epoch,
            "open": 1.1000, "high": 1.1010, "low": 1.0990, "close": 1.1005,
            "tick_volume": 100, "spread": 10, "real_volume": 100
        }]


class TestBarClockEvidence(unittest.TestCase):

    def test_dst_functions(self):
        # Summer (EU DST active)
        dt_summer = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(is_eu_dst(dt_summer))
        self.assertTrue(is_us_dst(dt_summer))

        # Winter (No DST)
        dt_winter = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        self.assertFalse(is_eu_dst(dt_winter))
        self.assertFalse(is_us_dst(dt_winter))

    def _generate_synthetic_bars(self, release_utc, shift, peak_offset_minutes=0, peak_multiplier=5.0):
        # Create +/- 4 hour bar series around release_utc + shift
        bars = []
        target_server = release_utc + timedelta(hours=shift) + timedelta(minutes=peak_offset_minutes)
        start_server = release_utc + timedelta(hours=shift) - timedelta(hours=4)

        for i in range(96):  # 96 M5 bars in 8 hours
            t = start_server + timedelta(minutes=i * 5)
            vol = 100
            if t == target_server:
                vol = int(100 * peak_multiplier)
            bars.append({"time_utc": t.isoformat(), "tick_volume": vol})
        return bars

    def test_release_shift_synthetic_plus3_plus2(self):
        release_utc = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)  # NFP June 2024

        # +3 shift test
        bars_plus3 = {sym: self._generate_synthetic_bars(release_utc, shift=3)
                      for sym in ("EURUSD", "USDJPY", "XAUUSD")}
        self.assertEqual(release_shift(bars_plus3, release_utc), 3)

        # +2 shift test
        bars_plus2 = {sym: self._generate_synthetic_bars(release_utc, shift=2)
                      for sym in ("EURUSD", "USDJPY", "XAUUSD")}
        self.assertEqual(release_shift(bars_plus2, release_utc), 2)

    def test_release_shift_shifted_5min_rejected(self):
        release_utc = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)
        # Peak shifted by 5 minutes
        bars_shifted = {sym: self._generate_synthetic_bars(release_utc, shift=3, peak_offset_minutes=5)
                        for sym in ("EURUSD", "USDJPY", "XAUUSD")}
        self.assertIsNone(release_shift(bars_shifted, release_utc))

    def test_release_shift_small_volume_rejected(self):
        release_utc = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)
        # Peak multiplier only 2.0x (needs >= 3x)
        bars_small = {sym: self._generate_synthetic_bars(release_utc, shift=3, peak_multiplier=2.0)
                      for sym in ("EURUSD", "USDJPY", "XAUUSD")}
        self.assertIsNone(release_shift(bars_small, release_utc))

    def test_release_shift_single_symbol_insufficient(self):
        release_utc = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)
        bars_single = {
            "EURUSD": self._generate_synthetic_bars(release_utc, shift=3),
            "USDJPY": [],
            "XAUUSD": []
        }
        self.assertIsNone(release_shift(bars_single, release_utc))

    def test_shift_timeline_dst_transitions(self):
        # 2 samples in EU DST transitions (+2 winter, +3 summer)
        samples = [
            {"release_utc": "2024-01-15T13:30:00+00:00", "shift_hours": 2},
            {"release_utc": "2024-06-15T12:30:00+00:00", "shift_hours": 3},
        ]
        timeline = shift_timeline(samples)
        self.assertGreater(len(timeline), 0)
        verified_segs = [s for s in timeline if s["status"] == "VERIFIED"]
        self.assertTrue(len(verified_segs) > 0)

    def test_shift_timeline_off_calendar_shift_change(self):
        # Shift changes from +2 to +3 between Jan 10 and Jan 20 (no DST boundary in Jan!)
        samples = [
            {"release_utc": "2024-01-10T13:30:00+00:00", "shift_hours": 2},
            {"release_utc": "2024-01-20T13:30:00+00:00", "shift_hours": 3},
        ]
        timeline = shift_timeline(samples)
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["status"], "NO_EVIDENCE")

    def test_shift_timeline_no_extrapolation(self):
        # Sample only in 2024 should not extrapolate VERIFIED to 2020 or 2026
        samples = [{"release_utc": "2024-06-15T12:30:00+00:00", "shift_hours": 3}]
        timeline = shift_timeline(samples)
        first_seg = timeline[0]
        last_seg = timeline[-1]
        self.assertEqual(first_seg["status"], "NO_EVIDENCE")
        self.assertEqual(last_seg["status"], "NO_EVIDENCE")

    def test_verified_historical_bar_shift_adapter(self):
        raw_broker = DummyBroker()
        timeline = [
            {"start_utc": "2024-01-01T00:00:00+00:00", "end_utc": "2024-03-31T00:00:00+00:00",
             "shift_hours": 2, "status": "VERIFIED"},
            {"start_utc": "2024-03-31T00:00:00+00:00", "end_utc": "2024-10-27T00:00:00+00:00",
             "shift_hours": 3, "status": "VERIFIED"},
        ]
        adapter = BarClockEvidenceAdapter(raw_broker, timeline, "a" * 64)

        # Query completely inside first segment
        res1 = adapter.verified_historical_bar_shift("EURUSD", "M5", "2024-01-10T00:00:00Z", "2024-01-17T00:00:00Z")
        self.assertTrue(res1["verified"])
        self.assertEqual(res1["shift_hours"], 2)
        self.assertEqual(res1["source_sha256"], "a" * 64)

        # Batch crossing segment boundary
        res2 = adapter.verified_historical_bar_shift("EURUSD", "M5", "2024-03-25T00:00:00Z", "2024-04-05T00:00:00Z")
        self.assertFalse(res2["verified"])

    def test_export_dev_bars_with_evidence_adapter(self):
        raw_broker = DummyBroker()
        timeline = [
            {"start_utc": "2024-01-01T00:00:00+00:00", "end_utc": "2024-10-13T00:00:00+00:00",
             "shift_hours": 2, "status": "VERIFIED"}
        ]
        adapter = BarClockEvidenceAdapter(raw_broker, timeline, "b" * 64)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "dev-export"
            start_dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_dt = datetime(2024, 1, 7, tzinfo=timezone.utc)
            manifest = export_dev_bars(
                adapter,
                core=["EURUSD"],
                start=start_dt,
                end=end_dt,
                out=str(out_path),
                chunk_days=6
            )
            self.assertIn("manifest_sha256", manifest)
            self.assertEqual(manifest["stage"], "WP8A_DEVELOPMENT_ONLY")

    def test_report_lineage_empty_calendar_and_hash_mismatch(self):
        empty_csv = "release_date,release_utc,source_url\n"
        valid_csv = "release_date,release_utc,source_url\n2024-06-07,2024-06-07T12:30:00Z,https://bls.gov\n"
        samples = [{"release_utc": "2024-06-07T12:30:00+00:00", "shift_hours": 3}]

        # Empty calendar content throws exception
        with self.assertRaises(ValidationError) as ctx:
            build_evidence_report(empty_csv, samples)
        self.assertEqual(str(ctx.exception), "CALENDAR_EVIDENCE_EMPTY")

        # Valid report creation with real calendar entry
        r1 = build_evidence_report(valid_csv, samples)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_cal = Path(tmpdir) / "cal.csv"
            tmp_cal.write_text(valid_csv, encoding="utf-8")

            tmp_rep = Path(tmpdir) / "report.json"
            tmp_rep.write_text(json.dumps(r1), encoding="utf-8")

            # Successfully loads with matching calendar
            loaded = load_evidence_report(tmp_rep, calendar_path=tmp_cal)
            self.assertEqual(loaded["source_sha256"], r1["source_sha256"])

            # Tampering with calendar throws CALENDAR_HASH_MISMATCH
            tmp_cal.write_text(valid_csv + "2024-07-05,2024-07-05T12:30:00Z,https://bls.gov\n", encoding="utf-8")
            with self.assertRaises(ValidationError) as ctx2:
                load_evidence_report(tmp_rep, calendar_path=tmp_cal)
            self.assertEqual(str(ctx2.exception), "CALENDAR_HASH_MISMATCH")


if __name__ == "__main__":
    unittest.main()
