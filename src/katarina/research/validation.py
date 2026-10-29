"""Stage 1 validation tool: the single judge for every later stage (docs/ROADMAP.md, Tahap 1).

Protocol: docs/research/VALIDATION_PROTOCOL.md. The pieces:

* :class:`HypothesisRegistry` — append-only, hash-chained registry. A hypothesis is registered
  *before* it is tested; its id is the SHA-256 of its canonical definition, so any change is a new
  hypothesis and a new trial. The registry size is the trial count used for correction.
* :class:`DataSplit` — development and holdout periods fixed by date, plus recorded GAP periods.
* :class:`HoldoutVault` — the only way to read holdout trades. Opening appends to a hash-chained
  ledger, requires a registered hypothesis and a finished holdout, and works once per hypothesis.
* :class:`CostModel` — net R from observed spread at entry and exit, slippage and commission.
* Leakage guard — trades whose inputs postdate entry, that cross the dev/holdout boundary, start
  in a GAP, overlap, or are learned before they close are rejected.
* Baselines — no trade, random side at the same timing (same exits and costs), simple trend rule.
* Weekly-block bootstrap lower bound with Bonferroni correction for the trial count.
* :func:`evaluate_development` / :func:`evaluate_holdout` — deterministic reports with ``report_sha256``.

No broker access, no orders, no live authority. A PASS is research evidence for the promotion
gate, which additionally needs the Owner's approval.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random

SIDES = ("BUY", "SELL")
PROMOTION_MIN_TRADES = 100
PROMOTION_MIN_PROFIT_FACTOR = 1.2
CONFIDENCE = 0.95
BOOTSTRAP_RESAMPLES = 4000
REQUIRED_SPEC_FIELDS = ("name", "symbol", "side", "regime", "playbook", "rules", "parameters")


class ValidationError(ValueError):
    """Input that the validation tool must refuse (bad spec, leakage, tampering)."""


class HoldoutAlreadyOpened(ValidationError):
    pass


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utc(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValidationError("aware_utc_datetime_required")
    return value.astimezone(timezone.utc)


from katarina.intelligence.operations.data_health import _nth_sunday


def is_us_dst(moment: datetime) -> bool:
    """US Daylight Saving Time: 2nd Sunday in March 02:00 EST (07:00 UTC) to 1st Sunday in Nov 02:00 EDT (06:00 UTC)."""
    moment = _utc(moment)
    year = moment.year
    start_date = _nth_sunday(year, 3, 2)
    end_date = _nth_sunday(year, 11, 1)
    start_utc = datetime(year, 3, start_date.day, 7, 0, tzinfo=timezone.utc)
    end_utc = datetime(year, 11, end_date.day, 6, 0, tzinfo=timezone.utc)
    return start_utc <= moment < end_utc


def calculate_rollover_nights(entry_at: datetime, exit_at: datetime, triple_swap_weekday: int = 2) -> int:
    """Calculates rollover nights (17:00 NY time) between entry_at < t <= exit_at for Mon-Fri."""
    entry_at = _utc(entry_at)
    exit_at = _utc(exit_at)
    if entry_at >= exit_at:
        return 0
    nights = 0
    current_day = (entry_at - timedelta(days=1)).date()
    end_day = (exit_at + timedelta(days=1)).date()
    while current_day <= end_day:
        if current_day.weekday() < 5:  # Monday (0) to Friday (4)
            check_utc = datetime(current_day.year, current_day.month, current_day.day, 21, 0, tzinfo=timezone.utc)
            rollover_hour = 21 if is_us_dst(check_utc) else 22
            rollover_utc = datetime(current_day.year, current_day.month, current_day.day, rollover_hour, 0, tzinfo=timezone.utc)
            if entry_at < rollover_utc <= exit_at:
                nights += 3 if current_day.weekday() == triple_swap_weekday else 1
        current_day += timedelta(days=1)
    return nights


# --------------------------------------------------------------------------- append-only ledgers

class _ChainedLedger:
    """JSON lines where every entry carries the hash of the previous one."""

    def __init__(self, path):
        self.path = Path(path)

    def entries(self) -> list[dict]:
        if not self.path.is_file():
            return []
        previous = "0" * 64
        entries = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            entry = json.loads(line)
            body = {k: v for k, v in entry.items() if k != "entry_sha256"}
            if entry.get("previous_sha256") != previous or sha256_text(canonical(body)) != entry.get("entry_sha256"):
                raise ValidationError(f"ledger_tampered:{self.path.name}:{number}")
            previous = entry["entry_sha256"]
            entries.append(entry)
        return entries

    def append(self, body: dict) -> dict:
        entries = self.entries()
        body = dict(body, previous_sha256=entries[-1]["entry_sha256"] if entries else "0" * 64)
        entry = dict(body, entry_sha256=sha256_text(canonical(body)))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical(entry) + "\n")
        return entry


class HypothesisRegistry:
    def __init__(self, path):
        self.ledger = _ChainedLedger(path)

    @staticmethod
    def hypothesis_id(spec: dict) -> str:
        return sha256_text(canonical(_checked_spec(spec)))

    def register(self, spec: dict, *, registered_utc: datetime) -> dict:
        """Register before testing. An identical definition is not a new trial."""
        spec = _checked_spec(spec)
        hid = sha256_text(canonical(spec))
        for entry in self.ledger.entries():
            if entry["hypothesis_id"] == hid:
                return entry
        return self.ledger.append({"kind": "HYPOTHESIS", "hypothesis_id": hid,
                                   "registered_utc": _utc(registered_utc).isoformat(), "spec": spec})

    def get(self, hid: str) -> dict | None:
        return next((e for e in self.ledger.entries() if e["hypothesis_id"] == hid), None)

    def trial_count(self) -> int:
        return len(self.ledger.entries())


def _checked_spec(spec: dict) -> dict:
    if not isinstance(spec, dict) or any(key not in spec for key in REQUIRED_SPEC_FIELDS):
        raise ValidationError("spec_requires:" + ",".join(REQUIRED_SPEC_FIELDS))
    if spec["side"] not in SIDES:
        raise ValidationError("spec_side_must_be_BUY_or_SELL")
    for key in ("name", "symbol", "regime", "playbook", "rules"):
        if not isinstance(spec[key], str) or not spec[key].strip():
            raise ValidationError(f"spec_{key}_required")
    if not isinstance(spec["parameters"], dict):
        raise ValidationError("spec_parameters_must_be_object")
    code = spec.get("code_sha256")
    if code is not None and not re.fullmatch("[0-9a-f]{64}", str(code)):
        raise ValidationError("spec_code_sha256_invalid")
    json.loads(canonical(spec))  # rejects NaN/inf and non-JSON values
    return spec


# --------------------------------------------------------------------------- data split

@dataclass(frozen=True)
class DataSplit:
    development_start: datetime
    development_end: datetime
    holdout_start: datetime
    holdout_end: datetime
    gaps: tuple = ()  # ((start, end, reason), ...)

    def __post_init__(self):
        for name in ("development_start", "development_end", "holdout_start", "holdout_end"):
            object.__setattr__(self, name, _utc(getattr(self, name)))
        gaps = tuple((_utc(s), _utc(e), str(r)) for s, e, r in self.gaps)
        object.__setattr__(self, "gaps", gaps)
        if not (self.development_start < self.development_end <= self.holdout_start < self.holdout_end):
            raise ValidationError("split_periods_must_be_ordered_and_disjoint")
        if any(not (s < e) for s, e, _ in gaps):
            raise ValidationError("gap_must_have_positive_length")

    def as_dict(self) -> dict:
        return {"development_start": self.development_start.isoformat(),
                "development_end": self.development_end.isoformat(),
                "holdout_start": self.holdout_start.isoformat(),
                "holdout_end": self.holdout_end.isoformat(),
                "gaps": [[s.isoformat(), e.isoformat(), r] for s, e, r in self.gaps]}

    @property
    def sha256(self) -> str:
        return sha256_text(canonical(self.as_dict()))

    def period(self, moment: datetime) -> str:
        moment = _utc(moment)
        if any(s <= moment < e for s, e, _ in self.gaps):
            return "GAP"
        if self.development_start <= moment < self.development_end:
            return "DEVELOPMENT"
        if self.holdout_start <= moment < self.holdout_end:
            return "HOLDOUT"
        return "OUTSIDE"

    def end_of(self, period: str) -> datetime:
        return self.development_end if period == "DEVELOPMENT" else self.holdout_end


# --------------------------------------------------------------------------- trades and costs

@dataclass(frozen=True)
class Trade:
    """One simulated or observed trade, priced at mid with observed spreads.

    ``data_until`` is the newest market data the decision used; it must not be after ``entry_at``.
    ``trend_side`` is an optional causal trend label at entry used by the trend baseline.
    """
    trade_id: str
    side: str
    entry_at: datetime
    exit_at: datetime
    known_at: datetime
    data_until: datetime
    entry_mid: float
    exit_mid: float
    stop_distance: float
    spread_entry: float
    spread_exit: float
    trend_side: str | None = None

    @classmethod
    def from_dict(cls, row: dict) -> "Trade":
        try:
            return cls(trade_id=str(row["trade_id"]), side=str(row["side"]),
                       entry_at=_utc(row["entry_at"]), exit_at=_utc(row["exit_at"]),
                       known_at=_utc(row["known_at"]), data_until=_utc(row["data_until"]),
                       entry_mid=float(row["entry_mid"]), exit_mid=float(row["exit_mid"]),
                       stop_distance=float(row["stop_distance"]), spread_entry=float(row["spread_entry"]),
                       spread_exit=float(row["spread_exit"]), trend_side=row.get("trend_side"))
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError(f"trade_row_invalid:{type(error).__name__}") from None


@dataclass(frozen=True)
class CostModel:
    """All costs in price units of the instrument; observed spread is charged half at entry and exit."""
    slippage_per_side: float = 0.0
    commission_round_trip: float = 0.0
    swap_long_per_night: float = 0.0
    swap_short_per_night: float = 0.0
    triple_swap_weekday: int = 2

    def __post_init__(self):
        if not all(math.isfinite(v) and v >= 0 for v in (self.slippage_per_side, self.commission_round_trip,
                                                        self.swap_long_per_night, self.swap_short_per_night)):
            raise ValidationError("cost_model_values_must_be_finite_and_non_negative")
        if type(self.triple_swap_weekday) is not int or not (0 <= self.triple_swap_weekday <= 6):
            raise ValidationError("triple_swap_weekday_must_be_int_between_0_and_6")

    def swap_cost(self, trade: Trade, side: str | None = None) -> float:
        trade_side = side or trade.side
        rate = self.swap_long_per_night if trade_side == "BUY" else self.swap_short_per_night
        if rate <= 0:
            return 0.0
        nights = calculate_rollover_nights(trade.entry_at, trade.exit_at, self.triple_swap_weekday)
        return nights * rate

    def cost_r(self, trade: Trade, side: str | None = None) -> float:
        price = (trade.spread_entry / 2 + trade.spread_exit / 2 + 2 * self.slippage_per_side
                 + self.commission_round_trip + self.swap_cost(trade, side))
        return price / trade.stop_distance

    @staticmethod
    def gross_r(trade: Trade, side: str | None = None) -> float:
        direction = 1 if (side or trade.side) == "BUY" else -1
        return direction * (trade.exit_mid - trade.entry_mid) / trade.stop_distance

    def net_r(self, trade: Trade, side: str | None = None) -> float:
        return self.gross_r(trade, side) - self.cost_r(trade, side)


def guard_trades(trades, split: DataSplit, period: str, *, expected_side: str | None = None,
                 as_of: datetime | None = None):
    """Leakage guard. Returns (accepted, rejected) where rejected is [(trade_id, reason)]."""
    accepted, rejected, seen = [], [], set()
    last_exit = None
    for trade in sorted(trades, key=lambda t: (t.entry_at, t.trade_id)):
        reason = None
        values = (trade.entry_mid, trade.exit_mid, trade.stop_distance, trade.spread_entry, trade.spread_exit)
        if trade.trade_id in seen or not trade.trade_id:
            reason = "DUPLICATE_OR_EMPTY_ID"
        elif trade.side not in SIDES or (expected_side and trade.side != expected_side):
            reason = "SIDE_NOT_REGISTERED"
        elif not all(math.isfinite(v) for v in values) or trade.stop_distance <= 0 or min(values[3:]) < 0:
            reason = "INVALID_PRICES"
        elif trade.data_until > trade.entry_at:
            reason = "LOOKAHEAD_DATA_AFTER_ENTRY"
        elif not trade.entry_at < trade.exit_at <= trade.known_at:
            reason = "OUTCOME_KNOWN_BEFORE_EXIT"
        elif as_of is not None and trade.known_at > _utc(as_of):
            reason = "OUTCOME_NOT_YET_KNOWN"
        elif split.period(trade.entry_at) == "GAP":
            reason = "ENTRY_IN_GAP"
        elif split.period(trade.entry_at) != period:
            reason = "OUTSIDE_PERIOD"
        elif trade.exit_at > split.end_of(period):
            reason = "CROSSES_PERIOD_END"
        elif any(trade.entry_at < end and trade.exit_at >= start for start, end, _ in split.gaps):
            reason = "POSITION_CROSSES_GAP"
        elif last_exit is not None and trade.entry_at < last_exit:
            reason = "OVERLAPPING_POSITION"
        if reason:
            rejected.append((trade.trade_id, reason))
            continue
        seen.add(trade.trade_id)
        last_exit = trade.exit_at
        accepted.append(trade)
    return accepted, rejected


# --------------------------------------------------------------------------- holdout vault

class HoldoutVault:
    """Holds the trades of one data source; holdout trades only leave through :meth:`open`."""

    def __init__(self, trades, split: DataSplit, registry: HypothesisRegistry, ledger_path, *, holdout_loader=None):
        self.split = split
        self.registry = registry
        self.ledger = _ChainedLedger(ledger_path)
        self.__trades = tuple(trades)
        self.__holdout_loader = holdout_loader

    def development(self) -> tuple:
        # Keep GAP rows inside the requested date range so the guard rejects them visibly.
        return tuple(t for t in self.__trades
                     if self.split.development_start <= t.entry_at < self.split.development_end)

    def openings(self) -> list[dict]:
        return self.ledger.entries()

    def open(self, hypothesis_id: str, *, opened_by: str, now: datetime, reason: str) -> tuple:
        now = _utc(now)
        registered = self.registry.get(hypothesis_id)
        if registered is None:
            raise ValidationError("holdout_requires_registered_hypothesis")
        registered_at = _utc(registered["registered_utc"])
        if registered_at > now:
            raise ValidationError("hypothesis_registered_in_future")
        if now < self.split.holdout_end:
            raise ValidationError("holdout_not_finished")
        if not str(opened_by).strip() or not str(reason).strip():
            raise ValidationError("holdout_opening_requires_who_and_why")
        openings = self.ledger.entries()
        if any(e["hypothesis_id"] == hypothesis_id for e in openings):
            raise HoldoutAlreadyOpened(hypothesis_id)
        for previous in openings:
            # A revised hypothesis registered after exposure needs a new, disjoint holdout.
            # Legacy receipts lack dates: conservatively refuse reuse after exposure.
            start, end = previous.get("holdout_start"), previous.get("holdout_end")
            overlaps = (start is None or end is None or
                        self.split.holdout_start < _utc(end) and _utc(start) < self.split.holdout_end)
            if registered_at >= _utc(previous["opened_utc"]) and overlaps:
                raise ValidationError("new_hypothesis_requires_unseen_holdout")
        self.ledger.append({"kind": "HOLDOUT_OPENED", "hypothesis_id": hypothesis_id,
                            "opened_utc": now.isoformat(), "opened_by": str(opened_by), "reason": str(reason),
                            "split_sha256": self.split.sha256,
                            "holdout_start": self.split.holdout_start.isoformat(),
                            "holdout_end": self.split.holdout_end.isoformat()})
        trades = self.__holdout_loader() if self.__holdout_loader is not None else self.__trades
        return tuple(t for t in trades
                     if self.split.holdout_start <= t.entry_at < self.split.holdout_end)


# --------------------------------------------------------------------------- statistics

def summarize(values) -> dict:
    values = list(values)
    n = len(values)
    wins = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    cumulative = peak = drawdown = 0.0
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        drawdown = max(drawdown, peak - cumulative)
    return {"trades": n, "total_r": _round(sum(values)), "expectancy_r": _round(sum(values) / n) if n else None,
            "profit_factor": _round(wins / losses) if losses else None,
            "win_rate": _round(sum(v > 0 for v in values) / n) if n else None,
            "max_drawdown_r": _round(drawdown)}


def _round(value):
    return None if value is None else round(float(value), 6)


def weekly_blocks(trades, values) -> list[list[float]]:
    blocks = {}
    for trade, value in zip(trades, values):
        iso = trade.entry_at.isocalendar()
        blocks.setdefault((iso.year, iso.week), []).append(value)
    return [blocks[key] for key in sorted(blocks)]


def block_bootstrap_lower(blocks, *, trials: int, seed: str, resamples: int = BOOTSTRAP_RESAMPLES):
    """One-sided lower bound of mean R at confidence 1 - 0.05/trials (Bonferroni)."""
    if type(trials) is not int or trials < 1:
        raise ValidationError("trial_count_required")
    if len(blocks) < 2:
        return None, 0.05 / trials
    rng = Random(int(sha256_text(seed)[:16], 16))
    means = []
    for _ in range(resamples):
        sample = [blocks[rng.randrange(len(blocks))] for _ in blocks]
        means.append(sum(map(sum, sample)) / sum(map(len, sample)))
    means.sort()
    alpha = (1 - CONFIDENCE) / trials
    return _round(means[max(0, math.floor(alpha * resamples) - 1)]), alpha


def baselines(trades, costs: CostModel, seed: str) -> dict:
    """Comparators on the same trades: no trade, random side (same timing/exit/cost), trend rule."""
    rng = Random(int(sha256_text("random-side:" + seed)[:16], 16))
    draws = []
    for _ in range(1000):
        draws.append(sum(costs.net_r(t, rng.choice(SIDES)) for t in trades))
    draws.sort()
    trend = [t for t in trades if t.trend_side in SIDES]
    trend_values = [costs.net_r(t, t.trend_side) for t in trend]
    expected_random_cost = (
        sum((costs.cost_r(t, "BUY") + costs.cost_r(t, "SELL")) / 2 for t in trades) / len(trades)
        if trades else None
    )
    return {
        "no_trade": {"expectancy_r": 0.0, "total_r": 0.0},
        "random_side_same_timing": {
            "expected_expectancy_r": _round(-expected_random_cost) if expected_random_cost is not None else None,
            "simulated_total_r_p50": _round(draws[499]) if trades else None,
            "simulated_total_r_p95": _round(draws[949]) if trades else None},
        "trend_rule": {"labelled_trades": len(trend),
                       "expectancy_r": _round(sum(trend_values) / len(trend)) if trend else None},
    }


def walk_forward(trades, values, split: DataSplit, *, fold_days: int = 28) -> list[dict]:
    """Consecutive, non-overlapping development folds (time order preserved)."""
    if type(fold_days) is not int or fold_days < 7:
        raise ValidationError("fold_days_at_least_7")
    folds, start = [], split.development_start
    while start < split.development_end:
        end = min(start + timedelta(days=fold_days), split.development_end)
        chosen = [v for t, v in zip(trades, values) if start <= t.entry_at < end]
        folds.append({"start": start.isoformat(), "end": end.isoformat(), **summarize(chosen)})
        start = end
    return folds


# --------------------------------------------------------------------------- report

@dataclass(frozen=True)
class Evaluation:
    hypothesis_id: str
    period: str
    split: DataSplit
    costs: CostModel = field(default_factory=CostModel)


def evaluate_development(vault: HoldoutVault, hypothesis_id: str, *, costs: CostModel, as_of: datetime,
                         code_sha256: str | None = None) -> dict:
    """Development-period report; never touches holdout trades."""
    evaluation = Evaluation(hypothesis_id, "DEVELOPMENT", vault.split, costs)
    return _build_report(evaluation, vault.development(), vault.registry, as_of=as_of, code_sha256=code_sha256)


def evaluate_holdout(vault: HoldoutVault, hypothesis_id: str, *, costs: CostModel, opened_by: str, reason: str,
                     now: datetime, code_sha256: str | None = None) -> dict:
    """Open the holdout (recorded, once per hypothesis) and report on it."""
    _registered_evaluation(vault.registry, hypothesis_id, now, code_sha256)
    trades = vault.open(hypothesis_id, opened_by=opened_by, now=now, reason=reason)
    evaluation = Evaluation(hypothesis_id, "HOLDOUT", vault.split, costs)
    report = _build_report(evaluation, trades, vault.registry, as_of=now, code_sha256=code_sha256,
                           opening=vault.openings()[-1])
    return report


def _registered_evaluation(registry, hypothesis_id, as_of, code_sha256):
    entry = registry.get(hypothesis_id)
    if entry is None:
        raise ValidationError("hypothesis_not_registered")
    if _utc(entry["registered_utc"]) > _utc(as_of):
        raise ValidationError("hypothesis_registered_in_future")
    if code_sha256 is not None and not re.fullmatch("[0-9a-f]{64}", str(code_sha256)):
        raise ValidationError("evaluation_code_sha256_invalid")
    if entry["spec"].get("code_sha256") is not None and code_sha256 != entry["spec"]["code_sha256"]:
        raise ValidationError("evaluation_code_does_not_match_registered_hypothesis")
    return entry


def _build_report(evaluation: Evaluation, trades, registry: HypothesisRegistry, *, as_of: datetime,
                  code_sha256: str | None = None, opening: dict | None = None) -> dict:
    """Deterministic report for one hypothesis on one period ("DEVELOPMENT" or "HOLDOUT")."""
    if (evaluation.period == "HOLDOUT") != (opening is not None):
        raise ValidationError("holdout_report_requires_recorded_opening")
    entry = _registered_evaluation(registry, evaluation.hypothesis_id, as_of, code_sha256)
    if evaluation.period not in ("DEVELOPMENT", "HOLDOUT"):
        raise ValidationError("period_must_be_DEVELOPMENT_or_HOLDOUT")
    spec = entry["spec"]
    as_of = _utc(as_of)
    split, costs = evaluation.split, evaluation.costs
    accepted, rejected = guard_trades(trades, split, evaluation.period, expected_side=spec["side"], as_of=as_of)
    values = [costs.net_r(t) for t in accepted]
    trials = registry.trial_count()
    seed = evaluation.hypothesis_id + evaluation.period + split.sha256
    lower, alpha = block_bootstrap_lower(weekly_blocks(accepted, values), trials=trials, seed=seed)
    stats = summarize(values)
    stats["gross_expectancy_r"] = _round(sum(costs.gross_r(t) for t in accepted) / len(accepted)) if accepted else None
    stats["mean_cost_r"] = _round(sum(costs.cost_r(t) for t in accepted) / len(accepted)) if accepted else None
    stats["weeks"] = len(weekly_blocks(accepted, values))

    gross_exp = stats["gross_expectancy_r"]
    mean_cost = stats["mean_cost_r"]
    net_1_5_values = [costs.gross_r(t) - 1.5 * costs.cost_r(t) for t in accepted]
    net_2_0_values = [costs.gross_r(t) - 2.0 * costs.cost_r(t) for t in accepted]
    net_1_5_exp = _round(sum(net_1_5_values) / len(accepted)) if accepted else None
    net_2_0_exp = _round(sum(net_2_0_values) / len(accepted)) if accepted else None
    breakeven_mult = _round(gross_exp / mean_cost) if (gross_exp is not None and mean_cost is not None and mean_cost > 0 and gross_exp > 0) else None

    if gross_exp is None or gross_exp <= 0:
        cost_verdict = "NO_GROSS_EDGE"
    elif stats["expectancy_r"] is None or stats["expectancy_r"] <= 0:
        cost_verdict = "NOT_ECONOMIC_AFTER_COSTS"
    else:
        cost_verdict = "POSITIVE_AFTER_COSTS"

    cost_sensitivity = {
        "net_expectancy_r_1_5x": net_1_5_exp,
        "net_expectancy_r_2_0x": net_2_0_exp,
        "breakeven_cost_multiple": breakeven_mult,
        "cost_verdict": cost_verdict,
    }

    base = baselines(accepted, costs, seed)
    expectancy = stats["expectancy_r"]
    comparators = [0.0, base["random_side_same_timing"]["expected_expectancy_r"], base["trend_rule"]["expectancy_r"]]
    baseline_complete = bool(accepted) and base["trend_rule"]["labelled_trades"] == len(accepted)
    beats = (baseline_complete and expectancy is not None
             and all(c is not None and expectancy > c for c in comparators))
    gates = {
        "all_baselines_available": baseline_complete,
        "net_expectancy_positive": expectancy is not None and expectancy > 0,
        "beats_all_baselines": beats,
        "no_rejected_trades": not rejected,
    }
    if evaluation.period == "HOLDOUT":
        gates.update({
            "min_trades": stats["trades"] >= PROMOTION_MIN_TRADES,
            "profit_factor": stats["profit_factor"] is not None and stats["profit_factor"] >= PROMOTION_MIN_PROFIT_FACTOR,
            "bootstrap_lower_bound_positive": lower is not None and lower > 0,
        })
    if rejected:
        verdict = "FAIL"
    elif evaluation.period == "HOLDOUT" and not gates["min_trades"]:
        verdict = "PENDING_INSUFFICIENT_SAMPLE"
    elif not accepted:
        verdict = "NO_TRADES"
    else:
        verdict = "PASS" if all(gates.values()) else "FAIL"
    report = {
        "schema_version": 1,
        "tool": "katarina.research.validation",
        "as_of_utc": _utc(as_of).isoformat(),
        "hypothesis_id": evaluation.hypothesis_id,
        "hypothesis": spec,
        "registered_utc": entry["registered_utc"],
        "period": evaluation.period,
        "split": split.as_dict(),
        "split_sha256": split.sha256,
        "code_sha256": code_sha256,
        "cost_model": asdict(costs),
        "trial_count": trials,
        "registry_head_sha256": registry.ledger.entries()[-1]["entry_sha256"],
        "holdout_opening_sha256": opening["entry_sha256"] if opening else None,
        "familywise_alpha": _round(alpha),
        "confidence": CONFIDENCE,
        "statistics": stats,
        "cost_sensitivity": cost_sensitivity,
        "weekly_block_bootstrap_lower_expectancy_r": lower,
        "baselines": base,
        "walk_forward": walk_forward(accepted, values, split) if evaluation.period == "DEVELOPMENT" else [],
        "rejected_trades": [{"trade_id": i, "reason": r} for i, r in rejected],
        "gates": gates,
        "verdict": verdict,
        "live_execution_authorized": False,
        "note": "Research evidence only. Promotion also needs an Owner-approved record (docs/ROADMAP.md).",
    }
    report["report_sha256"] = sha256_text(canonical(report))
    return report


def write_report(report: dict, path) -> str:
    """Write canonical JSON (LF, sorted keys) and return the file's SHA-256 for a promotion record."""
    text = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
