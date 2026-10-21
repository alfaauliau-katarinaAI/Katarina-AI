from __future__ import annotations

import importlib
import json
from pathlib import Path

from katarina.body import BodyRegistry, STAGE_MODULES
from katarina.body.functional import ExecutionIntent, TesterEvaluationIntent


def component(stage: int):
    return importlib.import_module(STAGE_MODULES[stage]).Component()


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    specs = BodyRegistry(root).validate()

    specialist = component(14).analyze({"instrument": "XAUUSD"})
    decision = component(15).decide(specialist)
    risk = component(16).authorize(decision)
    sizing = component(17).size(risk)
    execution = component(18).stage_intent(
        ExecutionIntent("cross-stage-audit", 1, "BUY", 1)
    )
    tester_evidence = component(25).record(
        TesterEvaluationIntent("cross-stage-tester", execution)
    )
    micro = component(38).validate(
        {"tester_evidence": tester_evidence}
    )

    policy_pending = {
        spec.stage for spec in specs if spec.policy_pending
    }
    windows_pending = {
        spec.stage for spec in specs if spec.windows_required
    }

    checks = {
        "stage_count_30": len(specs) == 30,
        "policy_pending_exact": policy_pending == {14, 15, 16, 17, 38},
        "windows_pending_exact": windows_pending == {35, 36, 38},
        "specialist_no_signal": specialist["signal"] == "NO_SIGNAL",
        "decision_no_trade": decision["decision"] == "NO_TRADE",
        "risk_denied": risk["approved"] is False,
        "risk_not_ready": risk["live_risk_ready"] is False,
        "size_zero": sizing["quantity_units"] == 0,
        "execution_not_live": execution["accepted_for_live_execution"] is False,
        "tester_only": tester_evidence["tester_only"] is True,
        "tester_no_broker_mutation": tester_evidence["broker_mutation"] is False,
        "micro_risk_denied": micro["approved"] is False,
        "micro_live_risk_false": micro["live_risk_ready"] is False,
        "micro_execution_authority_false":
            micro["live_execution_authority"] is False,
        "all_specs_live_risk_false":
            all(not spec.live_risk_ready for spec in specs),
        "all_specs_live_execution_false":
            all(not spec.live_execution_authority for spec in specs),
    }

    passed = all(checks.values())
    report = {
        "schema_version": 1,
        "proof_type": "KATARINA_CROSS_STAGE_FAIL_CLOSED_AUDIT",
        "stage_range": [11, 40],
        "checks": checks,
        "policy_pending": sorted(policy_pending),
        "windows_pending": sorted(windows_pending),
        "strategy_policy_finalized": False,
        "risk_policy_finalized": False,
        "live_risk_ready": False,
        "live_execution_enabled": False,
        "result": (
            "PASS_KATARINA_CROSS_STAGE_FAIL_CLOSED"
            if passed
            else "FAIL_KATARINA_CROSS_STAGE_FAIL_CLOSED"
        ),
    }

    output = root / "build" / "body" / "cross_stage_fail_closed.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(report["result"])
    print(f"output={output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
