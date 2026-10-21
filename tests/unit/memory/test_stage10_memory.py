import sqlite3
from hashlib import sha256
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from katarina.memory import IdempotencyConflict, MemoryStore, SchemaVersionError


class Stage10MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "katarina.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_schema_initializes_and_integrity_is_ok(self):
        with MemoryStore(self.db) as store:
            self.assertEqual(store.schema_version, 1)
            self.assertTrue(store.integrity_check())

    def test_deterministic_id_is_order_independent_for_json_keys(self):
        left = MemoryStore.deterministic_id("x", {"a": 1, "b": 2})
        right = MemoryStore.deterministic_id("x", {"b": 2, "a": 1})
        self.assertEqual(left, right)

    def test_operational_event_is_idempotent(self):
        with MemoryStore(self.db) as store:
            first = store.append_operational_event("heartbeat", {"seq": 7}, event_id="evt-7")
            second = store.append_operational_event("heartbeat", {"seq": 7}, event_id="evt-7")
            self.assertTrue(first.inserted)
            self.assertFalse(second.inserted)
            self.assertEqual(first.sequence, second.sequence)

    def test_operational_id_conflict_fails_closed(self):
        with MemoryStore(self.db) as store:
            store.append_operational_event("heartbeat", {"seq": 7}, event_id="evt-7")
            with self.assertRaises(IdempotencyConflict):
                store.append_operational_event("heartbeat", {"seq": 8}, event_id="evt-7")

    def test_restart_recovery_preserves_order(self):
        with MemoryStore(self.db) as store:
            store.append_operational_event("a", {"v": 1}, event_id="a1")
            store.append_operational_event("b", {"v": 2}, event_id="b1")
        with MemoryStore(self.db) as store:
            rows = store.load_operational_events()
            self.assertEqual([r["event_id"] for r in rows], ["a1", "b1"])
            self.assertEqual([r["sequence"] for r in rows], [1, 2])

    def test_trade_experience_is_separate_from_operational_events(self):
        with MemoryStore(self.db) as store:
            store.append_operational_event("position_closed", {"ticket": 10}, event_id="op-10")
            store.append_trade_experience({"ticket": 10, "r_multiple": 1.25}, experience_id="xp-10")
            self.assertEqual(len(store.load_operational_events()), 1)
            self.assertEqual(len(store.load_trade_experiences()), 1)

    def test_append_only_operational_table_rejects_update_and_delete(self):
        with MemoryStore(self.db) as store:
            store.append_operational_event("a", {"v": 1}, event_id="a1")
            with self.assertRaises(sqlite3.DatabaseError):
                store._conn.execute("UPDATE operational_events SET event_type='x' WHERE event_id='a1'")
            with self.assertRaises(sqlite3.DatabaseError):
                store._conn.execute("DELETE FROM operational_events WHERE event_id='a1'")

    def test_append_only_trade_experience_rejects_update_and_delete(self):
        with MemoryStore(self.db) as store:
            store.append_trade_experience({"ticket": 1}, experience_id="x1")
            with self.assertRaises(sqlite3.DatabaseError):
                store._conn.execute("UPDATE trade_experiences SET closed_utc='x' WHERE experience_id='x1'")
            with self.assertRaises(sqlite3.DatabaseError):
                store._conn.execute("DELETE FROM trade_experiences WHERE experience_id='x1'")

    def test_unmodified_memory_survives_restart_and_duplicate_replay(self):
        with MemoryStore(self.db) as store:
            op = store.append_operational_event("risk", {"limit": .08}, event_id="risk-1")
            xp = store.append_trade_experience({"net_r": -1.5}, experience_id="xp-1")
            self.assertTrue(op.inserted)
            self.assertTrue(xp.inserted)
        with MemoryStore(self.db) as store:
            self.assertEqual(store.load_operational_events()[0]["payload"], {"limit": .08})
            self.assertEqual(store.load_latest_operational_event("risk")["payload"], {"limit": .08})
            self.assertEqual(store.load_trade_experiences()[0]["payload"], {"net_r": -1.5})
            self.assertFalse(store.append_operational_event(
                "risk", {"limit": .08}, event_id="risk-1").inserted)
            self.assertFalse(store.append_trade_experience(
                {"net_r": -1.5}, experience_id="xp-1").inserted)

    def test_reusing_operational_id_for_different_event_type_is_rejected(self):
        with MemoryStore(self.db) as store:
            store.append_operational_event("risk_guard", {"ok": True}, event_id="shared")
            with self.assertRaisesRegex(IdempotencyConflict, "event_id conflict"):
                store.append_operational_event(
                    "risk_override", {"ok": True}, event_id="shared")

    def test_modified_operational_payload_cannot_be_replayed_or_reused(self):
        with MemoryStore(self.db) as store:
            store.append_operational_event(
                "risk_snapshot", {"max_open_risk": .08}, event_id="trusted")
        # Simulate an outside writer bypassing SQLite append-only trigger,
        # in a disposable test DB only; never touch an Owner memory DB.
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("DROP TRIGGER operational_events_no_update")
            con.execute(
                "UPDATE operational_events SET payload_json=? WHERE event_id='trusted'",
                ('{"max_open_risk":0.99}',))
        with MemoryStore(self.db) as store:
            self.assertTrue(store.integrity_check())  # SQLite pages remain structurally valid
            with self.assertRaisesRegex(ValueError, "memory_payload_digest_mismatch"):
                store.load_operational_events()
            with self.assertRaisesRegex(ValueError, "memory_payload_digest_mismatch"):
                store.load_latest_operational_event("risk_snapshot")
            with self.assertRaisesRegex(ValueError, "memory_payload_digest_mismatch"):
                store.append_operational_event(
                    "risk_snapshot", {"max_open_risk": .08}, event_id="trusted")

    def test_modified_experience_payload_cannot_be_loaded_or_reused(self):
        with MemoryStore(self.db) as store:
            store.append_trade_experience(
                {"outcome": "LOSS", "net_r": -1.0}, experience_id="loss-1")
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("DROP TRIGGER trade_experiences_no_update")
            con.execute(
                "UPDATE trade_experiences SET payload_json=? WHERE experience_id='loss-1'",
                ('{"outcome":"WIN","net_r":3.0}',))
        with MemoryStore(self.db) as store:
            with self.assertRaisesRegex(ValueError, "memory_payload_digest_mismatch"):
                store.load_trade_experiences()
            with self.assertRaisesRegex(ValueError, "memory_payload_digest_mismatch"):
                store.append_trade_experience(
                    {"outcome": "LOSS", "net_r": -1.0}, experience_id="loss-1")

    def test_nonfinite_memory_payloads_cannot_be_appended(self):
        with MemoryStore(self.db) as store:
            for value in (float("nan"),float("inf"),-float("inf")):
                with self.subTest(nonfinite=str(value)):
                    with self.assertRaisesRegex(
                            ValueError,"nonfinite_or_invalid_memory_payload"):
                        store.append_operational_event("risk",{"dd":value})
                    with self.assertRaisesRegex(
                            ValueError,"nonfinite_or_invalid_memory_payload"):
                        store.append_trade_experience({"virtual_r":value})
                    with self.assertRaisesRegex(
                            ValueError,"nonfinite_or_invalid_memory_payload"):
                        store.deterministic_id("research",{"score":value})
            self.assertEqual(store.load_operational_events(),[])
            self.assertEqual(store.load_trade_experiences(),[])

    def test_legacy_matching_sha_nonfinite_memory_is_still_rejected(self):
        raw='{"fake_broker_r":NaN}'
        digest=sha256(raw.encode("utf-8")).hexdigest()
        with MemoryStore(self.db) as store:
            with store._conn:
                store._conn.execute(
                    "INSERT INTO operational_events("
                    "event_id,event_type,created_utc,payload_json,payload_hash)"
                    " VALUES (?,?,?,?,?)",
                    ("legacy-test","risk_snapshot","2026-01-01T00:00:00+00:00",raw,digest),
                )
            self.assertTrue(store.integrity_check())
            with self.assertRaisesRegex(ValueError,"memory_payload_corrupt"):
                store.load_operational_events()
            with self.assertRaisesRegex(ValueError,"memory_payload_corrupt"):
                store.load_latest_operational_event("risk_snapshot")
            with self.assertRaisesRegex(ValueError,"memory_payload_corrupt"):
                store.append_operational_event(
                    "risk_snapshot",{"fake_broker_r":0},event_id="legacy-test")

    def test_valid_finite_nested_memory_still_roundtrips(self):
        payload={"outer":{"growth":[0,1.25,-0.5],"side":"SELL"}}
        with MemoryStore(self.db) as store:
            first=store.append_operational_event("model",payload,event_id="valid")
            second=store.append_operational_event("model",payload,event_id="valid")
            self.assertTrue(first.inserted)
            self.assertFalse(second.inserted)
            self.assertEqual(store.load_latest_operational_event("model")["payload"],payload)

    def test_future_schema_version_is_rejected(self):
        conn = sqlite3.connect(str(self.db))
        conn.execute("CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO schema_meta(key,value) VALUES('schema_version','99')")
        conn.commit()
        conn.close()
        with self.assertRaises(SchemaVersionError):
            MemoryStore(self.db)


if __name__ == "__main__":
    unittest.main()
