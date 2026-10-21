"""Actual host-independent launches plus deterministic host-policy scenarios."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from katarina.host import MiB, detect_capacity, inspect_host, observation_budget, state_directory
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.intelligence.cognition.observer import lock_worker

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / 'scripts/ai/run_contextual_market_observer.py'


class PortableHostTests(unittest.TestCase):
    def test_platform_defaults_and_explicit_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            for system, tail in [('Linux', '.local/state/Katarina/contextual-observer'),
                                 ('Darwin', 'Library/Application Support/Katarina/contextual-observer'),
                                 ('Windows', 'AppData/Local/Katarina/contextual-observer')]:
                self.assertEqual(state_directory(env={}, system=system, home=home), (home / tail).resolve())
            self.assertEqual(state_directory(home/'explicit', env={'KATARINA_STATE_DIR':str(home/'env')}), (home/'explicit').resolve())
            self.assertEqual(state_directory(env={'KATARINA_STATE_DIR':str(home/'env')}), (home/'env').resolve())
            with self.assertRaises(ValueError):
                state_directory('', env={})

    def test_relative_xdg_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(state_directory(env={'XDG_STATE_HOME':'relative'}, system='Linux', home=tmp),
                             (Path(tmp)/'.local/state/Katarina/contextual-observer').resolve())

    def test_capacity_profiles_never_authorize_or_create_workers(self):
        for cpu, mem, expected in [(8,None,3),(1,16*1024*MiB,3),(2,4*1024*MiB,8),(8,16*1024*MiB,17)]:
            budget = observation_budget(cpu,mem)
            self.assertEqual(budget.max_symbols,expected)
            self.assertEqual(budget.background_workers,0)
            self.assertFalse(budget.live_authorized)

    def test_cgroup_limits_override_large_host(self):
        with patch('katarina.host.platform.system',return_value='Linux'), \
             patch('katarina.host.os.cpu_count',return_value=64), \
             patch('katarina.host.os.sched_getaffinity',return_value=set(range(64)),create=True), \
             patch('katarina.host.os.sysconf',side_effect=[16*1024*1024,4096],create=True), \
             patch('katarina.host._linux_limit',return_value=512*MiB), \
             patch('pathlib.Path.read_text',return_value='100000 100000'):
            self.assertEqual(detect_capacity(),(1,512*MiB))

    def test_unwritable_directory_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'file'; path.write_text('occupied')
            report=inspect_host(path)
            self.assertIn('STATE_DIRECTORY_NOT_WRITABLE',report['blockers'])
            self.assertFalse(report['offline_research_available'])

    def test_low_disk_blocks(self):
        from collections import namedtuple
        usage=namedtuple('Usage','total used free')
        with tempfile.TemporaryDirectory() as tmp, patch('katarina.host.shutil.disk_usage',return_value=usage(100,99,1)):
            self.assertIn('STATE_DISK_SPACE_LOW',inspect_host(tmp)['blockers'])

    def test_doctor_launches_outside_checkout_without_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=subprocess.run([sys.executable,str(CLI),'--doctor','--state-dir',str(Path(tmp)/'state')],
                                  cwd=tmp,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(result.stdout)
            self.assertFalse(report['broker_connection_verified'])
            self.assertFalse(report['live_authorized'])
            self.assertTrue(report['state_writable'])

    def test_offline_cycle_persists_and_resumes_without_broker_or_network(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch('socket.create_connection',side_effect=AssertionError('network forbidden')):
            for _ in range(2):
                result=UnifiedKatarinaBrain.research_once(tmp)
                self.assertEqual(result['orders_submitted'],0)
                self.assertFalse(result['live_execution_authorized'])
                self.assertEqual(result['input_scope'],'EXISTING_LOCAL_EVIDENCE_ONLY_NO_MARKET_FETCH')
            self.assertTrue((Path(tmp)/'cognitive-memory.sqlite3').exists())
            self.assertNotIn('MetaTrader5',sys.modules)

    def test_same_directory_lock_prevents_offline_second_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            with lock_worker(Path(tmp)):
                with self.assertRaisesRegex(RuntimeError,'ALREADY_RUNNING'):
                    UnifiedKatarinaBrain.research_once(tmp)

    def test_offline_cli_environment_path_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,KATARINA_STATE_DIR=str(Path(tmp)/'portable'))
            result=subprocess.run([sys.executable,str(CLI),'--offline-research'],env=env,
                                  cwd=tmp,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['orders_submitted'],0)
            self.assertTrue((Path(tmp)/'portable/context.sqlite3').exists())

    def test_failure_releases_lock_and_no_research_on_invalid_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(UnifiedKatarinaBrain,'run_unified_cognitive_cycle',side_effect=ValueError('synthetic failure')):
                with self.assertRaises(ValueError):
                    UnifiedKatarinaBrain.research_once(tmp)
            UnifiedKatarinaBrain.research_once(tmp)
            with self.assertRaises(ValueError):
                UnifiedKatarinaBrain.research_once(tmp,mode='unknown')

    def test_closed_state_can_resume_after_directory_relocation(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'old'; target=Path(tmp)/'new'
            first=UnifiedKatarinaBrain.research_once(source)
            shutil.copytree(source,target)
            second=UnifiedKatarinaBrain.research_once(target)
            self.assertEqual(first['architecture'],second['architecture'])
            self.assertEqual(second['host_environment']['state_directory'],str(target.resolve()))
            self.assertEqual(second['orders_submitted'],0)
