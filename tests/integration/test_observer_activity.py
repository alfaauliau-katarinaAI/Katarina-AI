"""A real offline observer emits events only around its existing execution path."""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import tempfile
import unittest
from katarina.adapters.automatic_connection import BoundLocalBroker
from katarina.intelligence.continuous_observation import run_continuous
from katarina.monitoring.activity_trace import read_activity
from katarina.monitoring.public_runtime import build_public_runtime
from katarina.intelligence.unified_brain import UnifiedKatarinaBrain
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
            for phase in ('NEWS','SENSORS','MEMORY','SETTLE','CHECKPOINT','LEARNING_REVIEW',
                          'RESEARCH','MEMORY_WRITE','RECALL','ASSOCIATION','RISK_AUDIT','WAIT_ACK','PUBLISH'):
                self.assertIn((phase,'STARTED'),phases)
                self.assertIn((phase,'DONE'),phases)
            self.assertEqual(activity['current']['phase'],'STOPPED')
            symbols=[e for e in activity['events'] if e['phase']=='TECHNICAL' and e['state']=='DONE']
            self.assertGreater(len(symbols),0)
            self.assertTrue(all(e['symbol'] and e['method'] and e['action'] for e in symbols))
            public=build_public_runtime(root)
            self.assertEqual(public['agent_board']['result'],'BLOCKED')
            self.assertFalse(public['agent_board']['live_execution_authorized'])

    def test_transient_clock_failure_is_recorded_and_next_cycle_recovers_without_orders(self):
        class GlitchBrain(UnifiedKatarinaBrain):
            attempts=0
            def observe_connected_market(self,*args,**kwargs):
                self.attempts+=1
                if self.attempts==1:
                    raise RuntimeError('BROKER_CLOCK_NOT_VERIFIED')
                return super().observe_connected_market(*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            broker=AccountBroker();root=Path(tmp)
            result=run_continuous(root,config=config(priority=('local',),attempts=1),
                factories={'local':lambda c:BoundLocalBroker(broker,c)},brain_type=GlitchBrain,
                max_symbols=3,max_cycles=2,wait=lambda _:None)
            self.assertEqual(result['cycles'],2)
            self.assertEqual(result['successful_cycles'],1)
            self.assertEqual(result['consecutive_failures'],0)
            self.assertEqual(broker.orders,0)
            events=read_activity(root)['events']
            self.assertTrue(any(e['phase']=='SENSORS' and e['state']=='FAILED'
                and e.get('action')=='BROKER_CLOCK_NOT_VERIFIED' for e in events))
            self.assertTrue(any(e['phase']=='DEGRADED' for e in events))

    def test_permission_and_unexpected_runtime_failures_still_stop_the_observer(self):
        for message in ('FAIL_CLOSED_TRADING_MUST_BE_DISABLED','UNEXPECTED_INTEGRITY_FAILURE'):
            class BrokenBrain(UnifiedKatarinaBrain):
                def observe_connected_market(self,*args,**kwargs):
                    raise RuntimeError(message)
            with tempfile.TemporaryDirectory() as tmp:
                broker=AccountBroker();root=Path(tmp)
                with self.assertRaises(RuntimeError):
                    run_continuous(root,config=config(priority=('local',),attempts=1),
                        factories={'local':lambda c:BoundLocalBroker(broker,c)},brain_type=BrokenBrain,
                        max_symbols=3,max_cycles=2,wait=lambda _:None)
                self.assertEqual(read_activity(root)['current']['phase'],'BLOCKED')
                self.assertEqual(broker.orders,0)

    def test_conditional_research_hypothesis_uses_the_existing_atr_engine(self):
        calls=[]
        class CandidateBrain(UnifiedKatarinaBrain):
            def evaluate_contextually(self,**evidence):
                card=super().evaluate_contextually(**evidence)
                price=evidence['candles']['M5'][-1].close
                return replace(card,conditional_side='BUY',
                    conditional_invalidation=price*.5,conditional_target=price*1.5)
            def market_atr(self,rows):
                calls.append(len(rows))
                return super().market_atr(rows)
        with tempfile.TemporaryDirectory() as tmp:
            broker=AccountBroker();root=Path(tmp)
            # Force this engineering branch, not a profitable strategy or live permission.
            with patch('katarina.intelligence.brain_observer.calendar_status',
                       return_value=(True,False,'fixture_calendar')):
                result=run_continuous(root,config=config(priority=('local',),attempts=1),
                    factories={'local':lambda c:BoundLocalBroker(broker,c)},brain_type=CandidateBrain,
                    max_symbols=3,max_cycles=1)
            self.assertGreater(len(calls),0)
            self.assertTrue(all(n>=55 for n in calls))
            self.assertEqual(result['received_market_data_symbols'],result['observed_symbols'] if 'observed_symbols' in result else 3)
            import json
            report=json.loads((root/'latest.json').read_text(encoding='utf-8'))
            self.assertTrue(all(card['market_state']!='UNKNOWN' for card in report['symbols'].values()))
            self.assertTrue(all(card['live_execution_authorized'] is False for card in report['symbols'].values()))
            self.assertEqual(broker.orders,0)
