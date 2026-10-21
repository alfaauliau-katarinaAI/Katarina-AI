# KATARINA AI Brain — historical tick-level SL/TP laboratory
Research finalized 2026-10-10 (WIB). **NO_TRADE and live execution disabled.**

## Purpose
The previous gate measured spread relative to ATR while fixed-horizon
bid/ask markouts did not establish whether a position could have hit a
target or stop. This incremental, read-only experimental study reconstructs
the first chronological bid/ask quote crossing a predefined hypothetical
take-profit or stop-loss using actual historical broker ticks.

**These are simulated mark-to-quote exits, not executed broker orders or
audited account profits.** Do not assert a funded strategy from this data.

## Input evidence
- Six immutable research archives produced from MT5 ALFA broker history,
  three discrete windows: 2026-08-16 through 08-31, 2026-09-15 through
  09-30, 2026-10-01 through 10-09, all dates UTC.
- Reuses frozen M1/M5 and independent M5/M15 technical hypotheses, not
  new indicators tuned against the TP/SL outcomes.
- Source SHA256 is checked by the independent final auditor.
- Up to **0.50 spread/entry-timeframe ATR** is considered exploratory.
  The original 0.15 production research gate remains unchanged; 0.25,
  0.35, and 0.50 are conditional analysis slices only.
- Entry-time indicator ATR is **recomputed from the same 120 closed
  historical candles** used by each original hypothesis and accepted
  only when their SHA256 matches the archived point-in-time bar snapshot.
  No incomplete M1, M5 or M15 candle is used.

## Hypothetical scenario contract (frozen)
- Target/stop multipliers of ATR: (TP 1 / SL 1), (TP 1.5 / SL 1),
  (TP 2 / SL 1), (TP 2 / SL 1.5).
- Extra round-trip cost stress: 0, 2, 5 bps *beyond* the spread already
  paid in the broker historical quote. 2 and 5 bps are invented stress
  scenarios, not calibrated commissions or slippage. Do not double count
  the spread.
- Entry hypothetical BUY price = historical ask; SELL = historical bid.
  The entry tick must exactly match the quote and millisecond timestamp
  from the original immutable observation. No backfilled or assumed fills.
- BUY exit is broker bid, SELL exit is broker ask. First TP/SL crossing
  before the deadline ends the position. Favorable TP gaps are capped
  at TP price; adverse stop gaps incur the actual worse quote.
- If no barrier is crossed, exit on first actual valid broker quote at
  or after 30 minutes, at most 90 seconds after. Time exit takes
  precedence over any same-tick barrier event at/after the deadline.
- A >180-second quote gap, invalid/crossed quote, absent exit quote,
  missing OHLC evidence, or inconsistent ATR evidence fails closed;
  such a sample is not silently assigned a profit.
- Conservatively allow only one 30-minute position per symbol in each
  independent family. Overlap-excluded samples remain visible in the
  candidate counts; *cross-symbol correlation and shared risk are not
  modelled*. Original 15-minute candidate spacing is not confused
  with true 30-minute order concurrency.
- Outcome R = tick-quoted price delta / nominal stop distance;
  hypothetical bps fees/slippage additionally subtract equivalent R.
  This is **not** actual account equity growth, real cash PnL,
  or SL/TP fill probability from an execution venue.
- Profit factor uses sum of positive R divided by absolute negative R.
  Summaries with fewer than 30 valid trials, fewer than 10 UTC dates,
  or less than 80% included outcomes are explicitly insufficient.
  Even a DESCRIPTIVE_ONLY group is *not* proof of profitability or
  permitted to promote a model.

## Actual VPS results / immutable outputs
Archive location:
`C:\KatarinaDev\artifacts\historical-brain\`

`tick-sl-tp-all-spread050-v3-auditable.json`
- 302 candidate entries with <=0.50 spread/ATR, from both families.
- 275 non-overlapping candidate paths replayed, 27 overlap-excluded.
- 4 TP/SL combinations times 3 extra cost scenarios =
  3,624 stored scenario records: 3,300 computed, 324 overlap-excluded.
- 192 grouped summaries (family x four cost ceilings x four TP/SL
  pairs x three cost-stress scenarios x BUY/SELL).
- Original exact source quotes and closed-bar fingerprints verified;
  no completed-replay trial relies on a fabricated tick.
- Raw scenario records include quote entry/exit prices, hypothetical
  exit fill, tick-path SHA256, the original source, timing, ATR, R
  and the reason for each exit.

`tick-sl-tp-all-spread050-v3-integrity.json`
- Independently verified all six source files, 3,624 scenario records,
  302 entry scenario groups and all 192 aggregated cohorts.
- The immutable replay file SHA256 is recorded for comparison.

### Predeclared illustrative scenario: spread <= 0.35 entry ATR,
TP=2 ATR, SL=1 ATR, 30-minute maximum (descriptive, not OOS)
| Family and side | Eligible signals | Finished nonoverlapping paths | TP | SL | Time | Quoted expectancy R, no extra bps | PF | +2 bps stress expectancy R |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M1/M5 BUY | 73 | 69 | 18 | 50 | 1 | -0.225 | 0.706 | -0.802 |
| M1/M5 SELL | 60 | 53 | 12 | 41 | 0 | -0.399 | 0.532 | -0.915 |
| M5/M15 BUY | 21 | 16 | 3 | 9 | 4 | -0.198 | 0.687 | -0.538 |
| M5/M15 SELL | 29 | 25 | 9 | 13 | 3 | +0.207 | 1.385 | -0.126 |

M5/M15 SELL's apparent tiny positive historical result has **only
25 finished simulations over 9 UTC dates**, fails the minimum sample
size, and reverses to negative under 2 bps hypothetical extra cost.
The 192 scenarios are a sensitivity grid, *not* 192 attempts to
find the best live strategy. Earlier exploratory history cannot
provide untouched holdout validation.

## Usage (dedicated VPS read-only Python, repo root)
```text
python scripts/research/replay_historical_tick_stops.py --m1-report AUG_M1.json SEP_M1.json OCT_M1.json --m5-report AUG_M5.json SEP_M5.json OCT_M5.json --output NEW_UNIQUE_FILE.json
python scripts/research/audit_tick_sl_tp_paths.py --report REPLAY.json --output NEW_UNIQUE_AUDIT.json
python scripts/research/summarize_tick_sl_tp_paths.py --report REPLAY.json --spread-limit 0.35 --extra-bps 2
```

The sources and report names are never silently overwritten. Current
Scheduled Task `Katarina-MarketBrain-Observer` remains an independent
read-only observer; no changes to MT5 order routing or production
parameters are made.

## Further work before any trading
Broker-specific actual commission/contract tick value and spread
history, Monte Carlo risk/drawdown and correlation, reproducible
MT5 tick completeness, real market order/stop order execution
assumptions, and separated chronological out-of-sample windows
are essential. Fee stress in bps cannot be trusted as broker actual.

**Status: research completed, strategy not validated. Do not
automatically widen the old 15% limit or enable live trading.**
