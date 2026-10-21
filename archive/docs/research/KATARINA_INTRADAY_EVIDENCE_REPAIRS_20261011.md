# KATARINA — Intraday architecture repair and evidence review

Research date: **2026-10-11**. This report is **not** an authorization for real-money trading. Current user direction: prioritize intraday over forced scalping, single entries with mandatory initial stop-loss, separate market-specific playbooks, measured costs, Adaptive Risk Governor with smaller risk fractions as capital grows.

## Evidence hierarchy and credible sources

1. **Gao, Han, Li & Zhou (2018), Journal of Financial Economics — Market Intraday Momentum.**
   - Peer-reviewed publication: https://doi.org/10.1016/j.jfineco.2018.05.009
   - Reports that the first 30 minutes of S&P 500 ETF price action predict the final half-hour under some conditions, with stronger patterns on more volatile/high-volume days.
   - **Relevance:** generates an index-opening-session hypothesis. **Not evidence** that Valetax NAS100/US30 CFDs or a retest strategy will be profitable. Their endpoint is very different (last half-hour rather than our 3-hour exit).
2. **Moskowitz, Ooi & Pedersen (2012), Journal of Financial Economics — Time Series Momentum.**
   - https://doi.org/10.1016/j.jfineco.2011.11.003
   - Documents price momentum over **1–12 months** in liquid futures across classes. **Not proof of a 5-minute strategy**, but motivation to ask whether regimes and instruments must be modeled separately.
3. **Bailey & López de Prado (2014), Journal of Portfolio Management — The Deflated Sharpe Ratio.**
   - https://doi.org/10.3905/jpm.2014.40.5.094
   - Multiple experiments and choosing winners inflate historical profitability estimates. We tested thousands of configurations; **the 2026 sample has repeatedly been inspected and is not independent OOS**.
4. **MetaQuotes, MT5 Strategy Testing / Testing Features / Tick Generation.**
   - https://www.metatrader5.com/en/terminal/help/algotrading/testing
   - https://www.mql5.com/en/docs/runtime/testing
   - https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation
   - True tick tests use broker tick Bid/Ask history and modeled fills; in MT5 Strategy Tester even real-tick mode can substitute generated ticks when stored tick/bar history diverges. Our custom tick replay is **not** an MT5 Strategy Tester confirmed trade or exchange transaction report.
5. **MetaQuotes, OrderCalcProfit.**
   - https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py
   - Broker-native account-currency result matters for cent balance and minimum volume: contract units, quoted tick money and costs must be verified before sizing $100.
6. **CFTC investor advisory: OTC forex costs, leverage, counterparties and historical win-rate limitations.**
   - https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html
   - Risk warnings; do not assume increased trade frequency or leverage creates profitability.

## Repairs implemented (research-branch only)

- `src/katarina/engines/multi_symbol_execution.py` now passes a verified `account_currency` into the already-existing `AccountRiskCoordinator.with_adaptive_risk(...)` process; missing/unverified currency results in PAUSE and no reservation.
- Optional `require_correlation_evidence=True` flag now rejects new multi-pair exposure if historical return arrays are missing, too short, unaligned by length, constant, non-finite or otherwise invalid. This remains **opt-in** for code backward compatibility. It does not assert date alignment or verification of fresh return timestamps; those remain required at the data adapter layer.
- The existing Adaptive Risk Governor caps, reserve accounting, and all Stage36/38 real execution safeguards remain unchanged. No order submission functions were used.
- Added three independently distinct hypothesis families:
  - `Gold`: retain XAUUSD opening-range trend breakout with closed H1/H4, H1 ADX20, next M5, fixed SL0.55 H1 ATR, take profit 2R, hold 6 hours. Gold is shadow-only exploratory; source hypothesis needs a fresh untouched holdout.
  - `Index`: fixed UTC approximations for 13:30 and 14:30 opening intervals; 30min range retest after breakout or failed extension; stops 0.8 H1 ATR; TP2R, hold 3h. These fixed anchors are not yet adjusted to US DST. Tests covered NAS100, US30, JPN225 and the latter is only a deliberately negative portability control (US open is not its own native cash open).
  - `Forex`: Asian 00:00–06:00 UTC range sweep rejection or London-session continuation; tests EURUSD, GBPUSD, USDJPY.
- Index/FX historical research assumes observed M5 spreads, next-bar entries, stop-first ambiguity, one tick adverse slip and **0.03R assumed commission**. None had both a solid 2025 development signal and positive reused 2026 diagnostic. Therefore **all index/FX playbooks remain NO_TRADE**. Further research should use DST-adjusted native-market trading sessions and actual broker tick execution if a promising hypothesis arises.

## Empirical results

### Six non-gold instrument families: failed gates
`artifacts/historical-brain/katarina_distinct_index_fx_intraday_2025_2026.json`

- NAS100 UTC13:30 retest 2025 n32 mean +0.210R; 2026 n33 mean +0.080R, **fails minimum 2025 sample size 40**. NAS100 UTC13:30 false break 2025 n39 mean +0.252R then 2026 n59 mean −0.081R.
- Most other NAS100, US30, JPN225, EURUSD, GBPUSD, USDJPY index-open or session-range variants have negative 2025 and/or 2026 means.
- No new 2025-qualified multi-year method. Zero profit added to the owner’s existing XAU gold projection.

### XAUUSD three-way exit testing, same 49+50 events, broker tick path
`artifacts/historical-brain/katarina_xau_exit_three_way_tick_2025_2026.json`

| Exit | 2025 mean R | 2026 mean R | Remark |
|---|---:|---:|---|
| Fixed full TP2R / SL−1R | +0.41504 | +0.26588 | **Best average R in both years** |
| BE+0.1R floor; trail gap0.8R after +1R; TP3R | +0.32715 | +0.23027 | 2026 excluding top five trades sum becomes **negative** |
| Take half at +1R, trail remainder after +1.5R; TP3R | +0.32669 | +0.24987 | More complex, lower mean R |

Costs: BASE = historical Bid/Ask path + one adverse tick each way + assumed flat 0.03R fee; STRESS = 3 adverse ticks each way + 0.05R fee. Same event list; no real MT5 deal confirmation. **Conservative decision: freeze Fixed SL/TP 2R as the current exploratory gold benchmark.** Do not adopt partial/trailing just to add sophistication; doing so worsens the historical mean R.

## Limitations

- All results suffer from **multiple testing/selection bias** and reuse of inspected 2026 observations. Positive historical figures are not a fresh out-of-sample guarantee.
- Historical M5 and tick datasets may be uneven across markets and dates. No aggregate PnL claim can be drawn for the multi-pair portfolio.
- Gold signal source still ignores major-news blackout; distinguish event volatility from indiscriminate overnight / release exposure.
- Trading/account costs (actual commissions, swaps, full spread time series for cent, rejection, margin and realized latency) not independently verified.
- With $1,000 starting capital, last model projected about **$169.56** across 21.3 months on standard Valetax, too little to cover meaningful VPS/AI bills. The model still is not proven profitable.
- Native market sessions and daylight savings must be correctly mapped via an IANA timezone database prior to live-stage research.
- For all new strategies, require **single initial hard SL**; no martingale, no averaging down, no forced daily signal. Risk Governor remains the principal sizing authority.
- In any future version, genuine new held-out data and/or shadow-run records with realized costs need to survive a predeclared cost and drawdown threshold before promotion; a recent 2026 simulation is not a clean independent OOS.

## Files / reproducibility

- `scripts/research/independent_index_fx_intraday_2025.py`
- `scripts/research/xau_exit_three_way_tick_2025.py`
- `src/katarina/engines/multi_symbol_execution.py`
- `tests/unit/engines/test_multi_symbol_execution.py`
- Artifacts listed above under `C:\KatarinaDev\artifacts\historical-brain\`.

No live trading enabled. Research scripts were executed using only historical data read interfaces.
