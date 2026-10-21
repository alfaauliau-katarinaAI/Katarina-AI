import unittest

from katarina.contracts.runtime import EventEnvelope
from katarina.intelligence.perception.market_universe import (
    AssetClass,
    BrokerMarketUniverse,
    MarketTaxonomy,
    SymbolNewsExposureResolver,
    TradableInstrument,
)
from katarina.validation.engine import ValidationDisposition, ValidationResult


def accepted(topic,payload):
    return ValidationResult(EventEnvelope(topic,payload),ValidationDisposition.ACCEPT,(),1)


class MarketUniverseTests(unittest.TestCase):
    def test_taxonomy_major_markets(self):
        self.assertEqual(MarketTaxonomy.infer("XAUUSD","XAU","USD"),AssetClass.METAL)
        self.assertEqual(MarketTaxonomy.infer("EURUSD","EUR","USD"),AssetClass.FOREX)
        self.assertEqual(MarketTaxonomy.infer("USOIL","USD","USD"),AssetClass.ENERGY)
        self.assertEqual(MarketTaxonomy.infer("BTCUSD","BTC","USD"),AssetClass.CRYPTO)
        self.assertEqual(MarketTaxonomy.infer("US500","USD","USD"),AssetClass.INDEX)

    def test_broker_universe_requires_accepted_ready_session(self):
        u=BrokerMarketUniverse()
        u.observe(accepted("symbol.spec",{
            "instrument_id":1,"spec_revision":1,"canonical_symbol":"EURUSD",
            "broker_symbol":"EURUSD.a","base_currency":"EUR","profit_currency":"USD",
            "margin_currency":"USD","trade_mode_raw":4,
        }))
        self.assertEqual(u.instruments(),())
        u.observe(accepted("session.state",{
            "instrument_id":1,"session_open":1,"fresh_tick":1,"terminal_connected":1,
            "terminal_trade_allowed":1,"symbol_trade_allowed":1,
        }))
        items=u.instruments()
        self.assertEqual(len(items),1)
        self.assertTrue(items[0].ready)
        self.assertEqual(items[0].asset_class,AssetClass.FOREX)

    def test_news_exposure_resolver(self):
        def instrument(symbol,asset,base,profit):
            return TradableInstrument(1,1,symbol,symbol,base,profit,profit,asset,True,True,True,True,True,True)
        self.assertTrue({"EUR","USD","FX"}.issubset(set(SymbolNewsExposureResolver.exposures(instrument("EURUSD",AssetClass.FOREX,"EUR","USD")))))
        self.assertTrue({"GOLD","METALS","USD"}.issubset(set(SymbolNewsExposureResolver.exposures(instrument("XAUUSD",AssetClass.METAL,"XAU","USD")))))
        self.assertTrue({"OIL","ENERGY","USD"}.issubset(set(SymbolNewsExposureResolver.exposures(instrument("USOIL",AssetClass.ENERGY,"USD","USD")))))
        self.assertTrue({"BTC","CRYPTO","USD"}.issubset(set(SymbolNewsExposureResolver.exposures(instrument("BTCUSD",AssetClass.CRYPTO,"BTC","USD")))))


if __name__=="__main__": unittest.main()
