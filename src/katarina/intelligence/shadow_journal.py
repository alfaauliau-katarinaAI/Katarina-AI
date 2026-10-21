"""Append-only, replayable shadow-trading journal (no MT5 or broker API).

Event files use O_EXCL and fsync so a duplicate cannot overwrite evidence.
This is a SINGLE-WRITER journal: external processes must serialize writes.
SHA256 checks accidental corruption, NOT counterparty/authenticity attestation.
Failed/incomplete files STOP replay instead of being silently skipped.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from threading import RLock
import json
import os

from katarina.intelligence.strategy_evidence import ClosedStrategyTrade


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp_not_timezone_aware")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat()


def _parse(text: str) -> datetime:
    return _utc(datetime.fromisoformat(text))


def _finite(value: float) -> float:
    if isinstance(value, bool):
        raise ValueError("nonfinite_journal_amount")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("nonfinite_journal_amount") from exc
    if not isfinite(result):
        raise ValueError("nonfinite_journal_amount")
    return result


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True, slots=True)
class ShadowSignal:
    event_id: str
    symbol: str
    strategy_id: str
    strategy_version: str
    observed_at_utc: datetime
    frozen_at_utc: datetime
    m5_closed_at_utc: datetime
    h1_closed_at_utc: datetime
    h4_closed_at_utc: datetime
    side: str                 # BUY, SELL or WAIT
    action: str               # ACCEPT, REJECT or NO_TRADE
    reason: str
    broker_session_open: bool
    data_fresh: bool
    news_blackout: bool
    spread_price_units: float
    spec_revision: int


@dataclass(frozen=True, slots=True)
class ShadowTradeClose:
    event_id: str
    signal_id: str
    recorded_at_utc: datetime
    entry_at_utc: datetime
    closed_at_utc: datetime
    gross_pnl_account: float     # spread-inclusive broker or paper account money
    commission_account: float    # negative/zero debit
    swap_account: float          # signed credit/debit
    slippage_cost_account: float # positive extra exit/entry cost
    initial_risk_account: float  # loss to initial SL, verified native account units
    account_currency: str
    provenance: str              # PAPER or BROKER_DEAL only
    broker_deal_ids: tuple[str, ...]
    costs_reconciled: bool
    contract_verified: bool
    final_close: bool


_SIGNAL_TIMES = ("observed_at_utc", "frozen_at_utc", "m5_closed_at_utc",
                 "h1_closed_at_utc", "h4_closed_at_utc")
_CLOSE_TIMES = ("recorded_at_utc", "entry_at_utc", "closed_at_utc")


class ShadowJournal:
    """Durable evidence for review, not a means of enabling broker execution."""

    def __init__(self, directory: str | Path):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._signals: dict[str, ShadowSignal] = {}
        self._closes: dict[str, ShadowTradeClose] = {}
        self._payload: dict[tuple[str, str], str] = {}
        self._load()

    @staticmethod
    def _signal_payload(signal: ShadowSignal) -> dict:
        d = asdict(signal)
        for key in _SIGNAL_TIMES:
            d[key] = _iso(d[key])
        return d

    @staticmethod
    def _close_payload(close: ShadowTradeClose) -> dict:
        d = asdict(close)
        for key in _CLOSE_TIMES:
            d[key] = _iso(d[key])
        d["broker_deal_ids"] = list(close.broker_deal_ids)
        return d

    @staticmethod
    def _signal_from_payload(value: dict) -> ShadowSignal:
        row = dict(value)
        for key in _SIGNAL_TIMES:
            row[key] = _parse(row[key])
        return ShadowSignal(**row)

    @staticmethod
    def _close_from_payload(value: dict) -> ShadowTradeClose:
        row = dict(value)
        for key in _CLOSE_TIMES:
            row[key] = _parse(row[key])
        row["broker_deal_ids"] = tuple(row["broker_deal_ids"])
        return ShadowTradeClose(**row)

    @staticmethod
    def _validate_signal(s: ShadowSignal) -> None:
        if (not s.event_id or not s.symbol or not s.strategy_id or
                not s.strategy_version or not s.reason or s.spec_revision <= 0):
            raise ValueError("invalid_signal_identity")
        if s.side not in ("BUY", "SELL", "WAIT") or s.action not in (
                "ACCEPT", "REJECT", "NO_TRADE"):
            raise ValueError("invalid_signal_action")
        if (s.action == "ACCEPT" and (s.side == "WAIT" or not s.data_fresh or
                not s.broker_session_open or s.news_blackout)):
            raise ValueError("untradeable_signal_cannot_be_accepted")
        if s.action == "NO_TRADE" and s.side != "WAIT":
            raise ValueError("no_trade_requires_wait")
        observed = _utc(s.observed_at_utc)
        if _utc(s.frozen_at_utc) >= observed:
            raise ValueError("strategy_not_frozen_before_signal")
        for field in (s.m5_closed_at_utc, s.h1_closed_at_utc, s.h4_closed_at_utc):
            if _utc(field) > observed:
                raise ValueError("future_candle_in_signal")
        for v in (s.broker_session_open, s.data_fresh, s.news_blackout):
            if not isinstance(v, bool):
                raise ValueError("invalid_signal_boolean")
        if _finite(s.spread_price_units) < 0:
            raise ValueError("invalid_spread")

    @staticmethod
    def _validate_close(t: ShadowTradeClose, s: ShadowSignal) -> None:
        if not t.event_id or not t.signal_id or t.signal_id != s.event_id:
            raise ValueError("unmatched_close_identity")
        if s.action != "ACCEPT" or s.side not in ("BUY", "SELL"):
            raise ValueError("close_of_unaccepted_signal")
        if not isinstance(t.final_close, bool):
            raise ValueError("invalid_final_close")
        if (not (_utc(s.observed_at_utc) <= _utc(t.entry_at_utc) <
                 _utc(t.closed_at_utc) <= _utc(t.recorded_at_utc))):
            raise ValueError("invalid_trade_timeline")
        for field in ("gross_pnl_account", "commission_account", "swap_account",
                      "slippage_cost_account", "initial_risk_account"):
            _finite(getattr(t, field))
        if (t.commission_account > 0 or t.slippage_cost_account < 0 or
                t.initial_risk_account <= 0):
            raise ValueError("invalid_trade_cost_geometry")
        if (t.provenance not in ("PAPER", "BROKER_DEAL") or
                not t.account_currency or not isinstance(t.costs_reconciled, bool)
                or not isinstance(t.contract_verified, bool)):
            raise ValueError("unverified_trade_origin")
        if (not isinstance(t.broker_deal_ids, tuple) or
                any(not x for x in t.broker_deal_ids) or
                len(set(t.broker_deal_ids)) != len(t.broker_deal_ids)):
            raise ValueError("invalid_broker_deal_ids")
        if t.provenance == "BROKER_DEAL" and not t.broker_deal_ids:
            raise ValueError("broker_deal_ids_required")
        if t.provenance == "PAPER" and t.broker_deal_ids:
            raise ValueError("paper_cannot_claim_broker_deals")

    def _install(self, kind: str, event: ShadowSignal | ShadowTradeClose) -> None:
        if kind == "signal":
            self._validate_signal(event)
            if event.event_id in self._signals:
                raise ValueError("duplicate_signal")
            self._signals[event.event_id] = event
        elif kind == "close":
            parent = self._signals.get(event.signal_id)
            if parent is None:
                raise ValueError("close_missing_signal")
            self._validate_close(event, parent)
            if event.event_id in self._closes:
                raise ValueError("duplicate_close")
            same = [x for x in self._closes.values() if x.signal_id == event.signal_id]
            if any(x.final_close for x in same):
                raise ValueError("close_after_final")
            if same and (
                    event.entry_at_utc != same[0].entry_at_utc or
                    event.initial_risk_account != same[0].initial_risk_account or
                    event.account_currency != same[0].account_currency or
                    event.provenance != same[0].provenance or
                    event.closed_at_utc < max(x.closed_at_utc for x in same)):
                raise ValueError("inconsistent_partial_close")
            existing_ids = {v for x in self._closes.values() for v in x.broker_deal_ids}
            if existing_ids.intersection(event.broker_deal_ids):
                raise ValueError("broker_deal_already_counted")
            self._closes[event.event_id] = event
        else:
            raise ValueError("invalid_journal_record_kind")

    @staticmethod
    def _event_key(kind: str, event_id: str) -> str:
        return sha256((kind + ":" + event_id).encode("utf-8")).hexdigest()

    def _load(self) -> None:
        stored = []
        for path in self.path.iterdir():
            if not path.is_file() or path.suffix != ".json":
                raise ValueError("unknown_journal_file")
            try:
                outer = json.loads(path.read_text(encoding="utf-8"))
                kind = outer["kind"]
                data = outer["payload"]
                if sha256(_canonical(data).encode()).hexdigest() != outer["hash"]:
                    raise ValueError("journal_digest_mismatch")
                event = (self._signal_from_payload(data) if kind == "signal"
                         else self._close_from_payload(data) if kind == "close"
                         else None)
                if event is None or path.stem != self._event_key(kind, event.event_id):
                    raise ValueError("journal_record_identity_mismatch")
                stored.append((kind, event, _canonical(data)))
            except (OSError, KeyError, TypeError, ValueError, UnicodeError) as exc:
                raise ValueError("journal_corrupt_or_incomplete") from exc
        # Files are named by hash, not chronology; install parents before closes.
        for kind, event, payload in sorted(
                stored, key=lambda x: (x[0] != "signal",
                                       x[1].closed_at_utc if x[0] == "close"
                                       else x[1].observed_at_utc)):
            self._install(kind, event)
            self._payload[(kind, event.event_id)] = payload

    def append(self, record: ShadowSignal | ShadowTradeClose) -> bool:
        kind = ("signal" if isinstance(record, ShadowSignal)
                else "close" if isinstance(record, ShadowTradeClose) else None)
        if kind is None:
            raise ValueError("unsupported_journal_record")
        with self._lock:
            payload = (self._signal_payload(record) if kind == "signal"
                       else self._close_payload(record))
            plain = _canonical(payload)
            key = (kind, record.event_id)
            if key in self._payload:
                if self._payload[key] != plain:
                    raise ValueError("idempotency_conflict")
                return False
            # Validate the proposed record BEFORE writing it to disk.
            if kind == "signal":
                self._validate_signal(record)
            else:
                parent = self._signals.get(record.signal_id)
                if parent is None:
                    raise ValueError("close_missing_signal")
                self._validate_close(record, parent)
                # Check partial consistency before touching disk.
                prior = [x for x in self._closes.values() if x.signal_id == record.signal_id]
                if any(x.final_close for x in prior):
                    raise ValueError("close_after_final")
                if prior and (
                        record.entry_at_utc != prior[0].entry_at_utc or
                        record.initial_risk_account != prior[0].initial_risk_account or
                        record.account_currency != prior[0].account_currency or
                        record.provenance != prior[0].provenance or
                        record.closed_at_utc < max(x.closed_at_utc for x in prior)):
                    raise ValueError("inconsistent_partial_close")
                if set(record.broker_deal_ids).intersection(
                    {v for x in self._closes.values() for v in x.broker_deal_ids}):
                    raise ValueError("broker_deal_already_counted")
            digest = sha256(plain.encode()).hexdigest()
            content = (_canonical({"kind": kind, "payload": payload, "hash": digest})
                       + "\n").encode("utf-8")
            path = self.path / (self._event_key(kind, record.event_id) + ".json")
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError as exc:
                raise ValueError("journal_path_conflict_or_concurrent_writer") from exc
            try:
                with os.fdopen(fd, "wb") as file:
                    file.write(content)
                    file.flush()
                    os.fsync(file.fileno())
            except OSError:
                # Intentionally leave incomplete file in place: restart fails closed.
                raise
            self._install(kind, record)
            self._payload[key] = plain
            return True

    def forward_outcomes(self, *, symbol: str, strategy_id: str,
                         strategy_version: str) -> tuple[ClosedStrategyTrade, ...]:
        """Group partial closes to ONE trade per entry; no incomplete trade leakage."""
        by_signal: dict[str, list[ShadowTradeClose]] = {}
        for close in self._closes.values():
            parent = self._signals[close.signal_id]
            if (parent.symbol == symbol and parent.strategy_id == strategy_id
                    and parent.strategy_version == strategy_version):
                by_signal.setdefault(close.signal_id, []).append(close)
        results = []
        for signal_id, closes in by_signal.items():
            if sum(x.final_close for x in closes) != 1:
                continue
            closes.sort(key=lambda x: x.closed_at_utc)
            final = closes[-1]
            if not final.final_close:
                raise ValueError("partial_close_after_final")
            first = closes[0]
            if any((x.initial_risk_account != first.initial_risk_account or
                    x.account_currency != first.account_currency or
                    x.provenance != first.provenance) for x in closes):
                raise ValueError("inconsistent_partial_close")
            net = sum(x.gross_pnl_account + x.commission_account +
                      x.swap_account - x.slippage_cost_account for x in closes)
            verified = all(x.costs_reconciled and x.contract_verified for x in closes)
            parent = self._signals[signal_id]
            results.append(ClosedStrategyTrade(
                trade_id=signal_id, symbol=parent.symbol,
                strategy_id=parent.strategy_id,
                closed_at_utc=final.closed_at_utc,
                net_r=net / first.initial_risk_account,
                provenance=first.provenance, costs_verified=verified,
            ))
        return tuple(sorted(results, key=lambda x: x.closed_at_utc))

    @property
    def signal_count(self) -> int:
        return len(self._signals)

    @property
    def close_count(self) -> int:
        return len(self._closes)
