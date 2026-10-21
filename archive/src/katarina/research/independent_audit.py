"""Frozen-policy final-window audit. Outputs research evidence, never orders.

Historical replay of a fixed journal cannot model changed position availability.
Its filtered P&L is diagnostic and requires a new MT5 backtest for confirmation.
"""
from dataclasses import asdict
from decimal import Decimal

from katarina.intelligence.brain import KatarinaAIBrain
from katarina.research.mt5_journal import FEATURE_NAMES, JournalDataset


def profit_summary(profits):
    profits = tuple(profits)
    gains = sum((p for p in profits if p > 0), Decimal(0))
    losses = -sum((p for p in profits if p < 0), Decimal(0))
    return {'trades': len(profits), 'net_profit': str(gains - losses),
            'profit_factor': str(gains / losses) if losses else None,
            'win_rate': sum(p > 0 for p in profits) / len(profits) if profits else None}


def audit(data: JournalDataset) -> dict:
    """Reserve final 20% before training/selection; purge crossing labels.

    Threshold .55 and sample requirements are fixed before reading final outcomes.
    No model refit or threshold search occurs on the reserved window.
    """
    if not data.rows or len(data.rows) != len(data.net_profits) or len(data.rows) != len(data.sides):
        raise ValueError('unaligned or empty dataset')
    if any(a.observed_ns > b.observed_ns for a, b in zip(data.rows, data.rows[1:])):
        raise ValueError('chronological dataset required')
    final_size = max(12, len(data.rows) // 5)
    cutoff = data.rows[max(0, len(data.rows) - final_size)].observed_ns
    development = tuple(r for r in data.rows if r.observed_ns < cutoff and r.label_known_ns < cutoff)
    final_indices = [i for i, r in enumerate(data.rows) if r.observed_ns >= cutoff]
    brain = KatarinaAIBrain()
    validation = brain.train_candidate(development, feature_names=FEATURE_NAMES)
    result = {'schema_version': 1, 'journal_sha256': data.source_sha256,
              'final_cutoff_ns': cutoff, 'development_count': len(development),
              'final_count': len(final_indices), 'selection': asdict(validation),
              'probability_threshold': brain.min_win_probability,
              'research_only': True, 'strategy_validated': False,
              'live_execution_enabled': False,
              'limitations': ['historical dataset already inspected; not a prospective test',
                              'fixed-journal replay does not simulate execution feedback',
                              'cost completeness and source provenance require external verification']}
    result['baseline_final'] = profit_summary(data.net_profits[i] for i in final_indices)
    if not validation.valid:
        result.update(result='NO_VALIDATED_AI_CANDIDATE', reasons=list(validation.reasons))
        return result
    model = validation.model
    train = [r for r in development if r.observed_ns < validation.cutoff_ns and r.label_known_ns < validation.cutoff_ns]
    prior = sum(r.profitable_after_costs for r in train) / len(train)
    selected = []
    brier = baseline = 0.0
    for i in final_indices:
        row = data.rows[i]
        p = model.predict_proba(row.features)
        brier += (p - row.profitable_after_costs) ** 2
        baseline += (prior - row.profitable_after_costs) ** 2
        in_bounds = all(lo - .25 * max(1, abs(lo), abs(hi)) <= x <= hi + .25 * max(1, abs(lo), abs(hi))
                        for x, (lo, hi) in zip(row.features, validation.training_bounds))
        if in_bounds and p >= brain.min_win_probability:
            selected.append(i)
    brier /= len(final_indices)
    baseline /= len(final_indices)
    reasons = []
    if len({data.rows[i].profitable_after_costs for i in final_indices}) < 2:
        reasons.append('single_class_final_window')
    if brier + brain.min_brier_improvement > baseline:
        reasons.append('no_independent_brier_improvement')
    if len(selected) < 12:
        reasons.append('insufficient_selected_trades')
    if sum((data.net_profits[i] for i in selected), Decimal(0)) <= 0:
        reasons.append('nonpositive_selected_net_profit')
    result.update(result='FINAL_AUDIT_REJECTED' if reasons else 'PASS_RESEARCH_FINAL_AUDIT',
                  reasons=reasons, final_brier=brier, final_baseline_brier=baseline,
                  filtered_final=profit_summary(data.net_profits[i] for i in selected),
                  by_side={side: profit_summary(data.net_profits[i] for i in selected if data.sides[i] == side)
                           for side in ('BUY', 'SELL')})
    return result
