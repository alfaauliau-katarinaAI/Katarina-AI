#!/usr/bin/env python3
"""Thin CLI tool to collect bar clock evidence and generate historical evidence report.

Read-only evidence collection tool for research/development use.
Rejects output paths located inside the repository tree to prevent repo/holdout pollution.
Imports MetaTrader5 only inside main() when connecting to MT5.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from katarina.research.bar_clock_evidence import (
    DEFAULT_CALENDAR_PATH,
    build_evidence_report,
    collect_release_samples,
)
from katarina.research.validation import ValidationError, canonical, sha256_text


def is_path_inside_repo(out_path: str | Path) -> bool:
    """True if out_path resolves to a location within REPO_ROOT."""
    try:
        resolved = Path(out_path).resolve()
        return resolved == REPO_ROOT or REPO_ROOT in resolved.parents
    except Exception:
        return True


def build_evidence(
    broker: object,
    calendar_path: str | Path = DEFAULT_CALENDAR_PATH,
    max_releases: int = 50,
    *,
    generated_utc: str | datetime | None = None,
) -> dict:
    cal_p = Path(calendar_path)
    if not cal_p.is_file():
        raise ValidationError("CALENDAR_FILE_NOT_FOUND")

    cal_content = cal_p.read_text(encoding="utf-8")
    if not cal_content.strip():
        raise ValidationError("CALENDAR_EVIDENCE_EMPTY")

    rows = list(csv.DictReader(cal_content.strip().splitlines()))
    if not rows:
        raise ValidationError("CALENDAR_EVIDENCE_EMPTY")

    if type(max_releases) is not int or max_releases <= 0:
        raise ValidationError("INVALID_MAX_RELEASES")

    selected_rows = rows[:max_releases]
    samples, rejected = collect_release_samples(broker, selected_rows)

    if not samples:
        raise ValidationError("NO_SAMPLES_COLLECTED_FAIL_CLOSED")

    provenance = {
        "calendar_path": str(cal_p),
        "max_releases": max_releases,
        "processed_releases": len(selected_rows),
    }
    if generated_utc is not None:
        if isinstance(generated_utc, str):
            dt = datetime.fromisoformat(generated_utc.replace("Z", "+00:00"))
        else:
            dt = generated_utc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        provenance["generated_utc"] = dt.astimezone(timezone.utc).isoformat()

    report = build_evidence_report(
        cal_content,
        samples,
        rejected=rejected,
        provenance=provenance,
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build historical bar clock evidence report.")
    parser.add_argument(
        "--calendar",
        default=str(DEFAULT_CALENDAR_PATH),
        help="Path to release calendar CSV (default: config/research/us_release_calendar.csv)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output file path (must be OUTSIDE repository directory)",
    )
    parser.add_argument(
        "--max-releases",
        type=int,
        default=50,
        help="Maximum releases to process (default: 50)",
    )

    args = parser.parse_args()

    out_path = Path(args.out)
    if is_path_inside_repo(out_path):
        sys.stderr.write("ERROR: Output path must be outside repository directory.\n")
        return 1

    try:
        import MetaTrader5 as mt5
    except ImportError:
        sys.stderr.write("ERROR: MetaTrader5 package not available.\n")
        return 1

    if not mt5.initialize():
        sys.stderr.write("ERROR: Failed to initialize MT5 connection.\n")
        return 1

    try:
        report = build_evidence(
            broker=mt5,
            calendar_path=args.calendar,
            max_releases=args.max_releases,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(canonical(report) + "\n", encoding="utf-8")
        sys.stdout.write(f"SUCCESS: Evidence report written to {out_path}\n")
        return 0
    except ValidationError as err:
        sys.stderr.write(f"FAIL-CLOSED: {err}\n")
        return 1
    except Exception as ex:
        sys.stderr.write(f"FAIL-CLOSED: Unexpected error {type(ex).__name__}\n")
        return 1
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
