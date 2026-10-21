"""Read-only MT5 shadow portfolio: crash-recoverable opens and quote-side exits.

NO broker trading methods. Opening a paper position only writes immutable
research evidence. Journal tracks the resulting simulated close in native
account units. Historical imported ticks MUST NOT be labeled PAPER-forward
unless actually observed live after strategy freeze.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite
from pathlib import Path
from threading import RLock
from typing import Callable
import json
import os

from katarina.intelligence.shadow.shadow_journal import (
    ShadowJournal, ShadowTradeClose, _canonical, _parse, _iso, _utc,
)


@dataclass(frozen=True, slots=True)
class PaperPosition:
    signal_id: str
    symbol: str
    side: str
    entry_at_utc: datetime
    exit_deadline_utc: datetime
    entry_price: float            # BUY=ASK; SELL=BID; includes observed spread
    sl_price: float
    tp_price: float
    volume: float
    account_currency: str
    initial_risk_account: float    # order_calc_profit or verified symbol contract
    entry_commission_account: float = 0.
    exit_commission_account: float = 0.
    costs_verified: bool = False
    contract_verified: bool = False
    exposure_group: str = "GOLD"


@dataclass(frozen=True, slots=True)
class ObservedQuote:
    symbol: str
    observed_at_utc: datetime
    bid: float
    ask: float


@dataclass(frozen=True, slots=True)
class PaperCloseResult:
    signal_id: str
    event_id: str
    reason: str
    exit_price: float
    net_r: float


class ShadowPaperBook:
    """Only one writer process can own a paper book.

    Each paper OPEN is a separate O_EXCL/fsynced immutable record.
    The accompanying ShadowJournal is authoritative for its CLOSE. If a crash
    happens between recording a close and returning its acknowledgment,
    restart detects the journal close and does not duplicate the trade.
    """

    def __init__(self, directory: str | Path, journal: ShadowJournal):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=True)
        self.journal = journal
        self._lock = RLock()
        self._opened: dict[str, PaperPosition] = {}
        self._load()

    @staticmethod
    def _valid(p: PaperPosition) -> None:
        if (not p.signal_id or not p.symbol or not p.account_currency or
                not p.exposure_group or p.side not in ("BUY", "SELL") or
                type(p.costs_verified) is not bool or
                type(p.contract_verified) is not bool):
            raise ValueError("invalid_paper_identity")
        first, deadline = _utc(p.entry_at_utc), _utc(p.exit_deadline_utc)
        if first >= deadline:
            raise ValueError("paper_deadline_before_entry")
        values = (p.entry_price, p.sl_price, p.tp_price, p.volume,
                  p.initial_risk_account, p.entry_commission_account,
                  p.exit_commission_account)
        if not all(isinstance(x, (int, float)) and
                   not isinstance(x, bool) and isfinite(x) for x in values):
            raise ValueError("nonfinite_paper_position")
        if (min(p.entry_price, p.sl_price, p.tp_price, p.volume,
                p.initial_risk_account) <= 0 or
                p.entry_commission_account > 0 or p.exit_commission_account > 0):
            raise ValueError("invalid_paper_risk_or_cost")
        if ((p.side == "BUY" and not p.sl_price < p.entry_price < p.tp_price) or
                (p.side == "SELL" and not p.tp_price < p.entry_price < p.sl_price)):
            raise ValueError("invalid_paper_stop_target")

    @staticmethod
    def _payload(p: PaperPosition) -> dict:
        out = asdict(p)
        out["entry_at_utc"] = _iso(p.entry_at_utc)
        out["exit_deadline_utc"] = _iso(p.exit_deadline_utc)
        return out

    @staticmethod
    def _parse_position(row: dict) -> PaperPosition:
        obj = dict(row)
        obj["entry_at_utc"] = _parse(obj["entry_at_utc"])
        obj["exit_deadline_utc"] = _parse(obj["exit_deadline_utc"])
        return PaperPosition(**obj)

    def _load(self) -> None:
        for path in self.path.iterdir():
            if not path.is_file() or path.suffix != ".json":
                raise ValueError("unknown_paper_book_file")
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
                payload = doc["payload"]
                if sha256(_canonical(payload).encode()).hexdigest() != doc["sha256"]:
                    raise ValueError("paper_position_digest_mismatch")
                position = self._parse_position(payload)
                if path.stem != sha256(position.signal_id.encode()).hexdigest():
                    raise ValueError("paper_position_filename_mismatch")
                self._valid(position)
                if position.signal_id in self._opened:
                    raise ValueError("duplicate_paper_open")
                self._opened[position.signal_id] = position
            except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
                raise ValueError("paper_book_corrupt_or_incomplete") from exc
        for p in self._opened.values():
            self._matching_signal(p)

    def _matching_signal(self, p: PaperPosition) -> None:
        sig = self.journal._signals.get(p.signal_id)
        if (sig is None or sig.action != "ACCEPT" or sig.symbol != p.symbol or
                sig.side != p.side or sig.observed_at_utc > p.entry_at_utc or
                sig.spec_revision <= 0):
            raise ValueError("paper_open_has_no_valid_signal")

    def pending(self) -> tuple[PaperPosition, ...]:
        # Once closed, a position is no longer counted as open on restart.
        final_ids = {t.signal_id for t in self.journal._closes.values()
                     if t.final_close}
        return tuple(sorted((p for p in self._opened.values()
                             if p.signal_id not in final_ids),
                            key=lambda p: (p.entry_at_utc, p.signal_id)))

    def open(self, position: PaperPosition) -> bool:
        with self._lock:
            self._valid(position)
            self._matching_signal(position)
            if position.signal_id in self._opened:
                if self._payload(position) != self._payload(self._opened[position.signal_id]):
                    raise ValueError("paper_position_idempotency_conflict")
                return False
            for other in self.pending():
                if other.exposure_group == position.exposure_group:
                    raise ValueError("paper_exposure_group_busy")
            payload = self._payload(position)
            serialized = _canonical(payload)
            data = (_canonical({"payload":payload,
                "sha256":sha256(serialized.encode()).hexdigest()}) + "\n").encode()
            path = self.path / (sha256(position.signal_id.encode()).hexdigest() + ".json")
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError as exc:
                raise ValueError("paper_book_concurrent_writer") from exc
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            self._opened[position.signal_id] = position
            return True

    def on_quote(self, quote: ObservedQuote, *,
                 profit_at_exit: Callable[[PaperPosition, float], float],
                 slippage_cost_account: float = 0.,
                 swap_account: float = 0.) -> tuple[PaperCloseResult, ...]:
        """Receive CURRENT broker quote only; never request historical fills.

        Profit callback must use broker order_calc_profit or a verified paper
        contract in the ACCOUNT currency. Slippage is an adverse extra debit.
        """
        with self._lock:
            instant = _utc(quote.observed_at_utc)
            if (not isfinite(quote.bid) or not isfinite(quote.ask) or
                    quote.bid <= 0 or quote.ask < quote.bid or
                    not isfinite(slippage_cost_account) or slippage_cost_account < 0 or
                    not isfinite(swap_account)):
                raise ValueError("invalid_observed_quote_or_cost")
            completed = []
            for p in self.pending():
                if p.symbol != quote.symbol or instant < p.entry_at_utc:
                    continue
                executable = quote.bid if p.side == "BUY" else quote.ask
                hit_sl = executable <= p.sl_price if p.side == "BUY" else executable >= p.sl_price
                hit_tp = executable >= p.tp_price if p.side == "BUY" else executable <= p.tp_price
                time_limit = instant >= p.exit_deadline_utc
                if not (hit_sl or hit_tp or time_limit):
                    continue
                reason = "SL" if hit_sl else "TP" if hit_tp else "TIME"
                # Actual observed executable quote, NOT optimistic SL/TP on gaps.
                gross = float(profit_at_exit(p, executable))
                if not isfinite(gross):
                    raise ValueError("unverified_account_currency_profit")
                close = ShadowTradeClose(
                    event_id="paper-close:" + p.signal_id,
                    signal_id=p.signal_id, recorded_at_utc=instant,
                    entry_at_utc=p.entry_at_utc, closed_at_utc=instant,
                    gross_pnl_account=gross,
                    commission_account=(p.entry_commission_account +
                                        p.exit_commission_account),
                    swap_account=swap_account,
                    slippage_cost_account=slippage_cost_account,
                    initial_risk_account=p.initial_risk_account,
                    account_currency=p.account_currency, provenance="PAPER",
                    broker_deal_ids=(),
                    costs_reconciled=p.costs_verified, contract_verified=p.contract_verified,
                    final_close=True,
                )
                self.journal.append(close)
                net = gross + close.commission_account + swap_account - slippage_cost_account
                completed.append(PaperCloseResult(
                    p.signal_id, close.event_id, reason, executable,
                    net / p.initial_risk_account))
            return tuple(completed)
