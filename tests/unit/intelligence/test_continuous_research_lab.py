from datetime import datetime, timezone
from types import SimpleNamespace
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from katarina.intelligence.continuous_research_lab import select_batch, step, evaluate
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

    def test_future_prices_cannot_change_development_selection(self):
        rows=[(i*3600,100+i*.1,101+i*.1,99+i*.1,100.1+i*.1) for i in range(900)]
        a=evaluate(rows,.1)
        altered=list(rows)
        for i in range(600,900):
            t,o,h,l,c=altered[i]; altered[i]=(t,o+20,h+20,l+20,c+20)
        b=evaluate(altered,.1)
        self.assertEqual([(x['method'],x['side'],x['development_n'],x['development_mean_r']) for x in a['candidates']],
                         [(x['method'],x['side'],x['development_n'],x['development_mean_r']) for x in b['candidates']])

if __name__=='__main__':unittest.main()
