"""Research-process attestation must not imply complete market data or model improvement."""
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from katarina.monitoring.public_runtime import build_public_runtime

class TelemetryScopesTests(unittest.TestCase):
    def test_partial_market_preserves_fresh_matching_research_memory_only(self):
        now=datetime.now(timezone.utc).isoformat()
        with TemporaryDirectory() as root:
            root=Path(root)
            status=dict(pid=42,status='OBSERVING',delivery='DISABLED',orders_submitted=0,
                        live_execution_authorized=False,production_execution=False,heartbeat_utc=now)
            observation=dict(observed_at_utc=now,unified_cognitive_cycle=dict(matured_observations=2),
                             neuro_link_memory=dict(records_inserted=1),private='PRIVATE_SENTINEL')
            (root/'latest.json').write_text(json.dumps(observation),encoding='utf-8')
            activity=dict(pid=42,fresh=True,events=[],active=[])
            evidence=dict(result='BLOCKED',blockers=['MARKET_DATA_INCOMPLETE_OR_INCONSISTENT'],
                          operational=dict(snapshot_pid=42))
            with patch('katarina.monitoring.public_runtime.read_runtime',return_value=evidence), \
                 patch('katarina.monitoring.public_runtime.read_activity',return_value=activity), \
                 patch('katarina.monitoring.public_research.read_public_research',return_value=({'status':'OK','nodes':[],'edges':[]},{'status':'NOT_ATTESTED'})):
                def read():
                    (root/'continuous-status.json').write_text(json.dumps(status),encoding='utf-8')
                    return build_public_runtime(root)['agent_board']
                b=read()
                self.assertTrue(b['telemetry_verified']);self.assertFalse(b['market_snapshot_verified'])
                self.assertEqual(b['result'],'BLOCKED');self.assertEqual(b['learning']['memory_records_inserted'],1)
                self.assertFalse(b['learning']['improvement_verified']);self.assertNotIn('PRIVATE_SENTINEL',json.dumps(b))
                for key,value in [('production_execution',True),('live_execution_authorized',True),('orders_submitted',1)]:
                    original=status[key];status[key]=value;b=read()
                    self.assertFalse(b['telemetry_verified']);self.assertEqual(b['learning']['status'],'NOT_ATTESTED');status[key]=original
                status['heartbeat_utc']=(datetime.now(timezone.utc)-timedelta(seconds=181)).isoformat()
                self.assertTrue(read()['telemetry_verified']) # fresh matching activity remains independent evidence
                activity['fresh']=False
                self.assertFalse(read()['telemetry_verified'])
                activity['fresh']=True
                activity['pid']=99
                self.assertFalse(read()['telemetry_verified'])
