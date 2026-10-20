import unittest
from katarina.monitoring.snapshot_io import replace_snapshot

class SnapshotIOTests(unittest.TestCase):
    def test_transient_reader_does_not_stop_observer_or_change_payload(self):
        class Source:
            calls=0
            def replace(self,target):
                self.calls+=1
                if self.calls<3:raise PermissionError('sharing violation')
                return target
        source=Source();waits=[]
        self.assertEqual(replace_snapshot(source,'snapshot',wait=waits.append),'snapshot')
        self.assertEqual(source.calls,3)
        self.assertEqual(len(waits),2)
    def test_persistent_failure_is_bounded_and_still_reported(self):
        class Source:
            calls=0
            def replace(self,target):
                self.calls+=1
                raise PermissionError('persistent denial')
        source=Source();waits=[]
        with self.assertRaises(PermissionError):replace_snapshot(source,'snapshot',wait=waits.append)
        self.assertEqual(source.calls,8)
        self.assertEqual(len(waits),7)
        self.assertLess(sum(waits),.4)
