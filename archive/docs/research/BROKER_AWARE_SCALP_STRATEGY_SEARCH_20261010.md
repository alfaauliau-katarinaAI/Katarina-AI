# KATARINA AI Brain — Broker-aware strategy search (10 October 2026)

## Executive research outcome

**NO_TRADE. No objectively validated profitable scalping setup was found.**

Read-only MT5 Valetax (demo account, USD, leverage 1:1000) research
on XAUUSD.vx, NAS100.vx, US30.vx, JPN225.vx, EURUSD.vx, GBPUSD.vx
and USDJPY.vx tested three new objective entry patterns and the
previous impulse-breakout control, separately by BUY/SELL.

Historical periods in UTC: Aug 16–31, Sep 15–30 and Oct 1–9, 2026.
September 1–14 was not tested in this run. October was previously
examined in other KATARINA research, **not an untouched holdout**.

The seven-symbol merged report contains 2,036 simulated entry points,
24,432 TP/SL/slippage scenario rows, 24,419 completed scenario outcomes,
13 incomplete outcomes, and 2,016 cohort summaries. Audits verified
bid/ask order-side arithmetic, broker contract size, quote chronology,
minimum stop distance, input provenance and no unauthorized live trade.

Four predefined ATR exit combinations:
TP1 / SL1, TP1.5 / SL1, TP2 / SL1, TP2 / SL1.5.
Adverse slippage stress per side: 0, 1 or 3 broker ticks. A historical
bid/ask spread is paid in the hypothetical entry and exit; no extra
spread is charged twice. Maximum quote path 30 minutes, 250ms
post-candle decision latency, up to 30 seconds to get an entry quote,
and no interpolation across missing quotes.

## Broker contract and fee evidence

Connected terminal: C:\Program Files\MetaTrader 5 ALFA\terminal64.exe
Broker company: Valetax International Limited.
Current MT5 account trade mode 0 = demo; account currency USD.
Historical deals with actual symbol-specific commissions were unavailable.

Current symbol metadata:
- XAUUSD.vx: 100 ounces/lot, min 0.01 lot, tick 0.01,
  stop level 31 points = 0.31 of quoted price.
- NAS100.vx: 10 contract units/lot, min 0.01, tick 0.1,
  stop minimum 37 points = 3.7.
- US30.vx: 10 contract units/lot, min 0.01, tick 0.1,
  stop minimum 35 points = 3.5.
- JPN225.vx: 1000 contract units/lot, min 0.01, tick 0.1,
  stop minimum 146 points = 14.6.
- EURUSD.vx, GBPUSD.vx, USDJPY.vx: nominal 100,000/lot,
  stop levels 16, 21 and 30 broker points respectively.

Public Valetax Standard account documentation advertises $0 commission,
market execution, and spreads from 1.2 pip. The .vx suffix and
contract specs correspond to the Standard instrument table, but
a missing executable trade commission history prevents guaranteeing
the account's exact historical fees. Extra real slippage is unknown.
Currency conversion for JPN225 and USDJPY's JPY profits was not
reconstructed using historic conversion rates, so account-dollar
results for those symbols are not reported.

Sources:
- https://valetax.com/account-types/standard/
- https://valetax.com/trading-instruments/metals/
- https://www.mql5.com/en/docs/python_metatrader5/mt5symbolinfo_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py

## Setup definitions and source references

Rules only use **fully closed** M1 and M5 bars, 120-bar warmups,
causal levels and point-in-time M5 direction and ADX:

1. EMA20 trend reclaim: previous candle on wrong side of EMA20,
   latest M1 candle retakes EMA; M5 direction aligned, ADX>=18,
   directional candle and relative tick activity.
2. Liquidity sweep and reclaim: M1 takes the previous 12-bar
   high/low by at least 0.05 ATR, closes back within/through
   the prior zone, with direction not opposite M5 context.
3. Breakout/retest: previous closed M1 candle breaks a prior
   12-bar level; latest candle retests and closes outside it,
   aligned with M5 trend, ADX>=18.
4. Frozen impulse-breakout research v1 as independent control.

Design inspiration, not trustworthy performance evidence:
- https://github.com/yeboster/liquidity-sweep-freqtrade
- https://github.com/guillemustafa-ux/ict-sweep-mss-fvg

## Audit and methodological limits

Completed batch trials:

| Symbols | Simulated entries | Scenario records |
| --- | ---: | ---: |
| XAUUSD and NAS100 | 1,011 | 12,132 |
| US30 and JPN225 | 967 | 11,604 |
| EURUSD, GBPUSD and USDJPY | 58 | 696 |
| Total | **2,036** | **24,432** |

Selection considered **216** symbol-family-side-TP/SL combinations
at 1 adverse broker tick on both entry and exit. Of these, 52
had adequate samples in both development windows; **zero** met the
predeclared dual-period profitability and 99% lower-confidence
daily mean requirements.

The *least negative* sufficiently sampled candidate was
US30.vx SELL, liquidity sweep/reclaim, TP1.5 ATR/SL1 ATR:
- August: 51 simulated paths, mean -0.116 R, PF 0.83;
- September: 52 paths, mean -0.106 R, PF 0.84;
- October diagnostic: 29 paths, mean -0.108 R, PF 0.84.

This is a **consistent losing hypothesis**, not a profitable setup.
XAUUSD liquidity-sweep SELL at TP2/SL1 swung from -0.192 R
in August, +0.065 R September, to -0.377 R October.
NAS100 EMA20 reclaim SELL has only ~+0.010 R in the examined
October samples and negative development, not a validated edge.

A further 324 symbol/setup/session-regime filters tested fixed
London/New York, strong-volume and ADX conditioning of existing
price paths. **Zero** passed positive dual-development 99%
lower-bound expectation. These filters are post-hoc exploratory.

Historical broker quotes are real, but hypothetical TP and SL
crossings are **not actual broker order fills**. Position sums are
not reliable portfolio simulations: independent family-side trials
on the same symbol may overlap or oppose one another; multi-asset
correlation, actual fills, dated news vintages, changes to broker
trading conditions, leverage regime near rollover and all
cross-symbol portfolio constraints are uncalibrated. There is
substantial multiple-testing and reused-history selection bias.
Production cost gate and live execution were NOT changed.

## Evidence saved on the authorized VPS

C:\KatarinaDev\artifacts\historical-brain\

- broker-aware-seven-symbol-study-v1.json
- broker-aware-seven-symbol-study-v1-audit.json
- broker-aware-seven-symbol-study-v1-selection.json
- session-regime-seven-symbol-diagnostic-v2.json
- Three input batch files and three matching integrity audit files,
  all retaining SHA256 source hashes.

Use scripts/research/benchmark_broker_scalp_setups.py,
merge_broker_scalp_studies.py, audit_broker_scalp_setups.py,
select_broker_scalp_diagnostics.py and
diagnose_session_regime_setups.py for reproducibility.
These scripts do not send orders and refuse to overwrite evidence.

## Decision

NO_TRADE. Prioritize evaluation of a materially new, confirmed
market structure/FVG plus liquidity event rather than re-tuning the
same failed EMA/sweep/breakout combinations to a desired number.
Reserve truly unused future price data, obtain measured real trade
fees and slippage, and enforce same-symbol opposite-side exclusion
before proposing any risk authorization.
