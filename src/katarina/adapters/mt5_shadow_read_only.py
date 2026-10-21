"""MT5 read-only shadow adapter with dependency-injected broker API.

This module intentionally cannot call order_send, positions_close or trade
operations. It fetches quotes, fully closed OHLC candles and computes
broker-native account-currency risk using order_calc_profit/margin.
A quote is ONLY forward PAPER evidence if the terminal is observed LIVE.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import floor, isfinite
from typing import Any

from katarina.intelligence.shadow.shadow_paper_book import ObservedQuote, PaperPosition
from katarina.intelligence.shadow.shadow_journal import ShadowSignal, _utc


@dataclass(frozen=True, slots=True)
class ClosedBar:
    open_at_utc: datetime
    closed_at_utc: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int


@dataclass(frozen=True, slots=True)
class ShadowMarketSnapshot:
    symbol: str
    account_currency: str
    observed_at_utc: datetime
    bid: float
    ask: float
    tick_size: float
    point: float
    volume_min: float
    volume_step: float
    volume_max: float
    free_margin_account: float
    m5: tuple[ClosedBar, ...]
    h1: tuple[ClosedBar, ...]
    h4: tuple[ClosedBar, ...]


class MT5ShadowReadOnly:
    """The injected MT5 module supports only reads and calculator calls.

    Call initialize() explicitly in an operator-owned process, then pass
    that initialized MetaTrader5 object here. The adapter does not own
    terminal lifecycle, trade credentials, scheduling or order routing.
    """

    def __init__(self, mt5_api: Any, *, max_quote_age_seconds: int = 90):
        if max_quote_age_seconds < 1:
            raise ValueError("invalid_quote_freshness")
        self.mt5 = mt5_api
        self.max_quote_age_seconds = max_quote_age_seconds

    @staticmethod
    def _finite_positive(value: object) -> float:
        if isinstance(value, bool):
            raise ValueError("nonfinite_or_nonpositive_broker_value")
        try:
            val = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("nonfinite_or_nonpositive_broker_value") from exc
        if not isfinite(val) or val <= 0:
            raise ValueError("nonfinite_or_nonpositive_broker_value")
        return val

    def _account(self) -> Any:
        account = self.mt5.account_info()
        if account is None or not getattr(account, "currency", ""):
            raise ValueError("broker_account_currency_not_verified")
        self._finite_positive(getattr(account, "margin_free", None))
        return account

    @staticmethod
    def _bars(rows: object, duration_seconds: int,
              observed: datetime) -> tuple[ClosedBar, ...]:
        if rows is None:
            raise ValueError("broker_candle_history_missing")
        items = []
        for row in rows:
            # MetaTrader5 returns NumPy structured arrays (field indexing).
            ts = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)
            end = ts + timedelta(seconds=duration_seconds)
            if end > observed:
                # Protect against lookahead from incomplete current bars.
                continue
            numbers = [float(row[key]) for key in ("open","high","low","close")]
            volume = int(row["tick_volume"])
            if (not all(isfinite(x) and x>0 for x in numbers) or
                    numbers[2] > min(numbers[0],numbers[3]) or
                    numbers[1] < max(numbers[0],numbers[3]) or
                    volume < 0):
                raise ValueError("corrupt_broker_candle")
            items.append(ClosedBar(ts,end,*numbers,volume))
        items.sort(key=lambda x:x.open_at_utc)
        if not items or len({x.open_at_utc for x in items}) != len(items):
            raise ValueError("broker_candle_history_empty_or_duplicate")
        if observed - items[-1].closed_at_utc > timedelta(seconds=duration_seconds*2):
            raise ValueError("stale_closed_candles")
        return tuple(items)

    def snapshot(self, symbol: str, *, observed_at_utc: datetime,
                 m5_count: int = 112, h1_count: int = 80,
                 h4_count: int = 55) -> ShadowMarketSnapshot:
        observed = _utc(observed_at_utc)
        if not symbol or min(m5_count,h1_count,h4_count) < 3:
            raise ValueError("unverified_symbol_or_bar_depth")
        account = self._account()
        spec = self.mt5.symbol_info(symbol)
        quote = self.mt5.symbol_info_tick(symbol)
        if spec is None or quote is None:
            raise ValueError("broker_symbol_or_tick_unavailable")
        tick_time = datetime.fromtimestamp(int(quote.time_msc)/1000, tz=timezone.utc)
        if not (timedelta(0) <= observed-tick_time <=
                timedelta(seconds=self.max_quote_age_seconds)):
            raise ValueError("stale_or_future_broker_quote")
        bid = self._finite_positive(quote.bid)
        ask = self._finite_positive(quote.ask)
        if ask < bid:
            raise ValueError("crossed_broker_market")
        values = {k:self._finite_positive(getattr(spec,k,None))
                  for k in ("trade_tick_size","point","volume_min","volume_step","volume_max")}
        if values["volume_min"] > values["volume_max"]:
            raise ValueError("broker_minimum_volume_exceeds_max")
        prices = {}
        for key,period,count,seconds in (
                ("m5",self.mt5.TIMEFRAME_M5,m5_count,300),
                ("h1",self.mt5.TIMEFRAME_H1,h1_count,3600),
                ("h4",self.mt5.TIMEFRAME_H4,h4_count,14400)):
            bars = self.mt5.copy_rates_from_pos(symbol,period,0,count+1)
            prices[key] = self._bars(bars, seconds, observed)
            if len(prices[key]) < count:
                raise ValueError("insufficient_closed_candle_history")
            prices[key] = prices[key][-count:]
        return ShadowMarketSnapshot(
            symbol,account.currency,observed,bid,ask,
            values["trade_tick_size"],values["point"],values["volume_min"],
            values["volume_step"],values["volume_max"],
            self._finite_positive(account.margin_free),
            prices["m5"],prices["h1"],prices["h4"])

    def _order_type(self, side: str) -> int:
        if side not in ("BUY","SELL"):
            raise ValueError("unsupported_paper_side")
        return self.mt5.ORDER_TYPE_BUY if side=="BUY" else self.mt5.ORDER_TYPE_SELL

    def profit_account(self, position: PaperPosition, exit_price: float) -> float:
        price = self._finite_positive(exit_price)
        account=self._account()
        if account.currency != position.account_currency:
            raise ValueError("broker_account_currency_changed")
        profit=self.mt5.order_calc_profit(
            self._order_type(position.side), position.symbol,position.volume,
            position.entry_price,price)
        if profit is None or not isfinite(float(profit)):
            raise ValueError("broker_profit_calculator_unavailable")
        return float(profit)

    def build_position(self, signal: ShadowSignal, snapshot: ShadowMarketSnapshot,
                       *, stop_distance: float, reward_ratio: float,
                       holding_minutes: int, risk_budget_account: float,
                       commission_round_trip_per_lot: float | None = None,
                       exposure_group: str = "GOLD") -> PaperPosition:
        """Calculate minimum-lot-safe paper size, no order sent.

        Commission must be broker-verified before outcomes may serve as
        proof. Default None intentionally keeps costs_verified=False.
        """
        if (signal.action != "ACCEPT" or signal.side not in ("BUY","SELL") or
                signal.symbol != snapshot.symbol or
                _utc(signal.observed_at_utc) > snapshot.observed_at_utc):
            raise ValueError("signal_snapshot_mismatch")
        distance=self._finite_positive(stop_distance)
        rr=self._finite_positive(reward_ratio)
        budget=self._finite_positive(risk_budget_account)
        if holding_minutes < 1:
            raise ValueError("invalid_shadow_holding_period")
        if self._account().currency != snapshot.account_currency:
            raise ValueError("broker_account_currency_changed")
        entry=snapshot.ask if signal.side=="BUY" else snapshot.bid
        stop=entry-distance if signal.side=="BUY" else entry+distance
        target=entry+distance*rr if signal.side=="BUY" else entry-distance*rr
        if stop <= 0 or target <= 0:
            raise ValueError("invalid_shadow_stop_or_target")
        if distance < 2.5*(snapshot.ask-snapshot.bid) or distance < 4*snapshot.tick_size:
            raise ValueError("paper_stop_too_near_spread")
        order_type=self._order_type(signal.side)
        minlot=snapshot.volume_min
        loss_min=self.mt5.order_calc_profit(order_type,signal.symbol,minlot,entry,stop)
        if loss_min is None or not isfinite(float(loss_min)) or float(loss_min) >= 0:
            raise ValueError("broker_stop_risk_unavailable")
        if commission_round_trip_per_lot is not None:
            if (not isfinite(float(commission_round_trip_per_lot)) or
                    commission_round_trip_per_lot < 0):
                raise ValueError("invalid_paper_commission")
            commission=float(commission_round_trip_per_lot)
        else:
            commission=0.
        # If volume_step does not divide volume_min, enumerate from broker min.
        step=snapshot.volume_step
        risk_per_min=abs(float(loss_min))+minlot*commission
        max_by_risk=(budget/risk_per_min)*minlot
        increments=floor((max_by_risk-minlot+1e-10)/step)
        if increments < 0:
            raise ValueError("paper_risk_below_minimum_broker_lot")
        volume=round(minlot+max(0,increments)*step,8)
        volume=min(volume,snapshot.volume_max)
        # Never round UP if the max broker volume is off the step grid.
        volume=round(minlot+max(0,floor((volume-minlot+1e-10)/step))*step,8)
        while volume+1e-10 >= minlot:
            loss=self.mt5.order_calc_profit(order_type,signal.symbol,volume,entry,stop)
            margin=self.mt5.order_calc_margin(order_type,signal.symbol,volume,entry)
            if (loss is None or margin is None or
                    not isfinite(float(loss)) or not isfinite(float(margin)) or
                    float(loss)>=0 or float(margin)<=0):
                raise ValueError("broker_paper_risk_or_margin_unavailable")
            risk=abs(float(loss))+commission*volume
            if (risk <= budget + 1e-8 and
                    float(margin) <= snapshot.free_margin_account*.5):
                return PaperPosition(
                    signal_id=signal.event_id,symbol=signal.symbol,side=signal.side,
                    entry_at_utc=snapshot.observed_at_utc,
                    exit_deadline_utc=snapshot.observed_at_utc+
                       timedelta(minutes=holding_minutes),
                    entry_price=entry,sl_price=stop,tp_price=target,
                    volume=volume,account_currency=snapshot.account_currency,
                    initial_risk_account=risk,
                    entry_commission_account=-commission*volume/2,
                    exit_commission_account=-commission*volume/2,
                    # A configured PAPER commission is an assumption, NOT
                    # broker-attested fills/fees. ForwardStrategyEvidenceGate
                    # must remain blocked until independent reconciliation.
                    costs_verified=False,
                    contract_verified=True,exposure_group=exposure_group)
            volume=round(volume-step,8)
        raise ValueError("paper_risk_or_margin_below_minimum_broker_lot")

    @staticmethod
    def quote(snapshot: ShadowMarketSnapshot) -> ObservedQuote:
        return ObservedQuote(snapshot.symbol,snapshot.observed_at_utc,
                             snapshot.bid,snapshot.ask)
