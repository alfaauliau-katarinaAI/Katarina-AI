# KATARINA AI — Intraday-first method screening and adaptive account projection
Date: October 11, 2026. **Research, not live trading.**

## Tested methods
- Seven Valetax symbols: XAUUSD, NAS100, US30, JPN225, EURUSD, GBPUSD, USDJPY.
- 2,800 configuration cells = 400 per symbol across three playbooks (opening-range trend breakout, failed break, aligned pullback), two UTC session anchors, ADX, Fibonacci, M5 relative quote tick volume, D1 confirmation, candle body strength, two H1 ATR stop multipliers, TP:SL ratios 2/3, and 3h/6h holds.
- 2025 development screen and 2026 chronological diagnostics. **The 2026 data have been inspected in many previous research runs and are not an independent pristine holdout.** All methods contain many shared event timestamps; selection bias is severe.
- Main M5 exploratory gate: >=40 entries, >=7 months and >=25 active weeks in 2025, expected R>=0.12, PF>=1.25 and positive PnL excluding five best results. XAU 18 combinations passed 2025 and six were positive in the stricter 2026 exploratory gate. US30 had one 2025 pass but failed 2026. Others none. This is NOT proof of net future profit.

## Selected provisional candidate
XAUUSD.vx ONLY, opening range 06:00–07:00 UTC (13:00–14:00 WIB), seek first aligned H1/H4 confirmed M5 close breakout between 07:00 and 09:00 UTC, H1 ADX>=20, enter at next M5 opening tick, stop = 0.55 x ATR14 H1, target = +2R, max holding 6h. Long and short based on closed H1/H4 trend.

- 2025 real Bid/Ask tick path: 49 modeled trades, mean +0.41504R, PF 1.8105, 17/29 positive active weeks, blocked-week bootstrap 95% mean interval +0.0109 to +0.8513R.
- 2026 through Oct9: 50 modeled trades, mean +0.26588R, PF 1.4672, 16/29 positive active weeks, 95% week-block bootstrap -0.1591 to +0.6937R (contains zero).
- Assumed one adverse tick per side and commission 0.03R; 3 ticks per side with 0.05R fee reduces net mean R to +0.39168 in 2025 and +0.24445 in 2026.
- ADX20 plus Fibonacci 61.8% zone looked stronger in 2025 (+0.51425R) but worsened in 2026 (+0.15665R) and excluding top five in 2026 becomes negative. Therefore **do not make Fibonacci mandatory**.
- Quote tick-volume >=1.2x prior median reduces samples to 28 in 2025 and 26 in 2026. It is too thin to justify a hard filter.
- A September 2026 MT5 historical check showed real_volume=0 for XAU and NAS100; only quote tick volume is available. This is not exchange traded volume, order-book depth, or true institutional footprint.
- RR3 has higher mean R in 2026 but less stable distribution and larger risk in earlier screens. RR2 chosen provisionally as the conservative investigation candidate.

## Adaptive Risk Governor capital projection
Starts Jan 2025, ends Oct9 2026 (partial October). Runs exactly the same 99 frozen candidate events (49+50); position sizing enforces *actual opt-in adaptive governor*, minimum lot, active capital and observed closed-equity high-water mark. 30% reserve triggers only at a balance doubling milestone; no simulated account doubled. Drawdown is closed-balance peak-to-valley and excludes floating and margin events. Broker fills and fees not confirmed; 2026 reuse selection-biased.

| Initial USD | Account assumptions | Executed / 99 | Total simulated USD profit | Ending equivalent USD | Closed-balance max DD |
|---|---|---:|---:|---:|---:|
| $100 | Valetax standard 100 oz/lot, min 0.01 | 0 | $0.00 | $100.00 | 0% |
| $100 | hypothetical cent, 1 oz/lot, min 0.01, USC units | 99 | +$76.55 | $176.55 | 10.00% |
| $1,000 | Valetax standard 100 oz/lot, min 0.01 | 79 | +$169.56 | $1,169.56 | 5.64% |
| $10,000 | Valetax standard 100 oz/lot, min 0.01 | 99 | +$2,380.99 | $12,380.99 | 3.73% |

Quote costs for hypothetical CENT scenario were **copied from Valetax STANDARD tick path, not observed from a cent broker**. The $100 cent profit projection is *not* a verified achievable broker result. Risk starts 2% at $100, 1.25% at $1k, 0.75% at $10k and decreases smoothly as equity grows. Hard Risk Governor limits unchanged. Three-tick extra adverse slip and 0.05R fee: $100 cent +$64.88, $1k standard +$151.05, $10k standard +$2,121.37.

**Cent extra-cost stress:** Add 0.1R per filled trade -> $100 cent +$39.40, add 0.2R -> +$3.36, add 0.3R -> **-$7.96**, add 0.4R -> -$13.22. This illustrates that the small-account model is extremely cost-sensitive.

For all accounts, expect negative calendar weeks, no-trade weeks and negative months. The primary strategy signals are sparse and do not meet the owner's target of profit every day or at least every week. Real calendar-week positivity is not established. The multi-pair scanner cannot assume six failing pair models are profitable; all other markets and scalping contribute ZERO in the projection.

## Exact research files
- scripts/research/intraday_tool_method_matrix_2025.py
- scripts/research/xau_intraday_method_tick_ablation_2025.py
- scripts/research/simulate_three_capitals_adaptive_2025.py
- scripts/research/stress_cent_proxy_cost_2025.py
- scripts/research/audit_intraday_method_three_capitals_2025.py
- artifacts/historical-brain/katarina_intraday_tool_matrix_2025_2026.json
- artifacts/historical-brain/katarina_xau_method_tick_ablation_2025_2026.json
- artifacts/historical-brain/katarina_intraday_three_capitals_adaptive_2025_2026.json
- artifacts/historical-brain/katarina_cent_extra_execution_cost_sensitivity_2025_2026.json
- artifacts/historical-brain/katarina_intraday_method_risk_audit_20261011.json

## Research discipline and remaining work
No live orders. The strategy has *not* been promoted. Risk Governor remains the existing config and all Stage36/38 authorization gates stay disarmed.
Next: obtain actual cent broker 2025–2026 Bid/Ask and symbol contract, tick and commission specifications; run real MT5 Strategy Tester with order_calc_profit and margin/swap, then true chronological blind fresh period; independent symbol-specific models, e.g. US indices separate from FX and gold, only if they show positive independent net expectancy. Consider exchange-traded centralized volume only if the data source actually supplies it; do not treat MT5 tick_volume as genuine futures volume. Risk grouping must treat correlated equity indices and EURUSD/GBPUSD as shared macro positions. No forced trading to meet arbitrary daily profit target.
