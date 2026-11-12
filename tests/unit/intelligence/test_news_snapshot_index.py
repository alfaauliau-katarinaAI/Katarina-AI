"""RH-015 follow-up: per-cycle news cache lookups must use an index, never a full table scan."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from katarina.intelligence.news import market_article_context
from katarina.intelligence.news.public_context import ContextStore

QUERIES = (
    ("SELECT fetched,status,digest,payload,error FROM snapshots WHERE source=? AND fetched<=? "
     "ORDER BY fetched DESC,id DESC LIMIT 1", ("fed", "2026-11-12T00:00:00+00:00")),
    ("SELECT fetched FROM snapshots WHERE source=? ORDER BY id DESC LIMIT 1", ("fed",)),
    ("SELECT fetched,status,digest,raw,payload FROM snapshots WHERE source=? ORDER BY id DESC LIMIT 1", ("fed",)),
)


class SnapshotIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "context.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lookups_use_index_without_scan_or_sort(self):
        store = ContextStore(self.path)
        for sql, args in QUERIES:
            plan = " ".join(row[3] for row in store.db.execute("EXPLAIN QUERY PLAN " + sql, args))
            self.assertIn("USING INDEX", plan, sql)
            self.assertNotIn("SCAN snapshots", plan, sql)
            self.assertNotIn("TEMP B-TREE", plan, sql)
        store.db.close()

    def test_existing_database_gets_index_and_keeps_rows(self):
        db = sqlite3.connect(self.path)
        db.execute("""CREATE TABLE snapshots(id INTEGER PRIMARY KEY, source TEXT, fetched TEXT, status TEXT,
                      digest TEXT, raw BLOB, payload TEXT, error TEXT)""")
        db.executemany("INSERT INTO snapshots VALUES(NULL,?,?,?,?,?,?,?)",
                       [("fed", f"2026-11-0{i}T00:00:00+00:00", "OK", "d", b"x", "{}", "") for i in range(1, 6)])
        db.commit()
        before = db.execute("SELECT * FROM snapshots ORDER BY id").fetchall()
        db.close()
        store = ContextStore(self.path)
        names = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        self.assertTrue({"snapshots_source_fetched", "snapshots_source_id"} <= names)
        self.assertEqual(before, store.db.execute("SELECT * FROM snapshots ORDER BY id").fetchall())
        latest = store.latest("fed", datetime(2026, 11, 12, tzinfo=timezone.utc))
        self.assertEqual("2026-11-05T00:00:00+00:00", latest["fetched_utc"])
        store.db.close()

    def test_newest_articles_read_uses_index(self):
        db = sqlite3.connect(self.path)
        market_article_context._schema(db)
        plan = " ".join(r[3] for r in db.execute(
            "EXPLAIN QUERY PLAN SELECT url,published,body,fetched,sha256 FROM contextual_market_articles "
            "ORDER BY published DESC LIMIT 12"))
        self.assertIn("contextual_market_articles_published", plan)
        self.assertNotIn("TEMP B-TREE", plan)
        db.close()


if __name__ == "__main__":
    unittest.main()
