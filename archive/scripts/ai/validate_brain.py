"""Validate an external, timestamped trade-outcome JSONL file offline.

Use genuine, completed net-of-cost labels only. This command cannot place trades.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from katarina.intelligence.brain import KatarinaAIBrain, LabeledMarketExample


def load_rows(path: Path) -> list[LabeledMarketExample]:
    rows: list[LabeledMarketExample] = []
    with path.open(encoding="utf-8") as source:
        for lineno, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
                    raise ValueError("features must be a JSON array")
                # No permissive coercion of timestamps, labels or features.
                rows.append(LabeledMarketExample(
                    sample_id=payload["sample_id"],
                    observed_ns=payload["observed_ns"],
                    label_known_ns=payload["label_known_ns"],
                    features=tuple(payload["features"]),
                    profitable_after_costs=payload["profitable_after_costs"],
                ))
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise ValueError(f"invalid record at line {lineno}: {exc}") from exc
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KATARINA offline AI Brain research validation")
    parser.add_argument("--input", type=Path, required=True, help="Private JSONL of completed, cost-aware trade outcomes")
    parser.add_argument("--features", required=True, help="Comma-separated names in fixed feature order")
    parser.add_argument("--output", type=Path, default=Path("build/ai/validation.json"))
    args = parser.parse_args(argv)
    feature_names = tuple(s.strip() for s in args.features.split(","))
    if not args.input.is_file():
        parser.error("input file does not exist")
    try:
        rows = load_rows(args.input)
        result = KatarinaAIBrain().train_candidate(rows, feature_names=feature_names)
    except ValueError as exc:
        parser.error(str(exc))

    evidence = {
        "schema_version": 1,
        "result": "PASS_AI_BRAIN_RESEARCH_CANDIDATE" if result.valid else "NO_VALIDATED_AI_BRAIN_CANDIDATE",
        "data_provenance_verified": False,
        "research_only": True,
        "live_risk_ready": False,
        "live_execution_enabled": False,
        "validated": result.valid,
        "reasons": list(result.reasons),
        "feature_names": list(result.feature_names),
        "train_count": result.train_count,
        "test_count": result.test_count,
        "cutoff_ns": result.cutoff_ns,
        "trained_until_ns": result.trained_until_ns,
        "baseline_brier": result.baseline_brier,
        "model_brier": result.model_brier,
        "model_hash": result.model_hash,
        "model": None if result.model is None else {
            "version": result.model.version,
            "weights": list(result.model.weights),
            "bias": result.model.bias,
            "training_bounds": [list(x) for x in result.training_bounds],
            "research_only": True,
            "live_execution_enabled": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(evidence["result"])
    print("evidence=" + str(args.output))
    print("NOTE: holdout test only; performance is not independently broker verified")
    return 0 if result.valid else 2


if __name__ == "__main__":
    sys.exit(main())
