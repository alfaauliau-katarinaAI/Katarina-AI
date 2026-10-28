"""WP13: the same stale snapshot must never establish its own offset."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import unittest
from katarina.intelligence.broker import broker_clock_alignment as clock

UTC = timezone.utc
NOW = datetime(2026, 10, 29, 12, tzinfo=UTC)


def evidence(now=NOW, shift=3, server='fixture'):
    return clock.ClockEvidence(shift, now - timedelta(minutes=5), now + timedelta(minutes=5),
        'BROKER_DOCUMENT', 'a'*64, sha256(server.encode()).hexdigest())


class IndependentClockTests(unittest.TestCase):
    def ticks(self, now=NOW, age=2, shift=3):
        return {s:int(now.timestamp()+shift*3600-age) for s in ('A','B','C')}

    def test_snapshot_alone_cannot_authorize_clock(self):
        result = clock.infer_clock_shift(self.ticks(), NOW.timestamp())
        self.assertFalse(result.suitable_for_readonly_snapshot)

    def test_four_hour_stale_is_rejected_even_when_all_symbols_agree(self):
        for day in (NOW, NOW + timedelta(days=2)):
            with self.subTest(day=day):
                result = clock.infer_clock_shift(self.ticks(day, age=14400), day.timestamp(),
                    evidence=evidence(day), broker_server='fixture')
                self.assertFalse(result.suitable_for_readonly_snapshot)

    def test_fresh_quorum_survives_two_one_hour_stale_symbols(self):
        ticks=self.ticks();ticks.update({s:int(NOW.timestamp()+10800-3602) for s in ('D','E')})
        result=clock.infer_clock_shift(ticks,NOW.timestamp(),evidence=evidence(),broker_server='fixture')
        self.assertTrue(result.suitable_for_readonly_snapshot)
        self.assertEqual(result.observed_hours_shift,3)
        self.assertEqual(result.stale_symbols,('D','E'))
        self.assertEqual(result.confirming_symbols,3)

    def test_expired_future_wrong_broker_and_inferred_evidence_are_rejected(self):
        from dataclasses import replace
        for proof in (replace(evidence(),valid_until=NOW),
                      replace(evidence(),valid_from=NOW+timedelta(seconds=1)),
                      evidence(server='other'), replace(evidence(),source='QUOTE_INFERENCE')):
            with self.subTest(proof=proof):
                result=clock.infer_clock_shift(self.ticks(),NOW.timestamp(),evidence=proof,broker_server='fixture')
                self.assertFalse(result.suitable_for_readonly_snapshot)

    def test_fx_weekend_boundaries_and_sunday_reopening(self):
        for day,valid in ((datetime(2026,10,30,20,tzinfo=UTC),False),
                          (datetime(2026,11,1,20,59,tzinfo=UTC),False),
                          (datetime(2026,11,1,21,30,tzinfo=UTC),True)):
            with self.subTest(day=day):
                result=clock.infer_clock_shift(self.ticks(day),day.timestamp(),
                    evidence=evidence(day),broker_server='fixture')
                self.assertEqual(result.suitable_for_readonly_snapshot,valid)

    def test_capture_keeps_source_and_cannot_extend_evidence_lifetime(self):
        finding=clock.infer_clock_shift(self.ticks(),NOW.timestamp(),evidence=evidence(),broker_server='fixture')
        ref=clock.capture_time_reference(finding,NOW)
        self.assertEqual(ref.as_dict()['shift_evidence'],'BROKER_DOCUMENT')
        with self.assertRaises(ValueError):
            clock.capture_time_reference(finding,NOW+timedelta(minutes=6))

    def test_loader_rejects_malformed_and_oversized_files(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'evidence.json'
            self.assertIsNone(clock.load_clock_evidence(path))
            for content in ('null', '[]', '{}', '{', 'x'*16385,
                            '{"schema_version":true}'):
                path.write_text(content, encoding='utf-8')
                self.assertIsNone(clock.load_clock_evidence(path))

    def test_dst_evidence_boundary_does_not_reinterpret_old_offset(self):
        from dataclasses import replace
        new = replace(evidence(shift=2), valid_from=NOW)
        old_ticks = self.ticks(shift=3)
        result = clock.infer_clock_shift(old_ticks, NOW.timestamp(), evidence=new,
                                        broker_server='fixture')
        self.assertFalse(result.suitable_for_readonly_snapshot)
        self.assertIsNone(result.observed_hours_shift)

    def test_wall_timestamp_before_evidence_start_is_rejected(self):
        from dataclasses import replace
        proof = replace(evidence(), valid_from=NOW-timedelta(seconds=5))
        finding = clock.infer_clock_shift(self.ticks(), NOW.timestamp(),
                                         evidence=proof, broker_server='fixture')
        ref = clock.capture_time_reference(finding, NOW)
        with self.assertRaises(ValueError):
            clock.normalize_incoming_time('2026-10-29T14:59:50', source='BROKER_WALL_CURRENT',
                                          reference=ref, received_at_utc=NOW)
