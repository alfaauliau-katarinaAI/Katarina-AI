"""Bounded routing and actual brain lifecycle through authenticated sensor protocol."""
from datetime import datetime
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from katarina.adapters.automatic_connection import (
    BoundLocalBroker, ConnectionConfig, ConnectionUnavailable, run_connected,
)
from katarina.adapters.readonly_cloud import (
    CloudReadOnlyBroker, PROTOCOL, ReadOnlySensorBridge, validate_endpoint, pack,
)
from katarina.intelligence.unified_brain import UnifiedKatarinaBrain
from tests.integration.test_brain_owned_workflow import SyntheticBroker

TOKEN='test-only-sensor-token-not-for-production-12345678'


class AccountBroker(SyntheticBroker):
    def account_info(self):
        base=super().account_info()
        return SimpleNamespace(**vars(base),login=123,server='Test-Demo')


def config(**kwargs):
    return ConnectionConfig(123,'Test-Demo',**kwargs)


class AutomaticConnectionTests(unittest.TestCase):
    def test_no_identity_configuration_runs_offline_without_probing(self):
        with tempfile.TemporaryDirectory() as root:
            result=run_connected(UnifiedKatarinaBrain,root,factories={})
            self.assertEqual(result['connection']['route'],'offline')
            self.assertEqual(result['orders_submitted'],0)

    def test_local_binding_and_no_order_interface(self):
        native=AccountBroker(); bound=BoundLocalBroker(native,config())
        self.assertTrue(bound.initialize())
        self.assertEqual(bound.account_info().login,123)
        with self.assertRaises(AttributeError): bound.order_send({})
        native.account_info=lambda:SimpleNamespace(login=456,server='Test-Demo')
        with self.assertRaises(ConnectionUnavailable): bound.symbols_get()
        self.assertTrue(bound.connection_failed)
        bound.shutdown()

    def test_active_terminal_never_selected(self):
        native=AccountBroker(active=True)
        with self.assertRaises(ConnectionUnavailable): BoundLocalBroker(native,config()).initialize()
        self.assertEqual(native.orders,0)

    def test_failure_diagnostics_identify_binding_issue_without_values(self):
        for change, expected in [
                ('active', 'TERMINAL_TRADING_MUST_BE_OFF'),
                ('account', 'ACCOUNT_LOGIN_MISMATCH'),
                ('server', 'ACCOUNT_SERVER_MISMATCH')]:
            native = AccountBroker(active=change == 'active')
            if change == 'account':
                native.account_info = lambda: SimpleNamespace(login=999, server='Test-Demo')
            if change == 'server':
                native.account_info = lambda: SimpleNamespace(login=123, server='private-server')
            with tempfile.TemporaryDirectory() as root:
                result = run_connected(UnifiedKatarinaBrain, root,
                    config=config(priority=('local',), attempts=1),
                    factories={'local': lambda c: BoundLocalBroker(native, c)})
            connection = result['connection']
            self.assertFalse(connection['receiving_market_data'])
            self.assertEqual(connection['attempts'][0]['reason'], expected)
            self.assertNotIn('private-server', json.dumps(result))

    def test_missing_mt5_dependency_is_explicit_and_does_not_fake_data(self):
        def missing(c):
            raise ImportError('private path must not be exposed')
        with tempfile.TemporaryDirectory() as root:
            result = run_connected(UnifiedKatarinaBrain, root,
                config=config(priority=('local',), attempts=1), factories={'local':missing})
        self.assertEqual(result['connection']['attempts'][0]['reason'], 'LOCAL_MT5_PACKAGE_UNAVAILABLE')
        self.assertFalse(result['connection']['receiving_market_data'])
        self.assertNotIn('private path', json.dumps(result))

    def test_connected_terminal_with_failed_sensors_is_not_receiving_data(self):
        native = AccountBroker()
        native.copy_rates_from_pos = lambda *a: None
        with tempfile.TemporaryDirectory() as root:
            result = run_connected(UnifiedKatarinaBrain, root,
                config=config(priority=('local',)), fetch_news=False,
                factories={'local':lambda c:BoundLocalBroker(native,c)})
        self.assertEqual(result['connection']['route'], 'local')
        self.assertGreater(result['observed_symbols'], 0)
        self.assertEqual(result['received_market_data_symbols'], 0)
        self.assertFalse(result['connection']['receiving_market_data'])

    def test_strict_sensor_cli_blocks_offline_fallback(self):
        import os
        import subprocess
        import sys
        env = dict(os.environ)
        env.pop('KATARINA_CONNECTION_CONFIG', None)
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable,
                str(root/'scripts/ai/run_contextual_market_observer.py'),
                '--state-dir', tmp, '--no-fetch', '--require-market-data'],
                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertIn('"receiving_market_data": false', result.stdout)

    def test_local_preferred_only_one_route_used(self):
        native=AccountBroker()
        with tempfile.TemporaryDirectory() as root:
            result=run_connected(UnifiedKatarinaBrain,root,config=config(),fetch_news=False,
                factories={'local':lambda c:BoundLocalBroker(native,c),
                           'cloud':lambda c:self.fail('second route must not be opened')})
            self.assertEqual(result['connection']['route'],'local')
            self.assertEqual(result['observed_symbols'],3)
            self.assertEqual(native.orders,0)

    def test_cloud_adapter_runs_real_brain_pipeline_after_local_failure(self):
        native=AccountBroker(); server=ReadOnlySensorBridge(native,config())
        def offline(c): raise ConnectionUnavailable('unavailable')
        def cloud(c): return CloudReadOnlyBroker('https://localhost',TOKEN,c,exchange=server.dispatch)
        with tempfile.TemporaryDirectory() as root:
            result=run_connected(UnifiedKatarinaBrain,root,config=config(attempts=1),fetch_news=False,
                                 factories={'local':offline,'cloud':cloud})
            self.assertEqual(result['connection']['route'],'cloud')
            report=json.loads((Path(root)/'latest.json').read_text())
            self.assertEqual(report['observed_symbols'],3)
            self.assertTrue(all('sensor_error:' not in '|'.join(row['blocking_reasons'])
                                for row in report['symbols'].values()))
            self.assertEqual(native.orders,0)

    def test_exhausted_routes_fall_back_offline_with_redacted_faults(self):
        calls=[]
        def fail(c):
            calls.append(1); raise ConnectionUnavailable(TOKEN)
        with tempfile.TemporaryDirectory() as root:
            result=run_connected(UnifiedKatarinaBrain,root,config=config(),factories={'local':fail,'cloud':fail})
            self.assertEqual(len(calls),4)
            self.assertEqual(result['connection']['route'],'offline')
            self.assertNotIn(TOKEN,json.dumps(result))

    def test_integrity_error_is_not_hidden_as_connection_failure(self):
        class Brain:
            @classmethod
            def observe_once(cls,*a,**kw): raise ValueError('digest mismatch')
        native=BoundLocalBroker(AccountBroker(),config())
        with self.assertRaisesRegex(ValueError,'digest mismatch'):
            run_connected(Brain,'.',config=config(),factories={'local':lambda c:native})

    def test_session_restart_invalidates_client_until_new_initialization(self):
        bridge=ReadOnlySensorBridge(AccountBroker(),config())
        client=CloudReadOnlyBroker('https://localhost',TOKEN,config(),exchange=bridge.dispatch)
        client.initialize(); bridge.session='new-session'
        with self.assertRaises(ConnectionUnavailable): client.symbols_get()
        self.assertTrue(client.connection_failed)
        client.shutdown(); self.assertTrue(client.initialize())

    def test_server_refuses_order_and_account_switch(self):
        native=AccountBroker(); bridge=ReadOnlySensorBridge(native,config())
        request=dict(protocol=PROTOCOL,request_id='0'*32,sent_at=time.time(),session=bridge.session,args=[])
        with self.assertRaises(ValueError): bridge.dispatch(dict(request,method='order_send'))
        native.account_info=lambda:SimpleNamespace(login=9,server='Other')
        with self.assertRaises(ConnectionUnavailable): bridge.dispatch(dict(request,method='symbols_get'))

    def test_nonce_clock_and_protocol_are_checked(self):
        for field,value in [('request_id','other'),('sent_at',0),('protocol','wrong')]:
            bridge=ReadOnlySensorBridge(AccountBroker(),config())
            def exchange(req):
                response=bridge.dispatch(req); response[field]=value; return response
            client=CloudReadOnlyBroker('https://localhost',TOKEN,config(),exchange=exchange)
            with self.subTest(field=field), self.assertRaises(ConnectionUnavailable): client.initialize()

    def test_endpoint_and_config_reject_unsafe_values(self):
        for url in ['http://host','https://user:pass@host','https://host/?token=abc','https://host/#x','https://host/order']:
            with self.subTest(url=url),self.assertRaises(ValueError): validate_endpoint(url)
        for kwargs in [dict(attempts=0),dict(priority=('cloud','cloud')),dict(priority=('unknown',))]:
            with self.assertRaises(ValueError): config(**kwargs)
        with self.assertRaises(ConnectionUnavailable): CloudReadOnlyBroker('https://localhost','short',config())

    def test_datetime_and_numpy_wire_fields_preserve_sensor_shapes(self):
        import numpy as np
        rows=np.array([(123,1.2,1.3)],dtype=[('time_msc','i8'),('bid','f8'),('ask','f8')])
        self.assertEqual(pack(rows),[dict(time_msc=123,bid=1.2,ask=1.3)])
        with self.assertRaises(ValueError): pack(datetime.now())

    def test_auto_cli_without_configuration_stays_offline(self):
        import os
        import subprocess
        import sys
        root=Path(__file__).resolve().parents[2]
        env=dict(os.environ); env.pop('KATARINA_CONNECTION_CONFIG',None)
        with tempfile.TemporaryDirectory() as tmp:
            result=subprocess.run([sys.executable,str(root/'scripts/ai/run_contextual_market_observer.py'),
                '--state-dir',tmp,'--no-fetch'],cwd=tmp,env=env,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('ACCOUNT_BINDING_NOT_CONFIGURED',result.stdout)

    def test_disconnect_restarts_full_pass_before_returning_ready(self):
        class Brain:
            passes=0
            @classmethod
            def observe_once(cls,root,*,broker,**kw):
                cls.passes+=1
                broker.initialize()
                try:
                    if cls.passes==1:
                        broker._native.account_info=lambda:SimpleNamespace(login=999,server='Other')
                    broker.symbols_get()
                    return {'orders_submitted':0}
                finally: broker.shutdown()
        made=[]
        def factory(c):
            adapter=BoundLocalBroker(AccountBroker(),c); made.append(adapter); return adapter
        result=run_connected(Brain,'.',config=config(priority=('local',)),factories={'local':factory})
        self.assertEqual(Brain.passes,2)
        self.assertEqual(result['connection']['attempt'],2)
        self.assertTrue(all(not adapter._ready for adapter in made))

    def test_cloud_cleanup_does_not_label_application_failure_as_disconnect(self):
        bridge=ReadOnlySensorBridge(AccountBroker(),config())
        client=CloudReadOnlyBroker('https://localhost',TOKEN,config(),exchange=bridge.dispatch)
        class Brain:
            @classmethod
            def observe_once(cls,root,*,broker,**kw):
                broker.initialize(); broker.shutdown(); raise RuntimeError('application failure')
        with self.assertRaisesRegex(RuntimeError,'application failure'):
            run_connected(Brain,'.',config=config(priority=('cloud',)),factories={'cloud':lambda c:client})

    def test_real_https_authentication_and_certificate_validation(self):
        import shutil
        import ssl
        import subprocess
        import threading
        from http.server import HTTPServer
        from scripts.ai.run_readonly_sensor_bridge import handler_type
        executable=shutil.which('openssl')
        if not executable:
            self.skipTest('openssl unavailable for ephemeral TLS test certificate')
        with tempfile.TemporaryDirectory() as tmp:
            cert,key=Path(tmp)/'cert.pem',Path(tmp)/'key.pem'
            subprocess.run([executable,'req','-x509','-newkey','rsa:2048','-nodes',
                '-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost',
                '-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True)
            bridge=ReadOnlySensorBridge(AccountBroker(),config())
            server=HTTPServer(('127.0.0.1',0),handler_type(bridge,TOKEN))
            tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(cert,key)
            server.socket=tls.wrap_socket(server.socket,server_side=True)
            worker=threading.Thread(target=server.serve_forever,daemon=True); worker.start()
            url='https://localhost:'+str(server.server_port)
            try:
                with self.assertRaises(ConnectionUnavailable):
                    CloudReadOnlyBroker(url,TOKEN,config()).initialize()
                trusted=ssl.create_default_context(cafile=str(cert))
                with patch('katarina.adapters.readonly_cloud.ssl.create_default_context',return_value=trusted):
                    client=CloudReadOnlyBroker(url,TOKEN,config()); self.assertTrue(client.initialize())
                    self.assertEqual(client.account_info().login,123)
                    with self.assertRaises(ConnectionUnavailable):
                        CloudReadOnlyBroker(url,'wrong-token-that-is-long-enough-123456',config()).initialize()
            finally:
                server.shutdown(); server.server_close(); worker.join(timeout=5)

    def test_account_switch_during_read_discards_returned_data(self):
        for route in ('local','cloud'):
            native=AccountBroker()
            def changing_read():
                native.account_info=lambda:SimpleNamespace(login=999,server='Other')
                return []
            native.symbols_get=changing_read
            if route=='local':
                adapter=BoundLocalBroker(native,config())
            else:
                bridge=ReadOnlySensorBridge(native,config())
                adapter=CloudReadOnlyBroker('https://localhost',TOKEN,config(),exchange=bridge.dispatch)
            adapter.initialize()
            with self.subTest(route=route), self.assertRaises(ConnectionUnavailable):
                adapter.symbols_get()
            adapter.shutdown()
