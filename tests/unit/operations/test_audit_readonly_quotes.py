"""Offline safety tests: no broker, network, or real account required."""
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.mt5.audit_readonly_quotes import observe, quote_snapshot  # noqa: E402

NOW = 1_800_000_000_000
SPEC = SimpleNamespace(trade_contract_size=100, trade_tick_size=0.01,
                       volume_min=0.01, volume_step=0.01, point=0.01)


def tick(*, millis=NOW - 1000, bid=2700., ask=2700.1):
    return SimpleNamespace(time_msc=millis, bid=bid, ask=ask)


class FakeMt5:
    ACCOUNT_TRADE_MODE_REAL = 2
    ACCOUNT_TRADE_MODE_DEMO = 0
    ACCOUNT_TRADE_MODE_CONTEST = 1

    def __init__(self, *, good=True, connected=True, account=True):
        self.good = good
        self.connected = connected
        self.account = account
        self.called = []

    def initialize(self, **kwargs):
        self.called.append('initialize')
        return self.good

    def terminal_info(self):
        self.called.append('terminal_info')
        return SimpleNamespace(connected=self.connected)

    def account_info(self):
        self.called.append('account_info')
        return (SimpleNamespace(trade_mode=0, currency='USC', login=12345678,
                                server='private.example', balance=987654)
                if self.account else None)

    def symbol_info(self, symbol):
        self.called.append('symbol_info')
        return SPEC

    def symbol_info_tick(self, symbol):
        self.called.append('symbol_info_tick')
        return tick()

    def shutdown(self):
        self.called.append('shutdown')


class ReadOnlyQuotesTests(unittest.TestCase):
    def test_fresh_bid_ask_and_valid_spec_observed_but_not_trade_ready(self):
        mt5 = FakeMt5()
        out = observe(mt5, symbols=('XAUUSD.vx',), now_ms=NOW, max_age_ms=180000)
        self.assertEqual(out['result'], 'PASS_SINGLE_READ_ONLY_OBSERVATION')
        self.assertEqual(out['quotes'][0]['decision'], 'OBSERVED_ONLY')
        self.assertEqual(out['account_denomination'], 'USC')
        self.assertEqual(out['account_mode'], 'demo')
        self.assertFalse(out['live_execution_enabled'])
        self.assertFalse(out['strategy_validated'])
        self.assertEqual(mt5.called[-1], 'shutdown')
        self.assertNotIn('order_send', mt5.called)
        serialized = str(out)
        for private in ('12345678', 'private.example', '987654'):
            self.assertNotIn(private, serialized)

    def test_stale_future_crossed_and_invalid_contract_all_wait(self):
        invalid = [
            (SPEC, tick(millis=NOW - 3600000), 'stale_quote'),
            (SPEC, tick(millis=NOW + 3600000), 'future_dated_quote'),
            (SPEC, tick(bid=2701, ask=2700), 'invalid_bid_ask_or_timestamp'),
            (SimpleNamespace(trade_contract_size=100, trade_tick_size=0,
                             volume_min=0.01, volume_step=0.01), tick(), 'invalid_broker_contract_spec'),
            (SPEC, tick(millis=10**20), 'invalid_quote_timestamp'),
            (SPEC, None, 'quote_unavailable'),
            (None, None, 'symbol_metadata_unavailable'),
        ]
        for info, quote, reason in invalid:
            with self.subTest(reason=reason):
                actual = quote_snapshot('XAUUSD.vx', info, quote,
                                        now_ms=NOW, max_age_ms=180000)
                self.assertEqual(actual['decision'], 'WAIT')
                self.assertEqual(actual['reason'], reason)

    def test_causal_utc_reader_ignores_broker_local_raw_tick_and_no_fallback(self):
        fake = FakeMt5()
        def historical_reader(_mt5, _symbol, _as_of, *, lookback_seconds,server_shift_hours):
            self.assertEqual(server_shift_hours,0)
            self.assertEqual(lookback_seconds, 180)
            return (2700., 2700.1, (NOW - 1000) / 1000)
        out = observe(fake, symbols=('XAUUSD.vx',), now_ms=NOW,
                      max_age_ms=180000, historical_quote_reader=historical_reader,
                      server_shift_hours=0)
        self.assertEqual(out['result'], 'PASS_SINGLE_READ_ONLY_OBSERVATION')
        self.assertEqual(out['quotes'][0]['quote_source'], 'MT5_HISTORICAL_SERVER_CONVERTED_UTC_BID_ASK_READONLY')
        self.assertNotIn('symbol_info_tick', fake.called)

        missing = FakeMt5()
        blocked = observe(missing, symbols=('XAUUSD.vx',), now_ms=NOW,
                          max_age_ms=180000,
                          historical_quote_reader=lambda *_a, **_kw: None,
                          server_shift_hours=0)
        self.assertEqual(blocked['result'], 'WAIT_INSUFFICIENT_BROKER_EVIDENCE')
        self.assertEqual(blocked['quotes'][0]['reason'], 'quote_unavailable')
        self.assertNotIn('symbol_info_tick', missing.called)

    def test_empty_or_duplicate_symbol_selection_waits_without_connection(self):
        for symbols in ((), ('XAUUSD.vx', 'XAUUSD.vx')):
            fake = FakeMt5()
            out = observe(fake, symbols=symbols, now_ms=NOW, max_age_ms=180000)
            self.assertEqual(out['reason'], 'invalid_symbol_selection')
            self.assertEqual(fake.called, [])

    def test_disconnected_missing_account_or_failed_init_wait(self):
        for args in ({'good': False}, {'connected': False}, {'account': False}):
            with self.subTest(args=args):
                fake = FakeMt5(**args)
                result = observe(fake, symbols=('XAUUSD.vx',), now_ms=NOW,
                                 max_age_ms=180000)
                self.assertEqual(result['result'], 'WAIT_INSUFFICIENT_BROKER_EVIDENCE')
                self.assertFalse(result['live_risk_ready'])
                self.assertEqual(fake.called[-1], 'shutdown')


if __name__ == '__main__':
    unittest.main()
