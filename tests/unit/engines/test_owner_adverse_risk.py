"""Synthetic adverse-case checks for the Owner's provisional 35% stop.

These prove pure RiskGovernor logic, NOT broker fills, slippage, gap handling,
emergency liquidation ability, or LIVE authorization.
"""
import unittest

from katarina.engines.risk import (
    DrawdownAuthority, DrawdownMode, RiskAction, RiskGovernor, RiskRequest,
)


class OwnerAdverseRiskTests(unittest.TestCase):
    def setUp(self):
        self.gov=RiskGovernor()

    def request(self, *, per_trade=.05, total_dd=.0, daily_dd=.0, open_risk=0.,
                entry_kind="NORMAL", health=True, reconciled=True,
                unlimited=False, authority=None):
        return RiskRequest(
            requested_fraction=per_trade,
            open_risk_fraction=open_risk,
            drawdown_fraction=total_dd,
            uncertainty=.1, expected_rr=2.,
            health_ok=health,reconciled=reconciled,
            daily_drawdown_fraction=daily_dd,
            unbounded_open_risk=unlimited,
            entry_kind=entry_kind,
            trading_day_key="broker-day",
            drawdown_authority=authority,
        )

    def test_owner_caused_dd35_stops_every_entry_kind(self):
        a=DrawdownAuthority("broker-day",DrawdownMode.EXTREME_SURVIVAL,
                            .35,True,True)
        for kind in ("NORMAL","RECOVERY_FACTOR","EXTREME_RECOVERY"):
            with self.subTest(kind=kind):
                result=self.gov.evaluate(self.request(total_dd=.35,daily_dd=.35,
                                                      entry_kind=kind,authority=a))
                self.assertEqual(result.action,RiskAction.PAUSE)
                self.assertEqual(result.approved_fraction,0.)

    def test_equity_bounce_does_not_unlock_daily_peak_drawdown(self):
        result=self.gov.evaluate(self.request(total_dd=.05,daily_dd=.35))
        self.assertEqual(result.action,RiskAction.PAUSE)

    def test_worse_than_threshold_remains_blocked(self):
        for dd in (.351,.50,.80,.99):
            with self.subTest(dd=dd):
                result=self.gov.evaluate(self.request(total_dd=dd,daily_dd=dd))
                self.assertEqual(result.approved_fraction,0.)

    def test_unknown_open_loss_cannot_pass(self):
        result=self.gov.evaluate(self.request(unlimited=True))
        self.assertEqual(result.action,RiskAction.PAUSE)

    def test_missing_broker_health_or_reconciliation_cannot_pass(self):
        for health,reconciled in ((False,True),(True,False),(False,False)):
            with self.subTest(health=health,reconciled=reconciled):
                result=self.gov.evaluate(self.request(health=health,reconciled=reconciled))
                self.assertEqual(result.action,RiskAction.PAUSE)

    def test_unverified_10_percent_is_not_granted(self):
        result=self.gov.evaluate(self.request(per_trade=.10))
        self.assertEqual(result.action,RiskAction.REDUCE)
        self.assertLessEqual(result.approved_fraction,.05)

    def test_open_portfolio_risk_cap_stops_more_exposure(self):
        result=self.gov.evaluate(self.request(open_risk=.08))
        self.assertEqual(result.approved_fraction,0.)

    def test_bad_nan_drawdown_evidence_is_rejected(self):
        result=self.gov.evaluate(self.request(daily_dd=float("nan")))
        self.assertEqual(result.action,RiskAction.PAUSE)


if __name__=="__main__":
    unittest.main()
