"""Actual event provenance, relay authentication/privacy, expiry and replay checks."""
from datetime import datetime,timedelta,timezone
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from katarina.monitoring.activity_trace import ActivityTrace,clean_activity,read_activity
from katarina.monitoring.monitor_relay import SnapshotBuffer,create_relay
from katarina.monitoring.monitor_publisher import publish_once

def fixture(now):
    return {'captured_at_utc':now.isoformat(),'private':'PRIVATE_SENTINEL','agent_board':{
        'result':'SNAPSHOT_PASS','market_symbols':1,'cycles':2,'successful_cycles':2,
        'observed_at_utc':now.isoformat(),'delivery':'DISABLED','current_process_pid':42,
        'snapshot_process_matches':True,'private':'PRIVATE_SENTINEL','blockers':[],
        'operational':{'account_login':'PRIVATE_SENTINEL','positions_count':123,
            'technical_evaluations':[dict(symbol='XAUUSD',market_state='TREND_UP',
                method='PULLBACK',action='WAIT',private='PRIVATE_SENTINEL')]},
        'activity':dict(pid=42,cycle=2,events=[dict(seq=1,at_utc=now.isoformat(),
            phase='TECHNICAL',state='DONE',symbol='XAUUSD',secret='PRIVATE_SENTINEL')]),
        'model':{'configured':False,'endpoint':'PRIVATE_SENTINEL','telemetry':None}}}

class RuntimeMonitorTests(unittest.TestCase):
    def test_events_are_bounded_redacted_and_expire(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace=ActivityTrace(tmp)
            for _ in range(90):
                trace.emit('TECHNICAL','DONE',symbol='XAUUSD',method='PULLBACK',secret='PRIVATE_SENTINEL')
            data=read_activity(tmp)
            self.assertEqual(len(data['events']),80)
            self.assertEqual(data['current']['seq'],90)
            self.assertNotIn('PRIVATE_SENTINEL',json.dumps(data))
            self.assertTrue(data['fresh'])
            stale=clean_activity(data,now=datetime.now(timezone.utc)+timedelta(seconds=181))
            self.assertFalse(stale['fresh'])
            with self.assertRaises(ValueError):trace.emit('INVENTED_NEURON','DONE')

    def test_relay_strips_private_data_rejects_replays_and_expires(self):
        clock=[datetime.now(timezone.utc)]
        buffer=SnapshotBuffer(now=lambda:clock[0])
        report=fixture(clock[0])
        buffer.accept(report)
        saved=buffer.read()
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(saved))
        self.assertNotIn('positions_count',json.dumps(saved))
        self.assertEqual(saved['agent_board']['activity']['current']['phase'],'TECHNICAL')
        self.assertEqual(saved['agent_board']['operational']['technical_evaluations'][0]['action'],'WAIT')
        with self.assertRaises(ValueError):buffer.accept(report)
        clock[0]+=timedelta(seconds=121)
        self.assertIsNone(buffer.read())
        with self.assertRaises(ValueError):buffer.accept(fixture(clock[0]-timedelta(seconds=121)))

    def test_actual_http_relay_has_no_owner_or_broker_control_route(self):
        token='test-only-'+'x'*40
        server=create_relay(token=token)
        thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            def request(method,path,body=None,key=None):
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                headers={'Content-Type':'application/json'}
                if key:headers['Authorization']='Bearer '+key
                conn.request(method,path,json.dumps(body) if body is not None else None,headers)
                reply=conn.getresponse();result=(reply.status,reply.read().decode())
                conn.close();return result
            self.assertEqual(request('GET','/healthz')[0],200)
            self.assertEqual(request('GET','/public-status')[0],503)
            self.assertIn('const PUBLIC_STATUS = true;',request('GET','/')[1])
            self.assertEqual(request('POST','/ingest',fixture(datetime.now(timezone.utc)))[0],403)
            self.assertEqual(request('POST','/turn',{},token)[0],403)
            self.assertEqual(request('POST','/status',{},token)[0],403)
            self.assertEqual(request('POST','/ingest',fixture(datetime.now(timezone.utc)),token)[0],202)
            status,body=request('GET','/public-status')
            self.assertEqual(status,200)
            self.assertNotIn('PRIVATE_SENTINEL',body)
            self.assertEqual(json.loads(body)['transport'],'VPS_SIGNED_TELEMETRY')
            self.assertEqual(request('POST','/ingest',{'bad':'PRIVATE_SENTINEL'},token)[0],400)
        finally:
            server.shutdown();thread.join(timeout=4);server.server_close()

    def test_publisher_rejects_insecure_or_unexpected_destinations_before_reading_state(self):
        for endpoint in ('http://test.onrender.com/ingest','https://evil.example/ingest',
                         'https://test.onrender.com/ingest?token=PRIVATE'):
            with self.assertRaises(ValueError):
                publish_once('unused',dict(endpoint=endpoint,token='x'*40))

    def test_publisher_uses_official_site_service_access_only_for_its_exact_origin(self):
        endpoint='https://monitor.example.chatgpt.site/ingest'
        config=dict(endpoint=endpoint,token='ingest-test-'+'x'*40,
                    service_origin='https://monitor.example.chatgpt.site',
                    sites_service_token='service-test-'+'y'*40)
        seen=[]
        class Reply:
            status=202
            def __enter__(self):return self
            def __exit__(self,*a):pass
        class Opener:
            def open(self,request,**options):
                seen.append(request);return Reply()
        with patch('katarina.monitoring.monitor_publisher.build_public_runtime',return_value={'agent_board':{'result':'BLOCKED'}}), \
             patch('katarina.monitoring.monitor_publisher.build_opener',return_value=Opener()):
            result=publish_once('unused',config)
        headers={key.lower():value for key,value in seen[0].header_items()}
        self.assertEqual(headers['oai-sites-authorization'],'Bearer '+config['sites_service_token'])
        self.assertEqual(headers['user-agent'],'Katarina-Runtime-Monitor/1.0')
        self.assertNotIn(config['token'],seen[0].data.decode())
        self.assertNotIn(config['sites_service_token'],seen[0].data.decode())
        self.assertNotIn(config['sites_service_token'],json.dumps(result))
        for origin in ('https://other.chatgpt.site','https://monitor.example.chatgpt.site/other'):
            with self.assertRaises(ValueError):
                publish_once('unused',{**config,'service_origin':origin})
        with self.assertRaises(ValueError):
            publish_once('unused',{**config,'endpoint':'https://monitor.onrender.com/ingest'})

class PublicationLatencyTests(unittest.TestCase):
    def test_changed_events_are_coalesced_within_half_second(self):
        from katarina.monitoring.monitor_publisher import _wait_for_publication
        tick=[0.]
        def clock(): return tick[0]
        def sleep(value): tick[0]+=value
        with patch('katarina.monitoring.monitor_publisher._source_version',return_value=('new',)):
            _wait_for_publication('unused',('old',),0,10,sleep=sleep,clock=clock)
        self.assertEqual(tick[0],.5)
