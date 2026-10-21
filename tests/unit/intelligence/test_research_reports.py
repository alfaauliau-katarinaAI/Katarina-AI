from copy import deepcopy
from contextlib import closing
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from katarina.intelligence.lab.research_reports import decision_report,publish_reports,read_reports


def evidence():
    return dict(method='MOMENTUM',side='BUY',lookback=12,horizon=4,threshold=.5,status='NEEDS_FORWARD_VALIDATION',development={'n':60,'mean_range_units':.2},review={'n':40,'mean_range_units':.1},account='PRIVATE_ACCOUNT',spread_proxy_price='PRIVATE_PRICE')

class ReportsTests(unittest.TestCase):
    def test_agreement_requires_all_checks_and_never_authorizes_execution(self):
        value=evidence();now=datetime.now(timezone.utc).isoformat()
        r=decision_report('a'*64,'PRIVATE_SYMBOL',now,value,[None,None])
        self.assertEqual(r['decision'],'AWAITING_COST_REVIEWS')
        r=decision_report('a'*64,'PRIVATE_SYMBOL',now,value,[value,value])
        self.assertEqual(r['decision'],'CANDIDATE_FORWARD');self.assertEqual(r['checks_passed'],3)
        self.assertFalse(r['production_approved']);self.assertFalse(r['live_authorized']);self.assertFalse(r['mt5_tester_verified'])
        self.assertNotIn('PRIVATE',json.dumps(r))
        bad=deepcopy(value);bad['review']['mean_range_units']=-.1
        self.assertEqual(decision_report('a'*64,'x',now,value,[value,bad])['decision'],'REJECTED')
        bad=deepcopy(value);bad['review']['n']=3
        self.assertEqual(decision_report('a'*64,'x',now,bad,[None,None])['decision'],'INSUFFICIENT_EVIDENCE')
        unavailable={'status':'DATASET_CHANGED_REVIEW_UNAVAILABLE'}
        self.assertEqual(decision_report('a'*64,'x',now,value,[unavailable,value])['decision'],'REVIEW_BLOCKED')

    def test_reports_persist_update_without_duplicates_and_reject_stale_or_wrong_pid(self):
        with TemporaryDirectory() as root:
            p=Path(root);now=datetime.now(timezone.utc).isoformat();value=evidence()
            with closing(sqlite3.connect(p/'experiment-jobs.sqlite3')) as db,db:
                db.execute('CREATE TABLE trials(id PRIMARY KEY,symbol,digest,created_utc,result_json)')
                db.execute('CREATE TABLE stress_reviews(trial_id PRIMARY KEY,created_utc,result_json)')
                db.execute('INSERT INTO trials VALUES(?,?,?,?,?)',('a'*64,'PRIVATE_SYMBOL','b'*64,now,json.dumps(value)))
            self.assertEqual(publish_reports(root),1);self.assertEqual(publish_reports(root),0)
            self.assertEqual(read_reports(root,os.getpid())['candidates'][0]['decision'],'AWAITING_COST_REVIEWS')
            with closing(sqlite3.connect(p/'experiment-jobs.sqlite3')) as db,db:
                for key in ('a'*64,'COST3:'+'a'*64):db.execute('INSERT INTO stress_reviews VALUES(?,?,?)',(key,now,json.dumps(value)))
            self.assertEqual(publish_reports(root),1)
            self.assertEqual(read_reports(root,os.getpid())['counts']['CANDIDATE_FORWARD'],1)
            with closing(sqlite3.connect(p/'experiment-jobs.sqlite3')) as db,db:
                bad=deepcopy(value);bad['review']['mean_range_units']=-1
                db.execute('UPDATE stress_reviews SET result_json=? WHERE trial_id=?',(json.dumps(bad),'COST3:'+'a'*64))
            self.assertEqual(publish_reports(root),1)
            report=read_reports(root,os.getpid());self.assertEqual(report['counts']['REJECTED'],1);self.assertEqual(report['candidates'],[])
            self.assertNotIn('PRIVATE',json.dumps(report))
            restarted=read_reports(root,os.getpid()+1)
            self.assertEqual(restarted['status'],'RESEARCH_REPORTS')
            self.assertEqual(restarted['pid'],os.getpid()+1)
            self.assertEqual(restarted['latest_report_utc'],report['latest_report_utc'])
            report['as_of_utc']=(datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat();(p/'research-reports.json').write_text(json.dumps(report))
            self.assertEqual(read_reports(root,os.getpid())['counts'],report['counts'])
