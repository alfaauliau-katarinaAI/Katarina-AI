import unittest

from katarina.contracts.runtime import EventEnvelope
from katarina.engines.manual_risk import (
    Kat1SharedAccountRiskRuntime,
    PositionRiskInput,
    SharedAccountRiskEngine,
    SharedAccountRiskTracker,
    SymbolRiskSpec,
    PositionPnLChange,
    BrokerPnLReconciler,
)
from katarina.engines.risk import RiskAction, RiskGovernor
from katarina.validation.engine import (
    ValidationDisposition,
    ValidationResult,
)


SPEC = SymbolRiskSpec(tick_size=0.01, tick_value_loss=1.0)


def manual(
    position_id="m1",
    *,
    origin="MANUAL_MOBILE",
    side="BUY",
    volume=.5,
    open_price=2000.0,
    current_price=2000.0,
    stop_loss=1994.0,
    broker_loss_to_sl=None,
    symbol_spec=SPEC,
):
    return PositionRiskInput(
        position_id=position_id,
        origin=origin,
        side=side,
        volume=volume,
        open_price=open_price,
        current_price=current_price,
        stop_loss=stop_loss,
        symbol_spec=symbol_spec,
        broker_loss_to_sl=broker_loss_to_sl,
    )


def accepted(topic, payload):
    return ValidationResult(
        EventEnvelope(topic,payload),
        ValidationDisposition.ACCEPT,
        (),
        1,
    )


class ManualAccountRiskTests(unittest.TestCase):
    def setUp(self):
        self.engine=SharedAccountRiskEngine()
        self.gov=RiskGovernor(max_open_risk=.08,hard_per_trade=.05)

    def test_manual_trade_risk_is_included(self):
        a=self.engine.assess([manual()],equity=10000)
        self.assertAlmostEqual(a.external_risk_cash,300.0)
        self.assertAlmostEqual(a.external_risk_fraction,.03)
        self.assertAlmostEqual(a.open_risk_fraction,.03)
        self.assertFalse(a.has_unbounded_risk)

    def test_kat1_numeric_origin_and_side_are_supported(self):
        a=self.engine.assess([manual(origin=3,side=1)],equity=10000)
        self.assertAlmostEqual(a.external_risk_fraction,.03)
        self.assertEqual(a.position_risks[0].origin,"MANUAL_MOBILE")

    def test_three_percent_manual_plus_five_percent_katarina_fills_eight_percent_cap(self):
        a=self.engine.assess([manual()],equity=10000)
        d=self.gov.evaluate_account(
            a,requested_fraction=.05,drawdown_fraction=0,daily_drawdown_fraction=0,
            uncertainty=.1,expected_rr=2,health_ok=True,reconciled=True,
        )
        self.assertEqual(d.action,RiskAction.APPROVE)
        self.assertAlmostEqual(d.approved_fraction,.05)

    def test_six_percent_manual_reduces_new_katarina_risk_to_two_percent(self):
        a=self.engine.assess([manual(volume=1.0)],equity=10000)
        d=self.gov.evaluate_account(
            a,requested_fraction=.05,drawdown_fraction=0,daily_drawdown_fraction=0,
            uncertainty=.1,expected_rr=2,health_ok=True,reconciled=True,
        )
        self.assertEqual(d.action,RiskAction.REDUCE)
        self.assertAlmostEqual(d.approved_fraction,.02)

    def test_manual_without_sl_blocks_new_automated_risk(self):
        a=self.engine.assess([manual(stop_loss=None)],equity=10000)
        d=self.gov.evaluate_account(
            a,requested_fraction=.01,drawdown_fraction=0,daily_drawdown_fraction=0,
            uncertainty=.1,expected_rr=2,health_ok=True,reconciled=True,
        )
        self.assertEqual(d.action,RiskAction.PAUSE)
        self.assertEqual(d.reason,"unbounded_open_risk")

    def test_partial_close_reduces_risk_immediately(self):
        before=self.engine.assess([manual(volume=.5)],equity=10000)
        after=self.engine.assess([manual(volume=.25)],equity=10000)
        self.assertAlmostEqual(after.open_risk_cash,before.open_risk_cash/2)

    def test_tracker_upsert_partial_close_and_remove(self):
        tracker=SharedAccountRiskTracker()
        tracker.upsert(manual(position_id="ticket",volume=.5))
        self.assertAlmostEqual(tracker.assess(equity=10000).open_risk_fraction,.03)
        tracker.upsert(manual(position_id="ticket",volume=.25))
        self.assertAlmostEqual(tracker.assess(equity=10000).open_risk_fraction,.015)
        tracker.remove("ticket")
        self.assertEqual(tracker.assess(equity=10000).position_count,0)

    def test_multiple_manual_origins_are_aggregated(self):
        a=self.engine.assess([
            manual("desktop",origin="MANUAL_DESKTOP",volume=.25),
            manual("mobile",origin="MANUAL_MOBILE",volume=.25),
            manual("web",origin="MANUAL_WEB",volume=.25),
        ],equity=10000)
        self.assertEqual(a.external_position_count,3)
        self.assertAlmostEqual(a.external_risk_cash,450.0)

    def test_foreign_ea_and_unknown_are_risk_aware(self):
        a=self.engine.assess([
            manual("foreign",origin="FOREIGN_EA",volume=.25),
            manual("unknown",origin="UNKNOWN",volume=.25),
        ],equity=10000)
        self.assertEqual(a.external_position_count,2)

    def test_katarina_and_manual_both_count_toward_total_open_risk(self):
        a=self.engine.assess([
            manual("manual",origin="MANUAL_MOBILE",volume=.5),
            manual("katarina",origin="KATARINA",volume=.25),
        ],equity=10000)
        self.assertAlmostEqual(a.external_risk_cash,300.0)
        self.assertAlmostEqual(a.open_risk_cash,450.0)

    def test_broker_ordercalcprofit_value_is_preferred(self):
        a=self.engine.assess([manual(broker_loss_to_sl=275.0,symbol_spec=None)],equity=10000)
        self.assertAlmostEqual(a.open_risk_cash,275.0)

    def test_open_manual_position_rejects_invalid_broker_loss_evidence(self):
        for loss in (0, -1, float("nan"), float("inf"), "bad", True):
            with self.subTest(broker_loss_to_sl=loss):
                assessment=self.engine.assess([
                    manual(broker_loss_to_sl=loss, symbol_spec=None)
                ],equity=10000)
                self.assertTrue(assessment.has_unbounded_risk)
                decision=self.gov.evaluate_account(
                    assessment,requested_fraction=.01,drawdown_fraction=0,
                    daily_drawdown_fraction=0,uncertainty=.1,expected_rr=2,
                    health_ok=True,reconciled=True,
                )
                self.assertEqual(decision.action,RiskAction.PAUSE)

    def test_open_manual_position_rejects_corrupt_tick_spec(self):
        for spec in (
            SymbolRiskSpec(float("nan"),1.0),
            SymbolRiskSpec(float("inf"),1.0),
            SymbolRiskSpec(.01,float("nan")),
            SymbolRiskSpec(.01,float("inf")),
            SymbolRiskSpec("bad",1.0),
            SymbolRiskSpec(.01,"bad"),
        ):
            with self.subTest(spec=spec):
                assessment=self.engine.assess([
                    manual(symbol_spec=spec)
                ],equity=10000)
                self.assertTrue(assessment.has_unbounded_risk)
                self.assertEqual(self.gov.evaluate_account(
                    assessment,requested_fraction=.01,drawdown_fraction=0,
                    daily_drawdown_fraction=0,uncertainty=.1,expected_rr=2,
                    health_ok=True,reconciled=True,
                ).action,RiskAction.PAUSE)

    def test_manual_position_calculated_loss_overflow_never_approves(self):
        assessment=self.engine.assess([
            manual(volume=1e300,symbol_spec=SymbolRiskSpec(1e-300,1e300))
        ],equity=10000)
        self.assertTrue(assessment.has_unbounded_risk)

    def test_protected_position_zero_risk_is_still_valid(self):
        assessment=self.engine.assess([
            manual(current_price=2010,stop_loss=2011,broker_loss_to_sl=0)
        ],equity=10000)
        self.assertFalse(assessment.has_unbounded_risk)
        self.assertEqual(assessment.open_risk_cash,0)

    def test_missing_symbol_spec_without_broker_calc_blocks(self):
        a=self.engine.assess([manual(symbol_spec=None,broker_loss_to_sl=None)],equity=10000)
        self.assertTrue(a.has_unbounded_risk)

    def test_trailing_stop_above_entry_still_counts_giveback_from_current_equity(self):
        a=self.engine.assess([
            manual(open_price=2000,current_price=2010,stop_loss=2005,volume=.5)
        ],equity=10000)
        self.assertAlmostEqual(a.open_risk_cash,250.0)

    def test_stop_beyond_current_market_has_zero_remaining_downside(self):
        a=self.engine.assess([
            manual(open_price=2000,current_price=2010,stop_loss=2011,volume=.5)
        ],equity=10000)
        self.assertAlmostEqual(a.open_risk_cash,0.0)

    def test_sell_risk(self):
        a=self.engine.assess([
            manual(side="SELL",open_price=2000,current_price=2000,stop_loss=2006,volume=.5)
        ],equity=10000)
        self.assertAlmostEqual(a.open_risk_cash,300.0)

    def test_invalid_equity_fails_closed(self):
        a=self.engine.assess([manual()],equity=0)
        self.assertTrue(a.has_unbounded_risk)

    def test_broker_pnl_owner_floating_loss_reconciles_without_realized_close(self):
        result=BrokerPnLReconciler.reconcile(
            previous_equity=8000,current_equity=6000,external_cash_flow=0,
            changes=(PositionPnLChange("manual","MANUAL_MOBILE",0,-2000),))
        self.assertTrue(result.balanced)
        self.assertAlmostEqual(result.owner_loss_cash,2000)
        self.assertEqual(result.katarina_loss_cash,0)
        self.assertIn("not_broker_authenticated",result.reason)

    def test_broker_pnl_manual_realized_loss_included(self):
        result=BrokerPnLReconciler.reconcile(
            previous_equity=10000,current_equity=7000,external_cash_flow=0,
            changes=(PositionPnLChange("closed_manual","MANUAL_WEB",-3000,0),))
        self.assertTrue(result.balanced)
        self.assertAlmostEqual(result.owner_loss_cash,3000)

    def test_broker_pnl_deposit_not_counted_as_owner_profit(self):
        result=BrokerPnLReconciler.reconcile(
            previous_equity=10000,current_equity=11000,external_cash_flow=2000,
            changes=(PositionPnLChange("manual","MANUAL_DESKTOP",-1000,0),))
        self.assertTrue(result.balanced)
        self.assertAlmostEqual(result.owner_loss_cash,1000)

    def test_broker_pnl_missing_fee_or_unknown_origin_fails_closed(self):
        missing=BrokerPnLReconciler.reconcile(
            previous_equity=10000,current_equity=8900,external_cash_flow=0,
            changes=(PositionPnLChange("manual","MANUAL_WEB",-1000,0),))
        self.assertFalse(missing.balanced)
        self.assertAlmostEqual(missing.unexplained_cash,-100)
        unknown=BrokerPnLReconciler.reconcile(
            previous_equity=10000,current_equity=9000,external_cash_flow=0,
            changes=(PositionPnLChange("manual","MANUAL_WEB",-1000,0),
                     PositionPnLChange("foreign","FOREIGN_EA",100,-100)))
        self.assertFalse(unknown.balanced)
        self.assertIn("unknown_or_foreign",unknown.reason)

    def test_broker_pnl_multiple_origins_not_misattributed(self):
        result=BrokerPnLReconciler.reconcile(
            previous_equity=10000,current_equity=7200,external_cash_flow=0,
            changes=(PositionPnLChange("manual","MANUAL_MOBILE",-2000,0),
                     PositionPnLChange("katarina","KATARINA",-800,0)))
        self.assertTrue(result.balanced)
        self.assertAlmostEqual(result.owner_loss_cash,2000)
        self.assertAlmostEqual(result.katarina_loss_cash,800)

    def test_broker_pnl_duplicate_or_nan_rejected(self):
        item=PositionPnLChange("position1","MANUAL_MOBILE",-100,0)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            BrokerPnLReconciler.reconcile(
                previous_equity=10000,current_equity=9800,external_cash_flow=0,
                changes=(item,item))
        with self.assertRaisesRegex(ValueError,"nonfinite"):
            BrokerPnLReconciler.reconcile(
                previous_equity=10000,current_equity=9800,external_cash_flow=0,
                changes=(PositionPnLChange("p","KATARINA",float("nan"),0),))

    def test_runtime_consumes_only_accepted_kat1_state(self):
        rt=Kat1SharedAccountRiskRuntime()
        rt.observe(accepted("account.state",{
            "equity_units":1000000,
            "account_currency_digits":2,
        }))
        rt.observe(accepted("symbol.spec",{
            "instrument_id":1,
            "spec_revision":1,
            "price_scale":2,
            "volume_scale":2,
            "tick_size_units":1,
            "tick_value_loss_units":100,
        }))
        rt.observe(accepted("position.state",{
            "position_identifier":77,
            "instrument_id":1,
            "spec_revision":1,
            "change_kind":1,
            "origin_class":3,
            "side":1,
            "volume_units":50,
            "open_price_units":200000,
            "current_price_units":200000,
            "sl_units":199400,
        }))
        a=rt.assessment()
        self.assertAlmostEqual(a.equity,10000.0)
        self.assertAlmostEqual(a.external_risk_fraction,.03)

        rejected=ValidationResult(
            EventEnvelope("position.state",{
                "position_identifier":77,
                "change_kind":2,
            }),
            ValidationDisposition.REJECT,
            (),
            2,
        )
        self.assertFalse(rt.observe(rejected))
        self.assertEqual(rt.assessment().position_count,1)

    def test_runtime_remove_closes_manual_risk(self):
        rt=Kat1SharedAccountRiskRuntime()
        rt.observe(accepted("account.state",{"equity_units":1000000,"account_currency_digits":2}))
        rt.observe(accepted("symbol.spec",{
            "instrument_id":1,"spec_revision":1,"price_scale":2,"volume_scale":2,
            "tick_size_units":1,"tick_value_loss_units":100,
        }))
        rt.observe(accepted("position.state",{
            "position_identifier":77,"instrument_id":1,"spec_revision":1,
            "change_kind":1,"origin_class":2,"side":1,"volume_units":50,
            "open_price_units":200000,"current_price_units":200000,"sl_units":199400,
        }))
        rt.observe(accepted("position.state",{"position_identifier":77,"change_kind":2}))
        self.assertEqual(rt.assessment().position_count,0)


if __name__=="__main__":
    unittest.main()
