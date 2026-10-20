import json
from pathlib import Path
import runpy
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

MODULE=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/ai/activate_autonomous_workers_test.py'))
XML='<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"><RegistrationInfo><URI>old</URI></RegistrationInfo><Principals><Principal><UserId>TEST-EXISTING-PRINCIPAL</UserId></Principal></Principals><Settings><ExecutionTimeLimit>PT72H</ExecutionTimeLimit></Settings><Actions><Exec><Command>old</Command><Arguments>old</Arguments></Exec></Actions></Task>'

class ActivationTests(unittest.TestCase):
    def setup_state(self,root):
        (root/'demo-forward').mkdir()
        (root/'continuous-status.json').write_text(json.dumps(dict(live_execution_authorized=False,production_execution=False)))
        (root/'demo-forward/status.json').write_text(json.dumps(dict(live_authorized=False,broker_positions_open=0,unresolved_submissions=0)))
    def test_preserves_task_principal_and_runs_scanner_before_executor(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.setup_state(root);calls=[]
            def run(args,**kwargs):
                calls.append(args)
                return SimpleNamespace(returncode=1 if args[1]=='/Query' and args[3]=='KatarinaDemoExecutionWorker' else 0,stdout=XML)
            with patch.object(MODULE['subprocess'],'run',side_effect=run):MODULE['activate'](root,root,'python.exe','private-config.json')
            p=root/'handoff-backups/autonomous-workers-20261020/executor-task.xml';t=ET.parse(p);ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}
            self.assertEqual(t.find('t:Principals/t:Principal/t:UserId',ns).text,'TEST-EXISTING-PRINCIPAL')
            self.assertEqual([x[3] for x in calls if x[1]=='/Run'],['KatarinaOwnerContinuousReadonly','KatarinaDemoExecutionWorker'])
            self.assertTrue((root/'demo-forward/independent.enabled').exists())
    def test_owner_stop_prevents_all_scheduler_actions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.setup_state(root);(root/'continuous.stop').touch()
            with patch.object(MODULE['subprocess'],'run') as run:
                with self.assertRaises(RuntimeError):MODULE['activate'](root,root,'python.exe','private-config.json')
                run.assert_not_called()
