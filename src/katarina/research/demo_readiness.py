"""Stage 3 preparation: restrictive risk adapter and read-only existing-outbox reports.

Nothing here activates the demo worker or authorizes trading. Runtime integration and
final profile values remain separate from these offline, synthetic-testable tools.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math

from katarina.engines.risk import RiskAction, RiskDecision


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class DemoRiskLimits:
    # No defaults: these are experiment parameters, not Owner-approved runtime policy.
    per_trade_fraction: float
    daily_stop_fraction: float

    def __post_init__(self):
        if (not _finite(self.per_trade_fraction) or not 0 < self.per_trade_fraction <= .05 or
                not _finite(self.daily_stop_fraction) or not 0 < self.daily_stop_fraction <= .35):
            raise ValueError("demo_limits_cannot_expand_main_safety_limits")


class DemoRiskOverlay:
    """Wrap the SAME governor; never recompute or override its risk approval.

    Compatible with DemoExecutionBoundary's governor interface for sandbox tests.
    The existing boundary still verifies account identity, cash loss, minimum lot,
    freshness, outbox state and broker protection. This adapter never sizes a lot.
    """
    def __init__(self, governor, limits: DemoRiskLimits):
        if not isinstance(limits, DemoRiskLimits) or not callable(getattr(governor, "evaluate", None)):
            raise ValueError("governor_and_explicit_demo_limits_required")
        self.governor, self.limits = governor, limits

    def evaluate(self, request):
        try:
            decision = self.governor.evaluate(request)
        except Exception:
            return RiskDecision(RiskAction.PAUSE, 0.0, "demo_upstream_evaluation_failed")
        if not isinstance(decision, RiskDecision):
            return RiskDecision(RiskAction.PAUSE, 0.0, "demo_invalid_upstream_decision")
        if decision.action in (RiskAction.REJECT, RiskAction.PAUSE):
            return decision
        if (decision.action not in (RiskAction.APPROVE, RiskAction.REDUCE) or
                not _finite(decision.approved_fraction) or not 0 < decision.approved_fraction <= .05):
            return RiskDecision(RiskAction.PAUSE, 0.0, "demo_invalid_upstream_budget")
        daily = getattr(request, "daily_drawdown_fraction", None)
        if not _finite(daily) or not 0 <= daily <= 1:
            return RiskDecision(RiskAction.PAUSE, 0.0, "demo_invalid_daily_drawdown")
        if daily >= self.limits.daily_stop_fraction:
            return RiskDecision(RiskAction.PAUSE, 0.0, "demo_daily_stop")
        approved = min(decision.approved_fraction, self.limits.per_trade_fraction)
        if approved < decision.approved_fraction:
            return RiskDecision(RiskAction.REDUCE, approved, "demo_per_trade_cap")
        return decision


# OPEN is reconciled exposure, not a completed trade or a profitable outcome.
SETTLED_STATES = frozenset({"OPEN", "CLOSED", "REJECTED", "CHECK_REJECTED", "CANCELLED", "NOT_FILLED"})
REJECTED_STATES = frozenset({"REJECTED", "CHECK_REJECTED"})


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _stats(outcomes):
    # Observation-order strategy P/L, not account equity, floating P/L or cashflow-aware HWM.
    values = [o["net_profit_native"] for o in outcomes]
    wins = sum(x for x in values if x > 0)
    losses = -sum(x for x in values if x < 0)
    total = peak = dd = 0.0
    for value in values:
        total += value
        peak = max(peak, total)
        dd = max(dd, peak - total)
    return {"closed_trades": len(values), "net_profit_native": total,
            "expectancy_native": total / len(values) if values else None,
            "profit_factor": wins / losses if losses else None,
            "profit_factor_state": "FINITE" if losses else "NO_LOSSES" if wins else "UNDEFINED",
            "win_rate_net": sum(x > 0 for x in values) / len(values) if values else None,
            "realized_observation_order_drawdown_native": dd,
            "commission_native": sum(o["commission_native"] for o in outcomes),
            "swap_native": sum(o["swap_native"] for o in outcomes),
            "fee_native": sum(o["fee_native"] for o in outcomes)}


def summarize_demo_outbox(db, *, currency: str, regimes=None, decisions=()):
    """Read the existing demo_outbox; no broker calls, schema changes or reconciliation writes.

    Currency and optional regime labels are caller-supplied metadata for ONE account.
    Only valid CLOSED broker outcomes enter performance; uncertainty blocks readiness.
    """
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("single_account_currency_required")
    regimes = dict(regimes or {})
    if any(not isinstance(v, str) or not v.strip() for v in regimes.values()):
        raise ValueError("invalid_regime_labels")
    decisions = list(decisions)
    waits = Counter()
    seen = set()
    for row in decisions:
        ident, action = row.get("decision_id"), row.get("action")
        if not isinstance(ident, str) or not ident or ident in seen or action not in ("BUY", "SELL", "WAIT"):
            raise ValueError("invalid_or_duplicate_decision")
        seen.add(ident)
        if action == "WAIT":
            reasons = row.get("reasons")
            if (not isinstance(reasons, list) or not reasons or
                    any(not isinstance(r, str) or not r.strip() for r in reasons)):
                raise ValueError("wait_requires_reasons")
            waits.update(set(reasons))
    rows = db.execute("SELECT intent_id,state,intent_json,outcome_json,position_id FROM demo_outbox ORDER BY intent_id").fetchall()
    if set(regimes) - {r[0] for r in rows}:
        raise ValueError("regime_label_has_no_intent")
    states, problems = Counter(), Counter()
    positions = Counter(r[4] for r in rows if r[4] is not None)
    settled = 0
    closed = []
    for ident, state, raw_intent, raw_outcome, position_id in rows:
        states[state] += 1
        if state not in SETTLED_STATES:
            problems["UNRESOLVED_STATE:" + state] += 1
            continue
        if state in ("OPEN", "CLOSED") and (type(position_id) is not int or position_id <= 0 or positions[position_id] != 1):
            problems["INVALID_OR_DUPLICATE_POSITION"] += 1
            continue
        if state != "CLOSED":
            settled += 1
            continue
        try:
            intent, outcome = json.loads(raw_intent), json.loads(raw_outcome)
            if not isinstance(intent, dict) or not isinstance(outcome, dict):
                raise ValueError()
            fields = ("net_profit_native", "commission_native", "swap_native", "fee_native", "closed_observed_at")
            if any(not _finite(outcome.get(k)) for k in fields):
                raise ValueError()
            if (outcome.get("prospective_broker_outcome") is not True or
                    outcome.get("live_authorized") is not False or outcome["closed_observed_at"] <= 0 or
                    not _finite(outcome.get("entry_volume")) or outcome["entry_volume"] <= 0 or
                    type(outcome.get("deal_count")) is not int or outcome["deal_count"] < 2 or
                    intent.get("side") not in ("BUY", "SELL") or
                    not isinstance(intent.get("symbol"), str) or not intent["symbol"].strip()):
                raise ValueError()
            slip = outcome.get("entry_slippage_price")
            if slip is not None and not _finite(slip):
                raise ValueError()
        except (TypeError, ValueError):
            problems["INVALID_CLOSED_OUTCOME"] += 1
            continue
        settled += 1
        closed.append((outcome["closed_observed_at"], ident, intent, outcome))
    closed.sort(key=lambda x: (x[0], x[1]))
    groups, slips = defaultdict(list), defaultdict(list)
    missing_slippage = missing_regime = 0
    for _, ident, intent, outcome in closed:
        regime = regimes.get(ident)
        missing_regime += int(regime is None)
        groups[(intent["symbol"], intent["side"], regime)].append(outcome)
        if outcome.get("entry_slippage_price") is None:
            missing_slippage += 1
        else:
            slips[intent["symbol"]].append(outcome["entry_slippage_price"])
    report = {"schema_version": 1, "tool": "katarina.research.demo_readiness",
              "currency": currency, "currency_source": "CALLER_SINGLE_ACCOUNT_DECLARATION",
              "outbox_states": dict(sorted(states.items())), "outbox_rows": len(rows),
              "reconciliation": {"settled_rows": settled, "unresolved_rows": len(rows) - settled,
                                 "rate": settled / len(rows) if rows else None,
                                 "status": "NO_DATA" if not rows else "COMPLETE" if settled == len(rows) else "INCOMPLETE",
                                 "problems": dict(sorted(problems.items()))},
              "performance": _stats([o for _, _, _, o in closed]),
              "by_symbol_side_regime": [dict(symbol=k[0], side=k[1], regime=k[2], **_stats(items))
                                        for k, items in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1], x[0][2] or ""))],
              "entry_slippage_by_symbol": {symbol: {"samples": len(values), "mean_adverse_price": sum(values) / len(values)}
                                           for symbol, values in sorted(slips.items())},
              "coverage": {"closed_without_slippage": missing_slippage, "closed_without_regime": missing_regime,
                           "decision_rows_supplied": len(decisions)},
              "wait_reasons": dict(sorted(waits.items())),
              "rejected_orders": sum(states[s] for s in REJECTED_STATES),
              "input_sha256": _hash({"outbox": rows, "regimes": regimes, "currency": currency,
                                     "decisions": sorted(decisions, key=lambda x: x["decision_id"])}),
              "stage_clearance_granted": False, "demo_execution_authorized": False, "live_execution_authorized": False,
              "note": "Stored outbox evidence only, not a fresh broker audit. Net P/L already includes signed "
                      "commission/swap/fee; do not subtract again. Drawdown excludes open exposure and cashflows; "
                      "win rate is not calibrated forecast accuracy. Spread cost is embedded in fills, not separately measured."}
    report["report_sha256"] = _hash(report)
    return report
