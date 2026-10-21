# KATARINA AI Brain — multi-timeframe historical lab, 2026-10-10

## Status: independent research finished; no validated scalping edge
The existing Windows VPS MT5 research account was queried directly using
historical closed bars and actual historical bid/ask ticks, **without waiting
for market reopening**. No order placement or live risk authorization was
introduced. The prior M1/M5 observer and its 5-minute Windows task remain
operational.

### Frozen exploration periods (UTC)
1. 2026-08-16 to 2026-09-01 exclusive.
2. 2026-09-15 to 2026-10-01 exclusive.
3. 2026-10-01 to 2026-10-10 exclusive.

**September 1–14 is not covered** in this report: these are three discrete
historical windows, not a continuous August–October backtest. Price periods
used here were previously researched in KATARINA; these are descriptive
exploratory results, not untouched out-of-sample proof.

### Experimental M1 entry / M5 trend context (original)
- 74 broker symbols discovered; 55 with M1 history in each window.
- Total 3,435 genuine historical entry/exit quote markouts, 23 retained by
  the frozen spread <=0.15 *M1 ATR* gate (0.67%).
- Spread-pass BUY: 14 observations, average -4.2109 basis points.
- Spread-pass SELL: 9 observations, average -6.1275 basis points.
- The remaining 3,412 are explicitly **cost-rejected**, not rescued by their
  theoretical results.
- Price change at 15 minutes only: no actual SL/TP fills or commissions.
  All historical macro availability is unknown, not fabricated.
- Cost profile (grouped by broker symbol/side) shows that certain FX symbols
  incur multiple times their M1 ATR in spread. This is an economic constraint,
  not an indicator code problem. For example, AUDCAD.vx entry samples had
  median spread-to-M1-ATR ratios >2 on both sides. Broker-specific.

### Experimental M5 entry / M15 trend context (new independent arm)
A newly frozen read-only diagnostic uses the same body/volume/breakout
numerical rules but CLOSED M5 signals, CLOSED M15 market-regime confirmation,
its own M5 ATR cost denominator, and first actual tick at/after M5 close.
This is **not** the same strategy as M1/M5, and performance cannot be
compared as an equal-signal controlled A/B test.
- August period: 209 tick-quoted candidates, **0** passed <=0.15 M5 ATR.
- September period: 238 candidates, **1** spread-pass (SELL, -0.7845 bps).
- October period: 141 candidates, **0** spread-pass.
- Total: 588 marked observations; **1** spread-eligible case.
- The September run was independently replayed with frozen M15 context
  closure timestamps to make the historical evidence audit complete.
- All 588 observations passed the causal timing, broker-direction, spread
  arithmetic, M5/M15 hash presence and missing-fill/unknown-macro audit.

### Decision
**NO_TRADE**. No strategy has sufficient statistically meaningful,
fee-calibrated samples. M5/M15 did not solve economic infeasibility.
*Do not loosen spread risk to force a profitable-looking backtest.*
Avoid ranking timeframe strategies by in-sample mean return; missing
commission/slippage and reused date windows preclude reliable promotion.

## Immutable audit files, kept on VPS not GitHub
Base folder:
`C:\KatarinaDev\artifacts\historical-brain\`

Historical M1/M5:
- `aug16-31-all-broker-ticks-v1.json`
- `sep15-30-all-broker-ticks-v2.json`
- `oct1-9-all-broker-ticks-v2.json`
- `aug16-oct09-audit-v1.json`
- `cost-profile-aug16-oct9-v1.json`

Historical M5/M15:
- `m5m15-aug16-31-all-v1.json`
- `m5m15-sep15-30-all-v2-auditable.json`
- `m5m15-oct1-9-all-v1.json`
- `m5m15-aug16-oct9-integrity-v1.json`
- `m1m5-vs-m5m15-aug16-31-v1.json`
- `m1m5-vs-m5m15-sep15-30-v1.json`
- `m1m5-vs-m5m15-oct1-9-v1.json`

The first M5 September exploratory file predates the persisted context
closure field. The `-v2-auditable` rerun, not the earlier file, is the
audited source for that month.

## Architecture, causality and safety
- Uses explicit authorized installed MT5 ALFA research terminal and Python
  bridge; no external feeds are retroactively applied to past timestamps.
- Historical entry quote is from first broker tick at/after a completed
  signal bar; exit is from first broker tick at/after entry +900 seconds,
  within 90 seconds. No quotes means no completed outcome.
- M15 closed context is aligned via `bisect_right` on bar close times, never
  current forming context candle. Frozen context close UTC is audited.
- Both hypotheses are research-only, separately tagged families; all
  order execution, live model promotion and compounding remain disabled.
- Strategy-profit and win-rate claims would require historical tick-level
  SL/TP paths, realistic commission/slippage, contract-spec risk sizing,
  a separated chronological period not tuned to earlier results, and
  sufficient count of independent observations after purging overlaps.
- Existing broker credentials/session are not copied into research artifacts.
- Historical artifacts have file hashes; scripts do not overwrite an
  existing run silently.

## How to reproduce / extend without market reopening
Use dedicated research Python environment from repository root:
`C:\KatarinaDev\brain-runtime\Scripts\python.exe`

```text
python scripts/research/historical_shadow_ticks.py --start YYYY-MM-DD --end YYYY-MM-DD --symbols all --output UNIQUE_FILE.json
python scripts/research/historical_m5_m15_shadow.py --start YYYY-MM-DD --end YYYY-MM-DD --symbols all --output UNIQUE_FILE.json
python scripts/research/historical_cost_profile.py --report AUG.json SEP.json OCT.json --output UNIQUE_PROFILE.json
python scripts/research/audit_historical_m5_m15.py --report AUG_M5.json SEP_M5.json OCT_M5.json --output UNIQUE_AUDIT.json
python scripts/research/compare_historical_timeframes.py --m1-report A.json --m5-report B.json --output UNIQUE_COMPARISON.json
```

**Next research priority:** inspect actual broker spread/commission quality
and historical event/session coverage; identify tradable account types
and contracts where a rational transaction cost budget is possible before
investing more search into indicator combinations. Historical collection
can run anytime, but the next strategy must be evaluated against data not
used to invent or tune its rules.

API references:
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py
