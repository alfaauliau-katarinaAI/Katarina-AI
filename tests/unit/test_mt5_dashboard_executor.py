from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from katarina.monitoring.mt5_dashboard import publish_mt5_dashboard

class Mt5ExecutorTests(unittest.TestCase):
 def test_independent_pid_and_stale_rejection_without_permission_renewal(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);p=r/'demo-forward';p.mkdir();now=datetime.now(timezone.utc);stamp=now.isoformat();old=(now-timedelta(seconds=200)).isoformat()
   (p/'executor.json').write_text(json.dumps(dict(pid=99,independent=True,mode='DEMO',status='RUNNING',as_of_utc=stamp)))
   (p/'status.json').write_text(json.dumps(dict(pid=99,as_of_utc=stamp,status='WAIT_STRATEGY_SIGNAL',execution_permission='DEMO_ORDER_PERMISSION_ON')))
   status=dict(pid=7,status='WAITING',demo_forward={'pid':7,'as_of_utc':old})
   dest=r/'out.tsv';cfg=SimpleNamespace(expected_login=123,expected_server='test')
   def fields():
    self.assertTrue(publish_mt5_dashboard(r,status,cfg,target=dest,now=now.timestamp()));return dest.read_text().strip().split('\t')
   v=fields();self.assertEqual(len(v),17);self.assertEqual(v[16],'1');self.assertEqual(v[15],'0');self.assertEqual(v[8],'WAIT_STRATEGY_SIGNAL')
   (p/'status.json').write_text(json.dumps(dict(pid=123,as_of_utc=stamp,status='WRONG_ACCOUNT',execution_permission='DEMO_ORDER_PERMISSION_ON')))
   v=fields();self.assertEqual(v[16],'1');self.assertEqual(v[7],'UNKNOWN');self.assertEqual(v[8],'PENDING')
   (p/'executor.json').write_text(json.dumps(dict(pid=99,independent=True,mode='DEMO',status='RUNNING',as_of_utc=old)))
   v=fields();self.assertEqual(v[16],'0');self.assertEqual(v[15],'999999');self.assertEqual(v[7],'UNKNOWN')
