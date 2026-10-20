from datetime import datetime,timezone,timedelta
import json,sqlite3,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as S
from katarina.intelligence.data_recovery import record_gaps,recover_due,read_recovery
from katarina.intelligence.causal_broker_quotes import last_past_quote

class Broker:
    TIMEFRAME_M5=5;TIMEFRAME_M15=15;TIMEFRAME_H1=60;COPY_TICKS_INFO=1
    def __init__(self,now,empty=False):self.now=now;self.empty=empty;self.calls=[];self.unsafe=False
    def terminal_info(self):return S(trade_allowed=self.unsafe)
    def symbol_select(self,s,on):self.calls.append(('subscribe',s));return True
    def symbol_info_tick(self,s):return None if self.empty else S(bid=10,ask=11)
    def copy_ticks_range(self,s,start,end,flags):
        self.calls.append(('ticks',s))
        return [] if self.empty else [dict(bid=10,ask=11,time_msc=(self.now.timestamp()-1)*1000)]
    def copy_rates_from_pos(self,s,tf,start,count):
        self.calls.append(('bars',s,tf,count))
        return [dict(time=int(self.now.timestamp())-(132-i)*tf*60,open=10,high=12,low=9,close=11,tick_volume=5) for i in range(130)]

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name);self.db=sqlite3.connect(':memory:');self.now=datetime.now(timezone.utc)
        (self.root/'latest.json').write_text(json.dumps({'broker_server_shift_hours':0}))
    def tearDown(self):self.db.close();self.temp.cleanup()
    def seed(self,n=1):return record_gaps(self.db,{str(i):{'sensor_reason':'no_past_broker_bidask_quote'} for i in range(n)},{},self.now,self.root)
    def test_recovery_requests_multiple_inputs_and_waits_for_real_observation(self):
        self.seed();b=Broker(self.now);events=[]
        out=recover_due(self.db,b,self.root,self.now,emit=lambda *a,**k:events.append(a))
        self.assertEqual(out['inputs_ready'],1);self.assertEqual(out['verified'],0)
        self.assertEqual(len([x for x in b.calls if x[0]=='bars']),6)
        self.assertIn(('HISTORY','DONE'),events)
        out=record_gaps(self.db,{'0':{}},{'0':(10,11,self.now.timestamp())},self.now,self.root)
        self.assertEqual(out['verified'],1);self.assertEqual(out['missing'],0)
    def test_missing_market_gets_warmup_segmented_retries_and_backoff(self):
        self.seed(3);b=Broker(self.now,empty=True)
        out=recover_due(self.db,b,self.root,self.now)
        self.assertEqual(out['attempts'],2);self.assertEqual(out['missing'],3);self.assertEqual(out['inputs_ready'],0)
        self.assertEqual(len([x for x in b.calls if x[0]=='ticks']),8)
        out=recover_due(self.db,b,self.root,self.now);self.assertEqual(out['attempts'],3)
        out=recover_due(self.db,b,self.root,self.now);self.assertEqual(out['attempts'],3)
        self.assertEqual(out['reasons']['no_past_broker_bidask_quote'],3)
    def test_identity_wrapper_and_live_off_gates_are_preserved(self):
        self.seed();b=Broker(self.now);b.unsafe=True
        with self.assertRaisesRegex(RuntimeError,'ACCOUNT_OR_TRADING_PERMISSION_CHANGED'):recover_due(self.db,b,self.root,self.now)
        self.assertFalse(b.calls)
        out=read_recovery(self.root,999);self.assertEqual(out['status'],'NOT_ATTESTED')
    def test_explicit_bound_demo_recovery_coexists_with_algo_on(self):
        self.seed();b=Broker(self.now);b.unsafe=True
        b.demo_observation_enabled=True;b.ACCOUNT_TRADE_MODE_DEMO=0
        b.account_info=lambda:S(trade_mode=0)
        self.assertEqual(recover_due(self.db,b,self.root,self.now)['inputs_ready'],1)
        b.account_info=lambda:S(trade_mode=2)
        with self.assertRaisesRegex(RuntimeError,'ACCOUNT_OR_TRADING_PERMISSION_CHANGED'):
            recover_due(self.db,b,self.root,self.now)

    def test_tick_fallback_keeps_original_causal_bounds(self):
        b=Broker(self.now);calls=[]
        def ticks(s,start,end,flags):
            calls.append((start,end));return [] if len(calls)==1 else [dict(time_msc=(self.now.timestamp()-1)*1000,bid=10,ask=11),dict(time_msc=(self.now.timestamp()+1)*1000,bid=10,ask=11)]
        b.copy_ticks_range=ticks
        q=last_past_quote(b,'0',self.now)
        self.assertAlmostEqual(q[2],self.now.timestamp()-1,places=5);self.assertEqual(len(calls),2)
        self.assertLessEqual((calls[1][1]-calls[1][0]).total_seconds(),30)

    def test_old_diagnostics_seed_requests_without_becoming_live_data(self):
        from katarina.intelligence.data_recovery import seed_existing_gaps
        (self.root/'latest.json').write_text(json.dumps({'symbols':{'missing':{'blocking_reasons':['sensor_error:ValueError']},'valid':{'market_state':'TREND_UP'}}}))
        out=seed_existing_gaps(self.db,self.root,self.now)
        self.assertEqual(out['missing'],1);self.assertEqual(out['verified'],0)

    def test_fresh_quote_does_not_hide_stale_bars_or_close_only_symbol(self):
        cards={'old':{'sensor_quality':{'closed_bars_recent':False,'trade_mode':4}},
               'closed':{'sensor_quality':{'closed_bars_recent':True,'trade_mode':3}}}
        out=record_gaps(self.db,cards,{'old':(1,2,3),'closed':(1,2,3)},self.now,self.root)
        self.assertEqual(out['missing'],2);self.assertEqual(out['verified'],0)
        self.assertEqual(dict(self.db.execute('SELECT symbol,reason FROM sensor_recovery')),
                         {'old':'STALE_CLOSED_BARS','closed':'SYMBOL_CLOSE_ONLY'})

    def test_date_range_history_is_researched_without_becoming_live_quote(self):
        self.seed();self.db.execute('UPDATE sensor_recovery SET attempts=1');self.db.commit()
        b=Broker(self.now,empty=True);b.symbol_info=lambda _:S(trade_mode=4)
        calls=[]
        def history(symbol,tf,start,end):
            calls.append((tf,start,end))
            return [dict(time=int((self.now-timedelta(days=1)).timestamp()),open=10.,high=12.,low=9.,close=11.)]
        b.copy_rates_range=history
        out=recover_due(self.db,b,self.root,self.now)
        self.assertEqual(len(calls),3);self.assertEqual(out['verified'],0)
        self.assertEqual(self.db.execute('SELECT status FROM sensor_recovery').fetchone()[0],'HISTORY_RESEARCH_ONLY')
        evidence=json.loads(self.db.execute('SELECT report_json FROM sensor_recovery_attempts').fetchone()[0])
        self.assertEqual(evidence['history']['H1']['rows'],1)
        self.assertFalse(evidence['history']['H1']['validated_for_entry'])
        self.assertEqual(evidence['session_status'],'NOT_INFERRED_FROM_MISSING_QUOTES')

    def test_disabled_symbol_is_classified_without_useless_history_calls(self):
        self.seed();b=Broker(self.now);b.symbol_info=lambda _:S(trade_mode=0)
        recover_due(self.db,b,self.root,self.now)
        self.assertEqual(self.db.execute('SELECT reason,status FROM sensor_recovery').fetchone(),('SYMBOL_DISABLED','WAIT_BROKER_PERMISSION'))
        self.assertFalse(any(x[0] in ('bars','ticks') for x in b.calls))
