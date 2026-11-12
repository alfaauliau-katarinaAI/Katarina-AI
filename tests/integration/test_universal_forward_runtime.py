from dataclasses import asdict, replace
from pathlib import Path
import unittest
from unittest.mock import patch

from tests.integration import test_demo_forward_runtime as legacy
from katarina.engines.account_authorization import AccountAuthorization
from katarina.intelligence.demo.demo_forward import DemoForwardRuntime
from katarina.intelligence.demo.universal_forward import UniversalForwardRuntime
from katarina.adapters.automatic_connection import BoundLocalBroker
from katarina.adapters.demo_permissions import observation_permission


class UniversalForwardTests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.DemoForwardTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_real_demo_switch_uses_shared_engine_and_preserves_owned_book(self):
        f = self.fixture
        demo = f.native
        real = legacy.Native(f.clock)
        real.account.trade_mode = 2
        real.account.login = 456
        for broker in (demo, real):
            broker.ACCOUNT_TRADE_MODE_REAL = 2
            broker.ACCOUNT_TRADE_MODE_CONTEST = 1
            broker.account.leverage = 100
        approval = AccountAuthorization('DEMO', 123, 'TEST-DEMO', frozenset({'b'*64}), .01, .5, f.now+86400)
        cfg = replace(f.config, universal_execution=True, execution_authorizations=(asdict(approval),))
        runtime = UniversalForwardRuntime(f.root, cfg, native=demo, clock=f.clock)
        candidate = f.runtime._candidate()
        with patch.object(DemoForwardRuntime, '_candidate', return_value=candidate):
            self.assertEqual(runtime.step(force=True)['status'], 'ACCOUNT_CHANGED_REVALIDATION_REQUIRED')
            self.assertEqual(runtime.step(force=True)['status'], 'DEMO_ACCEPTED')
            demo_path = runtime.active.boundary.path
            runtime.native = real
            self.assertEqual(runtime.step(force=True)['status'], 'ACCOUNT_CHANGED_REVALIDATION_REQUIRED')
            self.assertEqual(runtime.step(force=True)['status'], 'ACCOUNT_NOT_AUTHORIZED')
            self.assertFalse(real.sent)
            runtime.config = replace(cfg, execution_authorizations=(asdict(approval), asdict(replace(approval, mode='REAL', login=456))))
            self.assertEqual(runtime.step(force=True)['status'], 'DEMO_ACCEPTED')
            self.assertNotEqual(runtime.active.boundary.path, demo_path)
            self.assertTrue(runtime.status['live_authorized'])
            runtime.native = demo
            self.assertEqual(runtime.step(force=True)['status'], 'ACCOUNT_CHANGED_REVALIDATION_REQUIRED')
            self.assertEqual(runtime.step(force=True)['status'], 'DEMO_POSITION_MONITORING')
            self.assertEqual(runtime.active.boundary.path, demo_path)
            self.assertEqual(len(demo.sent), 1)
            self.assertEqual(len(real.sent), 1)

    def test_research_observation_does_not_require_execution_authorization(self):
        f = self.fixture
        f.native.ACCOUNT_TRADE_MODE_REAL = 2
        f.native.account.trade_mode = 2
        cfg = replace(f.config, universal_execution=True)
        broker = BoundLocalBroker(f.native, cfg)
        self.assertTrue(broker.initialize())
        self.assertTrue(observation_permission(broker))
        runtime = UniversalForwardRuntime(f.root, cfg, native=f.native, clock=f.clock)
        runtime.step()
        self.assertEqual(runtime.step()['status'], 'ACCOUNT_NOT_AUTHORIZED')
        self.assertFalse(f.native.sent)

    def test_universal_observer_stays_bound_to_declared_account(self):
        from katarina.adapters.automatic_connection import ConnectionUnavailable, verify_identity
        f = self.fixture
        cfg = replace(f.config, universal_execution=True)
        verify_identity(f.native, cfg)
        f.native.account.login = 456
        with self.assertRaisesRegex(ConnectionUnavailable, 'ACCOUNT_LOGIN_MISMATCH'):
            verify_identity(f.native, cfg)
        f.native.account.login = 123
        f.native.account.server = 'OTHER-SERVER'
        with self.assertRaisesRegex(ConnectionUnavailable, 'ACCOUNT_SERVER_MISMATCH'):
            verify_identity(f.native, cfg)

    def test_switch_during_ledger_read_does_not_persist_foreign_account(self):
        import sqlite3
        from katarina.intelligence.demo.demo_account import DemoAccountLedger
        f = self.fixture
        f.native.ACCOUNT_TRADE_MODE_REAL = 2
        with sqlite3.connect(':memory:') as db:
            ledger = DemoAccountLedger(db, login=123, server='TEST-DEMO', clock=f.clock, expected_mode='DEMO')
            def switch(*args, **kwargs):
                f.native.account.trade_mode = 2
                return []
            f.native.history_deals_get = switch
            with self.assertRaisesRegex(ValueError, 'ACCOUNT_LEDGER_BINDING_CHANGED'):
                ledger.capture(f.native)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM demo_account_state').fetchone()[0], 0)
        self.assertFalse(f.native.sent)

    def test_runtime_failure_does_not_claim_no_order_and_publishes_blocked_status(self):
        import json
        f = self.fixture
        auth = AccountAuthorization('DEMO', 123, 'TEST-DEMO', frozenset({'b'*64}), .01, .5, f.now+100)
        cfg = replace(f.config, universal_execution=True, execution_authorizations=(asdict(auth),))
        runtime = UniversalForwardRuntime(f.root, cfg, native=f.native, clock=f.clock)
        runtime.step()
        with patch.object(DemoForwardRuntime, 'step', side_effect=OSError('disk failed after submission')):
            result = runtime.step()
        self.assertIsNone(result['orders_submitted'])
        self.assertFalse(result['live_authorized'])
        saved = json.loads((f.root/'demo-forward/status.json').read_text())
        self.assertEqual(saved['execution_permission'], 'BLOCKED')
        self.assertEqual(saved['mode'], 'DEMO')
        self.assertIsNone(saved['orders_submitted'])
        self.assertEqual(f.native.shutdowns, 2)

    def test_status_republication_does_not_refresh_stale_decision(self):
        f = self.fixture
        cfg = replace(f.config, universal_execution=True)
        runtime = UniversalForwardRuntime(f.root, cfg, native=f.native, clock=f.clock)
        old = '2000-01-01T00:00:00+00:00'
        result = runtime._publish({'status':'WAIT', 'as_of_utc':old})
        self.assertEqual(result['as_of_utc'], old)
