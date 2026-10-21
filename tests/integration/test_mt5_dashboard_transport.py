from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from katarina.monitoring.mt5_dashboard import publish_mt5_dashboard
class DashboardTransportTests(unittest.TestCase):
    def test_identity_freshness_and_stop_are_observable(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);target=r/'status.tsv'
            config=SimpleNamespace(expected_login=123,expected_server='DEMO')
            status=dict(pid=8,status='WAITING',successful_cycles=3,background_workers=14,
                        demo_forward=dict(pid=8,status='WAIT_STRATEGY_SIGNAL',as_of_utc='1970-01-01T00:01:30+00:00'))
            self.assertTrue(publish_mt5_dashboard(r,status,config,target=target,now=100))
            fields=target.read_text().strip().split('\t')
            self.assertEqual(len(fields),17);self.assertEqual(fields[12:14],['123','DEMO'])
            self.assertEqual(fields[15:],['10','1'])
            (r/'continuous.stop').touch();status['demo_forward']['pid']=7
            publish_mt5_dashboard(r,status,config,target=target,now=100)
            fields=target.read_text().strip().split('\t');self.assertEqual(fields[14],'1');self.assertEqual(fields[16],'0')
    def test_missing_demo_never_claims_executor_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'status.tsv'
            publish_mt5_dashboard(tmp,dict(pid=9,status='BLOCKED'),SimpleNamespace(expected_login=1,expected_server='TEST'),target=p,now=100)
            fields=p.read_text().strip().split('\t');self.assertEqual(fields[3],'BLOCKED');self.assertEqual(fields[16],'0')

    def test_liveness_heartbeat_preserves_stale_executor_and_progress(self):
        from katarina.monitoring.mt5_dashboard import DashboardHeartbeat
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'status.tsv'
            status=dict(pid=9,status='OBSERVING',successful_cycles=0,demo_forward=dict(pid=9,as_of_utc='1970-01-01T00:00:00+00:00'))
            hb=DashboardHeartbeat(tmp,SimpleNamespace(expected_login=1,expected_server='TEST'),lambda:status,target=p)
            self.assertTrue(hb.tick());fields=p.read_text().strip().split('\t')
            self.assertEqual(fields[4],'0');self.assertGreater(int(fields[15]),90)
            self.assertEqual(status['demo_forward']['as_of_utc'],'1970-01-01T00:00:00+00:00')
            status['status']='BLOCKED';hb.tick()
            self.assertEqual(p.read_text().strip().split('\t')[3],'BLOCKED')
