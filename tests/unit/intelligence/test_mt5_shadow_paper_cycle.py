"""Read-only shadow execution contract: synthetic MT5 and restart regression."""
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace

from katarina.adapters.mt5_shadow_read_only import (
    MT5ShadowReadOnly,ShadowMarketSnapshot,ClosedBar)
from katarina.engines.risk import RiskGovernor
from katarina.intelligence.shadow.shadow_journal import ShadowJournal,ShadowSignal
from katarina.intelligence.shadow.shadow_paper_book import (
    ShadowPaperBook,ObservedQuote,PaperPosition)
from katarina.intelligence.shadow.shadow_gold_intraday import (
    ShadowSetup)
from katarina.intelligence.broker.mt5_shadow_cycle import MT5ShadowCycle

UTC=timezone.utc
FREEZE=datetime(2026,10,1,tzinfo=UTC)
BAR_CLOSE=datetime(2026,10,12,7,10,tzinfo=UTC)
OBS=BAR_CLOSE+timedelta(seconds=10)


def signal(i=1,side="BUY",symbol="XAUUSD.vx"):
    return ShadowSignal(
        event_id=f"shadow-{i}",symbol=symbol,strategy_id="GOLD_OR_SHADOW_V1",
        strategy_version="frozen-20261001",observed_at_utc=BAR_CLOSE,
        frozen_at_utc=FREEZE,
        m5_closed_at_utc=BAR_CLOSE,h1_closed_at_utc=BAR_CLOSE-timedelta(minutes=10),
        h4_closed_at_utc=BAR_CLOSE-timedelta(hours=3,minutes=10),
        side=side,action="ACCEPT",reason="research-only",
        broker_session_open=True,data_fresh=True,news_blackout=False,
        spread_price_units=.2,spec_revision=1)


def bars(end: datetime,n: int,minutes: int,p0=4100.):
    duration=timedelta(minutes=minutes)
    start=end-duration*n
    output=[]
    for k in range(n):
        opened=start+k*duration
        price=p0+.05*k
        output.append(ClosedBar(
            opened,opened+duration,price,price+1.,price-.8,
            price+.4,1000+k))
    return tuple(output)


def snapshot(*,obs=OBS,bid=4100.,ask=4100.2,m5end=BAR_CLOSE):
    return ShadowMarketSnapshot(
        "XAUUSD.vx","USD",obs,bid,ask,
        .01,.01,.01,.01,50.,10000.,
        bars(m5end,113,5),bars(datetime(2026,10,12,7,tzinfo=UTC),80,60),
        bars(datetime(2026,10,12,4,tzinfo=UTC),55,240))


class FakeMT5:
    TIMEFRAME_M5=5
    TIMEFRAME_H1=60
    TIMEFRAME_H4=240
    ORDER_TYPE_BUY=0
    ORDER_TYPE_SELL=1

    def __init__(self):
        self.currency="USD"
        self.margin_free=10000.
        self.time=OBS
        self.bid=4100.
        self.ask=4100.2
        self.missing=False

    def account_info(self):
        return SimpleNamespace(currency=self.currency,margin_free=self.margin_free)

    def symbol_info(self,symbol):
        if self.missing:return None
        return SimpleNamespace(
            trade_tick_size=.01,point=.01,volume_min=.01,
            volume_step=.01,volume_max=50.)

    def symbol_info_tick(self,symbol):
        if self.missing:return None
        return SimpleNamespace(time_msc=int(self.time.timestamp()*1000),
            bid=self.bid,ask=self.ask)

    def copy_rates_from_pos(self,symbol,timeframe,pos,count):
        if self.missing:return None
        timeframes={
            5:(datetime(2026,10,12,7,10,tzinfo=UTC),timedelta(minutes=5)),
            60:(datetime(2026,10,12,7,tzinfo=UTC),timedelta(hours=1)),
            240:(datetime(2026,10,12,4,tzinfo=UTC),timedelta(hours=4))}
        end,duration=timeframes[timeframe]
        # include one unfinished current candle in the source to prove
        # closed-bar filtering excludes it, regardless of array order.
        records=[]
        for i in range(count):
            opened=end-duration*(count-1-i)
            price=4050.+i*.15
            records.append({
                "time":int(opened.timestamp()),"open":price,
                "high":price+1,"low":price-1,"close":price+.3,
                "tick_volume":100+i})
        return records

    def order_calc_profit(self,kind,symbol,volume,start,end):
        return (1 if kind==0 else -1)*(end-start)*volume*100.

    def order_calc_margin(self,kind,symbol,volume,price):
        return 200.*volume


class FakeSnapshotBroker(MT5ShadowReadOnly):
    def __init__(self,mt5,snap):
        super().__init__(mt5)
        self.test_snapshot=snap

    def snapshot(self,symbol,*,observed_at_utc,**kwargs):
        return replace(self.test_snapshot,observed_at_utc=observed_at_utc)


class FixedAnalyzer:
    def __init__(self,both=False):
        self.both=both

    def analyze(self,s):
        first=ShadowSetup("GOLD_OR_ADX20_SHADOW_V1",
                          "BUY","closed_bar_breakout",10.,2.,360)
        if self.both:
            return (first,ShadowSetup("GOLD_VWAP_ADX25_SHADOW_V1",
                                     "BUY","vwap",10.,1.5,180))
        return (first,)


class PaperBookTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.base=Path(self.t.name)
        self.journal=ShadowJournal(self.base/"journal")
        self.book=ShadowPaperBook(self.base/"paper",self.journal)

    def tearDown(self):
        self.t.cleanup()

    def position(self,sig=None):
        sig=sig or signal()
        return PaperPosition(
            signal_id=sig.event_id,symbol=sig.symbol,side=sig.side,
            entry_at_utc=OBS,exit_deadline_utc=OBS+timedelta(hours=3),
            entry_price=4100.2,sl_price=4090.2,tp_price=4120.2,
            volume=.02,account_currency="USD",initial_risk_account=20.,
            costs_verified=True,contract_verified=True)

    def test_minimum_lot_volume_is_never_forced_above_risk_budget(self):
        api=FakeMT5();adapter=MT5ShadowReadOnly(api)
        s=signal();snap=snapshot()
        with self.assertRaisesRegex(ValueError,"paper_risk_below_minimum"):
            adapter.build_position(s,snap,stop_distance=10.,reward_ratio=2.,
                                   holding_minutes=180,risk_budget_account=5.)
        good=adapter.build_position(s,snap,stop_distance=10.,reward_ratio=2.,
                                    holding_minutes=180,risk_budget_account=20.)
        self.assertAlmostEqual(good.volume,.02)
        self.assertAlmostEqual(good.initial_risk_account,20.)
        self.assertFalse(good.costs_verified) # commission not attested

    def test_buy_uses_ask_and_stop_exit_uses_actual_bid_when_gapped(self):
        s=signal();self.journal.append(s)
        pos=self.position(s)
        self.book.open(pos)
        self.assertEqual(len(self.book.pending()),1)
        profit=lambda p,px:(px-p.entry_price)*p.volume*100.
        first=self.book.on_quote(ObservedQuote(s.symbol,OBS+timedelta(minutes=1),
                         4100.1,4100.3),profit_at_exit=profit)
        self.assertFalse(first)
        close=self.book.on_quote(ObservedQuote(s.symbol,OBS+timedelta(minutes=2),
                         4088.,4088.5),profit_at_exit=profit)
        self.assertEqual(len(close),1)
        self.assertEqual(close[0].reason,"SL")
        self.assertAlmostEqual(close[0].exit_price,4088.)
        self.assertLess(close[0].net_r,-1.)
        self.assertEqual(len(self.book.pending()),0)
        self.assertFalse(self.book.on_quote(
            ObservedQuote(s.symbol,OBS+timedelta(minutes=3),4087.,4087.3),
            profit_at_exit=profit))

    def test_sell_uses_ask_to_exit(self):
        s=signal(side="SELL");self.journal.append(s)
        p=replace(self.position(s),entry_price=4100.,sl_price=4110.,
                  tp_price=4080.)
        self.book.open(p)
        profit=lambda p,px:(p.entry_price-px)*p.volume*100.
        closed=self.book.on_quote(ObservedQuote(s.symbol,OBS+timedelta(minutes=2),
                                                4085.,4111.),
                                  profit_at_exit=profit)
        self.assertEqual(len(closed),1)
        self.assertEqual(closed[0].reason,"SL")
        self.assertEqual(closed[0].exit_price,4111.)

    def test_same_group_opening_is_blocked_and_duplicate_is_idempotent(self):
        s=signal();self.journal.append(s);p=self.position(s)
        self.assertTrue(self.book.open(p))
        self.assertFalse(self.book.open(p))
        with self.assertRaisesRegex(ValueError,"paper_position_idempotency_conflict"):
            self.book.open(replace(p,entry_price=4100.1))
        second=signal(2,symbol="XAUEUR.vx")
        self.journal.append(second)
        new=replace(self.position(second),symbol=second.symbol)
        with self.assertRaisesRegex(ValueError,"paper_exposure_group_busy"):
            self.book.open(new)

    def test_restart_recovers_open_then_close_without_double_book(self):
        s=signal();self.journal.append(s)
        self.book.open(self.position(s))
        restarted=ShadowPaperBook(self.base/"paper",
            ShadowJournal(self.base/"journal"))
        self.assertEqual(len(restarted.pending()),1)
        profit=lambda p,px:(px-p.entry_price)*p.volume*100.
        restarted.on_quote(ObservedQuote(s.symbol,OBS+timedelta(hours=4),
                         4105.,4105.2),profit_at_exit=profit)
        fresh=ShadowPaperBook(self.base/"paper",ShadowJournal(self.base/"journal"))
        self.assertEqual(len(fresh.pending()),0)
        self.assertEqual(fresh.journal.close_count,1)

    def test_corrupt_paper_open_fails_closed(self):
        s=signal();self.journal.append(s);self.book.open(self.position(s))
        file=next((self.base/"paper").glob("*.json"))
        file.write_text("{incomplete",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"paper_book_corrupt"):
            ShadowPaperBook(self.base/"paper",self.journal)

    def test_unverified_risk_and_invalid_order_geometry_rejected(self):
        s=signal();self.journal.append(s)
        p=self.position(s)
        for changed in (replace(p,sl_price=4102.),
                        replace(p,initial_risk_account=float("nan")),
                        replace(p,volume=0)):
            with self.assertRaises(ValueError):
                self.book.open(changed)
        self.assertEqual(len(self.book.pending()),0)


class AdapterAndCycleTests(unittest.TestCase):
    def test_readonly_adapter_filters_current_lookahead_bar_and_stale_quote(self):
        api=FakeMT5()
        adapter=MT5ShadowReadOnly(api)
        got=adapter.snapshot("XAUUSD.vx",observed_at_utc=OBS,
                             m5_count=5,h1_count=5,h4_count=5)
        self.assertEqual(len(got.m5),5)
        self.assertTrue(all(x.closed_at_utc<=OBS for x in got.m5))
        self.assertEqual(got.account_currency,"USD")
        api.time=OBS-timedelta(minutes=3)
        with self.assertRaisesRegex(ValueError,"stale_or_future"):
            adapter.snapshot("XAUUSD.vx",observed_at_utc=OBS,
                             m5_count=5,h1_count=5,h4_count=5)

    def test_account_currency_change_is_fail_closed_for_profit(self):
        api=FakeMT5();adapter=MT5ShadowReadOnly(api)
        s=signal()
        p=adapter.build_position(s,snapshot(),stop_distance=10.,reward_ratio=2.,
                                 holding_minutes=180,risk_budget_account=20.)
        api.currency="USC"
        with self.assertRaisesRegex(ValueError,"broker_account_currency_changed"):
            adapter.profit_account(p,4088.)

    def test_paper_cycle_logs_only_new_closed_bar_and_recovers_after_restart(self):
        api=FakeMT5();snap=snapshot()
        broker=FakeSnapshotBroker(api,snap)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            journal=ShadowJournal(root/"journal")
            book=ShadowPaperBook(root/"paper",journal)
            obj=MT5ShadowCycle(
                broker=broker,journal=journal,paper_book=book,
                risk_governor=RiskGovernor(per_trade_default=.02),
                strategy_version="frozen-20261001",frozen_at_utc=FREEZE,
                initial_paper_balance_account=1000.,
                analyst=FixedAnalyzer())
            first=obj.run_once("XAUUSD.vx",observed_at_utc=OBS,
                               research_news_clear=True)
            self.assertEqual(first.accepted_paper_positions,1)
            self.assertEqual(first.live_order_count,0)
            self.assertEqual(len(book.pending()),1)
            second=obj.run_once("XAUUSD.vx",observed_at_utc=OBS+timedelta(seconds=10),
                                research_news_clear=True)
            self.assertEqual(second.accepted_paper_positions,0)
            self.assertEqual(journal.signal_count,1)
            broker.test_snapshot=replace(snap,bid=4088.,ask=4088.2)
            closed=obj.run_once("XAUUSD.vx",observed_at_utc=OBS+timedelta(seconds=25),
                                research_news_clear=True)
            self.assertEqual(closed.closed_paper_positions,1)
            self.assertEqual(journal.close_count,1)
            self.assertLess(closed.paper_account_balance,1000.)
            recovered=ShadowPaperBook(root/"paper",ShadowJournal(root/"journal"))
            self.assertEqual(len(recovered.pending()),0)

    def test_intraday_drawdown_is_latched_after_paper_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            journal=ShadowJournal(root/"journal")
            book=ShadowPaperBook(root/"paper",journal)
            # Synthetic closed ledger is sufficient to isolate the
            # drawdown calculation (order/fill tests are separate).
            book._opened.update({"loss":object(),"recovery":object()})
            for key,when,pnl in (
                ("loss",datetime(2026,10,12,9,tzinfo=UTC),-120.),
                ("recovery",datetime(2026,10,12,10,tzinfo=UTC),200.),
            ):
                journal._closes["close-"+key]=SimpleNamespace(
                    signal_id=key,final_close=True,closed_at_utc=when,
                    gross_pnl_account=pnl,commission_account=0.,
                    swap_account=0.,slippage_cost_account=0.)
            obj=MT5ShadowCycle(
                broker=FakeSnapshotBroker(FakeMT5(),snapshot()),
                journal=journal,paper_book=book,
                risk_governor=RiskGovernor(),strategy_version="test-only",
                frozen_at_utc=FREEZE,initial_paper_balance_account=1000.,
                analyst=FixedAnalyzer())
            balance,peak,daily,total=obj._balance(
                datetime(2026,10,12,12,tzinfo=UTC))
            self.assertAlmostEqual(balance,1080.)
            self.assertAlmostEqual(peak,1080.)
            self.assertAlmostEqual(daily,.12)
            self.assertAlmostEqual(total,.12)
            _,_,next_day,_=obj._balance(
                datetime(2026,10,13,8,tzinfo=UTC))
            self.assertEqual(next_day,0.)

    def test_virtual_paper_margin_not_subsidized_by_large_real_mt5_balance(self):
        class ExcessiveMarginMT5(FakeMT5):
            def order_calc_margin(self,kind,symbol,volume,price):
                return 60000.*volume

        api=ExcessiveMarginMT5()
        api.margin_free=10000.
        broker=FakeSnapshotBroker(api,snapshot())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            journal=ShadowJournal(root/"journal")
            obj=MT5ShadowCycle(
                broker=broker,journal=journal,
                paper_book=ShadowPaperBook(root/"paper",journal),
                risk_governor=RiskGovernor(per_trade_default=.02),
                strategy_version="frozen-paper-cap",frozen_at_utc=FREEZE,
                initial_paper_balance_account=1000.,
                analyst=FixedAnalyzer())
            report=obj.run_once("XAUUSD.vx",observed_at_utc=OBS,
                                research_news_clear=True)
            self.assertEqual(report.accepted_paper_positions,0)
            self.assertEqual(report.rejected_or_wait_signals,1)
            self.assertEqual(next(iter(journal._signals.values())).reason,
                             "paper_risk_or_margin_below_minimum_broker_lot")
            self.assertEqual(journal.close_count,0)

    def test_no_external_news_clearance_creates_rejection_not_position(self):
        api=FakeMT5();broker=FakeSnapshotBroker(api,snapshot())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            journal=ShadowJournal(root/"journal")
            obj=MT5ShadowCycle(
                broker=broker,journal=journal,
                paper_book=ShadowPaperBook(root/"paper",journal),
                risk_governor=RiskGovernor(),strategy_version="frozen-v1",
                frozen_at_utc=FREEZE,initial_paper_balance_account=1000.,
                analyst=FixedAnalyzer())
            rep=obj.run_once("XAUUSD.vx",observed_at_utc=OBS)
            self.assertEqual(rep.accepted_paper_positions,0)
            self.assertEqual(rep.rejected_or_wait_signals,1)
            logged=next(iter(journal._signals.values()))
            self.assertEqual(logged.reason,"news_clearance_not_verified")
            self.assertFalse(logged.news_blackout)  # unknown != verified news

    def test_multi_strategy_same_gold_group_never_opens_two(self):
        api=FakeMT5();broker=FakeSnapshotBroker(api,snapshot())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            journal=ShadowJournal(root/"journal")
            book=ShadowPaperBook(root/"paper",journal)
            obj=MT5ShadowCycle(
                broker=broker,journal=journal,paper_book=book,
                risk_governor=RiskGovernor(per_trade_default=.02),
                strategy_version="frozen-v1",
                frozen_at_utc=FREEZE,
                initial_paper_balance_account=1000.,
                analyst=FixedAnalyzer(both=True))
            result=obj.run_once("XAUUSD.vx",observed_at_utc=OBS,
                                research_news_clear=True)
            self.assertEqual(result.accepted_paper_positions,1)
            self.assertEqual(result.rejected_or_wait_signals,1)
            self.assertEqual(len(book.pending()),1)

    def test_paper_book_does_not_contain_broker_order_actions(self):
        # A deliberate code-surface regression: adapter exposes reads only.
        for name in ("order_send","positions_close","place_order","execute_order"):
            self.assertFalse(hasattr(MT5ShadowReadOnly,name))


if __name__ == "__main__":
    unittest.main()
