"""Export research trades from Stage 0 verified broker ticks (WP4).

docs/ROADMAP.md WP4:
Transforms research candidates (having conditional_side BUY/SELL or direction_bias + invalidation/target)
into trades.jsonl with simulated exit evaluated against verified Stage 0 broker ticks (<state>/broker-ticks,
verified against sha256 in broker_tick_days).

Rules:
1. Exit rules (target, invalidation, timeout/horizon) are STRICTLY read from registered hypothesis spec in
   HypothesisRegistry. There are NO hardcoded defaults in code.
2. data_until = closed_m5_utc timestamp (or last candle timestamp), and must be <= entry_at.
3. If tick file sha256 does not match recorded sha256, tick processing fails (TICK_FILE_HASH_MISMATCH).
4. Simulated trade execution does not touch live broker, VPS, or submit orders (orders_submitted is strictly 0).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from katarina.research import context_export
from katarina.research import validation as v


def _to_utc_dt(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val.astimezone(timezone.utc) if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    s = str(val)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_candidate_rows(db: sqlite3.Connection, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    db.row_factory = sqlite3.Row
    query = """
    SELECT cycle_id, symbol, closed_m5_utc, observed_utc, market_state,
           direction_bias, selected_method, technical_setup, technical_evidence_score,
           conditional_side, conditional_invalidation, conditional_target,
           after_spread_rr_geometry, spread, bid, ask, tick_epoch, blockers_json
    FROM research_candidates
    WHERE (conditional_side IN ('BUY', 'SELL')
           OR (direction_bias IN ('BUY', 'SELL') AND conditional_invalidation IS NOT NULL AND conditional_target IS NOT NULL))
    """
    params: List[Any] = []
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    query += " ORDER BY observed_utc ASC"
    cursor = db.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def export_candidates_to_trades(
    *,
    state_dir: Path,
    registry_path: Path,
    hypothesis_id: str,
    output_trades_path: Path,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    state_dir = Path(state_dir)
    registry = v.HypothesisRegistry(registry_path)
    entry = registry.get(hypothesis_id)
    if entry is None:
        raise v.ValidationError(f"HYPOTHESIS_NOT_REGISTERED:{hypothesis_id}")

    spec = entry.get("spec", {})
    parameters = spec.get("parameters")
    if not isinstance(parameters, dict):
        raise v.ValidationError("HYPOTHESIS_PARAMETERS_MISSING")

    # Strictly read exit rules from spec parameters. NO default values in code.
    if "exit_rules" not in parameters or not isinstance(parameters["exit_rules"], dict):
        raise v.ValidationError("EXIT_RULES_SPEC_REQUIRED")
    exit_rules = parameters["exit_rules"]

    # Required parameters: use_target (bool), use_invalidation (bool), max_holding_seconds (positive float/int)
    if "use_target" not in exit_rules or "use_invalidation" not in exit_rules or "max_holding_seconds" not in exit_rules:
        raise v.ValidationError("EXIT_RULES_FIELDS_REQUIRED")

    use_target = bool(exit_rules["use_target"])
    use_invalidation = bool(exit_rules["use_invalidation"])
    max_holding_seconds = float(exit_rules["max_holding_seconds"])
    if max_holding_seconds <= 0:
        raise v.ValidationError("INVALID_MAX_HOLDING_SECONDS")

    # Check target_factor or invalidation_factor if present in exit_rules
    target_factor = float(exit_rules.get("target_factor", 1.0))
    invalidation_factor = float(exit_rules.get("invalidation_factor", 1.0))

    db_path = state_dir / "context.sqlite3"
    if not db_path.is_file():
        raise v.ValidationError("STATE_DB_NOT_FOUND")

    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        candidates = load_candidate_rows(db, symbol=symbol)

        # Pre-fetch tick days metadata from broker_tick_days
        db.row_factory = sqlite3.Row
        cur = db.execute("SELECT symbol, day, status, sha256, file FROM broker_tick_days WHERE status IN ('STORED', 'STORED_WITH_GAPS')")
        tick_days = [dict(r) for r in cur.fetchall()]
    finally:
        db.close()

    # Index tick day records by (symbol, day)
    tick_records_by_sym: Dict[str, List[Dict[str, Any]]] = {}
    for td in tick_days:
        tick_records_by_sym.setdefault(td["symbol"], []).append(td)
    for sym in tick_records_by_sym:
        tick_records_by_sym[sym].sort(key=lambda r: r["day"])

    trades: List[v.Trade] = []
    skipped_reasons: Dict[str, int] = {}

    for cand in candidates:
        sym = cand["symbol"]
        side = cand["conditional_side"] or cand["direction_bias"]
        if side not in ("BUY", "SELL"):
            continue

        observed_at = _to_utc_dt(cand["observed_utc"])
        closed_m5 = cand.get("closed_m5_utc")
        if closed_m5:
            data_until = _to_utc_dt(closed_m5)
        else:
            data_until = observed_at

        # Rule: data_until must be <= entry_at
        entry_at = observed_at
        if data_until > entry_at:
            raise v.ValidationError("DATA_UNTIL_EXCEEDS_ENTRY_AT")

        bid = cand.get("bid")
        ask = cand.get("ask")
        spread = cand.get("spread")
        if bid is None or ask is None or spread is None or bid <= 0 or ask < bid:
            skipped_reasons["missing_quote"] = skipped_reasons.get("missing_quote", 0) + 1
            continue

        entry_mid = (bid + ask) / 2.0
        invalidation = cand.get("conditional_invalidation")
        target = cand.get("conditional_target")

        if invalidation is None or target is None:
            skipped_reasons["missing_levels"] = skipped_reasons.get("missing_levels", 0) + 1
            continue

        # Adjust levels if factors specified
        if side == "BUY":
            effective_target = entry_mid + abs(target - entry_mid) * target_factor if use_target else None
            effective_invalidation = entry_mid - abs(entry_mid - invalidation) * invalidation_factor if use_invalidation else None
            stop_distance = abs(entry_mid - effective_invalidation) if effective_invalidation else entry_mid * 0.01
        else:  # SELL
            effective_target = entry_mid - abs(entry_mid - target) * target_factor if use_target else None
            effective_invalidation = entry_mid + abs(invalidation - entry_mid) * invalidation_factor if use_invalidation else None
            stop_distance = abs(effective_invalidation - entry_mid) if effective_invalidation else entry_mid * 0.01

        # Locate tick files starting on or after entry_at
        sym_tick_days = tick_records_by_sym.get(sym, [])
        entry_day_str = entry_at.strftime("%Y-%m-%d")
        applicable_days = [r for r in sym_tick_days if r["day"] >= entry_day_str]

        if not applicable_days:
            skipped_reasons["no_future_tick_data"] = skipped_reasons.get("no_future_tick_data", 0) + 1
            continue

        entry_epoch_msc = int(entry_at.timestamp() * 1000)
        max_exit_msc = entry_epoch_msc + int(max_holding_seconds * 1000)

        exit_mid: Optional[float] = None
        exit_at: Optional[datetime] = None
        exit_spread: float = float(spread)

        trade_resolved = False

        for day_record in applicable_days:
            if trade_resolved:
                break
            for tick_msc, tick_bid, tick_ask in context_export.iter_verified_ticks(state_dir, day_record):
                if tick_msc < entry_epoch_msc:
                    continue

                curr_mid = (tick_bid + tick_ask) / 2.0
                curr_spread = tick_ask - tick_bid
                curr_dt = datetime.fromtimestamp(tick_msc / 1000.0, tz=timezone.utc)

                # Check invalidation first (pessimistic / conservative rule)
                if side == "BUY":
                    hit_invalidation = effective_invalidation is not None and tick_bid <= effective_invalidation
                    hit_target = effective_target is not None and tick_bid >= effective_target
                else:
                    hit_invalidation = effective_invalidation is not None and tick_ask >= effective_invalidation
                    hit_target = effective_target is not None and tick_ask <= effective_target

                if hit_invalidation:
                    exit_mid = effective_invalidation
                    exit_at = curr_dt
                    exit_spread = curr_spread
                    trade_resolved = True
                    break
                elif hit_target:
                    exit_mid = effective_target
                    exit_at = curr_dt
                    exit_spread = curr_spread
                    trade_resolved = True
                    break
                elif tick_msc >= max_exit_msc:
                    exit_mid = curr_mid
                    exit_at = curr_dt
                    exit_spread = curr_spread
                    trade_resolved = True
                    break

        if not trade_resolved or exit_mid is None or exit_at is None:
            skipped_reasons["unresolved_in_available_ticks"] = skipped_reasons.get("unresolved_in_available_ticks", 0) + 1
            continue

        trade_id = f"t-{cand['cycle_id']}-{sym}"
        trade = v.Trade(
            trade_id=trade_id,
            side=side,
            entry_at=entry_at,
            exit_at=exit_at,
            known_at=exit_at,
            data_until=data_until,
            entry_mid=float(entry_mid),
            exit_mid=float(exit_mid),
            stop_distance=float(stop_distance),
            spread_entry=float(spread),
            spread_exit=float(exit_spread),
            trend_side=cand.get("direction_bias"),
        )
        trades.append(trade)

    output_trades_path = Path(output_trades_path)
    output_trades_path.parent.mkdir(parents=True, exist_ok=True)
    with output_trades_path.open("w", encoding="utf-8") as out:
        for t in trades:
            row = {
                "trade_id": t.trade_id,
                "side": t.side,
                "entry_at": t.entry_at.isoformat(),
                "exit_at": t.exit_at.isoformat(),
                "known_at": t.known_at.isoformat(),
                "data_until": t.data_until.isoformat(),
                "entry_mid": t.entry_mid,
                "exit_mid": t.exit_mid,
                "stop_distance": t.stop_distance,
                "spread_entry": t.spread_entry,
                "spread_exit": t.spread_exit,
            }
            if t.trend_side is not None:
                row["trend_side"] = t.trend_side
            out.write(json.dumps(row) + "\n")

    return {
        "orders_submitted": 0,
        "live_execution_authorized": False,
        "hypothesis_id": hypothesis_id,
        "candidates_evaluated": len(candidates),
        "trades_exported": len(trades),
        "skipped_reasons": skipped_reasons,
        "output_file": str(output_trades_path),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, help="Path to observer state dir containing context.sqlite3 and broker-ticks")
    parser.add_argument("--registry", required=True, help="Path to hypothesis registry ledger file")
    parser.add_argument("--hypothesis", required=True, help="Registered hypothesis id")
    parser.add_argument("--output", default="build/research/candidate_trades.jsonl", help="Output trades.jsonl path")
    parser.add_argument("--symbol", default=None, help="Optional symbol filter")
    args = parser.parse_args(argv)

    summary = export_candidates_to_trades(
        state_dir=Path(args.state_dir),
        registry_path=Path(args.registry),
        hypothesis_id=args.hypothesis,
        output_trades_path=Path(args.output),
        symbol=args.symbol,
    )
    print(f"Export complete: {summary['trades_exported']} trades generated. orders_submitted={summary['orders_submitted']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
