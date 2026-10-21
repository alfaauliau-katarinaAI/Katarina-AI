"""Forward quote markouts, not fills, strategy backtests or profit labels.

Immutable entry context is linked to its observation. Outcome quotes must be
fresh, observed after the horizon, and within 90 seconds of that horizon.
Unavailable exits expire; a later session must never replace a missing exit.
"""
from datetime import datetime
from math import isfinite
import json

HORIZONS = (300, 900, 1800)
MAX_DELAY = 90


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result.timestamp()


def fresh_quote(row, now):
    try:
        bid, ask, tick = (float(row[k]) for k in ("bid", "ask", "tick_time"))
        return (row.get("connected") is True and
                all(isfinite(v) for v in (bid, ask, tick)) and
                0 < bid <= ask and 0 <= now - tick <= 30)
    except (KeyError, TypeError, ValueError):
        return False


class ForwardOutcomes:
    def __init__(self, db):
        self.db = db
        db.execute("""CREATE TABLE IF NOT EXISTS forward_markouts(
            observation_id INTEGER, symbol TEXT, side TEXT, horizon INTEGER,
            entry_time REAL, due_time REAL, entry_bid REAL, entry_ask REAL,
            entry_atr REAL, context TEXT, status TEXT,
            exit_observation_id INTEGER, exit_time REAL, exit_tick_time REAL,
            markout_bps REAL, markout_atr REAL, midpoint_bps REAL,
            PRIMARY KEY(observation_id,symbol,side,horizon))""")
        db.execute("""CREATE INDEX IF NOT EXISTS forward_pending
                      ON forward_markouts(status,due_time)""")
        db.execute("""CREATE TABLE IF NOT EXISTS forward_progress(
                      singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                      last_id INTEGER, last_time REAL)""")
        db.commit()

    def process(self, observation_id, result):
        now = timestamp(result["as_of_utc"])
        progress = self.db.execute(
            "SELECT last_id,last_time FROM forward_progress WHERE singleton=1"
        ).fetchone()
        if progress and observation_id <= progress[0]:
            return self.summary()
        if progress and now < progress[1]:
            raise ValueError("out_of_order_observation")
        rows = {r["symbol"]: r for r in result.get("symbols", [])}
        with self.db:
            self.db.execute("""UPDATE forward_markouts SET status='MISSING_EXIT'
                WHERE status='PENDING' AND due_time+? < ?""", (MAX_DELAY, now))
            pending = self.db.execute("""SELECT observation_id,symbol,side,
                horizon,entry_time,due_time,entry_bid,entry_ask,entry_atr
                FROM forward_markouts WHERE status='PENDING' AND due_time<=?""",
                (now,)).fetchall()
            for oid, symbol, side, horizon, start, due, bid, ask, atr in pending:
                row = rows.get(symbol, {})
                if not fresh_quote(row, now) or row["tick_time"] < due:
                    continue
                mid = (bid + ask) / 2
                exit_mid = (row["bid"] + row["ask"]) / 2
                delta = row["bid"] - ask if side == "BUY" else bid - row["ask"]
                midpoint = (exit_mid - mid) * (1 if side == "BUY" else -1)
                self.db.execute("""UPDATE forward_markouts SET status='OBSERVED',
                    exit_observation_id=?,exit_time=?,exit_tick_time=?,
                    markout_bps=?,markout_atr=?,midpoint_bps=?
                    WHERE observation_id=? AND symbol=? AND side=? AND horizon=?""",
                    (observation_id, now, row["tick_time"], delta/mid*10000,
                     delta/atr, midpoint/mid*10000, oid, symbol, side, horizon))
            for symbol, row in rows.items():
                # Keep valid market observations even when macro context blocks
                # them, permitting later descriptive filter comparisons.
                if row.get("market_reasons") or not fresh_quote(row, now):
                    continue
                atr = row.get("m1", {}).get("atr", 0)
                if not isfinite(atr) or atr <= 0:
                    continue
                mode_sides = {1: ("BUY",), 2: ("SELL",), 4: ("BUY", "SELL")}
                context = json.dumps({k: row.get(k) for k in
                    ("context", "regime", "regime_detail", "research_score", "spread_atr",
                     "research_candidate", "selection_reason", "decision_reasons",
                     "shadow_hypotheses")},
                    sort_keys=True, allow_nan=False)
                for side in mode_sides.get(row.get("trade_mode"), ()):
                    for horizon in HORIZONS:
                        self.db.execute("""INSERT OR IGNORE INTO forward_markouts
                            (observation_id,symbol,side,horizon,entry_time,due_time,
                             entry_bid,entry_ask,entry_atr,context,status)
                            VALUES(?,?,?,?,?,?,?,?,?,?,'PENDING')""",
                            (observation_id, symbol, side, horizon, now, now+horizon,
                             row["bid"], row["ask"], atr, context))
            self.db.execute("INSERT OR REPLACE INTO forward_progress VALUES(1,?,?)",
                            (observation_id, now))
        return self.summary()

    def summary(self):
        counts = dict(self.db.execute(
            "SELECT status,COUNT(*) FROM forward_markouts GROUP BY status"))
        return dict(kind="forward_quote_markout_not_strategy_pnl",
                    horizons_seconds=list(HORIZONS), max_exit_delay_seconds=MAX_DELAY,
                    counts=counts, includes_spread=True,
                    commission_slippage_included=False,
                    overlapping_samples=True, model_promotion_allowed=False)
