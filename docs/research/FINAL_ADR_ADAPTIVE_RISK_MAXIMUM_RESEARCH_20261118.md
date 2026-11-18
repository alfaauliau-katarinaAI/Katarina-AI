# Katarina AI — Final ADR Adaptive Risk Research
Date: 2026-11-18 | Status: RESEARCH COMPLETE; NOT LIVE APPROVED.

## Method
Causal ADR20 uses the average High-Low of the prior 20 FULL broker H1-derived trading days; no current-day range.
For absolute regime scale, compare ADR20 to an EXPANDING historical median ADR20 from days strictly before this day's evaluation.
ADR multiplier: ratio <0.90 -> 0.75x risk; 0.90 <= ratio <1.30 -> 1.0x; ratio >=1.30 -> 1.25x.
ADR is computed per symbol. Days with <12 H1 bars are excluded. Broker session timezone is not independently confirmed.
P9 Adaptive V3.1 + XAU SELL (NAS BUY disabled), 8 engines, 2 open-symbol-family slots, no hedging.
Starting synthetic capital USD10000; tests Aug2024-Oct2026 27 complete spread-available months; Nov2026 partial.
Risk%, compounding, lot floor/step, broker current snapshot margin75% budget, drawdown closed balance guard 4% halve risk / 8% block.
NAS profit per 0.1 index tick 1 lot is $1 by MT5 OrderCalcProfit, despite incorrect reported tick-value $0.10.

## ADR levels per symbol (median daily ADR20)
|Symbol|Aug-Dec2024|2025|Jan-Oct2026|
|---|---:|---:|---:|
|XAUUSD.vx|35.414|50.929|103.36|
|NAS100.vx|323.1|382.79|497.52|
|EURJPY.vx|1.7007|1.1959|1.128|
|USDCHF.vx|0.0064|0.00608|0.00548|

XAU daily range changed ~2.9x, NAS~1.54x in the median ADR20; this does NOT prove ADR causes improved edge.
XAU event-level correlation Spearman ADR20/ADR100 with raw trade R is only +.04, NAS +.276 on only 26 event samples.

## Search
21 risk multiplier policies x325 base allocation vectors = 6825 configurations. 383 provisionally passed normal and -0.6R; 276 also passed -0.4R/-0.5R 8% closed DD and veto tests, normal DD <=6%, and concentration rules.
2024-25 training and 2026 data have already been examined in earlier searches; these are retrospective mined results, NOT a valid untouched OOS test.

## Selected maximum historical growth UNDER these finite cost/DD constraints
|Symbol|Base risk %|Low ADR <0.90|Normal ADR 0.90–1.30|High ADR >=1.30|
|---|---:|---:|---:|---:|
|XAUUSD|0.50%|0.375%|0.50%|0.625%|
|NAS100|3.00%|2.25%|3.00%|3.75%|
|EURJPY|0.50%|0.375%|0.50%|0.625%|
|USDCHF|1.00%|0.75%|1.00%|1.25%|

|Metric|Old static max|ADR adaptive winner|Same new base without ADR|
|---|---:|---:|---:|
|27 month profit USD|+33,360.86|+37,532.27|+32,373.21|
|Monthly normal USD|+1,235.59|+1,390.08|+1,199.01|
|Max normal closed DD|5.955%|5.724%|6.551%|
|Closed fills normal|244|244|244|

## Cost resilience (normal / extra R penalty)
|Stress|Old static USD/month|ADR winner USD/month|ADR winner closed DD|ADR winner veto|
|---|---:|---:|---:|---:|
|0.0|+1,235.59|+1,390.08|5.724%|0|
|0.4|+325.47|+369.57|7.047%|0|
|0.5|+191.73|+219.56|7.691%|0|
|0.6|+79.63|+99.02|7.750%|0|
|0.7|-18.07|+2.00|8.151%|142|

At -0.7R, selected model breaches 8% closed DD and vetoes 142 new entries. Small positive aggregate ~$2/month there reflects blocked future entries; NOT a resilient profitable system.
At extra -0.6R, winner USD99.02/month DD7.750% versus old USD79.63 DD7.803%; these are closed balance DD only.

## Annual profit by model
|Period|Old static USD|ADR winner USD|
|---|---:|---:|
|2024|+2,709.23|+3,406.86|
|2025|+14,723.69|+15,442.58|
|2026|+15,927.94|+18,682.83|

2024=Aug–Dec; 2026=Jan–Oct. 27-full-month ending balance winner $47,532.27; 2026-Nov partial -$206.83; as-of latest bar hypothetical $47,325.44.

## Monthly normal simulated net profit
|Month|Old static USD|ADR winner USD|
|---|---:|---:|
|2024-08|+561.61|+892.16|
|2024-09|+358.52|+663.23|
|2024-10|-132.04|-75.70|
|2024-11|+613.87|+598.76|
|2024-12|+1,307.29|+1,328.42|
|2025-01|+1,683.41|+2,073.50|
|2025-02|+1,124.43|+1,196.58|
|2025-03|+1,022.69|+599.12|
|2025-04|+1,455.34|+1,640.50|
|2025-05|+1,637.18|+1,660.12|
|2025-06|+387.02|+845.11|
|2025-07|+750.22|+496.98|
|2025-08|+1,951.61|+1,620.76|
|2025-09|+91.14|+53.01|
|2025-10|+876.27|+907.57|
|2025-11|+1,807.43|+2,106.00|
|2025-12|+1,936.96|+2,243.33|
|2026-01|+2,833.50|+2,886.66|
|2026-02|+1,907.30|+2,591.77|
|2026-03|+2,461.66|+2,942.78|
|2026-04|-1,268.05|-1,140.27|
|2026-05|-559.75|-805.41|
|2026-06|+1,125.09|+1,531.70|
|2026-07|+636.75|+682.08|
|2026-08|+3,849.06|+4,312.22|
|2026-09|+1,950.61|+2,239.43|
|2026-10|+2,991.78|+3,441.87|

## Alternative: highest severe-cost return, also beyond native cap
Base XAU0.5%, NAS3%, EUR0.25%, CHF0.25%; rule: ADR ratio below0.90 ->0.50x, middle1x, above1.30 ->1.50x.
Normal USD+1,209.45/month, stressed -0.4R +427.86, -0.5R +277.93, -0.6R +149.83; severe DD 7.750%.
At -0.7R DD>8% and many vetoes (187), so not robust against still-worse costs.

## How far larger risk failed
NAS4% with XAU0.75% had >8% DD and multiple vetoes under -.5R.
XAU1% NAS6% already exceeded 8% DD and 34 vetoes in normal costs.
XAU2% NAS8% -0.6R fell below zero net/month, DD>8 and 274 vetoes.
NAS10% and NAS12% yielded normal DD >10%, frequent vetoes; ADAPTIVE risk multipliers did not prevent risk damage.
Do not confuse maximum raw return on one scenario with robust optimization or safely executable risk.

## Risk and operational limitations
Native P9 risk approval remains <=0.25% per ENTRY. NAS high ADR of 3.75% is 15x native cap; alternative 4.5% is 18x. These are RESEARCH ONLY; no live approval.
Data source ValetaxIntl-Live2 H1/H4 broker OHLC; Jan-Jun2024 historical spread zero; Jul2024 incomplete; Nov2026 partial.
Not a native MT5 Every tick based on real ticks test. Historical intrabar equity DD, real spread gaps, broker account historic margin, real commission/swap and 2024 FX conversions are not fully validated.
Historical selection repeatedly mines the same 2024-26 data; profit and ADR relations may be overfitted. No causal or live forecast claim.
P9V2/P7 original frozen SHA locks unchanged, 0 broker trades, 0 production or GitHub writes; EvidenceRiskGate WAIT.

## Reproducible VPS output
Directory C:\Katarina\research\p9-v31-adr-risk-optimization-20261118\
CAUSAL_ADR_REGIME_AND_EVENTS.json, P9_V31_ADR_EVENT_REGIME_RECORDS.csv
ADR_RISK_FULL_SEARCH_RESULT.json, ADR_RISK_SECOND_STAGE_HARD_GUARD.json
ADR_RISK_MATCHED_STATIC_AND_BOUNDARY.json, MONTHLY_ADR_OPTIMAL_VS_STATIC.csv
FINAL_ADR_ADAPTIVE_RISK_MAXIMUM_RESEARCH_20261118.md
