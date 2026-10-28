"""Independent clock evidence gates the real observer before historical reads."""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from tests.integration.test_brain_owned_workflow import SyntheticBroker, write_clock_fixture


class ObserverClockEvidenceTests(unittest.TestCase):
    def test_missing_expired_mismatched_and_malformed_evidence_block_without_tick_history(self):
        for case in ('missing','expired','broker_mismatch','malformed'):
            with self.subTest(case=case), TemporaryDirectory() as folder:
                root=Path(folder);broker=SyntheticBroker()
                if case!='missing':
                    write_clock_fixture(root,server='wrong' if case=='broker_mismatch' else 'Test-Demo')
                    path=root/'broker-clock-evidence.json'
                    if case=='expired':
                        value=json.loads(path.read_text(encoding='utf-8'))
                        value['valid_until']=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
                        path.write_text(json.dumps(value),encoding='utf-8')
                    elif case=='malformed':
                        path.write_text('{',encoding='utf-8')
                with patch.object(broker,'copy_ticks_range',side_effect=AssertionError('unverified history')) as ticks:
                    with self.assertRaisesRegex(RuntimeError,'BROKER_CLOCK_NOT_VERIFIED'):
                        UnifiedKatarinaBrain.observe_once(root,broker=broker,fetch_news=False)
                ticks.assert_not_called()
                self.assertEqual(broker.orders,0)
                self.assertEqual(broker.shutdowns,1)

    def test_four_hour_stale_weekday_snapshot_cannot_read_history(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);broker=SyntheticBroker();broker.now-=14400
            write_clock_fixture(root)
            with patch.object(broker,'copy_ticks_range',side_effect=AssertionError('stale history')) as ticks:
                with self.assertRaisesRegex(RuntimeError,'BROKER_CLOCK_NOT_VERIFIED'):
                    UnifiedKatarinaBrain.observe_once(root,broker=broker,fetch_news=False)
            ticks.assert_not_called()


def setUpModule():
    from tests.integration.test_brain_owned_workflow import freeze_test_clock
    unittest.addModuleCleanup(freeze_test_clock(__name__).close)
