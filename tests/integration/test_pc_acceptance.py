"""PC acceptance must distinguish invented data, offline fallback and actual route reads."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.pc.run_pc_acceptance import run
from katarina.adapters.automatic_connection import run_connected
from katarina.adapters.pc_simulation import PCSimulationBroker

ROOT=Path(__file__).resolve().parents[2]


class PCAcceptanceTests(unittest.TestCase):
    def test_demo_real_pipeline_and_restarts_produce_local_html(self):
        with tempfile.TemporaryDirectory(prefix='PC test space ') as tmp:
            first=run(tmp)
            second=run(tmp)
            self.assertEqual(first['status'],'PASS_SYNTHETIC_PC_ONLY')
            self.assertFalse(first['broker_verified'])
            self.assertNotEqual(first['run_directory'],second['run_directory'])
            self.assertTrue((Path(tmp)/'latest-pc-test.html').exists())
            self.assertFalse((Path(tmp)/'readonly-observer').exists())
            self.assertEqual(json.loads((Path(tmp)/'latest-pc-test.json').read_text())['orders_sent'],0)

    def test_missing_connection_is_blocked_not_broker_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=run(tmp,mode='observe')
            self.assertEqual(report['status'],'BLOCKED')
            self.assertEqual(report['reason'],'CONNECTION_CONFIG_REQUIRED')

    def test_offline_fallback_is_not_counted_as_broker_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'connection.json'
            path.write_text(json.dumps(dict(expected_login=123,expected_server='Test',priority=['local'])))
            offline={'orders_submitted':0,'live_execution_authorized':False,'connection':{'route':'offline'}}
            with patch('scripts.pc.run_pc_acceptance.run_connected',return_value=offline):
                report=run(tmp,mode='observe',connection_config=path)
            self.assertEqual(report['status'],'BLOCKED')
            self.assertEqual(report['reason'],'BROKER_UNAVAILABLE_OFFLINE_ONLY')
            self.assertFalse(report['broker_verified'])

    def test_failed_sensor_cannot_pass_synthetic_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(PCSimulationBroker,'copy_rates_from_pos',return_value=None):
            self.assertEqual(run(tmp)['status'],'BLOCKED')

    def test_exceptions_cannot_leak_credential_text_into_summary(self):
        secret='do-not-publish-test-credential'
        with tempfile.TemporaryDirectory() as tmp, patch('scripts.pc.run_pc_acceptance.UnifiedKatarinaBrain.observe_once',side_effect=RuntimeError(secret)):
            report=run(tmp)
            self.assertNotIn(secret,json.dumps(report))
            self.assertEqual(report['status'],'BLOCKED')

    def test_cli_runs_from_unrelated_working_directory_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='PC test space ') as tmp:
            result=subprocess.run([sys.executable,str(ROOT/'scripts/pc/run_pc_acceptance.py'),
                '--state-dir',str(Path(tmp)/'state')],cwd=tmp,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('PASS_SYNTHETIC_PC_ONLY',result.stdout)

    def test_pc_bootstrap_help_needs_no_research_dependencies(self):
        result=subprocess.run([sys.executable,'-I','-X','utf8',str(ROOT/'katarina_pc.py'),'--help'],
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('LIVE OFF',result.stdout)

    def test_readonly_success_requires_actual_observer_report(self):
        from katarina.adapters.automatic_connection import BoundLocalBroker
        from tests.integration.test_automatic_connection import AccountBroker
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'connection.json'
            path.write_text(json.dumps(dict(expected_login=123,expected_server='Test-Demo',priority=['local'])))
            def connected(brain,root,**kwargs):
                return run_connected(brain,root,**kwargs,
                    factories={'local':lambda config:BoundLocalBroker(AccountBroker(),config)})
            with patch('scripts.pc.run_pc_acceptance.run_connected',side_effect=connected):
                report=run(tmp,mode='observe',connection_config=path)
            self.assertEqual(report['status'],'PASS_READONLY_OBSERVATION_ONLY')
            self.assertEqual(report['route'],'local')
            self.assertFalse(report['profitability_proven'])
            self.assertTrue((Path(tmp)/'readonly-observer/latest.json').exists())


# This synthetic suite patches only its observer call sites and restores them.
from tests.synthetic_clock_fixture import ModuleClockFixture
_clock_fixture = ModuleClockFixture()

def setUpModule():
    _clock_fixture.start()

def tearDownModule():
    _clock_fixture.stop()
