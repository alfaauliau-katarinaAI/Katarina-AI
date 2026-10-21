# KATARINA — Historical Analog Prediction Memory v1
**Date:** 11 October 2026 WIB
**Branch:** `research/brain-forward-outcomes-20261010`
**Broker:** connected Valetax demo read-only history (source events)
**Decision:** `NO_TRADE` / `model_promotion_allowed=false`.

## Problem and reasoned choice
The previous historical market regime / 1h direction logistic models
performed worse than a train-only prevalence baseline on both 1h
and 4h chronological windows. Building a larger black-box or importing
a hedge-fund strategy without instrument-level evidence would worsen
overfitting risk. The first alternative chosen was a small,
interpretable **same-symbol case memory**:
- Observe completed H1, M15, M5 trend, ADX, +/-DI, directional
  efficiency and time-of-day, together with a causal regime label.
- Retrieve 25 similar, *already resolved* snapshots from that
  symbol only. A neighbor's outcome and timestamp must have
  completed plus a 4-hour embargo before the prediction.
- Smoothed empirical up-fraction with fixed 35-example
  train-only prior. It is an **uncalibrated direction estimate**,
  NOT a trading win probability. Abstain when neighbors are
  too dissimilar/low-quality, insufficient, or market data stale.
- Profiles for different broker symbols are never mixed. No
  order-sending code exists in the historical memory observer.

## Verified historical evidence
The archived M5/M15/H1 study was already inspected in KATARINA's
research. Development August 16–31, September 15–30; later October
1–9; calendar gaps remain gaps. Predictions were only evaluated
on later chronological windows with 4h label-resolution embargo,
but **these are reused histories, not pristine future OOS**.

Frozen bank cutoff 2026-10-10 12:00 UTC:
`C:\KatarinaDev\artifacts\historical-brain\frozen-per-symbol-analog-memory-v1.json`
Contains 17,768 *horizon-specific labeled examples* over seven
broker symbols; a single dated observation can appear once for 1h
and again for 4h, so this is NOT 17,768 independent trades.
Independent sample audit checked all 17,768 records' causal
features, actual label timestamps, target signs and lack of
future outcome leakage.
- XAUUSD.vx: 1h 1,251, 4h 1,181.
- NAS100.vx: 1h 1,251, 4h 1,205.
- US30.vx: 1h 1,251, 4h 1,205.
- JPN225.vx: 1h 1,251, 4h 1,181.
- EURUSD.vx: 1h 1,356, 4h 1,308.
- GBPUSD.vx: 1h 1,355, 4h 1,307.
- USDJPY.vx: 1h 1,357, 4h 1,309.

Historical chronological backtests + auditor:
| Model (lower Brier is better) | 1h / 5,782 test cases | 4h / 5,548 |
| --- | ---: | ---: |
| Prevalence prior (trained on past only) | **0.250042** | **0.250857** |
| Old technical + regime logistic | 0.266788 | 0.280432 |
| New historical analog memory | 0.250926 | 0.251484 |

The analog approach is less bad than old logistic but does
**NOT beat the baseline overall**. Model promotion is blocked.

Auditors verified **11,330** individual predictions, **33,990**
example-provenance pointers, chronological training/test splitting,
scores, and reproducibility of sampled predictions.
Evidence:
- `analog-retrieval-1h-v1.json` / `-audit.json`
- `analog-retrieval-4h-v1.json` / `-audit.json`
- `historical-analog-dayblock-uncertainty-v1.json`

Per-UTC-day block bootstrap of (baseline Brier – analog Brier):
- USDJPY 4h: +0.001497; 95% CI approx
  **[-0.005697, +0.007448]**, September and October both positive
  but neither overall-confidence nor broker profitability established.
- NAS100 1h: -0.003019; approx 95% CI
  **[-0.005664, -0.000371]**. Reject this one-hour
  analog predictor as a trading signal.
- All bootstrap intervals are exploratory, overlapping horizons
  and multiple-model search are not fully corrected.

## Add entry outcome memory: actual quote path TP/SL
The closer-to-trading question is NOT just 'up in 1h?',
but 'will this **symbol-specific setup** reach its structural
TP before structural SL after bid/ask/slippage?'
New immutable research bank
`C:\KatarinaDev\artifacts\historical-brain\tp-sl-first-event-memory-v1.json`
stores 423 *historically replayed*, per-symbol entries:
| Market/unique setup | Entry outcomes | TP | SL | TIME | Average simulated R |
| --- | ---: | ---: | ---: | ---: | ---: |
| NAS100 continuation | 29 | 12 | 13 | 4 | +0.149 |
| XAUUSD sweep rejection | 345 | 79 | 261 | 5 | -0.264 |
| US30 failed breakout | 28 | 10 | 18 | 0 | -0.0014 |
| JPN225 broker opening impulse | 21 | 8 | 12 | 1 | -0.079 |

The event bank is a **training-research dataset**, not a trained
meta-labeler, not actual executed broker fills, and not a portfolio
backtest. It joins prior regime as-of <=30min to entry and includes
one adverse broker tick at entry and exit on top of actual
historical bid/ask. Source hash and outcome/clock audit checked
all 423 events. The 345 gold examples are sufficiently numerous
to study avoiding bad setups, but do not imply the strategy is
profitable. NAS/US30/JPN have too few events for a reliable
separately trained precision model.

## Operational read-only observer
`Katarina-AnalogMemory-Observer` is a **SEPARATE** Windows task
registered under the same interactive user as the existing
market observer, scheduled every **15 minutes**. It reads only
the original observer JSON plus immutable frozen memory and
writes `current-analog-shadow.json`. It cannot send orders.
Latest run test: result code 0; seven symbols recognized;
seven abstained due stale/UNKNOWN candles at weekend.
Never emits a recommendation from old quotes.
Training bank is frozen; new true future labels must mature
and be validated before any controlled update. No continuous
self-training on its own predictions.

## Trade-offs and own strategic assessment
1. **Keep:** causal multi-timeframe snapshots and same-symbol
   analog retrieval for explainable historical evidence;
   fixed audit/evidence fingerprints and explicit abstention.
2. **Do NOT deploy for trading:** this analog frequency as
   calibrated 1h/4h up probability or broker-net setup edge.
3. **Next most promising:** event-aligned, symbol-specific
   TP-first-vs-SL-first meta-labeler with real tick bid/ask,
   same-side setup logic, genuinely later unseen evaluation
   and conservative broker fees, minimum independent dates,
   and full coverage accounting.
4. **Need more data:** pattern *shape* embeddings (last N
   completed candles, normalized by volatility), fresh
   forward tape and official timestamped broker fees.
   Test incremental value vs the baseline, not add
   unvalidated factors to production.
5. **Avoid:** universal pair model, forced buy/sell,
   tuning analog distance to historical October,
   using future-resolved outcomes within validation,
   using candle direction accuracy as win-rate.
6. If the matched examples are far away, sparse or the
   spread consumes expected target, return ABSTAIN/NO_TRADE.

## Research sources, not copied secret fund signals
- AQR Moskowitz/Ooi/Pedersen (2012), Time Series Momentum:
  https://www.aqr.com/insights/research/journal-article/time-series-momentum
  Historical effects concern much longer futures horizons,
  not proof of M1 scalping.
- Hudson & Thames, Meta-labeling and Triple Barrier:
  https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy-triple-barrier-method/
  Need an effective primary signal, quality event and good
  sample data before using meta-labeling.
- Hudson & Thames labeling reference:
  https://hudsonthames.org/machine-learning-trading-essentials-part-2-fractionally-differentiated-features-filtering-and-labelling/

Scripts in `scripts/research`: evaluate_historical_analog_memory,
audit_historical_analog_study, freeze_historical_analog_memory,
audit_frozen_analog_memory, assess_analog_uncertainty,
prepare_trade_event_memory, audit_trade_event_memory,
probe_current_market_analogs, register_analog_shadow_task.
Core implementation:
`src/katarina/intelligence/analog_feature_schema.py`,
`src/katarina/intelligence/historical_analog_memory.py`.
