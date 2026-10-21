from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True, slots=True)
class EconomicEvent:
    name: str
    timestamp_utc: datetime
    impact: int
    currencies: tuple[str,...]

@dataclass(frozen=True, slots=True)
class EconomicContext:
    blackout: bool
    minutes_to_event: float|None
    impact: int
    reason: str

class EconomicIntelligenceEngine:
    def assess(self, events: list[EconomicEvent], *, now_utc: datetime, symbols: tuple[str,...]=("USD",), blackout_minutes: int=15) -> EconomicContext:
        if now_utc.tzinfo is None: now_utc=now_utc.replace(tzinfo=timezone.utc)
        relevant=[e for e in events if set(e.currencies)&set(symbols)]
        if not relevant: return EconomicContext(False,None,0,"no_relevant_event")
        e=min(relevant,key=lambda x:abs((x.timestamp_utc-now_utc).total_seconds()))
        mins=(e.timestamp_utc-now_utc).total_seconds()/60.0
        blackout=e.impact>=2 and abs(mins)<=blackout_minutes
        return EconomicContext(blackout,mins,e.impact,"high_impact_blackout" if blackout else "event_context")
