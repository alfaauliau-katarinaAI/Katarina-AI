from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from katarina.intelligence.operations.parallel_storage import prepare_parallel_storage
class ParallelStorageTests(unittest.TestCase):
    def test_reader_can_hold_snapshot_while_writer_commits_and_evidence_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'experiment-jobs.sqlite3'
            with closing(sqlite3.connect(path)) as db,db:
                db.execute('CREATE TABLE evidence(id INTEGER PRIMARY KEY,value TEXT)')
                db.execute("INSERT INTO evidence VALUES(1,'preserve')")
            self.assertEqual(prepare_parallel_storage(root)['experiment-jobs.sqlite3'],'wal')
            with closing(sqlite3.connect(path,timeout=.1)) as reader,closing(sqlite3.connect(path,timeout=.1)) as writer:
                reader.execute('BEGIN');self.assertEqual(reader.execute('SELECT COUNT(*) FROM evidence').fetchone()[0],1)
                with writer:writer.execute("INSERT INTO evidence VALUES(2,'new')")
                self.assertEqual(reader.execute('SELECT COUNT(*) FROM evidence').fetchone()[0],1)
                reader.rollback()
                self.assertEqual(reader.execute('SELECT value FROM evidence ORDER BY id').fetchall(),[('preserve',),('new',)])
