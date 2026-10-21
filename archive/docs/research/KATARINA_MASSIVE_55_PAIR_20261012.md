# Laporan Final: KATARINA AI — Riset Besar 55 Pair (12 Oktober 2026)

**HASIL: SELESAI 55/55, tetapi BELUM ADA KONFIGURASI YANG LULUS UNTUK LIVE.**

## Rekap

- Total kombinasi teoretis: **1,995,840**; benar-benar disimulasikan: **313,362**; cukup data train: **285,294**.
- Kandidat hasil pemilihan **hanya dari 2025**: 43 pair; tanpa kandidat: 12; lolos biaya stres dan 2 jendela evaluasi 2026: **0 pair**.
- Entry gabungan kandidat terpilih: **2129**; profil pengaturan risiko portofolio: **288**.
- Penelitian read-only MT5, **nol order broker** dan live risk OFF. Tidak ada setelan risk produksi yang diubah.

## Strategi dan pengaturan yang dibandingkan

14 strategi: EMA pullback, Donchian, MACD, Fibonacci, RSI continuation, Ichimoku, Bollinger/RSI/Keltner sideways, exhaustion reversal, swing reversal, volatility breakout, liquidity sweep, Bollinger squeeze. Regime: TREND_BUY, TREND_SELL, SIDEWAYS, VOLATILE dan NO_CONCLUSION (WAIT).
Timeframe: M15, M30, H1, H4. Candle: ANY, BODY55, ENGULF, PIN. Arah: BOTH/BUY/SELL. Sesi: ALL/EU_US. SL=0,9/1,3/1,8 ATR (minimum 3x spread); RR=1,3/2/3; waktu exit=8/16/32 bar.
Seleksi minimal 28 trade pada sekurangnya 4 bulan 2025, rangking memakai expectancy dan penalti drawdown. Dua periode 2026 dihitung tanpa mengubah parameter yang terpilih.
**Periode 2026 sudah pernah dianalisis sebelum riset ini**, sehingga tidak memenuhi standar holdout yang benar-benar baru. Optimasi ratusan ribu konfigurasi menghasilkan risiko besar overfitting.
Biaya: spread bid/ask yang diproksikan dari bar MT5 M15, tambahan 0,05R dan stress extra 0,15R; jika SL/TP bersamaan dihitung SL, gap stop memakai harga open lebih buruk. Bukan true-tick fill dan belum termasuk swap, komisi broker riil, margin, rounding lot dan intratrade DD.

## Setelan kandidat tiap pair (BUKAN rekomendasi live)

Angka train/val/diag: jumlah entry / rata-rata R **sebelum** tambahan biaya stres 0,15R. Status seluruh setelan adalah NO-GO karena tidak memenuhi kedua segmen 2026 atau data kurang.

| Pair | Strategi | TF | Candle | Arah | SL ATR | RR | Hold | Train n/R | Val n/R | Diag n/R |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| AUDCAD.vx | RANGE_KELTNER | H1 | NONE | BOTH | 0.9 | 3 | 16 | 40/+0.367 | 21/-0.635 | 5/-0.250 |
| AUDCHF.vx | RANGE_KELTNER | H1 | NONE | BOTH | 1.8 | 3 | 16 | 29/+0.186 | 12/-0.448 | 1/+0.090 |
| AUDJPY.vx | TREND_ICHIMOKU | M15 | ENGULF | BUY | 0.9 | 2 | 16 | 28/+0.511 | 12/-0.300 | 1/-1.050 |
| AUDNZD.vx | TREND_ICHIMOKU | H4 | NONE | BOTH | 1.3 | 1.3 | 8 | 30/+0.219 | 13/-0.549 | 10/-0.053 |
| AUDUSD.vx | RANGE_BB | H1 | ENGULF | BOTH | 1.8 | 3 | 32 | 28/+0.583 | 10/-0.048 | 8/-0.674 |
| AUS200.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| BCHUSD.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| BTCEUR.vx | TREND_DONCHIAN | H4 | NONE | BOTH | 1.3 | 2 | 8 | 29/+0.086 | 24/-0.383 | 10/-0.150 |
| BTCUSD.vx | TREND_RSI50 | H1 | BODY55 | BOTH | 0.9 | 3 | 16 | 31/+0.814 | 16/-0.550 | 13/-0.742 |
| CADCHF.vx | TREND_ICHIMOKU | M30 | NONE | BOTH | 1.3 | 1.3 | 8 | 29/+0.044 | 1/+0.184 | 0/+0.000 |
| CADJPY.vx | TREND_ICHIMOKU | M30 | NONE | BUY | 1.8 | 3 | 32 | 28/+0.335 | 1/-1.050 | 2/-0.315 |
| CHFJPY.vx | TREND_PULLBACK | M30 | BODY55 | BUY | 1.8 | 3 | 32 | 36/+0.525 | 12/-0.248 | 4/-0.402 |
| DAX40.vx | TREND_FIB50 | M15 | ENGULF | BUY | 0.9 | 3 | 32 | 30/+0.658 | 17/+0.224 | 15/-0.250 |
| DOGEUSD.vx | TREND_PULLBACK | M30 | NONE | BOTH | 0.9 | 2 | 16 | 33/+0.338 | 0/+0.000 | 0/+0.000 |
| DXY.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| ETHUSD.vx | VOL_BREAKOUT | M30 | NONE | SELL | 1.8 | 3 | 32 | 32/+0.662 | 11/-0.526 | 3/-1.050 |
| EU50.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| EURAUD.vx | TREND_PULLBACK | M30 | ENGULF | BUY | 0.9 | 2 | 32 | 38/+0.529 | 12/-0.300 | 6/-1.050 |
| EURCAD.vx | RANGE_BB | H4 | NONE | BOTH | 0.9 | 3 | 8 | 28/+0.381 | 9/+0.287 | 10/+1.135 |
| EURCHF.vx | RANGE_BB | H4 | NONE | BOTH | 1.3 | 1.3 | 8 | 32/+0.162 | 8/+0.061 | 1/-1.363 |
| EURGBP.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| EURJPY.vx | TREND_PULLBACK | M30 | ENGULF | BUY | 1.8 | 3 | 32 | 30/+0.636 | 7/+0.169 | 1/-1.050 |
| EURNZD.vx | RANGE_KELTNER | H1 | NONE | BUY | 1.3 | 3 | 32 | 29/+0.702 | 14/-1.050 | 4/-0.592 |
| EURUSD.vx | REVERSAL_SWING | M30 | PIN | BUY | 1.8 | 3 | 32 | 29/+0.672 | 6/-0.859 | 6/-0.383 |
| FRA40.vx | TREND_FIB50 | H1 | BODY55 | BOTH | 1.3 | 3 | 32 | 29/+0.230 | 12/-0.383 | 5/-1.050 |
| GBPAUD.vx | REVERSAL_SWING | M30 | PIN | BOTH | 1.3 | 3 | 32 | 37/+0.450 | 12/+0.036 | 7/+0.093 |
| GBPCAD.vx | TREND_ICHIMOKU | H1 | ENGULF | BUY | 0.9 | 3 | 16 | 30/+0.626 | 6/-1.056 | 2/+0.341 |
| GBPCHF.vx | VOL_BREAKOUT | M30 | BODY55 | BOTH | 0.9 | 3 | 8 | 28/+0.354 | 4/+0.279 | 5/-0.090 |
| GBPJPY.vx | RANGE_BB | H1 | PIN | BOTH | 1.3 | 2 | 16 | 30/+0.467 | 5/+0.236 | 8/-0.244 |
| GBPNZD.vx | RANGE_BB | M30 | ENGULF | SELL | 1.8 | 3 | 32 | 33/+0.405 | 6/-0.383 | 3/-0.378 |
| GBPUSD.vx | TREND_PULLBACK | M30 | PIN | BOTH | 1.3 | 3 | 32 | 38/+0.509 | 9/-0.161 | 10/-0.838 |
| HK50.vx | TREND_ICHIMOKU | H1 | NONE | BOTH | 0.9 | 3 | 32 | 39/+0.324 | 25/-0.601 | 27/+0.093 |
| JPN225.vx | RANGE_KELTNER | H1 | BODY55 | BOTH | 0.9 | 3 | 16 | 29/+0.743 | 17/-0.689 | 12/-0.035 |
| LTCUSD.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| NAS100.vx | RANGE_BB | M30 | BODY55 | SELL | 0.9 | 3 | 16 | 36/+0.617 | 10/-0.148 | 14/+0.282 |
| NZDCAD.vx | TREND_PULLBACK | H4 | NONE | BOTH | 0.9 | 1.3 | 16 | 34/+0.179 | 18/-0.167 | 11/+0.205 |
| NZDCHF.vx | TREND_ICHIMOKU | H4 | NONE | SELL | 0.9 | 3 | 8 | 31/+0.566 | 5/-0.834 | 7/+0.463 |
| NZDJPY.vx | RANGE_KELTNER | H1 | NONE | BUY | 1.8 | 2 | 32 | 37/+0.365 | 12/-0.422 | 0/+0.000 |
| NZDUSD.vx | TREND_ICHIMOKU | M15 | NONE | BOTH | 1.8 | 1.3 | 32 | 29/+0.671 | 16/-0.057 | 1/-1.050 |
| SP500.vx | TREND_PULLBACK | M15 | NONE | BOTH | 0.9 | 2 | 8 | 31/+0.284 | 3/+0.383 | 10/-0.150 |
| UK100.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| US30.vx | TREND_ICHIMOKU | M30 | ENGULF | BUY | 1.3 | 3 | 32 | 33/+0.656 | 13/+0.263 | 18/-0.273 |
| USDCAD.vx | TREND_RSI50 | M30 | NONE | BUY | 1.3 | 1.3 | 32 | 30/+0.463 | 7/-0.506 | 1/-1.050 |
| USDCHF.vx | TREND_DONCHIAN | H1 | BODY55 | SELL | 1.8 | 3 | 32 | 40/+0.717 | 11/+0.768 | 9/-0.574 |
| USDJPY.vx | VOL_BREAKOUT | M30 | NONE | BUY | 0.9 | 3 | 8 | 34/+0.694 | 6/-1.050 | 8/+0.281 |
| XAGEUR.vx | TREND_DONCHIAN | M30 | BODY55 | BUY | 1.3 | 3 | 32 | 30/+0.665 | 30/-0.250 | 15/-0.535 |
| XAGUSD.vx | TREND_PULLBACK | H1 | NONE | BUY | 1.8 | 3 | 16 | 28/+0.572 | 8/+0.309 | 13/-0.591 |
| XAUEUR.vx | TREND_FIB50 | M30 | ENGULF | BUY | 1.3 | 3 | 32 | 28/+0.981 | 7/+0.457 | 7/+0.664 |
| XAUUSD.vx | TREND_DONCHIAN | M30 | ENGULF | BUY | 0.9 | 3 | 32 | 37/+1.004 | 8/+0.950 | 7/+0.664 |
| XBRUSD.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| XNGUSD.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| XPDUSD.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| XPTUSD.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |
| XRPUSD.vx | TREND_ICHIMOKU | H4 | NONE | BOTH | 0.9 | 1.3 | 8 | 28/+0.073 | 1/-1.050 | 4/-0.775 |
| XTIUSD.vx | TANPA KANDIDAT | - | - | - | - | - | - | - | - | - |

## Gabungan entry seluruh pair per bulan

Sum R adalah penjumlahan kandidat individual dan **bukan return akun atau ekuitas bersih portofolio**.

| Bulan | Entry | Total R dasar | Total R setelah stres | Pair aktif |
|---|---:|---:|---:|---:|
| 2025-01 | 72 | +50.056 | +39.256 | 26 |
| 2025-02 | 76 | +27.914 | +16.514 | 30 |
| 2025-03 | 136 | +69.089 | +48.689 | 34 |
| 2025-04 | 171 | +81.812 | +56.162 | 37 |
| 2025-05 | 124 | +42.140 | +23.540 | 35 |
| 2025-06 | 110 | +52.052 | +35.552 | 38 |
| 2025-07 | 128 | +56.268 | +37.068 | 37 |
| 2025-08 | 87 | +67.300 | +54.250 | 34 |
| 2025-09 | 110 | +61.166 | +44.666 | 34 |
| 2025-10 | 121 | +39.315 | +21.165 | 38 |
| 2025-11 | 131 | +75.219 | +55.569 | 38 |
| 2025-12 | 102 | +50.176 | +34.876 | 33 |
| 2026-01 | 91 | -7.529 | -21.179 | 35 |
| 2026-02 | 118 | -35.118 | -52.818 | 36 |
| 2026-03 | 102 | -27.177 | -42.477 | 37 |
| 2026-04 | 73 | -24.207 | -35.157 | 27 |
| 2026-05 | 73 | -24.315 | -35.265 | 27 |
| 2026-06 | 74 | -19.383 | -30.483 | 28 |
| 2026-07 | 76 | -13.860 | -25.260 | 28 |
| 2026-08 | 67 | -9.060 | -19.110 | 25 |
| 2026-09 | 73 | -7.917 | -18.867 | 28 |
| 2026-10 | 14 | -5.472 | -7.572 | 11 |

## Simulasi pengelolaan risiko

288 skenario: risiko per transaksi 0,10/0,25/0,50/1,00%, maksimal 1/2/3 posisi, limit harian 1/2%, batas closed drawdown 6/10/15%, cooldown mingguan setelah 3/5 losing trades, serta limit 1/2 posisi per kelas aset. Hasil simulasi dengan modal virtual $10.000. Bukan P&L riil, tidak memasukkan floating DD atau broker margin.

**Baseline defensif simulasi (0,25% per trade; 1 slot; stop harian 1%; DD guard 6%; cooldown 3 loss; grup maksimal 1):**
- Train 2025: return virtual +28.312%, DD 4.361%, n=367, halted=false.
- Validasi 2026 Jan–Mei: return virtual -5.178%, DD 6.151%, n=92, halted=true.
- Diagnostik 2026 Jun–Okt: return virtual -6.281%, DD 6.281%, n=39, halted=true.

**Optimizer khusus training 2025 memilih 1%/trade, 3 posisi, daily 2%, batas DD 15%, cooldown 5 loss, batas grup 1.**
- Train 2025: +1379.440% virtual; DD 11.643%; 734 trade.
- Validasi Jan–Mei 2026: -12.969% virtual; DD 15.564%; n=54; halted=true.
- Diagnostik Jun–Okt 2026: -15.220% virtual; DD 15.22%; n=24; halted=true.
**Setelan agresif ditolak:** angka 2025 terdongkrak bias seleksi dan hasil 2026 negatif/menyentuh batas risiko.

## Keputusan dan artefak

**NO-GO live trading** sampai ada data baru yang benar-benar belum diperiksa dengan parameter dibekukan, tick bid/ask, biaya akun, margin, dan forward demo terukur.
- `docs/research/outputs/20261012/per_pair.csv`: 55 konfigurasi dan statistik.
- `docs/research/outputs/20261012/monthly.csv`: rekap semua entry kandidat per bulan.
- `docs/research/outputs/20261012/risk_sweep.csv`: 288 variasi portofolio.
- `scripts/research/mega_multi_asset_v2.py` + `massive_risk_report.py`: engine reproduksi pada VPS Windows MT5.
- Data OHLC broker disimpan PRIVAT pada VPS, tidak masuk repository publik; GitHub-hosted CI hanya menguji kode menggunakan data sintetis.

## Rujukan metodologi

- Moskowitz et al., Time Series Momentum (2012): https://doi.org/10.1016/j.jfineco.2011.11.003
- Bailey & López de Prado, Deflated Sharpe Ratio (2014): https://doi.org/10.3905/jpm.2014.40.5.094
- Bailey et al., Probability of Backtest Overfitting: https://escholarship.org/uc/item/4w1110bb
- CFTC, simulated-performance disclosure: https://www.cftc.gov/sites/default/files/enf/00orders/enfcts.htm
