"""Exercise the real persistent lifecycle using synthetic, nonexecuting sensors."""
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch

from katarina.adapters.automatic_connection import ConnectionConfig, ConnectionUnavailable
from katarina.intelligence.cognition.observer import lock_worker
from katarina.intelligence.cognition.continuous_observation import run_continuous
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain

CONFIG = ConnectionConfig(123, 'Synthetic fixture', priority=('local',), attempts=1)


class Sensor:
    def shutdown(self):
        pass


class ContinuousObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.instances = []
        self.calls = []
        owner = self
        class Brain(UnifiedKatarinaBrain):
            def __init__(self, *args):
                super().__init__(*args)
                owner.instances.append(self)

            def observe_connected_market(self, root, broker, **options):
                owner.calls.append(self)
                # The real shared lock remains held throughout all cycles.
                with owner.assertRaisesRegex(RuntimeError, 'ALREADY_RUNNING'):
                    lock_worker(root)
                self.memory.append_operational_event('synthetic_continuous_test', {'cycle':len(owner.calls)})
                return dict(orders_submitted=0, live_execution_authorized=False,
                            production_execution=False, received_market_data_symbols=3)
        self.Brain = Brain

    def tearDown(self):
        self.tmp.cleanup()

    def run_loop(self, **kwargs):
        return run_continuous(self.root, config=CONFIG, brain_type=self.Brain,
            factories={'local':lambda _: Sensor()}, wait=lambda _:None, **kwargs)

    def test_one_brain_across_cycles_and_restart_reuses_database(self):
        result = self.run_loop(max_cycles=3)
        self.assertEqual(result['successful_cycles'], 3)
        self.assertEqual(len(self.instances), 1)
        self.assertTrue(all(x is self.instances[0] for x in self.calls))
        before = (self.root/'cognitive-memory.sqlite3').stat().st_size
        self.assertGreater(before, 0)
        result = self.run_loop(max_cycles=1)
        self.assertEqual(len(self.instances), 2)
        self.assertEqual(result['successful_cycles'], 1)
        lock_worker(self.root).close()

    def test_stop_request_does_not_start_or_delete_state(self):
        (self.root/'continuous.stop').touch()
        result = self.run_loop(max_cycles=1)
        self.assertEqual(result['reason'], 'EXISTING_STOP_REQUEST')
        self.assertEqual(len(self.instances), 0)
        self.assertTrue((self.root/'continuous.stop').exists())

    def test_owner_can_stop_during_idle_without_another_pass(self):
        def stop(_):
            (self.root/'continuous.stop').touch()
        result = run_continuous(self.root, config=CONFIG, brain_type=self.Brain,
            factories={'local':lambda _:Sensor()}, wait=stop)
        self.assertEqual(result['cycles'], 1)
        self.assertEqual(result['reason'], 'OWNER_STOP_REQUEST')

    def test_transient_fault_recovers_without_recreating_brain(self):
        calls = []
        original = self.Brain.observe_connected_market
        def observe(brain, *args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise ConnectionUnavailable('LOCAL_CONNECT_FAILED')
            return original(brain, *args, **kwargs)
        with patch.object(self.Brain, 'observe_connected_market', observe):
            result = self.run_loop(max_cycles=2)
        self.assertEqual(result['successful_cycles'], 1)
        self.assertEqual(len(self.instances), 1)
        self.assertEqual(result['consecutive_failures'], 0)

    def test_idle_terminal_connect_failure_retries_without_blocking_owner(self):
        from types import SimpleNamespace
        pool=SimpleNamespace(background_count=13,state={},model=None,close=lambda:None)
        pool.start=lambda:pool
        doctor=SimpleNamespace(state={},thread=SimpleNamespace(is_alive=lambda:False),close=lambda:None)
        doctor.start=lambda:doctor
        class OfflineSensor(Sensor):
            def initialize(self):return False
        with patch.dict('os.environ',{'KATARINA_ALL_MARKET_RESEARCH':'1'}), \
             patch('katarina.intelligence.lab.autonomous_research.ResearchPool',return_value=pool), \
             patch('katarina.intelligence.operations.network_doctor.NetworkDoctor',return_value=doctor):
            result=run_continuous(self.root,config=CONFIG,brain_type=self.Brain,max_cycles=2,
                factories={'local':lambda _:OfflineSensor()},wait=lambda _:None)
        self.assertEqual(result['successful_cycles'],2)
        self.assertNotEqual(result['status'],'BLOCKED')

    def test_identity_change_blocks_and_releases_lock_without_leaking_account(self):
        with patch.object(self.Brain, 'observe_connected_market',
                          side_effect=ConnectionUnavailable('ACCOUNT_LOGIN_MISMATCH')):
            with self.assertRaisesRegex(RuntimeError, 'ACCOUNT_OR_TRADING_PERMISSION_CHANGED'):
                self.run_loop(max_cycles=2)
        raw = (self.root/'continuous-status.json').read_text()
        self.assertIn('BLOCKED', raw)
        self.assertNotIn('expected_login', json.loads(raw))
        self.assertNotIn('Synthetic fixture', raw)
        lock_worker(self.root).close()

    def test_unexpected_failure_is_not_retried_or_reported_as_success(self):
        with patch.object(self.Brain, 'observe_connected_market',
                          side_effect=RuntimeError('private-account-and-token')) as observed:
            with self.assertRaises(RuntimeError):
                self.run_loop(max_cycles=2)
        self.assertEqual(observed.call_count, 1)
        self.assertNotIn('private-account-and-token', (self.root/'continuous-status.json').read_text())

    def test_resource_pressure_blocks_before_sensor_pass(self):
        with patch('katarina.intelligence.cognition.continuous_observation.inspect_host',
                   return_value={'blockers':['STATE_DISK_SPACE_LOW']}):
            with self.assertRaisesRegex(RuntimeError, 'HOST_RESOURCE'):
                self.run_loop(max_cycles=1)
        self.assertEqual(self.calls, [])

    def test_actual_brain_pipeline_repeats_with_bound_sensor_and_no_orders(self):
        from tests.integration.test_automatic_connection import AccountBroker, config
        from katarina.adapters.automatic_connection import BoundLocalBroker
        native = AccountBroker()
        result = run_continuous(self.root, config=config(priority=('local',), attempts=1),
            max_cycles=3, factories={'local':lambda c:BoundLocalBroker(native, c)},
            wait=lambda _:None)
        self.assertEqual(result['successful_cycles'], 3)
        self.assertEqual(result['received_market_data_symbols'], 3)
        self.assertEqual(native.orders, 0)
        report = json.loads((self.root/'latest.json').read_text())
        self.assertFalse(report['production_execution'])
        self.assertFalse(report['live_execution_authorized'])
        self.assertEqual(report['orders_submitted'], 0)

    def test_disabled_news_fetch_does_not_fetch_uncached_article_from_cached_feed(self):
        from datetime import datetime, timezone
        from katarina.intelligence.cognition.observer import load_articles
        from katarina.intelligence.news.public_context import ContextStore
        store = ContextStore(self.root/'article-test.sqlite3')
        now = datetime.now(timezone.utc)
        try:
            snapshot = dict(ready=True, payload=dict(items=[dict(
                published_utc=now.isoformat(),url='https://www.federalreserve.gov/example',title='Fixture')]))
            with patch.object(store,'latest',return_value=snapshot), \
                 patch('katarina.intelligence.cognition.observer.fetch_official_article') as fetch:
                articles, diagnostics = load_articles(store,now,allow_fetch=False)
            fetch.assert_not_called()
            self.assertEqual(articles,[])
            self.assertEqual(diagnostics['fed_article_fetch_disabled'],1)
        finally:
            store.db.close()
