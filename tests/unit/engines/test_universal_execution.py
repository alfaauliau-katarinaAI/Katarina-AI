from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch

from tests.unit.engines import test_demo_execution as legacy
from katarina.engines.account_authorization import AccountAuthorization, account_mode
from katarina.engines.demo_execution import DemoExecutionBoundary
from katarina.intelligence.demo.universal_forward import UniversalForwardRuntime
from katarina.adapters.automatic_connection import ConnectionConfig


class UniversalExecutionTests(legacy.DemoExecutionTests):
    def setUp(self):
        super().setUp()
        self.broker.ACCOUNT_TRADE_MODE_REAL = 2
        self.broker.ACCOUNT_TRADE_MODE_CONTEST = 1
        self.broker.account.__dict__.update(balance=10000., equity=10000., margin_free=9000., currency='USD', leverage=100)
        self.broker.symbol_info = lambda s: NS(volume_min=.01, volume_max=10., volume_step=.01)
        self.broker.order_calc_margin = lambda *a: 10.

    def authorized(self, mode='DEMO', name='authorized'):
        auth = AccountAuthorization(mode, 123, 'TEST-DEMO', frozenset({'a'*64}), .01, .5, 2000.)
        return DemoExecutionBoundary(self.broker, self.gov, Path(self.tmp.name)/(name+'.sqlite3'),
            expected_login=123, expected_server='TEST-DEMO', stop_requested=lambda: self.stop,
            clock=lambda: 1000., authorization=auth)

    def test_authorized_demo_real_demo_and_contest(self):
        demo = self.authorized()
        real = self.authorized('REAL', 'real')
        contest = self.authorized('CONTEST', 'contest')
        self.assertEqual(self.send(boundary=demo)['orders_submitted'], 1)
        self.broker.account.trade_mode = 2
        self.assertEqual(self.send(boundary=demo)['status'], 'ACCOUNT_NOT_AUTHORIZED')
        self.assertEqual(self.send(boundary=real)['orders_submitted'], 1)
        self.broker.account.trade_mode = 0
        self.assertEqual(self.send(boundary=real)['status'], 'ACCOUNT_NOT_AUTHORIZED')
        self.assertEqual(self.send(boundary=demo)['status'], 'DUPLICATE_ACCEPTED')
        self.broker.account.trade_mode = 1
        self.assertEqual(self.send(boundary=contest)['orders_submitted'], 1)
        self.assertEqual(len(self.broker.sent), 3)

    def test_unauthorized_strategy_expiry_and_profile(self):
        boundary = self.authorized()
        self.assertEqual(self.send(boundary=boundary, intent=replace(self.intent, experiment_id='b'*64))['status'], 'STRATEGY_NOT_APPROVED')
        boundary.authorization = replace(boundary.authorization, expires_at=999.)
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_NOT_AUTHORIZED')
        boundary.authorization = replace(boundary.authorization, expires_at=2000., max_risk_fraction=.0001)
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_RISK_PROFILE_LIMIT')
        self.assertFalse(self.broker.sent)

    def test_switch_during_broker_check_and_permission_revocation(self):
        boundary = self.authorized()
        self.broker.check_hook = lambda: setattr(self.broker.account, 'trade_mode', 2)
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_NOT_AUTHORIZED')
        self.assertFalse(self.broker.sent)
        self.broker.account.trade_mode = 0
        self.broker.check_hook = lambda: setattr(self.broker.account, 'trade_expert', False)
        self.assertEqual(self.send(boundary=boundary, intent=replace(self.intent, intent_id='next'))['status'], 'DEMO_TRADING_PERMISSION_OFF')
        self.assertFalse(self.broker.sent)

    def test_unknown_mode_and_server_are_never_inferred(self):
        self.broker.account.trade_mode = 99
        self.assertEqual(account_mode(self.broker, self.broker.account), 'UNKNOWN')
        self.assertEqual(self.send(boundary=self.authorized())['orders_submitted'], 0)
        self.broker.account.trade_mode = 0
        boundary = self.authorized()
        self.broker.account.server = 'different'
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_NOT_AUTHORIZED')

    def test_outbox_cannot_cross_account_modes(self):
        self.authorized()
        with self.assertRaisesRegex(ValueError, 'OUTBOX_ACCOUNT_BINDING_CHANGED'):
            self.authorized('REAL')

    def test_coordinator_pauses_switch_and_requires_separate_authorization(self):
        from dataclasses import asdict
        auth = asdict(self.authorized().authorization)
        cfg = ConnectionConfig(123, 'TEST-DEMO', priority=('local',), terminal_path='test',
                               demo_experiments=True, universal_execution=True, execution_authorizations=(auth,))
        runtime = UniversalForwardRuntime(self.tmp.name, cfg, native=self.broker, clock=lambda:1000.)
        with patch('katarina.intelligence.demo.demo_forward.DemoForwardRuntime') as factory:
            factory.return_value.step.return_value = {'status':'READY'}
            def step(): return runtime.step(already_connected=True)
            self.assertEqual(step()['status'], 'ACCOUNT_CHANGED_REVALIDATION_REQUIRED')
            self.assertEqual(step()['status'], 'READY')
            demo_root = factory.call_args.args[0]
            self.broker.account.trade_mode = 2
            self.assertEqual(step()['status'], 'ACCOUNT_CHANGED_REVALIDATION_REQUIRED')
            self.assertEqual(step()['status'], 'ACCOUNT_NOT_AUTHORIZED')
            self.broker.account.trade_mode = 0
            self.assertEqual(step()['status'], 'ACCOUNT_CHANGED_REVALIDATION_REQUIRED')
            self.assertEqual(step()['status'], 'READY')
            self.assertEqual(factory.call_args.args[0], demo_root)
        self.assertFalse(self.broker.sent)

    def test_unapproved_close_never_sends(self):
        boundary = self.authorized()
        self.broker.account.trade_mode = 2
        receipt = boundary.close_owned(789, price=100., observed_at=1000., filling_mode=0)
        self.assertEqual(receipt['status'], 'ACCOUNT_NOT_AUTHORIZED')
        self.assertFalse(self.broker.sent)

    def test_margin_volume_and_missing_books_fail_closed(self):
        boundary = self.authorized()
        self.broker.order_calc_margin = lambda *a: 10000.
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_MARGIN_LIMIT')
        self.broker.order_calc_margin = lambda *a: 10.
        self.assertEqual(self.send(boundary=boundary, intent=replace(self.intent, volume=.015))['status'], 'VOLUME_INVALID')
        self.broker.positions_get = lambda: None
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_BOOK_UNAVAILABLE')
        self.assertFalse(self.broker.sent)

    def test_authorized_real_sell_and_kill_switch(self):
        boundary = self.authorized('REAL', 'sell')
        self.broker.account.trade_mode = 2
        intent = replace(self.intent, side='SELL', stop_loss=110., take_profit=90.)
        self.stop = True
        self.assertEqual(self.send(boundary=boundary, intent=intent)['status'], 'OWNER_STOP_REQUEST')
        self.assertFalse(self.broker.sent)
        self.stop = False
        self.assertEqual(self.send(boundary=boundary, intent=intent)['orders_submitted'], 1)
        self.assertEqual(self.broker.sent[0]['type'], self.broker.ORDER_TYPE_SELL)

    def test_external_order_appearing_during_check_blocks_entry(self):
        boundary = self.authorized()
        self.broker.check_hook = lambda: self.broker.orders.append(NS(ticket=999))
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_BOOK_REQUIRES_RECONCILIATION')
        self.assertFalse(self.broker.sent)

    def test_authorization_cannot_be_removed_or_rebound_on_existing_outbox(self):
        boundary = self.authorized()
        original = boundary.authorization
        boundary.authorization = None
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_NOT_AUTHORIZED')
        boundary.authorization = replace(original, mode='REAL')
        self.broker.account.trade_mode = 2
        self.assertEqual(self.send(boundary=boundary)['status'], 'ACCOUNT_NOT_AUTHORIZED')
        with self.assertRaisesRegex(ValueError, 'EXPLICIT_ACCOUNT_AUTHORIZATION_REQUIRED'):
            DemoExecutionBoundary(self.broker, self.gov, boundary.path, expected_login=123,
                expected_server='TEST-DEMO', stop_requested=lambda:False)
        self.assertFalse(self.broker.sent)

    def test_switch_during_reconciliation_does_not_clear_unknown_submission(self):
        import sqlite3
        boundary = self.authorized()
        self.broker.fail = True
        self.assertEqual(self.send(boundary=boundary)['orders_submitted'], 1)
        with sqlite3.connect(boundary.path) as db:
            db.execute('UPDATE demo_outbox SET updated_at=0')
        def switched_history(*args, **kwargs):
            self.broker.account.trade_mode = 2
            return []
        self.broker.history_deals_get = switched_history
        self.assertEqual(boundary.reconcile()['status'], 'ACCOUNT_NOT_AUTHORIZED')
        with sqlite3.connect(boundary.path) as db:
            self.assertEqual(db.execute('SELECT state FROM demo_outbox').fetchone()[0], 'UNKNOWN')
