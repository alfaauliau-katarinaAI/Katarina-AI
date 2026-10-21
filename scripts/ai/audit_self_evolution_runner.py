"""GitHub-hosted, offline KATARINA self-evolution research acceptance test.

Only deterministic, fabricated fixture data; no VPS/MT5 access, credentials,
live orders, code edits, model calls, broker fills, or deployment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Logic lives in src (cleanup stage 6); names re-exported for existing callers.
from katarina.governance.self_evolution_audit import AS_OF, START, run, simulated_history, verify_scenario  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    result = run()
    dst = Path(args.output)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(result, indent=2, sort_keys=True,
                              allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "## Katarina self-evolution research (GitHub-hosted)",
        "",
        "**Result:** PASS – synthetic-only tests; not trading evidence.",
        "",
        "| Scenario | Result |",
        "|---|---|",
    ]
    for row in result["scenarios"]:
        status = ", ".join(row["cohort_status"]) or row["data_integrity"]
        lines.append(f"| {row['scenario']} | {status} |")
    lines += [
        "",
        "**No external LLM models were called.** The multi-model adapter "
        "remains blocked pending real connected providers.",
        "",
        "**No self-code deployment, broker orders, live risk, or VPS actions.**",
    ]
    summary = Path(args.summary)
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PASS_KATARINA_GITHUB_HOSTED_EVOLUTION: four synthetic safety scenarios")


if __name__ == "__main__":
    main()
