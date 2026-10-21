# KATARINA AI — Quant Research Evidence Registry & Prediction Audit
**Tanggal:** 11 Oktober 2026 WIB. **Mode:** READ_ONLY / `NO_TRADE`.
**VPS:** `C:\KatarinaDev\indicator-research`
**Branch:** `research/brain-forward-outcomes-20261010`.

## Mandat
Temukan pendekatan riset dan metodologi dari hedge fund publik, tokoh
kuantitatif, serta proyek open source; **himpun metode** dan pertahankan
hanya yang lolos bukti empiris Valetax per simbol. Rahasia perdagangan
fund tidak tersedia. Ide riset fund jangka panjang bukan scalping CFD
yang dapat disalin langsung. Tidak satu pun hasil di bawah berupa
transaksi benar-benar dieksekusi atau bukti payout trading.

## Sumber ditelaah dan keputusan katalog
1. **AQR — Hurst, Ooi, Pedersen**, "A Century of Evidence on
   Trend-Following Investing", 2017.
   https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing
   RETAIN RESEARCH: momentum trend lintas horizon, stabilitas
   risiko, diversifikasi. Jangan menyamakan hasil futures bulanan
   selama sejarah panjang dengan tick-scalping CFD M1.
2. **Man AHL — The Need for Speed in Trend-Following**.
   https://www.man.com/insights/need-for-speed-trend-following
   RETAIN RESEARCH: pisahkan kecepatan trend cepat/lambat.
   Dari sini KATARINA membandingkan horizon 1h vs 4h
   dengan split dan parameter yang dinyatakan, bukan mencari
   kebetulan skor terbaik secara post-hoc.
3. **Marcos López de Prado — purged validation, embargo,
   triple barrier, meta-labeling**.
   https://python.financial/concepts/purged-cross-validation/
   RETAIN VALIDATION: jangan gunakan outcome label train yang
   belum selesai ketika periode evaluasi dimulai; pasang 4h
   embargo tambahan; tidak otomatis menghapus seluruh bias
   jika dataset pernah dipakai dalam riset lain.
4. **Hudson & Thames — MlFinLab**.
   https://hudsonthames.org/mlfinlab/
   RETAIN FUTURE TEST: event sampling, triple-barrier,
   meta-labeling; belum diaktifkan atau dibuktikan broker-net.
5. **Microsoft — Qlib**.
   https://github.com/microsoft/qlib
   ENGINEERING REFERENCE: catatan eksperimen dan structured
   feature pipeline, bukan pindah VPS lama ke stack baru
   yang belum diuji kompatibilitasnya.
6. **QuantConnect — LEAN**.
   https://github.com/QuantConnect/Lean
   ENGINEERING REFERENCE: disiplin simulasi event-based
   dan eksekusi broker; jangan menambah infrastruktur
   tanpa manfaat pengujian yang terukur.
7. **Open source PurgedCV**.
   https://github.com/eslazarev/purged-cross-validation
   RETAIN VALIDATION: kode referensi pembanding implementasi
   purging dan walk-forward; kode berlisensi belum diimpor
   atau dipaketkan dalam KATARINA.

Register mesin yang dapat dibaca ulang:
`C:\KatarinaDev\artifacts\historical-brain\quant-evidence-registry-v2.json`
Mencatat referensi, keputusan, hasil skor, alasan dan
SHA256 berkas riset. Semua kode analitik ditulis mandiri.

## Hasil prediksi per simbol, leakage-aware
Input sumber: 9.687 observasi M5/M15/H1 sebelumnya dari
tujuh simbol Valetax, periode Aug 16–31, Sep 15–30,
Oct 1–9 UTC. Semua merupakan riwayat yang pernah
diteliti KATARINA; penyebutan train/test kronologis
TIDAK menjadikannya holdout prospektif benar-benar baru.

Dua pengujian per simbol:
- TRAIN Agustus → EVALUATE September.
- TRAIN Agustus+September → EVALUATE Oktober.
- Label future harga M5 close satu jam atau empat jam
  setelah snapshot; harga dan label yang resolusinya
  melampaui awal test berikut embargo 4h DIBUANG.
- Fitur: EMA trend direction, ADX Wilder, +DI / -DI,
  directional efficiency, sesi UTC sin/cos, dan
  kategori market regime. Model standardisasi dan
  regularized logistic fit **hanya dengan TRAIN**.
- Pembanding pertama adalah training-only base-rate
  harga naik; aturan model dan regularisasi tidak diubah
  antar simbol. Ini riset arah harga, bukan model broker
  TP/SL PnL dan bukan klasifikasi "regime ground truth".
- Skor probabilistik: **Brier score** (lebih rendah
  lebih baik), log loss dan accuracy sebagai metrik
  deskriptif. Accuracy nominal bisa terlihat membaik
  meski probabilitas model tidak terkalibrasi.

### Hasil rata-rata Brier tertimbang
| Metode | 1 jam (5.782 test) | 4 jam (5.548 test) |
| --- | ---: | ---: |
| Training-only baseline | **0,25004** | **0,25086** |
| Fitur teknikal saja | 0,26506 | 0,27778 |
| Kategori regime saja | 0,25195 | 0,25701 |
| Teknikal + regime | 0,26679 | 0,28043 |

Semua model baru kalah secara agregat dari baseline,
baik 1h maupun 4h. Pada 14 simbol-periode evaluasi 1h:
teknikal menang dari baseline pada 1; regime-only 1;
teknikal+regime 1. Pada evaluasi 4h: masing-masing
2/14, 3/14, dan 1/14. **Tidak ada kombinasi
simbol-model yang memperbaiki kedua fold.**

Pada XAUUSD 4h, teknikal+regime lebih baik daripada
baseline di Oktober (Brier 0,23182 vs 0,24943),
tetapi buruk di September (0,28016 vs 0,25011):
contoh ketidakstabilan, tidak boleh dipromosikan.

Auditor 1h dan 4h memeriksa label, tanggal resolusi,
purging, embargo, probabilitas train-only baseline
dan skor Brier/logloss dari 11.330 prediksi:
- `regime-prediction-purged-seven-symbols-v1.json`
- `regime-prediction-purged-seven-symbols-v1-audit.json`
- `regime-prediction-purged-seven-symbols-4h-v1.json`
- `regime-prediction-purged-seven-symbols-4h-v1-audit.json`

**Decision: REJECT PRODUKSI** model logistic versi ini.
Tetap simpan script, unit test, dan audit untuk diagnosa.

## Filter regime pada entry yang benar-benar spesifik per simbol
Sebagai langkah berikutnya, empat metode SETUP yang
sebelumnya dipisahkan per simbol diberi filter statis:
- NAS100 pullback/trend → hanya continuation atau pullback
  searah dalam konteks timeframe.
- XAUUSD sweep/rejection → sideways atau confirmed
  reversal ke arah entry.
- US30 failed opening-range breakout → sideways/reversal.
- JPN225 Tokyo range impulse → continuation searah.

As-of regime diambil pada/sebelum entry, maksimum umur
30 menit, tanpa mengintip timeframe masa depan.
Kejadian entry memakai replay TP/SL asli termasuk
bid/ask historis dan tambahan satu tick adverse
pada entry serta exit, jadi metriknya *simulated R*
bukan keuntungan kas terealisasi.

| Market | Jumlah entry asli | Mean R asli | Entry lolos regime | Mean R setelah gate |
| --- | ---: | ---: | ---: | ---: |
| NAS100 | 29 | +0,149 | 10 | +0,213 |
| XAUUSD | 345 | −0,264 | 22 | −0,243 |
| US30 | 28 | −0,001 | 2 | +0,190 |
| JPN225 | 21 | −0,079 | 1 | −1,004 |

Tidak ada filtered group yang mencapai minimum
30 transaksi/10 hari; satu atau dua transaksi menang
bukan bukti edge. XAU tetap rugi bahkan sesudah gate.
Catatan: NAS hanya mencakup Aug–Oct, tidak termasuk
Juli, karena arsip regime tidak memiliki Juli.

Hasil dan audit:
- `symbol-regime-gate-versus-raw-ticks-v1.json`
- `symbol-regime-gate-versus-raw-ticks-v1-audit.json`
- Audit 423 entry memeriksa timing as-of, fixed gate
  rules, origin family per simbol dan ulang metrik.

**Decision: KEEP REGIME AS RESEARCH CONTEXT,
REJECT AUTO-GATING TRADES FOR NOW.**

## Yang dipertahankan
- MTF closed-bar market regime dalam observer `NO_TRADE`.
- Strategi dan karakter biaya per broker symbol; bukan
  satu setup disalin ke semua simbol.
- As-of features dan data lineage immutable SHA256.
- Purged chronological testing, train-only standardisasi,
  score probabilistik vs baseline.
- Harga actual bid/ask tick & broker min-stop,
  tanpa menggandakan spread.
- Katalog keputusan: `RETAIN`, `REJECT`,
  `DEFER`, tidak ada promosi otomatis.

## Yang ditunda
- Triple barrier dengan titik sentuh bid/ask intratick,
  *meta-labeling* entry yang sudah memiliki arah dari
  strategi simbol spesifik.
- Kondisi calendar macro/news berdasarkan data *vintage*
  yang sungguh diketahui pada waktu kejadian.
- Footprint/CVD hanya bila tersedia transaksi volume
  aggressor nyata, bukan menamakan MT5 tick_volume
  sebagai order flow futures.
- Volatility normalization dan broker fee/slippage
  terukur dari eksekusi nyata, korelasi portofolio.
- Pengujian PROSPEKTIF setelah kode/threshold/model
  dibekukan, bukan mendaur ulang data lama sebagai OOS.

## Integrasi VPS dan risiko
- Operasi kode baru adalah lab riset dan registry;
  **tidak mengganti model prediksi live**, tidak
  mengirim order, tidak menaikkan spread gate aktif.
- Task `Katarina-MarketBrain-Observer` tetap dapat
  memantau 74 simbol. Seluruh usulan tetap research-only.
- `model_promotion_allowed=false`, `NO_TRADE`.
- Keputusan akhir: **kemampuan menguji dan menolak model
  meningkat; belum ada peningkatan prediksi yang
  terbukti secara konsisten**.

## Reproduce (script dari repo root VPS)
```text
python scripts/research/evaluate_regime_prediction_ml.py --horizon-hours 1 --report REGIME.json --output NEW1.json
python scripts/research/evaluate_regime_prediction_ml.py --horizon-hours 4 --report REGIME.json --output NEW4.json
python scripts/research/audit_regime_prediction_ml.py --report NEW1.json --source REGIME.json --output AUDIT.json
python scripts/research/compare_regime_gate_to_raw_setups.py --regime REGIME.json --strategies NAS.json GOLD_US30.json JPN.json --output NEW_GATE.json
python scripts/research/audit_symbol_regime_gate.py --report NEW_GATE.json --output AUDIT_GATE.json
python scripts/research/build_quant_evidence_registry.py --prediction NEW1.json --prediction-four-hour NEW4.json --gates NEW_GATE.json --output NEW_REGISTER.json
```
