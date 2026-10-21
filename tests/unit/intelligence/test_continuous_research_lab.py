from datetime import datetime, timezone
from types import SimpleNamespace
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import random
from katarina.intelligence.lab.continuous_research_lab import select_batch, step, evaluate, verdict, trades, swap_costs, forward_record, setup
from katarina.monitoring.research_lab_status import clean_lab_status

class ResearchLabTests(unittest.TestCase):
    def test_rotation_and_recovery_persist(self):
        db=sqlite3.connect(':memory:'); now=datetime.now(timezone.utc)
        catalog=[SimpleNamespace(name=f'PAIR{i:02}',trade_mode=4) for i in range(54)]
        seen=set()
        for i in range(4):
            batch=select_batch(db,catalog,17,now.replace(microsecond=i))
            self.assertLessEqual(len(batch),17);seen.update(batch)
        self.assertEqual(len(seen),54)
        self.assertEqual(select_batch(db,[SimpleNamespace(name='bad secret!',trade_mode=4)],17,now),[])

    def test_resume_dedupe_and_no_execution(self):
        db=sqlite3.connect(':memory:');now=datetime.now(timezone.utc)
        select_batch(db,[SimpleNamespace(name='TEST',trade_mode=4)],17,now)
        class Broker:
            TIMEFRAME_H1=60
            def symbol_select(self,*args): return True
            def symbol_info_tick(self,*args):return SimpleNamespace(bid=100,ask=100.1)
            def copy_rates_from_pos(self,symbol,frame,offset,count):
                return [dict(time=100000+i*3600,open=100+i*.1,high=101+i*.1,low=99+i*.1,close=100.1+i*.1) for i in range(600)]
        with tempfile.TemporaryDirectory() as root:
            result=step(db,Broker(),root,now)
            self.assertEqual(result['experiments'],1)
            self.assertEqual(step(db,Broker(),root,now)['experiments'],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM lab_bars').fetchone()[0],600)
            with patch('shutil.disk_usage',return_value=SimpleNamespace(free=0)):
                self.assertEqual(step(db,Broker(),root,now)['status'],'PAUSED_LOW_DISK')
        public=clean_lab_status(dict(result,private='SECRET',recent=['SECRET']))
        self.assertNotIn('SECRET',str(public));self.assertFalse(public['live_authorized'])
        self.assertFalse(result['recent'][0]['result']['independent_holdout'])
        forged=dict(result,recent=[dict(result=dict(selected=dict(method='MOMENTUM',side='BUY'),verdict=dict(result='LIVE')))])
        self.assertIsNone(clean_lab_status(forged)['results'][0]['verdict'])

    def test_future_prices_cannot_change_development_selection(self):
        rows=[(i*3600,100+i*.1,101+i*.1,99+i*.1,100.1+i*.1) for i in range(900)]
        a=evaluate(rows,.1)
        altered=list(rows)
        for i in range(600,900):
            t,o,h,l,c=altered[i]; altered[i]=(t,o+20,h+20,l+20,c+20)
        b=evaluate(altered,.1)
        self.assertEqual([(x['method'],x['side'],x['development_n'],x['development_mean_r']) for x in a['candidates']],
                         [(x['method'],x['side'],x['development_n'],x['development_mean_r']) for x in b['candidates']])

    @staticmethod
    def walk(drift, seed, n=6000):
        rng=random.Random(seed); price=100.0; rows=[]
        for i in range(n):
            o=price; price=max(1.0,price+drift+rng.gauss(0,.3))
            rows.append((i*3600,o,max(o,price)+.05,min(o,price)-.05,price))
        return rows

    def test_precommitted_rule_rejects_driftless_walk(self):
        for seed in range(5):
            result=evaluate(self.walk(0.0,seed),.01)
            self.assertEqual(result['verdict']['result'],'REJECTED',seed)
            self.assertIsNone(result['verdict']['next_step'])
        self.assertFalse(result['live_authorized'])

    def test_precommitted_rule_passes_persistent_drift_only_for_demo(self):
        result=evaluate(self.walk(.08,1),.01)
        self.assertEqual(result['verdict']['result'],'PASSED_PRECOMMITTED_RULE')
        self.assertEqual(result['verdict']['next_step'],'DEMO_FORWARD_TEST')
        self.assertFalse(result['live_authorized'])

    def test_review_must_agree_with_development(self):
        base=dict(development_n=80,development_mean_r=.3,development_t=3.0,review_n=40,review_mean_r=-.1,review_t=-.5)
        self.assertIn('review mean after cost not positive',verdict(base)['reasons'])
        self.assertEqual(verdict(dict(base,review_mean_r=.3,review_t=2.0))['result'],'PASSED_PRECOMMITTED_RULE')
        self.assertEqual(verdict(None)['result'],'INSUFFICIENT_SAMPLES')

    def test_bracket_books_stop_when_a_bar_touches_both_levels(self):
        rows=[(i*3600,100.0,100.5,99.5,100.0) for i in range(60)]
        rows[32]=(32*3600,100.0,100.5,99.5,103.0)   # breakout signal close
        rows[33]=(33*3600,103.0,110.0,90.0,103.0)   # next bar spans stop and target
        found=trades(rows,0.0,'BREAKOUT',1,'ATR_BRACKET')
        self.assertEqual(len(found),1)
        signal,last,value=found[0]
        self.assertEqual((signal,last),(32,33))
        self.assertLess(value,-1.0)  # full stop plus the 0.2 ATR reserve

    def test_point_swap_is_charged_per_broker_night(self):
        info=SimpleNamespace(swap_mode=1,point=.01,swap_long=-50.0,swap_short=10.0)
        swap=swap_costs(info)
        self.assertAlmostEqual(swap[1],.5); self.assertAlmostEqual(swap[-1],-.1)
        self.assertIsNone(swap_costs(SimpleNamespace(swap_mode=2,point=.01,swap_long=1,swap_short=1)))
        rows=self.walk(.0,3,1200)
        plain=[v for *_,v in trades(rows,.01,'MOMENTUM',1,'CLOSE_12')]
        charged=[v for *_,v in trades(rows,.01,'MOMENTUM',1,'CLOSE_12',swap)]
        self.assertEqual(len(plain),len(charged))
        self.assertLess(sum(charged),sum(plain))

    def test_forward_record_scores_only_bars_after_nomination(self):
        db=sqlite3.connect(':memory:'); setup(db); now=datetime.now(timezone.utc)
        rows=self.walk(.08,1)
        first=evaluate(rows,.01)
        record=forward_record(db,'TEST',rows,.01,None,first,now)
        self.assertEqual((record['state'],record['forward_n']),('FORWARD_PENDING',0))
        # Later data: the same drift continues, so the nominated rule confirms forward.
        later=self.walk(.08,1,6000+40*13*3)
        confirmed=forward_record(db,'TEST',later,.01,None,evaluate(later,.01),now)
        self.assertGreaterEqual(confirmed['forward_n'],30)
        self.assertEqual(confirmed['state'],'FORWARD_CONFIRMED')
        self.assertEqual(confirmed['next_step'],'DEMO_FORWARD_TEST'); self.assertFalse(confirmed['live_authorized'])
        # The nomination is fixed: a different later selection never replaces it.
        self.assertEqual(db.execute('SELECT COUNT(*) FROM lab_nominations').fetchone()[0],1)

    def test_forward_record_fails_when_drift_disappears(self):
        db=sqlite3.connect(':memory:'); setup(db); now=datetime.now(timezone.utc)
        rows=self.walk(.08,1)
        forward_record(db,'TEST',rows,.01,None,evaluate(rows,.01),now)
        rng=random.Random(9); later=list(rows); price=later[-1][4]
        for i in range(len(rows),len(rows)+13*13*40):
            o=price; price=max(1.0,price+rng.gauss(0,.3))
            later.append((i*3600,o,max(o,price)+.05,min(o,price)-.05,price))
        failed=forward_record(db,'TEST',later,.01,None,evaluate(later,.01),now)
        self.assertGreaterEqual(failed['forward_n'],30)
        self.assertEqual(failed['state'],'FORWARD_FAILED'); self.assertIsNone(failed['next_step'])

    def test_rejected_run_is_never_nominated(self):
        db=sqlite3.connect(':memory:'); setup(db)
        rows=self.walk(0.0,2)
        self.assertIsNone(forward_record(db,'TEST',rows,.01,None,evaluate(rows,.01),datetime.now(timezone.utc)))

if __name__=='__main__':unittest.main()
