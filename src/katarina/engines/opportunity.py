from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from katarina.engines.scalper_entry import EntryProposal
from katarina.intelligence.perception.market_universe import TradableInstrument
from katarina.intelligence.news.news_intelligence import NewsContext


@dataclass(frozen=True, slots=True)
class MarketCandidate:
    instrument: TradableInstrument
    proposal: EntryProposal
    news: NewsContext
    spread_bps: float
    liquidity_score: float
    correlation_penalty: float = 0.0


@dataclass(frozen=True, slots=True)
class RankedOpportunity:
    symbol: str
    instrument_id: int
    spec_revision: int
    score: float
    proposal: EntryProposal
    asset_class: str
    reasons: tuple[str,...]


class MultiMarketOpportunityEngine:
    """Ranks valid opportunities across the broker-ready symbol universe."""

    def rank(self,candidates:Sequence[MarketCandidate],*,limit:int=5,min_score:float=.55)->tuple[RankedOpportunity,...]:
        out=[]
        for c in candidates:
            if not c.instrument.ready:
                continue
            if not c.proposal.valid:
                continue
            if not c.news.ready or c.news.blackout:
                continue
            liquidity=max(0.0,min(1.0,c.liquidity_score))
            spread_penalty=max(0.0,min(.35,c.spread_bps/100.0))
            corr=max(0.0,min(.50,c.correlation_penalty))
            news_penalty=max(0.0,min(.45,c.news.risk_score*.35))
            score=c.proposal.score*(.65+.35*liquidity)-spread_penalty-corr-news_penalty
            if score<min_score:
                continue
            out.append(RankedOpportunity(
                c.instrument.canonical_symbol,c.instrument.instrument_id,c.instrument.spec_revision,score,c.proposal,
                c.instrument.asset_class.value,
                ("broker_ready","entry_valid","news_ready","portfolio_adjusted"),
            ))
        out.sort(key=lambda x:(-x.score,x.symbol))
        return tuple(out[:max(0,limit)])
