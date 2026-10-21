# Forward brain evaluation - 2026-10-10

## Purpose
The observer recorded entry-time market and macro context but did not measure
subsequent price changes. The new forward ledger collects auditable quote
markouts at 5, 15 and 30 minutes, separately for broker-permitted BUY and SELL.

This is descriptive data collection, not a trading strategy or learned model.
It does not establish profitability, infer news causation, promote a model,
place orders, or bypass the existing NO_TRADE decision.

## Evidence and timing
- Valid fresh market observations seed both permitted directions, including
  observations blocked by macro context. Entry context is frozen as JSON.
- Each row links to its original immutable brain observation ID.
- Entry BUY uses ask and exit uses bid; SELL uses bid then ask.
- Record returns in basis points relative to entry midpoint and in entry ATR
  units. ATR units are not risk R. A midpoint comparison separates spread drag.
- Exit uses the first processed observation at or after its due time, no later
  than 90 seconds after. The quote itself must be at or after the due time and
  at most 30 seconds old relative to that observation.
- Missing or late exits are MISSING_EXIT with NULL outcome. They must not use
  the next session's price. The ledger expires them on the next cycle.
- Quotes are snapshots, not executable fill guarantees. No SL/TP path,
  commission, slippage, position size, account currency or realized PnL.
- Observations overlap. Row counts must not be treated as independent trades.
- A SQLite transaction stores outcomes and a progress cursor. Restart preserves
  pending samples; repeated observation IDs cannot double-label. A clock
  regression fails rather than rewriting chronology.
- Pre-deployment observations are not backfilled. A crash between observation
  persistence and evaluation can omit that entry cohort; no data is invented.

## Runtime
The existing five-minute task and research terminal are reused; no extra worker.
latest.json includes forward_evaluation counts and explicit limitations.
The SQLite forward_markouts table preserves pending, observed and missing exits.

Read-only report:
    python scripts/ai/report_forward_outcomes.py --database PATH/brain.sqlite3

Report groups by symbol, side, horizon, entry-time context readiness and regime.
All results remain DESCRIPTIVE_ONLY or AWAITING_VALID_QUOTES. Differences between
groups are observational associations and are not a causal test of news value.

## Validation and remaining work
82 intelligence unit tests and 11 brain/forward integration tests passed.
The 15 new tests cover spread accounting, direction restrictions, immutable
entry ATR/context, late/stale/future/disconnected quotes, idempotency, restart,
clock regression, observation links and report aggregation.
Actual VPS cycle scanned 74 symbols and created zero evaluation samples because
current quotes did not meet market eligibility. Synthetic test quotes stayed in
temporary/in-memory databases; none were inserted into the live observer store.
The scheduled task was restored and invoked after deployment.

Collect valid forward observations during trading sessions before evaluating
coverage and sample counts. This five-minute sampling cannot measure intra-minute
execution quality. Commission/slippage calibration, verified sessions, broader
news coverage and per-symbol strategy validation remain incomplete. Existing
training and promotion gates are unchanged. No new profitable model is claimed.
