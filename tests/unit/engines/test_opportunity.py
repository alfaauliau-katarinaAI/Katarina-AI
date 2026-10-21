import unittest

from katarina.engines.opportunity import MarketCandidate, MultiMarketOpportunityEngine
from katarina.engines.scalper_entry import EntryMode, EntryProposal, EntrySide
from katarina.intelligence.perception.market_universe import AssetClass, TradableInstrument
from katarina.intelligence.news.news_intelligence import NewsContext


def inst(i,symbol,asset):
    return TradableInstrument(i,1,symbol,symbol,"USD","USD","USD",asset,True,True,True,True,True,True)

def proposal(score):
    return EntryProposal(True,EntrySide.BUY,EntryMode.TREND_PULLBACK,score,1-score,2.0,1.0,3,("test",))

def news(risk=.1):
    return NewsContext(True,False,risk,0,2,2,("ready",))


class OpportunityTests(unittest.TestCase):
    def test_best_market_selected_not_fixed_xauusd(self):
        c=[
            MarketCandidate(inst(1,"XAUUSD",AssetClass.METAL),proposal(.75),news(.2),2.0,.8),
            MarketCandidate(inst(2,"EURUSD",AssetClass.FOREX),proposal(.90),news(.1),.7,.95),
            MarketCandidate(inst(3,"BTCUSD",AssetClass.CRYPTO),proposal(.82),news(.3),4.0,.9),
        ]
        ranked=MultiMarketOpportunityEngine().rank(c,min_score=.4)
        self.assertEqual(ranked[0].symbol,"EURUSD")

    def test_news_blackout_excludes_market(self):
        blocked=NewsContext(True,True,.9,0,1,1,("blackout",))
        c=[MarketCandidate(inst(1,"EURUSD",AssetClass.FOREX),proposal(.95),blocked,.5,1.0)]
        self.assertEqual(MultiMarketOpportunityEngine().rank(c,min_score=.1),())

    def test_not_ready_broker_symbol_is_excluded(self):
        x=TradableInstrument(1,1,"EURUSD","EURUSD","EUR","USD","USD",AssetClass.FOREX,True,False,True,True,True,True)
        c=[MarketCandidate(x,proposal(.95),news(),.5,1.0)]
        self.assertEqual(MultiMarketOpportunityEngine().rank(c,min_score=.1),())


if __name__=="__main__": unittest.main()
