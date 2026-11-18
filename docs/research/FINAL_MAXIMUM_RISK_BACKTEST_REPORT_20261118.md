# KATARINA AI — MAXIMUM RISK BACKTEST, 2024–CURRENT

**Tanggal audit:** 18 November 2026
**Status:** REPLAY HISTORIS OFFLINE SELESAI, NO ORDER / NO PRODUCTION CHANGE.
**Model:** P9 Adaptive V3.1 + XAU SELL BOS12 pullback; NAS BUY tidak digunakan.
**Waktu:** 1 Agustus 2024 sampai 31 Oktober 2026, 27 bulan PENUH dengan broker H1 spread. November 2026 sampai data terminal terakhir masih parsial. Jan–Jun 2024 ada OHLC namun spread bernilai nol, tidak bisa direkonstruksi secara valid sebagai transaksi pada biaya nyata.

## 1. Konfigurasi maksimum dari GRID RISET SEBELUMNYA
Risiko per entry sebagai persen SALDO tertutup saat masuk:
- XAUUSD.vx: 0.75% = $75 pada akun ilustrasi $10,000
- NAS100.vx: 3.00% = $300 pada akun ilustrasi $10,000
- EURJPY.vx: 0.25% = $25 pada akun ilustrasi $10,000
- USDCHF.vx: 0.50% = $50 pada akun ilustrasi $10,000
Maksimal dua keluarga posisi (XAU/NAS/EUR/CHF) terbuka bersamaan. Satu simbol tanpa hedge BUY-SELL. Entry baru dibelah saat closed DD>=4%; entry baru berhenti saat closed DD>=8%. Tidak ada floating DD stop. Maks theoretical simultaneous initial SL risk: 3.75% XAU + NAS before gaps/slippage. Nas order calculation VERIFIED from read-only OrderCalcProfit: $1 per tick 0.1 index price, per 1 lot; symbol_info trade_tick_value $0.1 is inconsistent and MUST NOT be used alone.

Delapan signal engines dipakai, tanpa mengubah source P9 V2/P7, tanpa melakukan order:
XAU_H1_BUY, XAU_H4_BUY, NAS_H4_SELL, EUR_H4_BUY, CHF_H4_BUY, EUR_H1_SELL, CHF_H4_SELL, XAU_H1_SELL.
Harga Bid/Ask H1/H4 Valetax; sinyal candle sudah selesai; SL=max(1.4 ATR14,3 spread), TP/timeouts strategi; stops diprioritaskan ketika H1 SL dan TP sama-sama tersentuh. Lot dinamis berdasarkan risk per 1 lot, volume_step/min/max; biaya meliputi bid/ask, spread p90, slippage baseline/ekstra, estimated $4/lot komisi dan snapshot swap current, tambahan hipotetis stress R. Current broker margin snapshot dari OrderCalcMargin digunakan untuk total used margin<=75% synthetic closed balance dengan reserve25% (bukan native historical margin).

## 2. Hasil uji ULANG dan AUDIT
| Biaya ekstra per trade | Net $ 27 bulan | Rata-rata $/bulan | Max closed DD % | Trades ditutup (27 bulan) | Entry veto DD |
|---|---:|---:|---:|---:|---:|
| Normal | +33,360.86 | +1,235.59 | 5.955 | 244 | 0 |
| -0.40R | +8,787.65 | +325.47 | 7.416 | 243 | 0 |
| -0.50R | +5,176.67 | +191.73 | 7.202 | 242 | 0 |
| -0.60R | +2,149.91 | +79.63 | 7.803 | 240 | 0 |
| -0.70R | **-487.91** | **-18.07** | **9.029** | 147 | 114 |
| -0.80R | -797.81 | -29.55 | 8.156 | 87 | 189 |
| -1.00R | -826.63 | -30.62 | 8.378 | 35 | 258 |

**CLIFf:** Di antara stress -0.6R dan -0.7R sistem kehilangan edge, rugi dan berkali-kali memblokir entry karena DD>=8%. Veto tidak membuktikan future safety; closed DD bisa melewati threshold karena gap.

Normal 27 bulan: starting $10,000 -> **$43,360.86** saldo teoretis after Oct2026 (+333.61% cumulatively vs initial, compounding as modeled); November 2026 PARTIAL **-$110.35** -> $43,250.51 as of latest frozen bar, incomplete month, NOT a full-month monthly average. Win rate 65.16% (244 historical fills), profit factor 3.96, mean $1,235.59/month, 24 positive full months, 3 losing full months. Worst month April2026 **-$1,268.05**, best month August2026 **+$3,849.06**.
Growth was primarily from NAS: NAS100.vx **+$19,428.71 on just 26 closed entries** (58.2% total profit); XAUUSD +$10,666.28 on 119; EURJPY +$1,499.14 on 60; USDCHF +$1,766.74 on 39. 26 NAS entries extremely sparse given 3% risk, major overfit & concentrated risk flag. XAU SELL 12 fills, EUR SELL15, CHF SELL14 — insufficient independent validation.

## 3. Per-year hasil normal 27 full months
- Aug–Dec 2024 (5 bulan): +$2,709.23, 51 closed entries.
- Jan–Dec 2025 (12 bulan): +$14,723.69, 130 closed entries.
- Jan–Oct 2026 (10 bulan): +$15,927.94, 63 closed entries.
- Nov 2026 PARTIAL: -$110.35 / 3 closed entries. **Do not include this partial month in average**.

## 4. Perbandingan risk cap & failure
| Portfolio tested (XAU NAS EUR CHF) | Normal $/bulan | -0.6R $/bulan | Normal DD % | Stress -0.6R DD % |
|---|---:|---:|---:|---:|
| CAP_EQUAL 0.25/0.25/0.25/0.25 | +106.74 | -15.32 | 1.516 | 4.816 |
| MAX_RESEARCH .75/3/.25/.5 | +1,235.59 | +79.63 | 5.955 | 7.803 |
| REF_RESEARCH .5/3/.25/.25 | +863.00 | +86.91 | 5.992 | 7.473 |
| EQUAL RESEARCH .75% all | +665.33 | -26.27 | 5.235 | 8.397 |
| EQUAL RESEARCH 1% all | +1,159.32 | -25.15 | 6.110 | 8.109 |
| EQUAL RESEARCH 2% all | +3,298.82 | -20.13 | 8.272 | 8.135 |
*These are all PAPER models; high-profit risk settings are not suitable for direct trading without much stronger evidence.*

## 5. Actual historical tested lot range (at compounded simulated balance)
| Symbol | Min lot | Median lot | Max lot | Closed fills |
|---|---:|---:|---:|---:|
| XAUUSD.vx | 0.02 | 0.08 | 0.16 | 119 |
| NAS100.vx | 0.13 | 0.295 | 0.71 | 26 |
| EURJPY.vx | 0.02 | 0.12 | 0.65 | 60 |
| USDCHF.vx | 0.06 | 0.21 | 0.42 | 39 |

Lot bukan nilai tetap. Risk per trade dikuantisasikan ke volume step; per-signal ATR/SL beda. Reported max combined used margin on fills using CURRENT 1lot snapshot = $1,907.95 at one moment; **NOT actual equity-based margin-call audit**. Largest combined initial stop risk modeled 3.703% of then-closed balance. Historical synthetic account was 1:1000 leverage reference and margin requirements may have changed.

## 6. Highest risks of false certainty and limits
- Data **2024–2026 extensively mined and model risk chosen on this history**; not untouched OOS, so high historical compounded returns can represent overfitting.
- Previous 10,000 three-month block reorder (same mined dataset) showed 34.4% scenario reshufflings crossing closed DD8% in -0.6R; this is descriptive fragility, not a calibrated future probability.
- The latest test is **NOT native MT5 Every tick based on real ticks**. Trade fills use H1 OHLC first-touch; floating equity DD, real spread spikes inside H1, gaps, native margin stop-outs, full historical commission, historical swaps, and changing conversion/tick size not all measured.
- Late 2026-Nov partial is not a full month, and Jan–Jun 2024 had zero historical spread.
- Cost penalties -0.4R to -1.0R are hypothetical sensitivity, not actual broker fees.
- At extreme risks, closed DD threshold 8% in one path is not a maximum safe risk; gaps and intra-bar excursion can cause greater loss.
- This is a **FINITE HISTORICAL GRID MAXIMUM**, not a market-wide optimum nor deployable safe ceiling.

## 7. Research decision / operational safety
Historical maximum model .75/3/.25/.5 **passes** the prior constrained grid under -0.6R but **fails** one slightly more adverse extra -0.7R by -$487.91 total, DD9.029%, 114 blocked entries. NAS 3% is 12 times the current authorized production per-entry risk limit 0.25%. Thus no approval for live promotion. P9 V2, P7 locked and still untouched; EvidenceRiskGate WAIT, 0 broker orders, no changes to any live MetaTrader EA or GitHub.

## 8. Reproducible files
Folder `C:\Katarina\research\p9-v31-risk-allocation-limit-20261118\MAXIMUM_RISK_BACKTEST_20261118\`:
- `rerun_maximum_historical_risk.py` — reproduce 7 profiles × 7 cost scenarios.
- `MAXIMUM_RISK_REBACKTEST_FINAL.json` — complete 27 monthly profit/equity, scenarios 0.0...1.0, by symbol & engine lots, years and risk.
- `MAXIMUM_RISK_MONTHLY_NORMAL_VS_STRESSES.csv` — month-level results and simulated ending balance including Nov PARTIAL.
- `FINAL_MAXIMUM_RISK_BACKTEST_REPORT_20261118.md` — this memo.
- `verify_maximum_risk_backtest.py` — compare engine output with frozen prior and original SHA256 locks.

**CONCLUSION:** Research maximum is economically attractive ONLY on historical normal cost, but fragile beyond -0.6R. Do not increase live risk; native real tick/float DD/independent forward evidence required.
