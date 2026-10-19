"""A real offline observer emits events only around its existing execution path."""
from pathlib import Path
import tempfile
import unittest
from katarina.adapters.automatic_connection import BoundLocalBroker
from katarina.intelligence.continuous_observation import run_continuous
from katarina.monitoring.activity_trace import read_activity
from katarina.monitoring.public_runtime import build_public_runtime
from tests.integration.test_automatic_connection import AccountBroker,config

class ObserverActivityTests(unittest.TestCase):
    def test_existing_observer_pipeline_emits_real_stages_and_keeps_live_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);broker=AccountBroker()
            result=run_continuous(root,config=config(priority=('local',),attempts=1),
                factories={'local':lambda c:BoundLocalBroker(broker,c)},max_symbols=3,max_cycles=1)
            self.assertEqual(result['successful_cycles'],1)
            self.assertEqual(broker.orders,0)
            activity=read_activity(root)
            phases={(e['phase'],e['state']) for e in activity['events']}
            for phase in ('NEWS','SENSORS','MEMORY','RISK_AUDIT','WAIT_ACK','PUBLISH'):
                self.assertIn((phase,'STARTED'),phases)
                self.assertIn((phase,'DONE'),phases)
            self.assertEqual(activity['current']['phase'],'STOPPED')
            symbols=[e for e in activity['events'] if e['phase']=='TECHNICAL' and e['state']=='DONE']
            self.assertGreater(len(symbols),0)
            self.assertTrue(all(e['symbol'] and e['method'] and e['action'] for e in symbols))
            public=build_public_runtime(root)
            self.assertEqual(public['agent_board']['result'],'BLOCKED')
            self.assertFalse(public['agent_board']['live_execution_authorized'])
