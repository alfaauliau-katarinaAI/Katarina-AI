# Unified offline adaptive learning — Memory / Curiosity / Brain / Entry–Exit

Source: `src/katarina/intelligence/cognition/unified_adaptive_research_cycle.py`.

**This implements one integration contract, not a profitable production AI.**

The existing read-only cognitive cycle (episodic+semantic memory, chronological
virtual quote outcomes, curiosity and metacognitive error review) is joined
with the existing Adaptive Brain V2 entry proposal and structural Smart Exit
plan. The resulting Owner evidence receipt is deterministic and contains:

- Current shadow memory snapshot SHA-256 and a separate Entry/Exit source
  receipt SHA-256. It is not an external signature or broker authentication.
- Exact source cohort matching by **symbol, method, BUY/SELL and regime**.
  Different methodologies such as `SWEEP` versus `TREND_PULLBACK` do not
  become equivalent by assumption.
- Falsifiable curiosity proposal selected for the same research cohort.
- Explicit WAIT reasons for absent or unvalidated shadow evidence, quote gaps,
  inconsistent Entry/Exit, and unmapped methods.
- An exploratory `VIRTUAL_EXPERIMENT_REVIEW_ONLY` state when the existing
  (quote-only) learner has a favorable matching cohort without missing quote
  paths, while the broker-forward evidence requirement still remains.
- **No production permission**: no orders, no real broker edge claim, no
  policy parameter changes, no internal scheduler, no cloud commands.

`synthesize_offline_research` uses `run_unified_cognitive_cycle(...,
persist=False)`, therefore no learning checkpoint is written by this review.
Persistent learning remains available in the existing explicit controlled
cognitive pathway; this integration does not modify its ledger.

For tests, use GitHub Body CI (or focused):
`PYTHONPATH=src python -m unittest discover -s tests/unit/intelligence -p test_unified_adaptive_research_cycle.py -v`.

Still **NOT COMPLETE** for Master Design: selective trusted lifelong memory,
quantitatively validated artificial curiosity or self-evolution, predictive
market/world model with Fast/Deep scheduling, actual independent forward
outcomes, broker-aware Smart Entry and lifecycle HOLD/FULL/PARTIAL/TRAIL
cost modeling. Six Owner deferred decisions are not invented.
