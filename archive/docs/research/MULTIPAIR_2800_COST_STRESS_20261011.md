# KATARINA — Seven-market 2,800-cell retrospective cost stress (11 October 2026)

**Research-only retrospective diagnostic; no independently proven alpha; no real orders.** Aggregates were recomputed on the authorized Windows research workstation from the private historical file `katarina_intraday_tool_matrix_2025_2026.json` (seven symbols, 400 previously modeled configurations each). The original 2026 observations were **already examined repeatedly**; this is not a virgin holdout. The source and executable analysis remain in private `C:\KatarinaDev`, outside public GitHub.

## Repeated stress test of the complete matrix

| Further fixed adverse cost per modeled trade | Configurations passing *both* historical periods | Symbol coverage |
| ---: | ---: | --- |
| +0.00R | 4 / 2,800 | XAUUSD only |
| +0.05R | 2 / 2,800 | XAUUSD only |
| **+0.10R** | **0 / 2,800** | None |
| +0.15R | 0 / 2,800 | None |
| +0.20R | 0 / 2,800 | None |
| +0.30R | 0 / 2,800 | None |

This **new post-hoc stress screen** requires, for *each* of 2025 and the reused 2026 diagnostics: >=40 modeled trades, >=25 active ISO weeks, >=7 months, sample mean R **after** incremental adverse-cost buffer >=0.05, original-model profit factor >=1.25, original-model 5-largest-trades-excluded sum **less extra cost × (N−5)** still positive, modeled max drawdown <=12R and >=50% positive active weeks. **The profit factor is not recomputed for each extra-cost scenario**, so the criterion is lenient: the number of passing variants could be lower under true recomputation. Drawdown is also not recalculated and actual achievable broker execution is unverified. This screen is *not* a valid statistical multiple-testing adjustment or an estimator of unseen returns. The very large and correlated model search requires a more conservative blind test.

Importantly, some models that fail these thresholds could still be investable; the results reject this **tested configuration set under these particular assumptions**, not every possible market strategy or instrument. No optimistic extrapolation from 2,800 tried rules is permitted.

## Source integrity and confidentiality

- Historical private source: `katarina_intraday_tool_matrix_2025_2026.json`; previously attested SHA256 `7d0e6db9aeefa79e5245ca97e25943a3c6d06283aa799a6be6295e3ec242e4cc`.
- Private generated audit: `katarina_multi_pair_2800_cost_audit_20261011.json`; SHA256 `541dfc933a2bb6ba01043aae1b811301935e4a505cd844d3c2a567066759a54f`.
- Only aggregates are published. The raw events, tick data and proprietary execution parameters are not included here.
- Live orders disabled; validated live alpha count remains **zero**.

## Recommended next research trials

1. Keep **XAUUSD BUY** as a *hypothesis* pending truly new forward observation; park the cost-fragile XAU SELL configuration. All current results are historical and selected/inspected.
2. Investigate **different economic mechanisms** rather than another fine grid of the same breakout parameters: e.g. separate FX London continuation, range-to-trend regime transition, and indices *exchange-session/DST-corrected* breakout. Treat these as preregistered research families, not profitable rules.
3. Pre-register instrument-specific hypotheses and reserve a never-inspected chronological test set. Do not publish periodic performance from the sealed blind window or use it to tune.
4. Use actual broker Bid/Ask, commission, margin/contract, swaps and slippage evidence; stress more than one fixed cost level. Include separate BUY/SELL, loss sequences, monthly/weekly consistency and correlated portfolio drawdown.
5. Stage35 MT5 native Strategy Tester, Stage36 broker specifications and paper/shadow logs remain requirements. No Risk Governor change and no capital deployment based on these 2,800 cells.

## Methodological context

- [Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*](https://doi.org/10.1016/j.jfineco.2011.11.003): evidence applies to **monthly futures** momentum, not automatically intraday CFD strategy performance.
- [Bailey et al., *The Probability of Backtest Overfitting*](https://escholarship.org/uc/item/4w1110bb): repeated selection can create impressive but unstable in-sample results.
- [Harvey, Liu & Zhu (2016), *… and the Cross-Section of Expected Returns*](https://doi.org/10.1093/rfs/hhv059): accounting for many hypotheses demands higher confidence.

**Decision: zero demonstrated independent cost-resilient alpha. Continue only with new, predeclared hypotheses and properly sealed forward evidence; do not force a trade because the system is running.**
