import unittest,sqlite3,json,tempfile
from pathlib import Path
from katarina.intelligence.research_reports import read_reports,prepare_report_indexes
class PersistedReportsTests(unittest.TestCase):
    def test_restart_observes_persisted_reports_without_rewriting_experiment_time(self):
        with tempfile.TemporaryDirectory() as root:
            db=sqlite3.connect(Path(root)/'experiment-jobs.sqlite3')
            db.executescript('CREATE TABLE trials(id TEXT); CREATE TABLE research_reports(id TEXT,created_utc TEXT,decision TEXT,report_json TEXT); CREATE TABLE research_report_heads(trial_id TEXT,report_id TEXT);')
            row=dict(id='a'*64,trial_id='b'*64,reported_utc='2026-10-19T00:00:00+00:00',decision='REJECTED')
            db.execute('INSERT INTO trials VALUES(?)',('trial',));db.execute('INSERT INTO research_reports VALUES(?,?,?,?)',(row['id'],row['reported_utc'],'REJECTED',json.dumps(row)));db.execute('INSERT INTO research_report_heads VALUES(?,?)',('trial',row['id']));db.commit();prepare_report_indexes(db);db.commit();before=db.total_changes
            out=read_reports(root,999)
            self.assertEqual(out['status'],'RESEARCH_REPORTS');self.assertEqual(out['pid'],999)
            self.assertEqual(out['latest_report_utc'],row['reported_utc']);self.assertEqual(out['recent'][0]['reported_utc'],row['reported_utc'])
            self.assertEqual(out['reviewed_experiments'],1);self.assertFalse(out['production_approved']);self.assertEqual(db.total_changes,before)
            db.close()

    def test_busy_or_missing_database_keeps_historical_report_with_its_old_timestamp(self):
        with tempfile.TemporaryDirectory() as root:
            stamp='2026-10-19T00:00:00+00:00'
            Path(root,'research-reports.json').write_text(json.dumps(dict(status='RESEARCH_REPORTS',pid=10,as_of_utc=stamp,recent=[],counts={})))
            out=read_reports(root,999)
            self.assertEqual(out['latest_report_utc'],stamp)
            self.assertEqual(out['producer_pid'],10)
            self.assertEqual(out['pid'],999)
            self.assertNotEqual(out['as_of_utc'],stamp)
            self.assertFalse(out['production_approved'])

    def test_report_writer_processes_pending_evidence_and_publishes_a_snapshot(self):
        from katarina.intelligence.research_reports import publish_reports
        with tempfile.TemporaryDirectory() as root:
            db=sqlite3.connect(Path(root)/'experiment-jobs.sqlite3')
            db.executescript('CREATE TABLE trials(id TEXT PRIMARY KEY,symbol TEXT,digest TEXT,created_utc TEXT,result_json TEXT); CREATE TABLE stress_reviews(trial_id TEXT PRIMARY KEY,created_utc TEXT,result_json TEXT);')
            result=dict(method='MOMENTUM',side='BUY',status='NEEDS_FORWARD_VALIDATION',development={'n':50,'mean_range_units':.3},review={'n':40,'mean_range_units':.2})
            db.execute('INSERT INTO trials VALUES(?,?,?,?,?)',('a'*64,'EURUSD','b'*64,'2026-10-20T00:00:00+00:00',json.dumps(result)));db.commit();db.close()
            self.assertEqual(publish_reports(root,batch=1),1)
            out=json.loads(Path(root,'research-reports.json').read_text())
            self.assertEqual(out['reviewed_experiments'],1)
            self.assertEqual(out['recent'][0]['decision'],'AWAITING_COST_REVIEWS')
            self.assertEqual(publish_reports(root,batch=1),0)
