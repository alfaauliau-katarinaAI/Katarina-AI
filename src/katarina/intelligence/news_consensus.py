from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from katarina.intelligence.news_intelligence import NewsItem, NewsSourceRegistry


@dataclass(frozen=True, slots=True)
class SourceConsensus:
    ready: bool
    consensus: float
    independent_sources: int
    official_source_present: bool
    conflict: bool
    reason: str


class NewsConsensusEngine:
    """Separates official evidence from repeated media reporting."""

    OFFICIAL_TYPES={"CENTRAL_BANK","OFFICIAL_MACRO","ENERGY_OFFICIAL","REGULATOR"}

    def __init__(self,registry:NewsSourceRegistry|None=None):
        self.registry=registry or NewsSourceRegistry()

    def assess(
        self,
        items:Sequence[NewsItem],
        *,
        min_nonofficial_sources:int=2,
    )->SourceConsensus:
        if not items:
            return SourceConsensus(False,0.0,0,False,False,"no_sources")
        sources={x.source_id for x in items}
        official=False
        weighted_pos=0.0
        weighted_neg=0.0
        trust_total=0.0
        for item in items:
            src=self.registry.get(item.source_id)
            trust=src.trust_weight if src else .25
            trust_total+=trust
            if src and src.source_type in self.OFFICIAL_TYPES:
                official=True
            if item.sentiment>0:
                weighted_pos+=trust*min(1.0,item.sentiment)
            elif item.sentiment<0:
                weighted_neg+=trust*min(1.0,-item.sentiment)
        conflict=weighted_pos>.20 and weighted_neg>.20
        independent=len(sources)
        if not official and independent<min_nonofficial_sources:
            return SourceConsensus(False,.25,independent,False,conflict,"insufficient_independent_sources")
        agreement=1.0
        if conflict:
            agreement=max(0.0,1.0-min(weighted_pos,weighted_neg)/max(weighted_pos,weighted_neg))
        breadth=min(1.0,independent/3.0)
        trust=min(1.0,trust_total/max(1.0,float(independent)))
        consensus=max(0.0,min(1.0,.45*trust+.35*breadth+.20*agreement))
        if conflict:
            consensus*=.65
        return SourceConsensus(True,consensus,independent,official,conflict,"consensus_ready")
