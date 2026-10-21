"""Offline KATARINA AI Brain: chronological learning and research-only signals.

No network access, broker adapter, risk authorization, or automatic model promotion.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from typing import Sequence

from katarina.engines.decision import DecisionAction, DecisionEngine
from katarina.engines.opportunity import MarketCandidate
from katarina.engines.setup_quality import SetupQualityEngine, SetupQualityInput
from katarina.intelligence.regime import Regime, RegimeAssessment
from katarina.intelligence.simple_ml import LogisticModel, MachineLearningV1


@dataclass(frozen=True, slots=True)
class LabeledMarketExample:
    """Features captured at observation time; label becomes known only at exit."""

    sample_id: str
    observed_ns: int
    label_known_ns: int
    features: tuple[float, ...]
    profitable_after_costs: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "features", tuple(self.features))
        if not self.sample_id or type(self.observed_ns) is not int or self.observed_ns <= 0:
            raise ValueError("invalid sample identity/time")
        if type(self.label_known_ns) is not int or self.label_known_ns <= self.observed_ns:
            raise ValueError("label must be known after market observation")
        if type(self.profitable_after_costs) is not int or self.profitable_after_costs not in (0, 1):
            raise ValueError("binary net-profit label required")
        if not self.features or any(not isfinite(x) or abs(x) > 10 for x in self.features):
            raise ValueError("non-finite or unscaled features")


@dataclass(frozen=True, slots=True)
class AIBrainValidation:
    """Candidate model is research-only; never a live-model promotion record."""

    valid: bool
    model: LogisticModel | None
    feature_names: tuple[str, ...]
    train_count: int
    test_count: int
    cutoff_ns: int
    trained_until_ns: int
    baseline_brier: float | None
    model_brier: float | None
    training_bounds: tuple[tuple[float, float], ...]
    reasons: tuple[str, ...]
    model_hash: str
    live_risk_ready: bool = False


@dataclass(frozen=True, slots=True)
class AIBrainSignal:
    symbol: str
    action: DecisionAction
    net_win_probability: float | None
    score: float
    risk_multiplier: float
    reasons: tuple[str, ...]
    model_hash: str
    research_only: bool = True
    live_risk_authorized: bool = False


class KatarinaAIBrain:
    """Deterministic, cost-aware offline learner and fail-closed signal filter.

    The trainer sees only labels known BEFORE the test window begins.
    Model evaluation uses a chronological untouched holdout; it is never
    retrained on the test window. Signals remain research/shadow outputs.
    """

    def __init__(
        self, *, min_train: int = 24, min_test: int = 12,
        min_brier_improvement: float = 0.005, min_win_probability: float = 0.55,
    ) -> None:
        if min_train < 10 or min_test < 5:
            raise ValueError("insufficient training/holdout requirements")
        if not 0 <= min_brier_improvement <= 1 or not .5 <= min_win_probability <= 1:
            raise ValueError("invalid threshold")
        self.min_train = min_train
        self.min_test = min_test
        self.min_brier_improvement = min_brier_improvement
        self.min_win_probability = min_win_probability

    def survey_markets(self, observations, *, context_store, now_utc, limit=5):
        """Read-only multi-symbol perception; no model or risk promotion."""
        from katarina.intelligence.multi_market_brain import screen
        return screen(observations, context_store, now_utc, limit)

    def train_strategy_selector(self, observations, *, train_cutoff_ns, selection_end_ns):
        """Separate offline expected-R research path; does not replace live policy."""
        from katarina.intelligence.strategy_selector import StrategySelectionBrain
        selector = StrategySelectionBrain()
        evidence = selector.fit(observations, train_cutoff_ns=train_cutoff_ns,
                                selection_end_ns=selection_end_ns)
        return selector, evidence

    def recall_experience_connections(
        self, memory_store, *, context_tags: Sequence[str], as_of_ns: int,
        deep: bool = False, limit: int = 5,
    ):
        """Read-only Neuro-Link connections; not an order or risk decision.

        Both fast and deep cognition use the SAME memory and causal evidence.
        Independent Risk Governor and live approval remain entirely separate.
        """
        from katarina.memory.neuro_link import NeuroLinkMemory

        return NeuroLinkMemory(memory_store).recall(
            tuple(context_tags), as_of_ns=as_of_ns,
            mode="deep" if deep else "fast", limit=limit,
        )

    def train_candidate(
        self,
        examples: Sequence[LabeledMarketExample],
        *,
        feature_names: Sequence[str],
    ) -> AIBrainValidation:
        names = tuple(feature_names)
        if not names or any(not n or not isinstance(n, str) for n in names) or len(set(names)) != len(names):
            raise ValueError("invalid feature schema")
        rows = sorted(examples, key=lambda x: (x.observed_ns, x.sample_id))
        if len(set(x.sample_id for x in rows)) != len(rows):
            raise ValueError("duplicate sample ID")
        if any(len(x.features) != len(names) for x in rows):
            raise ValueError("feature schema mismatch")

        holdout_size = max(self.min_test, len(rows) // 5)
        if len(rows) <= holdout_size:
            return self._invalid(names, 0, 0, 0, "insufficient_labeled_samples")
        holdout = rows[-holdout_size:]
        cutoff_ns = holdout[0].observed_ns
        # Purge observations whose realized results were not available at cutoff.
        train = [x for x in rows[:-holdout_size] if x.observed_ns < cutoff_ns and x.label_known_ns < cutoff_ns]
        # A single timestamp may appear on multiple symbols; never split it into
        # both training and holdout. All test observations are at/after cutoff.
        if len(train) < self.min_train or len(holdout) < self.min_test:
            return self._invalid(names, len(train), len(holdout), cutoff_ns, "insufficient_purged_history")
        if len(set(x.profitable_after_costs for x in train)) < 2:
            return self._invalid(names, len(train), len(holdout), cutoff_ns, "single_class_training")
        if len(set(x.profitable_after_costs for x in holdout)) < 2:
            return self._invalid(names, len(train), len(holdout), cutoff_ns, "single_class_holdout")

        model = MachineLearningV1().train(
            [x.features for x in train],
            [x.profitable_after_costs for x in train],
            epochs=300,
            lr=.15,
            version="ai-brain-research-candidate-v1",
        )
        prior = sum(x.profitable_after_costs for x in train) / len(train)
        baseline = sum((prior - x.profitable_after_costs) ** 2 for x in holdout) / len(holdout)
        candidate = sum((model.predict_proba(x.features) - x.profitable_after_costs) ** 2 for x in holdout) / len(holdout)
        if not (isfinite(candidate) and isfinite(baseline)):
            return self._invalid(names, len(train), len(holdout), cutoff_ns, "non_finite_validation")
        bounds = tuple((min(x.features[i] for x in train), max(x.features[i] for x in train)) for i in range(len(names)))
        end_ns = max(x.label_known_ns for x in train)
        artifact = {
            "feature_names": names, "train_cutoff": cutoff_ns,
            "trained_until_ns": end_ns, "weights": model.weights,
            "bias": model.bias, "training_sample_ids": [x.sample_id for x in train],
        }
        fingerprint = sha256(json.dumps(artifact, sort_keys=True, allow_nan=False).encode()).hexdigest()
        valid = candidate + self.min_brier_improvement <= baseline
        return AIBrainValidation(
            valid, model if valid else None, names, len(train), len(holdout),
            cutoff_ns, end_ns, baseline, candidate, bounds,
            ("out_of_sample_brier_improved",) if valid else ("no_holdout_improvement",),
            fingerprint if valid else "", False,
        )

    @staticmethod
    def _invalid(names: tuple[str, ...], train: int, test: int, cutoff: int, reason: str) -> AIBrainValidation:
        return AIBrainValidation(False, None, names, train, test, cutoff, 0, None, None, (), (reason,), "", False)

    @staticmethod
    def _blocked(symbol: str, *reasons: str, action: DecisionAction = DecisionAction.NO_TRADE) -> AIBrainSignal:
        return AIBrainSignal(symbol, action, None, 0.0, 0.0, tuple(reasons), "")

    def evaluate(
        self,
        candidate: MarketCandidate,
        quality_input: SetupQualityInput,
        validation: AIBrainValidation,
        *,
        features: Sequence[float],
        observed_ns: int,
        regime: RegimeAssessment,
        system_healthy: bool,
        drift_detected: bool = False,
    ) -> AIBrainSignal:
        symbol = candidate.instrument.canonical_symbol
        if not system_healthy:
            return self._blocked(symbol, "system_unhealthy", action=DecisionAction.SAFE_MODE)
        if not candidate.instrument.ready:
            return self._blocked(symbol, "broker_symbol_not_ready")
        if regime.out_of_distribution or regime.regime is Regime.UNKNOWN or not isfinite(regime.confidence):
            return self._blocked(symbol, "unknown_or_ood_regime")
        if drift_detected:
            return self._blocked(symbol, "feature_or_outcome_drift")
        if not candidate.news.ready or candidate.news.blackout:
            return self._blocked(symbol, "news_unavailable_or_blackout")
        if (
            quality_input.proposal != candidate.proposal
            or quality_input.news_ready != candidate.news.ready
            or quality_input.news_blackout != candidate.news.blackout
            or abs(quality_input.news_risk_score - candidate.news.risk_score) > 1e-9
        ):
            return self._blocked(symbol, "inconsistent_quality_evidence")
        decision = DecisionEngine().decide_scalper(candidate.proposal, system_healthy=system_healthy)
        if decision.action not in (DecisionAction.BUY, DecisionAction.SELL):
            return self._blocked(symbol, "entry_decision_denied")
        quality = SetupQualityEngine().evaluate(quality_input)
        if not quality.valid:
            return self._blocked(symbol, *quality.reasons)
        if not validation.valid or validation.model is None:
            return self._blocked(symbol, "model_not_out_of_sample_validated")
        if (
            type(observed_ns) is not int or observed_ns <= validation.cutoff_ns
            or observed_ns <= validation.trained_until_ns
        ):
            return self._blocked(symbol, "stale_or_noncausal_model")
        values = tuple(features)
        if len(values) != len(validation.feature_names) or len(values) != len(validation.training_bounds):
            return self._blocked(symbol, "feature_schema_mismatch")
        if any(not isfinite(x) or abs(x) > 10 for x in values):
            return self._blocked(symbol, "invalid_market_features")
        # No extrapolation far outside what the training sample observed.
        for value, (lo, hi) in zip(values, validation.training_bounds):
            margin = .25 * max(1.0, abs(lo), abs(hi))
            if value < lo - margin or value > hi + margin:
                return self._blocked(symbol, "feature_out_of_distribution")
        probability = validation.model.predict_proba(values)
        if not isfinite(probability):
            return self._blocked(symbol, "non_finite_prediction")
        if probability < self.min_win_probability:
            return AIBrainSignal(symbol, DecisionAction.NO_TRADE, probability, 0.0, 0.0, ("model_edge_below_threshold",), validation.model_hash)
        # Model is an extra veto, never a replacement for proposal/quality/risk governors.
        return AIBrainSignal(
            symbol, decision.action, probability,
            min(decision.score, quality.adjusted_score),
            min(1.0, max(0.0, quality.risk_multiplier)),
            ("research_candidate", "model_holdout_pass", "entry_and_quality_gates_pass"),
            validation.model_hash,
        )

    def rank_research(
        self, signals: Sequence[AIBrainSignal], *, limit: int = 5
    ) -> tuple[AIBrainSignal, ...]:
        """Prioritized research candidates, not execution instructions."""
        eligible = [x for x in signals if x.action in (DecisionAction.BUY, DecisionAction.SELL)]
        return tuple(sorted(
            eligible,
            key=lambda x: (-x.score * (x.net_win_probability or 0), x.symbol),
        )[:max(0, limit)])
