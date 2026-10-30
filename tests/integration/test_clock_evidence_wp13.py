"""Integration test suite for WP13 clock evidence with capture_time_reference and normalize_incoming_time."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import unittest

from katarina.intelligence.broker.broker_clock_alignment import (
    ClockEvidence,
    infer_clock_shift,
    capture_time_reference,
    normalize_incoming_time,
)


class ClockEvidenceIntegrationWP13Tests(unittest.TestCase):
    def test_capture_time_reference_includes_evidence_metadata(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        ev = ClockEvidence(
            shift_hours=3,
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            source="INDEPENDENT_CLOCK_OBSERVATION",
            source_sha256=sha256(b"source").hexdigest(),
            broker_server_sha256=sha256(b"ICMarkets-Server").hexdigest(),
        )

        tick_ts = int(now_ts + 3 * 3600 - 2)
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        finding = infer_clock_shift(ticks, now_ts, evidence=ev, broker_server="ICMarkets-Server")
        self.assertTrue(finding.suitable_for_readonly_snapshot)

        ref = capture_time_reference(finding, now)
        data = ref.as_dict()

        self.assertEqual(data["shift_evidence"], "INDEPENDENT_CLOCK_OBSERVATION")
        self.assertEqual(data["evidence_sha256"], ev.source_sha256)
        self.assertEqual(data["evidence_valid_from"], ev.valid_from.isoformat())
        self.assertEqual(data["evidence_valid_until"], ev.valid_until.isoformat())

    def test_normalize_incoming_time_enforces_evidence_validity(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        ev = ClockEvidence(
            shift_hours=3,
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            source="INDEPENDENT_CLOCK_OBSERVATION",
            source_sha256=sha256(b"source").hexdigest(),
            broker_server_sha256=sha256(b"ICMarkets-Server").hexdigest(),
        )

        tick_ts = int(now_ts + 3 * 3600 - 2)
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        finding = infer_clock_shift(ticks, now_ts, evidence=ev, broker_server="ICMarkets-Server")
        ref = capture_time_reference(finding, now)

        # Naive broker wall time (15:00:00 = 12:00:00 UTC + 3 hours shift)
        wall_str = (now + timedelta(hours=3)).replace(tzinfo=None).isoformat()
        normalized = normalize_incoming_time(
            wall_str,
            source="BROKER_WALL_CURRENT",
            reference=ref,
            received_at_utc=now,
        )
        self.assertEqual(normalized.utc, now)

        # Outside evidence valid_until window raises ValueError
        future_now = now + timedelta(days=2)
        with self.assertRaisesRegex(ValueError, "broker_clock_evidence_expired"):
            normalize_incoming_time(
                wall_str,
                source="BROKER_WALL_CURRENT",
                reference=ref,
                received_at_utc=future_now,
            )


if __name__ == "__main__":
    unittest.main()
