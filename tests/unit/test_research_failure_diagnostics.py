"""Research FAILED events carry a short, public error class for diagnosis."""
from datetime import datetime, timezone
import sqlite3
import tempfile
import unittest
from pathlib import Path

from katarina.intelligence.autonomous_research import REPORT_INTERVAL_SECONDS, ResearchWorker
from katarina.intelligence.research_capacity import DB_TIMEOUT
from katarina.monitoring.activity_trace import clean_activity, error_code


class Trace:
    def __init__(self):
        self.events = []

    def emit(self, phase, state, **values):
        self.events.append(dict(phase=phase, state=state, **values))


class ErrorCodeTest(unittest.TestCase):
    def test_locked_database_is_named_without_message_text(self):
        code = error_code(sqlite3.OperationalError('database is locked at C:/private/path'))
        self.assertEqual(code, 'OperationalError:locked')
        self.assertNotIn('private', code)

    def test_busy_and_plain_errors(self):
        self.assertEqual(error_code(sqlite3.OperationalError('database is busy')), 'OperationalError:busy')
        self.assertEqual(error_code(ValueError('DATASET_INTEGRITY_FAILED')), 'ValueError')

    def test_public_activity_keeps_error_field(self):
        now = datetime.now(timezone.utc)
        event = dict(seq=1, at_utc=now.isoformat(), phase='TEST_MOMENTUM_H4', state='FAILED',
                     action='AUTONOMOUS_CACHED_RESEARCH', error='OperationalError:locked')
        clean = clean_activity(dict(pid=1, cycle=0, events=[event]), now=now)
        self.assertEqual(clean['events'][0]['error'], 'OperationalError:locked')

    def test_public_activity_drops_unsafe_error_text(self):
        now = datetime.now(timezone.utc)
        event = dict(seq=1, at_utc=now.isoformat(), phase='GEMINI', state='FAILED',
                     error='database is locked at C:\\Users\\owner')
        clean = clean_activity(dict(pid=1, cycle=0, events=[event]), now=now)
        self.assertNotIn('error', clean['events'][0])


class LockTuningTest(unittest.TestCase):
    def test_lock_wait_is_longer_than_two_seconds_but_below_stop_timeout(self):
        self.assertGreater(DB_TIMEOUT, 2)
        self.assertLess(DB_TIMEOUT, 15)

    def test_reports_are_published_sparsely(self):
        self.assertGreaterEqual(REPORT_INTERVAL_SECONDS, 30)


class WorkerFailureEventTest(unittest.TestCase):
    def test_failed_experiment_event_names_error_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with sqlite3.connect(root / 'context.sqlite3') as data:
                data.execute('CREATE TABLE lab_universe(symbol TEXT PRIMARY KEY)')
                data.execute('CREATE TABLE lab_bars(symbol TEXT,stamp INTEGER,o REAL,h REAL,l REAL,c REAL)')
                data.execute('CREATE TABLE lab_runs(id TEXT,symbol TEXT,created_utc TEXT,digest TEXT,result_json TEXT)')
                data.execute("INSERT INTO lab_universe VALUES('XAUUSD')")
                data.executemany('INSERT INTO lab_bars VALUES(?,?,?,?,?,?)',
                                 [('XAUUSD', 3600 * i, 100 + i % 7, 103 + i % 7, 98 + i % 7, 101 + i % 7) for i in range(600)])
                data.execute("INSERT INTO lab_runs VALUES('r','XAUUSD','2026-10-21','d','{\"spread_proxy_price\": 0.1}')")
            trace = Trace()
            worker = ResearchWorker(root, trace, 'MOMENTUM', 4)
            import katarina.intelligence.autonomous_research as module
            original = module.evaluate
            module.evaluate = lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError('database is locked'))
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    worker.tick()
            finally:
                module.evaluate = original
            failed = [e for e in trace.events if e['state'] == 'FAILED']
            self.assertEqual(failed[-1]['error'], 'OperationalError:locked')
            self.assertEqual(worker.state['last_error'], 'OperationalError:locked')


if __name__ == '__main__':
    unittest.main()
