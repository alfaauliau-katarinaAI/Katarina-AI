from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING
import json

from katarina.engines.adaptive_risk import AdaptiveRiskProfile

if TYPE_CHECKING:
    from katarina.engines.manual_risk import AccountRiskAssessment

class RiskAction(str, Enum):
    APPROVE="APPROVE"; REDUCE="REDUCE"; REJECT="REJECT"; PAUSE="PAUSE"

class DrawdownMode(str,Enum):
    NORMAL="NORMAL"
    CAUTION="CAUTION"
    RECOVERY_FACTOR_ONLY="RECOVERY_FACTOR_ONLY"
    EXTREME_SURVIVAL="EXTREME_SURVIVAL"
    EMERGENCY_LOCKDOWN="EMERGENCY_LOCKDOWN"


@dataclass(frozen=True,slots=True)
class DrawdownAuthority:
    day_key: str
    mode: DrawdownMode
    drawdown_fraction: float
    owner_caused: bool
    verified: bool


class OwnerDrawdownTracker:
    """Broker-reconciled Owner vs Katarina P/L attribution; never sends orders."""
    def __init__(self):
        self.day_key=""
        self.previous_dd=0.0
        self.katarina_locked=False
        self.extreme_today=False
        self.manual_worsened_after_lock=False

    def observe(self,day_key:str,dd:float,*,hwm_cash:float,
                owner_loss_cash:float=0.,katarina_loss_cash:float=0.,
                reconciled:bool=False)->DrawdownAuthority:
        vals=(dd,hwm_cash,owner_loss_cash,katarina_loss_cash)
        if (not day_key or any(not isfinite(v) for v in vals)
                or not 0<=dd<=1 or hwm_cash<=0
                or owner_loss_cash<0 or katarina_loss_cash<0):
            raise ValueError("invalid_drawdown_attribution")
        if day_key!=self.day_key:
            carry=self.manual_worsened_after_lock if self.day_key else False
            self.day_key=day_key
            self.previous_dd=dd
            self.katarina_locked=False
            self.extreme_today=carry and reconciled
            self.manual_worsened_after_lock=False
            if self.extreme_today and dd>=.35:
                return DrawdownAuthority(day_key,DrawdownMode.EXTREME_SURVIVAL,dd,True,True)
        before=self.previous_dd
        self.previous_dd=dd
        if self.katarina_locked:
            if reconciled and owner_loss_cash>0:
                self.manual_worsened_after_lock=True
            return DrawdownAuthority(day_key,DrawdownMode.EMERGENCY_LOCKDOWN,dd,False,reconciled)
        if dd>=.35:
            if self.extreme_today:
                return DrawdownAuthority(day_key,DrawdownMode.EXTREME_SURVIVAL,dd,True,reconciled)
            need=max(0.,(.35-before)*hwm_cash)
            owner_cause=(reconciled and before<.35 and owner_loss_cash>=need-1e-8
                         and owner_loss_cash>katarina_loss_cash and owner_loss_cash>0)
            if owner_cause:
                self.extreme_today=True
                return DrawdownAuthority(day_key,DrawdownMode.EXTREME_SURVIVAL,dd,True,True)
            self.katarina_locked=True
            return DrawdownAuthority(day_key,DrawdownMode.EMERGENCY_LOCKDOWN,dd,False,reconciled)
        mode=(DrawdownMode.RECOVERY_FACTOR_ONLY if dd>=.23
              else DrawdownMode.CAUTION if dd>=.10 else DrawdownMode.NORMAL)
        return DrawdownAuthority(day_key,mode,dd,False,reconciled)

    def snapshot_state(self):
        return dict(day_key=self.day_key,previous_dd=self.previous_dd,
                    katarina_locked=self.katarina_locked,extreme_today=self.extreme_today,
                    manual_worsened_after_lock=self.manual_worsened_after_lock)

    def restore_state(self,state):
        dd=float(state["previous_dd"])
        if not isfinite(dd) or not 0<=dd<=1:
            raise ValueError("invalid_saved_drawdown")
        if bool(state["katarina_locked"]) and bool(state["extreme_today"]):
            raise ValueError("conflicting_drawdown_authority")
        self.day_key=str(state["day_key"])
        self.previous_dd=dd
        self.katarina_locked=bool(state["katarina_locked"])
        self.extreme_today=bool(state["extreme_today"])
        self.manual_worsened_after_lock=bool(state["manual_worsened_after_lock"])



@dataclass(frozen=True, slots=True)
class RiskRequest:
    requested_fraction: float | None
    open_risk_fraction: float
    drawdown_fraction: float
    uncertainty: float
    expected_rr: float
    health_ok: bool
    reconciled: bool
    daily_drawdown_fraction: float = 0.0
    unbounded_open_risk: bool = False
    # Required only when an adaptive profile is enabled; native broker units.
    risk_capital: float | None = None
    risk_reference_capital: float | None = None
    account_currency: str | None = None
    entry_kind: str = "NORMAL"
    trading_day_key: str = ""
    drawdown_authority: DrawdownAuthority | None = None

@dataclass(frozen=True, slots=True)
class RiskDecision:
    action: RiskAction
    approved_fraction: float
    reason: str

class RiskGovernor:
    def __init__(
        self,
        *,
        per_trade_default: float = 0.01,
        hard_per_trade: float = 0.05,
        max_open_risk: float = 0.08,
        max_drawdown: float = 0.35,
        max_daily_drawdown: float = 0.35,
        adaptive_profile: AdaptiveRiskProfile | None = None,
    ):
        vals=(per_trade_default,hard_per_trade,max_open_risk,max_drawdown,max_daily_drawdown)
        if any(not isfinite(v) or v<=0 for v in vals):
            raise ValueError("invalid_risk_limits")
        if (per_trade_default>.05 or hard_per_trade>.05 or
                max_open_risk>.08 or max_daily_drawdown>.35 or
                max_drawdown>.35):
            raise ValueError("cannot_expand_fixed_safety_limits")
        self.per_trade_default=per_trade_default
        self.hard_per_trade=hard_per_trade
        self.max_open_risk=max_open_risk
        self.max_drawdown=max_drawdown
        self.max_daily_drawdown=max_daily_drawdown
        self.adaptive_profile=adaptive_profile

    @classmethod
    def from_config(cls, path: str | Path) -> "RiskGovernor":
        """Opt-in creation from a verified risk config; not live authorization."""
        obj=json.loads(Path(path).read_text(encoding="utf-8"))
        options=obj.get("adaptive_risk",{})
        adaptive=None
        if options.get("enabled",False):
            tiers=options.get("tiers_usd")
            scales=options.get("money_units_per_usd")
            if not isinstance(tiers,list) or not isinstance(scales,dict):
                raise ValueError("adaptive_config_missing_tiers_or_currency")
            adaptive=AdaptiveRiskProfile(
                tiers_usd=tuple((float(x[0]),float(x[1])) for x in tiers),
                money_units_per_usd=scales,
                soft_daily_drawdown=float(options["soft_daily_drawdown"]),
                soft_total_drawdown=float(options["soft_total_drawdown"]),
                drawdown_multiplier=float(options["drawdown_multiplier"]),
            )
        return cls(
            per_trade_default=float(obj["per_trade_default_fraction"]),
            hard_per_trade=float(obj["hard_per_entry_fraction"]),
            max_open_risk=float(obj["max_open_risk_fraction"]),
            max_drawdown=float(obj["max_total_drawdown_fraction"]),
            max_daily_drawdown=float(obj["max_daily_drawdown_fraction"]),
            adaptive_profile=adaptive,
        )

    def evaluate(self, r: RiskRequest) -> RiskDecision:
        if not r.health_ok or not r.reconciled:
            return RiskDecision(RiskAction.PAUSE,0.0,"health_or_reconciliation")
        if r.unbounded_open_risk:
            return RiskDecision(RiskAction.PAUSE,0.0,"unbounded_open_risk")
        values=(r.open_risk_fraction,r.drawdown_fraction,r.daily_drawdown_fraction,
                r.uncertainty,r.expected_rr)
        # Reject malformed broker evidence rather than throwing an exception
        # or letting an impossible fraction slip through the risk gate.
        if any(type(v) not in (int,float) or not isfinite(v) for v in values):
            return RiskDecision(RiskAction.PAUSE,0.0,"invalid_risk_evidence")
        if (not 0<=r.open_risk_fraction<=1 or
                not 0<=r.drawdown_fraction<=1 or
                not 0<=r.daily_drawdown_fraction<=1 or
                not 0<=r.uncertainty<=1):
            return RiskDecision(RiskAction.PAUSE,0.0,"invalid_risk_evidence")
        if r.entry_kind not in {"NORMAL","RECOVERY_FACTOR","EXTREME_RECOVERY"}:
            return RiskDecision(RiskAction.REJECT,0.0,"invalid_entry_kind")
        a=r.drawdown_authority
        # A Katarina-caused emergency is latched for the full broker day.
        # Improvements to DD or a stale/unverified attribution receipt may
        # not silently re-authorize NEW trades while lockdown is in force.
        # The OwnerDrawdownTracker explicitly issues a fresh authority on
        # the next trading day; that is evaluation, never automatic entry.
        # Both emergency and Owner-origin extreme observations must latch
        # the no-new-entry policy even if a RiskRequest carries stale DD.
        # Existing-position management is assessed separately.
        if (isinstance(a,DrawdownAuthority)
                and a.mode in (DrawdownMode.EMERGENCY_LOCKDOWN,
                               DrawdownMode.EXTREME_SURVIVAL)):
            return RiskDecision(RiskAction.PAUSE,0.0,"emergency_drawdown_lock")
        # Owner's latest policy: 35% stops ALL new exposure, regardless of
        # whether losses were caused by manual trades or Katarina.
        # This is the new-entry governor; existing position management
        # remains a separate risk-reducing pathway.
        if (r.daily_drawdown_fraction>=self.max_daily_drawdown
                or r.drawdown_fraction>=self.max_drawdown):
            return RiskDecision(RiskAction.PAUSE,0.0,"emergency_drawdown_lock")
        if .23<=r.drawdown_fraction<.35 and r.entry_kind!="RECOVERY_FACTOR":
            return RiskDecision(RiskAction.REJECT,0.0,"recovery_factor_entry_only")
        # Never unlock NEW entries through an owner-origin drawdown exception.
        if r.entry_kind=="EXTREME_RECOVERY":
            return RiskDecision(RiskAction.PAUSE,0.0,"owner_daily_stop_no_extreme_entry")
        if r.entry_kind=="RECOVERY_FACTOR" and r.drawdown_fraction<.23:
            return RiskDecision(RiskAction.REJECT,0.0,"recovery_factor_not_active")
        if r.expected_rr <= 0 or r.uncertainty >= 0.75:
            return RiskDecision(RiskAction.REJECT,0.0,"insufficient_edge")

        remaining=max(0.0,self.max_open_risk-r.open_risk_fraction)
        cap=min(self.hard_per_trade,remaining)
        cap_without_adaptive=cap
        adaptive=None
        if self.adaptive_profile is not None:
            try:
                adaptive=self.adaptive_profile.quote(
                    active_capital_native=r.risk_capital,
                    reference_capital_native=r.risk_reference_capital,
                    account_currency=r.account_currency,
                    daily_drawdown=r.daily_drawdown_fraction,
                    total_drawdown=r.drawdown_fraction,
                )
            except (TypeError,ValueError,OverflowError):
                return RiskDecision(RiskAction.PAUSE,0.0,"adaptive_capital_unverified")
            cap=min(cap,adaptive.fraction)
        requested=self.per_trade_default if r.requested_fraction is None else r.requested_fraction
        if adaptive is not None and r.requested_fraction is None:
            requested=adaptive.fraction
        if not isfinite(requested) or requested<0:
            return RiskDecision(RiskAction.REJECT,0.0,"invalid_requested_risk")
        if .10<=r.drawdown_fraction<.23:
            cap=min(cap,self.hard_per_trade*.5)
        approved=min(requested,cap)
        if approved<=0:
            return RiskDecision(RiskAction.REJECT,0.0,"risk_capacity_exhausted")
        if approved<requested-1e-12:
            reason=("adaptive_capital_risk_cap"
                    if adaptive is not None and adaptive.fraction<cap_without_adaptive-1e-12
                    else "hard_risk_cap")
            return RiskDecision(RiskAction.REDUCE,approved,reason)
        return RiskDecision(RiskAction.APPROVE,approved,
            adaptive.reason if adaptive is not None else "within_limits")

    def evaluate_state(
        self,
        state,
        *,
        requested_fraction: float | None,
        uncertainty: float,
        expected_rr: float,
        health_ok: bool,
        reconciled: bool,
        account_currency: str | None = None,
        risk_reference_capital: float | None = None,
        entry_kind: str = "NORMAL",
        trading_day_key: str = "",
        drawdown_authority: DrawdownAuthority | None = None,
    ) -> RiskDecision:
        """Evaluate a full account snapshot; includes pending/reserved/manual risk."""
        return self.evaluate(RiskRequest(
            requested_fraction=requested_fraction,
            open_risk_fraction=state.total_committed_risk_fraction,
            drawdown_fraction=state.total_drawdown_fraction,
            uncertainty=uncertainty,
            expected_rr=expected_rr,
            health_ok=health_ok,
            reconciled=reconciled,
            daily_drawdown_fraction=state.daily_drawdown_fraction,
            unbounded_open_risk=state.has_unbounded_risk,
            risk_capital=state.risk_capital,
            risk_reference_capital=risk_reference_capital,
            account_currency=account_currency,
            entry_kind=entry_kind,
            trading_day_key=trading_day_key,
            drawdown_authority=drawdown_authority,
        ))

    def evaluate_account(
        self,
        account_risk: "AccountRiskAssessment",
        *,
        requested_fraction: float | None,
        drawdown_fraction: float,
        daily_drawdown_fraction: float,
        uncertainty: float,
        expected_rr: float,
        health_ok: bool,
        reconciled: bool,
        risk_capital: float | None = None,
        risk_reference_capital: float | None = None,
        account_currency: str | None = None,
        entry_kind: str = "NORMAL",
        trading_day_key: str = "",
        drawdown_authority: DrawdownAuthority | None = None,
    ) -> RiskDecision:
        """Shared-account path; adaptive mode requires verified capital & currency."""
        return self.evaluate(RiskRequest(
            requested_fraction=requested_fraction,
            open_risk_fraction=account_risk.open_risk_fraction,
            drawdown_fraction=drawdown_fraction,
            uncertainty=uncertainty,
            expected_rr=expected_rr,
            health_ok=health_ok,
            reconciled=reconciled,
            daily_drawdown_fraction=daily_drawdown_fraction,
            unbounded_open_risk=account_risk.has_unbounded_risk,
            risk_capital=risk_capital,
            risk_reference_capital=risk_reference_capital,
            account_currency=account_currency,
            entry_kind=entry_kind,
            trading_day_key=trading_day_key,
            drawdown_authority=drawdown_authority,
        ))
