"""Synthetic broker-clock fixture for integration tests ONLY.

These bytes are invented and may never serve as real Stage-0 data evidence.
Do not import from runtime, deploy, or copy into a real broker state directory.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path


def seed_synthetic_clock(root: str | Path, *, server: str, shift_hours: int) -> None:
    """Provide a short-lived MOCK clock source for an isolated temp test root."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if not isinstance(server, str) or not server:
        raise ValueError("synthetic_broker_server_required")
    if type(shift_hours) is not int or not -12 <= shift_hours <= 14:
        raise ValueError("synthetic_shift_invalid")
    now = datetime.now(timezone.utc)
    source_bytes = ("SYNTHETIC_TEST_ONLY_NOT_BROKER_PROOF\\n"
                    + server + "\\n").encode("utf-8")
    (root / "broker-clock-source.txt").write_bytes(source_bytes)
    metadata = {
        "schema_version": 1,
        "shift_hours": shift_hours,
        "valid_from": (now - timedelta(minutes=2)).isoformat(),
        "valid_until": (now + timedelta(minutes=2)).isoformat(),
        "source": "INDEPENDENT_CLOCK_OBSERVATION",
        "source_sha256": sha256(source_bytes).hexdigest(),
        "broker_server_sha256": sha256(server.encode("utf-8")).hexdigest(),
    }
    (root / "broker-clock-evidence.json").write_text(
        json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
