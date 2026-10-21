# KATARINA — Scalping vs Intraday, Multi-pair Survival Research
Date: 2026-10-11 | Workspace: local research branch | LIVE: NO

## Decision
**Prefer evidence-based, selectively traded intraday opportunities (M5 trigger + H1/H4 context), with opportunistic scalping only if broker cost and per-symbol model validation pass.**
A daily/weekly profit guarantee is neither statistically defensible nor possible to enforce by increasing order frequency. No trading on an uncertain day is a valid controlled decision.

## Verified development experiments in this session
1. Independent event-based hypotheses (2025 development; previously inspected 2026 diagnostic) on 7 symbols, 36 configurations per symbol = **252 research configurations**: H1/H4-aligned opening-range break, failed opening-range sweep, and pullback resume. Two fixed UTC session anchors (06 and 12), TP:SL 1.25/2/3, and holds 3/6 hours. Real historical M5 Bid-based candle with broker bar spread, assumed 1 tick slippage each way and hypothetical 0.03R fee. Full broker order/fill/fee simulator **not performed**.
2. Only **XAUUSD 06:00 UTC opening-range trend breakout** passed the 2025 research gate. 6 variants (RR 1.25/2/3, holds 3/6h) met 2025 gate, and displayed positive mean R in the reused 2026 comparison. Other six instruments: none met the same 2025 gate. These six variants share almost identical 65/64 signal timestamps; **not independent edge confirmations**.
3. Candidate OR_TREND_BREAK baseline **M5 OHLC approximation**, risk=0.55×H1 ATR, 06–07 UTC range; entry on H1/H4 aligned close breakout in 07–09 UTC:
   - RR 1:2, hold 6h: 2025 65 trades, mean **+0.31585R**, PF 1.585, weekly positive 21/37 active weeks; 2026 64 trades, **+0.17497R**, PF 1.291, weekly positive **17/34 active weeks**. 2025 bootstrap weekly 95% CI on mean **[-0.040,+0.706]R**, 2026 **[-0.213,+0.564]R**.
   - RR 1:3, hold 6h: 2025 65 trades, **+0.37591R**, PF 1.607, positive 19/37 active weeks; 2026 64 trades, **+0.24438R**, PF 1.392, positive 16/34 active weeks. Bootstrap CI 2026 **[-0.174,+0.685]R**. **Both include negative lower bounds**, so statistical edge not established.
4. Exact historical broker **Bid/Ask real-tick price-path replay**, with assumed fills, one tick of adverse slippage on both sides and 0.03R assumed fees:
   - RR 1:2, 2025 65 trades, **+0.30944R** / PF **1.567**; 2026 64 trades, **+0.16798R** / PF **1.277**. Weekly-block 95% mean R CI 2025 **[-0.048,+0.703]**, 2026 **[-0.222,+0.561]**.
   - RR 1:3, 2025 +0.36881R/PF1.589; 2026 +0.23705R/PF1.376. Weekly-block CIs still overlap zero.
   - Stress 3 adverse ticks per side and assumed 0.05R fees: RR 1:2 results 2025 +0.28551R, 2026 +0.14609R; RR 1:3 results 2025 +0.34509R, 2026 +0.21497R. These are modeled fills, not actual broker deal records.
   - 129 signals, 516 simulated tick outcome calculations. No tick fetch errors in this local replay.
   - **Real tick path replay is NOT the full MT5 Strategy Tester**, no model of broker rejection, funding, swap or queue.
5. Limited placebo comparing otherwise identical directional entry delayed by 30 minutes:
   - RR 1:2 2025 early +0.31585R vs delayed -0.15486R; 2026 early +0.17497R vs delayed +0.10755R. Early timing advantage fell dramatically from +0.4707R (2025) to +0.0674R (2026). Delayed-entry is not a randomized matched market-time control and should not be over-interpreted.
6. Pair return correlation (UTC daily log-returns, overlapping trading days): EURUSD–GBPUSD **+0.8202** (352 days), NAS100–JPN225 **+0.7256** (365 days), NAS100–US30 **+0.6733** (365 days). These are raw returns, not signal PnL, and do not imply fixed relationships through crises. A multi-pair brain should count aligned exposure as a **shared directional bet**, not 3 diversified investments. No change to current Risk Governor.

## Scientific assessment
**What we learned:** There is one intriguing *research-only* intraday direction that survived two historically reused years and a real-tick price-path check, unlike prior scalping systems that suffered persistent negative R across 7 symbols and 7,392 parameter combinations. This is an exploratory association, not proven repeatable net profitability, because the week-block CIs contain zero, sample sizes are small, actual broker costs are unverified, and 2026 has been examined before.

**What this implies for user's profit-per-day/week goal:** At most 1–2 setups per week on this single candidate, and only 17/34 positive **active** weeks in 2026 with RR2 6h. Weeks with no trades are not profitable weeks. Opening more unprofitable pairs to meet arbitrary frequency would damage expected returns.

## Next development focus
- Retain KATARINA identity: autonomous observation across all permitted pairs, classify regime and trade only when a verified per-symbol setup appears; NO_TRADE otherwise.
- Different playbooks for different symbols, not a universal EMA/RSI stack: opening-range trend break; liquidity sweep then reclaim; distinct session-conditioned mean reversion only after independent validation.
- Decouple **session-specific opportunity quality** from trade trigger, and **prediction probability** from risk sizing. M15/M5 entry, H1/H4 regime, D1 macro context. M1 for precise execution when spread/ATR cost supports it.
- Use rolling symbol-specific bid/ask costs, news timestamps and seasonal event effects, and adjust session windows for daylight-savings and exchange holidays. Crucially train on one window without referencing subsequent test labels, then hold out *new* dates never previously analyzed.
- Evaluate weekly profit share (including no-trade weeks), lower bound of week-block net expectancy, worst losing streak, slippage jumps, drawdown and correlated simultaneous portfolio exposure. Test Portfolio annualized/account PnL ONLY after actual deal economics and risk settings are properly simulated; do not equate R trade sums to account profits.
- No forced daily/weekly monetary target. Risk Governor exactly as current, no config changes, and existing live gates remain fail-closed. Model is **not** promoted.

## VPS evidence paths
- `C:\KatarinaDev\artifacts\historical-brain\katarina_intraday_session_2025_2026.json`
- `C:\KatarinaDev\artifacts\historical-brain\xau_intraday_session_robustness_2025_2026.json`
- `C:\KatarinaDev\artifacts\historical-brain\xau_intraday_real_tick_path_2025_2026.json`
- `C:\KatarinaDev\artifacts\historical-brain\multi_pair_daily_correlations_2025_2026.json`
- Scripts: `scripts/research/intraday_session_2025.py`, `audit_xau_intraday_robustness_2025.py`, `xau_intraday_real_tick_path_2025.py`, `audit_pair_correlations_2025.py`.
- All four scripts are **read-only** broker research with no order sending.

## Academic and official references
- Gao, Han, Li, Zhou (2018), *Market Intraday Momentum*, Journal of Financial Economics: https://www.sciencedirect.com/science/article/pii/S0304405X18301351 . Findings concern ETFs, not a broker CFD guarantee.
- Moskowitz, Ooi, Pedersen (2012), *Time Series Momentum*, Journal of Financial Economics: https://doi.org/10.1016/j.jfineco.2011.11.003 . Multi-month persistence is not proof of a 5-minute signal.
- BIS December 2025 Quarterly Review on FX spreads/liquidity: https://www.bis.org/publ/qtrpdf/r_qt2512.pdf .
- Bailey/Lopez de Prado (2014), *The Deflated Sharpe Ratio*: https://doi.org/10.3905/jpm.2014.40.5.094 . Selection over many trials is a serious false-discovery risk.
- CFTC customer advisory on forex retail losses/fees: https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html .
- MetaQuotes MT5 copy_ticks_range API: https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py .
- MetaQuotes Strategy Tester real tick mode: https://www.metatrader5.com/en/terminal/help/algotrading/testing .
