from __future__ import annotations
import importlib
import json
from pathlib import Path

ROOT=Path.cwd()
MODULES={
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
loaded={}
for stage,name in MODULES.items():
    importlib.import_module(name)
    loaded[stage]=name

from katarina.engines.risk import RiskGovernor
from katarina.governance.live_validation import LiveMicroRiskValidator
from katarina.governance.evolution import ContinuousEvolutionController

checks={
    "all_stage_modules_import": len(loaded)==30,
    "risk_hard_cap_lte_5pct": RiskGovernor().hard_per_trade <= .05,
    "daily_drawdown_cap_lte_10pct": RiskGovernor().max_daily_drawdown <= .10,
    "live_risk_cap_matches_5pct": LiveMicroRiskValidator.HARD_RISK_CAP == .05,
    "autonomous_live_promotion_disabled": not ContinuousEvolutionController().autonomous_live_promotion_allowed(),
    "constitution_present": (ROOT/"KATARINA_CONSTITUTION.md").is_file(),
    "stage_manifest_present": (ROOT/"docs/stages/STAGE_01_40_MANIFEST.json").is_file(),
}
passed=all(checks.values())
print(json.dumps({
 "schema_version":1,
 "proof_type":"KATARINA_STAGE11_40_IMPLEMENTATION_AUDIT",
 "checks":checks,
 "implemented_stage_modules":len(loaded),
 "live_risk_ready":False,
 "result":"PASS_STAGE11_40_IMPLEMENTATION_BASELINE" if passed else "FAIL_STAGE11_40_IMPLEMENTATION_BASELINE"
},sort_keys=True))
raise SystemExit(0 if passed else 1)
