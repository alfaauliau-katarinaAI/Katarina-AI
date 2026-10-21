# Self-evolution causal source integrity — offline research

This change protects the existing quote-only
`src/katarina/intelligence/cognition/self_evolution_lab.py` before it can update any
Cognitive Brain learning checkpoint or curiosity research proposals.

- Distinct SQLite row IDs **do not** prove independent market events.
  Exact repeated `(symbol, method, BUY/SELL, regime, observed_at)` samples
  invalidate the entire affected research read rather than inflating apparent
  learning quality. BUY and SELL remain separate, as do different methods.
- The bounded `MAX_ROWS` input cannot silently discard older observations.
  When more than the allowable rows exist, the learner returns an **INVALID**
  evidence status instead of reporting that a cherry-picked recent subset
  is complete. This is an engineering input bound, not an Owner-approved
  alpha or risk threshold.
- An invalid evidence report leaves the shadow-learning policy with
  `integrity_ok=False`, no cohort promotion, and WAIT; the cognitive
  checkpoint builder fails before writing its ledger.
- Unit regressions cover duplicate causal quotes, directional independence,
  separate methods, truncation, exact capacity, future observation masking,
  and prevention of learning checkpoints after invalid input.

Even a clean historical dataset is not broker-real: no broker fills,
commissions, slippage, independent forward validation, or production alpha
proof has been established. No new calibration threshold, Risk Governor
override, scheduler or live trading path is supplied.

Test under GitHub Body CI or:
`PYTHONPATH=src python -m unittest discover -s tests/unit/intelligence -p test_strict_self_evolution_integrity.py -v`.
