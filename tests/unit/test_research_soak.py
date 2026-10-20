from datetime import datetime,timedelta,timezone
import tempfile
import unittest
from katarina.monitoring.research_soak import record_soak

class SoakTests(unittest.TestCase):
    def test_elapsed_time_and_gaps_are_not_silently_passed(self):
        now=datetime.now(timezone.utc)
        status=dict(heartbeat_utc=now.isoformat(),run_id='test',status='WAITING',orders_submitted=0,live_execution_authorized=False,production_execution=False)
        with tempfile.TemporaryDirectory() as root:
            a=record_soak(root,status)
            self.assertEqual(a['windows']['24_hours']['status'],'PENDING_ELAPSED_TIME')
            status['heartbeat_utc']=(now+timedelta(days=1)).isoformat()
            a=record_soak(root,status)
            self.assertEqual(a['windows']['24_hours']['status'],'NEEDS_REVIEW')
            self.assertEqual(a['windows']['7_days']['status'],'PENDING_ELAPSED_TIME')
