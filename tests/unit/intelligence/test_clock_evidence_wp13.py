"""Deterministic test suite for WP13 broker clock alignment with independent evidence."""
import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import unittest
from unittest.mock import patch

from katarina.intelligence.broker.broker_clock_alignment import (
    ClockEvidence,
    HostClockTrust,
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
    source_bytes: bytes | None = None,
) -> ClockEvidence:
    s_sha = sha256(source_bytes if source_bytes is not None else b"source").hexdigest()
    return ClockEvidence(
        shift_hours=shift,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
        source=source,
        source_sha256=s_sha,
        broker_server_sha256=sha256(broker.encode("utf-8")).hexdigest(),
    )


class ClockEvidenceWP13Tests(unittest.TestCase):
    def test_untrusted_host_clock_returns_no_trusted_host_clock(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        tick_ts = int(now_ts + 3 * 3600 - 2)
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        with patch("katarina.intelligence.broker.broker_clock_alignment.inspect_host_clock",
                   return_value=HostClockTrust(False,"UNTRUSTED_OR_DESYNC","fixture")):
            finding = infer_clock_shift(ticks, now_ts, require_host_trust=True)
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.reason, "NO_TRUSTED_HOST_CLOCK")

    def test_broker_document_without_source_bytes_rejected(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        doc_bytes = b"Official Broker Contract Specification PDF Content"
        ev = evidence(now, shift=3, source="BROKER_DOCUMENT", source_bytes=doc_bytes)
        tick_ts = int(now_ts + 3 * 3600 - 2)
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        self.assertFalse(ev.valid_at(now, "fixture", source_bytes=None))
        self.assertFalse(ev.valid_at(now, "fixture", source_bytes=b"Wrong Bytes"))
        self.assertTrue(ev.valid_at(now, "fixture", source_bytes=doc_bytes))

        finding = infer_clock_shift(ticks, now_ts, evidence=ev, broker_server="fixture", source_bytes=b"Wrong")
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.reason, "CLOCK_EVIDENCE_EXPIRED_OR_WRONG_BROKER")

    def test_unexplained_shift_jump_is_quarantined(self):
        now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)  # Mid-summer, far from DST
        now_ts = now.timestamp()
        tick_ts = int(now_ts + 3 * 3600 - 2)  # Shift 3
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        finding = infer_clock_shift(ticks, now_ts, previous_shift=2)
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.reason, "QUARANTINED_UNEXPLAINED_SHIFT_JUMP")

    def test_three_quotes_without_evidence_rejected_when_require_evidence(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        tick_ts = int(now_ts + 3600 - 2)
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        finding = infer_clock_shift(ticks, now_ts, require_evidence=True, broker_server="fixture")
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.reason, "CLOCK_EVIDENCE_MISSING_OR_INVALID")

    def test_three_stale_quotes_simultaneously_rejected(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        ev = evidence(now, shift=3)
        stopped_ts = int(now_ts - 4 * 3600 + 3 * 3600)
        ticks = {"EURUSD": stopped_ts, "GBPUSD": stopped_ts, "USDJPY": stopped_ts}

        finding = infer_clock_shift(ticks, now_ts, evidence=ev, broker_server="fixture")
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertIsNone(finding.observed_hours_shift)
        self.assertEqual(finding.reason, "INSUFFICIENT_FRESH_QUOTES")
        self.assertEqual(len(finding.stale_symbols), 3)

    def test_weekend_closed_returns_fx_market_closed(self):
        saturday = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        saturday_ts = saturday.timestamp()
        ev = evidence(saturday, shift=3)
        ticks = {"EURUSD": int(saturday_ts + 3 * 3600), "GBPUSD": int(saturday_ts + 3 * 3600), "USDJPY": int(saturday_ts + 3 * 3600)}

        finding = infer_clock_shift(ticks, saturday_ts, evidence=ev, broker_server="fixture")
        self.assertFalse(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.reason, "FX_MARKET_CLOSED")

    def test_sunday_after_market_open_valid_with_fresh_quotes(self):
        sunday_open = datetime(2026, 10, 25, 21, 30, tzinfo=timezone.utc)
        sunday_ts = sunday_open.timestamp()
        ev = evidence(sunday_open, shift=3)
        tick_ts = int(sunday_ts + 3 * 3600 - 2)
        ticks = {"EURUSD": tick_ts, "GBPUSD": tick_ts, "USDJPY": tick_ts}

        finding = infer_clock_shift(ticks, sunday_ts, evidence=ev, broker_server="fixture")
        self.assertTrue(finding.suitable_for_readonly_snapshot)
        self.assertEqual(finding.observed_hours_shift, 3)
        self.assertEqual(finding.reason, "CLOCK_VERIFIED")

    def test_three_fresh_plus_two_stale_valid_with_correct_offset(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
        now_ts = now.timestamp()
        ev = evidence(now, shift=3)
        fresh_ts = int(now_ts + 3 * 3600 - 2)
        stale_ts = int(now_ts + 3 * 3600 - 3600)
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

        missing = infer_clock_shift(ticks, now_ts, require_evidence=True, broker_server="fixture")
        self.assertFalse(missing.suitable_for_readonly_snapshot)
        self.assertEqual(missing.reason, "CLOCK_EVIDENCE_MISSING_OR_INVALID")

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

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "evidence.json"
            path.write_text(json.dumps(valid_json), encoding="utf-8")

            loaded = load_clock_evidence(path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.shift_hours, 3)

            path.write_bytes(b"x" * 16385)
            self.assertIsNone(load_clock_evidence(path))

            self.assertIsNone(load_clock_evidence(Path(tmpdir) / "missing.json"))


if __name__ == "__main__":
    unittest.main()
