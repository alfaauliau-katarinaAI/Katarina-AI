# KATARINA AI — Adaptive Brain V2 Research and Implementation
Date: 2026-10-11 | Mode: offline research/shadow, NO_TRADE preserved

## Project identity (non-negotiable)
- Python remains the brain; MT5 sensors and deterministic execution.
- Regime labels and suggestions NEVER place broker orders or promote a live model.
- Existing risk governor, capital compounding and Stage 01–09 are UNCHANGED.
- Broker session, freshness, spread and high-impact news guard remain in force.
- Old indicator families remain for rollback, but new scalper route DOES NOT require simultaneous RSI, BB, ADX, EMA50, VWAP and orderflow evidence.
- No claim of demonstrated net-profit predictability from a descriptive regime label.

## New source and test modules
- src/katarina/intelligence/adaptive_regime.py — MTF causal closed-frame regime observer
- src/katarina/intelligence/closed_swing_structure.py — causal closed OHLC break/reclaim/wick extractor
- src/katarina/intelligence/adaptive_brain_v2.py — end-to-end research-only observable pipeline, NOT wired to live orders
- src/katarina/engines/adaptive_scalper.py — light closed-candle price-action plan mapping
- src/katarina/intelligence/causal_seasonality.py — per-symbol hour/day prior-only context
- scripts/research/audit_adaptive_regime_v2.py — replay archived observations
- tests/unit/intelligence/test_adaptive_regime_v2.py — 11 baseline unit and integration checks
- tests/fixtures/stage35/mock_terminal.ps1 — PowerShell 4 subprocess exit-code propagation fix (test fixture only; real risk code unchanged)

## Regime -> scalping playbook
| State | Playbook | Minimum positive evidence |
|---|---|---|
| TREND_UP / TREND_DOWN | TREND_PULLBACK | H1/M15 trend with closed bar bounce or continuation |
| PULLBACK_UP / PULLBACK_DOWN | TREND_PULLBACK | Trend H1/M15; opposing M5 leg and closed candle resume |
| SIDEWAYS | RANGE_FADE | Weak directional efficiency and price at range edge with rejection |
| BREAKOUT_UP / BREAKOUT_DOWN | BREAKOUT_RETEST | Confirmed closed swing break and volatility expansion |
| REVERSAL_UP / REVERSAL_DOWN | REVERSAL_RECLAIM | Verified swing reclaim and rejection (not just opposing M5) |
| VOLATILITY_SHOCK / TRANSITION / UNKNOWN | OBSERVE | No unsupported regime-to-entry promotion |

Evidence_strength is a descriptive score, NOT probability of winning.

## Point-in-time seasonality, news and risk context
- Estimate UTC hour and weekday association only on completed past labels, separately per instrument. Sparse hours are shrunk toward instrument prior. Never transfer NAS100 results to XAUUSD.
- Use published-at timestamps for BLS/CPI/central bank news; do not inject revised historical values into earlier decisions. ALFRED vintage data make revisions explicit.
- Implement exchange/broker timezone and daylight savings before interpreting exchange-specific hours. A generic UTC hour is not proof of session opportunity.
- Macro data and VIX give volatility/liquidity/market context, not universal BUY/SELL direction.
- Keep broker Bid/Ask spread, transaction commissions, adverse slippage and trading hours in tick-based execution research.
- Existing Stage 38 authorization remains fail-closed; it presently requires owner approval and demo/stress/broker compatibility/reconciliation/monitoring proof. Do not falsely mark these conditions as passed.
- Owner preference: do not add a prolonged demo forward-testing phase to the research roadmap. This does not override Stage 38 gate before any real-money orders.

## Trusted references reviewed
1. Hamilton 1989, latent Markov regime framework: https://citeseerx.ist.psu.edu/document?doi=de6046f58a05a769b5aa526d95a09c5fa5e5b42c&repid=rep1&type=pdf
2. Engle 1982, volatility clustering: https://doi.org/10.2307/1912773
3. Bailey et al 2015, backtest overfitting: https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253
4. Scikit-learn time series split and gap: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
5. MetaQuotes Strategy Tester real ticks: https://www.metatrader5.com/en/terminal/help/algotrading/testing
6. MetaQuotes real tick Bid/Ask mechanics: https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation
7. MetaQuotes tick gap and tester details: https://www.mql5.com/en/docs/runtime/testing
8. BIS 2025 global FX survey: https://www.bis.org/publications/triennial-central-bank-survey-foreign-exchange-and-over-the-counter-otc-derivatives-markets-2025
9. Intraday FX activity seasonality paper: https://www.sciencedirect.com/science/article/pii/S0889158306000463
10. FRED and ALFRED real-time vintages: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html
11. Economic series vintage dates: https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html
12. BLS official employment release calendar: https://www.bls.gov/schedule/news_release/empsit.htm
13. Federal Reserve FOMC calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
14. Cboe VIX definition and limitations: https://www.cboe.com/insights/posts/what-the-vix-and-vix-1-d-indices-attempt-to-measure-and-how-they-differ/
15. Fidelity ADX trend strength vs direction: https://www.fidelity.com/viewpoints/active-investor/average-directional-index-adx

Reference use is methodological: nothing here proves a strategy's real brokerage profitability.

## Methodology and required further evidence
- Replay existing archived closed M5/M15/H1 indicators, with no OHLC structural evidence invented. Incomplete historic frames remain UNKNOWN.
- Seasonality training on September known-label outcomes, October retrospective evaluation; historical October already inspected in earlier work, NOT independent untouched data.
- Compare historical regime coverage vs old 65.8% TRANSITION and assess direction separately. A higher classified fraction does not imply predictive accuracy.
- Complete causal actual closed OHLC swing/reclaim detection for reversal/breakout, real-tick net R research by symbol/playbook, independent later chronological holdout, and source provenance for macro events.
- Keep risk governor settings untouched. Do not link new engine to live order execution until net-cost performance and Stage 36/38 evidence are satisfactory.
