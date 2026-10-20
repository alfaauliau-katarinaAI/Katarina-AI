from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from katarina.intelligence.runtime_evidence import assess_runtime, read_runtime


class RuntimeEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 16, 11, 30, tzinfo=timezone.utc)
        stamp = self.now.isoformat()
        self.status = dict(heartbeat_utc=stamp, last_success_utc=stamp,
            status='WAITING', consecutive_failures=0, orders_submitted=0,
            live_execution_authorized=False, production_execution=False,
            background_workers=0, received_market_data_symbols=1, cycles=4, successful_cycles=4)
        self.observation = dict(observed_at_utc=stamp, market_snapshot_tick_utc=stamp,
            orders_submitted=0, live_execution_authorized=False, production_execution=False,
            received_market_data_symbols=1, observed_symbols=1,
            brain_hands_feedback=dict(status='ACKNOWLEDGED_LIVE_OFF', orders_submitted=0,
                broker_order_execution_verified=False, receipts=[dict(feedback_id='receipt1',
                    message_sha256='a'*64, status='ACKNOWLEDGED_LIVE_OFF',
                    orders_submitted=0, live_execution_authorized=False)]))

    def assess(self, status=None, observation=None):
        return assess_runtime(self.status if status is None else status,
            self.observation if observation is None else observation, now=self.now)

    def test_healthy_readonly_snapshot_never_clears_live(self):
        result = self.assess()
        self.assertEqual(result['result'], 'PASS_READONLY_SNAPSHOT_ONLY')
        for key in ('live_clearance', 'broker_execution_verified', 'model_quality_verified', 'phone_tls_verified'):
            self.assertIs(result[key], False)

    def test_heartbeat_cannot_hide_stale_data_or_future_clock(self):
        for offset in (-181, 1):
            observation = deepcopy(self.observation)
            observation['market_snapshot_tick_utc'] = (self.now+timedelta(seconds=offset)).isoformat()
            self.assertIn('MARKET_TICK_MISSING_OR_STALE', self.assess(observation=observation)['blockers'])

    def test_missing_and_boolean_safety_counters_fail_closed(self):
        for key, value in [('orders_submitted', False), ('production_execution', None),
                           ('live_execution_authorized', True), ('successful_cycles', True),
                           ('background_workers', False)]:
            status = dict(self.status, **{key: value})
            self.assertEqual(self.assess(status=status)['result'], 'BLOCKED')

    def test_duplicate_missing_and_executable_receipts_block(self):
        for change in ('duplicate', 'missing', 'unsafe', 'malformed'):
            observation = deepcopy(self.observation)
            receipts = observation['brain_hands_feedback']['receipts']
            if change == 'duplicate':
                receipts.append(dict(receipts[0]))
                observation.update(observed_symbols=2, received_market_data_symbols=2)
            elif change == 'missing':
                receipts.clear()
            elif change == 'unsafe':
                receipts[0]['orders_submitted'] = 1
            else:
                receipts[0] = []
            self.assertIn('WAIT_FEEDBACK_INCOMPLETE_OR_INVALID', self.assess(observation=observation)['blockers'])

    def test_stopped_and_partial_data_block(self):
        self.assertIn('OBSERVER_NOT_HEALTHY', self.assess(status=dict(self.status, status='STOPPED'))['blockers'])
        self.assertIn('MARKET_DATA_INCOMPLETE_OR_INCONSISTENT',
            self.assess(observation=dict(self.observation, observed_symbols=2))['blockers'])

    def test_reads_without_changes_and_never_exports_private_fields(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            self.observation['secret_account_field'] = 'PRIVATE_VALUE'
            for name, data in [('continuous-status.json', self.status), ('latest.json', self.observation)]:
                (path/name).write_text(json.dumps(data))
            before = {p.name: p.read_bytes() for p in path.iterdir()}
            result = read_runtime(root, now=self.now)
            self.assertEqual(result['result'], 'PASS_READONLY_SNAPSHOT_ONLY')
            self.assertNotIn('PRIVATE_VALUE', json.dumps(result))
            self.assertEqual(before, {p.name: p.read_bytes() for p in path.iterdir()})
            (path/'latest.json').write_text('{broken')
            self.assertIn('SNAPSHOT_UNREADABLE_OR_INVALID', read_runtime(root, now=self.now)['blockers'])

    def test_nonobject_snapshots_block(self):
        self.assertEqual(self.assess(status=[])['result'], 'BLOCKED')

    def test_bounded_research_pool_and_matching_doctor_remain_live_off(self):
        roles=[dict(phase=f'TEST_{family}_H{h}',live_authorized=False)
               for family in ('MOMENTUM','REVERSION','BREAKOUT') for h in (4,12,24)]
        status=dict(self.status,pid=42,background_workers=13,
                    research_worker=dict(background_workers=13,research_workers=12,
                                         status='RUNNING',live_authorized=False,workers=roles))
        self.assertEqual(self.assess(status=status)['result'],'PASS_READONLY_SNAPSHOT_ONLY')
        status.update(background_workers=14,network_doctor=dict(pid=42,status='HEALTHY',as_of_utc=self.now.isoformat()))
        result=self.assess(status=status)
        self.assertEqual(result['result'],'PASS_READONLY_SNAPSHOT_ONLY')
        self.assertFalse(result['live_clearance'])
        status['network_doctor']['pid']=99
        self.assertIn('UNEXPECTED_BACKGROUND_WORKERS',self.assess(status=status)['blockers'])
        status['network_doctor']['pid']=42
        status['research_worker']['workers'][0]['live_authorized']=True
        self.assertIn('UNEXPECTED_BACKGROUND_WORKERS',self.assess(status=status)['blockers'])
