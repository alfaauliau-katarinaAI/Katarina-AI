"""Diagram acceptance with a synthetic broker: one lifecycle, zero real orders."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.intelligence.cognition.brain_runtime_control import CHECKPOINT
from katarina.engines.risk import RiskGovernor, RiskRequest
from katarina.memory import MemoryStore
from tests.unit.engines.test_execution_recovery import plan


class SyntheticBroker:
    """Invented prices, never a live terminal or proof of broker compatibility."""
    TIMEFRAME_M5, TIMEFRAME_M15, TIMEFRAME_H1 = 5, 15, 60
    COPY_TICKS_INFO = 1
    ACCOUNT_TRADE_MODE_DEMO = 0

    def __init__(self, *, active=False, flip_permission=False):
        self.now = int(datetime.now(timezone.utc).timestamp()) - 1
        self.active, self.flip_permission = active, flip_permission
        self.initializations = self.shutdowns = self.terminal_reads = self.orders = 0

    def initialize(self):
        self.initializations += 1
        return True

    def shutdown(self):
        self.shutdowns += 1

    def terminal_info(self):
        self.terminal_reads += 1
        return SimpleNamespace(connected=True, trade_allowed=self.active or
                               (self.flip_permission and self.terminal_reads >= 3))

    def account_info(self):
        return SimpleNamespace(balance=1000., equity=1000., margin=0., margin_free=1000., trade_mode=0)

    def positions_get(self):return ()
    def orders_get(self):return ()
    def history_deals_get(self, *args):return ()
    def symbols_get(self):
        return [SimpleNamespace(name=s, trade_mode=4) for s in ('EURUSD', 'GBPUSD', 'XAUUSD')]
    def symbol_info_tick(self, symbol):
        return SimpleNamespace(time=self.now+10800, bid=2000., ask=2000.1)
    def symbol_info(self, symbol):return SimpleNamespace(trade_mode=4)
    def symbol_select(self, symbol, value):return True
    def copy_ticks_range(self, symbol, start, end, flags):
        return [{'time_msc':(self.now+10800) * 1000, 'bid':2000., 'ask':2000.1}]
    def copy_rates_from_pos(self, symbol, frame, offset, count):
        last = ((self.now+10800) // (frame * 60)) * frame * 60
        return [dict(time=last-(130-i)*frame*60, open=1990+i*.05,
                     high=1991+i*.05, low=1989+i*.05, close=1990.2+i*.05,
                     tick_volume=100) for i in range(130)]
    def order_send(self, *args, **kwargs):
        self.orders += 1
        raise AssertionError('Real-order boundary was crossed')


class BrainOwnedWorkflowTests(unittest.TestCase):
    def test_complete_synthetic_observer_runs_inside_brain_and_releases_resources(self):
        broker = SyntheticBroker()
        with tempfile.TemporaryDirectory() as d:
            result = UnifiedKatarinaBrain.observe_once(Path(d), broker=broker, fetch_news=False)
            self.assertEqual(result['observed_symbols'], 3)
            report = json.loads((Path(d)/'latest.json').read_text())
            self.assertEqual(report['brain_architecture'], 'SINGLE_COGNITIVE_BRAIN')
            self.assertEqual(report['brain_runtime']['delivery'], 'DISABLED')
            self.assertEqual(report['orders_submitted'], 0)
            self.assertFalse(report['live_execution_authorized'])
            # Exercise real sensing/perception, not just three swallowed sensor failures.
            self.assertTrue(all('sensor_error:' not in '|'.join(x['blocking_reasons'])
                                for x in report['symbols'].values()))
            with MemoryStore(Path(d)/'cognitive-memory.sqlite3') as memory:
                self.assertEqual(memory.load_latest_operational_event(
                    'single_brain_runtime_audit_v1')['payload']['phase'], 'COMPLETE')
                self.assertEqual(memory.load_latest_operational_event(CHECKPOINT)['payload']['delivery'], 'DISABLED')
        self.assertEqual((broker.initializations, broker.shutdowns, broker.orders), (1, 1, 0))

    def test_active_terminal_refused_and_shutdown_even_before_memory_creation(self):
        broker = SyntheticBroker(active=True)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError, 'TRADING_MUST_BE_DISABLED'):
                UnifiedKatarinaBrain.observe_once(Path(d), broker=broker, fetch_news=False)
            self.assertFalse((Path(d)/'latest.json').exists())
        self.assertEqual(broker.shutdowns, 1)

    def test_permission_change_mid_cycle_cannot_publish_success(self):
        broker = SyntheticBroker(flip_permission=True)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError, 'PERMISSION_CHANGED'):
                UnifiedKatarinaBrain.observe_once(Path(d), broker=broker, fetch_news=False)
            self.assertFalse((Path(d)/'latest.json').exists())
        self.assertEqual(broker.orders, 0)

    def test_failure_is_audited_without_sensitive_message_and_lock_is_released(self):
        broker = SyntheticBroker()
        with tempfile.TemporaryDirectory() as d:
            with patch('katarina.intelligence.cognition.observer.BrainObserver.run',
                       side_effect=RuntimeError('sensitive account value')):
                with self.assertRaises(RuntimeError):
                    UnifiedKatarinaBrain.observe_once(Path(d), broker=broker, fetch_news=False)
            with MemoryStore(Path(d)/'cognitive-memory.sqlite3') as memory:
                event = memory.load_latest_operational_event('single_brain_runtime_audit_v1')
                self.assertEqual(event['payload']['phase'], 'BLOCKED')
                self.assertNotIn('sensitive', json.dumps(event))
            UnifiedKatarinaBrain.observe_once(Path(d), broker=broker, fetch_news=False)
        self.assertEqual(broker.shutdowns, 2)

    def test_risk_veto_cannot_be_bypassed_and_approval_still_cannot_send(self):
        db = sqlite3.connect(':memory:')
        with MemoryStore(':memory:') as memory:
            brain = UnifiedKatarinaBrain(db, memory)
            request = RiskRequest(.01, 0., 0., .1, 2., True, True)
            missing = brain.review_delivery('missing', request)
            allowed = brain.review_delivery('paper', request, governor=RiskGovernor())
            veto = brain.review_delivery('veto', RiskRequest(.5, 0., .5, .1, 2., False, False), governor=RiskGovernor())
            self.assertEqual(missing['risk_action'], 'NOT_REVIEWED')
            self.assertTrue(allowed['risk_allows_review'])
            self.assertFalse(veto['risk_allows_review'])
            for item in (missing, allowed, veto):
                self.assertEqual(item['delivery_status'], 'BLOCKED_LIVE_OFF')
                self.assertEqual(item['orders_submitted'], 0)
                self.assertFalse(item['queued_for_retry'])
        db.close()

    def test_capital_and_recovery_restart_preserve_reserve_without_replaying_intents(self):
        with tempfile.TemporaryDirectory() as d:
            db = sqlite3.connect(':memory:')
            path = Path(d)/'memory.sqlite3'
            with MemoryStore(path) as memory:
                brain = UnifiedKatarinaBrain(db, memory)
                brain.control.capital.initialize(10000)
                brain.control.capital.observe_balance(20000)
                result = brain.preview_recovery(plan(), side='BUY', current_stop=1990,
                                                position_origin='KATARINA', current_volume=.1, volume_step=.01)
                self.assertEqual(len(result['commands']), 2)
                self.assertEqual(result['orders_submitted'], 0)
            with MemoryStore(path) as memory:
                brain = UnifiedKatarinaBrain(db, memory)
                self.assertEqual(brain.control.capital.reserve_balance, 5000)
                self.assertFalse(brain.control.capital.observe_balance(20000).milestone_triggered)
                self.assertEqual(brain.preview_recovery(plan(), side='BUY', current_stop=1990,
                    position_origin='KATARINA', current_volume=.1, volume_step=.01)['commands'], [])
                self.assertEqual(brain.control.phase, 'OFFLINE')
            db.close()

    def test_manual_position_recovery_is_refused(self):
        db = sqlite3.connect(':memory:')
        with MemoryStore(':memory:') as memory:
            brain = UnifiedKatarinaBrain(db, memory)
            with self.assertRaises(PermissionError):
                brain.preview_recovery(plan(), side='BUY', current_stop=1990,
                    position_origin='MANUAL_DESKTOP', current_volume=.1, volume_step=.01)
        db.close()

    def test_checkpoint_validation_is_atomic_and_never_accepts_live_mode(self):
        from copy import deepcopy
        db = sqlite3.connect(':memory:')
        with MemoryStore(':memory:') as memory:
            brain = UnifiedKatarinaBrain(db, memory)
            brain.control.capital.initialize(10000)
            brain.control.checkpoint()
            saved = memory.load_latest_operational_event(CHECKPOINT)['payload']
            for corrupt in ('delivery', 'recovery', 'fraction'):
                payload = deepcopy(saved)
                payload['capital']['total_balance'] = 20000.
                payload['capital']['active_balance'] = 20000.
                if corrupt == 'delivery':payload['delivery'] = 'ENABLED'
                if corrupt == 'recovery':payload['recovery'] = {'foreign':{'origin':'MANUAL_DESKTOP'}}
                if corrupt == 'fraction':payload['capital']['reserve_fraction'] = .30
                with self.subTest(corrupt=corrupt), self.assertRaises(ValueError):
                    brain.control.restore(payload)
                self.assertEqual(brain.control.capital.total_balance, 10000.)
                self.assertEqual(brain.control.delivery.inspect('blocked',
                    RiskRequest(.01,0.,0.,.1,2.,True,True), None)['orders_submitted'], 0)
            from katarina.health.engine import HealthState
            brain.control.health.observe_health_event(
                {name+'_health':1 for name in ('data', 'transport', 'execution',
                 'reconciliation', 'journal', 'clock', 'snapshot')}, observed_at_ns=1)
            brain.control.health.observe_data_fresh(True)
            self.assertEqual(brain.control.health.evaluate(now_ns=1).data, HealthState.OK)
            brain.control.restore(saved)
            self.assertNotEqual(brain.control.health.evaluate(now_ns=1).data, HealthState.OK)
        db.close()

    def test_tampered_persistent_checkpoint_prevents_restart(self):
        db = sqlite3.connect(':memory:')
        with MemoryStore(':memory:') as memory:
            brain = UnifiedKatarinaBrain(db, memory)
            brain.control.checkpoint()
            with memory._conn:
                memory._conn.execute('DROP TRIGGER operational_events_no_update')
                memory._conn.execute("UPDATE operational_events SET payload_json='{}'")
            with self.assertRaisesRegex(ValueError, 'digest_mismatch'):
                UnifiedKatarinaBrain(db, memory)
        db.close()

    def test_reentrant_observer_is_rejected_before_second_broker_initialization(self):
        from katarina.intelligence.cognition.observer import BrainObserver
        original = BrainObserver.run
        first, second = SyntheticBroker(), SyntheticBroker()
        with tempfile.TemporaryDirectory() as d:
            def reenter(observer, **kwargs):
                with self.assertRaisesRegex(RuntimeError, 'ALREADY_RUNNING'):
                    UnifiedKatarinaBrain.observe_once(Path(d), broker=second, fetch_news=False)
                return original(observer, **kwargs)
            with patch.object(BrainObserver, 'run', reenter):
                UnifiedKatarinaBrain.observe_once(Path(d), broker=first, fetch_news=False)
        self.assertEqual(second.initializations, 0)
        self.assertEqual(first.shutdowns, 1)

    def test_unsafe_report_cannot_overwrite_previous_observation(self):
        db = sqlite3.connect(':memory:')
        with tempfile.TemporaryDirectory() as d, MemoryStore(':memory:') as memory:
            target = Path(d)/'latest.json'
            target.write_text('previous verified snapshot')
            brain = UnifiedKatarinaBrain(db, memory)
            with self.assertRaisesRegex(RuntimeError, 'safety_violation'):
                brain.publish_observation(Path(d), dict(orders_submitted=1,
                    live_execution_authorized=True, production_execution=True))
            self.assertEqual(target.read_text(), 'previous verified snapshot')
        db.close()

    def test_failed_sensor_stays_wait_and_does_not_approve_foundation(self):
        broker = SyntheticBroker()
        with tempfile.TemporaryDirectory() as d:
            with patch.object(broker, 'copy_ticks_range', return_value=()):
                UnifiedKatarinaBrain.observe_once(Path(d), broker=broker, fetch_news=False)
            report = json.loads((Path(d)/'latest.json').read_text())
            self.assertTrue(all(x['action']=='WAIT' for x in report['symbols'].values()))
            self.assertFalse(report['foundation_readiness']['engineering_checks']['sensors_without_errors'])
            self.assertEqual(report['brain_runtime']['pending_delivery_queue'], 0)
        self.assertEqual(broker.orders, 0)
