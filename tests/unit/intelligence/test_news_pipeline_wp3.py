"""WP3 read-only news observability; all tests use injected feeds and clocks."""
from __future__ import annotations

import sqlite3
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from katarina.intelligence.cognition.observer import (
    load_articles, news_pipeline_summary,
)
from katarina.intelligence.operations import observation_ledger as ledger
from katarina.intelligence.operations.data_health import assess

UTC = timezone.utc
NOW = datetime(2026, 10, 23, 8, 0, tzinfo=UTC)


class FakeStore:
    def __init__(self, db, items=None, failed_sources=()):
        self.db = db
        self.items = items or {}
        self.failed = frozenset(failed_sources)

    def latest(self, source, now):
        if source in self.failed:
            return {"ready": False, "reason": "FETCH_FAILED"}
        return {"ready": True, "payload": {"items": self.items.get(source, [])}}


def entry(published, url):
    return {"published_utc": published, "url": url, "title": "Statement"}


class NewsPipelineTests(unittest.TestCase):
    def test_stale_invalid_and_latest_age_are_diagnostic_only(self):
        old = (NOW - timedelta(hours=10)).isoformat()
        store = FakeStore(sqlite3.connect(":memory:"), {
            "fed": [entry(old, "https://www.federalreserve.gov/old"),
                    entry("invalid", "https://www.federalreserve.gov/bad")]
        })
        try:
            articles, diag = load_articles(store, NOW, allow_fetch=False)
            self.assertEqual(articles, [])
            self.assertEqual(diag["fed_items_older_than_window"], 1)
            self.assertEqual(diag["fed_item_invalid_time"], 1)
            self.assertEqual(diag["fed_feed_items"], 2)
            self.assertEqual(diag["fed_items_in_window"], 0)
            self.assertEqual(diag["fed_newest_item_age_hours"], 10.0)
        finally:
            store.db.close()

    def test_missing_feed_timestamp_is_diagnostic_not_sort_failure(self):
        old = (NOW - timedelta(hours=8)).isoformat()
        store = FakeStore(sqlite3.connect(":memory:"), {
            "fed": [entry(None, "https://www.federalreserve.gov/invalid"),
                    entry(old, "https://www.federalreserve.gov/old")],
        })
        try:
            articles, diag = load_articles(store, NOW, allow_fetch=False)
            self.assertEqual(articles, [])
            self.assertEqual(diag["fed_item_invalid_time"], 1)
            self.assertEqual(diag["fed_items_older_than_window"], 1)
        finally:
            store.db.close()

    def test_article_fetch_failure_is_not_mislabelled_as_no_release(self):
        fresh = (NOW - timedelta(minutes=20)).isoformat()
        store = FakeStore(sqlite3.connect(":memory:"), {
            "fed": [entry(fresh, "https://www.federalreserve.gov/example")]
        })
        try:
            with patch("katarina.intelligence.cognition.observer.fetch_official_article",
                       side_effect=ValueError("synthetic")):
                articles, diag = load_articles(store, NOW, allow_fetch=True)
            report = news_pipeline_summary(diag, articles)
            self.assertEqual(articles, [])
            self.assertEqual(report["fed"]["feed_items"], 1)
            self.assertEqual(report["fed"]["in_window"], 1)
            self.assertEqual(report["fed"]["newest_age_hours"], 0.3)
            self.assertEqual(report["fed"]["verified"], 0)
            self.assertEqual(report["fed"]["failures"], {"article_unavailable_ValueError": 1})
        finally:
            store.db.close()

    def test_record_news_creates_one_row_per_source_per_cycle(self):
        with closing(sqlite3.connect(":memory:")) as db:
            key = "c-20261023T080000.000000Z"
            summary = {
                "fed": {"feed_items": 1, "newest_age_hours": 0.3, "in_window": 1,
                        "verified": 0, "failures": {"article_unavailable_ValueError": 1}},
                "ecb": {"feed_items": 0, "newest_age_hours": None, "in_window": 0,
                        "verified": 0, "failures": {}},
            }
            ledger.record_news(db, key, summary)
            ledger.record_news(db, key, summary)
            rows = db.execute(
                "SELECT source, feed_items, verified, failures_json FROM observer_news "
                "WHERE cycle_id=? ORDER BY source", (key,)).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][:3], ("ecb", 0, 0))
            self.assertEqual(rows[1][0], "fed")
            self.assertEqual(rows[1][3], '{"article_unavailable_ValueError": 1}')

    def test_data_health_distinguishes_no_release_from_fetch_failure_without_verdict_change(self):
        with closing(sqlite3.connect(":memory:")) as db:
            stamps = [NOW, NOW + timedelta(minutes=1), NOW + timedelta(minutes=2)]
            cycles = []
            for moment in stamps:
                ident = ledger.record_snapshot(
                    db, observed_utc=moment, clock_shift_hours=3,
                    cards={"EURUSD": {"action": "WAIT"}},
                    quotes={"EURUSD": (1.1, 1.1001, moment.timestamp() - 1)})
                ledger.close_cycle(db, finished_utc=moment, cycle_id=ident, status="OK")
                cycles.append(ident)
            original = assess(db, NOW + timedelta(hours=1))
            ledger.record_news(db, cycles[0], {
                "fed": {"feed_items": 3, "newest_age_hours": 11.0, "in_window": 0,
                        "verified": 0, "failures": {}},
            })
            ledger.record_news(db, cycles[1], {
                "fed": {"feed_items": 1, "newest_age_hours": 0.2, "in_window": 1,
                        "verified": 0, "failures": {"article_unavailable_ValueError": 1}},
            })
            ledger.record_news(db, cycles[2], {
                "fed": {"feed_items": 1, "newest_age_hours": 0.2, "in_window": 1,
                        "verified": 1, "failures": {}},
            })
            updated = assess(db, NOW + timedelta(hours=1))
            news = updated["news_pipeline"]
            self.assertEqual(updated["verdict"], original["verdict"])
            self.assertEqual([x["status"] for x in updated["criteria"]],
                             [x["status"] for x in original["criteria"]])
            self.assertEqual(news["cycles_with_news_rows"], 3)
            self.assertEqual(news["cycles_without_verified_articles"], 2)
            self.assertEqual(news["no_recent_release_cycles"], 1)
            self.assertEqual(news["retrieval_failed_cycles"], 1)
            self.assertEqual(news["no_recent_release_percent"], 50.0)
            self.assertEqual(news["retrieval_failed_percent"], 50.0)
            self.assertEqual(news["verdict_effect"], "NONE")


if __name__ == "__main__":
    unittest.main()
