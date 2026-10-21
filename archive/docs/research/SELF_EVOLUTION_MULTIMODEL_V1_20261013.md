# Katarina Self-Evolution Lab V1 — research only

Status: implemented research kernel; NOT autonomous production-code rewrite,
NOT connected to external LLM credentials, NOT real or demo orders.

## Reuses existing project components

- `ProspectiveShadowBook`: real timestamped broker BID/ASK *virtual* quote outcomes.
- `LearningEngine` and `ContinuousEvolutionController`: evolution policy and
  existing frozen safety constraints; no autonomous live promotion.
- `EvidenceRiskGate`: keeps risk at WAIT until independently verified fills.
- One canonical 5-minute MT5 observer: no second parallel trading daemon.

## Actual non-LLM learning loop

1. Consume at most 3,500 existing prospective shadow events as-of verified UTC.
2. Fail closed on invalid times, future outcomes, corrupt values, duplicate IDs.
3. Include uncertain quote gaps in coverage (minimum 80%) and keep pending
   records separate from winning/losing outcomes.
4. Cohorts are distinct by symbol + method + BUY/SELL + market regime.
5. Train research-only threshold variants (0.62, 0.70, 0.78) on the
   *chronologically earlier* ~70% of dates.
6. Exclude training trades that resolved after holdout began. Evaluate the
   fixed selected rule on the later ~30% of days (minimum 60 train and 30
   held-out quotes, plus independent days).
7. Use day-clustered lower bound and shrinkage in place of bare winrate.
8. Emit the candidate score cutoff and immutable SHA-256 input/review
   fingerprints. A changed ledger invalidates earlier review receipts.
9. Never execute proposals, rewrite strategy/code, change lot/risk, or
   promote any model without additional independently verified fills.

This is adaptive algorithmic research, not a trained high-capacity foundation
model, and not evidence of alpha. A retrospective held-out split of virtual
quotes is **not** an untouched real forward test.

## gstack-inspired review and G0DM0D3-inspired model critics

The native observers run four independent deterministic critiques: data
integrity, quant holdout, broker execution, and code-release readiness.
All four explicitly describe their mechanism as non-LLM policy. The
`multi_model_evolution_review` interchange can accept externally generated
opinions from at least two different providers, and compares them against
the exact current report receipt. Dissent, stale reviews, missing source
references, or quant/data failures block further experiments.

Actual commercial/open external models are **NOT connected or invoked** by
default. Review records must be supplied from a separately authorized model
bridge in future. No API tokens are embedded in repository files or VPS
tasks. Even independent models agreeing can authorize only *additional
isolated research tests*, never trading or code deployment.

## Operational integration

The existing one-canonical-market-observer writes these additional keys
in `C:\KatarinaDev\artifacts\contextual-observer\latest.json`:

- `self_evolution_lab`: per-cohort learned diagnostic and candidate rules.
- `self_evolution_model_review`: independent model-review readiness.

The observer must remain read-only with `orders_submitted: 0` and
`live_execution_authorized: false`. Any missing evidence means WAIT.

On the original 13 October VPS SQLite sample only five resolved virtual
observations were available; an immediate self-improvement proposal is
therefore NOT justified. No promises of higher winrate or profit.

## How to verify

`PYTHONPATH=src python -m unittest discover -s tests/unit/intelligence -p test_self_evolution_lab.py`

`PYTHONPATH=src python -m unittest discover -s tests/unit/governance -p test_multi_model_evolution_review.py`

Body CI must pass, then compare GitHub commit SHA, VPS observer schedule,
read-only MT5 status and actual observer report. Do not overwrite a working
production environment if the verification fails.
