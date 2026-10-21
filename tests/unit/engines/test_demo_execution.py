import concurrent.futures
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest

from katarina.engines.demo_execution import DemoExecutionBoundary, DemoIntent
from katarina.engines.risk import RiskGovernor, RiskRequest


class Broker:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    ORDER_TIME_GTC = 0
    TRADE_ACTION_DEAL = 1
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_REQUOTE = 10004
    TRADE_RETCODE_TIMEOUT = 10012
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(self):
        self.account = NS(login=123, server='TEST-DEMO', trade_mode=0,
                          trade_allowed=True, trade_expert=True)
        self.terminal = NS(connected=True, trade_allowed=True, tradeapi_disabled=False)
        self.sent = []
        self.check_hook = lambda: None
        self.fail = False
        self.code = self.TRADE_RETCODE_DONE
        self.deals, self.orders, self.positions = [], [], []

    def terminal_info(self): return self.terminal
    def account_info(self): return self.account
    def order_calc_profit(self, *args): return -10.
    def order_check(self, request):
        self.check_hook()
        return NS(retcode=0)
    def order_send(self, request):
        self.sent.append(request)
        if self.fail: raise TimeoutError('private broker details')
        return NS(retcode=self.code, order=456, deal=789)
    def history_deals_get(self, *args, **kwargs):
        if 'position' in kwargs: return [d for d in self.deals if d.position_id == kwargs['position']]
        if 'ticket' in kwargs: return [d for d in self.deals if d.ticket == kwargs['ticket']]
        return list(self.deals)
    def orders_get(self): return list(self.orders)
    def positions_get(self, ticket=None): return [p for p in self.positions if p.ticket == ticket]


class DemoExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'private-outbox.sqlite3'
        self.broker = Broker()
        self.stop = False
        self.intent = DemoIntent('intent1', 'a'*64, 'TEST', 'BUY', .01, 100, 90, 120, 1000.)
        self.risk = RiskRequest(.01, 0, 0, .1, 2, True, True,
                                risk_capital=10000, risk_reference_capital=10000,
                                account_currency='USD')
        self.gov = RiskGovernor.from_config(Path(__file__).resolve().parents[3]/'config/risk_governor_v2.json')
        self.boundary = self.boundary_for(self.broker)

    def boundary_for(self, broker):
        return DemoExecutionBoundary(broker, self.gov, self.path, expected_login=123,
            expected_server='TEST-DEMO', stop_requested=lambda: self.stop, clock=lambda: 1000.)

    def send(self, intent=None, risk=None, boundary=None, stamp=1000.):
        return (boundary or self.boundary).submit(intent or self.intent, risk or self.risk,
                                                 risk_observed_at=stamp, filling_mode=0)

    def test_governor_approved_demo_passes_check_and_sends_once(self):
        self.assertEqual(self.send()['status'], 'DEMO_ACCEPTED')
        self.assertEqual(self.send()['status'], 'DUPLICATE_ACCEPTED')
        self.assertEqual(len(self.broker.sent), 1)
        self.assertEqual(self.broker.sent[0]['deviation'], 0)
        self.assertGreater(self.broker.sent[0]['sl'], 0)

    def test_real_contest_and_missing_mode_never_send(self):
        for mode in (2, 1, None, False):
            self.broker.account.trade_mode = mode
            self.assertEqual(self.send()['status'], 'DEMO_ACCOUNT_REQUIRED')
        self.assertFalse(self.broker.sent)

    def test_binding_change_and_permission_off(self):
        self.broker.account.login = 321
        self.assertEqual(self.send()['status'], 'DEMO_ACCOUNT_BINDING_CHANGED')
        self.broker.account.login = 123
        self.broker.terminal.trade_allowed = False
        self.assertEqual(self.send()['status'], 'DEMO_TRADING_PERMISSION_OFF')
        self.assertFalse(self.broker.sent)

    def test_revalidates_account_after_order_check(self):
        self.broker.check_hook = lambda: setattr(self.broker.account, 'trade_mode', 2)
        self.assertEqual(self.send()['status'], 'DEMO_ACCOUNT_REQUIRED')
        self.assertFalse(self.broker.sent)

    def test_owner_stop_before_and_during_check(self):
        self.stop = True
        self.assertEqual(self.send()['status'], 'OWNER_STOP_REQUEST')
        self.stop = False
        self.broker.check_hook = lambda: setattr(self, 'stop', True)
        self.assertEqual(self.send()['status'], 'OWNER_STOP_REQUEST')
        self.assertFalse(self.broker.sent)

    def test_risk_governor_rejects_unreconciled_and_unbounded(self):
        for risk in (replace(self.risk, reconciled=False),
                     replace(self.risk, unbounded_open_risk=True),
                     replace(self.risk, daily_drawdown_fraction=.36)):
            self.assertEqual(self.send(risk=risk)['status'], 'RISK_GOVERNOR_PAUSE')
        self.assertFalse(self.broker.sent)

    def test_reduced_risk_cannot_send_oversized_lot(self):
        self.assertEqual(self.send(risk=replace(self.risk, requested_fraction=.0001))['status'],
                         'DEMO_VOLUME_EXCEEDS_APPROVED_RISK')
        self.assertFalse(self.broker.sent)

    def test_stale_risk_and_missing_protection(self):
        self.assertEqual(self.send(stamp=997.)['status'], 'DEMO_RISK_EVIDENCE_STALE')
        self.assertEqual(self.send(replace(self.intent, stop_loss=0))['status'], 'INVALID_DEMO_INTENT')
        self.assertEqual(self.send(replace(self.intent, created_at=990.))['status'], 'DEMO_INTENT_STALE')
        self.assertFalse(self.broker.sent)

    def test_unknown_send_blocks_other_intents_and_survives_restart(self):
        self.broker.fail = True
        result = self.send()
        self.assertEqual(result['status'], 'DEMO_UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertNotIn('private', str(result))
        fresh = self.boundary_for(self.broker)
        self.assertEqual(self.send(replace(self.intent, intent_id='next'), boundary=fresh)['status'],
                         'DEMO_RECONCILIATION_REQUIRED')
        self.assertEqual(len(self.broker.sent), 1)

    def test_concurrent_producers_across_boundary_instances_reserve_once(self):
        instances = [self.boundary_for(self.broker) for _ in range(8)]
        def submit(n):
            return self.send(replace(self.intent, intent_id='worker'+str(n)), boundary=instances[n])
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(submit, range(8)))
        self.assertEqual(sum(r['orders_submitted'] == 1 for r in results), 1)
        self.assertEqual(len(self.broker.sent), 1)

    def test_partial_and_other_retcodes_are_not_claimed_completed(self):
        self.broker.code = self.broker.TRADE_RETCODE_DONE_PARTIAL
        self.assertEqual(self.send()['status'], 'DEMO_PARTIAL')
        self.assertEqual(self.send(replace(self.intent, intent_id='next'))['status'],
                         'DEMO_RECONCILIATION_REQUIRED')

    def test_intent_conflict_never_resubmits(self):
        self.send()
        self.assertEqual(self.send(replace(self.intent, volume=.02))['status'], 'INTENT_ID_CONFLICT')
        self.assertEqual(len(self.broker.sent), 1)


    def test_definitive_broker_rejection_is_terminal_and_unblocks(self):
        self.broker.code = self.broker.TRADE_RETCODE_REQUOTE
        self.assertEqual(self.send()['status'], 'DEMO_REJECTED')
        self.broker.code = self.broker.TRADE_RETCODE_DONE
        self.assertEqual(self.send(replace(self.intent, intent_id='next'))['status'], 'DEMO_ACCEPTED')
        self.assertEqual(len(self.broker.sent), 2)

    def test_ambiguous_timeout_still_blocks(self):
        self.broker.code = self.broker.TRADE_RETCODE_TIMEOUT
        self.assertEqual(self.send()['status'], 'DEMO_UNKNOWN')
        self.assertEqual(self.send(replace(self.intent, intent_id='next'))['status'], 'DEMO_RECONCILIATION_REQUIRED')

    def boundary_at(self, now):
        clock = [now]
        boundary = DemoExecutionBoundary(self.broker, self.gov, self.path, expected_login=123,
            expected_server='TEST-DEMO', stop_requested=lambda: self.stop, clock=lambda: clock[0])
        return boundary, clock

    def test_unknown_without_deal_or_order_resolves_not_filled_after_grace(self):
        self.broker.fail = True
        self.send()
        boundary, clock = self.boundary_at(1000. + 600)
        boundary.reconcile()   # too early: stays blocking
        self.assertEqual(self.send(replace(self.intent, intent_id='early'), boundary=self.boundary)['status'],
                         'DEMO_RECONCILIATION_REQUIRED')
        self.broker.orders = [NS(comment='KD:other')]
        clock[0] = 1000. + 901
        boundary.reconcile()
        self.broker.fail = False
        self.assertEqual(self.send(replace(self.intent, intent_id='after'))['status'], 'DEMO_ACCEPTED')

    def test_pending_order_keeps_unknown_send_blocking(self):
        from hashlib import sha256
        self.broker.fail = True
        self.send()
        self.broker.orders = [NS(comment='KD:'+sha256(b'intent1').hexdigest()[:20])]
        boundary, clock = self.boundary_at(1000. + 5000)
        boundary.reconcile()
        self.assertEqual(self.send(replace(self.intent, intent_id='next'))['status'], 'DEMO_RECONCILIATION_REQUIRED')

    def test_closed_outcome_records_slippage_and_cost_split(self):
        self.send()
        deal = lambda **k: NS(magic=20261020, symbol='TEST', position_id=55, ticket=k.pop('ticket'), **k)
        self.broker.deals = [deal(ticket=789, entry=0, type=0, volume=.01, price=100.4, profit=0., commission=-.07, swap=0., fee=0.),
                             deal(ticket=790, entry=1, type=1, volume=.01, price=110., profit=9.6, commission=-.07, swap=-.2, fee=0.)]
        result = self.boundary.reconcile()
        self.assertEqual(result['closed'], 1)
        import sqlite3, json
        outcome = json.loads(sqlite3.connect(self.path).execute('SELECT outcome_json FROM demo_outbox').fetchone()[0])
        self.assertAlmostEqual(outcome['entry_slippage_price'], .4)
        self.assertAlmostEqual(outcome['commission_native'], -.14)
        self.assertAlmostEqual(outcome['swap_native'], -.2)
        self.assertFalse(outcome['live_authorized'])


if __name__ == '__main__': unittest.main()
