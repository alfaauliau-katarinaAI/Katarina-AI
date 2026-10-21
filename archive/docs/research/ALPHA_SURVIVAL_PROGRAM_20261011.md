# KATARINA ALPHA SURVIVAL PROGRAM — 11 October 2026

**Status: research protocol, not a demonstrated live trading edge.** The current KATARINA body already labels TREND_UP/DOWN, PULLBACK, BREAKOUT, REVERSAL, SIDEWAYS and VOLATILITY_SHOCK; it does **not** independently prove net expectancy after trading costs in those states.

## Economic hypotheses, not automatic signal permissions

| Observed closed-bar regime | Predeclared playbook | Side | Risk of failure |
| --- | --- | --- | --- |
| TREND_UP/DOWN, PULLBACK_UP/DOWN | Aligned trend pullback | BUY in UP, SELL in DOWN | Choppy trend, fake support/resistance, fees |
| BREAKOUT_UP/DOWN | Break-and-retest / opening-range expansion | Direction of confirmed break | False breaks, slippage at news |
| REVERSAL_UP/DOWN | Closed-bar liquidity sweep and reclaim | Confirmed reclaim direction | Reversal mistaken for retracement |
| SIDEWAYS | Range fade at statistically pre-specified closed range boundaries | BUY/SELL, **separate** models | True breakout or volatility expansion |
| VOLATILITY_SHOCK, TRANSITION, UNKNOWN | OBSERVE / NO TRADE | Neither | Avoid unbounded adverse fill / uncertain regime |

Do not treat volume from MT5 quote ticks as centralized exchange volume. Fibonacci is context, not an independent source of predictive alpha. All claims need bid/ask execution-level fees and scenario-specific contract, margin and currency.

## Freeze and multiple-testing discipline

The file `config/research/alpha_regime_program_v1.json` preregisters **7 markets × 10 regime/side cells = 70 hypotheses** for a future holdout beginning **2026-10-13 UTC** and ending **2027-04-30 UTC**. The dataset must be sourced, hashed, broker/spec-attested and independently verified as not previously used for tuning. Do not tune a strategy against these future outcomes and then call the same data blind. The protocol does not state any historical win rate for these untested cells.

`src/katarina/research/alpha_survival.py` provides a conservative *post-holdout* screen: >=60 resolved trades, >=20 distinct weeks, >=5 distinct months, buffered all-in net R + **0.10R additional adverse cost**, PF>=1.25, positive net excluding top five trades, >=55% positive weeks and <=12R modeled peak-to-trough drawdown. A seeded week-block bootstrap must have lower mean net R >0 using per-cell alpha=0.05/70. These thresholds are **predeclared safety research filters**, not empirically optimized profit-maximizing settings; they may exclude genuinely profitable methods and are not a mathematical guarantee of survival.

All event records need closed chronology, unique IDs, source hash and known-after-exit timestamps; overlapping positions and lookahead data are rejected. Missing independent holdout or fee/contract attestations **block** research qualification even when numbers look good. A passing screen yields `PASS_SHADOW_RESEARCH_ONLY`, never approval for live order routing.

The current `scripts/governance/audit_alpha_regime_program.py` intentionally reports **0 validated alpha** and labels every proposed cell `WAIT_UNVERIFIED_HYPOTHESIS`. It does not create profitable trades or fabricate future data.

## Evidence and relevant academic research

- Moskowitz, Ooi & Pedersen (2012), [Time Series Momentum](https://doi.org/10.1016/j.jfineco.2011.11.003): diversified trend-following evidence at **monthly futures horizon**, not proof of KATARINA intraday performance.
- Lo, Mamaysky & Wang (2000), [Foundations of Technical Analysis](https://doi.org/10.1111/0022-1082.00265): objective pattern recognition and statistical testing.
- Park & Irwin (2007), [What Do We Know About the Profitability of Technical Analysis?](https://doi.org/10.1111/j.1467-6419.2007.00519.x): heterogeneous results with data snooping and cost limitations.
- White (2000), [A Reality Check for Data Snooping](https://doi.org/10.1111/1468-0262.00152): repeated model selection on the same data can generate spurious alpha.
- Harvey, Liu & Zhu (2016), [… and the Cross-Section of Expected Returns](https://www.nber.org/papers/w20592): multiple-testing problem is severe in large factor searches.
- Hurst, Ooi & Pedersen (2017), [A Century of Evidence on Trend-Following Investing](https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing): long-horizon robustness of diversified trends, not a transferable win rate for broker CFDs.

## Operational discipline

1. Research engine remains READ-ONLY. **No forced trades to meet daily payout goals; no martingale, no adding to losers.**
2. Only adapt trade horizon or directional methods after a genuinely new chronological selection period. Do not change thresholds after seeing the holdout.
3. Apply Stage16/17 risk governor and actual broker lot, margin, cent/USD normalization to any separate tester; eliminate correlated overlapping positions.
4. Require Stage35 native Strategy Tester, Stage36 broker preflight, paper/shadow execution with recorded real costs, and Stage38 explicit owner approval before any live-risk discussion.
5. KATARINA operating costs must be funded independently of speculative trading until verified realized results exist.

**Last audited alpha count: 0. Profitability cannot yet be asserted.**
