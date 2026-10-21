# KATARINA AI Brain — historical real-tick shadow research (2026-10-10)

## Objective
Collect historical market information **now**, without waiting for an open
trading session. This experimental implementation replays the immutable
`trend_impulse_break_v1` hypothesis against closed historical M1/M5 bars and
seeks actual broker bid/ask tick quotes for entry and 15-minute markout.
It does not create orders or imply a backtested executable equity curve.

## Observed on the authorized VPS
Broker terminal: `C:\Program Files\MetaTrader 5 ALFA\terminal64.exe`.
Historical MT5 bar AND tick retrieval was directly verified for seven named
instruments at 2026-08-03, 2026-09-15 and 2026-10-08 (08:00 UTC).
No new live trading or default-terminal initialization is authorized.

Two completed all-catalogue snapshots:
- **2026-09-15 through 2026-09-30 UTC**: 74 discovered symbols, 55 with
  historical M1 bars, 1,425 tick-quoted shadow markouts; **6** matched the
  retained spread/ATR <= 0.15 research gate.
- **2026-10-01 through 2026-10-09 UTC**: 74 discovered, 55 with M1 bars,
  843 quoted shadow markouts; **7** passed the same spread gate.
- **Total: 2,268 marked observations, 13 spread-pass**; 2,255 cost-screen
  rejects must remain rejected as trade setups regardless of their markouts.
- Among spread-pass only: BUY 9, mean **-6.4053 bps**, 2/9 positive;
  SELL 4, mean **+0.9093 bps**, 2/4 positive.
- Symbol-side spread-pass counts: XAUUSD.vx BUY 7, JPN225.vx BUY 1,
  JPN225.vx SELL 1, NAS100.vx SELL 2, US30.vx BUY 1,
  US30.vx SELL 1. No group has >=30 observations across >=10 UTC dates.
- Research-only conclusion: **NO_TRADE**, no profitable method validated.

## Exact historical sampling contract
- A signal is computed exclusively from the most recent **fully closed**
  M1 bar and 120 prior/current CLOSED M1/M5 bars, with completed M5 candle
  close no later than the signal time. Missing/gapped historical context is
  rejected rather than forward-filled.
- A cheap, necessary (not sufficient) breakout/body/volume filter avoids
  expensive feature calculations for irrelevant bars. The original shadow
  hypothesis, Wilder ADX, closed-candle EMA, ATR and regime classifier are
  reused unmodified. BUY and SELL respect the broker's current trade mode,
  noting that historical trade permissions may have differed.
- Entry must have a real broker tick **at or after** the signal close within
  90 s; exit must have a real tick at or after **entry tick + 900 s** within
  90 s. No tick => no fabricated markout. Entry BUY pays ask and exit
  receives bid; SELL receives bid and covers at ask. Overlapping candidate
  intervals per symbol are omitted.
- Historical external news vintages, prior economic actual/forecast values,
  old broker sessions and per-trade commissions/slippage were NOT recovered.
  No current news is backdated into old signals.
- The spread-to-M1-ATR <=0.15 limit was **not relaxed**; rejected setups are
  kept only as a diagnostic group. No measured markout is a real fill, TP/SL
  sequence, cash profit, win-rate claim or model-promotion decision.
- September/October price periods had already been studied in previous
  KATARINA research. These results are EXPLORATORY, not untouched holdout
  or forward validation. Searching new variants on them can overfit.

## Evidence location (VPS, not GitHub)
`C:\KatarinaDev\artifacts\historical-brain\`
- `sep15-30-all-broker-ticks-v2.json` (SHA256
  e1f96e59927da5af54748ec44b9335c50c8536c345b14cf4b5e72869f17f0663)
- `oct1-9-all-broker-ticks-v2.json` (SHA256
  60e21cec7be3b8f4bff63f4ad1d5d5346ff17d303262bffd334f95b3421f4a0a)
- `2026-09-15-to-10-09-audit.json` (checks time ordering, quote arithmetic,
  controls, source hashes, per-market counts and sample sufficiency)
- `2026-10-08-to-10-10-pilot.json` (first diagnostic pilot, earlier script
  version — NOT comparable with the expanded blocked-cost groups)
- `oct1-9-seven-markets-ticks-v2.json` (subset reproduction).

## Reproducibility
From the repository root, with `C:\KatarinaDev\brain-runtime\Scripts\python.exe`:

```
python scripts/research/historical_shadow_ticks.py --start 2026-09-15 --end 2026-10-01 --symbols all --output PATH_TO_NEW_UNIQUE_JSON
python scripts/research/historical_shadow_ticks.py --start 2026-10-01 --end 2026-10-10 --symbols all --output PATH_TO_NEW_UNIQUE_JSON
python scripts/research/audit_historical_shadow_ticks.py --report PATH_TO_SEP_JSON PATH_TO_OCT_JSON --output PATH_TO_NEW_UNIQUE_AUDIT_JSON
```

Exact file paths cannot be overwritten silently. Keep output archives out of
Git to avoid large sensitive terminal evidence and repository duplication.

## Next validation
Collect earlier months in bounded, dated partitions from the existing broker
market history, adding missing-quote and spread quality monitoring, then
investigate M1 vs M5 execution horizon **without lifting the current risk
guardrails**. Any new candidate rule needs pre-registration and evaluation
on separate future data (or clearly labeled exploratory old data). Do not
enable trading until stress-tested expectancy after spread, commissions,
slippage, SL/TP path, broker contract specifications and sufficient out-of-sample
observations are shown.

References for MT5 API details:
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py
