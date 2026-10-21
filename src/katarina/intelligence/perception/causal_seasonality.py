"""Point-in-time seasonality for KATARINA (research/shadow context only).

Historical *known-at* timestamps prevent labels from the future entering priors.
Session/hour effects are per symbol; never transferred across instruments.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Sequence


@dataclass(frozen=True)
class HistoricalOutcome:
    symbol: str
    observed_at_utc: datetime
    label_known_at_utc: datetime
    direction_up: bool


@dataclass(frozen=True)
class SeasonalEstimate:
    symbol: str
    hour_utc: int
    weekday_utc: int
    baseline_up_rate: float
    hour_up_rate: float
    hour_samples: int
    weekday_up_rate: float
    weekday_samples: int
    directional_tilt: float
    research_only: bool = True


class CausalSeasonality:
    """Smoothed time-of-day/day-of-week association, NOT a trading signal.

    Do not treat seasonal bias as a forecast of net returns. A minimum sample
    budget is required before using any effect; otherwise neutral = 0 tilt.
    """

    def __init__(self, min_bin_samples: int = 25, prior_weight: int = 100):
        if min_bin_samples < 5 or prior_weight < 1:
            raise ValueError("invalid seasonality sample configuration")
        self.min_bin_samples = min_bin_samples
        self.prior_weight = prior_weight
        self._train: dict[str, list[HistoricalOutcome]] = {}
        self._cutoff: datetime | None = None

    def train(self, outcomes: Sequence[HistoricalOutcome], *, cutoff_utc: datetime) -> int:
        if cutoff_utc.tzinfo is None:
            raise ValueError("cutoff must include timezone")
        cutoff = cutoff_utc.astimezone(timezone.utc)
        grouped: dict[str, list[HistoricalOutcome]] = defaultdict(list)
        for row in outcomes:
            if (not row.symbol or row.observed_at_utc.tzinfo is None or
                    row.label_known_at_utc.tzinfo is None or
                    row.label_known_at_utc <= row.observed_at_utc):
                raise ValueError("invalid outcome or timing")
            if row.label_known_at_utc.astimezone(timezone.utc) < cutoff:
                grouped[row.symbol].append(row)
        self._train = dict(grouped)
        self._cutoff = cutoff
        return sum(len(x) for x in grouped.values())

    def estimate(self, symbol: str, *, as_of_utc: datetime) -> SeasonalEstimate:
        if as_of_utc.tzinfo is None:
            raise ValueError("as_of must be timezone aware")
        as_of = as_of_utc.astimezone(timezone.utc)
        if self._cutoff is None or as_of < self._cutoff:
            raise ValueError("seasonality fit not ready for this as_of")
        # Only rows whose future label was already known at as_of are present.
        examples = self._train.get(symbol, [])
        n = len(examples)
        prior = sum(x.direction_up for x in examples) / n if n else .5
        hour = [r for r in examples if r.observed_at_utc.astimezone(timezone.utc).hour == as_of.hour]
        dow = [r for r in examples if r.observed_at_utc.astimezone(timezone.utc).weekday() == as_of.weekday()]
        def rate(rows: list[HistoricalOutcome]) -> float:
            return (sum(x.direction_up for x in rows) + self.prior_weight * prior) / (len(rows) + self.prior_weight)
        hp = rate(hour) if len(hour) >= self.min_bin_samples else prior
        wp = rate(dow) if len(dow) >= self.min_bin_samples else prior
        # Tilt is a modest context modifier relative to the instrument prior,
        # never an unverified claimed profitability probability.
        tilt = max(-.10, min(.10, (hp - prior) * .65 + (wp - prior) * .35))
        if not isfinite(tilt):
            raise ValueError("nonfinite seasonal context")
        return SeasonalEstimate(symbol, as_of.hour, as_of.weekday(), prior,
                                hp, len(hour), wp, len(dow), tilt)
