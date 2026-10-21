"""Adaptive KATARINA risk curve and shared-account safety regression tests."""
import math
import unittest
from dataclasses import replace
from pathlib import Path

from katarina.engines.adaptive_risk import AdaptiveRiskProfile
from katarina.engines.risk import RiskGovernor, RiskRequest, RiskAction, OwnerDrawdownTracker, DrawdownMode
from katarina.engines.account_risk_state import AccountRiskCoordinator, AccountRiskStateEngine
from katarina.engines.manual_risk import SharedAccountRiskEngine
from katarina.engines.sizing import PositionSizingEngine
from katarina.engines.capital import CapitalCompoundingEngine


CONFIG=Path(__file__).resolve().parents[3]/"config"/"risk_governor_v2.json"


class AdaptiveRiskTests(unittest.TestCase):
    def setUp(self):
        self.profile=AdaptiveRiskProfile()
        self.gov=RiskGovernor.from_config(CONFIG)
        self.assertIsNotNone(self.gov.adaptive_profile)

    def test_exact_capital_tiers_decreasing(self):
        data=((100,.02),(250,.0175),(500,.015),(1000,.0125),
              (2500,.01),(10000,.0075),(50000,.005),
              (100000,.004),(250000,.003))
        for cash,expect in data:
            with self.subTest(cash=cash):
                q=self.profile.quote(active_capital_native=cash,account_currency="USD")
                self.assertAlmostEqual(q.fraction,expect)
                self.assertAlmostEqual(q.risk_cash_native,cash*expect)

    def test_log_interpolated_continuous_and_monotone(self):
        balances=(80.,100.,101.,200.,251.,700.,1200.,10000.,25000.,150000.,1000000.)
        fractions=[self.profile.quote(active_capital_native=x,account_currency="USD").fraction
                   for x in balances]
        self.assertTrue(all(a>=b for a,b in zip(fractions,fractions[1:])))
        self.assertLess(fractions[3],.02)
        self.assertGreater(fractions[3],.0175)

    def test_100_dollars_equal_10000_USC(self):
        a=self.profile.quote(active_capital_native=100.,account_currency="USD")
        b=self.profile.quote(active_capital_native=10000.,account_currency="USC")
        self.assertAlmostEqual(a.fraction,b.fraction)
        self.assertAlmostEqual(a.risk_cash_native,2.)
        self.assertAlmostEqual(b.risk_cash_native,200.)
        self.assertAlmostEqual(b.reference_cash_usd,100.)

    def test_unknown_currency_and_bad_data_fail_closed(self):
        for cur in ("",None,"EUR","USDC","XYZ"):
            with self.subTest(currency=cur),self.assertRaises(ValueError):
                self.profile.quote(active_capital_native=100,account_currency=cur)
        with self.assertRaises(ValueError):
            self.profile.quote(active_capital_native=float("nan"),account_currency="USD")
        with self.assertRaises(ValueError):
            self.profile.quote(active_capital_native=80,reference_capital_native=60,account_currency="USD")

    def test_reference_high_water_blocks_pct_increase_after_losses(self):
        x=self.profile.quote(active_capital_native=100,reference_capital_native=1000,account_currency="USD")
        self.assertAlmostEqual(x.fraction,.0125)
        self.assertAlmostEqual(x.risk_cash_native,1.25)

    def test_soft_drawdown_halves_risk_and_hard_pauses(self):
        profile=self.gov.adaptive_profile
        regular=profile.quote(active_capital_native=100.,account_currency="USD")
        soften=profile.quote(active_capital_native=100.,account_currency="USD",daily_drawdown=.051)
        self.assertAlmostEqual(soften.fraction,regular.fraction*.5)
        req=RiskRequest(None,0,0,.1,2,True,True,.10,
                        risk_capital=100,risk_reference_capital=100,account_currency="USD")
        result=self.gov.evaluate(req)
        self.assertIn(result.action,(RiskAction.APPROVE,RiskAction.REDUCE))
        self.assertGreater(result.approved_fraction,0.)

    def test_owner_caused_dd35_stops_all_new_entries_without_exception(self):
        tracker=OwnerDrawdownTracker()
        tracker.observe("2026-10-14",.20,hwm_cash=10000,reconciled=True)
        evidence=tracker.observe("2026-10-14",.40,hwm_cash=10000,
                                 owner_loss_cash=2000,reconciled=True)
        # Attribution is still reported; it no longer permits an entry.
        self.assertEqual(evidence.mode,DrawdownMode.EXTREME_SURVIVAL)
        for kind in ("NORMAL","RECOVERY_FACTOR","EXTREME_RECOVERY"):
            with self.subTest(kind=kind):
                req=RiskRequest(.01,0,.40,.1,2,True,True,.40,
                                risk_capital=6000,risk_reference_capital=10000,
                                account_currency="USD",entry_kind=kind,
                                trading_day_key="2026-10-14",
                                drawdown_authority=evidence)
                decision=self.gov.evaluate(req)
                self.assertEqual(decision.action,RiskAction.PAUSE)
                self.assertEqual(decision.approved_fraction,0)
                self.assertEqual(decision.reason,"emergency_drawdown_lock")

    def test_daily_drawdown_peak_stays_locked_after_equity_recovers(self):
        # The daily value is a peak drawdown, including floating P/L.
        req=RiskRequest(.01,0,.12,.1,2,True,True,.36,
                        risk_capital=8800,risk_reference_capital=10000,
                        account_currency="USD",entry_kind="NORMAL")
        decision=self.gov.evaluate(req)
        self.assertEqual(decision.action,RiskAction.PAUSE)
        self.assertEqual(decision.approved_fraction,0)

    def test_owner_extreme_recovery_not_a_new_entry_escape_hatch(self):
        req=RiskRequest(.01,0,.10,.1,2,True,True,.10,
                        risk_capital=9000,risk_reference_capital=10000,
                        account_currency="USD",entry_kind="EXTREME_RECOVERY")
        decision=self.gov.evaluate(req)
        self.assertEqual(decision.action,RiskAction.PAUSE)
        self.assertEqual(decision.approved_fraction,0)

    def test_katarina_caused_dd35_remains_locked_even_after_manual_loss(self):
        tracker=OwnerDrawdownTracker()
        tracker.observe("d1",.20,hwm_cash=10000,reconciled=True)
        a=tracker.observe("d1",.36,hwm_cash=10000,katarina_loss_cash=1600,reconciled=True)
        self.assertEqual(a.mode,DrawdownMode.EMERGENCY_LOCKDOWN)
        b=tracker.observe("d1",.45,hwm_cash=10000,owner_loss_cash=900,reconciled=True)
        self.assertEqual(b.mode,DrawdownMode.EMERGENCY_LOCKDOWN)
        c=tracker.observe("d2",.45,hwm_cash=10000,reconciled=True)
        self.assertEqual(c.mode,DrawdownMode.EXTREME_SURVIVAL)
        again=OwnerDrawdownTracker()
        again.restore_state(tracker.snapshot_state())
        self.assertEqual(again.observe("d2",.45,hwm_cash=10000,
                                       reconciled=True).mode,DrawdownMode.EXTREME_SURVIVAL)

    def test_katarina_lockdown_stays_closed_after_same_day_dd_recovery(self):
        tracker = OwnerDrawdownTracker()
        tracker.observe("d1", .20, hwm_cash=10000, reconciled=True)
        onset = tracker.observe("d1", .36, hwm_cash=10000,
                                katarina_loss_cash=1600, reconciled=True)
        self.assertEqual(onset.mode, DrawdownMode.EMERGENCY_LOCKDOWN)
        # Equity/balance may improve, but a same-day Katarina-caused
        # emergency must NOT automatically become new-entry permission.
        improved = tracker.observe("d1", .12, hwm_cash=10000,
                                   reconciled=True)
        self.assertEqual(improved.mode, DrawdownMode.EMERGENCY_LOCKDOWN)
        for entry_kind in ("NORMAL", "RECOVERY_FACTOR", "EXTREME_RECOVERY"):
            with self.subTest(entry_kind=entry_kind):
                req = RiskRequest(
                    .01, 0, .12, .1, 2, True, True, .12,
                    entry_kind=entry_kind,
                    risk_capital=8800, risk_reference_capital=10000,
                    account_currency="USD",
                    trading_day_key="d1", drawdown_authority=improved,
                )
                decision = self.gov.evaluate(req)
                self.assertEqual(decision.action, RiskAction.PAUSE)
                self.assertEqual(decision.approved_fraction, 0)
        # Stale/mismatched authority is not an excuse to bypass a
        # known emergency latch: fail closed until reconciled.
        stale = RiskRequest(.01, 0, .12, .1, 2, True, True, .12,
                            entry_kind="NORMAL", risk_capital=8800,
                            risk_reference_capital=10000,
                            account_currency="USD",
                            trading_day_key="d2",
                            drawdown_authority=improved)
        self.assertEqual(self.gov.evaluate(stale).action, RiskAction.PAUSE)

        # A new authenticated/reconciled broker day can EVALUATE afresh.
        next_day = tracker.observe("d2", .12, hwm_cash=10000,
                                   reconciled=True)
        self.assertEqual(next_day.mode, DrawdownMode.CAUTION)
        reevaluated = RiskRequest(
            .01, 0, .12, .1, 2, True, True, .12,
            entry_kind="NORMAL", risk_capital=8800,
            risk_reference_capital=10000, account_currency="USD",
            trading_day_key="d2", drawdown_authority=next_day,
        )
        self.assertGreater(self.gov.evaluate(reevaluated).approved_fraction, 0)

    def test_unverified_manual_attribution_never_unlocks(self):
        tracker=OwnerDrawdownTracker()
        tracker.observe("d",.20,hwm_cash=10000,reconciled=True)
        evidence=tracker.observe("d",.40,hwm_cash=10000,
                                 owner_loss_cash=2000,reconciled=False)
        self.assertEqual(evidence.mode,DrawdownMode.EMERGENCY_LOCKDOWN)
        req=RiskRequest(.01,0,.40,.1,2,True,True,.40,
                        entry_kind="EXTREME_RECOVERY",
                        trading_day_key="d",drawdown_authority=evidence)
        self.assertEqual(self.gov.evaluate(req).approved_fraction,0)

    def test_recovery_factor_only_from_23_to_35(self):
        for dd in (.23,.30,.349):
            with self.subTest(dd=dd):
                denied=self.gov.evaluate(RiskRequest(.01,0,dd,.1,2,True,True,0))
                self.assertEqual(denied.approved_fraction,0)
                allowed=self.gov.evaluate(RiskRequest(.01,0,dd,.1,2,True,True,0,
                    entry_kind="RECOVERY_FACTOR",risk_capital=100,
                    risk_reference_capital=100,account_currency="USD"))
                self.assertGreater(allowed.approved_fraction,0)

    def test_adaptive_governor_request_five_percent_reduced_to_two(self):
        r=RiskRequest(.05,0,0,.1,2,True,True,0,
                      risk_capital=100,risk_reference_capital=100,account_currency="USD")
        result=self.gov.evaluate(r)
        self.assertEqual(result.action,RiskAction.REDUCE)
        self.assertAlmostEqual(result.approved_fraction,.02)

    def test_adaptive_none_request_uses_tier(self):
        r=RiskRequest(None,0,0,.1,2,True,True,0,
                      risk_capital=10000,risk_reference_capital=10000,account_currency="USD")
        result=self.gov.evaluate(r)
        self.assertEqual(result.action,RiskAction.APPROVE)
        self.assertAlmostEqual(result.approved_fraction,.0075)

    def test_malformed_risk_evidence_fails_closed_without_exception(self):
        # Broker/adapter inputs may be malformed; the safety gate must never
        # let invalid fractions or invalid numeric types become trade approval.
        gov=RiskGovernor()
        baseline=RiskRequest(.01,0.0,0.0,.10,2.0,True,True,0.0)
        cases=(
            {"uncertainty":-.01},
            {"uncertainty":None},
            {"uncertainty":"0.10"},
            {"uncertainty":True},
            {"open_risk_fraction":1.01},
            {"drawdown_fraction":1.01},
            {"daily_drawdown_fraction":1.01},
            {"open_risk_fraction":None},
            {"expected_rr":None},
            {"expected_rr":"2"},
            {"drawdown_fraction":True},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                decision=gov.evaluate(replace(baseline,**overrides))
                self.assertEqual(decision.action,RiskAction.PAUSE)
                self.assertEqual(decision.approved_fraction,0)
                self.assertEqual(decision.reason,"invalid_risk_evidence")

    def test_unverified_account_data_never_approves(self):
        for capital,currency in ((None,"USD"),(100,None),(100,"EUR")):
            with self.subTest(capital=capital,currency=currency):
                r=RiskRequest(None,0,0,.1,2,True,True,0,
                              risk_capital=capital,account_currency=currency)
                decision=self.gov.evaluate(r)
                self.assertEqual(decision.action,RiskAction.PAUSE)
                self.assertAlmostEqual(decision.approved_fraction,0.)

    def test_open_risk_budget_and_stop_loss_gate_remain(self):
        r=RiskRequest(.03,.075,0,.1,2,True,True,0,
                      risk_capital=100,account_currency="USD")
        decision=self.gov.evaluate(r)
        self.assertEqual(decision.action,RiskAction.REDUCE)
        self.assertAlmostEqual(decision.approved_fraction,.005)
        unhealthy=RiskRequest(None,0,0,.1,2,False,True,0,
                              risk_capital=100,account_currency="USD")
        self.assertEqual(self.gov.evaluate(unhealthy).action,RiskAction.PAUSE)
        self.assertEqual(self.gov.evaluate(
            RiskRequest(None,0,.35,.1,2,True,True,0,risk_capital=100,account_currency="USD")
        ).action,RiskAction.PAUSE)

    def test_shared_account_authorize_and_reserve_with_native_currency(self):
        state=AccountRiskStateEngine()
        coord=AccountRiskCoordinator.with_adaptive_risk(state)
        p=SharedAccountRiskEngine().assess([],equity=10000)
        r=coord.authorize_and_reserve(
            p,reservation_id="r1",day_key="2026-10-11",requested_fraction=None,
            uncertainty=.1,expected_rr=2,health_ok=True,reconciled=True,
            account_currency="USC")
        self.assertTrue(r.reserved)
        self.assertAlmostEqual(r.approved_fraction,.02)
        self.assertAlmostEqual(state.reservations.total_fraction,.02)
        b=coord.authorize_and_reserve(
            p,reservation_id="r2",day_key="2026-10-11",requested_fraction=None,
            uncertainty=.1,expected_rr=2,health_ok=True,reconciled=True,
            account_currency=None)
        self.assertFalse(b.reserved)
        self.assertEqual(b.action,"PAUSE")

    def test_compounding_uses_active_capital_with_high_water(self):
        c=CapitalCompoundingEngine()
        c.observe_balance(100)
        c.observe_balance(200)
        st=AccountRiskStateEngine()
        coord=AccountRiskCoordinator.with_adaptive_risk(st,capital=c)
        p=SharedAccountRiskEngine().assess([],equity=200)
        r=coord.authorize_and_reserve(
            p,reservation_id="r1",day_key="2026-10-11",requested_fraction=None,
            uncertainty=.1,expected_rr=2,health_ok=True,reconciled=True,
            account_currency="USD")
        self.assertAlmostEqual(r.state.risk_capital,150)
        self.assertTrue(0<r.approved_fraction<.02)

    def test_minimum_volume_not_forced_above_risk_budget(self):
        sizing=PositionSizingEngine()
        # 0.01 standard lot XAU = 1 oz: a $10 stop risks $10, above $2.
        standard=sizing.size_active(active_balance=100,current_equity=100,
            risk_fraction=.02,stop_distance=10,
            value_per_price_unit_per_lot=100.,volume_min=.01,
            volume_max=50,volume_step=.01)
        self.assertFalse(standard.valid)
        self.assertEqual(standard.reason,"below_min_volume")
        # Illustrative cent contract: 1 oz/lot -> 100 USC per $1 per full lot.
        cent=sizing.size_active(active_balance=10000,current_equity=10000,
            risk_fraction=.02,stop_distance=10,
            value_per_price_unit_per_lot=100.,volume_min=.01,
            volume_max=50,volume_step=.01)
        self.assertTrue(cent.valid)
        self.assertAlmostEqual(cent.volume,.2)

if __name__=="__main__":
    unittest.main()
