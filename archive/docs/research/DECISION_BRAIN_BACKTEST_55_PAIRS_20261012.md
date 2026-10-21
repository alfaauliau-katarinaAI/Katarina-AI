# Backtest Decision Brain KATARINA — 55 Pair (12 Oktober 2026)

**Riset historis selesai. Ini bukan bukti strategi live menguntungkan.**

## Ringkasan faktual

- Broker simbol: 55, berhasil: 55, error/kurang data: 0.
- Snapshot historis yang dianalisis: 134,772, sampling 1 dari 36 M5 bar (~3 jam) per pair.
- Keputusan: BUY 3,952, SELL 4,358, WAIT 126,462.
- Trade hipotetis dengan exit terdefinisi: 8,310; mean -0.2051R, PF +0.7008, win rate +31.3100%.
- Entry pada open M5 berikutnya, spread dari candle broker; SL 1,2 ATR M5, TP 1,8R, hold maksimum 24 M5 bar, biaya tambahan asumsi 0,03R.
- News historis TIDAK divalidasi. Sinyal dihitung hanya untuk diagnosis teknis dengan berita DIASUMSIKAN aman; tidak boleh menjadi izin entry.
- Backtest pasar menggunakan data lampau yang sudah pernah diteliti. Tidak boleh disebut independent forward/OOS.
- Tambahan stress test biaya +0,10R/trade dan +0,20R/trade masing-masing menghasilkan rata-rata -0.3051R dan -0.4051R.

## Total hasil retrospektif per periode

| Periode | Trade | Avg R | Jumlah R | PF | Win% |
|---|---:|---:|---:|---:|---:|
| 2025_available | 3085 | -0.1928 | -594.6548 | +0.7146 | +31.9000% |
| 2026_Jan_May | 3351 | -0.2117 | -709.3364 | +0.6944 | +30.8600% |
| 2026_Jun_Oct | 1874 | -0.2136 | -400.3453 | +0.6901 | +31.1600% |

## Performa menurut kondisi pasar dan strategi

Sinyal ini hanya kandidat teknis dengan asumsi berita valid, tidak termasuk Risk Governor live.

| Kondisi | Trade | Mean R | PF | Win% |
|---|---:|---:|---:|---:|
| BREAKOUT_DOWN | 691 | -0.1996 | +0.7132 | +30.9700% |
| BREAKOUT_UP | 642 | -0.2653 | +0.6260 | +29.1300% |
| PULLBACK_DOWN | 462 | -0.2146 | +0.6841 | +30.7400% |
| PULLBACK_UP | 355 | -0.1560 | +0.7644 | +33.2400% |
| REVERSAL_DOWN | 16 | -0.2258 | +0.6803 | +31.2500% |
| REVERSAL_UP | 34 | -0.3401 | +0.5323 | +29.4100% |
| SIDEWAYS | 2767 | -0.2075 | +0.6977 | +31.3300% |
| TREND_DOWN | 1707 | -0.1856 | +0.7272 | +31.9300% |
| TREND_UP | 1636 | -0.2051 | +0.6992 | +31.4200% |

| Strategi | Trade | Mean R | PF | Win% |
|---|---:|---:|---:|---:|
| BREAKOUT_RETEST | 1333 | -0.2312 | +0.6708 | +30.0800% |
| RANGE_FADE | 2767 | -0.2075 | +0.6977 | +31.3300% |
| REVERSAL_RECLAIM | 50 | -0.3035 | +0.5787 | +30.0000% |
| TREND_PULLBACK | 4160 | -0.1940 | +0.7145 | +31.7100% |

## Data lengkap semua pair

| Pair | Status | Snapshot | BUY | SELL | WAIT | Trade | Avg R | PF | 2025 n/R | Jan–Mei 2026 n/R | Jun–Okt 2026 n/R |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| AUDCAD.vx | OK | 2466 | 13 | 17 | 2436 | 30 | -0.4932 | +0.3039 | 1/-1.0300 | 26/-0.5305 | 3/+0.0085 |
| AUDCHF.vx | OK | 2465 | 8 | 16 | 2441 | 24 | -0.1444 | +0.7770 | 6/-0.1883 | 16/-0.1922 | 2/+0.3700 |
| AUDJPY.vx | OK | 2466 | 72 | 95 | 2299 | 167 | -0.2776 | +0.5968 | 69/-0.1373 | 83/-0.3623 | 15/-0.4545 |
| AUDNZD.vx | OK | 2468 | 9 | 7 | 2452 | 16 | -0.0385 | +0.9259 | 5/-0.7778 | 10/+0.2100 | 1/+1.1731 |
| AUDUSD.vx | OK | 2468 | 65 | 76 | 2327 | 141 | -0.3421 | +0.5471 | 30/-0.1619 | 88/-0.4464 | 23/-0.1779 |
| AUS200.vx | OK | 2446 | 1 | 0 | 2445 | 1 | -1.0300 | +0.0000 | 0/— | 1/-1.0300 | 0/— |
| BCHUSD.vx | OK | 2492 | 1 | 0 | 2491 | 1 | +1.7700 | — | 0/— | 1/+1.7700 | 0/— |
| BTCEUR.vx | OK | 2491 | 0 | 6 | 2485 | 6 | -0.5633 | +0.3437 | 0/— | 5/-0.4700 | 1/-1.0300 |
| BTCUSD.vx | OK | 2493 | 207 | 243 | 2043 | 450 | -0.1974 | +0.7171 | 43/-0.4824 | 242/-0.2035 | 165/-0.1143 |
| CADCHF.vx | OK | 2466 | 1 | 0 | 2465 | 1 | -0.5191 | +0.0000 | 0/— | 1/-0.5191 | 0/— |
| CADJPY.vx | OK | 2468 | 8 | 26 | 2434 | 34 | -0.3373 | +0.5351 | 13/-0.5224 | 17/-0.0328 | 4/-1.0300 |
| CHFJPY.vx | OK | 2465 | 81 | 88 | 2296 | 169 | -0.1998 | +0.7041 | 56/-0.0563 | 69/-0.3184 | 44/-0.1963 |
| DAX40.vx | OK | 2399 | 270 | 286 | 1843 | 556 | -0.1525 | +0.7708 | 237/-0.0953 | 163/-0.1353 | 156/-0.2574 |
| DOGEUSD.vx | OK | 2470 | 0 | 0 | 2470 | 0 | — | — | 0/— | 0/— | 0/— |
| DXY.vx | OK | 2418 | 0 | 0 | 2418 | 0 | — | — | 0/— | 0/— | 0/— |
| ETHUSD.vx | OK | 2490 | 12 | 20 | 2458 | 32 | -0.1879 | +0.6830 | 9/-0.5709 | 19/+0.0074 | 4/-0.2540 |
| EU50.vx | OK | 2314 | 4 | 10 | 2300 | 14 | -0.5046 | +0.3338 | 7/-0.6300 | 6/-0.3795 | 1/-0.3780 |
| EURAUD.vx | OK | 2466 | 123 | 129 | 2214 | 252 | -0.1455 | +0.7795 | 101/-0.1366 | 124/-0.0584 | 27/-0.5783 |
| EURCAD.vx | OK | 2468 | 51 | 61 | 2356 | 112 | -0.1415 | +0.7854 | 45/-0.4012 | 58/+0.0782 | 9/-0.2592 |
| EURCHF.vx | OK | 2464 | 1 | 2 | 2461 | 3 | -0.6341 | +0.0766 | 0/— | 2/-1.0300 | 1/+0.1578 |
| EURGBP.vx | OK | 2468 | 2 | 1 | 2465 | 3 | -0.5388 | +0.2154 | 2/-0.2932 | 1/-1.0300 | 0/— |
| EURJPY.vx | OK | 2470 | 106 | 131 | 2233 | 237 | -0.1842 | +0.7276 | 131/-0.2066 | 77/-0.1066 | 29/-0.2894 |
| EURNZD.vx | OK | 2469 | 83 | 62 | 2324 | 145 | -0.3468 | +0.5189 | 68/-0.3341 | 56/-0.3165 | 21/-0.4683 |
| EURUSD.vx | OK | 2466 | 149 | 148 | 2169 | 297 | -0.3002 | +0.5928 | 121/-0.1873 | 119/-0.3168 | 57/-0.5053 |
| FRA40.vx | OK | 2316 | 60 | 84 | 2172 | 144 | -0.3253 | +0.5401 | 101/-0.2856 | 36/-0.3773 | 7/-0.6300 |
| GBPAUD.vx | OK | 2467 | 164 | 155 | 2148 | 319 | -0.2447 | +0.6436 | 134/-0.2589 | 137/-0.2632 | 48/-0.1521 |
| GBPCAD.vx | OK | 2467 | 63 | 70 | 2334 | 133 | -0.2678 | +0.6273 | 43/-0.0671 | 70/-0.3541 | 20/-0.3972 |
| GBPCHF.vx | OK | 2467 | 5 | 11 | 2451 | 16 | -0.1371 | +0.7656 | 5/+0.6500 | 8/-0.2942 | 3/-1.0300 |
| GBPJPY.vx | OK | 2466 | 155 | 167 | 2144 | 322 | -0.2760 | +0.6165 | 156/-0.1653 | 115/-0.4771 | 51/-0.1611 |
| GBPNZD.vx | OK | 2468 | 82 | 58 | 2328 | 140 | -0.2031 | +0.6878 | 62/-0.0417 | 59/-0.3012 | 19/-0.4254 |
| GBPUSD.vx | OK | 2467 | 124 | 136 | 2207 | 260 | -0.2346 | +0.6638 | 98/-0.2295 | 111/-0.0836 | 51/-0.5727 |
| HK50.vx | OK | 2314 | 34 | 22 | 2258 | 56 | -0.1021 | +0.8165 | 37/+0.1075 | 9/-0.4724 | 10/-0.5441 |
| JPN225.vx | OK | 2371 | 287 | 297 | 1787 | 584 | -0.0972 | +0.8486 | 236/-0.1660 | 168/-0.0133 | 180/-0.0852 |
| LTCUSD.vx | OK | 2489 | 0 | 0 | 2489 | 0 | — | — | 0/— | 0/— | 0/— |
| NAS100.vx | OK | 2438 | 254 | 289 | 1895 | 543 | -0.1997 | +0.7088 | 185/-0.3359 | 201/-0.2155 | 157/-0.0189 |
| NZDCAD.vx | OK | 2470 | 4 | 6 | 2460 | 10 | -0.4538 | +0.3824 | 0/— | 7/-0.2068 | 3/-1.0300 |
| NZDCHF.vx | OK | 2470 | 5 | 5 | 2460 | 10 | -0.3544 | +0.3890 | 4/-0.3933 | 6/-0.3285 | 0/— |
| NZDJPY.vx | OK | 2471 | 16 | 27 | 2428 | 43 | -0.1590 | +0.7629 | 12/-0.5859 | 29/+0.0777 | 2/-1.0300 |
| NZDUSD.vx | OK | 2466 | 16 | 17 | 2433 | 33 | -0.6414 | +0.2513 | 2/-0.5695 | 27/-0.5762 | 4/-1.1174 |
| SP500.vx | OK | 2450 | 12 | 22 | 2416 | 34 | -0.2645 | +0.6159 | 14/-0.3325 | 11/-0.0199 | 9/-0.4578 |
| UK100.vx | OK | 2438 | 9 | 16 | 2413 | 25 | -0.2268 | +0.6762 | 1/+1.7700 | 13/-0.0539 | 11/-0.6127 |
| US30.vx | OK | 2402 | 302 | 289 | 1811 | 591 | -0.0717 | +0.8890 | 226/-0.1251 | 188/-0.0084 | 177/-0.0707 |
| USDCAD.vx | OK | 2465 | 38 | 45 | 2382 | 83 | -0.4047 | +0.4520 | 22/-0.1874 | 44/-0.5063 | 17/-0.4229 |
| USDCHF.vx | OK | 2467 | 89 | 88 | 2290 | 177 | -0.3653 | +0.5032 | 49/-0.3162 | 82/-0.4318 | 46/-0.2992 |
| USDJPY.vx | OK | 2465 | 101 | 140 | 2224 | 241 | -0.3051 | +0.5806 | 119/-0.1843 | 86/-0.4063 | 36/-0.4625 |
| XAGEUR.vx | OK | 2453 | 114 | 147 | 2192 | 261 | -0.1398 | +0.7865 | 80/-0.3474 | 142/-0.1276 | 39/+0.2417 |
| XAGUSD.vx | OK | 2454 | 135 | 171 | 2148 | 306 | -0.2824 | +0.6070 | 75/-0.3120 | 141/-0.2386 | 90/-0.3263 |
| XAUEUR.vx | OK | 2453 | 279 | 280 | 1894 | 559 | -0.1368 | +0.7993 | 222/-0.1882 | 196/-0.0493 | 141/-0.1772 |
| XAUUSD.vx | OK | 2457 | 285 | 331 | 1841 | 616 | -0.1333 | +0.8002 | 258/-0.0766 | 188/-0.1180 | 170/-0.2362 |
| XBRUSD.vx | OK | 2390 | 28 | 33 | 2329 | 61 | -0.5945 | +0.2973 | 0/— | 53/-0.5816 | 8/-0.6800 |
| XNGUSD.vx | OK | 2423 | 0 | 0 | 2423 | 0 | — | — | 0/— | 0/— | 0/— |
| XPDUSD.vx | OK | 2446 | 0 | 0 | 2446 | 0 | — | — | 0/— | 0/— | 0/— |
| XPTUSD.vx | OK | 2450 | 0 | 0 | 2450 | 0 | — | — | 0/— | 0/— | 0/— |
| XRPUSD.vx | OK | 2492 | 0 | 0 | 2492 | 0 | — | — | 0/— | 0/— | 0/— |
| XTIUSD.vx | OK | 2444 | 24 | 28 | 2392 | 52 | -0.4257 | +0.4627 | 0/— | 40/-0.5725 | 12/+0.0635 |

## Rekap seluruh entry multipair per bulan

Penjumlahan R **bukan** return akun, karena modal, ukuran kontrak dan exposure bersamaan tidak dimodelkan.

| Bulan | Trade | Avg R | Total R | Pair dengan entry |
|---|---:|---:|---:|---:|
| 2024-09 | 15 | +0.3883 | +5.8243 | 2 |
| 2024-10 | 20 | -0.1052 | -2.1039 | 2 |
| 2024-11 | 6 | -0.0967 | -0.5800 | 2 |
| 2024-12 | 7 | +0.0567 | +0.3966 | 2 |
| 2025-01 | 8 | -0.9327 | -7.4614 | 2 |
| 2025-02 | 10 | -0.2618 | -2.6176 | 2 |
| 2025-03 | 15 | +0.0822 | +1.2327 | 3 |
| 2025-04 | 25 | -0.4756 | -11.8899 | 4 |
| 2025-05 | 37 | +0.3151 | +11.6576 | 2 |
| 2025-06 | 67 | -0.1723 | -11.5433 | 3 |
| 2025-07 | 283 | -0.1197 | -33.8727 | 25 |
| 2025-08 | 451 | -0.3303 | -148.9888 | 30 |
| 2025-09 | 446 | -0.1947 | -86.8224 | 30 |
| 2025-10 | 606 | -0.1683 | -102.0173 | 34 |
| 2025-11 | 537 | -0.1118 | -60.0220 | 33 |
| 2025-12 | 552 | -0.2642 | -145.8467 | 32 |
| 2026-01 | 685 | -0.2579 | -176.6392 | 41 |
| 2026-02 | 712 | -0.2286 | -162.7736 | 37 |
| 2026-03 | 974 | -0.2220 | -216.2716 | 44 |
| 2026-04 | 516 | -0.1686 | -86.9828 | 41 |
| 2026-05 | 464 | -0.1437 | -66.6693 | 35 |
| 2026-06 | 487 | -0.1658 | -80.7548 | 35 |
| 2026-07 | 419 | -0.2171 | -90.9737 | 34 |
| 2026-08 | 341 | -0.2868 | -97.8007 | 28 |
| 2026-09 | 449 | -0.2466 | -110.7058 | 34 |
| 2026-10 | 178 | -0.1130 | -20.1103 | 31 |

## Mengapa KATARINA tidak entry?

Alasan WAIT paling banyak: entry_price_action_not_confirmed: 123,390, spread_excessive_relative_to_atr: 68,858, market_structure_not_resolved: 22,642, no_matching_playbook: 22,642, direction_uncertain: 22,642, scenario_reward_distance_too_small: 21,475.

## Batasan wajib disebutkan

- ONLY sampled one in every 36 M5 bars, not a bar-by-bar full scan.
- Historical news/blackouts are NOT verified. Signals are hypothetical assuming verified-clear news; actual safe decision is WAIT without archive.
- Retrospectively viewed 2025/2026 data are NOT a fresh independent out-of-sample validation.
- Broker MT5 timestamps are server time encoded in epoch fields; seasonal UTC/DST shifts not independently reconstructed.
- Entries use next M5 open and bar-recorded spread; hypothetical SL 1.2x M5 ATR, TP 1.8R, max 24 bars, extra .03R estimated cost.
- Same-bar stop+target is assumed stop-first; no true tick, swap, margin, commission reconciliation or severe slippage modeled.
- Independent trade sums are not account return; no portfolio correlation, exposure, overlapping positions or floating risk modeled.
- All outcomes are research-only, with no actual broker order or live-risk authorization.

## Keputusan

**Tidak ada promosi live.** Ini diagnostik menyeluruh untuk kualitas keputusan per pair; performa buruk/tidak cukup sampel harus dinyatakan gagal/belum terbukti.
File audit: per_pair.csv, monthly.csv, FINAL_SUMMARY.json. Bar mentah dan event individu tetap privat di VPS.