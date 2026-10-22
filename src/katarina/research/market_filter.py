"""Stage 2 market-intelligence filter tool (docs/ROADMAP.md, Tahap 2). Research only.

A filter decides, from information available *at entry*, whether a candidate signal is tradeable or
must WAIT, and always names the reason. It is judged with the Stage 1 tool:

* A filter is a hypothesis in the same hash-chained :class:`~katarina.research.validation.HypothesisRegistry`
  (``playbook = "MARKET_FILTER"``), registered before it is evaluated, so it counts as a trial.
* Evaluation only reads ``vault.development()``; holdout trades are never touched.
* Context newer than the entry (``context_until > entry_at``) is rejected as look-ahead.
* The roadmap criterion: on development data, median cost / median favourable move of the signals
  that pass the filter must be lower (better) than for all signals. ``favorable_move`` is known only
  after exit; it is used for that comparison and never for a filter decision.
* The development report of the filtered signals comes from the Stage 1 tool itself.

No broker access, no orders, no live authority; a PASS still needs an Owner-approved promotion.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from statistics import median

from katarina.research import validation as v

PLAYBOOK = "MARKET_FILTER"
CONDITIONS = ("max_spread_to_range", "max_spread_to_risk", "session_hours_utc", "min_volatility_ratio",
              "max_volatility_ratio", "min_ticks_per_minute")
REASONS = {
    "max_spread_to_range": "SPREAD_TOO_WIDE_FOR_RANGE",
    "max_spread_to_risk": "SPREAD_TOO_WIDE_FOR_RISK",
    "session_hours_utc": "OUTSIDE_SESSION",
    "min_volatility_ratio": "VOLATILITY_TOO_LOW",
    "max_volatility_ratio": "VOLATILITY_TOO_HIGH",
    "min_ticks_per_minute": "LIQUIDITY_TOO_LOW",
}


@dataclass(frozen=True)
class MarketContext:
    """Market state for one candidate signal. Everything except ``favorable_move`` is causal at entry.

    ``typical_range`` is the median bar range known at entry (price units), ``volatility_ratio`` the
    current volatility over its typical value, ``ticks_per_minute`` an optional liquidity proxy and
    ``favorable_move`` the maximum favourable excursion in price units, known only after exit.
    """
    trade_id: str
    context_until: datetime
    typical_range: float
    volatility_ratio: float
    favorable_move: float
    ticks_per_minute: float | None = None

    @classmethod
    def from_dict(cls, row: dict) -> "MarketContext":
        try:
            ticks = row.get("ticks_per_minute")
            return cls(trade_id=str(row["trade_id"]), context_until=v._utc(row["context_until"]),
                       typical_range=float(row["typical_range"]), volatility_ratio=float(row["volatility_ratio"]),
                       favorable_move=float(row["favorable_move"]),
                       ticks_per_minute=None if ticks is None else float(ticks))
        except (KeyError, TypeError, ValueError) as error:
            raise v.ValidationError(f"context_row_invalid:{type(error).__name__}") from None


def filter_spec(*, name: str, base_spec: dict, parameters: dict) -> dict:
    """Hypothesis definition for a filter applied to one registered base hypothesis."""
    base_id = v.HypothesisRegistry.hypothesis_id(base_spec)
    unknown = sorted(set(parameters) - set(CONDITIONS))
    if unknown or not parameters:
        raise v.ValidationError("filter_parameters_unknown_or_empty:" + ",".join(unknown))
    _check_thresholds(parameters)
    return {"name": name, "symbol": base_spec["symbol"], "side": base_spec["side"], "regime": base_spec["regime"],
            "playbook": PLAYBOOK, "rules": "WAIT unless every condition holds at entry; base " + base_id,
            "parameters": {"base_hypothesis_id": base_id, **parameters}}


def _check_thresholds(parameters: dict) -> None:
    for key, value in parameters.items():
        if key == "session_hours_utc":
            if (not isinstance(value, list) or not value
                    or any(not (isinstance(w, list) and len(w) == 2 and all(type(h) is int and 0 <= h <= 24 for h in w)
                                and w[0] < w[1]) for w in value)):
                raise v.ValidationError("session_hours_utc_must_be_list_of_[start,end)_hours")
        elif type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise v.ValidationError(f"{key}_must_be_positive_number")


def decide(trade: v.Trade, context: MarketContext | None, parameters: dict) -> list[str]:
    """Reasons to WAIT; an empty list means the signal passes. Never reads ``favorable_move``."""
    if context is None:
        return ["CONTEXT_MISSING"]
    if context.context_until > trade.entry_at:
        return ["LOOKAHEAD_CONTEXT_AFTER_ENTRY"]
    if not (context.typical_range > 0 and math.isfinite(context.volatility_ratio)):
        return ["CONTEXT_INVALID"]
    reasons = []
    for key, limit in parameters.items():
        if key == "max_spread_to_range" and trade.spread_entry / context.typical_range > limit:
            reasons.append(REASONS[key])
        elif key == "max_spread_to_risk" and trade.spread_entry / trade.stop_distance > limit:
            reasons.append(REASONS[key])
        elif key == "session_hours_utc" and not any(a <= trade.entry_at.hour < b for a, b in limit):
            reasons.append(REASONS[key])
        elif key == "min_volatility_ratio" and context.volatility_ratio < limit:
            reasons.append(REASONS[key])
        elif key == "max_volatility_ratio" and context.volatility_ratio > limit:
            reasons.append(REASONS[key])
        elif key == "min_ticks_per_minute" and (context.ticks_per_minute is None
                                                or context.ticks_per_minute < limit):
            reasons.append(REASONS[key])
    return reasons


def _cost_to_move(trades, contexts, costs: v.CostModel):
    pairs = [(costs.cost_r(t) * t.stop_distance, contexts[t.trade_id].favorable_move) for t in trades
             if t.trade_id in contexts]
    if not pairs:
        return None
    move = median(m for _, m in pairs)
    return v._round(median(c for c, _ in pairs) / move) if move > 0 else None


def evaluate_filter(vault: v.HoldoutVault, filter_id: str, contexts, *, costs: v.CostModel,
                    as_of: datetime) -> dict:
    """Development-only filter report. ``contexts`` maps trade_id -> :class:`MarketContext`."""
    entry = vault.registry.get(filter_id)
    if entry is None:
        raise v.ValidationError("filter_not_registered")
    spec = entry["spec"]
    if spec["playbook"] != PLAYBOOK:
        raise v.ValidationError("hypothesis_is_not_a_market_filter")
    parameters = {k: val for k, val in spec["parameters"].items() if k != "base_hypothesis_id"}
    base_id = spec["parameters"]["base_hypothesis_id"]
    if vault.registry.get(base_id) is None:
        raise v.ValidationError("base_hypothesis_not_registered")
    contexts = dict(contexts)
    signals, rejected = v.guard_trades(vault.development(), vault.split, "DEVELOPMENT", expected_side=spec["side"])
    passed, waits, reason_counts = [], [], {}
    for trade in signals:
        reasons = decide(trade, contexts.get(trade.trade_id), parameters)
        if reasons:
            waits.append({"trade_id": trade.trade_id, "reasons": reasons})
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        else:
            passed.append(trade)
    unfiltered = _cost_to_move(signals, contexts, costs)
    filtered = _cost_to_move(passed, contexts, costs)
    inner = v.HoldoutVault(passed, vault.split, vault.registry, vault.ledger.path)
    stage1 = v.evaluate_development(inner, filter_id, costs=costs, as_of=as_of)
    gates = {
        "registered_before_evaluation": v._utc(entry["registered_utc"]) <= v._utc(as_of),
        "every_wait_has_reason": all(w["reasons"] for w in waits),
        "no_lookahead_context": "LOOKAHEAD_CONTEXT_AFTER_ENTRY" not in reason_counts,
        "cost_to_move_improves": unfiltered is not None and filtered is not None and filtered < unfiltered,
        "no_rejected_signals": not rejected,
    }
    report = {
        "schema_version": 1,
        "tool": "katarina.research.market_filter",
        "as_of_utc": v._utc(as_of).isoformat(),
        "filter_id": filter_id,
        "base_hypothesis_id": base_id,
        "filter": spec,
        "period": "DEVELOPMENT",
        "split_sha256": vault.split.sha256,
        "trial_count": vault.registry.trial_count(),
        "signals": len(signals),
        "passed": len(passed),
        "waited": len(waits),
        "wait_reasons": dict(sorted(reason_counts.items())),
        "waits": waits,
        "rejected_signals": [{"trade_id": i, "reason": r} for i, r in rejected],
        "median_cost_to_favorable_move": {"unfiltered": unfiltered, "filtered": filtered},
        "stage1_development_report_sha256": stage1["report_sha256"],
        "stage1_verdict": stage1["verdict"],
        "stage1_statistics": stage1["statistics"],
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "live_execution_authorized": False,
        "note": "Development data only. A filter enters the active system only via an Owner-approved promotion.",
    }
    report["report_sha256"] = v.sha256_text(v.canonical(report))
    return report
