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
