import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from katarina.monitoring.worker_runtime import read_worker_runtime

class WorkerRuntimeTests(unittest.TestCase):
    def test_permission_scope_redaction_and_stale_workers(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);now=datetime.now(timezone.utc);s=now.isoformat()
            (root/'worker-TEST_MOMENTUM_H4.json').write_text(json.dumps(dict(pid=12,autonomous=True,as_of_utc=s,status='PAUSED_STORAGE_BUDGET',completed=3,secret='PRIVATE_SENTINEL')))
            (root/'latest.json').write_text(json.dumps(dict(observed_at_utc=s,broker_account_monitor=dict(algo_trading_off=False,account_login='PRIVATE_SENTINEL'))))
            r=read_worker_runtime(root,12,now=now);self.assertTrue(r['mt5_algo_enabled']);self.assertEqual(r['paused_workers'],1);self.assertNotIn('PRIVATE_SENTINEL',json.dumps(r))
            self.assertEqual(read_worker_runtime(root,13,now=now)['fresh_workers'],0)
            self.assertIsNone(read_worker_runtime(root,12,now=now+timedelta(minutes=5))['mt5_algo_enabled'])
    def test_independent_executor_is_attested_separately(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'demo-forward';p.mkdir();s=datetime.now(timezone.utc).isoformat()
            (p/'executor.json').write_text(json.dumps(dict(pid=99,mode='DEMO',independent=True,status='RUNNING',as_of_utc=s,cycles=4)))
            (p/'status.json').write_text(json.dumps(dict(pid=99,status='PROTECTED_VARIANT_NOT_QUALIFIED',execution_permission='DEMO_ORDER_PERMISSION_ON',as_of_utc=s)))
            r=read_worker_runtime(root,12);self.assertTrue(r['demo_permission']);self.assertFalse(r['live_authorized']);self.assertEqual(r['executor']['pid'],99)
