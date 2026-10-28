"""WP9a Stage 0–2 blocker ladder from existing observer decision evidence.

Read-only analysis of contextual_decisions. Hypothetically removing A/B/C
never alters cards, observer behavior, Risk Governor or trading authority.
Nothing here sends orders.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3

from katarina.research.validation import ValidationError, canonical, sha256_text

# WP9 classification is fixed in docs/ROADMAP.md; UNKNOWN is deliberately
# retained when a newer decision reason has not yet been classified.
BLOCKER_CLASSES = {
    "system_unhealthy": "A",
    "high_impact_news_blackout": "A",
    "macro_event_risk_too_high": "A",
    "no_verified_relevant_news": "B",
    "macro_policy_transmission_not_verified": "B",
    "insufficient_verified_forward_experience": "B",
    "no_confirmed_closed_candle_entry": "C",
    "risk_reward_geometry_not_favorable": "C",
    "technical_evidence_not_sufficient": "C",
    "spread_exceeds_M15_volatility_budget": "M",
    "uncertain_or_shock_regime": "M",
    "no_market_appropriate_playbook": "M",
    "stale_quote": "M",
    "broker_session_closed": "M",
    "snapshot_identity_or_clock_mismatch": "M",
    "invalid_broker_cost_or_atr": "M",
    "invalid_risk_snapshot": "M",
    "drawdown_pause": "M",
    "daily_loss_pause": "M",
    "concurrent_paper_limit": "M",
    "paper_exposure_cap": "M",
    "H1_M15_directional_contradiction": "M",
    "missing_structural_exit_plan": "M",
    "buy_structure_geometry_invalid": "M",
    "sell_structure_geometry_invalid": "M",
    "macro_missing_credible_clock": "M",
    "future_or_unobserved_macro_information": "M",
    "material_macro_direction_uncertain": "M",
    "contradictory_macro_direction": "M",
    "macro_technical_direction_conflict": "M",
    "outcome_ledger_violates_point_in_time": "M",
    "resolved_forward_performance_not_stable": "M",
}
CLASS_ORDER = ("A", "B", "C", "M", "UNKNOWN")
LADDER_STEPS = (
    ("baseline", frozenset()),
    ("fix_A", frozenset(("A",))),
    ("fix_A_B", frozenset(("A", "B"))),
    ("fix_A_B_C", frozenset(("A", "B", "C"))),
)
REQUIRED_COLUMNS = frozenset(("symbol", "method", "observed_utc", "blockers_json"))


def _utc(value):
    try:
        moment = (datetime.fromisoformat(value.replace("Z", "+00:00"))
                  if isinstance(value, str) else value)
        if not isinstance(moment, datetime) or moment.tzinfo is None:
            raise ValueError("aware_utc_datetime_required")
        return moment.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as error:
        raise ValidationError("aware_utc_datetime_required") from error


def _decode_blockers(raw):
    try:
        reasons = json.loads(raw)
    except (TypeError, ValueError) as error:
        raise ValidationError("invalid_blockers_json") from error
    if (not isinstance(reasons, list)
            or any(type(r) is not str or not r for r in reasons)):
        raise ValidationError("invalid_blockers_json")
    return tuple(sorted(set(reasons)))


def _bucket():
    return {"cards": 0, "frequency": Counter(), "classes": Counter(),
            "unknown": Counter(), "combos": Counter(),
            "only": Counter(), "remaining": Counter(),
            "remaining_classes": {key: Counter() for key, _ in LADDER_STEPS}}


def _add(bucket, reasons):
    bucket["cards"] += 1
    bucket["combos"][reasons] += 1
    bucket["frequency"].update(reasons)
    classes = {BLOCKER_CLASSES.get(reason, "UNKNOWN") for reason in reasons}
    bucket["classes"].update(classes)
    bucket["unknown"].update(reason for reason in reasons
                             if reason not in BLOCKER_CLASSES)
    for name, allowed in (("A", {"A"}), ("A+B", {"A", "B"}),
                          ("A+B+C", {"A", "B", "C"})):
        if classes and classes <= allowed:
            bucket["only"][name] += 1
    for step, fixed in LADDER_STEPS:
        unresolved = classes - fixed
        if unresolved:
            bucket["remaining"][step] += 1
            bucket["remaining_classes"][step].update(unresolved)


def _view(bucket):
    ladder = {}
    for name, _ in LADDER_STEPS:
        ladder[name] = {
            "remaining_blocked": bucket["remaining"][name],
            "remaining_by_class": {key: bucket["remaining_classes"][name][key]
                                   for key in CLASS_ORDER
                                   if bucket["remaining_classes"][name][key]},
        }
    return {
        "cards": bucket["cards"],
        "blocker_frequency": dict(sorted(bucket["frequency"].items())),
        "classes": {key: bucket["classes"][key] for key in CLASS_ORDER
                    if bucket["classes"][key]},
        "unknown_blockers": dict(sorted(bucket["unknown"].items())),
        "only_blocked_by": {key: bucket["only"][key] for key in
                            ("A", "A+B", "A+B+C")},
        "ladder": ladder,
        "top_combinations": [
            {"blockers": list(reasons), "count": count}
            for reasons, count in sorted(bucket["combos"].items(),
                                         key=lambda item: (-item[1], item[0]))[:10]
        ],
    }


def analyze_blockers(db: sqlite3.Connection, *, since=None):
    """Count blockers without modifying an existing SQLite database."""
    threshold = _utc(since) if since is not None else None
    columns = {x[1] for x in db.execute("PRAGMA table_info(contextual_decisions)")}
    if not REQUIRED_COLUMNS <= columns:
        raise ValidationError("contextual_decisions_unavailable")
    total, by_symbol = _bucket(), {}
    rows = db.execute("SELECT symbol, method, observed_utc, blockers_json "
                      "FROM contextual_decisions")
    for symbol, method, observed, raw in rows:
        if (not isinstance(symbol, str) or not symbol
                or not isinstance(method, str) or not method):
            raise ValidationError("invalid_contextual_decision")
        try:
            when = _utc(observed)
        except ValidationError as error:
            raise ValidationError("invalid_observed_utc") from error
        if threshold is not None and when < threshold:
            continue
        reasons = _decode_blockers(raw)
        _add(total, reasons)
        _add(by_symbol.setdefault(symbol, _bucket()), reasons)
    report = {
        "schema_version": 1,
        "tool": "katarina.research.blocker_ladder",
        "purpose": "diagnostic_only_no_promotion_or_trade_authority",
        "since_utc": threshold.isoformat() if threshold is not None else None,
        "classification": dict(sorted(BLOCKER_CLASSES.items())),
        "total": _view(total),
        "by_symbol": {symbol: _view(bucket) for symbol, bucket
                      in sorted(by_symbol.items())},
        "live_execution_authorized": False,
        "orders_submitted": 0,
    }
    report["report_sha256"] = sha256_text(canonical(report))
    return report


def read_blocker_ladder(state_dir, *, since=None):
    """Open observer context.sqlite3 with mode=ro; never create/write tables."""
    state = Path(state_dir)
    database = state / "context.sqlite3"
    try:
        with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro",
                                     uri=True, timeout=10)) as db:
            db.execute("PRAGMA query_only=ON")
            return analyze_blockers(db, since=since)
    except sqlite3.Error as error:
        raise ValidationError("blocker_ledger_read_unavailable") from error
