from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any, Mapping

from katarina.engines.manual_risk import (
    AccountRiskAssessment,
    PositionOrigin,
    SymbolRiskSpec,
)

def authenticated_broker_day_key(
    source_time_ns: int | None,
    utc_offset_minutes: int | None,
    *,
    broker_clock_authenticated: bool = False,
) -> str | None:
    """Never guess broker trading day from UTC or the VPS local timezone.

    KAT1 source timestamps alone do not establish the broker UTC offset.
    A separate trustworthy broker-clock observation must supply the offset.
    """
    if not broker_clock_authenticated:
        return None
    if (type(source_time_ns) is not int or source_time_ns <= 0
            or type(utc_offset_minutes) is not int
            or not -720 <= utc_offset_minutes <= 840):
        return None
    try:
        source=datetime.fromtimestamp(source_time_ns/1_000_000_000,tz=timezone.utc)
        return (source+timedelta(minutes=utc_offset_minutes)).date().isoformat()
    except (ValueError,OverflowError,OSError):
        return None


@dataclass(frozen=True, slots=True)
class BrokerSessionEvidence:
    source_time_ns: int
    utc_offset_minutes: int
    broker_clock_authenticated: bool = False

    @property
    def day_key(self) -> str | None:
        return authenticated_broker_day_key(
            self.source_time_ns,self.utc_offset_minutes,
            broker_clock_authenticated=self.broker_clock_authenticated,
        )


@dataclass(frozen=True, slots=True)
class PendingOrderRiskInput:
    order_id: str
    origin: str
    side: str
    volume: float
    entry_price: float
    stop_loss: float | None
    symbol_spec: SymbolRiskSpec | None
    broker_loss_to_sl: float | None = None


@dataclass(frozen=True, slots=True)
class PendingOrderRisk:
    order_id: str
    origin: str
    risk_cash: float
    bounded: bool
    reason: str


@dataclass(frozen=True, slots=True)
class DailyDrawdownSnapshot:
    day_key: str
    starting_equity: float
    net_external_cash_flow: float
    adjusted_baseline: float
    current_equity: float
    current_drawdown_fraction: float
    max_drawdown_fraction: float
    halted: bool


class DailyDrawdownTracker:
    def __init__(self, *, limit: float = 0.35):
        if not (0 < limit < 1):
            raise ValueError("daily drawdown limit")
        self.limit=limit
        self.day_key=""
        self.starting_equity=0.0
        self.net_external_cash_flow=0.0
        self.current_equity=0.0
        self.max_drawdown_fraction=0.0

    def start_day(self, day_key: str, equity: float) -> None:
        if not day_key or not isfinite(equity) or equity <= 0:
            raise ValueError("invalid daily baseline")
        self.day_key=str(day_key)
        self.starting_equity=float(equity)
        self.net_external_cash_flow=0.0
        self.current_equity=float(equity)
        self.max_drawdown_fraction=0.0

    def _ensure_day(self, day_key: str, equity: float) -> None:
        if self.day_key != day_key:
            self.start_day(day_key,equity)

    def apply_cash_flow(self, day_key: str, amount: float, *, equity_after: float) -> None:
        self._ensure_day(day_key,equity_after-amount if equity_after-amount > 0 else equity_after)
        if not isfinite(amount) or not isfinite(equity_after) or equity_after <= 0:
            raise ValueError("invalid cash flow")
        self.net_external_cash_flow += float(amount)
        self.observe(day_key,equity_after)

    def observe(self, day_key: str, equity: float) -> DailyDrawdownSnapshot:
        if not isfinite(equity) or equity <= 0:
            raise ValueError("invalid equity")
        self._ensure_day(day_key,equity)
        self.current_equity=float(equity)
        adjusted=max(1e-12,self.starting_equity+self.net_external_cash_flow)
        current=max(0.0,(adjusted-self.current_equity)/adjusted)
        self.max_drawdown_fraction=max(self.max_drawdown_fraction,current)
        return self.snapshot()

    def snapshot(self) -> DailyDrawdownSnapshot:
        adjusted=max(0.0,self.starting_equity+self.net_external_cash_flow)
        current=0.0 if adjusted <= 0 else max(0.0,(adjusted-self.current_equity)/adjusted)
        return DailyDrawdownSnapshot(
            self.day_key,self.starting_equity,self.net_external_cash_flow,adjusted,
            self.current_equity,current,self.max_drawdown_fraction,
            self.max_drawdown_fraction >= self.limit,
        )

    def snapshot_state(self) -> dict[str,Any]:
        return {
            "limit":self.limit,"day_key":self.day_key,
            "starting_equity":self.starting_equity,
            "net_external_cash_flow":self.net_external_cash_flow,
            "current_equity":self.current_equity,
            "max_drawdown_fraction":self.max_drawdown_fraction,
        }

    def restore_state(self, state: Mapping[str,Any]) -> None:
        if not state:
            return
        limit=float(state["limit"])
        if abs(limit-self.limit)>1e-12:
            raise ValueError("daily limit mismatch")
        self.day_key=str(state["day_key"])
        self.starting_equity=float(state["starting_equity"])
        self.net_external_cash_flow=float(state["net_external_cash_flow"])
        self.current_equity=float(state["current_equity"])
        self.max_drawdown_fraction=float(state["max_drawdown_fraction"])


class TotalDrawdownTracker:
    def __init__(self, *, limit: float = 0.35):
        self.limit=limit
        self.peak_equity=0.0
        self.current_equity=0.0
        self.max_drawdown_fraction=0.0

    def observe(self, equity: float) -> float:
        if not isfinite(equity) or equity <= 0:
            raise ValueError("invalid equity")
        self.current_equity=float(equity)
        self.peak_equity=max(self.peak_equity,self.current_equity)
        dd=0.0 if self.peak_equity <= 0 else max(0.0,(self.peak_equity-self.current_equity)/self.peak_equity)
        self.max_drawdown_fraction=max(self.max_drawdown_fraction,dd)
        return self.max_drawdown_fraction

    @property
    def current_drawdown_fraction(self)->float:
        if self.peak_equity<=0:
            return 0.0
        return max(0.0,(self.peak_equity-self.current_equity)/self.peak_equity)

    def apply_cash_flow(self, amount: float, *, equity_after: float) -> float:
        if not isfinite(amount):
            raise ValueError("invalid cash flow")
        if self.peak_equity > 0:
            self.peak_equity=max(1e-12,self.peak_equity+amount)
        return self.observe(equity_after)

    def snapshot_state(self) -> dict[str,float]:
        return {"limit":self.limit,"peak_equity":self.peak_equity,"current_equity":self.current_equity,"max_drawdown_fraction":self.max_drawdown_fraction}

    def restore_state(self,state:Mapping[str,Any])->None:
        if not state:return
        if abs(float(state["limit"])-self.limit)>1e-12: raise ValueError("total limit mismatch")
        self.peak_equity=float(state["peak_equity"]); self.current_equity=float(state["current_equity"]); self.max_drawdown_fraction=float(state["max_drawdown_fraction"])


class RiskReservationBook:
    def __init__(self):
        self._items: dict[str,float]={}

    def reserve(self,reservation_id:str,risk_fraction:float)->bool:
        if not reservation_id or not isfinite(risk_fraction) or risk_fraction <= 0:
            raise ValueError("invalid reservation")
        prior=self._items.get(reservation_id)
        if prior is not None:
            if abs(prior-risk_fraction)>1e-12: raise RuntimeError("risk_reservation_conflict")
            return False
        self._items[reservation_id]=float(risk_fraction)
        return True

    def release(self,reservation_id:str)->bool:
        return self._items.pop(reservation_id,None) is not None

    @property
    def total_fraction(self)->float:
        return sum(self._items.values())

    def snapshot_state(self)->dict[str,float]:
        return dict(self._items)

    def restore_state(self,state:Mapping[str,Any])->None:
        restored={}
        for k,v in state.items():
            x=float(v)
            if not k or not isfinite(x) or x<=0: raise ValueError("invalid reservation state")
            restored[str(k)]=x
        self._items=restored


@dataclass(frozen=True, slots=True)
class AccountRiskStateSnapshot:
    equity: float
    risk_capital: float
    position_risk_fraction: float
    external_position_risk_fraction: float
    pending_risk_fraction: float
    external_pending_risk_fraction: float
    reserved_risk_fraction: float
    total_committed_risk_fraction: float
    remaining_capacity_fraction: float
    daily_drawdown_fraction: float
    total_drawdown_fraction: float
    daily_halted: bool
    unbounded_exposure_ids: tuple[str,...]

    @property
    def has_unbounded_risk(self)->bool:
        return bool(self.unbounded_exposure_ids)


class AccountRiskStateEngine:
    EXTERNAL_ORIGINS={
        PositionOrigin.MANUAL_DESKTOP.value,PositionOrigin.MANUAL_MOBILE.value,
        PositionOrigin.MANUAL_WEB.value,PositionOrigin.FOREIGN_EA.value,
        PositionOrigin.UNKNOWN.value,
    }

    def __init__(self,*,max_open_risk:float=.08,daily_limit:float=.35,total_limit:float=.35):
        self.max_open_risk=max_open_risk
        self.pending: dict[str,PendingOrderRiskInput]={}
        self.reservations=RiskReservationBook()
        self.daily=DailyDrawdownTracker(limit=daily_limit)
        self.total=TotalDrawdownTracker(limit=total_limit)

    @staticmethod
    def _pending_risk(p:PendingOrderRiskInput)->PendingOrderRisk:
        # Unverified inputs must never turn an outstanding order into a
        # zero-risk commitment or crash account-wide risk assessment.
        def positive_number(value:Any)->bool:
            if type(value) not in (int,float):
                return False
            try:
                return isfinite(value) and value>0
            except (OverflowError,TypeError,ValueError):
                return False

        origin=str(p.origin or "UNKNOWN").upper()
        side=str(p.side or "").upper()
        if not positive_number(p.volume) or not positive_number(p.entry_price):
            return PendingOrderRisk(p.order_id,origin,0.0,False,"invalid_pending_values")
        if side not in {"BUY","SELL"}:
            return PendingOrderRisk(p.order_id,origin,0.0,False,"invalid_pending_side")
        if not positive_number(p.stop_loss):
            return PendingOrderRisk(p.order_id,origin,0.0,False,"missing_stop_loss")
        if side=="BUY" and p.stop_loss>=p.entry_price:
            return PendingOrderRisk(p.order_id,origin,0.0,False,"invalid_buy_stop_geometry")
        if side=="SELL" and p.stop_loss<=p.entry_price:
            return PendingOrderRisk(p.order_id,origin,0.0,False,"invalid_sell_stop_geometry")
        if p.broker_loss_to_sl is not None:
            if not positive_number(p.broker_loss_to_sl):
                return PendingOrderRisk(p.order_id,origin,0.0,False,"invalid_broker_loss")
            return PendingOrderRisk(
                p.order_id,origin,float(p.broker_loss_to_sl),True,"broker_ordercalcprofit"
            )
        spec=p.symbol_spec
        if (not isinstance(spec,SymbolRiskSpec)
                or not positive_number(spec.tick_size)
                or not positive_number(spec.tick_value_loss)):
            return PendingOrderRisk(p.order_id,origin,0.0,False,"missing_symbol_spec")
        cash=abs(p.entry_price-p.stop_loss)/spec.tick_size*spec.tick_value_loss*p.volume
        if not positive_number(cash):
            return PendingOrderRisk(p.order_id,origin,0.0,False,"invalid_calculated_loss")
        return PendingOrderRisk(p.order_id,origin,cash,True,"symbol_spec_fallback")

    def upsert_pending(self,p:PendingOrderRiskInput)->None:
        if not p.order_id: raise ValueError("order_id")
        self.pending[p.order_id]=p

    def remove_pending(self,order_id:str)->None:
        self.pending.pop(order_id,None)

    def bind_pending(self,p:PendingOrderRiskInput,*,reservation_id:str|None=None)->None:
        self.upsert_pending(p)
        if reservation_id:self.reservations.release(reservation_id)

    def observe_equity(self,day_key:str,equity:float)->None:
        self.daily.observe(day_key,equity)
        self.total.observe(equity)

    def apply_cash_flow(self,day_key:str,amount:float,*,equity_after:float)->None:
        self.daily.apply_cash_flow(day_key,amount,equity_after=equity_after)
        self.total.apply_cash_flow(amount,equity_after=equity_after)

    def assess(
        self,
        positions:AccountRiskAssessment,
        *,
        equity:float|None=None,
        risk_capital:float|None=None,
    )->AccountRiskStateSnapshot:
        eq=float(positions.equity if equity is None else equity)
        capital=eq if risk_capital is None else float(risk_capital)
        pending_risks=tuple(self._pending_risk(p) for p in self.pending.values())
        pending_cash=sum(x.risk_cash for x in pending_risks if x.bounded)
        external_pending_cash=sum(x.risk_cash for x in pending_risks if x.bounded and x.origin in self.EXTERNAL_ORIGINS)
        unbounded=list(positions.unbounded_position_ids)
        unbounded.extend("order:"+x.order_id for x in pending_risks if not x.bounded)
        if capital<=0 or not isfinite(capital):
            position_fraction=external_position_fraction=1.0
            pending_fraction=external_pending_fraction=1.0
            unbounded.append("RISK_CAPITAL_UNAVAILABLE")
        else:
            position_fraction=positions.open_risk_cash/capital
            external_position_fraction=positions.external_risk_cash/capital
            pending_fraction=pending_cash/capital
            external_pending_fraction=external_pending_cash/capital
        reserved=self.reservations.total_fraction
        committed=position_fraction+pending_fraction+reserved
        daily=self.daily.snapshot()
        return AccountRiskStateSnapshot(
            equity=eq,
            risk_capital=capital,
            position_risk_fraction=position_fraction,
            external_position_risk_fraction=external_position_fraction,
            pending_risk_fraction=pending_fraction,
            external_pending_risk_fraction=external_pending_fraction,
            reserved_risk_fraction=reserved,
            total_committed_risk_fraction=committed,
            remaining_capacity_fraction=max(0.0,self.max_open_risk-committed),
            daily_drawdown_fraction=daily.max_drawdown_fraction,
            total_drawdown_fraction=self.total.current_drawdown_fraction,
            daily_halted=daily.halted,
            unbounded_exposure_ids=tuple(sorted(set(unbounded))),
        )

    def snapshot_state(self)->dict[str,Any]:
        return {
            "max_open_risk":self.max_open_risk,
            "pending":[asdict(x) for x in self.pending.values()],
            "reservations":self.reservations.snapshot_state(),
            "daily":self.daily.snapshot_state(),
            "total":self.total.snapshot_state(),
        }

    def restore_state(self,state:Mapping[str,Any])->None:
        if abs(float(state.get("max_open_risk",self.max_open_risk))-self.max_open_risk)>1e-12:
            raise ValueError("max_open_risk mismatch")
        self.pending={}
        for raw in state.get("pending",[]):
            spec_raw=raw.get("symbol_spec")
            spec=None if spec_raw is None else SymbolRiskSpec(**spec_raw)
            item=PendingOrderRiskInput(
                order_id=str(raw["order_id"]),origin=str(raw["origin"]),side=str(raw["side"]),
                volume=float(raw["volume"]),entry_price=float(raw["entry_price"]),
                stop_loss=None if raw["stop_loss"] is None else float(raw["stop_loss"]),
                symbol_spec=spec,
                broker_loss_to_sl=None if raw.get("broker_loss_to_sl") is None else float(raw["broker_loss_to_sl"]),
            )
            self.pending[item.order_id]=item
        self.reservations.restore_state(state.get("reservations",{}))
        self.daily.restore_state(state.get("daily",{}))
        self.total.restore_state(state.get("total",{}))


@dataclass(frozen=True, slots=True)
class RiskAuthorizationResult:
    reservation_id: str
    approved_fraction: float
    action: str
    reason: str
    reserved: bool
    state: AccountRiskStateSnapshot


class AccountRiskCoordinator:
    """Serial authority boundary: assess -> approve -> reserve in one operation."""

    def __init__(self,state_engine:AccountRiskStateEngine,governor=None,capital=None):
        from katarina.engines.risk import RiskGovernor
        self.state_engine=state_engine
        self.governor=governor or RiskGovernor(max_open_risk=state_engine.max_open_risk)
        self.capital=capital

    @classmethod
    def with_adaptive_risk(cls,state_engine,*,capital=None,config_path=None):
        """Explicitly select the account-aware profile; does not arm execution."""
        from pathlib import Path
        from katarina.engines.risk import RiskGovernor
        path=config_path or Path(__file__).resolve().parents[3]/"config"/"risk_governor_v2.json"
        governor=RiskGovernor.from_config(path)
        if governor.adaptive_profile is None:
            raise ValueError("adaptive_risk_disabled")
        if abs(governor.max_open_risk-state_engine.max_open_risk)>1e-12:
            raise ValueError("risk_state_cap_mismatch")
        return cls(state_engine,governor,capital=capital)

    def authorize_and_reserve(
        self,
        positions:AccountRiskAssessment,
        *,
        reservation_id:str,
        day_key:str,
        requested_fraction:float|None,
        uncertainty:float,
        expected_rr:float,
        health_ok:bool,
        reconciled:bool,
        account_currency:str|None=None,
        entry_kind:str="NORMAL",
        drawdown_authority=None,
        broker_session:BrokerSessionEvidence|None=None,
    )->RiskAuthorizationResult:
        self.state_engine.observe_equity(day_key,positions.equity)
        risk_capital=None
        if self.capital is not None:
            snap=self.capital.snapshot()
            risk_capital=snap.effective_risk_capital(equity=positions.equity)
        state=self.state_engine.assess(positions,risk_capital=risk_capital)
        # Persistent equity high-water mark prevents raising the risk percentage
        # just because capital temporarily drops after a loss or reserve sweep.
        high_water=max(state.risk_capital,self.state_engine.total.peak_equity)
        from katarina.engines.risk import RiskAction, RiskDecision
        # No authenticated per-position realized+floating source exists in
        # the current KAT1 protocol. Do NOT authorize the Owner DD35
        # exception from an arbitrary "verified" boolean or JSON receipt.
        if entry_kind=="EXTREME_RECOVERY":
            decision=RiskDecision(RiskAction.PAUSE,0.0,
                                  "broker_origin_pnl_adapter_not_authenticated")
        elif entry_kind=="RECOVERY_FACTOR" and (
                not isinstance(broker_session,BrokerSessionEvidence)
                or broker_session.day_key!=day_key):
            decision=RiskDecision(RiskAction.PAUSE,0.0,
                                  "broker_trading_day_unverified")
        else:
            decision=self.governor.evaluate_state(
                state,requested_fraction=requested_fraction,uncertainty=uncertainty,
                expected_rr=expected_rr,health_ok=health_ok,reconciled=reconciled,
                account_currency=account_currency,
                risk_reference_capital=high_water,entry_kind=entry_kind,
                trading_day_key=day_key,
                drawdown_authority=drawdown_authority,
            )
        reserved=False
        if decision.action.value in {"APPROVE","REDUCE"} and decision.approved_fraction>0:
            reserved=self.state_engine.reservations.reserve(reservation_id,decision.approved_fraction)
        return RiskAuthorizationResult(
            reservation_id,decision.approved_fraction,decision.action.value,
            decision.reason,reserved,state
        )


class Kat1PendingOrderRiskRuntime:
    """Consumes ACCEPTED KAT1 account/symbol/order state into pending-risk state."""

    ACTIVE_PENDING_STATES={2,3}  # PLACED, PARTIAL

    def __init__(self,state_engine:AccountRiskStateEngine):
        self.state_engine=state_engine
        self._money_scale:int|None=None
        self._symbols:dict[int,dict[str,int]]={}

    @staticmethod
    def _scaled(units:int,scale:int)->float:
        return float(units)*(10.0**(-int(scale)))

    def observe(self,result)->bool:
        from katarina.validation.engine import ValidationDisposition
        if result.disposition is not ValidationDisposition.ACCEPT:
            return False
        event=result.event
        payload=event.payload
        if not isinstance(payload,Mapping):
            return False

        if event.topic=="account.state":
            if "account_currency_digits" not in payload:return False
            self._money_scale=int(payload["account_currency_digits"])
            return True

        if event.topic=="symbol.spec":
            required=("instrument_id","spec_revision","price_scale","volume_scale","tick_size_units","tick_value_loss_units")
            if any(x not in payload for x in required):return False
            self._symbols[int(payload["instrument_id"])]={
                "spec_revision":int(payload["spec_revision"]),
                "price_scale":int(payload["price_scale"]),
                "volume_scale":int(payload["volume_scale"]),
                "tick_size_units":int(payload["tick_size_units"]),
                "tick_value_loss_units":int(payload["tick_value_loss_units"]),
            }
            return True

        if event.topic!="order.state":
            return False

        order_id=str(int(payload.get("broker_order_ticket",0)))
        if order_id=="0":return False
        change=int(payload.get("change_kind",0))
        entry_type=int(payload.get("entry_type",0))
        state=int(payload.get("normalized_order_state",0))
        if change==2 or entry_type not in {2,3} or state not in self.ACTIVE_PENDING_STATES:
            self.state_engine.remove_pending(order_id)
            return True

        instrument=int(payload.get("instrument_id",0))
        profile=self._symbols.get(instrument)
        if profile is None or self._money_scale is None:
            # Preserve the exposure but make it unbounded/fail-closed.
            spec=None; price_scale=0; volume_scale=0
        else:
            price_scale=profile["price_scale"]; volume_scale=profile["volume_scale"]
            spec=SymbolRiskSpec(
                self._scaled(profile["tick_size_units"],price_scale),
                self._scaled(profile["tick_value_loss_units"],self._money_scale),
            )

        sl_units=int(payload.get("sl_units",0))
        item=PendingOrderRiskInput(
            order_id=order_id,
            origin={
                1:"KATARINA",2:"MANUAL_DESKTOP",3:"MANUAL_MOBILE",4:"MANUAL_WEB",
                5:"FOREIGN_EA",6:"BROKER_OPERATION"
            }.get(int(payload.get("origin_class",0)),"UNKNOWN"),
            side={1:"BUY",2:"SELL"}.get(int(payload.get("side",0)),"NONE"),
            volume=self._scaled(int(payload.get("volume_current_units",0)),volume_scale),
            entry_price=self._scaled(int(payload.get("price_open_units",0)),price_scale),
            stop_loss=None if sl_units<=0 else self._scaled(sl_units,price_scale),
            symbol_spec=spec,
        )
        self.state_engine.upsert_pending(item)
        return True


class Kat1AccountRiskStateRuntime:
    """Binds accepted KAT1 account ledger/equity/order events to risk state.

    External balance operations are accumulated from ACCOUNT_LEDGER_EVENT and
    neutralized against daily/total drawdown when the next account.state
    provides authoritative post-flow equity. Trading commission (ledger kind 7)
    is intentionally not neutralized.
    """

    EXTERNAL_LEDGER_KINDS={1,2,3,4,5,6,8,9,10,11}

    def __init__(self,state_engine:AccountRiskStateEngine):
        self.state_engine=state_engine
        self.pending_runtime=Kat1PendingOrderRiskRuntime(state_engine)
        self._money_scale:int|None=None
        self._pending_external_flow=0.0

    @staticmethod
    def _day_key(source_time_ns:int|None)->str:
        from datetime import datetime, timezone
        if source_time_ns is None or source_time_ns<=0:
            return datetime.now(timezone.utc).date().isoformat()
        return datetime.fromtimestamp(source_time_ns/1_000_000_000,tz=timezone.utc).date().isoformat()

    def observe(self,result)->bool:
        from katarina.validation.engine import ValidationDisposition
        if result.disposition is not ValidationDisposition.ACCEPT:
            return False
        event=result.event
        payload=event.payload
        if not isinstance(payload,Mapping):
            return False

        if event.topic=="account.ledger":
            if self._money_scale is None:
                return False
            kind=int(payload.get("ledger_kind",0))
            if kind in self.EXTERNAL_LEDGER_KINDS:
                amount=float(int(payload.get("amount_units",0)))*(10.0**(-self._money_scale))
                self._pending_external_flow+=amount
            return True

        if event.topic=="account.state":
            if "account_currency_digits" not in payload or "equity_units" not in payload:
                return False
            self._money_scale=int(payload["account_currency_digits"])
            equity=float(int(payload["equity_units"]))*(10.0**(-self._money_scale))
            day=self._day_key(event.source_time_ns)
            if abs(self._pending_external_flow)>1e-12:
                self.state_engine.apply_cash_flow(day,self._pending_external_flow,equity_after=equity)
                self._pending_external_flow=0.0
            else:
                self.state_engine.observe_equity(day,equity)
            self.pending_runtime.observe(result)
            return True

        return self.pending_runtime.observe(result)

    def snapshot_state(self)->dict[str,Any]:
        return {
            "money_scale":self._money_scale,
            "pending_external_flow":self._pending_external_flow,
        }

    def restore_state(self,state:Mapping[str,Any])->None:
        raw=state.get("money_scale")
        self._money_scale=None if raw is None else int(raw)
        self._pending_external_flow=float(state.get("pending_external_flow",0.0))
