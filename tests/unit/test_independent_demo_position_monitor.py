"""Independent DEMO position/PnL evidence for the public monitoring surface.

Synthetic tests. Neither MT5 access nor public projection can place orders.
"""
from contextlib import closing
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace as S

from katarina.intelligence.broker.broker_account_monitor import inspect_broker_account
from katarina.intelligence.demo.demo_forward import DemoForwardRuntime
from katarina.monitoring.entry_feed import _attested_currency
from katarina.monitoring.position_feed import read_position_feed


class DemoIndependentTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.private=self.root/'demo-forward'
        self.private.mkdir()
        self.now=datetime.now(timezone.utc)
        self.binding=sha256(b'123|TEST-DEMO').hexdigest()
        with closing(sqlite3.connect(self.private/'experiment.sqlite3')) as db, db:
            db.execute('CREATE TABLE demo_account_state(id INTEGER PRIMARY KEY,payload TEXT)')
            db.execute('INSERT INTO demo_account_state VALUES(1,?)',
                       (json.dumps({'binding':self.binding}),))
        with closing(sqlite3.connect(self.private/'orders.sqlite3')) as db, db:
            db.execute('CREATE TABLE demo_outbox(state TEXT,position_id INTEGER,intent_json TEXT)')
            db.execute('INSERT INTO demo_outbox VALUES(?,?,?)',
                       ('OPEN',7,json.dumps({'symbol':'UK100.vx','side':'BUY'})))
        self.broker=self.make_broker()
        self.write_witness()

    def make_broker(self, *,trade_mode=0):
        now=self.now
        class Broker:
            ACCOUNT_TRADE_MODE_DEMO=0
            def terminal_info(self):return S(connected=True,trade_allowed=True)
            def account_info(self):
                return S(login=123,server='TEST-DEMO',currency='USD',trade_mode=trade_mode,
                         balance=1000,equity=1010,margin=5,margin_free=1005)
            def positions_get(self):
                return [S(ticket=7,symbol='UK100.vx',type=0,price_open=8000,
                          time=int(now.timestamp()-60),price_current=8010,sl=7980,tp=8040,
                          profit=10.,swap=-1.)]
            def orders_get(self):return []
            def order_send(self,*a,**k):raise AssertionError('MUST_NOT_SEND_ORDER')
        return Broker()

    def write_witness(self, *,pid=456, asof=None):
        asof=asof or self.now
        monitor=inspect_broker_account(self.broker,observed_at_utc=asof)
        (self.private/'executor.json').write_text(json.dumps(dict(
            pid=pid,mode='DEMO',independent=True,live_authorized=False,
            status='RUNNING',as_of_utc=asof.isoformat())))
        (self.private/'position-monitor.json').write_text(json.dumps(dict(
            schema_version=1,pid=pid,mode='DEMO',live_authorized=False,
            as_of_utc=asof.isoformat(),monitor=monitor)))

    def test_independent_snapshot_shows_broker_position_even_with_stale_observer(self):
        (self.root/'latest.json').write_text(json.dumps(dict(
            observed_at_utc=(self.now-timedelta(minutes=10)).isoformat())))
        feed=read_position_feed(self.root,allowed=True,now=self.now)
        self.assertEqual(feed['status'],'OBSERVED')
        self.assertEqual(feed['floating_total'],9.)
        self.assertEqual(feed['katarina_floating'],9.)
        self.assertEqual(feed['positions'][0]['owner'],'KATARINA_DEMO')
        self.assertEqual(_attested_currency(self.root,self.now),'USD')
        self.assertNotIn('login',json.dumps(feed))
        self.assertNotIn('balance',json.dumps(feed))
        self.assertNotIn('ticket',json.dumps(feed))

    def test_mismatch_expiry_and_live_mode_fail_closed(self):
        self.assertEqual(read_position_feed(self.root,allowed=False,now=self.now)['status'],'NOT_ATTESTED')
        path=self.private/'executor.json'
        executor=json.loads(path.read_text());executor['pid']=999
        path.write_text(json.dumps(executor))
        self.assertEqual(read_position_feed(self.root,allowed=True,now=self.now)['status'],'NOT_ATTESTED')
        self.write_witness()
        self.assertEqual(read_position_feed(self.root,allowed=True,
                          now=self.now+timedelta(seconds=91))['status'],'NOT_ATTESTED')
        executor=json.loads(path.read_text());executor['live_authorized']=True
        path.write_text(json.dumps(executor))
        self.assertEqual(read_position_feed(self.root,allowed=True,now=self.now)['status'],'NOT_ATTESTED')
        self.write_witness()
        with closing(sqlite3.connect(self.private/'experiment.sqlite3')) as db,db:
            db.execute('UPDATE demo_account_state SET payload=?',
                       (json.dumps({'binding':'f'*64}),))
        self.assertEqual(read_position_feed(self.root,allowed=True,now=self.now)['status'],'NOT_ATTESTED')

    def test_writer_requires_correct_broker_mode_and_preserves_no_order_api(self):
        def runtime(broker):
            o=object.__new__(DemoForwardRuntime)
            o.private=self.private
            o.native=broker
            o.clock=lambda:self.now.timestamp()
            o.config=S(expected_login=123,expected_server='TEST-DEMO')
            o.boundary=S(_identity_error=lambda:None)
            return o
        (self.private/'position-monitor.json').unlink()
        runtime(self.make_broker(trade_mode=2))._publish_position_telemetry()
        self.assertFalse((self.private/'position-monitor.json').exists())
        runtime(self.make_broker())._publish_position_telemetry()
        self.assertTrue((self.private/'position-monitor.json').exists())
        data=json.loads((self.private/'position-monitor.json').read_text())
        self.assertEqual(data['monitor']['position_snapshot']['total_count'],1)
        self.assertIs(data['live_authorized'],False)


if __name__=='__main__':
    unittest.main()
