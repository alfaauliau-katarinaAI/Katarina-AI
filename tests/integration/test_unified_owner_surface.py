"""Actual HTTP -> same foreground brain -> tool -> memory, with bound sensors."""
from hashlib import sha256
import http.client
import json
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import patch

from katarina.adapters.automatic_connection import BoundLocalBroker
from katarina.adapters.continuous_owner_surface import owner_surface
from katarina.adapters.owner_access import authenticate, load_access, scoped_session
from katarina.adapters.owner_dialog_server import create_server
from katarina.intelligence.cognition.continuous_observation import run_continuous
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.memory.store import MemoryStore
from tests.integration.test_automatic_connection import AccountBroker, config

OWNER, ANALYST = 'owner-test-only-'+'x'*40, 'analyst-test-only-'+'y'*40


def policy(path, *, analyst_enabled=True):
    path.write_text(json.dumps(dict(schema_version=1, principals=[
        dict(id='owner', role='owner', token_sha256=sha256(OWNER.encode()).hexdigest(), enabled=True),
        dict(id='analyst', role='analyst', token_sha256=sha256(ANALYST.encode()).hexdigest(), enabled=analyst_enabled),
    ])), encoding='utf-8')


class UnifiedOwnerSurfaceTests(unittest.TestCase):
    def test_status_only_runs_on_same_brain_without_model_or_dialog_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            access = root/'access.json'; policy(access)
            ready, replies, made = queue.Queue(), queue.Queue(), []
            class Brain(UnifiedKatarinaBrain):
                def __init__(self, *args):
                    super().__init__(*args); made.append(self)
            def server(*args, **kwargs):
                result = create_server(*args, **kwargs)
                ready.put(result.server_port)
                return result
            def client():
                try:
                    port = ready.get(timeout=5)
                    rows = []
                    for route, token, body in [('/status', 'wrong', {}),
                            ('/status', OWNER, {}), ('/status', OWNER, {'grant':'shell'}),
                            ('/turn', OWNER, dict(text='Hello',session_id='owner',mode='auto'))]:
                        conn = http.client.HTTPConnection('127.0.0.1',port,timeout=5)
                        conn.request('POST',route,json.dumps(body),headers={'Authorization':'Bearer '+token})
                        response = conn.getresponse()
                        rows.append((response.status,json.loads(response.read())))
                        conn.close()
                    replies.put(rows)
                except Exception as error:
                    replies.put(error)
                finally:
                    (root/'continuous.stop').touch()
            thread = threading.Thread(target=client); thread.start()
            try:
                with patch('katarina.adapters.continuous_owner_surface.create_server',server):
                    result = run_continuous(root, config=config(priority=('local',),attempts=1),
                        factories={'local':lambda c:BoundLocalBroker(AccountBroker(),c)},brain_type=Brain,
                        surface_factory=owner_surface(state_dir=root,port=0,access_config=access))
                rows = replies.get(timeout=5)
                self.assertIsInstance(rows,list,rows)
                self.assertEqual([row[0] for row in rows],[403,200,400,200])
                self.assertEqual(rows[1][1]['surface_mode'],'STATUS_ONLY')
                self.assertFalse(rows[1][1]['dialog_available'])
                self.assertEqual(rows[1][1]['delivery'],'DISABLED')
                self.assertEqual(rows[3][1]['status'],'BLOCKED_MODEL_NOT_CONFIGURED')
                self.assertEqual(len(made),1)
                self.assertEqual(result['successful_cycles'],1)
                with MemoryStore(root/'cognitive-memory.sqlite3') as memory:
                    self.assertIsNone(memory.load_latest_operational_event('single_brain_dialog_v1'))
            finally:
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

    def test_http_dialog_sensor_and_memory_share_one_foreground_brain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            access = root/'access.json'; policy(access)
            ready, replies = queue.Queue(), queue.Queue()
            main_thread = threading.get_ident()
            native, made, model_threads = AccountBroker(), [], []
            class Brain(UnifiedKatarinaBrain):
                def __init__(self, *args):
                    super().__init__(*args); made.append(self)
            class Model:
                calls = 0
                def complete(self, *args, **kwargs):
                    model_threads.append(threading.get_ident())
                    self.calls += 1
                    return {'tool':'status','arguments':{}} if self.calls == 1 else {'answer':'LIVE OFF.'}
            def server(*args, **kwargs):
                result = create_server(*args, **kwargs)
                ready.put(result.server_port)
                return result
            def client():
                try:
                    conn = http.client.HTTPConnection('127.0.0.1', ready.get(timeout=5), timeout=5)
                    conn.request('POST', '/turn', json.dumps(dict(text='status',session_id='owner',mode='auto')),
                                 headers={'Authorization':'Bearer '+OWNER})
                    response = conn.getresponse()
                    replies.put((response.status, json.loads(response.read())))
                    conn.close()
                except Exception as error:
                    replies.put(error)
                finally:
                    (root/'continuous.stop').touch()
            thread = threading.Thread(target=client); thread.start()
            try:
                with patch('katarina.adapters.continuous_owner_surface.create_server', server):
                    result = run_continuous(root, config=config(priority=('local',), attempts=1),
                        factories={'local':lambda c:BoundLocalBroker(native,c)}, brain_type=Brain,
                        surface_factory=owner_surface(Model(),port=0,access_config=access))
                reply = replies.get(timeout=5)
                self.assertIsInstance(reply, tuple, reply)
                self.assertEqual(reply[0], 200)
                self.assertEqual(reply[1]['answer'], 'LIVE OFF.')
                self.assertEqual(reply[1]['trace'][0]['result']['delivery'], 'DISABLED')
                self.assertEqual(len(made), 1)
                self.assertTrue(all(t == main_thread for t in model_threads))
                self.assertEqual(result['successful_cycles'], 1)
                self.assertEqual(native.orders, 0)
                with MemoryStore(root/'cognitive-memory.sqlite3') as memory:
                    self.assertIsNotNone(memory.load_latest_operational_event('single_brain_dialog_v1'))
                    self.assertIsNotNone(memory.load_latest_operational_event('brain_hands_feedback_v1'))
            finally:
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

    def test_revocation_and_session_isolation_are_server_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp)/'access.json'; policy(access)
            owner = authenticate(access, 'Bearer '+OWNER)
            analyst = authenticate(access, 'Bearer '+ANALYST)
            self.assertNotEqual(scoped_session(owner,'owner'), scoped_session(analyst,'owner'))
            self.assertIsNone(authenticate(access, 'Bearer '+ANALYST+'wrong'))
            policy(access, analyst_enabled=False)
            self.assertIsNone(authenticate(access, 'Bearer '+ANALYST))
            self.assertIsNotNone(authenticate(access, 'Bearer '+OWNER))

    def test_missing_owner_duplicate_tokens_and_malformed_policy_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'access.json'; policy(path)
            rows = load_access(path)
            for altered in ([rows[1]], [rows[0], rows[0]], []):
                path.write_text(json.dumps(dict(schema_version=1,principals=altered)))
                with self.assertRaises(ValueError):
                    load_access(path)

    def test_analyst_cannot_acquire_research_tool(self):
        from scripts.pc.run_pretrial_acceptance import FixtureModel
        from katarina.intelligence.news.public_context import ContextStore
        class Server:
            def handle_request(self):
                pass
            def server_close(self):
                pass
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = ContextStore(root/'context.sqlite3')
            try:
                with MemoryStore(root/'cognitive-memory.sqlite3') as memory:
                    brain = UnifiedKatarinaBrain(context.db,memory)
                    calls = []
                    def make(turn, **kwargs):
                        calls.append(turn); return Server()
                    with patch('katarina.adapters.continuous_owner_surface.create_server',make):
                        with owner_surface(FixtureModel({'tool':'research','arguments':{}}))(brain):
                            result = calls[0]('research',session_id='analyst',principal={'id':'a','role':'analyst'})
                            self.assertEqual(result['status'], 'BLOCKED')
                            self.assertEqual(result['orders_submitted'], 0)
            finally:
                context.db.close()

    def test_actual_http_credential_scopes_revocation_and_client_grant_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp)/'access.json'; policy(access)
            seen = []
            def turn(text, **options):
                seen.append(options)
                return dict(answer='ok',trace=[],status='TEST')
            server = create_server(turn,port=0,access_config=access)
            try:
                def request(token, extra=None):
                    result = queue.Queue()
                    def client():
                        try:
                            conn = http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                            value = dict(text='status',session_id='owner',mode='auto')
                            value.update(extra or {})
                            conn.request('POST','/turn',json.dumps(value),headers={'Authorization':'Bearer '+token})
                            response = conn.getresponse(); result.put(response.status)
                            response.read(); conn.close()
                        except Exception as exc:
                            result.put(exc)
                    thread = threading.Thread(target=client); thread.start()
                    server.handle_request(); thread.join(timeout=4)
                    value = result.get(timeout=4)
                    self.assertIsInstance(value,int,value)
                    return value
                self.assertEqual(request(OWNER),200)
                self.assertEqual(request(ANALYST),200)
                self.assertNotEqual(seen[0]['session_id'],seen[1]['session_id'])
                self.assertEqual(seen[1]['principal']['role'],'analyst')
                self.assertEqual(request(ANALYST,dict(principal=dict(role='owner'))),400)
                policy(access,analyst_enabled=False)
                self.assertEqual(request(ANALYST),403)
                self.assertEqual(len(seen),2)
            finally:
                server.server_close()

    def test_agents_page_and_status_use_existing_authenticated_server(self):
        from katarina.monitoring.agent_projection import project_agent_board
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp)/'access.json'; policy(access)
            calls = []
            def status():
                calls.append('status')
                return {'agent_board': project_agent_board({'result': 'BLOCKED'})}
            server = create_server(lambda *a, **kw: self.fail('dashboard called turn'),
                                   port=0, access_config=access, status_callback=status)
            thread = threading.Thread(target=server.serve_forever); thread.start()
            try:
                def request(method, route, token=None):
                    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                    headers = {} if token is None else {'Authorization': 'Bearer '+token}
                    conn.request(method, route, '{}' if method == 'POST' else None, headers)
                    reply = conn.getresponse()
                    result = reply.status, reply.read().decode('utf-8')
                    conn.close()
                    return result
                code, page = request('GET', '/agents')
                self.assertEqual(code, 200)
                self.assertIn('Multi-Agent Intelligence', page)
                self.assertNotIn(OWNER, page)
                self.assertNotIn(ANALYST, page)
                self.assertEqual(request('POST', '/status', 'wrong')[0], 403)
                self.assertEqual(calls, [])
                code, body = request('POST', '/status', ANALYST)
                self.assertEqual(code, 200)
                board = json.loads(body)['agent_board']
                self.assertEqual(board['delivery'], 'DISABLED')
                self.assertEqual(board['agent_workers_started'], 0)
                self.assertFalse(board['live_execution_authorized'])
                self.assertEqual(len(board['lanes']), 6)
                policy(access, analyst_enabled=False)
                self.assertEqual(request('POST', '/status', ANALYST)[0], 403)
                self.assertEqual(calls, ['status'])
            finally:
                server.shutdown(); thread.join(timeout=4); server.server_close()
            self.assertFalse(thread.is_alive())

    def test_opt_in_public_dashboard_exposes_only_technical_status_and_no_commands(self):
        from katarina.monitoring.agent_projection import project_agent_board
        with tempfile.TemporaryDirectory() as tmp:
            access = Path(tmp)/'access.json'; policy(access)
            report = {'credential': 'PRIVATE_SENTINEL', 'agent_board': project_agent_board({
                'result': 'PASS_READONLY_SNAPSHOT_ONLY', 'received_market_data_symbols': 1,
                'cycles': 7, 'successful_cycles': 7, 'assessed_at_utc': '2026-10-19T11:00:00Z',
                'operational': {'technical_evaluations': [
                    dict(symbol='XAUUSD',market_state='TREND_UP',method='PULLBACK',
                         action='WAIT',private='PRIVATE_SENTINEL')],
                    'account_book_observed': True, 'positions_count': 123456,
                    'account_login': 'PRIVATE_SENTINEL'}})}
            board = report['agent_board']
            board.update(current_process_pid=42, snapshot_process_matches=True,
                         private='PRIVATE_SENTINEL',
                         model={'configured':False,'endpoint':'PRIVATE_SENTINEL','telemetry':None})
            for enabled in (False, True):
                server = create_server(lambda *a, **kw: self.fail('public route called turn'),
                    port=0, access_config=access, status_callback=lambda:report, public_status=enabled)
                thread = threading.Thread(target=server.serve_forever); thread.start()
                try:
                    def request(method, path):
                        conn = http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                        conn.request(method,path,'{}' if method == 'POST' else None)
                        reply=conn.getresponse()
                        data=(reply.status,reply.read().decode(),reply.getheader('Cache-Control'))
                        conn.close(); return data
                    self.assertEqual(request('POST','/turn')[0],403)
                    self.assertEqual(request('POST','/status')[0],403)
                    code, body, cache = request('GET','/public-status')
                    self.assertEqual(code,200 if enabled else 404)
                    if enabled:
                        self.assertEqual(cache,'no-store')
                        self.assertNotIn('PRIVATE_SENTINEL',body)
                        self.assertNotIn('positions_count',body)
                        self.assertNotIn('account_login',body)
                        public=json.loads(body)
                        self.assertEqual(public['view_mode'],'PUBLIC_READONLY')
                        self.assertFalse(public['dialog_available'])
                        self.assertEqual(public['agent_board']['operational']['technical_evaluations'][0]['action'],'WAIT')
                        self.assertEqual(public['delivery'],'DISABLED')
                        code, page, _ = request('GET','/')
                        self.assertEqual(code,200)
                        self.assertIn('const PUBLIC_STATUS = true;',page)
                        self.assertIn('class="public-status"',page)
                        self.assertNotIn(OWNER,page)
                    else:
                        self.assertNotIn('const PUBLIC_STATUS = true;',request('GET','/agents')[1])
                finally:
                    server.shutdown();thread.join(timeout=4);server.server_close()

    def test_public_status_failure_returns_no_partial_owner_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            access=Path(tmp)/'access.json';policy(access)
            server=create_server(lambda *a,**k:None,port=0,access_config=access,
                                 public_status=True,status_callback=lambda:{'secret':'PRIVATE_SENTINEL'})
            thread=threading.Thread(target=server.serve_forever);thread.start()
            try:
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                conn.request('GET','/public-status');reply=conn.getresponse()
                self.assertEqual(reply.status,503)
                self.assertNotIn('PRIVATE_SENTINEL',reply.read().decode())
                conn.close()
            finally:
                server.shutdown();thread.join(timeout=4);server.server_close()
