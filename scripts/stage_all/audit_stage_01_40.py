from __future__ import annotations

import importlib
import json
from pathlib import Path

ROOT = Path.cwd()

REQUIRED = {
    1: ["KATARINA_CONSTITUTION.md"],
    2: ["docs/KATARINA_FINAL_WORKFLOW.md"],
    3: ["docs/architecture/REPOSITORY_ARCHITECTURE.md"],
    4: ["protocol/message_registry_v1.json", "protocol/kat1_message_schemas_v1.json"],
    5: ["src/katarina/core/orchestrator.py"],
    6: ["mt5/Experts/KatarinaBridgeEA.mq5"],
    7: ["protocol/kat1_message_schemas_v1.json"],
    8: ["src/katarina/validation/engine.py"],
    9: ["src/katarina/health/engine.py"],
    10: ["src/katarina/memory/store.py"],
}
MODULES = {
    11:"katarina.intelligence.perception.market",
    12:"katarina.intelligence.perception.timeframe",
    13:"katarina.intelligence.perception.regime",
    14:"katarina.intelligence.perception.xauusd",
    15:"katarina.engines.decision",
    16:"katarina.engines.risk",
    17:"katarina.engines.sizing",
    18:"katarina.engines.execution",
    19:"katarina.engines.position",
    20:"katarina.engines.evaluation",
    21:"katarina.research.research",
    22:"katarina.research.backtest",
    23:"katarina.research.walkforward",
    24:"katarina.research.robustness",
    25:"katarina.research.shadow",
    26:"katarina.intelligence.perception.learning",
    27:"katarina.intelligence.perception.simple_ml",
    28:"katarina.governance.models",
    29:"katarina.intelligence.perception.economics",
    30:"katarina.engines.portfolio",
    31:"katarina.engines.exposure",
    32:"katarina.monitoring.dashboard",
    33:"katarina.governance.ci",
    34:"katarina.governance.constitution",
    35:"katarina.adapters.tester",
    36:"katarina.adapters.paper",
    37:"katarina.engines.stress",
    38:"katarina.governance.live_validation",
    39:"katarina.monitoring.performance",
    40:"katarina.governance.evolution",
}

manifest_path = ROOT / "docs/stages/STAGE_01_40_MANIFEST.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
checks = {
    "stage_count_40": manifest.get("stage_count") == 40,
    "records_40": len(manifest.get("records", [])) == 40,
    "frozen_through_9": manifest.get("frozen_through") == 9,
    "baseline_through_40": manifest.get("implementation_baseline_through") == 40,
    "live_risk_disabled": manifest.get("live_risk_ready") is False,
}
missing = {}
for stage, paths in REQUIRED.items():
    absent = [p for p in paths if not (ROOT / p).exists()]
    if absent:
        missing[stage] = absent

imports = {}
for stage, module in MODULES.items():
    importlib.import_module(module)
    imports[stage] = module

checks["stage01_10_required_files"] = not missing
checks["stage11_40_modules_import"] = len(imports) == 30
passed = all(checks.values())

print(json.dumps({
    "schema_version": 2,
    "proof_type": "KATARINA_STAGE01_40_IMPLEMENTATION_AUDIT",
    "checks": checks,
    "missing": missing,
    "implemented_module_count": len(imports),
    "live_risk_ready": False,
    "result": "PASS_STAGE01_40_IMPLEMENTATION_BASELINE" if passed else "FAIL_STAGE01_40_IMPLEMENTATION_BASELINE",
}, sort_keys=True))
raise SystemExit(0 if passed else 1)
