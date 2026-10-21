# M5/M1 scalping: entry/exit audit and bounded exit comparison

Research only. Extends PR #17, commit f7c543130472fded8ab0f89aff7bfacb031ab722.
This experiment does not claim a globally optimal scalping strategy.

## What the existing 127 trades show

Source: final 7.138 session-buffer checks, Jan-Jun 2026, fixed 10 USD planned risk
ceiling, M5 first-touch zones, M1 entry, middle-timeframe confirmation OFF.

BUY: 64 trades, +8.34 USD but -1.1927 net R before additional stress, 26 wins and
38 losses. Only 3 losers reached +1R; 11 reached +0.75R. Median loser MFE 0.3164R.
SELL: 63 trades, +31.66 USD and +4.3414 net R, 28 wins and 35 losses.
Only 6 losers reached +1R; 11 reached +0.75R. Median loser MFE 0.3700R.
Median winning-trade MAE: BUY 0.3517R, SELL 0.4105R.
Mean quoted spread at entry: BUY 0.0896 entry ATR, SELL 0.0885 entry ATR.

Cash P&L and sum of R can have different signs because broker lot steps mean
actual initial risks differ. The 10 USD ceiling is not exactly 10 USD per trade.
BUY's first quarter and SELL's second quarter were weak. Context-state and session
groups are descriptive small samples, not filters promoted into this experiment.

This evidence does not support assuming that all losses can be fixed by extending
targets or tightening stops. MAE/MFE are censored at the actual exit and do not
show the ordering of extrema. No modified-exit result is fabricated from MFE.

## Frozen comparison

Eight complete real-tick executions: BUY and SELL each with four profiles:

| Profile | Target | Time limit | Profit lock |
|---|---:|---:|---|
| Baseline reproduction | 1.5R | 45 minutes | Off |
| Nearer target | 1.1R | 45 minutes | Off |
| Profit lock | 1.5R | 45 minutes | At +0.75R, move stop to +0.05R |
| Faster timeout | 1.5R | 15 minutes | Off |

Entry logic, stop location, spread limits and cash-risk ceiling remain fixed.
The session admission horizon stays 105 minutes for every profile: 45+60 or
15+90. Otherwise reducing the time limit would accidentally admit new rollover
entries and confound the comparison. Position availability can still change when
exits change; every profile therefore executes fully in MT5.

Profit locking uses current bid for BUY and ask for SELL, with initial risk fixed
at entry. Stop changes are monotonic, rounded conservatively to symbol tick size,
and respect broker stop/freeze distances. A +0.05R price lock does not guarantee
net break-even after commission, spread changes or slippage. Failed modification
is not counted as success. Successful modifications receive their own quote audit.

MQL runtime self-tests cover both sides, premature triggering, widening rejection,
and zero risk. Python audit rejects nonfinite values, premature modifications,
stop widening, quote crossing and targets outside the declared lock.

## Chronology and choice

- Jan-Mar: first development window.
- Apr-Jun: selection window.
- Jul-Sep: later audit of frozen choices, one maximum per side.
- October remains unused.

Development thresholds remain those from PR #17: at least 30/20 trades and
10 days in each window; positive R and R-profit-factor >=1.1 after an extra
0.1R/trade stress in both; at least four positive months. Boundary-crossing trade
labels are purged. Ranking maximizes the weaker quarter's stressed expected R,
with candidate id as deterministic tie-break.

Prefer eligible candidates. If none qualifies for a side, the best sufficiently
sampled FAILED development candidate receives a later diagnostic, explicitly
labelled rejected_candidate_diagnostic. A positive later diagnostic cannot repair
its failed development gate. No replacement is selected from later results.

Jan-Jun history was already reused extensively, and Jul-Sep partly inspected in
earlier research. These are historical diagnostics, not pristine prospective
proof. The search includes previous strategy and indicator attempts; the eight
profiles are not eight independent new opportunities. No live promotion.

## Verification and references

- 52 Python research tests pass, including eight new profit-lock audit tests.
- All 18 MQL targets compile with zero errors/warnings, version 7.139:
  scalp-exit-build/4a389f5e693448a69d873a3559df06d1.
- Both baselines must reproduce exactly before exit results are accepted:
  BUY 64/+8.34 USD; SELL 63/+31.66 USD.
- Report/journal reconciliation, zone chronology, original risk and unchanged
  session horizon are audited. Stop modifications are audited separately.

Primary documentation:
- https://www.metatrader5.com/en/terminal/help/algotrading/testing_report
  MAE/MFE describe adverse/favorable excursions of actual positions.
- https://www.metatrader5.com/en/terminal/help/algotrading/testing
  Actual strategy execution versus parameter optimization.
- https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade
  Broker session boundaries for entry admission.

No external trading code copied and no AI probability threshold tuned.

## Results

Eight Jan-Jun executions completed, including both exact baseline reproductions.
Both frozen side choices received full Jul-Sep execution audits.

| Side / exit | Trades | Jan-Jun net USD | Cash PF | Stressed Jan-Mar R | Stressed Apr-Jun R | Development gate |
|---|---:|---:|---:|---:|---:|---|
| BUY / baseline | 64 | 8.34 | 1.03 | -12.2606 | 4.6679 | FAIL |
| BUY / near_target | 64 | -54.69 | 0.80 | -14.0301 | -1.3507 | FAIL |
| BUY / profit_lock | 64 | -16.19 | 0.92 | -9.3697 | -1.5586 | FAIL |
| BUY / fast_timeout | 64 | -18.65 | 0.92 | -13.2944 | 2.7734 | FAIL |
| SELL / baseline | 63 | 31.66 | 1.12 | 10.0402 | -11.9989 | FAIL |
| SELL / near_target | 63 | 39.97 | 1.17 | 5.0168 | -4.8362 | FAIL |
| SELL / profit_lock | 63 | 8.13 | 1.04 | 4.7397 | -9.5402 | FAIL |
| SELL / fast_timeout | 63 | 19.07 | 1.08 | 4.7279 | -7.9526 | FAIL |

### Locked later diagnostics

| Side / fixed exit | Jul-Sep trades | Net USD | Cash PF | Stressed net R | Decision |
|---|---:|---:|---:|---:|---|
| BUY / profit_lock | 17 | -45.12 | 0.33 | -8.7045 | NO_TRADE |
| SELL / near_target | 13 | -39.05 | 0.45 | -5.9264 | NO_TRADE |

Selection purpose for BUY: rejected_candidate_diagnostic; development pass: False.


Selection purpose for SELL: rejected_candidate_diagnostic; development pass: False.

No later outcome changes the frozen choice or rescues failed development gates.
No combined BUY/SELL return is inferred from separate runs. These diagnostics do
not establish a universally optimal method.

Stop-lock modifications were actually exercised and independently quote-audited.
Durations are conservative upper bounds from minute-resolution journals; the
per-run holding audit records any overrun beyond limit + one minute.

Final research decision: **NO_TRADE**. October unused; live execution disabled.
