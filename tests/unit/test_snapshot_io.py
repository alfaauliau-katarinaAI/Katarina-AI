import unittest
from katarina.monitoring.snapshot_io import replace_snapshot


class SnapshotIOTests(unittest.TestCase):
    def test_transient_reader_does_not_stop_observer_or_change_payload(self):
        class Source:
            calls = 0
            def replace(self, target):
                self.calls += 1
                if self.calls < 3:
                    raise PermissionError('sharing violation')
                return target
        source = Source()
        waits = []
        self.assertEqual(replace_snapshot(source, 'snapshot', wait=waits.append), 'snapshot')
        self.assertEqual(source.calls, 3)
        self.assertEqual(waits, [0.02, 0.04])

    def test_longer_sharing_conflict_can_clear_before_budget_expires(self):
        class Source:
            calls = 0
            def replace(self, target):
                self.calls += 1
                if self.calls < 10:
                    raise PermissionError('sharing violation')
                return target
        source = Source()
        waits = []
        self.assertEqual(replace_snapshot(source, 'snapshot', wait=waits.append), 'snapshot')
        self.assertEqual(source.calls, 10)
        self.assertEqual(len(waits), 9)
        self.assertGreater(sum(waits), 2)

    def test_persistent_failure_is_bounded_and_still_reported(self):
        class Source:
            calls = 0
            def replace(self, target):
                self.calls += 1
                raise PermissionError('persistent denial')
        source = Source()
        waits = []
        with self.assertRaises(PermissionError):
            replace_snapshot(source, 'snapshot', wait=waits.append)
        self.assertEqual(source.calls, 12)
        self.assertEqual(len(waits), 11)
        self.assertLess(sum(waits), 4)

    def test_other_os_errors_do_not_get_silenced(self):
        class Source:
            def replace(self, target):
                raise OSError('disk failure')
        with self.assertRaises(OSError):
            replace_snapshot(Source(), 'snapshot', wait=lambda _: self.fail('must not retry'))

    def test_invalid_attempt_budget_rejected(self):
        class Source:
            def replace(self, target):
                self.fail('must not attempt')
        with self.assertRaises(ValueError):
            replace_snapshot(Source(), 'snapshot', attempts=0)
