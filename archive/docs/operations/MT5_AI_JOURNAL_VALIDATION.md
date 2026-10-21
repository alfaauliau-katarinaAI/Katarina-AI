# Offline AI validation from MT5 journals

The journal adapter connects the installed research EA's feature export to the
existing offline AI trainer. It neither loads a model into MT5 nor places orders.
The production news/snapshot schema remains a separate integration.

Run from the repository root with Python 3.10 or later:

```sh
PYTHONPATH=src python scripts/ai/validate_mt5_journal.py \
  --journal /path/to/KatarinaFeatureJournal.csv \
  --expected-trades 136 --expected-net-profit -46.52 \
  --output build/ai/mt5-september-validation.json
```

Supply totals from the matching MT5 report. UTF-16 and UTF-8 exports are accepted.
The adapter rejects missing/nonfinite features, contradictory labels, duplicate
observations, mixed runs, and unreconciled counts/profit. Profit tolerance is half
a cent per exported row because the EA rounds each row. Aggregate agreement does
not certify per-trade entry commissions or data provenance.

Only 11 pre-entry measurements become predictors. Outcome columns never enter
the feature vector. Fixed transforms require no fitting on future observations.
The EA currently records the signal bar time as `entry_time`, not the actual
execution timestamp. This is a conservative earlier cutoff for training-label
purging; the journal cannot establish exact execution latency.
Broker dates are wall-clock coordinates, not verified UTC timestamps. Entry is
bounded below and label availability above by the timestamp precision. Labels
not known strictly before the holdout cutoff are purged from training.

The trainer uses the final 20% (minimum 12 observations) as chronological holdout,
requires both outcome classes, and requires a Brier improvement of at least
0.005 against the training-class-prior baseline. Lower Brier is better. A pass is
candidate acceptance only: the same holdout cannot establish independent forward
performance. Exit code 2 means no accepted candidate (or invalid CLI/data input);
the JSON result distinguishes a completed rejection from invalid input.

## September 2026 result

Source: the existing MT5 ALFA terminal's XAUUSD.vx M1 real-tick tester run,
2026-09-01 through 2026-10-01, baseline preset in PR #12. Its 136 exported trades
reconcile to -46.52 USD: 55 BUY and 81 SELL. Raw journals remain private.

- Training: 109 trades; chronological holdout: 27 trades.
- Baseline Brier: 0.2094193343; candidate Brier: 0.2074579480.
- Improvement: 0.0019613863, below the unchanged 0.005 requirement.
- Result: `NO_VALIDATED_AI_CANDIDATE`; no model exported or promoted.

This run does not establish profitable filtering or strategy readiness. Further
research needs additional periods, verified cost accounting, and a separate
forward evaluation. Do not tune the threshold to pass this observed holdout.

The evidence journal SHA identifies the normalized UTF-8 analysis copy, not the
original UTF-16 file. The original report SHA and VPS artifact location are
recorded alongside validation evidence in the private control repository.
