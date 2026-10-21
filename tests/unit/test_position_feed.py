from contextlib import closing
from datetime import datetime,timezone,timedelta
from pathlib import Path
import json,sqlite3,tempfile,unittest
from types import SimpleNamespace as S
from katarina.intelligence.broker_account_monitor import inspect_broker_account
from katarina.monitoring.position_feed import read_position_feed

class PositionFeedTests(unittest.TestCase):
    def test_pnl_negative_positive_swap_cent_ownership_and_no_trade_apis(self):
        now=datetime.now(timezone.utc)
        class Broker:
            ACCOUNT_TRADE_MODE_DEMO=0
            def terminal_info(self):return S(connected=True,trade_allowed=True)
            def account_info(self):return S(currency='USC',trade_mode=0,balance=9999,equity=10000,margin=0,margin_free=9999,login=123)
            def positions_get(self):return [S(ticket=7,symbol='XAUUSD.vx',type=0,price_open=4000,time=now.timestamp()-50,price_current=4001,sl=3990,tp=4020,profit=100,swap=-2),S(ticket=8,symbol='EURUSD.vx',type=1,price_open=1.1,time=now.timestamp()+10800,price_current=1.2,sl=0,tp=0,profit=-20,swap=-1)]
            def orders_get(self):return []
        broker=Broker();broker.demo_observation_enabled=True
        monitor=inspect_broker_account(broker,observed_at_utc=now)
        self.assertEqual(monitor["status"],"DEMO_ACCOUNT_OBSERVED_NO_RISK_CLEARANCE")
        self.assertEqual(monitor['position_snapshot']['floating_total'],77)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'demo-forward').mkdir()
            (root/'latest.json').write_text(json.dumps(dict(observed_at_utc=now.isoformat(),broker_account_monitor=monitor)))
            with closing(sqlite3.connect(root/'demo-forward/orders.sqlite3')) as db,db:
                db.execute('CREATE TABLE demo_outbox(state,position_id,intent_json)');db.execute('INSERT INTO demo_outbox VALUES(?,?,?)',('OPEN',7,json.dumps(dict(symbol='XAUUSD.vx',side='BUY'))))
            feed=read_position_feed(root,allowed=True,now=now)
            self.assertEqual(feed['floating_total'],77);self.assertEqual(feed['currency'],'USC');self.assertEqual(feed['katarina_floating'],98)
            self.assertEqual(feed['positions'][0]['owner'],'KATARINA_DEMO');self.assertEqual(feed['positions'][1]['owner'],'UNATTRIBUTED');self.assertIsNone(feed['positions'][1]['opened_utc'])
            for key in ('ticket','balance','equity','login','volume'):self.assertNotIn('"'+key+'"',json.dumps(feed))
            self.assertEqual(read_position_feed(root,allowed=False,now=now)['status'],'NOT_ATTESTED')
            self.assertEqual(read_position_feed(root,allowed=True,now=now+timedelta(seconds=91))['status'],'NOT_ATTESTED')
            monitor['position_snapshot']['positions'][0]['profit']=None
            (root/'latest.json').write_text(json.dumps(dict(observed_at_utc=now.isoformat(),broker_account_monitor=monitor)))
            self.assertIsNone(read_position_feed(root,allowed=True,now=now)['positions'][0]['floating'])

    def test_verified_empty_book_is_zero_missing_book_is_unknown(self):
        now=datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.assertEqual(read_position_feed(root,allowed=True,now=now)['status'],'NOT_ATTESTED')
            monitor=dict(connected=True,positions_read_success=True,position_snapshot=dict(status='OBSERVED',as_of_utc=now.isoformat(),currency='USD',mode='DEMO',positions=[],total_count=0,floating_total=0))
            (root/'latest.json').write_text(json.dumps(dict(observed_at_utc=now.isoformat(),broker_account_monitor=monitor)))
            feed=read_position_feed(root,allowed=True,now=now);self.assertEqual(feed['floating_total'],0);self.assertIsNone(feed['katarina_floating'])
