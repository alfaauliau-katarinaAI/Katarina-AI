import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.intelligence.shadow.shadow_journal import (
    ShadowJournal, ShadowSignal, ShadowTradeClose,
)
from katarina.intelligence.shadow.strategy_drift import StrategyDriftMonitor
from katarina.intelligence.shadow.strategy_evidence import ForwardStrategyEvidenceGate

UTC = timezone.utc
FREEZE = datetime(2026, 5, 31, tzinfo=UTC)
AS_OF = datetime(2026, 10, 11, tzinfo=UTC)


def make_signal(i, *, at=None, action="ACCEPT", version="frozen-v1"):
    observed = at or (datetime(2026, 6, 1, 9, tzinfo=UTC) + timedelta(days=2*i))
    return ShadowSignal(
        event_id=f"signal-{i}", symbol="XAUUSD", strategy_id="GOLD_OR",
        strategy_version=version, observed_at_utc=observed,
        frozen_at_utc=FREEZE,
        m5_closed_at_utc=observed-timedelta(minutes=5),
        h1_closed_at_utc=observed-timedelta(hours=1),
        h4_closed_at_utc=observed-timedelta(hours=4),
        side="BUY" if action == "ACCEPT" else "WAIT",
        action=action, reason="closed_signal",
        broker_session_open=True, data_fresh=True, news_blackout=False,
        spread_price_units=.12, spec_revision=1,
    )


def make_close(i, s=None, *, pnl=110., commission=-1., slippage=1.,
               provenance="PAPER", final=True, deal_ids=()):
    signal=s or make_signal(i)
    return ShadowTradeClose(
        event_id=f"close-{i}", signal_id=signal.event_id,
        recorded_at_utc=signal.observed_at_utc+timedelta(minutes=45),
        entry_at_utc=signal.observed_at_utc+timedelta(minutes=5),
        closed_at_utc=signal.observed_at_utc+timedelta(minutes=40),
        gross_pnl_account=pnl+2., commission_account=commission,
        swap_account=0., slippage_cost_account=slippage,
        initial_risk_account=100., account_currency="USD",
        provenance=provenance, broker_deal_ids=tuple(deal_ids),
        costs_reconciled=True, contract_verified=True, final_close=final,
    )


class ShadowJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.journal=ShadowJournal(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_restart_replays_completed_paper_trade_without_duplicate_count(self):
        signal=make_signal(1)
        close=make_close(1, signal)
        self.assertTrue(self.journal.append(signal))
        self.assertTrue(self.journal.append(close))
        self.assertFalse(self.journal.append(signal))
        self.assertFalse(self.journal.append(close))
        fresh=ShadowJournal(self.tmp.name)
        self.assertEqual(fresh.signal_count,1)
        self.assertEqual(fresh.close_count,1)
        results=fresh.forward_outcomes(symbol="XAUUSD",strategy_id="GOLD_OR",
                                       strategy_version="frozen-v1")
        self.assertEqual(len(results),1)
        self.assertAlmostEqual(results[0].net_r,1.10)
        self.assertTrue(results[0].costs_verified)

    def test_no_trade_rejections_are_remembered_but_never_counted_as_deals(self):
        signal=make_signal(1,action="NO_TRADE")
        self.journal.append(signal)
        self.assertEqual(self.journal.signal_count,1)
        self.assertEqual(len(self.journal.forward_outcomes(
            symbol="XAUUSD",strategy_id="GOLD_OR",
            strategy_version="frozen-v1")),0)
        with self.assertRaisesRegex(ValueError,"close_of_unaccepted_signal"):
            self.journal.append(make_close(1,signal))

    def test_partial_close_is_counted_once_after_final_reconciliation(self):
        s=make_signal(2)
        self.journal.append(s)
        partial=replace(make_close(2,s,pnl=30.),event_id="partial-2",
                        final_close=False)
        final=replace(make_close(2,s,pnl=75.),event_id="final-2",
                      closed_at_utc=s.observed_at_utc+timedelta(minutes=41),
                      recorded_at_utc=s.observed_at_utc+timedelta(minutes=46),
                      final_close=True)
        self.journal.append(partial)
        self.assertEqual(len(self.journal.forward_outcomes(
            symbol="XAUUSD",strategy_id="GOLD_OR",strategy_version="frozen-v1")),0)
        self.journal.append(final)
        new=ShadowJournal(self.tmp.name)
        results=new.forward_outcomes(
            symbol="XAUUSD",strategy_id="GOLD_OR",strategy_version="frozen-v1")
        self.assertEqual(len(results),1)
        self.assertAlmostEqual(results[0].net_r,1.05)
        with self.assertRaisesRegex(ValueError,"close_after_final"):
            new.append(replace(final,event_id="late-2"))

    def test_broker_deal_ids_required_and_cannot_be_reused(self):
        s=make_signal(3)
        self.journal.append(s)
        with self.assertRaisesRegex(ValueError,"broker_deal_ids_required"):
            self.journal.append(make_close(3,s,provenance="BROKER_DEAL"))
        self.journal.append(make_close(3,s,provenance="BROKER_DEAL",deal_ids=("42",)))
        other=make_signal(4)
        self.journal.append(other)
        with self.assertRaisesRegex(ValueError,"broker_deal_already_counted"):
            self.journal.append(make_close(4,other,provenance="BROKER_DEAL",
                                           deal_ids=("42",)))

    def test_new_signal_rejects_lookahead_and_untradeable_acceptance(self):
        s=make_signal(10)
        cases=(
            replace(s,m5_closed_at_utc=s.observed_at_utc+timedelta(minutes=5)),
            replace(s,news_blackout=True),
            replace(s,data_fresh=False),
            replace(s,broker_session_open=False),
        )
        for event in cases:
            with self.subTest(event=event):
                with self.assertRaises(ValueError):
                    self.journal.append(event)
        self.assertEqual(self.journal.signal_count,0)

    def test_invalid_cost_or_trade_timeline_cannot_touch_disk(self):
        s=make_signal(5)
        self.journal.append(s)
        t=make_close(5,s)
        for invalid in (
            replace(t,slippage_cost_account=-.01),
            replace(t,initial_risk_account=0),
            replace(t,gross_pnl_account=float("nan")),
            replace(t,closed_at_utc=s.observed_at_utc),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.journal.append(invalid)
        self.assertEqual(self.journal.close_count,0)
        self.assertEqual(len(list(Path(self.tmp.name).glob("*.json"))),1)

    def test_conflicting_duplicate_id_is_rejected(self):
        s=make_signal(6)
        self.journal.append(s)
        with self.assertRaisesRegex(ValueError,"idempotency_conflict"):
            self.journal.append(replace(s,reason="different_past"))

    def test_corrupt_file_rejected_on_restart_not_ignored(self):
        self.journal.append(make_signal(7))
        file=next(Path(self.tmp.name).glob("*.json"))
        content=json.loads(file.read_text())
        content["payload"]["strategy_version"]="tampered"
        file.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError,"journal_corrupt_or_incomplete"):
            ShadowJournal(self.tmp.name)

    def test_incomplete_cost_reconciliation_is_not_trusted_forward_evidence(self):
        s=make_signal(8)
        self.journal.append(s)
        self.journal.append(replace(make_close(8,s),costs_reconciled=False))
        outcome=self.journal.forward_outcomes(
            symbol="XAUUSD",strategy_id="GOLD_OR",strategy_version="frozen-v1")[0]
        self.assertFalse(outcome.costs_verified)
        self.assertEqual(ForwardStrategyEvidenceGate(bootstrap_draws=300).assess(
            symbol="XAUUSD",strategy_id="GOLD_OR",frozen_at_utc=FREEZE,
            as_of_utc=AS_OF,trades=(outcome,)
        ).reason,"unverified_forward_provenance_or_costs")


class StrategyDriftJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.journal=ShadowJournal(self.tmp.name)
        self.monitor=StrategyDriftMonitor(
            gate=ForwardStrategyEvidenceGate(bootstrap_draws=300))
        for i in range(60):
            signal=make_signal(i)
            self.journal.append(signal)
            result=make_close(i,signal,pnl=110. if i%4!=3 else -35.)
            self.journal.append(result)

    def tearDown(self):
        self.tmp.cleanup()

    def review(self, journal=None, **kwargs):
        return self.monitor.review(
            journal=journal or self.journal,symbol="XAUUSD",
            strategy_id="GOLD_OR",strategy_version="frozen-v1",
            frozen_at_utc=FREEZE,as_of_utc=kwargs.get("now",AS_OF))

    def test_cost_verified_paper_history_is_risk_review_only(self):
        v=self.review()
        self.assertEqual(v.state,"RISK_REVIEW_ONLY")
        self.assertGreater(v.risk_multiplier,0)
        self.assertFalse(v.live_execution_authorized)

    def test_frozen_strategy_mismatch_is_no_trade(self):
        self.assertEqual(self.monitor.review(
            journal=self.journal,symbol="XAUUSD",strategy_id="GOLD_OR",
            strategy_version="frozen-v1",frozen_at_utc=FREEZE-timedelta(days=1),
            as_of_utc=AS_OF).reason,"mixed_or_changed_strategy_freeze")

    def test_stale_evidence_halts_even_if_old_results_were_profitable(self):
        v=self.review(now=AS_OF+timedelta(days=35))
        self.assertEqual(v.state,"NO_TRADE")
        self.assertEqual(v.reason,"stale_strategy_evidence")

    def test_recent_bad_runs_halt_before_larger_trade(self):
        for i in range(55,60):
            old=self.journal._closes[f"close-{i}"]
            # A second journal is reconstructed with the modified *original*
            # evidence instead of mutating append-only data in place.
        with tempfile.TemporaryDirectory() as path:
            altered=ShadowJournal(path)
            for i in range(60):
                s=make_signal(i)
                altered.append(s)
                loss = i>=55 or i%4==3
                altered.append(make_close(i,s,pnl=-35. if loss else 110.))
            v=self.review(journal=altered)
            self.assertEqual(v.state,"NO_TRADE")
            self.assertIn(v.reason,(
                "recent_loss_streak","negative_recent_net_expectancy",
                "poor_forward_expectancy_or_drawdown",
                "forward_confidence_interval_includes_zero",
            ))

    def test_excessive_cost_r_halts_even_with_positive_pnl(self):
        with tempfile.TemporaryDirectory() as path:
            altered=ShadowJournal(path)
            for i in range(60):
                s=make_signal(i)
                altered.append(s)
                base=110. if i%4!=3 else -35.
                close=make_close(i,s,pnl=base)
                if i==59:
                    close=replace(close,slippage_cost_account=28.,
                                  gross_pnl_account=base+29.)
                altered.append(close)
            v=self.review(journal=altered)
            self.assertEqual(v.reason,"excessive_verified_trading_cost")
            self.assertEqual(v.risk_multiplier,0)


if __name__ == "__main__":
    unittest.main()
