import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from katarina.monitoring.entry_feed import read_entry_feed

class EntryFeedTests(unittest.TestCase):
    def test_verified_history_plans_redaction_and_readonly(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);private=root/'demo-forward';private.mkdir();now=datetime.now(timezone.utc)
            for name,doc in [('executor',dict(pid=7,independent=True,mode='DEMO',as_of_utc=now.isoformat())),('status',dict(pid=7,as_of_utc=now.isoformat(),live_authorized=False))]:
                (private/(name+'.json')).write_text(json.dumps(doc))
            with closing(sqlite3.connect(private/'orders.sqlite3')) as db, db:
                db.execute('CREATE TABLE demo_outbox(intent_id,state,updated_at,intent_json,outcome_json)')
                intent=dict(symbol='XAUUSD.vx',side='BUY',price=4000,stop_loss=3990,take_profit=4020,created_at=now.timestamp()-60,volume=99,login='SECRET')
                db.execute('INSERT INTO demo_outbox VALUES(?,?,?,?,?)',('entry','CLOSED',now.timestamp(),json.dumps(intent),json.dumps(dict(closed_observed_at=now.timestamp(),net_profit_native=99))))
                db.execute('INSERT INTO demo_outbox VALUES(?,?,?,?,?)',('unconfirmed','ACCEPTED',now.timestamp(),json.dumps(intent),None))
            ident='a'*64;trial='b'*64
            report=dict(qualified=False,parameters=dict(method='MOMENTUM',side='BUY',lookback=24,horizon=4,threshold=.5),checks=[dict(multiplier=1,passed=False)],secret='SECRET')
            with closing(sqlite3.connect(private/'experiment.sqlite3')) as db, db:
                db.execute('CREATE TABLE demo_variants(id,trial_id,report_json)');db.execute('INSERT INTO demo_variants VALUES(?,?,?)',(ident,trial,json.dumps(report)))
                db.execute('CREATE TABLE demo_candidate_visits(trial_id,last_checked)');db.execute('INSERT INTO demo_candidate_visits VALUES(?,?)',(trial,now.timestamp()))
                db.execute('CREATE TABLE demo_policy_reviews(variant_id,report_json)');db.execute('CREATE TABLE demo_lessons(variant_id,report_json)')
            with closing(sqlite3.connect(root/'experiment-jobs.sqlite3')) as db, db:
                db.execute('CREATE TABLE trials(id,symbol)');db.execute('INSERT INTO trials VALUES(?,?)',(trial,'XAUUSD.vx'))
            before={str(p):p.read_bytes() for p in root.rglob('*.sqlite3')}
            feed=read_entry_feed(root,allowed=True,now=now)
            self.assertEqual(len(feed['history']),1);self.assertEqual(feed['history'][0]['state'],'CLOSED')
            self.assertEqual(feed['plans'][0]['state'],'NOT_QUALIFIED');self.assertFalse(feed['plans'][0]['executable'])
            raw=json.dumps(feed);self.assertNotIn('SECRET',raw);self.assertNotIn('volume',raw);self.assertNotIn('net_profit_native',raw)
            for p,data in before.items():self.assertEqual(Path(p).read_bytes(),data)
            self.assertEqual(read_entry_feed(root,allowed=False,now=now)['status'],'NOT_ATTESTED')
            self.assertEqual(read_entry_feed(root,allowed=True,now=now+timedelta(minutes=3))['status'],'NOT_ATTESTED')
            (private/'status.json').write_text(json.dumps(dict(pid=8,as_of_utc=now.isoformat(),live_authorized=False)))
            self.assertEqual(read_entry_feed(root,allowed=True,now=now)['status'],'NOT_ATTESTED')

    def test_missing_databases_are_not_empty_verified_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'demo-forward';p.mkdir();now=datetime.now(timezone.utc)
            (p/'executor.json').write_text(json.dumps(dict(pid=1,independent=True,mode='DEMO',as_of_utc=now.isoformat())))
            (p/'status.json').write_text(json.dumps(dict(pid=1,live_authorized=False,as_of_utc=now.isoformat())))
            feed=read_entry_feed(root,allowed=True,now=now)
            self.assertEqual(feed['history_status'],'NOT_ATTESTED');self.assertEqual(feed['plans_status'],'NOT_ATTESTED')
            self.assertFalse((p/'orders.sqlite3').exists())

    def test_realized_pnl_covers_entire_closed_ledger_not_visible_page(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'demo-forward';p.mkdir();now=datetime.now(timezone.utc)
            (p/'executor.json').write_text(json.dumps(dict(pid=1,independent=True,mode='DEMO',as_of_utc=now.isoformat())))
            (p/'status.json').write_text(json.dumps(dict(pid=1,live_authorized=False,as_of_utc=now.isoformat())))
            with closing(sqlite3.connect(p/'orders.sqlite3')) as db,db:
                db.execute('CREATE TABLE demo_outbox(intent_id,state,updated_at,intent_json,outcome_json)')
                for i in range(22):
                    intent=dict(symbol='EURUSD.vx',side='SELL',created_at=now.timestamp()-60,price=1.1,risk=dict(account_currency='USC'))
                    outcome=dict(net_profit_native=-3 if i==0 else 2,prospective_broker_outcome=True,closed_observed_at=now.timestamp())
                    db.execute('INSERT INTO demo_outbox VALUES(?,?,?,?,?)',(str(i),'CLOSED',now.timestamp(),json.dumps(intent),json.dumps(outcome)))
            feed=read_entry_feed(root,allowed=True,now=now)
            self.assertEqual(len(feed['history']),20)
            self.assertEqual(feed['realized_summary']['closed_count'],22)
            self.assertEqual(feed['realized_summary']['net_pnl'],39)
            self.assertEqual(feed['realized_summary']['currency'],'USC')

    def test_legacy_currency_requires_same_account_binding(self):
        from katarina.monitoring.entry_feed import _attested_currency
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'demo-forward';p.mkdir();now=datetime.now(timezone.utc);binding='a'*64
            with closing(sqlite3.connect(p/'experiment.sqlite3')) as db,db:
                db.execute('CREATE TABLE demo_account_state(id,payload)');db.execute('INSERT INTO demo_account_state VALUES(1,?)',(json.dumps(dict(binding=binding)),))
            snapshot=dict(status='OBSERVED',mode='DEMO',currency='USC',private_account_binding=binding,as_of_utc=now.isoformat())
            latest=dict(observed_at_utc=now.isoformat(),broker_account_monitor=dict(position_snapshot=snapshot))
            (root/'latest.json').write_text(json.dumps(latest));self.assertEqual(_attested_currency(root,now),'USC')
            snapshot['private_account_binding']='b'*64;(root/'latest.json').write_text(json.dumps(latest));self.assertIsNone(_attested_currency(root,now))
