"""One-shot or repeating MT5 read-only shadow research controller.

Fully isolated from ExecutionEngine and broker order functions. Every M5
decision and simulated close uses a unique immutable ID. The controller
always denies live execution; no other code path is capable of placing orders.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import isfinite

from katarina.engines.risk import RiskAction, RiskGovernor, RiskRequest
from katarina.intelligence.shadow.shadow_gold_intraday import GoldShadowIntraday
from katarina.intelligence.shadow.shadow_journal import ShadowJournal, ShadowSignal, _utc
from katarina.intelligence.shadow.shadow_paper_book import ShadowPaperBook
from katarina.adapters.mt5_shadow_read_only import MT5ShadowReadOnly


@dataclass(frozen=True, slots=True)
class ShadowCycleReport:
    symbol: str
    closed_paper_positions: int
    accepted_paper_positions: int
    rejected_or_wait_signals: int
    paper_account_balance: float
    live_order_count: int = 0


class MT5ShadowCycle:
    def __init__(
        self,
        *, broker: MT5ShadowReadOnly,
        journal: ShadowJournal,
        paper_book: ShadowPaperBook,
        risk_governor: RiskGovernor,
        strategy_version: str,
        frozen_at_utc: datetime,
        initial_paper_balance_account: float,
        commission_round_trip_per_lot: float | None = None,
        analyst: GoldShadowIntraday | None = None,
    ):
        if not strategy_version or not isfinite(initial_paper_balance_account) or initial_paper_balance_account <= 0:
            raise ValueError("invalid_shadow_capital_or_version")
        if (commission_round_trip_per_lot is not None and
                (not isfinite(commission_round_trip_per_lot) or
                 commission_round_trip_per_lot < 0)):
            raise ValueError("invalid_shadow_fee")
        self.broker=broker
        self.journal=journal
        self.book=paper_book
        self.risk=risk_governor
        self.frozen=_utc(frozen_at_utc)
        self.version=strategy_version
        self.initial=float(initial_paper_balance_account)
        self.commission=commission_round_trip_per_lot
        self.analyst=analyst or GoldShadowIntraday()

    def _balance(self, as_of_utc: datetime) -> tuple[float,float,float,float]:
        """Reconcile net closed PAPER cash, peak, daily and total drawdown.

        A shadow book is a separate virtual account. Never infer paper capital
        from the live MT5 account. Closing timestamps form one coherent ledger.
        """
        groups={}
        for close in self.journal._closes.values():
            if close.signal_id in self.book._opened:
                groups.setdefault(close.signal_id,[]).append(close)
        transactions=[]
        for signal_id,items in groups.items():
            if sum(int(x.final_close) for x in items)!=1:
                continue
            latest=max(items,key=lambda x:x.closed_at_utc)
            total=sum(x.gross_pnl_account+x.commission_account+x.swap_account-
                      x.slippage_cost_account for x in items)
            transactions.append((latest.closed_at_utc,total))
        transactions.sort()
        balance=self.initial;peak=balance
        today=None;day_base=balance;daily_dd=total_dd=0.
        for timestamp,pnl in transactions:
            key=timestamp.date()
            if key!=today:
                today=key;day_base=balance;daily_dd=0.
            balance+=pnl
            peak=max(peak,balance)
            # A hard drawdown pause must remain latched for the whole
            # trading day, even if later paper wins recover the balance.
            daily_now=max(0,(day_base-balance)/day_base) if day_base>0 else 1.
            daily_dd=max(daily_dd,daily_now)
            total_now=max(0,(peak-balance)/peak) if peak>0 else 1.
            total_dd=max(total_dd,total_now)
        if today != _utc(as_of_utc).date():
            daily_dd=0.
        return balance,peak,daily_dd,total_dd

    @staticmethod
    def _event_id(symbol: str,strategy: str,version: str,close: datetime) -> str:
        raw=f"{symbol}|{strategy}|{version}|{close.astimezone(timezone.utc).isoformat()}"
        return "shadow-signal:"+sha256(raw.encode()).hexdigest()[:32]

    def run_once(self, symbol: str, *, observed_at_utc: datetime,
                 research_news_clear: bool = False) -> ShadowCycleReport:
        observed=_utc(observed_at_utc)
        if observed <= self.frozen:
            raise ValueError("strategy_version_not_frozen_before_observation")
        snap=self.broker.snapshot(symbol,observed_at_utc=observed)
        # First update positions with observed bid/ask: never fabricate a close
        # using the signal candle's high/low.
        closed=self.book.on_quote(
            self.broker.quote(snap),profit_at_exit=self.broker.profit_account)
        balance,peak,daily_dd,total_dd=self._balance(observed)
        if balance<=0:
            raise ValueError("shadow_bankrupt_no_new_trades")
        accepted=0;rejected=0
        if observed-snap.m5[-1].closed_at_utc>timedelta(minutes=5):
            raise ValueError("stale_latest_closed_m5")
        for setup in self.analyst.analyze(snap):
            # Once recorded, this bar is immutable: retries only replay
            # pending book state; no second order or repeated decision.
            event_id=self._event_id(symbol,setup.strategy_id,self.version,
                                    snap.m5[-1].closed_at_utc)
            if event_id in self.journal._signals:
                if (self.journal._signals[event_id].action=="ACCEPT" and
                        event_id not in self.book._opened):
                    raise ValueError("accepted_signal_missing_paper_open")
                continue
            day=snap.m5[-1].closed_at_utc.date()
            attempted=any(
                s.symbol==symbol and s.strategy_id==setup.strategy_id and
                s.strategy_version==self.version and s.action=="ACCEPT" and
                s.observed_at_utc.date()==day
                for s in self.journal._signals.values())
            reason=setup.reason;side=setup.side
            action="ACCEPT" if side in ("BUY","SELL") else "NO_TRADE"
            if action=="ACCEPT" and not research_news_clear:
                action="REJECT";reason="news_clearance_not_verified"
            elif action=="ACCEPT" and attempted:
                action="REJECT";reason="session_setup_already_attempted"
            elif action=="ACCEPT" and self.book.pending():
                action="REJECT";reason="shadow_exposure_group_busy"
            signal=ShadowSignal(
                event_id=event_id,symbol=symbol,strategy_id=setup.strategy_id,
                strategy_version=self.version,
                observed_at_utc=snap.m5[-1].closed_at_utc,
                frozen_at_utc=self.frozen,
                m5_closed_at_utc=snap.m5[-1].closed_at_utc,
                h1_closed_at_utc=snap.h1[-1].closed_at_utc,
                h4_closed_at_utc=snap.h4[-1].closed_at_utc,
                side=side,action=action,reason=reason,
                broker_session_open=True,data_fresh=True,
                # Calendar state is UNKNOWN until an authenticated news
                # adapter supplies it. Missing clearance is a REJECT reason,
                # not false evidence that a real blackout was detected.
                news_blackout=False,
                spread_price_units=snap.ask-snap.bid,
                spec_revision=1)  # research schema revision, not broker spec hash
            position=None
            if action=="ACCEPT":
                commitments=sum(p.initial_risk_account for p in self.book.pending())/balance
                approved=self.risk.evaluate(RiskRequest(
                    requested_fraction=None,
                    open_risk_fraction=commitments,
                    drawdown_fraction=total_dd,daily_drawdown_fraction=daily_dd,
                    uncertainty=.1,expected_rr=setup.rr,
                    health_ok=True,reconciled=True,
                    risk_capital=balance,risk_reference_capital=max(balance,peak),
                    account_currency=snap.account_currency,
                ))
                if approved.action not in (RiskAction.APPROVE,RiskAction.REDUCE):
                    signal=replace(signal,action="REJECT",reason="risk_governor:"+approved.reason)
                else:
                    try:
                        # A virtual account must never borrow the *real*
                        # terminal account's extra margin. Include only
                        # unused virtual capital after worst-case reserved
                        # paper losses, and separately respect the broker's
                        # reported margin availability.
                        virtual_reserved=sum(
                            p.initial_risk_account for p in self.book.pending())
                        virtual_free=max(0.,balance-virtual_reserved)
                        if virtual_free<=0:
                            raise ValueError("shadow_virtual_margin_exhausted")
                        capped_snapshot=replace(
                            snap,free_margin_account=min(
                                snap.free_margin_account,virtual_free))
                        position=self.broker.build_position(
                            signal,capped_snapshot,stop_distance=setup.sl_distance,
                            reward_ratio=setup.rr,holding_minutes=setup.hold_minutes,
                            risk_budget_account=approved.approved_fraction*balance,
                            commission_round_trip_per_lot=self.commission,
                            exposure_group="GOLD",
                        )
                    except ValueError as exc:
                        signal=replace(signal,action="REJECT",reason=str(exc))
            self.journal.append(signal)
            if position is not None:
                self.book.open(position)
                accepted+=1
            else:
                rejected+=1
        new_balance,_,_,_=self._balance(observed)
        return ShadowCycleReport(symbol,len(closed),accepted,rejected,new_balance)
