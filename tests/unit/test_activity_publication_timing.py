import unittest
from unittest.mock import patch
from katarina.monitoring.monitor_publisher import _wait_for_publication

class ActivityPublicationTimingTests(unittest.TestCase):
    def test_changed_source_coalesces_for_two_seconds(self):
        now=[0.0];waits=[]
        def sleep(seconds):
            self.assertLessEqual(seconds,1)
            waits.append(seconds);now[0]+=seconds
        with patch('katarina.monitoring.monitor_publisher._source_version',return_value=('new',)):
            _wait_for_publication('unused',('old',),0,10,sleep=sleep,clock=lambda:now[0])
        self.assertEqual(now[0],2)
        self.assertEqual(len(waits),2)

    def test_unchanged_source_uses_heartbeat_deadline(self):
        now=[0.0]
        with patch('katarina.monitoring.monitor_publisher._source_version',return_value=('same',)):
            _wait_for_publication('unused',('same',),0,10,
                sleep=lambda seconds:now.__setitem__(0,now[0]+seconds),clock=lambda:now[0])
        self.assertEqual(now[0],10)

    def test_slow_request_does_not_add_another_full_interval(self):
        with patch('katarina.monitoring.monitor_publisher._source_version',return_value=('new',)):
            _wait_for_publication('unused',('old',),0,10,
                sleep=lambda _:self.fail('unnecessary wait'),clock=lambda:12)
