# Multi-timeframe zone scalping experiment

Research only. Parent PR #16; base commit da3ecee7f83a75806b8274dda4bbcbb02d9f5039.
The prior frozen router failed. This experiment introduces one explicit new entry
hypothesis and compares complete executions, not filtered prior trade journals.

## Frozen matrix and chronology

Twelve configurations: H1/M15/M1, M30/M5/M1, H1/M15/M5, each BUY or SELL and
middle-timeframe confirmation enabled or disabled. This is a bounded comparison,
not a claim of optimality across all possible parameters or timeframes.
Zone timeframe / confirmation timeframe / entry timeframe is the order above.

- Jan 1 through Mar 31, 2026: first development window.
- Apr 1 through Jun 30: chronological selection window.
- Jul 1 through Sep 30: later execution audit of selected candidates only.
- Oct 1 onward remains reserved.
July-September history was partly inspected in earlier experiments. Therefore it
cannot be called pristine unseen or prospective evidence.

Require at least 30 trades and 10 active days in the first window, 20 trades and
10 days in the second, positive net R and R-profit-factor >=1.1 in both after
an extra 0.1R cost per trade, and at least four positive months out of six.
Trades whose exit labels cross a window boundary are purged from selection.
Select at most one whole strategy per side by the weaker-window expected R;
candidate id breaks ties. No regime-based journal filtering, replacement of
rejected choices using final results, or loosening thresholds after results.
Passing this screen only authorizes further paper research, never live capital.

## Exact causal hypothesis

On each new zone-timeframe bar, use the most recent CLOSED departure candle and
its preceding base candle. The volatility scale is mean true range of the 14
candles preceding the base. The base range must not exceed that scale, its body
must not exceed half the scale, and departure body must be at least one scale.
Departure closes beyond the preceding five-bar range and more than half a scale
beyond the proximal zone edge.

Demand is base low to maximum(base open, base close); supply is minimum(base open,
base close) to base high. These are price-action proxies, not proof of resting
institutional orders or exchange order flow. A new zone replaces the older zone
on the same side. It is only known after the departure candle has closed.
Startup does not backfill pre-existing zones; every run begins with empty state.

Track each valid closed entry candle, including while a position is occupied.
Only the first overlapping candle starts the entry window. A close beyond the
distal edge invalidates the zone; otherwise the entry window lasts three entry
candles, including the first touch. Zone lifetime is 48 zone candles.
The first qualifying signal consumes the zone even if occupied, spread-blocked,
or otherwise rejected. Consequently a missed touch never becomes fresh later.

Entry requires a directional candle closing beyond the proximal edge in the
outer 40% of its range. When confirmation is enabled, the last closed middle-TF
candle must have a higher low plus higher and bullish close for BUY, or a lower
high plus lower and bearish close for SELL. This is a two-bar structure proxy,
not a claim of confirmed swing BOS. Candle-close times are checked before use.

## Scalping execution and equal budget

Stop is outside the distal zone edge by 0.2 entry-timeframe ATR. Reject if entry
risk distance is below 1 or above 3 entry ATR. TP is 1.5R. Maximum quoted spread
is 0.12 entry ATR and 0.10 initial price risk. No grid, averaging or recovery lot.
Only one position at a time. At 45 minutes, close at the first available tick;
market closures can delay that exit and are reported, not hidden.

Every candidate has a 10 USD planned risk ceiling on a 10,000 USD test balance,
with leverage 1:100. OrderCalcProfit converts the stop into cash risk. Volume is
rounded DOWN to the broker's permitted grid. If minimum lot exceeds the budget,
skip the trade. Thus actual risks can be smaller than 10 USD due to lot granularity;
the budgets are equal, not the realized per-trade risk. R comparisons use actual
filled initial risk. Fill audit rejects risk above budget +0.02 USD rounding tolerance.
Fees/spread in reports remain distinct from the additional 0.1R stress. Fixed stress
is not a measured latency, commission or news-slippage model.

## Implementation and verification

- EA method KRM_ZONE_SCALP=7; existing methods and production defaults retained.
- ResearchZoneScalp.mqh owns causal zone lifecycle and runtime self-tests.
- Dedicated tester-only Expert; live terminal/strategy/risk governor unchanged.
- run_strategy_experiments supports explicit period/settings with old defaults.
- run_zone_scalp_experiments freezes the matrix, runs serially, verifies report/
  journal reconciliation, risk, chronology, unique zones and evidence hashes.
- 44 Python research unit tests passed, including eight audit rejection tests.
- All 18 MQL targets compiled with zero errors/warnings:
  zone-scalp-build/0ebf4cfdfc1d4724b40e59f589a95961.
- MQL initialization enforces synthetic tests for demand/supply departure,
  insufficient impulse, pre-formation touch, expiry and invalidation.
- Feature and opportunity logs are retained. Zone fill audit records exact zone,
  knowledge/touch/entry timestamps, stop, volume and actual cash risk.

The 12 configurations and their common market bars are not independent evidence.
Statistical significance is not established by these development screens. A future
survivor still needs untouched-period, execution-stress, and forward paper validation.
BUY and SELL pass separately; combining them needs another actual execution test
because position availability may change.

## Primary implementation references

- https://www.mql5.com/en/docs/series/copyrates
  Bar zero is incomplete; zone, confirmation and entry decisions use closed candles.
- https://www.mql5.com/en/docs/trading/ordercalcprofit
  Estimate stop economics in account currency rather than assuming a pip value.
- https://www.mql5.com/en/book/automation/symbols/symbols_volume
  Respect volume minimum, maximum and step.
- https://www.metatrader5.com/en/terminal/help/algotrading/testing
  Complete Strategy Tester execution with real ticks.

No external strategy code was copied. References document execution mechanics,
not evidence that supply/demand is profitable.

## Results

Twelve development executions completed. Frozen choices: []. Decision: **NO_TRADE**.
Every report has 100% real-tick quality; nonempty trade journals reconcile with reports.
Zone fill audit verifies causal timestamps, unique entry per zone, outside-zone stops,
and filled risk within the declared budget tolerance.

| Layout / side / confirmation | Trades | Net USD | Cash PF | Jan-Mar / Apr-Jun trades | Positive months after stress |
|---|---:|---:|---:|---:|---:|
| H1_M15_M1_BUY_confirm0 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| H1_M15_M1_BUY_confirm1 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| H1_M15_M1_SELL_confirm0 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| H1_M15_M1_SELL_confirm1 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| M30_M5_M1_BUY_confirm0 | 4 | 11.93 | 1.80 | 3/1 | 2 |
| M30_M5_M1_BUY_confirm1 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| M30_M5_M1_SELL_confirm0 | 8 | 21.43 | 1.89 | 3/5 | 3 |
| M30_M5_M1_SELL_confirm1 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| H1_M15_M5_BUY_confirm0 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| H1_M15_M5_BUY_confirm1 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| H1_M15_M5_SELL_confirm0 | 1 | 1.83 | 0.00 | 1/0 | 1 |
| H1_M15_M5_SELL_confirm1 | 0 | 0.00 | 0.00 | 0/0 | 0 |

Positive totals on very small samples do not meet the declared evidence threshold.
No final-window audit is run when no candidate qualifies. October remains unused.
Signals rejected before execution are counted in the diagnostic receipt; zero trades
means insufficient opportunity evidence, not proof that all zone strategies are unprofitable.

Durations and month-by-month R statistics appear in the result JSON. The report's
OTHER exit classification includes timed exits; it is not an unidentified stop loss.

## Smaller-timeframe follow-up

After the first 12 candidates produced insufficient opportunity coverage, a second
manifest froze eight additional M15/M5/M1 and M5/M3/M1 candidates, BUY/SELL and
confirmation on/off. All risk, entry, lifetime and admission thresholds stayed fixed.
This is an exploratory follow-up on reused development history, not independent
confirmation. Total search burden is 20 candidates, including all failed attempts.

| Layout / side / confirmation | Trades | Net USD | Cash PF | Jan-Mar / Apr-Jun trades | Positive months |
|---|---:|---:|---:|---:|---:|
| M15_M5_M1_BUY_confirm0 | 13 | -36.23 | 0.48 | 2/11 | 1 |
| M15_M5_M1_BUY_confirm1 | 0 | 0.00 | 0.00 | 0/0 | 0 |
| M15_M5_M1_SELL_confirm0 | 19 | -17.96 | 0.81 | 8/11 | 0 |
| M15_M5_M1_SELL_confirm1 | 3 | 13.72 | 2.29 | 3/0 | 2 |
| M5_M3_M1_BUY_confirm0 | 65 | -1.86 | 0.99 | 35/30 | 2 |
| M5_M3_M1_BUY_confirm1 | 2 | 8.70 | 2.37 | 1/1 | 1 |
| M5_M3_M1_SELL_confirm0 | 65 | 26.02 | 1.09 | 32/33 | 2 |
| M5_M3_M1_SELL_confirm1 | 4 | 22.79 | 4.82 | 2/2 | 3 |

Frozen choices: []. Decision: **NO_TRADE**.
Individual positive totals remain development results, not proven live edge.

No candidate is activated for live trading. October remains unused.

## Session-room execution fix (7.136)

The 7.135 source and all 20 original trials are preserved at commit
005bb491f3a5df5be3f435fc64647324a36599b4. The legacy non-zone baseline also reproduced
264 trades and -165.32 USD, confirming that the new method did not change that path.

One M5-zone SELL was entered on March 18 at 22:47 and exited March 19 at 01:05
(server clock), a 138-minute difference in minute-resolution timestamps. It lost
14.68 USD against 9.90 USD initial stop risk. Initial risk is not a guarantee of
maximum realized loss through gaps. This prevents claiming a hard 45-minute cap.

7.136 requires at least holding-limit + five minutes before the end of a broker
trading session. Missing session metadata blocks entry; overnight sessions are
handled explicitly and synthetic tests cover ordinary/overnight boundaries.
Both active M5/M1 BUY and SELL paths were re-executed for Jan-Jun without a
confirmation filter, solely to verify the execution change, not to select winners.

| Side | Trades | Net USD | Cash PF | Median holding upper bound (min) | Holding upper bound >46 min |
|---|---:|---:|---:|---:|---:|
| BUY | 65 | -1.86 | 0.99 | 7.0 | 0 |
| SELL | 65 | 26.02 | 1.09 | 10.0 | 1 |

Every resulting fill passed the session-room audit. Remaining long exits, if any,
are explicitly listed in the verification JSON. Session metadata reflects the
tester's broker specification and cannot guarantee historical schedule accuracy
or protection from unforeseen outages. This fix does not establish strategy edge.

Journal entry/exit timestamps are minute-resolution; reported conservative duration
statistics add one minute at the exit boundary. A displayed upper bound of 46 does
not itself mean a 46-minute actual holding time.

All 18 targets in build zone-session-build/62ea1213b95b426d8a87e97cade14ff6 compile
with zero errors/warnings. The final branch remains research only: **NO_TRADE**.
Twenty strategy trials, one legacy regression, and two execution checks completed.

Reference: https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade

## Final execution verification (7.138)

A dedicated 7.137 trace reproduced the long SELL and recorded return code 10018
(market closed) on timed-close attempts. Broker session metadata is 01:05-23:55
server time, but that did not prevent the observed quote/session interruption.
The five-minute session buffer did not fix it; that failed check is retained.

7.138 uses a 60-minute safety buffer in addition to the 45-minute holding horizon,
with an explicit input and failed-close retcode logging. This operational buffer
was chosen after the observed discrepancy, not by optimizing profit. It still
cannot guarantee execution during an unforeseen halt or data outage.

| Side (M5 zone / M1 entry, middle-TF filter off) | Trades | Net USD | Cash PF | Stressed Jan-Mar R | Stressed Apr-Jun R | Exits over 46-min upper bound |
|---|---:|---:|---:|---:|---:|---:|
| BUY | 64 | 8.34 | 1.03 | -12.2606 | 4.6679 | 0 |
| SELL | 63 | 31.66 | 1.12 | 10.0402 | -11.9989 | 0 |

All fills in these two re-executions satisfied the 105-minute session-room check.
The result is an execution verification on reused history, not fresh strategy
validation or permission to promote. The broader matrix was executed with 7.135;
only these two paths were rerun with the final buffer. No other layout inherits
these results. Final decision remains **NO_TRADE**.

Total this task: 26 real-tick tester runs (20 candidate trials, one legacy
regression, two initial session checks, one close-error trace, two final buffer
checks). Final build 2616e0e6ba9643a18d59c7e9c22011b1 compiles all 18 targets with
zero errors/warnings. 44 Python research tests passed. October remained unused.
