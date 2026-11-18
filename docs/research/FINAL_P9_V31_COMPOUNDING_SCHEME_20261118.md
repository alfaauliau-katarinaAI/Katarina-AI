# KATARINA AI — Rekomendasi Compounding Berbasis Backtest V3.1 + XAU SELL
Tanggal: 18 November 2026. Status: RISET SELESAI; TIDAK ADA AKTIVASI LIVE.

## Tujuan
Memilih skema reinvestment, penarikan cadangan profit, dan drawdown brake yang masuk akal dari backtest Katarina terakhir. Fokus BUKAN return historis maksimal nominal atau permintaan menaikkan risiko live. Semua skema diuji offline menggunakan data yang sama: ValetaxIntl-Live2 H1/H4 Agustus 2024–Oktober 2026 (27 bulan lengkap), November 2026 parsial. Modal awal simulasi USD10k, risiko per metode maksimal 0.25%, max2 slot simbol; NAS100 broker profit per tick sudah dikoreksi ke $1 per tick 0.1 indeks / 1lot menurut OrderCalcProfit.

## Temuan 13 compounding schemes × 4 tier risiko × 5 biaya (260 reruns)
Tiers: (1) cap .25% all 4 symbol, (2) defensive capped [.20,.25,.20,.25], (3) high historical [.75,3,.25,.50] PAPER ONLY, (4) half historical [.375,1.5,.125,.25] PAPER ONLY.
Modes: full sizing based on all trading balance; fixed principal $10k (risk never scales up); 50% / 25% profit reinvestment for sizing (untraded profits remain idle); step-$1000 sizing; brakes 3%/4%/6% and 2%/4%/5%; separate 25% or 50% of newly earned profit above the **total wealth high-water mark** into hypothetical external protected reserve on month turnover. Reserve no longer available to size trades or margin. This bank account was NOT actually opened and no withdrawals occurred. DD brake thresholds based on CLOSED trading balance peak (not floating equity).
Note: 50% sizing cap + 50% banked is doubly defensive and lowers growth; don't add this unless capital protection is priority.

Native cap .25% uniform (monthly normal / max closed DD / protected profit reserve after partial Nov):
- Full compound no bank: +$106.74/mo / 1.516% / $0.
- Full compound with 25% new highs banked + brake3/4/6: +$102.84/mo / 1.353% / $713.53.
- Half-size profits reinvested + bank 50% + brake3/4/6: +$97.19/mo / 1.105% / $1344.04.
- Full + 50% bank + brake3/4/6: +$99.84/mo / 1.193% / $1383.02.
- These uniform cap strategies still all show net negative at severe -0.6R. Full+25 bank: -$11.65/mo severe.

## Riset PER-METODE risiko within 0.25% (8 metode semuanya tetap ON)
Allocation EXACT order:
- XAU H1 BUY Donchian48: 0.15%;
- XAU H4 BUY Keltner: 0.25%;
- NAS H4 SELL MACDzero: 0.25%;
- EURJPY H4 BUY Momentum24: 0.10%;
- USDCHF H4 BUY RSI reentry: 0.05%;
- EURJPY H1 SELL EMA20 rejection: 0.25%;
- USDCHF H4 SELL MACDzero bearish: 0.15%;
- XAU H1 SELL BOS12 pullback: 0.25%.

All share per-symbol family exposure; max2 families open; no BUY and SELL same symbol simultaneously, no martingale. This allocation itself is selected from overmined historical 2024–25 with previous 2026 checks, so risk of overfit is considerable.

| Compounding policy within per-method cap | $ average/month normal | Total 27mo normal | Max closed DD normal | Hypothetical protected reserve after partial Nov | Stress -0.5R avg/month | Stress -0.6R avg/month |
|---|---:|---:|---:|---:|---:|---:|
| Full, no reserve, old brake4/8 | +62.80 | +1695.64 | 0.689% | $0 | +13.90 | +3.32 |
| **Full on active balance, 25% new net-profit high banked, brake3/4/6** | **+60.33** | **+1629.00** | **0.728%** | **$416.39** | **+13.72** | **+3.08** |
| Full active balance, 50% banked, brake3/4/6 | +59.35 | +1602.46 | 0.725% | $818.65 | +12.03 | +3.08 |
| Half-profit sizing, 50% banked, brake3/4/6 | +57.22 | +1544.82 | 0.699% | $787.98 | +11.68 | +2.96 |

NOTE: DD for bank25 actually **slightly increased** compared with no reserve in eight-method experiment (0.728 vs0.689 normal), although external cash protection is gained. Avoid claiming banking always reduces peak-to-trough DD.
After Nov partial for RECOMMENDED bank25 run: active trading balance $11,241.57; protected hypothetical reserve $416.39; combined net worth $11,657.96. November partial net +$28.95. After October full month total net worth $11,629.00 (27 months normal). The difference is because bank capital was removed from trading and simulated fill/lot rounded differently.
Severe stress -0.6R bank25 +$3.08/month across 27 full months, HOWEVER Jan–Oct 2026 specifically **-$14.33** in that stress, so no robust independent validation. At -0.7R bank25 **-$5.53/month** and DD2.027%; negative expectancy cannot be fixed by compounding.

## Recommended paper-only protocol
For research and demo assessment, Yura prefers FULL compound on the **active trading balance only**, with automatic protective reserve allocation of 25% of PROFITS ABOVE last combined high-water mark after each completed month. Keep 75% of newly earned profits available to compound, including no leverage or risk % increase. In response to drawdown on CLOSED trading balance:
- DD 0% to below 3%: full listed per-engine percentage.
- DD 3% to below 4%: half the listed risk percentage.
- DD 4% to below 6%: quarter of listed risk percentage.
- DD >=6%: pause new entries pending review (this gate will not independently recover if no new positive cash flows; manual approval required to reset).
- Protect reserve outside the EA/account; do not automatically redeposit it as trading loss recovery. No addition to losing positions.
- Lot ALWAYS calculated per signal based on current broker loss in account currency: riskUSD = active closed balance × riskMethod × brake, then find 1lot loss through OrderCalcProfit(actual entry to SL), quantize down to SYMBOL_VOLUME_STEP, reject if below min volume, cap to maximum volume, check OrderCalcMargin and total open family risk; NAS tick value reported may be 10x wrong.
- Maximum 2 slots; one slot per pair; one direction per pair; no hedge. No fixed lot increase after wins.
- Example hypothetical: active $10,000, make $1,000 profit (new high), bank25%=$250, active $10,750, external reserve $250. At no DD, a NAS H4 SELL risk 0.25% × active $10,750 = $26.875; a XAU H1 BUY risk0.15% = $16.125; lot depends on dynamic stop.
- The above is a **research recommendation, not a production change**; risk cannot go above original native 0.25% per entry without separate authorization and validation.

## Max historical aggressive compounding is NOT best to deploy
PAPER 0.75% XAU / 3% NAS / .25% EUR / .50% CHF:
- Full compounding no bank +$1235.59/mo, normal closed DD5.955%, -0.6R +$79.63/mo, -0.7R -$18.07/mo, DD9.029% and 114 blocked entries; not forward validated.
- Full + bank25 and brake3/4/6 +$913.16/mo, normal closed DD4.703%, external reserve $6129.12, -0.6R only +$2.81/mo; at -0.7R -$13.49/mo. Most growth hinges on 26 NAS trades at 3% risk, 12x native cap. These are dangerous overfit retrospective simulations, not acceptable live sizing.
- Static 50% or quarter compounding and fixed size limit growth, but neither can transform negative -0.7R expectancy into an actual positive edge.
- The aggressive risk out of current authorized 0.25% production cap was used only in OFFLINE research and MUST NOT be deployed.

## Evidence gate and caveats
- P9/P7 originals SHA256 frozen checked; 0 broker orders, 0 live changes.
- Historical price data Jan–Jun 2024 spread invalid, so only complete Aug2024–Oct2026 included. Nov partial separately.
- Backtest based on H1/H4 stop-first OHLC approximate BID/ASK, estimated fee/slippage/swap and current margin snapshot, NOT native MT5 Strategy Tester real ticks, true equity floating DD, historical full margin, or historically valid 1lot loss in every currency conversion.
- Much of same historical data was used in selecting indicators and per-engine risk weights, creating severe multiple-testing overfit risk; no virgin OOS or fresh forward test.
- A profit-reserve account and DD brake improve practical capital management but cannot guarantee recovery or profitability, especially as severe-cost regime shifts.
- Pausing at >=6% CLOSED DD does not cap floating DD or gaps, and may prevent recovery until manual review.

## Files
C:\Katarina\research\p9-v31-compounding-study-20261118\
- backtest_compounding_policies.py
- COMPOUNDING_POLICY_FULL_RESULTS.json
- compare_compound_per_eight_engine.py
- COMPOUNDING_EIGHT_ENGINE_RISK_COMPARISON.json
- final_compound_details.py
- FINAL_P9_V31_COMPOUNDING_SCHEME_20261118.md (this report)

**Conclusion:** Best operational PAPER compromise for Katarina within current cap is **75% new-profit reinvestment / 25% new-high-profit protected reserve, independent per-entry risk 0.05–0.25%, DD-aware brake3/4/6, dynamic lot by OrderCalcProfit**. This is NOT demonstrably global optimal compounding or future-proof. EvidenceRiskGate remains WAIT.
