"""WP8b: deterministic, read-only comparison of registered development reports.

Only reports from validate_strategy.py development are accepted. Not an
optimizer or ranking service; comparing variants does not unlock holdout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from katarina.research.validation import ValidationError, canonical, sha256_text


def compare_reports(reports):
    if not reports:
        raise ValidationError("comparison_requires_reports")
    rows, sources, seen = [], [], set()
    for report in reports:
        if not isinstance(report, dict) or report.get("tool") != "katarina.research.validation" or report.get("period") != "DEVELOPMENT":
            raise ValidationError("comparison_requires_development_only")
        digest = report.get("report_sha256")
        body = {k: v for k, v in report.items() if k != "report_sha256"}
        if not isinstance(digest, str) or sha256_text(canonical(body)) != digest:
            raise ValidationError("comparison_report_hash_mismatch")
        hid, spec = report.get("hypothesis_id"), report.get("hypothesis")
        if hid in seen or not isinstance(spec, dict) or spec.get("side") not in ("BUY", "SELL"):
            raise ValidationError("comparison_duplicate_or_invalid_hypothesis")
        if not isinstance(report.get("statistics"), dict) or not isinstance(report.get("baselines"), dict):
            raise ValidationError("comparison_missing_metrics")
        if report.get("live_execution_authorized") is not False or report.get("trial_count", 0) < 1:
            raise ValidationError("comparison_permission_or_trial_invalid")
        seen.add(hid)
        stats = report["statistics"]
        baselines = report["baselines"]
        rows.append({
            "symbol": spec["symbol"], "side": spec["side"], "setup": spec["playbook"],
            "regime": spec["regime"], "hypothesis_id": hid,
            "trials": report["trial_count"], "trades": stats["trades"],
            "net_expectancy_r": stats["expectancy_r"],
            "profit_factor": stats["profit_factor"],
            "win_rate": stats["win_rate"],
            "mean_cost_r": stats["mean_cost_r"],
            "bootstrap_lower_expectancy_r": report["weekly_block_bootstrap_lower_expectancy_r"],
            "cost_sensitivity": report["cost_sensitivity"],
            "no_trade_baseline_r": 0.0,
            "random_side_baseline_r": baselines["random_side_same_timing"]["expected_expectancy_r"],
            "trend_baseline_r": baselines["trend_rule"]["expectancy_r"],
            "verdict": report["verdict"],
            "report_sha256": digest,
        })
        sources.append(digest)
    rows.sort(key=lambda row: (row["symbol"], row["side"], row["setup"], row["regime"], row["hypothesis_id"]))
    result = {"schema_version": 1, "stage": "DEVELOPMENT_RESEARCH_ONLY",
              "label": "RISET — data pengembangan, bukan kelulusan",
              "source_reports_sha256": sorted(sources),
              "rows": rows, "live_execution_authorized": False}
    result["report_sha256"] = sha256_text(canonical(result))
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reports", nargs="+", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    output = Path(args.out)
    if output.exists() or output.is_symlink():
        raise ValidationError("comparison_output_already_exists")
    reports = [json.loads(Path(x).read_text(encoding="utf-8")) for x in args.reports]
    report = compare_reports(reports)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["stage"], "rows": len(report["rows"]),
                      "sha256": report["report_sha256"], "live_execution_authorized": False},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
