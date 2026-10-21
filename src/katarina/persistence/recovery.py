from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from katarina.persistence.sqlite_journal import SQLiteAppendOnlyJournal
from katarina.persistence.stores import (
    SQLiteExperienceMemoryStore,
    SQLiteOperationalStateStore,
)


class RecoveryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    journal_tail_ordinal: int
    snapshot_key: str
    snapshot_ordinal: int
    replay_after_ordinal: int
    snapshot_usable: bool
    reason: str
    live_risk_ready: bool = False
    live_execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.live_risk_ready or self.live_execution_authority:
            raise ValueError("persistence recovery cannot grant live authority")


def build_recovery_plan(
    journal: SQLiteAppendOnlyJournal,
    operational: SQLiteOperationalStateStore,
    *,
    snapshot_key: str = "runtime",
) -> RecoveryPlan:
    """Build fail-closed replay plan.

    A snapshot is only an acceleration hint. If it is absent, corrupt, or points
    beyond the authoritative journal tail, recovery replays from ordinal zero.
    """

    tail = journal.tail_ordinal()
    try:
        snapshot = operational.get(snapshot_key)
    except Exception as exc:
        return RecoveryPlan(
            journal_tail_ordinal=tail,
            snapshot_key=snapshot_key,
            snapshot_ordinal=0,
            replay_after_ordinal=0,
            snapshot_usable=False,
            reason=f"snapshot unavailable or invalid: {exc}",
        )

    if snapshot is None:
        return RecoveryPlan(
            journal_tail_ordinal=tail,
            snapshot_key=snapshot_key,
            snapshot_ordinal=0,
            replay_after_ordinal=0,
            snapshot_usable=False,
            reason="no operational snapshot; full journal replay required",
        )

    if snapshot.source_journal_ordinal > tail:
        return RecoveryPlan(
            journal_tail_ordinal=tail,
            snapshot_key=snapshot_key,
            snapshot_ordinal=snapshot.source_journal_ordinal,
            replay_after_ordinal=0,
            snapshot_usable=False,
            reason="snapshot cursor is ahead of authoritative journal tail",
        )

    return RecoveryPlan(
        journal_tail_ordinal=tail,
        snapshot_key=snapshot_key,
        snapshot_ordinal=snapshot.source_journal_ordinal,
        replay_after_ordinal=snapshot.source_journal_ordinal,
        snapshot_usable=True,
        reason="validated operational snapshot may accelerate journal replay",
    )


class PersistenceBundle:
    """Three physically separate Stage-10 SQLite stores."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

        self.journal_path = self.root / "event_journal.sqlite3"
        self.operational_path = self.root / "operational_state.sqlite3"
        self.experience_path = self.root / "experience_memory.sqlite3"

        resolved = {
            self.journal_path.resolve(),
            self.operational_path.resolve(),
            self.experience_path.resolve(),
        }
        if len(resolved) != 3:
            raise RecoveryError("persistence stores must use distinct database files")

        self.journal = SQLiteAppendOnlyJournal(self.journal_path)
        try:
            self.operational = SQLiteOperationalStateStore(
                self.operational_path
            )
            try:
                self.experience = SQLiteExperienceMemoryStore(
                    self.experience_path
                )
            except Exception:
                self.operational.close()
                raise
        except Exception:
            self.journal.close()
            raise

    def recovery_plan(self, *, snapshot_key: str = "runtime") -> RecoveryPlan:
        return build_recovery_plan(
            self.journal,
            self.operational,
            snapshot_key=snapshot_key,
        )

    def integrity_report(self) -> dict[str, object]:
        journal = self.journal.integrity_report()
        operational = self.operational.integrity_report()
        experience = self.experience.integrity_report()
        return {
            "journal": journal,
            "operational": operational,
            "experience": experience,
            "all_passed": bool(
                journal["passed"]
                and operational["passed"]
                and experience["passed"]
            ),
        }

    def close(self) -> None:
        self.experience.close()
        self.operational.close()
        self.journal.close()

    def __enter__(self) -> "PersistenceBundle":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


__all__ = (
    "PersistenceBundle",
    "RecoveryError",
    "RecoveryPlan",
    "build_recovery_plan",
)
