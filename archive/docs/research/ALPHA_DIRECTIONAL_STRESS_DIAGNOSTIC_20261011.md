# KATARINA — Independent directional stress review (11 October 2026)

> **Research only. No validated tradeable alpha and no live risk authorization.**
> Public report deliberately includes **aggregate results only**; raw broker tick files, outcomes and proprietary event details remain on the private Windows research host.

## Why this review was run

Past 2,800 screening configurations over seven instruments and selected XAU intraday research were positive in places but overfit risk is material. The 2026 observations are **already inspected**, not clean out-of-sample evidence. We have now re-aggregated the frozen existing XAU candidate **by BUY and SELL separately**, without searching new thresholds or fitting a new rule to 2026 returns. The source is the previously generated private, broker Bid/Ask tick-path approximation; actual achieved broker fills, cent contracts and fees are not independently verified.

## Directional diagnostic (net R under 3-tick stress assumptions)

| Historical period | Side | Trades | Mean R | Profit factor | Net R excluding 5 best trades | Weekly block-bootstrap 95% mean-R interval |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 2025 development | BUY | 34 | +0.2606 | 1.462 | -0.869 | [-0.1894, +0.8028] |
| 2025 development | SELL | 15 | +0.6887 | 2.604 | +0.596 | [+0.0615, +1.3014] |
| 2025 development | combined | 49 | +0.3917 | 1.748 | +9.456 | [-0.0128, +0.8316] |
| 2026 reused diagnostic through 9 Oct | BUY | 23 | +0.4722 | 1.993 | +1.119 | [-0.0670, +1.0336] |
| 2026 reused diagnostic through 9 Oct | SELL | 27 | +0.0504 | 1.075 | -8.382 | [-0.5018, +0.5978] |
| 2026 reused diagnostic through 9 Oct | combined | 50 | +0.2444 | 1.421 | +2.477 | [-0.1838, +0.6914] |

Intervals are *descriptive week-block resampling*, unadjusted for the many historical hypotheses and therefore not formal proof of edge. All combined and 2026 side-specific intervals include zero. The 2025 SELL cell has only 15 trades and **cannot qualify** as robust independent evidence despite its seemingly strong mean.

## Incremental execution-cost stress on 2026 already-stressed results

| Further cost per trade | BUY (23) mean R | SELL (27) mean R | Combined (50) mean R |
| --- | ---: | ---: | ---: |
| None | +0.4722 | +0.0504 | +0.2444 |
| +0.10R | +0.3722 | **-0.0496** | +0.1444 |
| +0.20R | +0.2722 | **-0.1496** | +0.0444 |
| +0.30R | +0.1722 | **-0.2496** | **-0.0556** |

Removing the top five model trades after another +0.10R cost makes even the 2026 BUY diagnostic **negative by -0.681R aggregate**, despite its positive average. This indicates fragility and underlines the need for independent costs and more completed events. Cost buffers are stylized, not certified spread/slippage predictions.

## Other asset-family hypotheses (independent method family, reused years)

- **NAS100**: a failed-open-break variation had 2025 mean +0.2516R (39 entries) but 2026 -0.0809R (59), and top-five-excluded 2025 total was already slightly negative. A separate open-retest variation showed 2026 +0.0801R (33) but top-five-excluded total -7.200R. Neither qualifies.
- **US30 / JPN225**: examined variants mostly negative or break-even across 2025/2026, with top-five-excluded results negative.
- **EURUSD / GBPUSD**: tested sweep and continuation variants had negative mean R in both periods.
- **USDJPY**: 2025 London continuation +0.061R (46) changed to 2026 -0.2559R (50). Other tested variant negative. **No validated forex alpha**.

These are results only for the specified research candidates. They do **not** rule out every possible profitable method in each instrument. No multi-asset risk allocation or aggregated monthly income is inferred from these separate and overlapping family studies.

## Practical decision for KATARINA

1. **Prioritize researching XAU BUY** because its newer *retrospective* pattern is comparatively favorable, while **do not upgrade it to a tradable strategy**. It has 23 trades in 2026, 16 active weeks, negative cost-stressed top-five-excluded outcome and wide uncertainty.
2. **Reject/park this specific XAU SELL configuration** for shadow-trading qualification: 2026 mean R is erased by +0.10R cost and top-five-excluded total is already negative; do not infer all SELL strategies are unprofitable.
3. Retain **NO TRADE** for the *specific failing* NAS/US30/JPN225/FX methods. Investigate new *predeclared*, distinct methods only on genuinely future data.
4. Require a verified hard initial stop, native broker specs/currency, Bid/Ask timestamps, slippage and commission, actual volume min/step and margin, alongside correlated open exposure and drawdown gates.
5. Freeze the current decision rules before forward collection; do not repeatedly reoptimize on the same 2026 sample or force daily profits.
6. Stage35 native tick Strategy Tester, Stage36 read-only broker verification and Stage38 owner authorization remain **pending**. This report **does not enable live execution**.

## Provenance and reproducibility boundary

Private input: `katarina_xau_method_tick_ablation_2025_2026.json` (source SHA256 `0655e03af231f3250ce076cb15b1a77f96586e657f8304402187d8d1eb6dc29a`, as previously listed in the repository's retrospective report).

Private output: `katarina_alpha_directional_diagnostic_20261011.json`, SHA256 `d5d02fe8ad54125f3fcb430574f91f5cb4381a85daf165e2e4cb81f4972a9952`.

The source data and analysis script remain on the private Windows research host under `C:\KatarinaDev`. The report was generated offline; no account mutation or broker trade submission. These hashes provide reproducibility references but not a guarantee of provenance authenticity.

## External methodological references

- [Moskowitz, Ooi & Pedersen (2012), Time Series Momentum](https://doi.org/10.1016/j.jfineco.2011.11.003) finds longer-horizon futures momentum; **not** automatic evidence of intraday CFD edge.
- [Bailey & López de Prado (2014), Deflated Sharpe Ratio](https://doi.org/10.3905/jpm.2014.40.5.094) addresses strategy selection bias and performance inflation after many searches.
- [Coakley, Marzano & Nankervis (2016), How profitable are FX technical trading rules?](https://doi.org/10.1016/j.irfa.2016.03.010) finds significantly fewer rules robust to data-snooping adjustments.
- [Zarrabi, Snaith & Coakley (2017), FX technical trading rules can be profitable sometimes!](https://doi.org/10.1016/j.irfa.2016.12.010) documents transient rule profitability after transaction costs and data-snooping controls.

**Research outcome: no verified independent net alpha; prioritize independent directional BUY XAU testing, retain abstention for weak cells.**
