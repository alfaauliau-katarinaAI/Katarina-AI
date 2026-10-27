"""Research-only detection of MT5 tick clock displacement from UTC.

MT5 documentation and broker implementations may disagree on timestamps.
This detects a CURRENT consistent integer-hour displacement from several
independent fresh quotes; it does NOT establish historical DST or certify
latency. No trading is permitted based on this detection.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from math import isfinite
from datetime import datetime, timezone
from typing import Mapping

@dataclass(frozen=True)
class ClockFinding:
    observed_hours_shift: int | None
    samples_considered: int
    confirming_symbols: int
    confidence_fraction: float
    suitable_for_readonly_snapshot: bool
    historical_dst_verified: bool = False
    live_execution_authorized: bool = False
    stale_symbols: tuple[str, ...] = ()

def infer_clock_shift(tick_epoch_by_symbol:Mapping[str,int],
                      observed_utc_epoch:float,
                      *,min_symbols:int=3,majority_fraction:float=.70) -> ClockFinding:
    if not isfinite(observed_utc_epoch) or min_symbols<3:
        raise ValueError("invalid_clock_inputs")
    # No fresh FX quorum is possible over this closed-market period. Previously
    # stale Friday quotes could be misread as a new -4/-7 UTC broker offset.
    utc = datetime.fromtimestamp(observed_utc_epoch, timezone.utc)
    if utc.weekday() >= 5 or (utc.weekday() == 4 and utc.hour >= 20):
        return ClockFinding(None,0,0,0.,False,
                            stale_symbols=tuple(sorted(tick_epoch_by_symbol)))
    considered=0;votes=Counter();stale=[]
    for sym,ts in tick_epoch_by_symbol.items():
        if not sym or not isinstance(ts,int) or ts<=0:continue
        considered+=1
        delta=ts-observed_utc_epoch
        hours=int(round(delta/3600))
        if not (-12<=hours<=14):
            stale.append(sym);continue
        age=observed_utc_epoch-(ts-hours*3600)
        if -15<=age<=180:
            votes[hours]+=1
        else:
            stale.append(sym)
    if considered<min_symbols or not votes:
        return ClockFinding(None,considered,0,0.,False,stale_symbols=tuple(sorted(stale)))
    hours,count=votes.most_common(1)[0]
    frac=count/sum(votes.values())
    valid=count>=min_symbols and frac>=majority_fraction
    return ClockFinding(hours if valid else None,considered,count,
                        round(frac,4),valid,stale_symbols=tuple(sorted(stale)))


def corroborate_clock_with_utc_history(
        finding: ClockFinding, raw_server_epochs: Mapping[str, int],
        historical_utc_quotes: Mapping[str, tuple], observed_utc_epoch: float,
        *, max_drift_seconds: float = 45, min_symbols: int = 3) -> bool:
    """Require a separate MT5 historical UTC tick alongside current server quotes.

    Timestamp inference alone is NOT proof: a stale weekend tick can look like
    a different timezone. The returned offset must also align with fresh
    bounded causal copy_ticks_range ticks on at least three distinct symbols.
    Neither stream alone establishes true UTC when the host OS is unsynced.
    """
    if (not finding.suitable_for_readonly_snapshot
            or finding.observed_hours_shift is None or min_symbols < 3
            or not isfinite(observed_utc_epoch)
            or not 0 < max_drift_seconds <= 90):
        return False
    confirmed = 0
    valid_history = 0
    for symbol, raw in raw_server_epochs.items():
        quote = historical_utc_quotes.get(symbol)
        if type(raw) is not int or quote is None:
            continue
        try:
            tick_utc = float(quote[2])
            bid, ask = float(quote[0]), float(quote[1])
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        if (not all(isfinite(x) for x in (tick_utc, bid, ask))
                or bid <= 0 or ask < bid
                or not 0 <= observed_utc_epoch - tick_utc <= 90):
            continue
        valid_history += 1
        server_minus_utc = raw - tick_utc
        if abs(server_minus_utc - finding.observed_hours_shift * 3600) <= max_drift_seconds:
            confirmed += 1
    # Raw latest ticks can be stale for closed/quiet symbols even while
    # three *other* symbols agree with fresh UTC history. Do not count stale
    # snapshots as a veto against the independently fresh quorum; the
    # candidate itself already required >=70% agreement among fresh votes.
    return confirmed >= min_symbols


# Canonical event-time conversion contract, recorded by the existing observer.
# This deliberately does not infer historical broker DST from today's shift.
from datetime import datetime, timedelta, timezone


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("incoming_time_requires_explicit_utc_offset")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class BrokerTimeReference:
    """Current broker clock evidence, not a timezone or a trade permission."""

    observed_at_utc: datetime
    server_shift_hours: int
    confirming_symbols: int
    confidence_fraction: float

    def as_dict(self) -> dict:
        return {
            "schema": 1,
            "canonical_market_clock": "MT5_COPY_TICKS_RANGE_TIME_MSC_UTC",
            "observed_at_utc": self.observed_at_utc.isoformat(),
            "broker_server_shift_minutes": self.server_shift_hours * 60,
            "shift_evidence": "CURRENT_MULTISYMBOL_QUOTES_ONLY",
            "confirming_symbols": self.confirming_symbols,
            "confidence_fraction": self.confidence_fraction,
            "historical_dst_verified": False,
            "external_naive_time_assumed_utc": False,
            "live_execution_authorized": False,
        }


def capture_time_reference(finding: ClockFinding, observed_at_utc: datetime) -> BrokerTimeReference:
    """Capture the offset from *this* MT5 observation, never a hard-coded UTC+3."""
    observed = _aware_utc(observed_at_utc)
    if (not finding.suitable_for_readonly_snapshot or
            finding.observed_hours_shift is None or
            finding.confirming_symbols < 3):
        raise ValueError("broker_clock_not_verified")
    return BrokerTimeReference(
        observed, finding.observed_hours_shift,
        finding.confirming_symbols, finding.confidence_fraction,
    )


@dataclass(frozen=True)
class NormalizedIncomingTime:
    """Only an MT5 historical tick can serve as a market decision timestamp."""

    utc: datetime
    source: str
    authoritative_market_event: bool
    server_wall_display_only: datetime | None

    def as_dict(self) -> dict:
        return {
            "normalized_utc": self.utc.isoformat(),
            "source": self.source,
            "authoritative_market_event": self.authoritative_market_event,
            "broker_wall_display_only": (
                self.server_wall_display_only.isoformat()
                if self.server_wall_display_only is not None else None
            ),
        }


def normalize_incoming_time(
    value: int | str | datetime,
    *,
    source: str,
    reference: BrokerTimeReference | None = None,
    received_at_utc: datetime | None = None,
) -> NormalizedIncomingTime:
    """Normalize incoming data into UTC on the MT5 historical tick timeline.

    Sources must be explicit. Broker wall timestamps are accepted only for a
    fresh CURRENT read-only snapshot, never for historical/DST conversion and
    never as independent trading-event authority. UTC already has a fixed
    meaning: the MT5 tick supplies the trusted event, not a replacement zone.
    """
    market_authority = False
    if source == "MT5_TICK_TIME_MSC_UTC":
        if type(value) is not int or not 946684800000 <= value < 4102444800000:
            raise ValueError("invalid_mt5_tick_milliseconds")
        normalized = datetime.fromtimestamp(value / 1000, timezone.utc)
        market_authority = True
    elif source == "EXPLICIT_OFFSET":
        if isinstance(value, datetime):
            normalized = _aware_utc(value)
        elif isinstance(value, str):
            try:
                normalized = _aware_utc(
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                )
            except (TypeError, ValueError) as exc:
                raise ValueError("incoming_time_requires_explicit_utc_offset") from exc
        else:
            raise ValueError("unsupported_incoming_time_type")
    elif source == "BROKER_WALL_CURRENT":
        if not isinstance(value, (datetime, str)):
            raise ValueError("unsupported_broker_wall_time_type")
        try:
            local_wall = datetime.fromisoformat(value) if isinstance(value, str) else value
        except ValueError as exc:
            raise ValueError("invalid_broker_wall_time") from exc
        if local_wall.tzinfo is not None:
            raise ValueError("broker_wall_must_be_naive")
        if reference is None or received_at_utc is None:
            raise ValueError("current_broker_clock_evidence_required")
        received = _aware_utc(received_at_utc)
        reference_age = (received - reference.observed_at_utc).total_seconds()
        if not 0 <= reference_age <= 180:
            raise ValueError("broker_clock_evidence_expired")
        normalized = (local_wall - timedelta(hours=reference.server_shift_hours)).replace(
            tzinfo=timezone.utc
        )
        data_age = (received - normalized).total_seconds()
        if not 0 <= data_age <= 180:
            raise ValueError("broker_wall_outside_verified_current_window")
    else:
        raise ValueError("unknown_or_unverifiable_timestamp_source")
    # This display conversion is diagnostic, not an MT5 historical tick source.
    # Never display an archived event with today's unverified DST offset.
    display_shift_is_current = (
        reference is not None and
        abs((normalized - reference.observed_at_utc).total_seconds()) <= 180
    )
    wall = (
        (normalized + timedelta(hours=reference.server_shift_hours)).replace(tzinfo=None)
        if display_shift_is_current else None
    )
    return NormalizedIncomingTime(normalized, source, market_authority, wall)
