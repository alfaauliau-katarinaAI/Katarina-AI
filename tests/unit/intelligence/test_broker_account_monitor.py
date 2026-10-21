"""Read-only MT5 broker account snapshot, with fail-closed unknowns."""
import unittest
from datetime import datetime,timezone
from types import SimpleNamespace
from katarina.intelligence.broker.broker_account_monitor import inspect_broker_account

NOW=datetime(2026,10,15,5,tzinfo=timezone.utc)


class Broker:
    ACCOUNT_TRADE_MODE_DEMO=0
    def __init__(self,*,trade_allowed=False,positions=(),orders=()):
        self._terminal=SimpleNamespace(connected=True,trade_allowed=trade_allowed)
        self._account=SimpleNamespace(balance=1000.,equity=950.,
            margin=0.,margin_free=950.,trade_mode=0,login=123456)
        self._positions=positions;self._orders=orders
    def terminal_info(self):return self._terminal
    def account_info(self):return self._account
    def positions_get(self):return self._positions
    def orders_get(self):return self._orders


class BrokerAccountReadOnlyTests(unittest.TestCase):
    def test_real_snapshot_uses_no_account_identifiers_or_balances(self):
        state=inspect_broker_account(Broker(),observed_at_utc=NOW)
        self.assertEqual(state["status"],"READONLY_ACCOUNT_OBSERVED_NO_RISK_CLEARANCE")
        self.assertEqual(state["positions_count"],0)
        self.assertEqual(state["pending_orders_count"],0)
        self.assertTrue(state["algo_trading_off"])
        self.assertFalse(state["risk_budget_approved"])
        self.assertFalse(state["correlated_portfolio_risk_verified"])
        self.assertFalse(state["live_execution_authorized"])
        for secret in ("login","balance","equity","margin_free","password"):
            self.assertNotIn(secret,state)

    def test_enabled_trading_never_marked_healthy(self):
        state=inspect_broker_account(
            Broker(trade_allowed=True),observed_at_utc=NOW)
        self.assertEqual(state["status"],"BROKER_ACCOUNT_SNAPSHOT_DEGRADED")
        self.assertFalse(state["algo_trading_off"])

    def test_unreadable_position_book_is_not_zero_positions(self):
        state=inspect_broker_account(
            Broker(positions=None,orders=None),observed_at_utc=NOW)
        self.assertEqual(state["status"],"BROKER_ACCOUNT_SNAPSHOT_DEGRADED")
        self.assertIsNone(state["positions_count"])
        self.assertIsNone(state["pending_orders_count"])

    def test_open_positions_detect_missing_sl_without_risk_approval(self):
        state=inspect_broker_account(Broker(
            positions=(SimpleNamespace(sl=0.0),SimpleNamespace(sl=104.))),
            observed_at_utc=NOW)
        self.assertEqual(state["positions_count"],2)
        self.assertEqual(state["positions_missing_protective_sl"],1)
        self.assertFalse(state["risk_budget_approved"])

    def test_observation_needs_utc_aware_datetime(self):
        with self.assertRaisesRegex(ValueError,"timezone_aware"):
            inspect_broker_account(Broker(),observed_at_utc=datetime(2026,10,15))
