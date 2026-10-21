"""GitHub-hosted, offline KATARINA self-evolution research acceptance test.

Only deterministic, fabricated fixture data; no VPS/MT5 access, credentials,
live orders, code edits, model calls, broker fills, or deployment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from katarina.governance.multi_model_evolution_review import review_candidate
from katarina.intelligence.lab.evidence_risk import EvidenceRiskGate
from katarina.intelligence.cognition.self_evolution_lab import evaluate_shadow_self_evolution

START = datetime(2026, 7, 1, tzinfo=timezone.utc)
AS_OF = datetime(2026, 8, 10, tzinfo=timezone.utc)
SCHEMA = """CREATE TABLE prospective_shadow (
    id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, method TEXT NOT NULL,
    side TEXT NOT NULL, regime TEXT NOT NULL, observed_at REAL NOT NULL,
    exit_at REAL, state TEXT NOT NULL, virtual_net_r REAL,
    evidence_score REAL NOT NULL, official_news_verified INTEGER NOT NULL
)"""


def simulated_history(*, days: int, strong_net_r: float, weak_net_r: float,
                      corrupt_future: bool = False) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute(SCHEMA)
    entries = []
    for day in range(days):
        for index in range(8):
            oid = day * 8 + index + 1
            observed = (START + timedelta(days=day, hours=index + 1)).timestamp()
            strong = index % 2 == 0
            exit_at = observed + 3600
            if corrupt_future and oid == 1:
                exit_at = (AS_OF + timedelta(hours=1)).timestamp()
            entries.append((
                oid, "SYNTHETIC.XAU", "SYNTHETIC_SWEEP", "SELL", "TREND_DOWN",
                observed, exit_at, "VIRTUAL_QUOTED",
                strong_net_r if strong else weak_net_r,
                0.85 if strong else 0.64, 0,
            ))
    db.executemany("INSERT INTO prospective_shadow VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   entries)
    return db


def verify_scenario(name: str, db: sqlite3.Connection) -> dict:
    try:
        report = evaluate_shadow_self_evolution(db, as_of_utc=AS_OF)
    finally:
        db.close()
    review = review_candidate(report)
    # No test-only mode or two invented LLM reviewers can override real
    # broker evidence / frozen constitution / authorization.
    assert report["live_risk_authorized_fraction"] == 0
    assert report["promotion_allowed"] is False
    assert report["order_submission_authorized"] is False
    assert report["self_code_mutation_authorized"] is False
    assert report["external_models_invoked"] == 0
    assert review.real_execution_authorized is False
    assert review.code_mutation_authorized is False
    assert review.status == "REVIEW_BLOCKED"
    assert "no_external_models_connected" in review.blockers
    assert "two_independent_providers_required" in review.blockers

    # Verify reproducible content and review receipt under the same as-of.
    if report["data_integrity"] == "VALID":
        # No use of external sources or imaginary exchange results.
        assert len(report["source_digest_sha256"]) == 64
        assert len(report["review_receipt_sha256"]) == 64
    return {
        "scenario": name,
        "observations": report["rows_read"],
        "data_integrity": report["data_integrity"],
        "decision": report["decision"],
        "cohort_status": [x["status"] for x in report["cohorts"]],
        "candidate_cutoffs": [x["proposed_min_evidence_score"]
                              for x in report["cohorts"]],
        "source_digest_sha256": report["source_digest_sha256"],
        "review_receipt_sha256": report["review_receipt_sha256"],
        "multi_model_review": review.status,
        "model_connections": report["external_models_invoked"],
        "live_execution_authorized": False,
        "model_promotion_authorized": False,
    }


def run() -> dict:
    cases = [
        verify_scenario("fabricated_positive_threshold_experiment",
            simulated_history(days=30, strong_net_r=2.0, weak_net_r=-1.0)),
        verify_scenario("fabricated_negative_strategy",
            simulated_history(days=30, strong_net_r=-0.3, weak_net_r=-0.9)),
        verify_scenario("fabricated_insufficient_data",
            simulated_history(days=5, strong_net_r=2.0, weak_net_r=-1.0)),
        verify_scenario("fabricated_future_outcome_leak",
            simulated_history(days=30, strong_net_r=2.0, weak_net_r=-1.0,
                              corrupt_future=True)),
    ]
    assert cases[0]["decision"] == "RESEARCH_PROPOSAL_ONLY"
    assert cases[0]["cohort_status"] == ["RESEARCH_CANDIDATE_REVIEW_REQUIRED"]
    assert cases[0]["candidate_cutoffs"] == [0.70]
    assert cases[1]["decision"] == "WAIT_FOR_VERIFIED_EVIDENCE"
    assert cases[2]["cohort_status"] == ["INSUFFICIENT_EVIDENCE"]
    assert cases[3]["data_integrity"] == "INVALID"
    assert cases[3]["decision"] == "WAIT_FOR_VERIFIED_EVIDENCE"
    evidence = EvidenceRiskGate().assess(None, None)
    assert evidence.level == "WAIT"
    assert evidence.live_authorized_fraction == 0
    return {
        "audit": "KATARINA_GITHUB_HOSTED_SELF_EVOLUTION_V1",
        "result": "PASS_SYNTHETIC_ONLY_NO_LIVE_PROMOTION",
        "evidence_origin": "FABRICATED_OFFLINE_SQLITE_FIXTURES_NOT_MARKET_DATA",
        "code_execution": "GITHUB_HOSTED_RUNNER_ONLY",
        "as_of_utc": AS_OF.isoformat(),
        "total_scenarios": len(cases),
        "scenarios": cases,
        "risk_gate": evidence.to_dict(),
        "external_ai_models_connected": False,
        "real_broker_trade_outcomes": 0,
        "independent_forward_edge_proven": False,
        "self_rewrite_or_merge_permitted": False,
        "trading_orders_permitted": False,
        "vps_access_or_change": False,
    }


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
