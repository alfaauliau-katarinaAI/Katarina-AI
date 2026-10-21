"""Fast fail-closed audit of PREEXISTING prospective shadow signal entry quotes.

Read-only SQLite and MT5 historical tick comparison. Never broker fills or
new independent forward returns; never permits trade or model promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3

MAX_ENTRY_SKEW_SECONDS = 5


def assess_entry(row: dict, ticks, *, tick_size: float = 0.0) -> dict:
    """Compare archived causal bid/ask with frozen entry; no future quotes."""
    status = {"id": row["id"], "symbol": row["symbol"],
              "side": row["side"], "prior_state": row["state"],
              "status": "UNVERIFIED_MISSING_ENTRY_TICK"}
    t = row["tick_at"]
    b, a = row["bid"], row["ask"]
    if (not all(isinstance(x, (int, float)) and math.isfinite(x)
                for x in (t, b, a, tick_size)) or
            t <= 0 or b <= 0 or a < b or tick_size < 0):
        status["status"] = "INVALID_FROZEN_ENTRY"
        return status
    candidates = []
    for q in (() if ticks is None else ticks):
        try:
            ts = float(q["time_msc"]) / 1000.0
            bid = float(q["bid"])
            ask = float(q["ask"])
        except (TypeError, ValueError, KeyError, OverflowError):
            continue
        if (all(math.isfinite(x) for x in (ts, bid, ask)) and bid > 0 and
                ask >= bid and 0 <= t - ts <= MAX_ENTRY_SKEW_SECONDS):
            candidates.append((ts, bid, ask))
    if not candidates:
        return status
    _, bid, ask = max(candidates)
    spread = max(a - b, tick_size)
    tolerance = 2 * spread + 2 * tick_size
    delta = max(abs(bid - b), abs(ask - a))
    status["entry_delta_spreads"] = round(delta / spread, 4) if spread else None
    status["status"] = ("MATCHED_ARCHIVED_ENTRY" if delta <= tolerance
                        else "MISMATCHED_ARCHIVED_ENTRY")
    return status


def scorecard(db, quote_reader, *, as_of_utc: datetime, max_rows: int = 500):
    if as_of_utc.tzinfo is None:
        raise ValueError("utc_aware_asof_required")
    now = as_of_utc.astimezone(timezone.utc)
    count = db.execute("SELECT count(*) FROM prospective_shadow").fetchone()[0]
    if count > max_rows:
        raise ValueError("too_many_rows_for_one_audit")
    records = db.execute(
        """SELECT id,symbol,side,tick_at,bid,ask,state,virtual_net_r,
                  official_news_verified FROM prospective_shadow
           WHERE observed_at<=? ORDER BY id""", (now.timestamp(),)).fetchall()
    results = []
    usable = []
    new_records = 0
    for id, symbol, side, tick_at, bid, ask, state, net_r, news in records:
        if tick_at >= datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp():
            new_records += 1
        row = dict(id=id, symbol=symbol, side=side, tick_at=tick_at,
                   bid=bid, ask=ask, state=state)
        try:
            ticks, tick_size = quote_reader(symbol, tick_at)
            assessment = assess_entry(row, ticks, tick_size=tick_size)
        except Exception:
            assessment = {"id": id, "symbol": symbol, "side": side,
                          "prior_state": state, "status": "ARCHIVE_READER_UNAVAILABLE"}
        assessment["official_news_verified"] = bool(news)
        results.append(assessment)
        if (assessment["status"] == "MATCHED_ARCHIVED_ENTRY" and
                state == "VIRTUAL_QUOTED" and
                isinstance(net_r, (float, int)) and math.isfinite(net_r)):
            usable.append(float(net_r))
    reasons = Counter(x["status"] for x in results)
    return {
        "proof_type": "KATARINA_RAPID_FORWARD_SHADOW_ENTRY_AUDIT",
        "as_of_utc": now.isoformat(),
        "registered_shadow_events": len(records),
        "new_registered_events_today_utc": new_records,
        "entry_audit_counts": dict(reasons),
        "previously_quoted_with_matching_entry": len(usable),
        "previously_quoted_matching_entry_negative": sum(x <= 0 for x in usable),
        "previously_quoted_matching_entry_positive": sum(x > 0 for x in usable),
        "mean_legacy_virtual_r_matching_entries": (
            round(sum(usable)/len(usable), 6) if usable else None),
        "historical_tick_comparison_is_independent_forward_test": False,
        "frozen_legacy_virtual_r_is_real_broker_profit": False,
        "commission_slippage_verified": False,
        "can_validate_profitability": False,
        "may_activate_live_trading": False,
        "decision": "NO_GO_INSUFFICIENT_VERIFIED_FORWARD_EVIDENCE",
        "events": results,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--database", required=True)
    ap.add_argument("--terminal", required=True)
    args = ap.parse_args()
    import MetaTrader5 as mt5
    if not mt5.initialize(path=args.terminal, timeout=10000):
        raise SystemExit("MT5_CONNECTION_REQUIRED")
    try:
        terminal = mt5.terminal_info()
        if terminal is None or not terminal.connected or terminal.trade_allowed:
            raise SystemExit("REFUSE_MT5_AUTOTRADING_OR_OFFLINE")
        def history(symbol, tick_at):
            begin = datetime.fromtimestamp(tick_at - MAX_ENTRY_SKEW_SECONDS,
                                           timezone.utc)
            end = datetime.fromtimestamp(tick_at + 1, timezone.utc)
            quotes = mt5.copy_ticks_range(symbol, begin, end, mt5.COPY_TICKS_INFO)
            info = mt5.symbol_info(symbol)
            return quotes, float(info.trade_tick_size) if info else 0.0
        dburi = Path(args.database).resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(dburi, uri=True) as db:
            report = scorecard(db, history, as_of_utc=datetime.now(timezone.utc))
        print(json.dumps(report, sort_keys=True, allow_nan=False))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
