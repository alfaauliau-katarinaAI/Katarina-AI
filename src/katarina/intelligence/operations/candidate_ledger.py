"""WP4: research-only candidate ledger.

This module persists *already published* ContextDecision cards (including WAIT)
and the already-used broker quote. It neither evaluates a strategy nor submits
an order. Its failure must never alter the active observer decision.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from sqlite3 import Connection


COLUMNS = (
    "cycle_id", "symbol", "closed_m5_utc", "observed_utc", "market_state",
    "direction_bias", "selected_method", "technical_setup",
    "technical_evidence_score", "conditional_side", "conditional_invalidation",
    "conditional_target", "after_spread_rr_geometry", "spread", "bid", "ask",
    "tick_epoch", "blockers_json",
)

DDL = """
CREATE TABLE IF NOT EXISTS research_candidates(
    cycle_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    closed_m5_utc TEXT,
    observed_utc TEXT NOT NULL,
    market_state TEXT,
    direction_bias TEXT,
    selected_method TEXT,
    technical_setup TEXT,
    technical_evidence_score REAL,
    conditional_side TEXT,
    conditional_invalidation REAL,
    conditional_target REAL,
    after_spread_rr_geometry REAL,
    spread REAL,
    bid REAL,
    ask REAL,
    tick_epoch REAL,
    blockers_json TEXT NOT NULL,
    PRIMARY KEY(cycle_id, symbol)
)
"""


def _number(value):
    if value is None:
        return None
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError("CANDIDATE_NUMERIC_INVALID")
    return float(value)


def _utcstamp(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("CANDIDATE_TIME_INVALID")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            raise ValueError("naive")
    except ValueError as error:
        raise ValueError("CANDIDATE_TIME_INVALID") from error
    return moment.astimezone(timezone.utc).isoformat()


def record(db: Connection, *, cycle_id: str, cards: dict, quotes: dict) -> int:
    """Idempotently record one row per symbol, including WAIT/sensor failure.

    The Stage0 cycle must already exist; no new cycle is created here. Data
    come from the same cards/quotes that the canonical observer produced.
    Conflicting replays never rewrite an earlier immutable candidate row.
    """
    if (not isinstance(cycle_id, str) or not cycle_id or not isinstance(cards, dict)
            or not isinstance(quotes, dict)):
        raise ValueError("CANDIDATE_INPUT_INVALID")
    row = db.execute(
        "SELECT observed_utc FROM observer_cycles WHERE cycle_id=?", (cycle_id,)
    ).fetchone()
    if row is None:
        raise ValueError("CANDIDATE_CYCLE_MISSING")
    observed = _utcstamp(row[0])
    prepared = []
    for symbol, card in sorted(cards.items()):
        if not isinstance(symbol, str) or not symbol or not isinstance(card, dict):
            raise ValueError("CANDIDATE_CARD_INVALID")
        bar_times = card.get("closed_bar_times_utc")
        if bar_times is not None and not isinstance(bar_times, dict):
            raise ValueError("CANDIDATE_BAR_TIMES_INVALID")
        closed = _utcstamp((bar_times or {}).get("M5"))
        if closed is not None and closed > observed:
            raise ValueError("CANDIDATE_LOOKAHEAD_FORBIDDEN")
        tick = quotes.get(symbol)
        if tick is None:
            bid = ask = epoch = None
        else:
            if not isinstance(tick, (list, tuple)) or len(tick) != 3:
                raise ValueError("CANDIDATE_QUOTE_INVALID")
            bid, ask, epoch = tuple(_number(x) for x in tick)
            if None in (bid, ask, epoch) or bid <= 0 or ask < bid:
                raise ValueError("CANDIDATE_QUOTE_INVALID")
        blockers = card.get("blocking_reasons", ())
        if (not isinstance(blockers, (list, tuple))
                or any(type(reason) is not str for reason in blockers)):
            raise ValueError("CANDIDATE_BLOCKERS_INVALID")
        side = card.get("conditional_side")
        if side not in ("BUY", "SELL", "WAIT", None):
            raise ValueError("CANDIDATE_SIDE_INVALID")
        spread = _number(card.get("broker_spread_price"))
        if spread is None and bid is not None and ask is not None:
            spread = ask - bid
        if spread is not None and spread < 0:
            raise ValueError("CANDIDATE_SPREAD_INVALID")
        values = (
            cycle_id, symbol, closed, observed, card.get("market_state"),
            card.get("direction_bias"), card.get("selected_method"),
            card.get("technical_setup"), _number(card.get("technical_evidence_score")),
            side, _number(card.get("conditional_invalidation")),
            _number(card.get("conditional_target")),
            _number(card.get("after_spread_rr_geometry")),
            spread, bid, ask, epoch, json.dumps(list(blockers), sort_keys=True),
        )
        prepared.append(values)
    placeholders = ",".join("?" for _ in COLUMNS)
    with db:
        db.execute(DDL)
        db.executemany(
            f"INSERT INTO research_candidates({','.join(COLUMNS)}) "
            f"VALUES({placeholders}) ON CONFLICT(cycle_id,symbol) DO NOTHING",
            prepared,
        )
    return len(prepared)
