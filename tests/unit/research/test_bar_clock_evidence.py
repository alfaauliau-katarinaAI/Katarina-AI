"""Deterministic unit tests for WP8c independent bar clock evidence."""
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
from katarina.research.bar_clock_evidence import (
    BarClockEvidenceAdapter,
    build_evidence_report,
    collect_release_samples,
    is_eu_dst,
    is_us_dst,
    load_evidence_report,
    release_shift,
    shift_timeline,
)
from scripts.research.build_bar_clock_evidence import (
    build_evidence,
    is_path_inside_repo,
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

    CAL = ("release_date,release_utc,source_url\n"
           "2024-01-05,2024-01-05T13:30:00Z,https://www.bls.gov/schedule/news_release/empsit.htm\n"
           "2024-06-07,2024-06-07T12:30:00Z,https://www.bls.gov/schedule/news_release/empsit.htm\n")

    def _report(self):
        samples = [{"release_utc": "2024-01-05T13:30:00+00:00", "shift_hours": 2, "bars_sha256": "1" * 64},
                   {"release_utc": "2024-06-07T12:30:00+00:00", "shift_hours": 3, "bars_sha256": "2" * 64}]
        return build_evidence_report(self.CAL, samples)

    def test_release_near_data_edge_needs_full_24_bar_context(self):
        release_utc = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)
        bars = {sym: [b for b in self._generate_synthetic_bars(release_utc, shift=3)
                      if datetime.fromisoformat(b["time_utc"]) >= release_utc + timedelta(hours=3, minutes=-30)]
                for sym in ("EURUSD", "USDJPY", "XAUUSD")}
        self.assertIsNone(release_shift(bars, release_utc))  # only 6 bars before the release

    def test_segment_without_own_sample_is_not_verified(self):
        timeline = shift_timeline([{"release_utc": "2024-06-07T12:30:00+00:00", "shift_hours": 3}])
        verified = [s for s in timeline if s["status"] == "VERIFIED"]
        self.assertEqual(len(verified), 1)
        seg = verified[0]
        self.assertLessEqual(seg["start_utc"], "2024-06-07")
        self.assertGreater(seg["end_utc"], "2024-06-07")
        # Winter 2024 next to the sample stays unverified (no 200-day extension).
        self.assertTrue(seg["start_utc"] >= "2024-03-31")

    def test_verified_historical_bar_shift_adapter(self):
        adapter = BarClockEvidenceAdapter(DummyBroker(), self._report())
        res1 = adapter.verified_historical_bar_shift("EURUSD", "M5", "2024-01-10T00:00:00Z", "2024-01-17T00:00:00Z")
        self.assertTrue(res1["verified"])
        self.assertEqual(res1["shift_hours"], 2)
        res2 = adapter.verified_historical_bar_shift("EURUSD", "M5", "2024-03-25T00:00:00Z", "2024-04-05T00:00:00Z")
        self.assertFalse(res2["verified"])
        res3 = adapter.verified_historical_bar_shift("EURUSD", "M5", "2023-01-10T00:00:00Z", "2023-01-17T00:00:00Z")
        self.assertFalse(res3["verified"])

    def test_adapter_rejects_hand_written_or_tampered_timeline(self):
        timeline = [{"start_utc": "2020-01-01T00:00:00+00:00", "end_utc": "2026-10-13T00:00:00+00:00",
                     "shift_hours": 2, "status": "VERIFIED"}]
        with self.assertRaises(ValidationError):
            BarClockEvidenceAdapter(DummyBroker(), {"timeline": timeline, "source_sha256": "b" * 64})
        report = self._report()
        report["timeline"] = timeline  # rehash so only reproducibility can catch it
        body = {k: v for k, v in report.items() if k != "source_sha256"}
        from katarina.research.validation import canonical, sha256_text
        report["source_sha256"] = sha256_text(canonical(body))
        with self.assertRaises(ValidationError) as ctx:
            BarClockEvidenceAdapter(DummyBroker(), report)
        self.assertEqual(str(ctx.exception), "EVIDENCE_REPORT_TIMELINE_NOT_REPRODUCIBLE")

    def test_samples_must_be_on_calendar_with_lineage(self):
        off = [{"release_utc": "2024-02-01T13:30:00+00:00", "shift_hours": 2, "bars_sha256": "1" * 64}]
        with self.assertRaises(ValidationError) as ctx:
            build_evidence_report(self.CAL, off)
        self.assertEqual(str(ctx.exception), "EVIDENCE_SAMPLE_OFF_CALENDAR")
        no_hash = [{"release_utc": "2024-01-05T13:30:00+00:00", "shift_hours": 2, "bars_sha256": ""}]
        with self.assertRaises(ValidationError) as ctx:
            build_evidence_report(self.CAL, no_hash)
        self.assertEqual(str(ctx.exception), "EVIDENCE_SAMPLE_LINEAGE_MISSING")

    def test_export_dev_bars_with_evidence_adapter(self):
        adapter = BarClockEvidenceAdapter(DummyBroker(), self._report())
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = export_dev_bars(adapter, core=["EURUSD"],
                                       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                                       end=datetime(2024, 1, 7, tzinfo=timezone.utc),
                                       out=str(Path(tmpdir) / "dev-export"), chunk_days=6)
            self.assertIn("manifest_sha256", manifest)
            self.assertEqual(manifest["stage"], "WP8A_DEVELOPMENT_ONLY")

    def test_report_lineage_empty_calendar_and_hash_mismatch(self):
        with self.assertRaises(ValidationError) as ctx:
            build_evidence_report("release_date,release_utc,source_url\n", [])
        self.assertEqual(str(ctx.exception), "CALENDAR_EVIDENCE_EMPTY")
        r1 = self._report()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_cal = Path(tmpdir) / "cal.csv"
            tmp_cal.write_text(self.CAL, encoding="utf-8")
            tmp_rep = Path(tmpdir) / "report.json"
            tmp_rep.write_text(json.dumps(r1), encoding="utf-8")
            self.assertEqual(load_evidence_report(tmp_rep, calendar_path=tmp_cal)["source_sha256"],
                             r1["source_sha256"])
            tmp_cal.write_text(self.CAL + "2024-07-05,2024-07-05T12:30:00Z,https://www.bls.gov/x\n",
                               encoding="utf-8")
            with self.assertRaises(ValidationError) as ctx2:
                load_evidence_report(tmp_rep, calendar_path=tmp_cal)
            self.assertEqual(str(ctx2.exception), "CALENDAR_HASH_MISMATCH")

    def test_collect_release_samples_synthetic_and_hash_determinism(self):
        release1 = datetime(2024, 1, 5, 13, 30, tzinfo=timezone.utc)
        release2 = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)

        class WP8dFakeBroker:
            def __init__(self):
                self.TIMEFRAME_M5 = "M5"

            def copy_rates_range(self, symbol, timeframe, start, end):
                bars = []
                curr = start
                while curr < end:
                    vol = 100
                    if curr == release1 + timedelta(hours=2) or curr == release2 + timedelta(hours=3):
                        vol = 500
                    bars.append({
                        "time": int(curr.timestamp()),
                        "open": 1.1000, "high": 1.1010, "low": 1.0990, "close": 1.1005,
                        "tick_volume": vol, "spread": 10, "real_volume": vol
                    })
                    curr += timedelta(minutes=5)
                return bars

        broker = WP8dFakeBroker()
        cal_content = (
            "release_date,release_utc,source_url\n"
            "2024-01-05,2024-01-05T13:30:00Z,https://www.bls.gov/schedule/news_release/empsit.htm\n"
            "2024-06-07,2024-06-07T12:30:00Z,https://www.bls.gov/schedule/news_release/empsit.htm\n"
        )
        samples, rejected = collect_release_samples(broker, cal_content)
        self.assertEqual(len(samples), 2)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(samples[0]["shift_hours"], 2)
        self.assertEqual(samples[1]["shift_hours"], 3)
        self.assertEqual(len(samples[0]["bars_sha256"]), 64)

        # Run twice to test determinism
        samples2, _ = collect_release_samples(broker, cal_content)
        self.assertEqual(samples[0]["bars_sha256"], samples2[0]["bars_sha256"])

    def test_collect_release_samples_no_consensus_rejected(self):
        class FlatFakeBroker:
            def __init__(self):
                self.TIMEFRAME_M5 = "M5"

            def copy_rates_range(self, symbol, timeframe, start, end):
                bars = []
                curr = start
                while curr < end:
                    bars.append({
                        "time": int(curr.timestamp()),
                        "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1,
                        "tick_volume": 100, "spread": 10, "real_volume": 100
                    })
                    curr += timedelta(minutes=5)
                return bars

        samples, rejected = collect_release_samples(
            FlatFakeBroker(),
            "release_date,release_utc,source_url\n2024-01-05,2024-01-05T13:30:00Z,https://www.bls.gov/x\n"
        )
        self.assertEqual(len(samples), 0)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["reason"], "NO_CONSENSUS_OR_WEAK_EVIDENCE")

    def test_repo_path_rejection_and_build_evidence_report_load(self):
        repo_root = Path(__file__).resolve().parents[3]
        self.assertTrue(is_path_inside_repo(repo_root / "build" / "test_out.json"))
        self.assertTrue(is_path_inside_repo("config/research/us_release_calendar.csv"))

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "evidence_out.json"
            self.assertFalse(is_path_inside_repo(out_file))

            release1 = datetime(2024, 1, 5, 13, 30, tzinfo=timezone.utc)
            release2 = datetime(2024, 6, 7, 12, 30, tzinfo=timezone.utc)

            class WP8dFakeBroker:
                def __init__(self):
                    self.TIMEFRAME_M5 = "M5"

                def copy_rates_range(self, symbol, timeframe, start, end):
                    bars = []
                    curr = start
                    while curr < end:
                        vol = 100
                        if curr == release1 + timedelta(hours=2) or curr == release2 + timedelta(hours=3):
                            vol = 500
                        bars.append({
                            "time": int(curr.timestamp()),
                            "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1,
                            "tick_volume": vol, "spread": 10, "real_volume": vol
                        })
                        curr += timedelta(minutes=5)
                    return bars

            cal_file = Path(tmpdir) / "calendar.csv"
            cal_file.write_text(self.CAL, encoding="utf-8")

            report = build_evidence(WP8dFakeBroker(), calendar_path=cal_file, max_releases=10)
            self.assertIn("source_sha256", report)
            self.assertIn("provenance", report)

            out_file.write_text(json.dumps(report), encoding="utf-8")
            loaded = load_evidence_report(out_file, calendar_path=cal_file)
            self.assertEqual(loaded["source_sha256"], report["source_sha256"])

    def test_partial_consensus_and_max_releases_validation(self):
        cal_content = (
            "release_date,release_utc,source_url\n"
            "2024-01-05,2024-01-05T13:30:00Z,https://www.bls.gov/schedule/news_release/empsit.htm\n"
            "2024-02-02,2024-02-02T13:30:00Z,https://www.bls.gov/schedule/news_release/empsit.htm\n"
            "2024-03-08,2024-03-08T13:30:00Z,https://www.bls.gov/schedule/news_release/empsit.htm\n"
        )
        release1 = datetime(2024, 1, 5, 13, 30, tzinfo=timezone.utc)

        class MixedFakeBroker:
            def __init__(self):
                self.TIMEFRAME_M5 = "M5"

            def copy_rates_range(self, symbol, timeframe, start, end):
                bars = []
                curr = start
                while curr < end:
                    vol = 100
                    # Only release 1 has a 500x volume spike (+2 shift)
                    if curr == release1 + timedelta(hours=2):
                        vol = 500
                    bars.append({
                        "time": int(curr.timestamp()),
                        "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1,
                        "tick_volume": vol, "spread": 10, "real_volume": vol
                    })
                    curr += timedelta(minutes=5)
                return bars

        with tempfile.TemporaryDirectory() as tmpdir:
            cal_file = Path(tmpdir) / "cal.csv"
            cal_file.write_text(cal_content, encoding="utf-8")
            out_file = Path(tmpdir) / "out.json"

            # 1 sample (release1), 2 rejected (release2, release3)
            report = build_evidence(MixedFakeBroker(), calendar_path=cal_file, max_releases=10)
            self.assertEqual(report["sample_count"], 1)
            self.assertEqual(len(report["rejected"]), 2)

            out_file.write_text(json.dumps(report), encoding="utf-8")
            loaded = load_evidence_report(out_file, calendar_path=cal_file)
            self.assertEqual(loaded["source_sha256"], report["source_sha256"])

            # Test max_releases truncation (max_releases=2)
            report_truncated = build_evidence(MixedFakeBroker(), calendar_path=cal_file, max_releases=2)
            self.assertEqual(report_truncated["sample_count"], 1)
            self.assertEqual(len(report_truncated["rejected"]), 1)
            out_file.write_text(json.dumps(report_truncated), encoding="utf-8")
            loaded_trunc = load_evidence_report(out_file, calendar_path=cal_file)
            self.assertEqual(loaded_trunc["source_sha256"], report_truncated["source_sha256"])

    def test_empty_calendar_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_cal = Path(tmpdir) / "empty.csv"
            empty_cal.write_text("release_date,release_utc,source_url\n", encoding="utf-8")
            class Dummy:
                pass
            with self.assertRaises(ValidationError) as ctx:
                build_evidence(Dummy(), calendar_path=empty_cal)
            self.assertEqual(str(ctx.exception), "CALENDAR_EVIDENCE_EMPTY")

    def test_mt5_never_imported_in_test(self):
        self.assertNotIn("MetaTrader5", sys.modules)

if __name__ == "__main__":
    unittest.main()
