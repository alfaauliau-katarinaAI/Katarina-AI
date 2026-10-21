from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any


class IdempotencyConflict(RuntimeError):
    pass


class SchemaVersionError(RuntimeError):
    pass


@dataclass(frozen=True)
class AppendResult:
    record_id: str
    sequence: int
    inserted: bool


def _canonical_json(value: Any) -> str:
    # Python otherwise serializes NaN/Infinity as nonstandard JSON. Those
    # values cannot be safe evidence or persisted runtime risk state.
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("nonfinite_or_invalid_memory_payload") from exc


def _reject_nonfinite_memory_constant(value: str) -> None:
    raise ValueError("memory_nonfinite_json_constant:" + value)


def _payload_hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _verified_payload(row: sqlite3.Row) -> Any:
    """Reject changed or malformed stored evidence before any replay/restore.

    SQLite integrity_check verifies page structure, not that the original
    signed-by-digest payload is still present. This hash is a local integrity
    guard, not external authentication against a DB attacker who can rewrite
    both payload and hash.
    """
    raw = row["payload_json"]
    expected = row["payload_hash"]
    if (not isinstance(raw, str) or not isinstance(expected, str)
            or sha256(raw.encode("utf-8")).hexdigest() != expected):
        raise ValueError("memory_payload_digest_mismatch")
    try:
        return json.loads(raw, parse_constant=_reject_nonfinite_memory_constant)
    except (TypeError, ValueError) as exc:
        raise ValueError("memory_payload_corrupt") from exc


def _deterministic_id(namespace: str, value: Any) -> str:
    raw = (namespace + "\x00" + _canonical_json(value)).encode("utf-8")
    return sha256(raw).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    CURRENT_SCHEMA_VERSION = 1

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), timeout=30.0)
        try:
            self._conn.row_factory = sqlite3.Row
            self._configure()
            self._migrate()
        except Exception:
            self._conn.close()
            raise

    def _configure(self) -> None:
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA journal_mode=WAL")

    def _migrate(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        row = self._conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()
        if row is not None:
            version = int(row["value"])
            if version > self.CURRENT_SCHEMA_VERSION:
                raise SchemaVersionError(
                    f"database schema {version} is newer than supported {self.CURRENT_SCHEMA_VERSION}"
                )
        else:
            version = 0

        if version < 1:
            with self._conn:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS operational_events (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL UNIQUE,
                        event_type TEXT NOT NULL,
                        created_utc TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        payload_hash TEXT NOT NULL
                    )
                    """
                )
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trade_experiences (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        experience_id TEXT NOT NULL UNIQUE,
                        closed_utc TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        payload_hash TEXT NOT NULL
                    )
                    """
                )
                self._conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS operational_events_no_update
                    BEFORE UPDATE ON operational_events
                    BEGIN SELECT RAISE(ABORT, 'operational_events is append-only'); END
                    """
                )
                self._conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS operational_events_no_delete
                    BEFORE DELETE ON operational_events
                    BEGIN SELECT RAISE(ABORT, 'operational_events is append-only'); END
                    """
                )
                self._conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS trade_experiences_no_update
                    BEFORE UPDATE ON trade_experiences
                    BEGIN SELECT RAISE(ABORT, 'trade_experiences is append-only'); END
                    """
                )
                self._conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS trade_experiences_no_delete
                    BEFORE DELETE ON trade_experiences
                    BEGIN SELECT RAISE(ABORT, 'trade_experiences is append-only'); END
                    """
                )
                self._conn.execute(
                    "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version','1')"
                )
            version = 1

        if version != self.CURRENT_SCHEMA_VERSION:
            raise SchemaVersionError(
                f"database schema {version} does not match supported {self.CURRENT_SCHEMA_VERSION}"
            )

        # Additive index: no schema-data rewrite and no changes to immutable rows.
        with self._conn:
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_operational_events_type_seq "
                "ON operational_events(event_type, sequence)"
            )

    @property
    def schema_version(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()
        return int(row["value"])

    @staticmethod
    def deterministic_id(namespace: str, payload: Any) -> str:
        return _deterministic_id(namespace, payload)

    def append_operational_event(
        self,
        event_type: str,
        payload: Any,
        *,
        event_id: str | None = None,
        created_utc: str | None = None,
    ) -> AppendResult:
        if not event_type:
            raise ValueError("event_type is required")
        payload_json = _canonical_json(payload)
        digest = sha256(payload_json.encode("utf-8")).hexdigest()
        record_id = event_id or _deterministic_id("operational:" + event_type, payload)
        existing = self._conn.execute(
            "SELECT sequence,event_type,payload_json,payload_hash FROM operational_events WHERE event_id=?",
            (record_id,),
        ).fetchone()
        if existing is not None:
            _verified_payload(existing)
            if (existing["payload_hash"] != digest
                    or existing["event_type"] != event_type):
                raise IdempotencyConflict(f"event_id conflict: {record_id}")
            return AppendResult(record_id, int(existing["sequence"]), False)

        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO operational_events(event_id,event_type,created_utc,payload_json,payload_hash)
                VALUES(?,?,?,?,?)
                """,
                (record_id, event_type, created_utc or _utc_now(), payload_json, digest),
            )
        return AppendResult(record_id, int(cur.lastrowid), True)

    def append_trade_experience(
        self,
        payload: Any,
        *,
        experience_id: str | None = None,
        closed_utc: str | None = None,
    ) -> AppendResult:
        payload_json = _canonical_json(payload)
        digest = sha256(payload_json.encode("utf-8")).hexdigest()
        record_id = experience_id or _deterministic_id("trade_experience", payload)
        existing = self._conn.execute(
            "SELECT sequence,payload_json,payload_hash FROM trade_experiences WHERE experience_id=?",
            (record_id,),
        ).fetchone()
        if existing is not None:
            _verified_payload(existing)
            if existing["payload_hash"] != digest:
                raise IdempotencyConflict(f"experience_id conflict: {record_id}")
            return AppendResult(record_id, int(existing["sequence"]), False)

        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO trade_experiences(experience_id,closed_utc,payload_json,payload_hash)
                VALUES(?,?,?,?)
                """,
                (record_id, closed_utc or _utc_now(), payload_json, digest),
            )
        return AppendResult(record_id, int(cur.lastrowid), True)

    def load_operational_events(self, after_sequence: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        if limit <= 0 or limit > 10000:
            raise ValueError("limit must be between 1 and 10000")
        rows = self._conn.execute(
            """
            SELECT sequence,event_id,event_type,created_utc,payload_json,payload_hash
            FROM operational_events
            WHERE sequence>?
            ORDER BY sequence ASC
            LIMIT ?
            """,
            (int(after_sequence), int(limit)),
        ).fetchall()
        return [
            {
                "sequence": int(row["sequence"]),
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "created_utc": row["created_utc"],
                "payload": _verified_payload(row),
                "payload_hash": row["payload_hash"],
            }
            for row in rows
        ]

    def load_operational_event(self, event_id: str) -> dict[str, Any] | None:
        """Read original availability and payload with the same integrity guard."""
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("event_id_required")
        row = self._conn.execute(
            "SELECT sequence,event_id,event_type,created_utc,payload_json,payload_hash "
            "FROM operational_events WHERE event_id=?", (event_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "sequence":int(row["sequence"]), "event_id":row["event_id"],
            "event_type":row["event_type"], "created_utc":row["created_utc"],
            "payload":_verified_payload(row), "payload_hash":row["payload_hash"],
        }

    def load_recent_operational_events_of_type(
        self, event_type: str, *, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Bounded, indexed recall with original immutable provenance.

        Most recent records are returned in chronological order. Read-only.
        """
        if not event_type or not 1 <= limit <= 20001:
            raise ValueError("invalid event type or limit")
        rows = self._conn.execute(
            """
            SELECT sequence,event_id,event_type,created_utc,payload_json,payload_hash
            FROM operational_events
            WHERE event_type=?
            ORDER BY sequence DESC
            LIMIT ?
            """,
            (event_type, limit),
        ).fetchall()
        return [
            {
                "sequence": int(row["sequence"]),
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "created_utc": row["created_utc"],
                "payload": _verified_payload(row),
                "payload_hash": row["payload_hash"],
            }
            for row in reversed(rows)
        ]

    def load_latest_operational_event(self, event_type: str) -> dict[str, Any] | None:
        if not event_type:
            raise ValueError("event_type is required")
        row = self._conn.execute(
            """
            SELECT sequence,event_id,event_type,created_utc,payload_json,payload_hash
            FROM operational_events
            WHERE event_type=?
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (event_type,),
        ).fetchone()
        if row is None:
            return None
        return {
            "sequence": int(row["sequence"]),
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "created_utc": row["created_utc"],
            "payload": _verified_payload(row),
            "payload_hash": row["payload_hash"],
        }

    def load_trade_experiences(self, after_sequence: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        if limit <= 0 or limit > 10000:
            raise ValueError("limit must be between 1 and 10000")
        rows = self._conn.execute(
            """
            SELECT sequence,experience_id,closed_utc,payload_json,payload_hash
            FROM trade_experiences
            WHERE sequence>?
            ORDER BY sequence ASC
            LIMIT ?
            """,
            (int(after_sequence), int(limit)),
        ).fetchall()
        return [
            {
                "sequence": int(row["sequence"]),
                "experience_id": row["experience_id"],
                "closed_utc": row["closed_utc"],
                "payload": _verified_payload(row),
                "payload_hash": row["payload_hash"],
            }
            for row in rows
        ]

    def integrity_check(self) -> bool:
        row = self._conn.execute("PRAGMA integrity_check").fetchone()
        return bool(row and str(row[0]).lower() == "ok")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
