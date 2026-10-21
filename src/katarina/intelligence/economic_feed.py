from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json

from katarina.intelligence.economics import EconomicEvent


@dataclass(frozen=True, slots=True)
class EconomicCalendarSnapshot:
    provider: str
    fetched_at_utc: datetime
    valid_until_utc: datetime
    events: tuple[EconomicEvent,...]


@dataclass(frozen=True, slots=True)
class EconomicFeedDecision:
    ready: bool
    blackout: bool
    stale: bool
    reason: str
    event_name: str|None
    minutes_to_event: float|None


class EconomicFeedGate:
    """Fail-closed calendar gate for scalping."""

    def assess(
        self,
        snapshot:EconomicCalendarSnapshot|None,
        *,
        now_utc:datetime,
        currencies:tuple[str,...]=("USD",),
        min_impact:int=2,
        pre_minutes:int=30,
        post_minutes:int=15,
    )->EconomicFeedDecision:
        if now_utc.tzinfo is None:now_utc=now_utc.replace(tzinfo=timezone.utc)
        if snapshot is None:
            return EconomicFeedDecision(False,True,True,"calendar_missing",None,None)
        if snapshot.valid_until_utc < now_utc or snapshot.fetched_at_utc > now_utc:
            return EconomicFeedDecision(False,True,True,"calendar_stale",None,None)
        relevant=[e for e in snapshot.events if e.impact>=min_impact and set(e.currencies)&set(currencies)]
        if not relevant:
            return EconomicFeedDecision(True,False,False,"calendar_clear",None,None)
        blocking=[e for e in relevant if -post_minutes <= (e.timestamp_utc-now_utc).total_seconds()/60 <= pre_minutes]
        event=min(blocking or relevant,key=lambda e:abs((e.timestamp_utc-now_utc).total_seconds()))
        mins=(event.timestamp_utc-now_utc).total_seconds()/60.0
        blackout=(-post_minutes)<=mins<=pre_minutes
        return EconomicFeedDecision(True,blackout,False,"economic_blackout" if blackout else "calendar_clear",event.name,mins)


class JsonEconomicCalendarAdapter:
    def parse(self,raw:str|bytes)->EconomicCalendarSnapshot:
        data=json.loads(raw)
        def dt(value:str)->datetime:
            x=datetime.fromisoformat(value.replace("Z","+00:00"))
            return x if x.tzinfo is not None else x.replace(tzinfo=timezone.utc)
        events=tuple(EconomicEvent(
            str(x["name"]),dt(str(x["timestamp_utc"])),int(x["impact"]),tuple(str(c) for c in x["currencies"])
        ) for x in data.get("events",[]))
        return EconomicCalendarSnapshot(str(data["provider"]),dt(data["fetched_at_utc"]),dt(data["valid_until_utc"]),events)
