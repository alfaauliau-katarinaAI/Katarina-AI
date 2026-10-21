# KATARINA Market Regime Intelligence v1 — Implementation & research audit
**Date:** 2026-10-11 WIB. **Status:** research-only, NO_TRADE.

## Objective
Differentiate observed market phase without recycling one universal
scalping strategy on unrelated broker symbols. Separate higher-timeframe
trend orientation (H1/M15) from M5 market phase; optionally inspect M1
timing. Return continuation, structural reversal, pullback, sideways,
local continuation, transition, or unknown. Explicitly no live entry
authorization and no advertised probability of future returns.

## Implementation
- Source: `src/katarina/intelligence/market_regime_intelligence.py`
- Observer: `src/katarina/intelligence/multi_market_brain.py`
- Study: `scripts/research/backtest_market_regime_labels.py`
- Audit: `scripts/research/audit_market_regime_labels.py`
- Summaries: `scripts/research/summarize_market_regime_study.py`
- Strict tests: `tests/unit/intelligence/test_market_regime_intelligence.py`
  and `test_regime_observer_and_audit.py`

Input timeframe: last 120 completed M5, M15, H1 candles. M1
optional, 60 completed bars, for independent low-timeframe timing
assessment. The system rejects future, duplicate, nonfinite, invalid,
and stale bars, including recent gaps; prior exchange/weekend
closures in 120-bar warmup do not automatically invalidate otherwise
valid newer bars. Wilder ADX14, +/-DI, EMA20/50 and 20-bar
directional efficiency are computed only from completed bars.
Five/six-point swing-sweep evidence is checked only AFTER the sweep
and after subsequent completed displacement through the previously
established structure, not from future-confirmed swings.

Labels (11 total):
- CONTINUATION_UP / DOWN: H1 and M15 directional bias together
  with M5 confirmation; local trend must exceed minimum observed
  ADX/efficiency. These describe context and are not BUY/SELL calls.
- LOCAL_CONTINUATION_UP / DOWN: M15 and M5 aligned while H1
  is neutral/low-trend; not misreported as full H1 continuation.
- PULLBACK_UP / DOWN: H1/M15 directional context aligned, but M5
  currently opposed; countertrend phase is NOT reversal confirmation.
- REVERSAL_UP / DOWN: prior H1 opposite context, prior M5 liquidity
  sweep, subsequent completed displacement above/below pre-sweep
  level, and M15/M5 side confirmation. Very rare by design.
- SIDEWAYS: both M15 and M5 have low ADX and low price-efficiency.
- TRANSITION: ambiguous/contradictory timeframe observations; abstain.
- UNKNOWN: missing or stale history, invalid candle, unregistered
  broker symbol or insufficient data.

Symbol registry has independent, initially fixed threshold profiles
for XAUUSD.vx, NAS100.vx, US30.vx, JPN225.vx, EURUSD.vx, GBPUSD.vx,
USDJPY.vx. Values are NOT optimized or calibrated to trading returns;
any symbols not registered are not assigned a copied profile.

The previous `regime_detail` and existing per-symbol shadow
hypotheses continue as separate research controls. New observer
field `market_regime_v1` does not authorize or gate real orders.
Registered markets now additionally fetch read-only M15 and H1
closed bars; evidence snapshots are deduplicated by SHA256 in
the existing SQLite market_evidence table. No new account orders
are sent. Non-registered broker symbols retain observation-only
coverage.

## Broker historical evaluation
Valetax demo / MT5 ALFA .vx catalogue. Historical UTC windows:
- 2026-08-16 to 2026-09-01 exclusive;
- 2026-09-15 to 2026-10-01 exclusive;
- 2026-10-01 to 2026-10-10 exclusive.

M5 completed-bar time series is sampled every 30 minutes with H1/M15
state reconstructed only as of that timestamp. After labeling, observe
future M5 CLOSE displacement in units of the M5 entry ATR at +1h
and +4h. **This is not real bid/ask TP/SL PnL** and no spread,
commission, swap, fill latency, or slippage is deducted. The
calendar periods were previously inspected by KATARINA, and this
same historical data influenced a revision that distinguished local
trends/pullbacks. It is NOT an untouched final OOS test.

Exact audited artifact:
`C:\KatarinaDev\artifacts\historical-brain\market-regime-seven-symbols-mtf-final-v2.json`
Integrity record:
`C:\KatarinaDev\artifacts\historical-brain\market-regime-seven-symbols-mtf-final-v2-audit.json`

The independent auditor verified **9,687 observations** and 162
regime-symbol-period diagnostic groups. State counts:
| State family | Observations |
| --- | ---: |
| H1/M15/M5 full continuation, both directions | 1,269 |
| M15/M5 local continuation, both directions | 918 |
| Sideways | 709 |
| Pullbacks | 10 |
| Structurally confirmed reversals | 11 |
| Transition / disagreement | 6,378 |
| Unknown / invalid / stale | 392 |
| **Total** | **9,687** |

### Directional diagnostic at +1h after full continuation
Only within valid *completed M5 future close* outcomes; overlapping
events and samples across timeframes are not independent trades.

| Symbol | +1h measured events | Same direction as label |
| --- | ---: | ---: |
| XAUUSD.vx | 190 | 45.8% |
| NAS100.vx | 173 | 50.3% |
| US30.vx | 157 | 43.9% |
| JPN225.vx | 176 | 49.4% |
| EURUSD.vx | 208 | 54.3% |
| GBPUSD.vx | 183 | 42.6% |
| USDJPY.vx | 159 | 42.8% |

NAS100 continuation at +4h: 166 measurable observations, 55.4%
in the labeled direction. No proof of positive broker-net edge.
A future close-direction check cannot replace market regime ground
truth, calibrated label probabilities, transition-detection accuracy
or a trade-level sequential TP/SL test. Sideways does NOT imply
the next 1h has less than one M5-ATR movement. Reversal count
only 11 across seven symbols/three periods; inadequate to claim
true reversal precision.

Strong implication: **the classifier now observes structure and
refuses uncertain signals, but is not a profitable trading model**.
The high share of TRANSITION is partly intentional abstention,
and partly a limit of simple trend/ADX indicators.

## Tests, safety, and integration
- Deterministic UP, DOWN, SIDEWAYS, TRANSITION, PULLBACK,
  LOCAL_CONTINUATION, REVERSAL, UNKNOWN fixtures verify causality.
- Unfinished bars, missing data, invalid quotes, unknown symbols
  trigger UNKNOWN and no trade. Score 0-100 is heuristic evidence
  only, NOT probability or win rate.
- Observer still scans 74 broker catalogue symbols, only 7
  registered for special MTF regime; weekends can lead to UNKNOWN.
- `live_execution_enabled=false`, `entry_authorized=false`,
  `model_promotion_allowed=false`.
- Compare Wilder ADX calculations with official iADXWilder indicator
  buffer 0 (ADX), 1 (+DI) and 2 (-DI) on MT5 before high-stakes use:
  https://www.mql5.com/en/docs/indicators/iadxwilder
- ADX basics:
  https://www.metatrader5.com/en/terminal/help/indicators/trend_indicators/admi

## Next validation
1. Collect fresh forward observations *after this design freezes*
   in the read-only market observer, with source SHA fingerprints.
2. Validate regime labels and state changes per broker symbol
   against a predefined swing/structure reference with blinded
   timestamps and measurable stability, not only forward direction.
3. Measure whether conditioning each symbol-specific setup on its
   matching regime improves TP-first hit expectancy after real
   bid/ask spread and conservative entry/exit slippage, compared
   with identical setup WITHOUT regime gate. Use chronologically
   separate unseen samples.
4. Confirm iADXWilder against MT5 buffer data; broker historical
   dates and price feed changes can affect classification.
5. No trading promotion until repeated unseen, net-positive
   risk-adjusted evidence with sufficient independent samples.
