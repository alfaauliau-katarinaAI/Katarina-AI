from katarina.body.component import PassiveStageComponent
from katarina.body.contracts import (
    AuthorityClass,
    BodyStatus,
    PolicyState,
    StageResult,
    StageSpec,
)
from katarina.body.registry import BodyRegistry, BodyRegistryError
from katarina.body.runtime import BodyRuntimeSnapshot, KatarinaBodyRuntime

# Stage number -> implementation module. config/stages/stageNN.json keeps the number as
# its file name; the old katarina.body.stageNN modules are deprecated aliases.
STAGE_MODULES = {
    11: "katarina.body.market_intelligence",
    12: "katarina.body.multi_timeframe",
    13: "katarina.body.market_regime",
    14: "katarina.body.xauusd_specialist",
    15: "katarina.body.decision",
    16: "katarina.body.risk_governor",
    17: "katarina.body.position_sizing",
    18: "katarina.body.execution",
    19: "katarina.body.position_manager",
    20: "katarina.body.trade_evaluation",
    21: "katarina.body.research",
    22: "katarina.body.backtesting",
    23: "katarina.body.walk_forward",
    24: "katarina.body.robustness",
    25: "katarina.body.tester_evaluation",
    26: "katarina.body.learning",
    27: "katarina.body.machine_learning",
    28: "katarina.body.model_promotion",
    29: "katarina.body.economic_intelligence",
    30: "katarina.body.portfolio",
    31: "katarina.body.exposure",
    32: "katarina.body.dashboard",
    33: "katarina.body.automated_testing",
    34: "katarina.body.constitution_guard",
    35: "katarina.body.strategy_tester",
    36: "katarina.body.live_preflight",
    37: "katarina.body.stress_test",
    38: "katarina.body.live_micro_risk",
    39: "katarina.body.performance_monitoring",
    40: "katarina.body.continuous_evolution",
}

__all__ = (
    "AuthorityClass",
    "BodyRegistry",
    "BodyRegistryError",
    "BodyRuntimeSnapshot",
    "BodyStatus",
    "KatarinaBodyRuntime",
    "PassiveStageComponent",
    "PolicyState",
    "StageResult",
    "StageSpec",
    "STAGE_MODULES",
)
