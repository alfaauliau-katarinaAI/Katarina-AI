"""Deterministic test suite for WP13 broker clock alignment with independent evidence."""
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import unittest

from katarina.intelligence.broker.broker_clock_alignment import (
    ClockEvidence,
    infer_clock_shift,
    load_clock_evidence,
    capture_time_reference,
    normalize_incoming_time,
)


def evidence(
    now: datetime,
    shift: int = 3,
    broker: str = "fixture",
    source: str = "INDEPENDENT_CLOCK_OBSERVATION",
) -> ClockEvidence:
    return ClockEvidence(
        shift_hours=shift,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
        source=source,
        source_sha256=sha256(b"source").hexdigest(),
        broker_server_sha256=sha256(broker.encode("utf-8")).hexdigest(),
    )


class ClockEvidenceWP13Tests(unittest.TestCase):
    def test_three_stale_quotes_simultaneously_rejected(self):
        # Wednesday 12:00 UTC
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        ev = evidence(now, shift=3)
        # 3 quotes stopped 4 hours ago (4 hours * 3600s = 14400s old relative to UTC)
        # Server timestamp stopped at now_ts - 4*3600 + 3*3600
        stopped_ts = int(now_ts - 4 * 3600 + 3 * 3600)
        ticks = {"EURUSD": stopped_ts, "GBPUSD": stopped_ts, "USDJPY": stopped_ts}

        finding = infer_clock_shift(ticks, now_ts, evidence=ev, broker_server="fixture")
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertIsNone(finding.observed_hours_shift)
        self.assertEqual(finding.reason, "INSUFFICIENT_FRESH_QUOTES")
        self.assertEqual(len(finding.stale_symbols), 3)

    def test_weekend_closed_returns_fx_market_closed(self):
        # Saturday 12:00 UTC
        saturday = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        saturday_ts = saturday.timestamp()
        ev = evidence(saturday, shift=3)
        ticks = {"EURUSD": int(saturday_ts + 3 * 3600), "GBPUSD": int(saturday_ts + 3 * 3600), "USDJPY": int(saturday_ts + 3 * 3600)}

        finding = infer_clock_shift(ticks, saturday_ts, evidence=ev, broker_server="fixture")
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.reason, "FX_MARKET_CLOSED")

    def test_sunday_after_market_open_valid_with_fresh_quotes(self):
        # Sunday 21:30 UTC (FX market opens at 21:00 UTC)
        sunday_open = datetime(2026, 10, 25, 21, 30, tzinfo=timezone.utc)
        sunday_ts = sunday_open.timestamp()
        # This date follows the EU DST transition; confine this evidence to
        # a period entirely AFTER the boundary rather than self-attesting
        # an unverified clock shift across it.
        template = evidence(sunday_open, shift=3)
        ev = ClockEvidence(
            shift_hours=template.shift_hours,
            valid_from=sunday_open - timedelta(minutes=20),
            valid_until=sunday_open + timedelta(minutes=20),
            source=template.source, source_sha256=template.source_sha256,
            broker_server_sha256=template.broker_server_sha256,
        )
        tick_ts = int(sunday_ts + 3 * 3600 - 2)
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        finding = infer_clock_shift(ticks, sunday_ts, evidence=ev, broker_server="fixture")
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.observed_hours_shift, 3)
        self.assertEqual(finding.reason, "CLOCK_VERIFIED")

    def test_three_fresh_plus_two_stale_valid_with_correct_offset(self):
        # Wednesday 12:00 UTC
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        ev = evidence(now, shift=3)
        fresh_ts = int(now_ts + 3 * 3600 - 2)
        stale_ts = int(now_ts + 3 * 3600 - 3600)  # 1 hour old
        ticks = {
            "EURUSD": fresh_ts,
            "GBPUSD": fresh_ts,
            "USDJPY": fresh_ts,
            "CLOSED1": stale_ts,
            "CLOSED2": stale_ts,
        }

        finding = infer_clock_shift(ticks, now_ts, evidence=ev, broker_server="fixture")
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.observed_hours_shift, 3)
        self.assertEqual(finding.confirming_symbols, 3)
        self.assertEqual(finding.stale_symbols, ("CLOSED1", "CLOSED2"))

    def test_missing_or_expired_or_wrong_server_evidence_fails_closed(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        tick_ts = int(now_ts + 3 * 3600 - 2)
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        # Explicit require_evidence without evidence
        missing = infer_clock_shift(ticks, now_ts, require_evidence=True, broker_server="fixture")
        self.assertFalse(missing.suitable_for_readonly_snapshot)
        self.assertEqual(missing.reason, "CLOCK_EVIDENCE_MISSING_OR_INVALID")

        # Expired evidence
        expired_ev = ClockEvidence(
            shift_hours=3,
            valid_from=now - timedelta(days=5),
            valid_until=now - timedelta(days=1),
            source="INDEPENDENT_CLOCK_OBSERVATION",
            source_sha256=sha256(b"source").hexdigest(),
            broker_server_sha256=sha256(b"fixture").hexdigest(),
        )
        expired = infer_clock_shift(ticks, now_ts, evidence=expired_ev, broker_server="fixture")
        self.assertFalse(expired.suitable_for_readonly_snapshot)
        self.assertEqual(expired.reason, "CLOCK_EVIDENCE_EXPIRED_OR_WRONG_BROKER")

        # Wrong server
        wrong_server = infer_clock_shift(ticks, now_ts, evidence=evidence(now, 3, "fixture"), broker_server="OtherServer")
        self.assertFalse(wrong_server.suitable_for_readonly_snapshot)
        self.assertEqual(wrong_server.reason, "CLOCK_EVIDENCE_EXPIRED_OR_WRONG_BROKER")

    def test_load_clock_evidence_validation(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        valid_json = {
            "schema_version": 1,
            "shift_hours": 3,
            "valid_from": (now - timedelta(days=1)).isoformat(),
            "valid_until": (now + timedelta(days=1)).isoformat(),
            "source": "INDEPENDENT_CLOCK_OBSERVATION",
            "source_sha256": sha256(b"source").hexdigest(),
            "broker_server_sha256": sha256(b"fixture").hexdigest(),
        }

        # Valid load via temp directory file
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "evidence.json"
            source = Path(tmpdir) / "broker-clock-source.txt"
            source.write_bytes(b"source")  # reviewed source bytes, not just a SHA string
            path.write_text(json.dumps(valid_json), encoding="utf-8")

            loaded = load_clock_evidence(path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.shift_hours, 3)

            # Forged SHA or missing source can never authenticate itself.
            source.write_bytes(b"tampered")
            self.assertIsNone(load_clock_evidence(path))
            source.unlink()
            self.assertIsNone(load_clock_evidence(path))
            source.write_bytes(b"source")
            self.assertIsNotNone(load_clock_evidence(path))

            # File > 16KB rejected
            path.write_bytes(b"x" * 16385)
            self.assertIsNone(load_clock_evidence(path))

            # Non-existent file
            self.assertIsNone(load_clock_evidence(Path(tmpdir) / "missing.json"))


    def test_dst_crossing_and_reversed_evidence_interval_rejected(self):
        now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
        ev = evidence(now, shift=2)
        crossing = ClockEvidence(
            shift_hours=ev.shift_hours,
            valid_from=datetime(2026, 10, 31, 12, tzinfo=timezone.utc),
            valid_until=datetime(2026, 11, 2, 12, tzinfo=timezone.utc),
            source=ev.source, source_sha256=ev.source_sha256,
            broker_server_sha256=ev.broker_server_sha256,
        )
        self.assertFalse(crossing.valid_at(now, "fixture"))
        reversed_interval = ClockEvidence(
            shift_hours=ev.shift_hours, valid_from=now + timedelta(days=1),
            valid_until=now - timedelta(days=1),
            source=ev.source, source_sha256=ev.source_sha256,
            broker_server_sha256=ev.broker_server_sha256,
        )
        self.assertFalse(reversed_interval.valid_at(now, "fixture"))

    def test_canonical_observer_requires_evidence_static_contract(self):
        # The inference helper may preserve legacy opt-in, but the canonical
        # read-only Stage-0 observer is NOT allowed to silently fall back.
        root = Path(__file__).resolve().parents[3]
        source = (root / "src/katarina/intelligence/cognition/observer.py").read_text(encoding="utf-8")
        self.assertIn("require_evidence=True)", source)
        runner = (root / "src/katarina/intelligence/cognition/continuous_observation.py").read_text(encoding="utf-8")
        self.assertIn("'CLOCK_EVIDENCE_MISSING_OR_INVALID'", runner)
        self.assertIn("'CLOCK_EVIDENCE_EXPIRED_OR_WRONG_BROKER'", runner)


if __name__ == "__main__":
    unittest.main()
