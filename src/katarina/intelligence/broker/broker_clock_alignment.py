"""Research-only detection of MT5 tick clock displacement from UTC.

MT5 documentation and broker implementations may disagree on timestamps.
This validates CURRENT quotes using reviewed independent offset evidence and host NTP trust.
Quote agreement alone does NOT establish freshness, historical DST or latency. No trading is permitted based on this detection.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
from typing import Mapping


@dataclass(frozen=True)
class HostClockTrust:
    """Mockable host NTP clock trust status."""
    trusted: bool
    time_basis: str  # 'TRUSTED_HOST_NTP' or 'UNTRUSTED_OR_DESYNC'
    reason: str  # 'NTP_SYNCHRONIZED', 'NO_TRUSTED_HOST_CLOCK'
    last_sync_utc: datetime | None = None
    skew_seconds: float = 0.0
    observed_at_utc: datetime | None = None
    monotonic_seconds: float | None = None
    source: str | None = None
    stratum: int | None = None
    source_sha256: str | None = None


def query_windows_w32tm(now: datetime | None = None, *, max_sync_age_seconds=14400.) -> HostClockTrust:
    """Use measured Windows status, never synthesize a successful sync."""
    from katarina.intelligence.broker.host_clock_probe import inspect_windows_host_clock
    probe = inspect_windows_host_clock(max_sync_age_seconds=max_sync_age_seconds)
    return HostClockTrust(
        probe.trusted, "TRUSTED_HOST_NTP" if probe.trusted else "UNTRUSTED_OR_DESYNC",
        probe.reason, probe.last_sync_utc,
        probe.offset_seconds if probe.offset_seconds is not None else float("inf"),
        probe.observed_utc, probe.monotonic_seconds, probe.source, probe.stratum,
        probe.raw_sha256,
    )


def inspect_host_clock(now: datetime | None = None, *, max_sync_age_seconds=14400.) -> HostClockTrust:
    """Probe measured OS status; fixtures must patch callers only in test scope."""
    return query_windows_w32tm(now, max_sync_age_seconds=max_sync_age_seconds)


@dataclass(frozen=True)
class ClockEvidence:
    """Operator-reviewed independent evidence; never minted from quote votes alone."""
    shift_hours: int
    valid_from: datetime
    valid_until: datetime
    source: str
    source_sha256: str
    broker_server_sha256: str
    time_basis: str = 'INDEPENDENT_UTC'

    def valid_at(self, now: datetime, broker_server: str | None, source_bytes: bytes | None = None) -> bool:
        basic_ok = (
            type(self.shift_hours) is int and -12 <= self.shift_hours <= 14
            and self.source in ('BROKER_DOCUMENT', 'INDEPENDENT_CLOCK_OBSERVATION', 'TRUSTED_HOST_NTP')
            and isinstance(self.source_sha256, str)
            and re.fullmatch(r'[0-9a-f]{64}', self.source_sha256) is not None
            and isinstance(broker_server, str) and bool(broker_server)
            and self.broker_server_sha256 == sha256(broker_server.encode('utf-8')).hexdigest()
            and isinstance(self.valid_from, datetime) and self.valid_from.tzinfo is not None
            and isinstance(self.valid_until, datetime) and self.valid_until.tzinfo is not None
            and self.valid_from <= now < self.valid_until
        )
        if not basic_ok:
            return False

        if self.source == 'BROKER_DOCUMENT':
            if source_bytes is None or sha256(source_bytes).hexdigest() != self.source_sha256:
                return False

        return True


def load_clock_evidence(path: str | Path) -> ClockEvidence | None:
    """Read a private reviewed configuration; missing/invalid evidence stays closed."""
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
            return None
        return ClockEvidence(
            shift_hours=data['shift_hours'],
            valid_from=datetime.fromisoformat(data['valid_from']),
            valid_until=datetime.fromisoformat(data['valid_until']),
            source=data['source'],
            source_sha256=data['source_sha256'],
            broker_server_sha256=data['broker_server_sha256'],
            time_basis=data.get('time_basis', 'INDEPENDENT_UTC'),
        )
    except (OSError, ValueError, TypeError, KeyError):
        return None


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
    evidence: ClockEvidence | None = None
    broker_server: str | None = None
    observed_utc_epoch: float | None = None
    reason: str = 'CLOCK_NOT_EVALUATED'


def infer_clock_shift(
    tick_epoch_by_symbol: Mapping[str, int],
    observed_utc_epoch: float,
    *,
    min_symbols: int = 3,
    majority_fraction: float = .70,
    evidence: ClockEvidence | None = None,
    broker_server: str | None = None,
    host_trust: HostClockTrust | None = None,
    previous_shift: int | None = None,
    require_host_trust: bool = False,
    require_evidence: bool = False,
    source_bytes: bytes | None = None,
) -> ClockFinding:
    if (not isfinite(observed_utc_epoch) or type(min_symbols) is not int or min_symbols < 3
            or not .70 <= majority_fraction <= 1):
        raise ValueError("invalid_clock_inputs")

    now = datetime.fromtimestamp(observed_utc_epoch, timezone.utc)
    ticks = {s: t for s, t in tick_epoch_by_symbol.items() if s and type(t) is int and t > 0}

    if require_host_trust:
        if host_trust is None:
            host_trust = inspect_host_clock(now)
        if host_trust is None or not isinstance(host_trust, HostClockTrust) or host_trust.trusted is not True:
            return ClockFinding(
                None, len(ticks), 0, 0., False,
                stale_symbols=tuple(sorted(ticks.keys())),
                evidence=evidence, broker_server=broker_server,
                observed_utc_epoch=observed_utc_epoch,
                reason='NO_TRUSTED_HOST_CLOCK'
            )
        sync_age = ((now - host_trust.last_sync_utc).total_seconds()
                    if isinstance(host_trust.last_sync_utc, datetime)
                    and host_trust.last_sync_utc.tzinfo is not None else float("inf"))
        if (host_trust.time_basis != "TRUSTED_HOST_NTP" or not 0 <= sync_age <= 14400
                or type(host_trust.skew_seconds) not in (int, float)
                or not isfinite(host_trust.skew_seconds) or abs(host_trust.skew_seconds) > 1):
            return ClockFinding(None, len(ticks), 0, 0., False,
                                reason="NO_TRUSTED_HOST_CLOCK")

    closed = (now.weekday() == 4 and now.hour >= 20 or now.weekday() == 5
              or now.weekday() == 6 and now.hour < 21)
    if closed:
        return ClockFinding(None, len(ticks), 0, 0., False, stale_symbols=tuple(sorted(ticks.keys())),
                            evidence=evidence, broker_server=broker_server,
                            observed_utc_epoch=observed_utc_epoch, reason='FX_MARKET_CLOSED')

    if require_evidence or evidence is not None:
        if not isinstance(evidence, ClockEvidence):
            return ClockFinding(None, len(ticks), 0, 0., False, stale_symbols=tuple(sorted(ticks.keys())),
                                evidence=None, broker_server=broker_server,
                                observed_utc_epoch=observed_utc_epoch, reason='CLOCK_EVIDENCE_MISSING_OR_INVALID')
        if not evidence.valid_at(now, broker_server, source_bytes=source_bytes):
            return ClockFinding(None, len(ticks), 0, 0., False, stale_symbols=tuple(sorted(ticks.keys())),
                                evidence=evidence, broker_server=broker_server,
                                observed_utc_epoch=observed_utc_epoch, reason='CLOCK_EVIDENCE_EXPIRED_OR_WRONG_BROKER')

    votes = Counter()
    stale = []

    candidate_info = {}
    for sym, ts in ticks.items():
        delta = ts - observed_utc_epoch
        hours = int(round(delta / 3600))
        if not (-12 <= hours <= 14):
            stale.append(sym)
            continue
        shift_to_use = evidence.shift_hours if evidence is not None else hours
        cand_utc = ts - shift_to_use * 3600
        candidate_info[sym] = (hours, ts, cand_utc)

    if candidate_info:
        latest_cand_utc = max(info[2] for info in candidate_info.values())
        for sym, (hours, ts, cand_utc) in candidate_info.items():
            age = observed_utc_epoch - cand_utc
            in_period = True
            if evidence is not None:
                in_period = (
                    evidence.valid_from.timestamp() <= cand_utc < evidence.valid_until.timestamp()
                )
            if -15 <= age <= 180 and (latest_cand_utc - cand_utc <= 180) and in_period:
                votes[hours] += 1
            else:
                stale.append(sym)

    stale_tuple = tuple(sorted(set(stale)))

    if not votes:
        return ClockFinding(None, len(ticks), 0, 0., False, stale_symbols=stale_tuple,
                            evidence=evidence, broker_server=broker_server,
                            observed_utc_epoch=observed_utc_epoch,
                            reason='INSUFFICIENT_FRESH_QUOTES')

    hours, count = votes.most_common(1)[0]
    frac = count / sum(votes.values())
    valid = count >= min_symbols and frac >= majority_fraction

    if evidence is not None and hours != evidence.shift_hours:
        valid = False

    if valid and previous_shift is not None and hours != previous_shift:
        return ClockFinding(
            None, len(ticks), count, round(frac, 4), False,
            stale_symbols=stale_tuple, evidence=evidence,
            broker_server=broker_server, observed_utc_epoch=observed_utc_epoch,
            reason='QUARANTINED_UNEXPLAINED_SHIFT_JUMP'
        )

    reason = 'CLOCK_VERIFIED' if valid else 'INSUFFICIENT_FRESH_QUOTES'

    return ClockFinding(
        hours if valid else None,
        len(ticks),
        count if valid else 0,
        round(frac, 4),
        valid,
        stale_symbols=stale_tuple,
        evidence=evidence,
        broker_server=broker_server,
        observed_utc_epoch=observed_utc_epoch,
        reason=reason,
    )


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
    evidence: ClockEvidence | None = None

    def as_dict(self) -> dict:
        data = {
            "schema": 1,
            "canonical_market_clock": "MT5_TICK_SERVER_TIME_CONVERTED_TO_UTC",
            "observed_at_utc": self.observed_at_utc.isoformat(),
            "broker_server_shift_minutes": self.server_shift_hours * 60,
            "time_basis": self.evidence.time_basis if self.evidence else "CURRENT_MULTISYMBOL_QUOTES_ONLY",
            "shift_evidence": self.evidence.source if self.evidence else "CURRENT_MULTISYMBOL_QUOTES_ONLY",
            "confirming_symbols": self.confirming_symbols,
            "confidence_fraction": self.confidence_fraction,
            "historical_dst_verified": False,
            "external_naive_time_assumed_utc": False,
            "live_execution_authorized": False,
        }
        if self.evidence:
            data.update({
                "evidence_sha256": self.evidence.source_sha256,
                "evidence_valid_from": self.evidence.valid_from.isoformat(),
                "evidence_valid_until": self.evidence.valid_until.isoformat(),
            })
        return data


def capture_time_reference(finding: ClockFinding, observed_at_utc: datetime) -> BrokerTimeReference:
    """Capture the offset from *this* MT5 observation, never a hard-coded UTC+3."""
    observed = _aware_utc(observed_at_utc)
    if (not finding.suitable_for_readonly_snapshot or
            finding.observed_hours_shift is None or
            finding.confirming_symbols < 3):
        raise ValueError("broker_clock_not_verified")
    if finding.evidence is not None:
        if not finding.evidence.valid_at(observed, finding.broker_server):
            raise ValueError("broker_clock_not_verified")
        if finding.observed_utc_epoch is not None and observed.timestamp() != finding.observed_utc_epoch:
            raise ValueError("broker_clock_not_verified")
    return BrokerTimeReference(
        observed, finding.observed_hours_shift,
        finding.confirming_symbols, finding.confidence_fraction,
        finding.evidence,
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
        if reference.evidence is not None:
            if not (reference.evidence.valid_from <= received < reference.evidence.valid_until):
                raise ValueError("broker_clock_evidence_expired")
        normalized = (local_wall - timedelta(hours=reference.server_shift_hours)).replace(
            tzinfo=timezone.utc
        )
        data_age = (received - normalized).total_seconds()
        if not 0 <= data_age <= 180:
            raise ValueError("broker_wall_outside_verified_current_window")
        if reference.evidence is not None:
            if not (reference.evidence.valid_from <= normalized < reference.evidence.valid_until):
                raise ValueError("broker_wall_outside_verified_current_window")
    else:
        raise ValueError("unknown_or_unverifiable_timestamp_source")
    display_shift_is_current = (
        reference is not None and
        abs((normalized - reference.observed_at_utc).total_seconds()) <= 180
    )
    wall = (
        (normalized + timedelta(hours=reference.server_shift_hours)).replace(tzinfo=None)
        if display_shift_is_current else None
    )
    return NormalizedIncomingTime(normalized, source, market_authority, wall)
