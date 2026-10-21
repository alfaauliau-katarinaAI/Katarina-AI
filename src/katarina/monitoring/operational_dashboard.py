from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ManagedPositionDashboard:
    position_id: str
    side: str
    current_r: float
    peak_r: float
    target_rr: float
    partial_done: bool
    current_volume: float
    stop: float


@dataclass(frozen=True, slots=True)
class OperationalDashboardSnapshot:
    lifecycle: str
    health: str
    execution_armed: bool
    equity: float
    daily_drawdown: float
    total_drawdown: float
    position_risk: float
    manual_position_risk: float
    pending_risk: float
    manual_pending_risk: float
    reserved_risk: float
    total_committed_risk: float
    remaining_risk_capacity: float
    unbounded_risk: bool
    regime: str
    active_strategy: str
    decision: str
    news_ready: bool
    news_blackout: bool
    profit_factor: float
    recovery_factor: float
    win_rate: float
    positions: tuple[ManagedPositionDashboard,...]
    data: Mapping[str,Any]
    total_balance: float = 0.0
    reserve_balance: float = 0.0
    active_trading_balance: float = 0.0
    next_compounding_target: float = 0.0
    compounding_milestones: int = 0


class OperationalDashboard:
    def render_json(self,snapshot:OperationalDashboardSnapshot)->str:
        return json.dumps(asdict(snapshot),sort_keys=True,separators=(",",":"))
