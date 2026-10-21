# Bounded scalping entry comparison — 2026-10-10

Decision: **NO_TRADE**. No tested method establishes a robust edge.

## Methods and controls

Research EA 7.140, XAUUSD.vx, M1 entries with closed M5 context.
Trend reclaim: ADX14 >= 20 and M5 close/EMA20/EMA50 aligned with direction;
M1 touches EMA20 within 0.1 ATR, closes back across it with directional candle,
and breaks the preceding candle high/low.
Range sweep: M5 ADX14 <= 20; M1 sweeps the preceding 20-bar range by
0.05–0.8 ATR and closes back inside with directional confirmation.

BUY and SELL run separately. Same initial SL 1.3 ATR, TP 1.5 initial R,
cash-risk ceiling USD 10, maximum hold 45 minutes, session buffer 60 minutes.
Position size is rounded down to broker volume steps; ineligible minimum lots
are skipped. No profit lock. No production execution enabled.

Four predeclared development candidates; Jan–Mar training, Apr–Jun selection.
At least 30/20 trades, 10 trading days per window, positive net R and PF >= 1.1
after subtracting 0.1 R per trade, and four positive development months required.
Best sufficiently sampled failed candidate per side receives a frozen Jul–Sep
diagnostic only; this cannot override failed development gates. October unused.

## Results

| Method / side | Jan–Jun trades | Net USD | Cash PF | Stressed Jan–Mar R | Stressed Apr–Jun R | Gate |
|---|---:|---:|---:|---:|---:|---|
| m5_trend_reclaim_BUY | 942 | -1449.31 | 0.72 | -174.4698 | -109.8772 | FAIL |
| m5_trend_reclaim_SELL | 970 | -622.23 | 0.87 | -54.6301 | -123.7191 | FAIL |
| m5_range_sweep_BUY | 217 | -302.26 | 0.73 | -48.0753 | -9.2234 | FAIL |
| m5_range_sweep_SELL | 205 | -206.47 | 0.81 | -25.4721 | -22.0433 | FAIL |

| Frozen diagnostic | Jul–Sep trades | Net USD | Cash PF | Stressed net R | Decision |
|---|---:|---:|---:|---:|---|
| m5_trend_reclaim_BUY | 240 | -267.53 | 0.79 | -58.3127 | NO_TRADE |
| m5_trend_reclaim_SELL | 225 | 54.01 | 1.05 | -12.0919 | NO_TRADE |

The later SELL cash gain does not survive the additional cost stress.
Neither direction qualifies for promotion. Separate runs cannot be added
together as a simulated combined portfolio.

## Verification and limits

60 Python research unit tests passed. All 18 MQL build targets compiled with
zero errors/warnings. These establish implementation checks, not profitability.
All six tester runs completed; reports indicate 100% real ticks. Fill audits
reconcile counts and verify causal closed context, risk ceilings, stop distance,
regime and session room. Journals have minute precision: holding upper bounds
allow one minute of rounding. See JSON holding audit for each run.

Reported commission and swap are zero in this tester environment. Cash figures
are the tester outputs; 0.1 R stress is a sensitivity assumption, not a calibrated
model of every real execution cost. Broker data, fills and a single symbol limit
generalization. Development history was reused, and later history was partly
inspected in previous research: this is not untouched prospective validation.
All failed candidates remain archived for reproducibility, not activated.

Combined with the exit audit this iteration executed 16 tester runs: eight exit
development runs, two frozen exit diagnostics, four entry development runs and
two frozen entry diagnostics. The search is bounded, not exhaustive optimization.

## Research references

- New York Fed, Carol Osler, Support for Resistance:
  https://www.newyorkfed.org/research/epr/00v06n2/0007osle.html
- New York Fed, Currency Orders and Exchange-Rate Dynamics:
  https://www.newyorkfed.org/research/staff_reports/sr125.html
- MetaTrader 5 tester report and excursion definitions:
  https://www.metatrader5.com/en/terminal/help/algotrading/testing_report

These sources motivate hypotheses about levels, continuation and reversals.
Historical FX evidence is not proof that these XAUUSD rules are profitable.
The implementation was evaluated on its own broker data.

## Next research boundary

Do not expand indicator combinations merely to obtain a passing backtest.
A further experiment first needs a specific falsifiable hypothesis and a fresh
evaluation window. Preserve October as unused in this iteration. The AI selector
must retain NO_TRADE when no candidate passes; do not weaken gates to force entry.
