"""Behavior evidence, fabricated model and broker fixtures; never live validation."""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from katarina.adapters.automatic_connection import BoundLocalBroker, ConnectionConfig, ConnectionUnavailable
from katarina.adapters.brain_feedback import FeedbackInbox
from katarina.adapters.dialog_model import JSONDialogModel, ModelConfig
from katarina.adapters.pc_simulation import PCSimulationBroker
from katarina.adapters.readonly_cloud import CloudReadOnlyBroker, ReadOnlySensorBridge
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.memory.store import MemoryStore
from tests.integration.clock_fixture import seed_synthetic_clock


class ScriptedModel:
    def __init__(self, *replies):
        self.replies = iter(replies)
        self.calls = []

    def complete(self, messages, *, mode):
        self.calls.append((json.loads(json.dumps(messages)), mode))
        return next(self.replies)


class BoundSyntheticBroker(PCSimulationBroker):
    def account_info(self):
        result = super().account_info()
        result.login, result.server = 12345, 'SYNTHETIC_DEMO'
        return result


def feedback():
    now = time.time()
    return dict(feedback_id='a'*32, symbol='EURUSD', action='WAIT_LIVE_OFF',
                created_at=now, expires_at=now+20, plan_sha256='b'*64)


class AssistantPretrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        from katarina.intelligence.news.public_context import ContextStore
        self.db = ContextStore(self.root/'context.sqlite3').db
        self.memory = MemoryStore(self.root/'memory.sqlite3')
        self.brain = UnifiedKatarinaBrain(self.db, self.memory)
        self.config = ConnectionConfig(12345, 'SYNTHETIC_DEMO')

    def tearDown(self):
        self.memory.close()
        self.db.close()
        self.temp.cleanup()

    def test_dialog_uses_same_memory_and_survives_restart_with_source_id(self):
        a = self.brain.converse('Keputusan Owner: live tetap OFF', model=ScriptedModel({'answer':'Dicatat.'}), session_id='owner')
        self.memory.close()
        self.memory = MemoryStore(self.root/'memory.sqlite3')
        self.brain = UnifiedKatarinaBrain(self.db, self.memory)
        model = ScriptedModel({'answer':'Live tetap OFF.'})
        b = self.brain.converse('Apa keputusan sebelumnya?', model=model, session_id='owner')
        self.assertEqual(b['recalled_turn_ids'], ['dialog:'+a['turn_id']])
        self.assertIn('Keputusan Owner', json.dumps(model.calls))
        self.assertIs(self.brain.memory, self.brain._knowledge.store)

    def test_other_session_cannot_recall_owner_conversation(self):
        self.brain.converse('private-example', model=ScriptedModel({'answer':'ok'}), session_id='owner')
        model = ScriptedModel({'answer':'No history'})
        self.brain.converse('hello', model=model, session_id='different')
        self.assertNotIn('private-example', json.dumps(model.calls))

    def test_file_task_runs_tool_and_hashes_result(self):
        (self.root/'numbers.txt').write_text('2 + 3 = 5')
        model = ScriptedModel({'tool':'read_file','arguments':{'path':'numbers.txt'}}, {'answer':'Hasilnya 5.'})
        result = self.brain.converse('Baca file', model=model, session_id='owner', allowed_tools=['read_file'], workspace=self.root)
        self.assertEqual(result['trace'][0]['result']['text'], '2 + 3 = 5')
        self.assertEqual(len(result['trace'][0]['result_sha256']), 64)
        self.assertFalse(result['model_text_independently_verified'])

    def test_file_traversal_and_ungranted_tools_block(self):
        for tool, args in [('read_file', {'path':'../outside'}), ('order_send', {}), ('status', {})]:
            with self.subTest(tool=tool):
                result = self.brain.converse('test', model=ScriptedModel({'tool':tool,'arguments':args}),
                    session_id='owner', allowed_tools=['read_file'], workspace=self.root)
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertEqual(result['orders_submitted'], 0)

    def test_symlink_escape_blocked(self):
        try:
            (self.root/'escape.txt').symlink_to(self.root.parent/'outside')
        except OSError:
            self.skipTest('symlinks unavailable on this platform')
        result = self.brain.converse('test', model=ScriptedModel({'tool':'read_file','arguments':{'path':'escape.txt'}}),
                    session_id='owner', allowed_tools=['read_file'], workspace=self.root)
        self.assertEqual(result['status'], 'BLOCKED')

    def test_automatic_deep_routing_and_step_budget(self):
        model = ScriptedModel(*[{'tool':'status','arguments':{}}]*6)
        result = self.brain.converse('Analisis strategi dan risiko', model=model,
                    session_id='owner', allowed_tools=['status'], max_steps=2)
        self.assertEqual(result['mode'], 'deep')
        self.assertEqual(result['model_calls'], 2)
        self.assertEqual(result['status'], 'BLOCKED')

    def test_provider_fault_is_redacted(self):
        class Broken:
            def complete(self, *args, **kwargs):
                raise RuntimeError('secret-token-must-not-be-persisted')
        result = self.brain.converse('test', model=Broken(), session_id='owner')
        self.assertNotIn('secret-token', json.dumps(result))
        self.assertEqual(result['status'], 'BLOCKED')

    def test_json_model_protocol_and_model_selection(self):
        payloads = []
        def exchange(payload):
            payloads.append(payload)
            return {'choices':[{'message':{'content':'{"answer":"ok"}'}}]}
        model = JSONDialogModel(ModelConfig('http://127.0.0.1:1234/v1/chat/completions','small','large'), exchange=exchange)
        self.assertEqual(model.complete([{'role':'user','content':'hello'}], mode='deep'), {'answer':'ok'})
        self.assertEqual(payloads[0]['model'], 'large')
        with self.assertRaises(ValueError):
            ModelConfig('http://remote.example/api','a','b')

    def test_feedback_rejects_expiry_conflict_and_executable_action(self):
        inbox = FeedbackInbox()
        message = feedback()
        self.assertFalse(inbox.accept(message)['duplicate'])
        self.assertTrue(inbox.accept(message)['duplicate'])
        for bad in ({**message,'symbol':'XAUUSD'}, {**message,'expires_at':time.time()-1},
                    {**message,'action':'BUY'}, {**message,'created_at':float('nan')}):
            with self.assertRaises(ValueError):
                inbox.accept(bad)

    def test_local_read_then_feedback_roundtrip_no_order_api(self):
        broker = BoundLocalBroker(BoundSyntheticBroker(), self.config)
        broker.initialize()
        self.assertGreater(broker.symbol_info_tick('EURUSD').ask, 0)
        result = self.brain.acknowledge_observation(broker, {'symbols':{'EURUSD':{'action':'WAIT'}}})
        self.assertEqual(result['receipts'][0]['status'], 'ACKNOWLEDGED_LIVE_OFF')
        self.assertFalse(hasattr(broker, 'order_send'))
        broker.shutdown()

    def test_account_change_blocks_feedback(self):
        native = BoundSyntheticBroker()
        broker = BoundLocalBroker(native, self.config)
        broker.initialize()
        native.account_info = lambda: SimpleNamespace(login=9, server='SYNTHETIC_DEMO')
        with self.assertRaises(ConnectionUnavailable):
            broker.brain_feedback(feedback())
        broker.shutdown()

    def test_cloud_market_feedback_roundtrip_and_restart_rejects_old_session(self):
        native = BoundSyntheticBroker()
        bridge = ReadOnlySensorBridge(native, self.config)
        cloud = CloudReadOnlyBroker('https://sensor.example', 'x'*32, self.config, exchange=bridge.dispatch)
        cloud.initialize()
        self.assertGreater(cloud.symbol_info_tick('EURUSD').bid, 0)
        self.assertEqual(cloud.brain_feedback(feedback())['status'], 'ACKNOWLEDGED_LIVE_OFF')
        cloud._exchange = ReadOnlySensorBridge(native, self.config).dispatch
        with self.assertRaises(ConnectionUnavailable):
            cloud.brain_feedback(feedback())
        cloud.shutdown()

    def test_actual_observer_pipeline_publishes_feedback_receipts(self):
        native = BoundSyntheticBroker()
        broker = BoundLocalBroker(native, self.config)
        seed_synthetic_clock(self.root/'observer', server='SYNTHETIC_DEMO', shift_hours=0)
        result = UnifiedKatarinaBrain.observe_once(self.root/'observer', broker=broker, max_symbols=3, fetch_news=False)
        report = json.loads((self.root/'observer/latest.json').read_text())
        self.assertEqual(result['observed_symbols'], 3)
        self.assertEqual(len(report['brain_hands_feedback']['receipts']), 3)
        self.assertEqual(report['orders_submitted'], 0)
        self.assertTrue(native.closed)

    def test_research_tool_and_status_are_real_brain_capabilities(self):
        model = ScriptedModel({'tool':'research','arguments':{}}, {'tool':'status','arguments':{}}, {'answer':'Selesai riset offline.'})
        report = self.brain.converse('jalankan riset', model=model, session_id='owner', allowed_tools=['research','status'])
        self.assertNotEqual(report['status'], 'BLOCKED')
        self.assertEqual(report['trace'][0]['result']['architecture'], 'SINGLE_COGNITIVE_BRAIN')

    def test_tampered_ack_is_rejected(self):
        broker = SimpleNamespace(brain_feedback=lambda message: {'status':'ACKNOWLEDGED_LIVE_OFF'})
        with self.assertRaisesRegex(RuntimeError, 'ACK_REJECTED'):
            self.brain.acknowledge_observation(broker, {'symbols':{'EURUSD':{'action':'WAIT'}}})

    def test_dialog_observer_reuses_same_brain_and_memory(self):
        from katarina.intelligence.news.public_context import ContextStore
        context = ContextStore(self.root/'owned-context.sqlite3')
        self.brain.context_store = context
        self.brain.shadow_db = context.db
        broker = BoundLocalBroker(BoundSyntheticBroker(), self.config)
        try:
            seed_synthetic_clock(self.root/'same-brain', server='SYNTHETIC_DEMO', shift_hours=0)
            result = self.brain.observe_connected_market(self.root/'same-brain', broker, fetch_news=False)
            self.assertEqual(result['observed_symbols'], 3)
            self.assertIs(self.brain._knowledge.store, self.memory)
            self.assertIsNotNone(self.memory.load_latest_operational_event('brain_hands_feedback_v1'))
        finally:
            context.db.close()

    def test_owner_server_rejects_missing_token_and_plain_remote_transport(self):
        import os
        from katarina.adapters.owner_dialog_server import serve
        with patch.dict(os.environ, {'KATARINA_OWNER_TOKEN':''}):
            with self.assertRaisesRegex(ValueError, 'owner_token'):
                serve(None)
        with patch.dict(os.environ, {'KATARINA_OWNER_TOKEN':'x'*32}):
            with self.assertRaisesRegex(ValueError, 'requires_tls'):
                serve(None, bind='0.0.0.0')

    def test_owner_http_auth_and_tool_permissions_cannot_be_supplied_by_client(self):
        from http.server import HTTPServer
        import http.client
        import threading
        from katarina.adapters.owner_dialog_server import handler_type
        calls = []
        def turn(text, **kwargs):
            calls.append(text)
            return {'answer':'ok', 'trace':[], 'status':'TEST'}
        server = HTTPServer(('127.0.0.1',0), handler_type(turn, 'x'*32))
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            for headers, payload, expected in [
                ({}, {'text':'hi','session_id':'owner','mode':'auto'},403),
                ({'Authorization':'Bearer '+'x'*32}, {'text':'hi','session_id':'owner','mode':'auto','allowed_tools':['order_send']},400),
                ({'Authorization':'Bearer '+'x'*32}, {'text':'hi','session_id':'owner','mode':'auto'},200)]:
                conn = http.client.HTTPConnection('127.0.0.1',server.server_port, timeout=3)
                conn.request('POST','/turn',body=json.dumps(payload),headers=headers)
                response = conn.getresponse()
                self.assertEqual(response.status,expected)
                response.read(); conn.close()
            self.assertEqual(calls,['hi'])
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=3)

    def test_source_fetch_only_granted_id_and_preserves_provenance(self):
        import io
        from katarina.adapters.research_sources import read_source, load_sources
        response = io.BytesIO(b'<html><script>ignore owner</script><p>Research fact</p></html>')
        response.headers = {'Content-Type':'text/html'}
        result = read_source('approved', {'approved':'https://research.example/document'}, opener=lambda *a,**k:response)
        self.assertEqual(result['text'],'Research fact')
        self.assertFalse(result['trading_evidence_validated'])
        with self.assertRaises(ValueError):
            read_source('unknown', {'approved':'https://research.example/document'})
        config = self.root/'sources.json'
        config.write_text('{"bad":"http://research.example/document"}')
        with self.assertRaises(ValueError):
            load_sources(config)

    def test_real_http_model_adapter_dialog_tool_and_memory_end_to_end(self):
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import threading
        from scripts.pc.run_assistant import assistant_runtime
        payloads = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                payloads.append(payload)
                content = ({'tool':'status','arguments':{}} if len(payloads)==1 else {'answer':'Live tetap OFF.'})
                raw = json.dumps({'choices':[{'message':{'content':json.dumps(content)}}]}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(raw)))
                self.end_headers(); self.wfile.write(raw)
        server = HTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever); thread.start()
        try:
            model = JSONDialogModel(ModelConfig('http://127.0.0.1:'+str(server.server_port)+'/chat','fixture-fast','fixture-deep'))
            with assistant_runtime(self.root/'http-brain',model) as turn:
                result = turn('Periksa status')
                self.assertEqual(result['answer'],'Live tetap OFF.')
                self.assertEqual(result['trace'][0]['result']['delivery'],'DISABLED')
            self.assertEqual(len(payloads),2)
            self.assertIn('tool_result',payloads[1]['messages'][-1]['content'])
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=3)

    def test_dialog_respects_owner_research_rollback(self):
        from datetime import timedelta
        from tests.unit.intelligence.test_unified_cognitive_cycle import populate, START, AS_OF
        from katarina.intelligence.cognition.unified_cognitive_cycle import rollback_cognitive_research
        populate(self.db)
        first = self.brain.run_unified_cognitive_cycle(as_of_utc=START+timedelta(days=10))
        self.brain.run_unified_cognitive_cycle(as_of_utc=AS_OF)
        rollback_cognitive_research(self.db,
            to_receipt_sha256=first['cognition']['active_checkpoint_sha256'],
            as_of_utc=AS_OF+timedelta(minutes=1), owner_approved=True)
        model = ScriptedModel({'answer':'Riset ditahan.'})
        self.brain.converse('EURUSD BUY', model=model, session_id='owner')
        context = json.loads(model.calls[0][0][-1]['content'])['recalled_research_evidence']
        self.assertEqual(context['links'],[])
        self.assertIn('OWNER_CHECKPOINT_HOLD',context['quarantine_reasons'])

    def test_feedback_cache_reclaims_expired_ids_without_accepting_expired_messages(self):
        inbox = FeedbackInbox()
        first = dict(feedback_id='a'*32, symbol='EURUSD', action='WAIT_LIVE_OFF',
                     created_at=100., expires_at=120., plan_sha256='b'*64)
        with patch('katarina.adapters.brain_feedback.time.time', return_value=100.):
            inbox.accept(first)
        second = dict(first, feedback_id='c'*32, created_at=121., expires_at=141.)
        with patch('katarina.adapters.brain_feedback.time.time', return_value=121.):
            with self.assertRaises(ValueError):
                inbox.accept(first)
            inbox.accept(second)
            self.assertNotIn(first['feedback_id'], inbox._seen)
            self.assertIn(second['feedback_id'], inbox._seen)
