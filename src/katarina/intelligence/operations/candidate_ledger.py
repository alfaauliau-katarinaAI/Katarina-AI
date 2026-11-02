"""Research candidates ledger: what the observer evaluated, including WAIT.

docs/ROADMAP.md (WP4 — Tahap 1–2):
Stores research candidates evaluating ContextDecision cards without modifying
active trading decisions, actions, or submitting orders (orders_submitted remains 0).

Schema:
research_candidates(
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
    blockers_json TEXT,
    UNIQUE(cycle_id, symbol)
)
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Mapping

SCHEMA_VERSION = 1


def setup(db) -> None:
    db.executescript("""
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
        blockers_json TEXT,
        UNIQUE(cycle_id, symbol));
    CREATE INDEX IF NOT EXISTS idx_research_candidates_symbol ON research_candidates(symbol, observed_utc);
    """)
    db.commit()


def _finite(value: Any) -> float | None:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    return val if math.isfinite(val) else None


def record(db, *, cycle_id: str, cards: Mapping[str, Mapping[str, Any]], quotes: Mapping[str, Any]) -> int:
    """Record research candidate rows from cards for a given cycle.

    All values are taken from existing ContextDecision cards (or card dictionaries)
    without recalculation. WAIT states are recorded without creating an entry.
    """
    setup(db)
    rows = []
    for symbol in sorted(cards):
        card = cards[symbol] or {}
        # Support both ContextDecision object and dict
        if hasattr(card, "to_dict"):
            card_data = card.to_dict()
        elif isinstance(card, dict):
            card_data = card
        else:
            card_data = {}

        observed_utc = (
            card_data.get("observed_vps_timestamp_utc")
            or card_data.get("analyzed_at_utc")
            or datetime.now(timezone.utc).isoformat()
        )

        closed_bar_times = card_data.get("closed_bar_times_utc")
        closed_m5 = None
        if isinstance(closed_bar_times, dict):
            closed_m5 = closed_bar_times.get("M5")
        elif card_data.get("closed_m5_utc"):
            closed_m5 = str(card_data.get("closed_m5_utc"))

        market_state = card_data.get("market_state")
        direction_bias = card_data.get("direction_bias")
        selected_method = card_data.get("selected_method")
        technical_setup = card_data.get("technical_setup")
        technical_evidence_score = _finite(card_data.get("technical_evidence_score"))
        conditional_side = card_data.get("conditional_side")
        conditional_invalidation = _finite(card_data.get("conditional_invalidation"))
        conditional_target = _finite(card_data.get("conditional_target"))
        after_spread_rr_geometry = _finite(card_data.get("after_spread_rr_geometry"))

        quote = quotes.get(symbol)
        bid = ask = tick_epoch = spread = None
        if quote is not None:
            bid, ask, tick_epoch = (_finite(v) for v in quote)
            if None not in (bid, ask) and ask >= bid:
                spread = ask - bid
        if spread is None:
            spread = _finite(card_data.get("broker_spread_price"))

        blockers = card_data.get("blocking_reasons") or card_data.get("blockers") or ()
        blockers_json = json.dumps(list(blockers), ensure_ascii=True, separators=(",", ":"))

        rows.append((
            str(cycle_id),
            str(symbol),
            closed_m5,
            str(observed_utc),
            str(market_state) if market_state is not None else None,
            str(direction_bias) if direction_bias is not None else None,
            str(selected_method) if selected_method is not None else None,
            str(technical_setup) if technical_setup is not None else None,
            technical_evidence_score,
            str(conditional_side) if conditional_side is not None else None,
            conditional_invalidation,
            conditional_target,
            after_spread_rr_geometry,
            spread,
            bid,
            ask,
            tick_epoch,
            blockers_json,
        ))

    with db:
        db.executemany("""
        INSERT OR IGNORE INTO research_candidates(
            cycle_id, symbol, closed_m5_utc, observed_utc, market_state,
            direction_bias, selected_method, technical_setup, technical_evidence_score,
            conditional_side, conditional_invalidation, conditional_target,
            after_spread_rr_geometry, spread, bid, ask, tick_epoch, blockers_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)

    return len(rows)
