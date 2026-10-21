# Continuous all-market research — 20 October 2026

Owner authorized implementation after documentary audit. LIVE OFF remains mandatory.

## Scope and evidence

Keep the single canonical brain, bounded broker wrapper, account identity checks,
and maximum 17 observations per cycle. Opt-in `--all-market-research` rotates
all trade-enabled catalog symbols (including suffixes), using persisted oldest-visit
scheduling. This is a research universe, never an execution whitelist.

The existing Gemini public-document reader remains bounded to public articles,
24 attempts/day and one attempt/15 minutes. Private market/account data are not
sent to that reader. No private credentials are migrated or printed.

Each cycle runs one persisted history/experiment task, raw broker H1 timestamps,
2048-bar chunks, up to 65536 bars/symbol; latest 8192 bars used per exploratory
experiment. Stop adding research data below 2 GiB free or above a 512 MiB shared
DB budget. No deletion, no fabricated ticks, no independent-holdout claim.

Six frozen candidates: momentum, mean reversion, breakout; BUY and SELL separate.
Signal completed before next-open entry, 12-bar close exit, nonoverlap, first 2/3
for development with matured exit required before boundary; last 1/3 repeated
historical review. Cost proxy current spread +0.20 ATR. No SL/TP execution claim,
true-tick claim, strategy promotion, or profit target. Result hashes deduplicate
repeated datasets; unavailable symbols retry on their next turn.

This lightweight continuing baseline supplements, does not replace, locked V3.1–3.3
research. The V3.3 universe snapshot was 54 instruments, 8 long-history and 46
metadata-only. V3.3 did not establish a stable edge. Historical review is reused.
Future work still required: independent market labels, broker-specific DST audit,
full tick entry–exit reconciliation, prospective frozen tests, and full portfolio
mark-to-market/margin evaluation. Runtime does not declare these completed.

## Dashboard semantics

Persisted experiment -> tested dataset -> instrument (hashed labels publicly).
Recent 24 experiment records form the bounded view, not total memory size.
Lab counters and six recent development-selected results are sent through the
existing technical relay. Broker/account secrets and raw prices remain private.
More nodes does not attest better prediction or Gemini weight training.
History and experiment phase events are real calls; bounded JSONL history survives
restart, rotated to about 20 MiB. Existing status PID/freshness checks stay intact.

## Operations

Existing scheduled task starts one canonical process. Add all-market flag without
changing account binding or model config. Retain graceful stop-file procedure.
Configure restart on failure and startup trigger; do not launch duplicate workers.
A 24-hour and seven-day soak require elapsed time and cannot be claimed on deployment.
Rollback: restore backed-up tracked files and original scheduled task XML, keeping
research tables/evidence and secrets intact. Remove flag to restore 17-market mode.
