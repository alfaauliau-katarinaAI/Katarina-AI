# Prospective shadow strategy laboratory — 2026-10-10

## Goal / status
KATARINA now records one directional research hypothesis, named
`trend_impulse_break_v1`, when market conditions and a completed M1 candle
meet predefined rules. **NO_TRADE and live_execution_enabled=false remain
unchanged.** This does not revive prior failed range-sweep experiments.

## Before-seeing-forward-returns hypothesis
- M5 regime TREND_UP -> BUY-only research; TREND_DOWN -> SELL-only research.
  This requires prior ADX(14), directional index and efficiency classification.
- The most recently CLOSED M1 candle closes beyond the previous six closed
  candle highs/lows by > 0.05 of M1 ATR(14); it agrees with M1 EMA20.
- Body is >= 60% of candle range, closes inside the directional outer quarter,
  volume is >= 1.25x the previous 20 closed candle volume mean.
- Reject a candle wider than 3x M1 ATR, a stale M1 bar (>90s) or restricted
  broker side. A complete quote/market validity gate is applied beforehand.
- RANGE/TRANSITION/UNKNOWN -> abstain; previous range-sweep strategy failed.
- Scans use closed bars from MT5 shift=1; entry-time bid/ask (not old candle
  prices) becomes the forward observation. This prevents backdated fills.
- Latest observer JSON exposes `shadow_candidate_count` and a concise
  `shadow_candidate_watchlist`; both remain research-only.

These are **untuned research hypotheses**, not profitable setups or investment
recommendations. The earlier Jan-Sep optimization and tests remain unsuccessful.

## Read-only outcome diagnostic
`python scripts/ai/evaluate_shadow_hypotheses.py --database PATH/brain.sqlite3`

Only this named family and its matching side is evaluated at the preselected
900-second quote markout horizon. The report:
- Compares bid/ask spread-adjusted quote changes; no SL/TP path, real fills,
  commission, actual slippage, realized PnL or account-currency normalization.
- Keeps entry-time macro availability; research context remains frozen with the
  observation, not revised retrospectively.
- Excludes overlapping observations **within each symbol/side/context/regime
  stratum**. Different strata/markets may still be dependent.
- Requires at least 30 matured observations spanning >=10 UTC dates and <=20%
  missing among matured horizon outcomes for adequate *descriptive* coverage.
- Shows averages/median and how many dates have positive markouts. No model
  can be promoted from these statistics, even if quoted markouts are positive.
- Tracks pending outcomes separately from expired or missing observations.
- Existing pre-deployment data is NOT backfilled with hypothetical signals.

## Next validation gate
When trading resumes, collect prospective observations without changing
thresholds. Inspect sample coverage, event effects and clock health. Then
test any retained hypothesis with broker tick data and executable bid/ask
SL/TP paths, realistic fees/slippage, independently frozen chronological
walk-forward windows, risk budgets and broker session verification. Test
MQL5 iADX parity before relying on its classifications for execution.

Official references:
- MT5 closed-bar indexing: https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrompos_py
- MT5 ADX indicator buffers: https://www.mql5.com/en/docs/indicators/iadx
