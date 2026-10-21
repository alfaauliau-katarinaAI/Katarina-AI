"""Selection tests: unavailable broker instruments never poison a scan."""
import unittest
from types import SimpleNamespace

from katarina.intelligence.broker.broker_scan_universe import (
    MAJORS, CROSSES, OPTIONAL_MARKETS, MAX_SCAN_SYMBOLS,
    resolve_broker_symbols,
)


def symbol(name, mode=4):
    return SimpleNamespace(name=name, trade_mode=mode)


class BrokerScanUniverseTests(unittest.TestCase):
    def test_budget_and_priorities(self):
        self.assertEqual(len(MAJORS), 7)
        self.assertEqual(len(CROSSES), 5)
        self.assertEqual(len(OPTIONAL_MARKETS), 5)
        self.assertEqual(MAX_SCAN_SYMBOLS, 17)
        self.assertIn("XAUUSD", OPTIONAL_MARKETS)
        self.assertIn("OIL", OPTIONAL_MARKETS)
        self.assertIn("US100", OPTIONAL_MARKETS)

    def test_selects_only_broker_advertised_symbols(self):
        catalog = [symbol(x + ".vx") for x in MAJORS + CROSSES]
        catalog += [symbol("XAUUSD.vx"), symbol("BTCUSD.vx"),
                    symbol("USOIL.vx"), symbol("US30.vx"),
                    symbol("NAS100.vx"), symbol("ETHUSD.vx"),
                    symbol("DOGEUSD.vx"), symbol("JPN225.vx")]
        got = resolve_broker_symbols(catalog)
        self.assertEqual(len(got.symbols), 17)
        self.assertEqual(got.matches["OIL"], "USOIL.vx")
        self.assertEqual(got.matches["US100"], "NAS100.vx")
        self.assertEqual(got.unavailable, ())
        self.assertNotIn("ETHUSD.vx", got.symbols)

    def test_missing_optional_symbols_are_skipped(self):
        got = resolve_broker_symbols([symbol("EURUSD"), symbol("GBPJPY")])
        self.assertEqual(got.symbols, ("EURUSD", "GBPJPY"))
        self.assertEqual(got.matches["EURUSD"], "EURUSD")
        self.assertTrue(set(OPTIONAL_MARKETS).issubset(got.unavailable))

    def test_empty_broker_catalog_is_safe(self):
        got = resolve_broker_symbols([])
        self.assertEqual(got.symbols, ())
        self.assertEqual(len(got.unavailable), MAX_SCAN_SYMBOLS)

    def test_unavailable_catalog_must_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "broker_catalog_unavailable"):
            resolve_broker_symbols(None)

    def test_disabled_and_close_only_symbols_not_scanned(self):
        got = resolve_broker_symbols([symbol("EURUSD", 0),
                                      symbol("GBPUSD", 3),
                                      symbol("USDJPY", 1),
                                      symbol("XAUUSD.r", 4)])
        self.assertEqual(got.symbols, ("USDJPY", "XAUUSD.r"))
        self.assertIn("EURUSD", got.unavailable)
        self.assertIn("GBPUSD", got.unavailable)

    def test_alias_preference_and_one_broker_symbol_per_market(self):
        got = resolve_broker_symbols([symbol("NAS100.vx"),
                                      symbol("US100.vx"),
                                      symbol("US100"),
                                      symbol("USTEC.vx"),
                                      symbol("UKOIL.vx"),
                                      symbol("XTIUSD.vx")])
        self.assertEqual(got.matches["US100"], "US100")
        self.assertEqual(got.matches["OIL"], "XTIUSD.vx")
        self.assertEqual(got.symbols.count("US100"), 1)
        self.assertNotIn("NAS100.vx", got.symbols)

    def test_broker_suffix_and_no_false_alias(self):
        got = resolve_broker_symbols([symbol("EURUSDm"),
                                      symbol("GBPUSD.raw"),
                                      symbol("BTCUSDT"),
                                      symbol("NAS1000"),
                                      symbol("US30C"),
                                      symbol("XAUUSD-ecn")])
        self.assertEqual(got.matches["EURUSD"], "EURUSDm")
        self.assertEqual(got.matches["GBPUSD"], "GBPUSD.raw")
        self.assertEqual(got.matches["US30"], "US30C")
        self.assertEqual(got.matches["XAUUSD"], "XAUUSD-ecn")
        self.assertIn("BTCUSD", got.unavailable)
        self.assertIn("US100", got.unavailable)

    def test_catalog_order_does_not_change_choice(self):
        catalog = [symbol("EURUSD.a"), symbol("EURUSD"),
                   symbol("EURUSD.vx"), symbol("NAS100.vx")]
        self.assertEqual(resolve_broker_symbols(catalog).symbols,
                         resolve_broker_symbols(list(reversed(catalog))).symbols)


if __name__ == "__main__":
    unittest.main()
