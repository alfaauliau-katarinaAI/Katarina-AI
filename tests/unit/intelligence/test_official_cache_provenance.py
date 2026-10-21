"""News transport CACHED never bypasses digest, freshness, or coverage."""
import unittest
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json,sqlite3
from katarina.intelligence.news.official_cache_provenance import inspect_cached_official_sources

NOW=datetime(2026,10,15,9,tzinfo=timezone.utc)

class OfficialCacheTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("""CREATE TABLE snapshots(
            id INTEGER PRIMARY KEY,source TEXT,fetched TEXT,status TEXT,
            digest TEXT,raw BLOB,payload TEXT,error TEXT)""")
    def tearDown(self):self.db.close()
    def record(self,source,*,age=0,status="OK",raw=b"feed",valid_digest=True):
        payload={"coverage":["USD"],"items":[{"id":"test"}]}
        if source=="calendar":
            payload=dict(coverage=["USD"],events=[],
                coverage_from=(NOW-timedelta(days=1)).isoformat(),
                coverage_to=(NOW+timedelta(days=1)).isoformat())
        digest=sha256(raw).hexdigest() if valid_digest else "f"*64
        self.db.execute("INSERT INTO snapshots VALUES(NULL,?,?,?,?,?,?,?)",(
            source,(NOW-timedelta(seconds=age)).isoformat(),
            status,digest,raw,json.dumps(payload),""))
    def populate(self):
        for k in ("fed","ecb","boe","calendar"):self.record(k)

    def test_four_good_sources_are_transport_only(self):
        self.populate()
        r=inspect_cached_official_sources(self.db,as_of_utc=NOW)
        self.assertEqual(r["status"],"ALL_FOUR_SOURCE_CACHES_VERIFIED")
        self.assertTrue(r["all_four_cache_digests_fresh"])
        self.assertFalse(r["point_in_time_article_relevance_verified"])
        self.assertFalse(r["live_execution_authorized"])

    def test_cached_recent_error_invalidates_older_good(self):
        self.populate()
        self.record("fed",status="ERROR")
        r=inspect_cached_official_sources(self.db,as_of_utc=NOW)
        self.assertEqual(r["status"],"SOURCE_CACHE_DEGRADED")
        self.assertEqual(r["sources"]["fed"]["status"],"LATEST_FETCH_NOT_OK")

    def test_detect_digest_tamper_and_stale_receipt(self):
        self.populate()
        self.record("ecb",valid_digest=False)
        self.record("boe",age=4000)
        r=inspect_cached_official_sources(self.db,as_of_utc=NOW)
        self.assertEqual(r["sources"]["ecb"]["status"],
                         "TAMPERED_OR_MISSING_RAW_DIGEST")
        self.assertEqual(r["sources"]["boe"]["status"],
                         "STALE_CACHE_RECEIPT")

    def test_future_receipt_and_missing_sources(self):
        self.record("fed",age=-10)
        r=inspect_cached_official_sources(self.db,as_of_utc=NOW)
        self.assertEqual(r["sources"]["fed"]["status"],"FUTURE_CACHE_RECEIPT")
        self.assertEqual(r["sources"]["ecb"]["status"],"SOURCE_UNAVAILABLE")

    def test_no_naive_datetime(self):
        with self.assertRaisesRegex(ValueError,"timezone_aware"):
            inspect_cached_official_sources(
                self.db,as_of_utc=datetime(2026,10,15))

if __name__=="__main__":
    unittest.main()
