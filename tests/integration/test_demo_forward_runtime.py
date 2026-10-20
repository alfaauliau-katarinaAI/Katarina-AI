from dataclasses import replace
from contextlib import closing
from hashlib import sha256
from datetime import datetime, timezone
import json
import io
import math
from pathlib import Path
import sqlite3
import runpy
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

from katarina.adapters.automatic_connection import ConnectionConfig, verify_identity, ConnectionUnavailable, BoundLocalBroker
from katarina.adapters.demo_permissions import observation_permission, monitor_permission
from katarina.intelligence.demo_forward import DemoForwardRuntime
from katarina.intelligence.demo_strategy import qualify_variant
from katarina.intelligence.demo_account import DemoAccountLedger


class Native:
    ACCOUNT_TRADE_MODE_DEMO=0
    ORDER_TYPE_BUY=0;ORDER_TYPE_SELL=1
    ORDER_FILLING_FOK=0;ORDER_FILLING_IOC=1;ORDER_FILLING_RETURN=2
    ORDER_TIME_GTC=0;TRADE_ACTION_DEAL=1
    TRADE_RETCODE_DONE=10009;TRADE_RETCODE_DONE_PARTIAL=10010
    DEAL_TYPE_BUY=0;DEAL_TYPE_SELL=1;DEAL_TYPE_BALANCE=2
    DEAL_ENTRY_IN=0;DEAL_ENTRY_OUT=1;DEAL_ENTRY_OUT_BY=3
    TIMEFRAME_H1=16385;COPY_TICKS_INFO=1
    def __init__(self, clock):
        self.clock=clock;self.account=NS(login=123,server='TEST-DEMO',trade_mode=0,
            trade_allowed=True,trade_expert=True,balance=10000.,equity=10000.,margin_free=10000.,currency='USD')
        self.terminal=NS(connected=True,trade_allowed=True,tradeapi_disabled=False)
        self.positions=[];self.deals=[];self.sent=[];self.timeout=False;self.history_missing=False;self.next_ticket=456
        self.initializations=0;self.shutdowns=0
    def initialize(self,*args,**kwargs):self.initializations+=1;return True
    def shutdown(self):self.shutdowns+=1
    def terminal_info(self):return self.terminal
    def account_info(self):return self.account
    def positions_get(self,**kw):return [p for p in self.positions if not kw or p.ticket==kw['ticket']]
    def orders_get(self):return []
    def history_deals_get(self,*args,**kw):
        if self.history_missing:return None
        return [d for d in self.deals if not kw or ('ticket' in kw and d.ticket==kw['ticket']) or ('position' in kw and d.position_id==kw['position'])]
    def order_calc_profit(self,side,symbol,volume,entry,exit):return (exit-entry)*volume*100*(1 if side==0 else -1)
    def order_calc_margin(self,*args):return 10.
    def symbol_info(self,symbol):return NS(volume_min=.01,volume_max=10.,volume_step=.01,trade_tick_size=.01,filling_mode=3)
    def copy_ticks_range(self,*args):return [dict(time_msc=int(self.clock()*1000),bid=100.,ask=100.1)]
    def copy_rates_from_pos(self,*args):
        hour=int(self.clock()//3600)*3600
        return [dict(time=hour-(66-i)*3600,open=100.,high=101.,low=97. if i==65 else 99.,close=97.5 if i==65 else 100.) for i in range(66)]
    def order_check(self,request):return NS(retcode=0)
    def order_send(self,r):
        self.sent.append(r)
        if 'position' in r:
            self.close_for_test();return NS(retcode=10009,order=999,deal=999)
        pid=self.next_ticket;self.next_ticket+=2;self.account.balance-=.1;self.account.equity=self.account.balance
        self.positions=[NS(ticket=pid,magic=r['magic'],symbol=r['symbol'],type=r['type'],volume=r['volume'],
                           price_current=r['price'],sl=r['sl'],tp=r['tp'])]
        self.deals.append(NS(ticket=pid,position_id=pid,magic=r['magic'],symbol=r['symbol'],type=r['type'],entry=0,
                             volume=r['volume'],profit=0.,commission=-.1,swap=0.,fee=0.,comment=r['comment']))
        if self.timeout:raise TimeoutError('private error')
        return NS(retcode=10009,order=pid,deal=pid)
    def close_for_test(self,profit=3.):
        p=self.positions.pop();self.account.balance+=profit-.1;self.account.equity=self.account.balance
        self.deals.append(NS(ticket=p.ticket+1,position_id=p.ticket,magic=p.magic,symbol=p.symbol,type=1-p.type,entry=1,
                             volume=p.volume,profit=profit,commission=-.1,swap=0.,fee=0.,comment='broker exit'))


class DemoForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.now=1800000000//3600*3600+10
        self.clock=lambda:self.now;self.native=Native(self.clock)
        self.config=ConnectionConfig(123,'TEST-DEMO',priority=('local',),terminal_path='TEST-terminal',demo_experiments=True)
        self.runtime=self.make_runtime()
        self.write_clock()
    def write_clock(self):
        (self.root/'latest.json').write_text(json.dumps(dict(time_reference=dict(observed_at_utc=datetime.fromtimestamp(self.now,timezone.utc).isoformat(),
            canonical_market_clock='MT5_COPY_TICKS_RANGE_TIME_MSC_UTC',broker_server_shift_minutes=0,confirming_symbols=5))))
    def make_runtime(self):
        r=DemoForwardRuntime(self.root,self.config,native=self.native,clock=self.clock)
        r._candidate=lambda:dict(trial_id='a'*64,symbol='TEST',config=dict(method='MEAN_REVERSION',side='BUY',lookback=48,horizon=4,threshold=.5),
                                 variant=dict(id='b'*64,qualified=True))
        return r
    def step(self,**kwargs):return self.runtime.step(force=True,**kwargs)

    def test_two_non_chart_symbols_flow_through_sensors_and_demo_orders(self):
        self.native.chart_symbol='XAUUSD.vx'
        reads=[]
        for name in ('copy_ticks_range','copy_rates_from_pos','symbol_info'):
            original=getattr(self.native,name)
            def wrapped(symbol,*args,_name=name,_original=original,**kwargs):
                reads.append((_name,symbol))
                return _original(symbol,*args,**kwargs)
            setattr(self.native,name,wrapped)
        for index,symbol in enumerate(('EURUSD.vx','USDJPY.vx')):
            self.runtime._candidate=lambda symbol=symbol,index=index:dict(
                trial_id=str(index)*64,symbol=symbol,
                config=dict(method='MEAN_REVERSION',side='BUY',lookback=48,horizon=4,threshold=.5),
                variant=dict(id=str(index+1)*64,qualified=True))
            self.assertEqual(self.step()['status'],'DEMO_ACCEPTED')
            self.assertEqual(self.native.sent[-1]['symbol'],symbol)
            for method in ('copy_ticks_range','copy_rates_from_pos','symbol_info'):
                self.assertIn((method,symbol),reads)
            self.native.close_for_test();self.step(execute=False)
        self.assertEqual([x['symbol'] for x in self.native.sent],['EURUSD.vx','USDJPY.vx'])
        self.assertFalse(any(symbol=='XAUUSD.vx' for _,symbol in reads))

    def test_complete_forward_cycle_persists_broker_outcome_and_lesson(self):
        self.assertEqual(self.step()['status'],'DEMO_ACCEPTED')
        self.assertEqual(self.step()['status'],'DEMO_POSITION_MONITORING')
        self.native.close_for_test()
        result=self.step(execute=False)
        self.assertEqual(result['closed_outcomes'],1);self.assertEqual(result['winning_outcomes'],1)
        with closing(sqlite3.connect(self.runtime.path)) as db:
            lesson=json.loads(db.execute('SELECT report_json FROM demo_lessons').fetchone()[0])
        self.assertAlmostEqual(lesson['net_profit_native'],2.8)
        self.assertFalse(lesson['live_authorized'])
        self.runtime=self.make_runtime()
        self.assertEqual(self.step()['status'],'DEMO_SIGNAL_ALREADY_EVALUATED')
        self.assertEqual(len(self.native.sent),1)

    def test_horizon_exit_is_owned_and_reconciled(self):
        self.step();self.step();self.now+=4*3600+1
        self.assertEqual(self.step()['status'],'DEMO_POSITION_MONITORING')
        self.assertEqual(self.native.sent[-1]['position'],456)
        self.assertEqual(self.step(execute=False)['closed_outcomes'],1)

    def test_real_switch_blocks_both_observer_and_executor(self):
        self.native.account.trade_mode=2
        self.assertEqual(self.step()['status'],'DEMO_ACCOUNT_REQUIRED')
        with self.assertRaises(ConnectionUnavailable):verify_identity(self.native,self.config)
        self.assertFalse(self.native.sent)

    def test_permission_off_still_reconciles_and_does_not_send(self):
        self.native.terminal.trade_allowed=False
        result=self.step()
        self.assertTrue(result['risk_reconciled'])
        self.assertEqual(result['status'],'DEMO_TRADING_PERMISSION_OFF')
        self.assertFalse(self.native.sent)

    def test_unknown_submission_reconciles_fill_without_resending(self):
        self.native.timeout=True
        self.assertEqual(self.step()['status'],'DEMO_UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(self.step()['status'],'DEMO_POSITION_MONITORING')
        self.assertEqual(len(self.native.sent),1)

    def test_owner_stop_and_missing_history_never_send(self):
        (self.root/'continuous.stop').touch()
        self.assertEqual(self.step()['status'],'OWNER_STOP_REQUEST')
        (self.root/'continuous.stop').unlink();self.native.history_missing=True
        self.assertEqual(self.step()['status'],'DEMO_FORWARD_REQUIRES_REVIEW')
        self.assertFalse(self.native.sent)

    def test_unexplained_balance_change_is_not_reconciled(self):
        self.step(execute=False);self.native.account.balance-=100
        self.assertEqual(self.step()['status'],'DEMO_FORWARD_REQUIRES_REVIEW')
        self.assertFalse(self.native.sent)

    def test_unqualified_protected_variant_cannot_execute(self):
        self.runtime._candidate=lambda:dict(variant=dict(id='b'*64,qualified=False))
        self.assertEqual(self.step()['status'],'PROTECTED_VARIANT_NOT_QUALIFIED')
        self.assertFalse(self.native.sent)

    def test_foreign_deal_prevents_managing_mixed_position(self):
        self.step();self.step()
        self.native.deals[0].magic=0
        self.now+=4*3600+1
        result=self.step()
        self.assertEqual(result['unresolved_submissions'],1)
        self.assertEqual(len(self.native.sent),1)

    def test_deposit_is_reconciled_as_external_cashflow(self):
        self.step(execute=False)
        self.native.account.balance+=1000;self.native.account.equity+=1000
        self.native.deals.append(NS(ticket=1234,type=2,profit=1000.,commission=0.,swap=0.,fee=0.))
        self.assertTrue(self.step(execute=False)['risk_reconciled'])
        with closing(sqlite3.connect(self.runtime.path)) as db:
            state=json.loads(db.execute('SELECT payload FROM demo_account_state').fetchone()[0])
        self.assertEqual(state['max_total_dd'],0.)

    def test_stale_market_clock_reference_never_creates_order(self):
        self.now+=200
        self.assertEqual(self.step()['status'],'DEMO_FORWARD_REQUIRES_REVIEW')
        self.assertFalse(self.native.sent)

    def test_three_losing_forward_outcomes_quarantine_variant(self):
        for i in range(3):
            self.write_clock()
            self.assertEqual(self.step()['status'],'DEMO_ACCEPTED')
            self.native.close_for_test(profit=-1.)
            self.step(execute=False)
            self.now+=3600
        self.write_clock()
        self.assertEqual(self.step()['status'],'DEMO_VARIANT_COOLDOWN_RESEARCH_REQUIRED')
        self.assertEqual(len(self.native.sent),3)

    def test_real_trial_schema_uses_digest_column_and_frozen_dataset(self):
        from katarina.intelligence.autonomous_research import preserve_dataset
        rows=[]
        for i in range(2400):
            p=100+5*math.sin(i/8);rows.append([1000000+i*3600,p,p+1,p-1,p])
        digest=sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
        config=dict(method='MEAN_REVERSION',side='BUY',lookback=24,horizon=4,threshold=.5,spread_proxy_price=.01,status='NEEDS_FORWARD_VALIDATION',dataset_preserved=True)
        with closing(sqlite3.connect(self.root/'experiment-jobs.sqlite3')) as db,db:
            db.execute('CREATE TABLE trials(id TEXT PRIMARY KEY,symbol TEXT,digest TEXT,created_utc TEXT,result_json TEXT)')
            db.execute('CREATE TABLE research_report_heads(trial_id TEXT,signature TEXT,report_id TEXT)')
            db.execute('CREATE TABLE research_reports(id TEXT,trial_id TEXT,created_utc TEXT,decision TEXT,report_json TEXT)')
            db.execute('INSERT INTO trials VALUES(?,?,?,?,?)',('a'*64,'TEST',digest,'2026-10-20',json.dumps(config)))
            db.execute('INSERT INTO research_report_heads VALUES(?,?,?)',('a'*64,'version','r1'))
            db.execute('INSERT INTO research_reports VALUES(?,?,?,?,?)',('r1','a'*64,'2026-10-20','CANDIDATE_FORWARD','{}'))
            preserve_dataset(db,digest,rows)
        result=DemoForwardRuntime._candidate(self.runtime)
        self.assertEqual(result['trial_id'],'a'*64)
        self.assertEqual(result['variant']['parameters']['stop_range'],2)
        self.assertFalse(result['variant']['prospective_validation'])
        cached=DemoForwardRuntime._candidate(self.runtime)
        self.assertEqual(cached['variant'],result['variant'])
        # A stress-rejected parent still receives its own protected demo review,
        # and visiting a candidate advances selection to the other instrument.
        with closing(sqlite3.connect(self.root/'experiment-jobs.sqlite3')) as db,db:
            db.execute('INSERT INTO trials VALUES(?,?,?,?,?)',('b'*64,'SECOND',digest,'2026-10-20',json.dumps(config)))
            db.execute('INSERT INTO research_report_heads VALUES(?,?,?)',('b'*64,'version','r2'))
            db.execute('INSERT INTO research_reports VALUES(?,?,?,?,?)',('r2','b'*64,'2026-10-20','REJECTED','{}'))
        rotated=DemoForwardRuntime._candidate(self.runtime)
        self.assertEqual(rotated['symbol'],'SECOND')
        self.assertEqual(rotated['variant']['qualification_policy'],'DEMO_BASE_COST_GOVERNOR_V2')

    def test_demo_cost_stress_is_advisory_and_preserves_identity(self):
        from katarina.intelligence.demo_strategy import demo_policy
        old=dict(id='stable-variant',qualified=False,checks=[dict(multiplier=i,passed=i<3) for i in (1,2,3)])
        updated=self.runtime._policy(old)
        self.assertTrue(updated['qualified'])
        self.assertFalse(updated['stress_resilient'])
        self.assertEqual(updated['id'],old['id'])
        self.assertFalse(old['qualified'])
        self.assertFalse(updated['live_authorized'])
        old['checks'][0]['passed']=False
        self.assertFalse(demo_policy(old)['qualified'])

    def test_demo_service_reuses_owner_connection_between_sensor_reads(self):
        bound=BoundLocalBroker(self.native,self.config)
        self.assertTrue(bound.initialize())
        results=[]
        bound.set_demo_service(lambda:results.append(self.runtime.step(execute=False,force=True,already_connected=True)))
        self.assertEqual(bound.account_info().login,123)
        self.assertEqual(results[-1]['status'],'DEMO_AUDIT_READY_NO_ORDER')
        self.assertEqual(self.native.initializations,1)
        self.assertEqual(self.native.shutdowns,0)
        self.assertFalse(self.native.sent)

    def test_demo_service_cannot_hide_account_change_from_sensor(self):
        bound=BoundLocalBroker(self.native,self.config);bound.initialize()
        bound.set_demo_service(lambda:setattr(self.native.account,'trade_mode',2))
        with self.assertRaises(ConnectionUnavailable):bound.account_info()

    def test_missing_exit_history_does_not_release_next_entry(self):
        self.step();self.step()
        self.native.positions=[]
        self.now+=3600;self.write_clock()
        self.assertEqual(self.step()['status'],'DEMO_RECONCILIATION_REQUIRED')
        self.assertEqual(len(self.native.sent),1)

    def test_audit_cli_refuses_running_owner_before_connecting(self):
        (self.root/'continuous-status.json').write_text('{"status":"OBSERVING"}')
        script=Path(__file__).resolve().parents[2]/'scripts/ai/audit_demo_forward.py'
        main=runpy.run_path(str(script))['main']
        with patch.object(sys,'argv',['audit','--connection-config','must-not-be-read','--state-dir',str(self.root)]),redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(),2)
        self.assertIn('GRACEFULLY_STOPPED_OWNER',out.getvalue())

    def test_minimum_lot_above_risk_budget_is_rejected(self):
        self.native.account.balance=100.;self.native.account.equity=100.
        self.assertEqual(self.step()['status'],'DEMO_VOLUME_EXCEEDS_APPROVED_RISK')
        self.assertFalse(self.native.sent)

    def test_read_only_default_still_rejects_algo_on(self):
        readonly=replace(self.config,demo_experiments=False)
        with self.assertRaises(ConnectionUnavailable):verify_identity(self.native,readonly)
        bound=BoundLocalBroker(self.native,self.config);self.assertTrue(bound.initialize())
        self.assertTrue(observation_permission(bound))
        self.native.account.trade_mode=2
        with self.assertRaises(ConnectionUnavailable):bound.account_info()
        self.assertFalse(monitor_permission(dict(algo_trading_off=False,account_mode='REAL',demo_observation_enabled=True)))

    def test_protected_variant_checks_three_cost_levels_and_cannot_claim_forward(self):
        rows=[]
        for i in range(2400):
            p=100+5*math.sin(i/8)
            rows.append([1000000+i*3600,p,p+1,p-1,p])
        report=qualify_variant(rows,dict(method='MEAN_REVERSION',side='BUY',lookback=24,horizon=4,threshold=.5),spread=.01,original_id='a'*64)
        self.assertEqual([x['multiplier'] for x in report['checks']],[1,2,3])
        self.assertFalse(report['prospective_validation']);self.assertFalse(report['independent_holdout'])
        with self.assertRaises(ValueError):qualify_variant(list(reversed(rows)),dict(method='MEAN_REVERSION',side='BUY',lookback=24,horizon=4,threshold=.5),spread=.01,original_id='a'*64)


if __name__=='__main__':unittest.main()
