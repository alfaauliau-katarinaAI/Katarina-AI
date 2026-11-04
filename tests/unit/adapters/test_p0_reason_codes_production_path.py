"""ERR-TEST: P0 reason codes on the canonical observer path that had no literal test (REASON_CODE_INDEX).

Each test drives the real function into the failure and asserts the stable code, so a log line can be
traced code -> source -> test. No broker, no network, no orders.
"""
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from katarina.adapters.automatic_connection import (
    BoundLocalBroker, ConnectionConfig, ConnectionUnavailable, cloud_factory, run_connected, verify_identity)
from katarina.intelligence.broker.causal_broker_quotes import server_epoch_to_utc
from katarina.intelligence.broker.observer_universe import ObserverUniverse, load_universe, select_symbols


def config(**kwargs):
    return ConnectionConfig(123, "Test-Demo", **kwargs)


class Native:
    """Minimal terminal double: read-only identity, optional failures."""
    def __init__(self, *, connect=True, explode=None):
        self.connect, self.explode, self.shutdowns = connect, explode, 0

    def initialize(self, *args):
        return self.connect

    def shutdown(self):
        self.shutdowns += 1

    def terminal_info(self):
        if self.explode == "terminal_info":
            raise OSError("pipe closed with secret detail")
        return SimpleNamespace(connected=True, trade_allowed=False)

    def account_info(self):
        return SimpleNamespace(login=123, server="Test-Demo", trade_mode=0)

    def symbol_info_tick(self, symbol):
        if self.explode == "symbol_info_tick":
            raise OSError("server said: token=abc")
        return SimpleNamespace(time=1, time_msc=1000, bid=1.0, ask=1.1)


class CausalQuoteCodes(unittest.TestCase):
    def test_unverified_shift_and_invalid_server_epoch(self):
        for shift in (None, 2.0, 15, -13, True):
            with self.subTest(shift=shift), self.assertRaisesRegex(ValueError, "^BROKER_CLOCK_SHIFT_UNVERIFIED$"):
                server_epoch_to_utc(1_700_000_000, shift)
        for epoch in (0, -5, math.nan, math.inf, "1700000000", None):
            with self.subTest(epoch=epoch), self.assertRaisesRegex(ValueError, "^BROKER_SERVER_EPOCH_INVALID$"):
                server_epoch_to_utc(epoch, 2)
        self.assertEqual(server_epoch_to_utc(1_700_007_200, 2), 1_700_000_000.0)


class ObserverUniverseCodes(unittest.TestCase):
    def test_invalid_core_symbols_and_rotating_slots(self):
        for core in ((), ("EURUSD.vx", "EURUSD.vx"), ("bad symbol",), ["EURUSD.vx"]):
            with self.subTest(core=core), self.assertRaisesRegex(ValueError, "^INVALID_OBSERVER_CORE_SYMBOLS$"):
                ObserverUniverse(core)
        for slots in (-1, 11, True, 1.0):
            with self.subTest(slots=slots), self.assertRaisesRegex(ValueError, "^INVALID_OBSERVER_ROTATING_SLOTS$"):
                ObserverUniverse(("EURUSD.vx",), slots)
        with self.assertRaisesRegex(ValueError, "^INVALID_OBSERVER_ROTATING_SLOTS$"):
            ObserverUniverse(tuple(f"S{i}" for i in range(8)), 10)  # more than 17 symbols

    def test_invalid_universe_config_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for text in ("{broken", json.dumps({"schema_version": 2, "core": ["X"]}),
                         json.dumps({"schema_version": "1", "core": ["X"]}), json.dumps([1])):
                path = Path(tmp) / "u.json"
                path.write_text(text, encoding="utf-8")
                with self.subTest(text=text), self.assertRaisesRegex(ValueError, "^INVALID_OBSERVER_UNIVERSE_CONFIG$"):
                    load_universe(path)
            with self.assertRaisesRegex(ValueError, "^INVALID_OBSERVER_UNIVERSE_CONFIG$"):
                load_universe(Path(tmp) / "missing.json")

    def test_selection_rejects_missing_catalog_bad_universe_and_bad_rotation(self):
        universe = ObserverUniverse(("EURUSD.vx", "XAUUSD.vx"), 1)
        with self.assertRaisesRegex(ValueError, "^BROKER_CATALOG_UNAVAILABLE$"):
            select_symbols(universe, None)
        with self.assertRaisesRegex(ValueError, "^INVALID_OBSERVER_UNIVERSE$"):
            select_symbols(("EURUSD.vx",), [])
        catalog = [SimpleNamespace(name="EURUSD.vx", trade_mode=4), SimpleNamespace(name="GBPUSD.vx", trade_mode=4)]
        with self.assertRaisesRegex(ValueError, "^INVALID_OBSERVER_ROTATION$"):
            select_symbols(universe, catalog, rotation=lambda budget, core: "GBPUSD.vx")
        self.assertEqual(select_symbols(universe, catalog, rotation=lambda budget, core: ["GBPUSD.vx"]),
                         (("EURUSD.vx", "GBPUSD.vx"), ("XAUUSD.vx",)))  # a missing core symbol is reported


class ConnectionCodes(unittest.TestCase):
    def test_identity_exception_is_redacted_to_identity_check_failed(self):
        with self.assertRaises(ConnectionUnavailable) as caught:
            verify_identity(Native(explode="terminal_info"), config())
        self.assertEqual(str(caught.exception), "IDENTITY_CHECK_FAILED")
        self.assertIsNone(caught.exception.__cause__)  # the secret-bearing message is dropped

    def test_reads_before_connect_and_failing_reads(self):
        bound = BoundLocalBroker(Native(), config())
        with self.assertRaisesRegex(ConnectionUnavailable, "^LOCAL_NOT_CONNECTED$"):
            bound.symbol_info_tick("EURUSD.vx")
        native = Native(explode="symbol_info_tick")
        bound = BoundLocalBroker(native, config())
        self.assertTrue(bound.initialize())
        with self.assertRaises(ConnectionUnavailable) as caught:
            bound.symbol_info_tick("EURUSD.vx")
        self.assertEqual(str(caught.exception), "LOCAL_READ_FAILED")
        self.assertTrue(bound.connection_failed)
        self.assertNotIn("token", repr(caught.exception))
        self.assertFalse(hasattr(bound, "order_send"))

    def test_cloud_route_without_url_and_offline_fallback_after_all_routes_fail(self):
        with self.assertRaisesRegex(ConnectionUnavailable, "^CLOUD_NOT_CONFIGURED$"):
            cloud_factory(config(priority=("cloud",)))

        class Brain:
            @staticmethod
            def research_once(root):
                return {"orders_submitted": 0}

            @staticmethod
            def observe_once(*args, **kwargs):
                raise AssertionError("must not observe without a verified connection")

        def failing(cfg):
            raise ConnectionUnavailable("LOCAL_CONNECT_FAILED")
        with tempfile.TemporaryDirectory() as root:
            result = run_connected(Brain, root, config=config(priority=("local",), attempts=2),
                                   factories={"local": failing})
        self.assertEqual(result["connection"]["reason"], "NO_VALID_CONFIGURED_CONNECTION")
        self.assertEqual([a["reason"] for a in result["connection"]["attempts"]],
                         ["LOCAL_CONNECT_FAILED", "LOCAL_CONNECT_FAILED"])  # bounded, no endless retry
        self.assertEqual(result["orders_submitted"], 0)
        self.assertFalse(result["connection"]["live_authorized"])
        with self.assertRaisesRegex(ValueError, "^INVALID_OBSERVER_UNIVERSE$"):
            run_connected(Brain, "unused", config=config(), universe=("EURUSD.vx",))


if __name__ == "__main__":
    unittest.main()
