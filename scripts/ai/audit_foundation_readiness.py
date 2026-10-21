"""Audit the single canonical observer, broker risk telemetry and knowledge ledger.

No MT5 imports, order gateways, trades, new scheduler, network, or DB writes.
Run on VPS after each engineering change; verdict is RESEARCH ONLY.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.operations.foundation_readiness import assess_foundation
from katarina.intelligence.cognition.unified_cognitive_cycle import verify_cognitive_history


def audit(root: Path, *, now_utc: datetime, max_age_seconds: int = 720) -> dict:
    if now_utc.tzinfo is None or not 30 <= max_age_seconds <= 3600:
        raise ValueError("invalid_audit_time_window")
    now=now_utc.astimezone(timezone.utc)
    root=root.resolve()
    latest=root/"latest.json"
    database=root/"context.sqlite3"
    if not latest.is_file() or not database.is_file():
        raise FileNotFoundError("single_canonical_observer_artifacts_missing")
    snapshot=json.loads(latest.read_text(encoding="utf-8"))
    engineering=assess_foundation(snapshot,
                                 expected_symbols=snapshot.get("observed_symbols",17))
    snapshot_at=datetime.fromisoformat(
        snapshot["observed_at_utc"].replace("Z","+00:00"))
    if snapshot_at.tzinfo is None:
        raise ValueError("unverifiable_observer_snapshot_timestamp")
    age=(now-snapshot_at.astimezone(timezone.utc)).total_seconds()
    freshness_ok=0 <= age <= max_age_seconds
    uri=database.as_uri()+"?mode=ro"
    with sqlite3.connect(uri,uri=True,timeout=8) as db:
        db.execute("PRAGMA query_only=ON")
        integrity=db.execute("PRAGMA quick_check").fetchone()
        disk_ok=bool(integrity and integrity[0]=="ok")
        knowledge=verify_cognitive_history(db)
        rows=dict(db.execute(
            "SELECT state,COUNT(*) FROM prospective_shadow GROUP BY state"))
    checkpoint=snapshot.get("unified_cognitive_cycle",{}).get(
        "active_checkpoint_sha256")
    persisted=knowledge.get("active_checkpoint_sha256")
    learned_consistent=(checkpoint==persisted and
                        snapshot.get("unified_cognitive_cycle",{}).get(
                            "source_snapshot_matches_active") is True)
    snapshot_rows=snapshot.get("virtual_shadow_summary",{}).get("counts",{})
    shadow_matches=snapshot_rows==rows
    criteria={
        "observer_snapshot_fresh":freshness_ok,
        "engineering_research_gates_pass":(
            engineering["status"]=="RESEARCH_FOUNDATION_PASS_PRODUCTION_BLOCKED"),
        "sqlite_quick_check":disk_ok,
        "cognitive_receipt_chain_matches_snapshot":learned_consistent,
        "virtual_position_book_matches_snapshot":shadow_matches,
        "virtual_portfolio_limit":rows.get("OPEN",0)<=1,
    }
    # NO single retrospective snapshot ever certifies trading profit.
    return {
        "kind":"KATARINA_FOUNDATION_READONLY_INTEGRITY_AUDIT",
        "as_of_utc":now.isoformat(),
        "latest_snapshot_utc":snapshot_at.isoformat(),
        "snapshot_age_seconds":round(age,1),
        "status":("RESEARCH_FOUNDATION_INTEGRITY_PASS" if all(criteria.values())
                  else "RESEARCH_FOUNDATION_INTEGRITY_BLOCKED"),
        "checks":criteria,
        "errors":[k for k,v in criteria.items() if not v],
        "broker_account_monitor":snapshot.get("broker_account_monitor"),
        "foundation_engineering":engineering,
        "virtual_book_counts":rows,
        "cognitive_ledger_events":knowledge.get("events"),
        "research_only":True,
        "strategy_parameters_modified":False,
        "execution_authorized":False,
        "orders_submitted":0,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-dir",required=True,type=Path)
    p.add_argument("--max-age-seconds",type=int,default=720)
    args=p.parse_args()
    report=audit(args.state_dir,now_utc=datetime.now(timezone.utc),
                 max_age_seconds=args.max_age_seconds)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True,allow_nan=False))
    if report["status"]!="RESEARCH_FOUNDATION_INTEGRITY_PASS":
        raise SystemExit(2)


if __name__=="__main__":
    main()
