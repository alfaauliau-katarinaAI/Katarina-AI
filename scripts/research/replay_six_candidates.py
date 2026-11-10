#!/usr/bin/env python3
"""Replay the six XAUUSD candidates over one verified development tick file (research only, no orders).

A real-data run is a backtest and needs a separate Owner approval: without ``--owner-approval-ref`` this
CLI only validates the inputs (hash, manifest, cutoff, quote grid) and exits. The output is the
deterministic event ledger plus per-candidate event counts; it deliberately prints no profit metrics.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from katarina.research.tick_replay import ReplayInputError, TickReplay  # noqa: E402
from katarina.research.tick_replay.dataset import load_inputs  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticks", required=True, type=Path, help="CSV time_msc,bid,ask[,flags]")
    parser.add_argument("--manifest", required=True, type=Path, help="evidence manifest JSON")
    parser.add_argument("--output-dir", type=Path, help="where ledger.jsonl and summary.json are written")
    parser.add_argument("--owner-approval-ref", help="link/id of the Owner approval for running a replay")
    args = parser.parse_args(argv)
    try:
        ticks, dataset, contract, costs, sessions = load_inputs(args.ticks, args.manifest)
    except ReplayInputError as exc:
        print(json.dumps({"status": "REJECTED", "reason_code": exc.reason, "detail": str(exc)}))
        return 2
    report = {"status": "INPUT_VALID", "ticks": len(ticks), "first_ms": ticks[0].time_ms,
              "last_ms": ticks[-1].time_ms, "sessions_present": sessions is not None,
              "sequence_evidence": dataset.sequence_evidence}
    if not args.owner_approval_ref:
        report["replay"] = "NOT_RUN_OWNER_APPROVAL_REQUIRED"
        print(json.dumps(report, sort_keys=True))
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required when running a replay")
    replay = TickReplay(ticks, contract=contract, dataset=dataset, costs=costs, sessions=sessions)
    result = replay.run()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "ledger.jsonl").open("w", encoding="utf-8") as handle:
        for event in replay.events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    summary = {key: value for key, value in result.items() if key != "candidates"}
    summary["owner_approval_ref"] = args.owner_approval_ref
    summary["event_counts"] = {cid: c["event_counts"] for cid, c in result["candidates"].items()}
    (args.output_dir / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2), encoding="utf-8")
    report.update(replay="RUN", ledger_sha256=result["ledger_sha256"])
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
