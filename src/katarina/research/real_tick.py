from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from katarina.engines.position import RRPositionState, RRProfitTracker
from katarina.research.backtest import BacktestResult, BacktestTrade, BacktestingEngine


@dataclass(frozen=True, slots=True)
class Tick:
    timestamp_ns: int
    bid: float
    ask: float


@dataclass(frozen=True, slots=True)
class RealTickTradeSpec:
    trade_id: str
    side: str
    entry_index: int
    stop_distance: float
    target_rr: float
    volume: float
    value_per_price_unit_per_lot: float
    volume_min: float=.01
    volume_step: float=.01
    commission_per_lot: float=0.0
    slippage_price: float=0.0


@dataclass(frozen=True, slots=True)
class RealTickTradeResult:
    trade_id: str
    net_pnl: float
    r_multiple: float
    exit_reason: str
    partial_done: bool
    peak_r: float
    final_stop: float
    remaining_volume: float


@dataclass(frozen=True, slots=True)
class RealTickBatchResult:
    trades: tuple[RealTickTradeResult,...]
    metrics: BacktestResult


class RealTickBacktester:
    """Tick-by-tick execution simulator with live RR-management semantics."""

    @staticmethod
    def _exit_price(t:Tick,side:str,slip:float)->float:
        return t.bid-slip if side=="BUY" else t.ask+slip

    @staticmethod
    def _entry_price(t:Tick,side:str,slip:float)->float:
        return t.ask+slip if side=="BUY" else t.bid-slip

    @staticmethod
    def _pnl(side:str,entry:float,exit_price:float,volume:float,value:float,commission_per_lot:float)->float:
        sign=1.0 if side=="BUY" else -1.0
        return sign*(exit_price-entry)*volume*value-abs(commission_per_lot)*volume

    def simulate_trade(self,ticks:Sequence[Tick],spec:RealTickTradeSpec)->RealTickTradeResult:
        if spec.side not in {"BUY","SELL"} or spec.entry_index<0 or spec.entry_index>=len(ticks):
            raise ValueError("invalid trade spec")
        if spec.stop_distance<=0 or spec.target_rr<=1 or spec.volume<=0 or spec.value_per_price_unit_per_lot<=0:
            raise ValueError("invalid trade economics")
        entry=self._entry_price(ticks[spec.entry_index],spec.side,spec.slippage_price)
        sign=1.0 if spec.side=="BUY" else -1.0
        stop=entry-sign*spec.stop_distance
        target=entry+sign*spec.target_rr*spec.stop_distance
        volume=spec.volume
        authorized=spec.volume
        tracker=RRProfitTracker()
        realized=0.0
        partial=False
        peak_r=0.0
        exit_reason="end_of_data"

        for tick in ticks[spec.entry_index+1:]:
            mark=self._exit_price(tick,spec.side,0.0)
            stop_hit=mark<=stop if spec.side=="BUY" else mark>=stop
            target_hit=mark>=target if spec.side=="BUY" else mark<=target
            if stop_hit:
                px=self._exit_price(tick,spec.side,spec.slippage_price)
                realized+=self._pnl(spec.side,entry,px,volume,spec.value_per_price_unit_per_lot,spec.commission_per_lot)
                volume=0.0;exit_reason="STOP";break
            if target_hit:
                px=self._exit_price(tick,spec.side,spec.slippage_price)
                realized+=self._pnl(spec.side,entry,px,volume,spec.value_per_price_unit_per_lot,spec.commission_per_lot)
                volume=0.0;exit_reason="TARGET";break

            plan=tracker.evaluate(RRPositionState(
                spec.trade_id,spec.side,entry,mark,stop,spec.stop_distance,spec.target_rr,
                authorized,volume,spec.volume_min,spec.volume_step
            ))
            peak_r=max(peak_r,plan.peak_r)
            if plan.partial_close_volume>0:
                px=self._exit_price(tick,spec.side,spec.slippage_price)
                realized+=self._pnl(spec.side,entry,px,plan.partial_close_volume,spec.value_per_price_unit_per_lot,spec.commission_per_lot)
                volume=round(volume-plan.partial_close_volume,8)
                partial=True
            if plan.modify_sl_required and plan.new_stop is not None:
                stop=plan.new_stop

        if volume>0:
            tick=ticks[-1]
            px=self._exit_price(tick,spec.side,spec.slippage_price)
            realized+=self._pnl(spec.side,entry,px,volume,spec.value_per_price_unit_per_lot,spec.commission_per_lot)
            volume=0.0

        initial_risk_cash=spec.stop_distance*spec.volume*spec.value_per_price_unit_per_lot
        return RealTickTradeResult(
            spec.trade_id,realized,realized/initial_risk_cash if initial_risk_cash>0 else 0.0,
            exit_reason,partial,peak_r,stop,volume
        )

    def run(self,ticks:Sequence[Tick],specs:Sequence[RealTickTradeSpec])->RealTickBatchResult:
        results=tuple(self.simulate_trade(ticks,s) for s in specs)
        metrics=BacktestingEngine().evaluate([BacktestTrade(x.net_pnl,0.0) for x in results])
        return RealTickBatchResult(results,metrics)
