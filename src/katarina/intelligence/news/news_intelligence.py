from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class NewsSource:
    source_id: str
    source_type: str
    trust_weight: float
    asset_tags: tuple[str,...]


@dataclass(frozen=True, slots=True)
class NewsItem:
    source_id: str
    published_utc: datetime
    title: str
    tags: tuple[str,...]
    impact: int
    sentiment: float = 0.0
    url: str|None = None


@dataclass(frozen=True, slots=True)
class NewsContext:
    ready: bool
    blackout: bool
    risk_score: float
    sentiment: float
    matched_items: int
    source_count: int
    reasons: tuple[str,...]


class NewsSourceRegistry:
    """Source metadata only; network adapters plug in separately."""

    def __init__(self,sources:Sequence[NewsSource]|None=None):
        self.sources={x.source_id:x for x in (sources or self.default_sources())}

    @staticmethod
    def default_sources()->tuple[NewsSource,...]:
        return (
            NewsSource("fed","CENTRAL_BANK",1.00,("USD","FX","GOLD","INDEX","RISK_SENTIMENT")),
            NewsSource("ecb","CENTRAL_BANK",1.00,("EUR","FX","INDEX")),
            NewsSource("boe","CENTRAL_BANK",1.00,("GBP","FX","INDEX")),
            NewsSource("boj","CENTRAL_BANK",1.00,("JPY","FX","INDEX")),
            NewsSource("snb","CENTRAL_BANK",1.00,("CHF","FX")),
            NewsSource("boc","CENTRAL_BANK",1.00,("CAD","FX","OIL")),
            NewsSource("rba","CENTRAL_BANK",1.00,("AUD","FX","METALS")),
            NewsSource("rbnz","CENTRAL_BANK",1.00,("NZD","FX")),
            NewsSource("bls","OFFICIAL_MACRO",1.00,("USD","FX","GOLD","INDEX","RISK_SENTIMENT")),
            NewsSource("bea","OFFICIAL_MACRO",1.00,("USD","FX","INDEX")),
            NewsSource("us_treasury","OFFICIAL_MACRO",1.00,("USD","BONDS","GOLD","INDEX")),
            NewsSource("eia","ENERGY_OFFICIAL",1.00,("ENERGY","OIL","USD")),
            NewsSource("opec","ENERGY_OFFICIAL",1.00,("ENERGY","OIL")),
            NewsSource("iea","ENERGY_OFFICIAL",.95,("ENERGY","OIL")),
            NewsSource("sec","REGULATOR",1.00,("EQUITY","CRYPTO","INDEX","USD")),
            NewsSource("cftc","REGULATOR",1.00,("FX","METALS","ENERGY","CRYPTO","USD")),
            NewsSource("reuters","NEWS_WIRE",.90,("GLOBAL",)),
            NewsSource("ap","NEWS_WIRE",.85,("GLOBAL",)),
            NewsSource("bloomberg","MARKET_NEWS",.90,("GLOBAL",)),
            NewsSource("economic_calendar","CALENDAR",.80,("GLOBAL",)),
        )

    def get(self,source_id:str)->NewsSource|None:
        return self.sources.get(source_id)


class MultiSourceNewsEngine:
    def __init__(self,registry:NewsSourceRegistry|None=None):
        self.registry=registry or NewsSourceRegistry()

    @staticmethod
    def _norm_title(title:str)->str:
        return re.sub(r"[^a-z0-9]+"," ",title.lower()).strip()

    @classmethod
    def _fingerprint(cls,item:NewsItem)->str:
        minute=int(item.published_utc.timestamp()//60)
        raw=f"{cls._norm_title(item.title)}|{minute}"
        return sha256(raw.encode()).hexdigest()

    def deduplicate(self,items:Iterable[NewsItem])->tuple[NewsItem,...]:
        best={}
        for item in items:
            fp=self._fingerprint(item)
            prior=best.get(fp)
            w=self.registry.get(item.source_id).trust_weight if self.registry.get(item.source_id) else 0.25
            pw=self.registry.get(prior.source_id).trust_weight if prior and self.registry.get(prior.source_id) else 0.0
            if prior is None or w>pw:
                best[fp]=item
        return tuple(sorted(best.values(),key=lambda x:x.published_utc))

    def assess(
        self,
        items:Sequence[NewsItem],
        *,
        exposures:Sequence[str],
        now_utc:datetime,
        freshness_minutes:int=180,
        blackout_pre_minutes:int=30,
        blackout_post_minutes:int=15,
    )->NewsContext:
        if now_utc.tzinfo is None:now_utc=now_utc.replace(tzinfo=timezone.utc)
        ex={x.upper() for x in exposures}
        dedup=self.deduplicate(items)
        matched=[]
        sources=set()
        weighted_sentiment=0.0
        weight_total=0.0
        blackout=False
        max_risk=0.0
        for item in dedup:
            age=(now_utc-item.published_utc).total_seconds()/60.0
            if age < -blackout_pre_minutes or age > freshness_minutes:
                continue
            src=self.registry.get(item.source_id)
            source_tags=set(src.asset_tags if src else ())
            item_tags={x.upper() for x in item.tags}
            global_match="GLOBAL" in source_tags
            if not (ex & item_tags or ex & source_tags or global_match):
                continue
            matched.append(item)
            sources.add(item.source_id)
            trust=src.trust_weight if src else .25
            recency=max(0.0,1.0-min(max(age,0.0),freshness_minutes)/freshness_minutes)
            risk=trust*max(0,min(3,item.impact))/3.0*(.4+.6*recency)
            max_risk=max(max_risk,risk)
            weight=max(.01,trust*recency)
            weighted_sentiment+=max(-1,min(1,item.sentiment))*weight
            weight_total+=weight
            mins_to=(item.published_utc-now_utc).total_seconds()/60.0
            if item.impact>=2 and -blackout_post_minutes<=mins_to<=blackout_pre_minutes:
                blackout=True

        if not matched:
            return NewsContext(False,True,1.0,0.0,0,0,("no_fresh_relevant_news_context",))
        sentiment=weighted_sentiment/weight_total if weight_total else 0.0
        return NewsContext(
            True,blackout,max_risk,sentiment,len(matched),len(sources),
            ("high_impact_news_blackout",) if blackout else ("news_context_ready",)
        )
