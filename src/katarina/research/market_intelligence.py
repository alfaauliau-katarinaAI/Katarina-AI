"""Stage 2 development-only filter experiments using the Stage 1 validation tool.

This is a report builder, not a second decision engine. It never imports the observer,
connects to a broker, reads a holdout, or installs a filter in the active brain.
Every threshold belongs to the registered hypothesis; there are no production defaults.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime

from katarina.research import validation as v


def _number(value, name, *, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or (value <= 0 if positive else value < 0)):
        raise v.ValidationError(f"invalid_market_context:{name}")
    return float(value)


@dataclass(frozen=True)
class FilterPolicy:
    max_spread_r: float
    max_cost_to_range: float
    min_atr_r: float
    max_atr_r: float
    min_ticks_per_minute: float
    max_context_age_seconds: float
    utc_hours: tuple[int, ...]

    def __post_init__(self):
        for name in ("max_spread_r", "max_cost_to_range", "min_atr_r", "max_atr_r",
                     "min_ticks_per_minute", "max_context_age_seconds"):
            _number(getattr(self, name), name)
        if self.max_atr_r <= 0 or self.min_atr_r > self.max_atr_r:
            raise v.ValidationError("invalid_atr_range")
        hours = tuple(self.utc_hours)
        if not hours or any(type(h) is not int or not 0 <= h < 24 for h in hours) or len(set(hours)) != len(hours):
            raise v.ValidationError("utc_hours_require_distinct_hours_0_to_23")
        object.__setattr__(self, "utc_hours", tuple(sorted(hours)))

    @classmethod
    def from_spec(cls, spec):
        try:
            return cls(**spec["parameters"]["market_filter"])
        except (KeyError, TypeError) as error:
            raise v.ValidationError("registered_market_filter_required") from error


@dataclass(frozen=True)
class MarketContext:
    """Causal closed-window measurements. Tick count is activity, NOT order-book liquidity."""
    trade_id: str
    symbol: str
    window_start: datetime
    observed_at: datetime
    range_price: float
    atr_price: float
    tick_count: int
    source_sha256: str

    def __post_init__(self):
        for name in ("window_start", "observed_at"):
            object.__setattr__(self, name, v._utc(getattr(self, name)))
        if self.window_start >= self.observed_at:
            raise v.ValidationError("context_window_must_be_positive")
        for name in ("range_price", "atr_price"):
            _number(getattr(self, name), name, positive=True)
        if type(self.tick_count) is not int or self.tick_count < 0:
            raise v.ValidationError("tick_count_requires_nonnegative_integer")
        if not re.fullmatch("[0-9a-f]{64}", str(self.source_sha256)):
            raise v.ValidationError("context_source_sha256_required")


@dataclass(frozen=True)
class FavorableOutcome:
    """Maximum favorable MID-price excursion over entry..exit; used ONLY in evaluation."""
    trade_id: str
    favorable_move_price: float
    known_at: datetime

    def __post_init__(self):
        _number(self.favorable_move_price, "favorable_move_price")
        object.__setattr__(self, "known_at", v._utc(self.known_at))


def decide_filter(trade: v.Trade, context: MarketContext | None, policy: FilterPolicy,
                  costs: v.CostModel) -> dict:
    """Decide from entry-time information only; exit spread and outcome are unavailable here."""
    reasons = []
    metrics = {}
    if context is None:
        reasons.append("WAIT_MISSING_CONTEXT")
    else:
        age = (trade.entry_at - context.observed_at).total_seconds()
        if age < 0:
            raise v.ValidationError("context_after_entry")
        if age > policy.max_context_age_seconds:
            reasons.append("WAIT_STALE_CONTEXT")
        minutes = (context.observed_at - context.window_start).total_seconds() / 60
        # Estimate a round trip with the spread known at ENTRY; never use future exit spread.
        estimated_cost = trade.spread_entry + 2 * costs.slippage_per_side + costs.commission_round_trip
        metrics = {"entry_spread_r": trade.spread_entry / trade.stop_distance,
                   "estimated_cost_to_range": estimated_cost / context.range_price,
                   "atr_r": context.atr_price / trade.stop_distance,
                   "ticks_per_minute": context.tick_count / minutes,
                   "context_age_seconds": age}
        if metrics["entry_spread_r"] > policy.max_spread_r:
            reasons.append("WAIT_SPREAD_RISK")
        if metrics["estimated_cost_to_range"] > policy.max_cost_to_range:
            reasons.append("WAIT_COST_RANGE")
        if not policy.min_atr_r <= metrics["atr_r"] <= policy.max_atr_r:
            reasons.append("WAIT_VOLATILITY")
        if metrics["ticks_per_minute"] < policy.min_ticks_per_minute:
            reasons.append("WAIT_LOW_TICK_ACTIVITY")
    if v._utc(trade.entry_at).hour not in policy.utc_hours:
        reasons.append("WAIT_SESSION")
    return {"trade_id": trade.trade_id, "action": "WAIT" if reasons else "KEEP_FOR_RESEARCH",
            "reasons": reasons, "metrics": metrics}


def _index(rows, name):
    result = {}
    for row in rows:
        if not row.trade_id or row.trade_id in result:
            raise v.ValidationError(f"duplicate_or_empty_{name}_id")
        result[row.trade_id] = row
    return result


def _ratio(trades, outcomes, costs):
    cost_r = sum(costs.cost_r(t) for t in trades)
    favorable_r = sum(outcomes[t.trade_id].favorable_move_price / t.stop_distance for t in trades)
    return {"trades": len(trades), "total_cost_r": cost_r, "total_favorable_r": favorable_r,
            "cost_to_favorable_move": cost_r / favorable_r if favorable_r > 0 else None}


def evaluate_market_filter(trades, contexts, outcomes, *, registry: v.HypothesisRegistry,
                           hypothesis_id: str, split: v.DataSplit, costs: v.CostModel,
                           as_of: datetime, code_sha256: str | None = None) -> dict:
    """Compare the ENTIRE supplied development cohort with its pre-registered filtered subset.

    Invalid trades fail before filtering: a WAIT cannot hide leakage or a duplicate. Holdout
    rows are rejected, not silently removed. The existing Stage 1 tool reports BOTH cohorts.
    DEVELOPMENT_IMPROVEMENT is not a stage clearance or strategy promotion.
    """
    as_of = v._utc(as_of)
    entry = v._registered_evaluation(registry, hypothesis_id, as_of, code_sha256)
    spec = entry["spec"]
    policy = FilterPolicy.from_spec(spec)
    if spec.get("data_split_sha256") != split.sha256:
        raise v.ValidationError("registered_data_split_mismatch")
    trades = tuple(trades)
    accepted, rejected = v.guard_trades(trades, split, "DEVELOPMENT", expected_side=spec["side"], as_of=as_of)
    if rejected:
        raise v.ValidationError("invalid_development_cohort:" + v.canonical(rejected))
    context_by_id = _index(contexts, "context")
    outcome_by_id = _index(outcomes, "outcome")
    ids = {t.trade_id for t in accepted}
    if set(context_by_id) - ids or set(outcome_by_id) != ids:
        raise v.ValidationError("market_rows_do_not_match_trade_cohort")
    for trade in accepted:
        context = context_by_id.get(trade.trade_id)
        if context is not None:
            if context.symbol != spec["symbol"]:
                raise v.ValidationError("context_symbol_not_registered")
            if context.observed_at > trade.entry_at:
                raise v.ValidationError("context_after_entry")
            if (split.period(context.window_start) != "DEVELOPMENT" or
                    split.period(context.observed_at) != "DEVELOPMENT" or
                    any(context.window_start < end and context.observed_at >= start
                        for start, end, _ in split.gaps)):
                raise v.ValidationError("context_window_outside_development_or_in_gap")
        outcome = outcome_by_id[trade.trade_id]
        if not trade.exit_at <= outcome.known_at <= as_of:
            raise v.ValidationError("favorable_outcome_not_known_at_evaluation")
        favorable_exit = max(0.0, costs.gross_r(trade) * trade.stop_distance)
        if outcome.favorable_move_price < favorable_exit:
            raise v.ValidationError("favorable_excursion_smaller_than_exit_move")
    decisions = [decide_filter(t, context_by_id.get(t.trade_id), policy, costs) for t in accepted]
    kept = [t for t, d in zip(accepted, decisions) if d["action"] == "KEEP_FOR_RESEARCH"]

    def stage1(rows):
        vault = v.HoldoutVault(rows, split, registry, registry.ledger.path.with_name("holdout-openings.jsonl"))
        return v.evaluate_development(vault, hypothesis_id, costs=costs, as_of=as_of, code_sha256=code_sha256)

    unfiltered, filtered = stage1(accepted), stage1(kept)
    before, after = _ratio(accepted, outcome_by_id, costs), _ratio(kept, outcome_by_id, costs)
    a, b = before["cost_to_favorable_move"], after["cost_to_favorable_move"]
    complete = len(context_by_id) == len(accepted)
    improved = bool(kept) and a is not None and b is not None and b < a
    verdict = ("NO_DATA" if not accepted else "INCOMPLETE_CONTEXT" if not complete else
               "DEVELOPMENT_IMPROVEMENT" if improved else "NO_IMPROVEMENT")
    input_data = {"trades": [asdict(t) for t in accepted],
                  "contexts": [asdict(context_by_id[k]) for k in sorted(context_by_id)],
                  "outcomes": [asdict(outcome_by_id[k]) for k in sorted(outcome_by_id)]}
    # Canonicalize UTC timestamps before hashing the evidence, including unused outcome values.
    def serial(value):
        if isinstance(value, datetime):
            return v._utc(value).isoformat()
        if isinstance(value, dict):
            return {k: serial(x) for k, x in value.items()}
        if isinstance(value, (tuple, list)):
            return [serial(x) for x in value]
        return value

    report = {"schema_version": 1, "tool": "katarina.research.market_intelligence",
              "stage": "TAHAP_2_DEVELOPMENT_RESEARCH", "as_of_utc": as_of.isoformat(),
              "hypothesis_id": hypothesis_id, "filter_policy": asdict(policy),
              "split_sha256": split.sha256, "input_sha256": v.sha256_text(v.canonical(serial(input_data))),
              "trial_count": registry.trial_count(), "decisions": decisions,
              "wait_reasons": dict(sorted(Counter(r for d in decisions for r in d["reasons"]).items())),
              "comparison": {"unfiltered": before, "filtered": after, "improved": improved},
              "stage1": {"unfiltered": unfiltered, "filtered": filtered},
              "verdict": verdict, "stage_clearance_granted": False, "promotion_authorized": False,
              "demo_execution_authorized": False, "live_execution_authorized": False,
              "note": "Development comparison only; tick activity is a proxy, not measured liquidity. "
                      "Source hashes are provenance references, not independent source verification."}
    report["report_sha256"] = v.sha256_text(v.canonical(report))
    return report
