# Katarina AI — Kontrak eksekusi & spesifikasi simulator keenam kandidat

**Status:** dokumen teknis riset, **DRAFT**. Dibuat setelah keputusan Owner D10-K22. **Bukan perubahan kode eksekusi, bukan approval backtest/holdout atau izin order.**
Rujukan [spesifikasi enam kandidat](SIX_CANDIDATE_PREREGISTRATION_SPEC_20261104.md) dan [protokol validasi](VALIDATION_PROTOCOL.md).

## 1. G3 — Zona H1 yang disetujui Owner (D10-K22)

| Kunci | BUY B2 demand | SELL S2 supply | Status |
|---|---|---|---|
| Pemicu | H1 BOS **close >= confirmed swing high + tick_size** | H1 BOS **close <= confirmed swing low - tick_size** | APPROVED |
| Persyaratan BOS | Level swing sudah terkonfirmasi sebelum candle H1 BOS dimulai; min 1 tick | Sama | APPROVED |
| Origin | **Candle bearish H1 terakhir** dalam **12 candle H1 selesai sebelum BOS** | **Candle bullish H1 terakhir** dalam 12 H1 sebelum BOS | APPROVED |
| Batas zona | High dan low candle origin utuh **full wick**, bukan body | Sama | APPROVED |
| Lahir zona | Setelah candle BOS H1 selesai, bukan intrabar | Sama | Interpretasi causal wajib |
| Entry reaksi | Satu **M15 candle yang memuat first touch**, perlu menyentuh zona lalu bullish dan **close di atas high zona** | Sama, bearish dan **close di bawah low zona** | APPROVED |
| Target zona lawan | **Proximal edge supply = low zona supply** | **Proximal edge demand = high zona demand** | APPROVED |
| Usia & invalidasi | Maksimum **48 valid closed H1** sejak confirm; first visit only; breach hybrid tidak pernah fresh lagi | Sama | APPROVED dari D10-K9/K10 |

Tidak ada candle origin dalam 12 H1 sah → `WAIT:NO_VALID_ZONE_ORIGIN`. Jangan memilih candle lain setelah melihat P/L. Jika first-touch M15 close gagal, zona `CONSUMED`; bila breach distal+buffer sebelum entry, tak boleh membuka entry dan status breach diselesaikan oleh H1 close. Waktu `zone_confirmed_at = BOS_close_utc` harus memiliki rekam sumber. Referensi harga touch BID/chart OHLC, deteksi overlap zona, dan penanganan tick tepat batas M15 tetap **PROPOSED G4**, belum disahkan.

## 2. Eksekusi riset: pemisahan aturan dan bukti broker

### Kontrak keputusan yang telah didukung Owner

1. Semua keputusan struktur memakai **bar tertutup** dan timestamp `known_at <= decision_at`. Swing H1/M15: 2 kiri + 2 kanan, dengan `confirmed_at` setelah 2 bar kanan selesai. TTL swing M15 96 bar dan H1 72 bar; zona H1 48 bar. Candle hilang/gap bukan candle sah.
2. Entry: sinyal menjadi eligible hanya **sesudah close bar konfirmasi**, fill BUY di ASK dan SELL di BID pada quote eksekutabel berikut, dengan biaya aktual dan batas sesi sah. Tidak ada filled order di waktu sinyal jika quote tidak ada; tidak ada entry kembali dari setup yang sudah dikonsumsi.
3. SL BUY di bawah ekstrem struktur minus buffer; SL SELL di atas ekstrem plus buffer; buffer `ceil_to_tick(max(tick_size, spread_at_decision, .10*ATR14_Wilder(closed entry TF)))`. TP dipilih dari tingkat struktur sah terdekat yang menguntungkan relatif terhadap harga fill, **tanpa min RR**, tie newer `confirmed_at`, lalu stable id. Jika stop/TP invalid atau melanggar batas spesifikasi broker → `WAIT` dengan reason; **bukan** melonggarkan stop atau mendekatkan target setelah hasil diketahui.
4. B1/S1 time exit 12 fully completed M5 bar/90 menit UTC/15 min sebelum official close, B2/S2 12 M15/240 min/30 min, B3/S3 24 M5/180 min/20 min. Yang terjadi pertama membuat **exit intent**; fill hanya di quote yang benar-benar dapat dieksekusi. Jika tidak ada quote: `EXIT_PENDING_NO_QUOTE`, laporkan posisi belum tertutup. SL/TP yang sudah terjadi lebih awal menang.
5. Satu posisi aktif **per kandidat**, dengan reason saat sinyal duplikat. Sejauh ini belum ada izin melakukan netting/hedging portofolio antarkandidat dalam riset. Keputusan terhadap **interaksi antar-kandidat** diperlukan sebelum suatu simulasi gabungan, tetapi bisa tetap menilai setiap hipotesis terpisah sesuai protokol.

### G4 — Pilihan desain yang masih harus dibekukan

| Item | Usulan riset konservatif | Risiko jika tidak dibuat eksplisit |
|---|---|---|
| Harga referensi touch | **BID** untuk OHLC/zone first touch/breach konsisten dengan candle broker BID; fill dan exit memakai bid/ask aktual | BUY ASK menyentuh zona dulu tetapi chart BID belum: hasil sinyal berubah |
| Urutan SL/TP pada candle sama | Jika tick kronologis tidak tersedia, tandai `BLOCKED_INTRABAR_ORDER`, **jangan** pilih outcome lebih baik. Alternatif fallback konservatif SL-first butuh persetujuan eksplisit dan diberi label keterbatasan | OHLC M5 tidak membuktikan yang disentuh lebih dahulu |
| Pending exit | Setelah deadline, submit close pada **quote valid berikut**; jika sesi/trade tidak tersedia, terus open, biaya dan gap tetap tercatat | Menganggap deadline sebagai fill mengurangi DD artifisial |
| Saat candle terbuka di waktu fill | Hanya menghitung candle TF entry yang `open_utc >= fill_at_utc` dan `close_utc > fill_at_utc` | Bar parsial dihitung sebagai 1 penuh |
| Tick/spread invalid | Fail closed dengan reason, tidak mengasumsikan spread nol / quote sebelum waktu event | Fill/TP optimistis |
| Tabrakan event dengan timestamp sama | Gunakan urutan quote asli dan broker semantics; jika sama/unknown, tandai ambiguous; jangan gunakan future bar | Urutan event tak dapat dibuktikan |
| Antarkandidat | **Evaluasi enam hipotesis secara terisolasi** (per symbol+side+spec, satu posisi per kandidat), jangan menilai hasil portofolio atau mengarang kebijakan exposure gabungan | Simulasi satu kandidat terpengaruh sinyal kandidat lain |

**Status:** proposal G4 adalah rekomendasi teknis **BELUM dipilih Owner**. Perbedaan antara simulasi berbasis OHLC dan tick harus terlihat pada laporan. Secara historis, `src/katarina/research/setups/simulator.py::_exit` memakai konservatif stop-first pada same-bar OHLC, tetapi itu bukan bukti urutan tick.

## 3. G8 — Gap kode simulator nyata di `main` (audit read-only)

| Lokasi | Kondisi sekarang | Perubahan offline yang diperlukan |
|---|---|---|
| `src/katarina/research/setups/core.py::signal` | `target_rr` tetap dan `min_rr >= 0.01` | Target struktur causal; tidak menghapus peluang hanya karena RR kecil |
| `src/katarina/research/setups/simulator.py::simulate` | Memuat M5 dan H1 saja; setiap setup berada pada loop M5 | Gunakan M15,H1,M5 secara timestamp-as-of, tidak ada lookahead |
| `simulator.py::_exit` | `max_hold_bars` M5 dan OHLC stop-first | Hybrid bar/UTC/verified preclose, tick-order, status pending/no quote dan gap |
| `src/katarina/research/setups/liquidity_sweep.py` | Range M5, tanpa confirmed M15 swing reference | Sweep+reclaim satu M5 terhadap M15 pivot + TTL 96 + min 1 tick |
| `src/katarina/research/setups/pullback.py` | Mean pullback M5, bukan fresh H1 zone | Pembentukan zona 12 H1 / BOS+1 tick / full wick, finite-state first-visit dan M15 |
| `src/katarina/research/setups/market_structure.py` | M5 close-break immediate entry | Breakout H1 >=1 tick + one M5 retest within six |
| `src/katarina/research/validation.py` + CLI | Memiliki registry dan validator, tidak menyelamatkan aturan sinyal yang berbeda | Pertahankan hash ledger; pastikan input simulator adalah versi yang dipraregistrasi |

**Batas edit:** tidak ada perubahan terhadap `src/`, `scripts/`, MT5, VPS, `main`, ledger Stage0, `holdout`, atau strategi demo/live dalam rapat ini. Implementasi baru pada branch riset terpisah dan perlu audit/CI serta persetujuan sesuai roadmap.

## 4. Urutan pekerjaan untuk menutup G4/G8

- **C1 — keputusan Owner:** pilih metode data event (tick yang dapat diverifikasi vs fallback OHLC), side quote touch, dan apakah penelitian tetap independen enam kandidat; tanpa ini jangan menulis perilaku fill yang ambigu.
- **C2 — fixture independen tanpa P/L:** pivot 2+2 confirmed, pivot TTL boundaries (96/72), origin 12 H1, BOS satu tick, gap DST, first visit/candle M15, BOS H1+6 M5, ATR Wilder14 rounding, SL/TP collision, BUY ask/SELL bid, no quote, 3 preclose per candidate.
- **C3 — desain pure simulator contract:** input `dataset_manifest`, `clock_evidence`, `symbol_spec`, `quotes`, `session_calendar`, `candidate_spec`; output events (signal, wait reason, intended exit, actual fill, source timestamps). Version dan hash seluruh input; kode tidak memakai terminal production.
- **C4 — coding offline only** sesudah keputusan C1, tes deterministik/lint, review diff terhadap 6 spec; risk governor/observer tidak tersentuh. Jika data tick valid tak ada, output **BLOCKED** untuk klaim hasil yang membutuhkan tick; tidak boleh diam-diam turun menjadi OHLC-only.
- **C5 — freeze + preregister** hanya sesudah G1–G8 lengkap, official broker session evidence, data development/cost/split hash, `code_sha256` final; register 6 sebelum melihat P/L. Batas 5 hipotesis per simbol/sisi dan Bonferroni alpha=.05/N tetap.

## 5. Status

`D10-K22_ZONE_BASELINE_APPROVED` · `G3_CORE_APPROVED` · `G4_EXECUTION_DECISION_PENDING` · `G6_DATA_COST_UNVERIFIED` · `G7_OFFICIAL_BROKER_SESSIONS_MISSING` · `G8_SIMULATOR_NOT_IMPLEMENTED` · `NO_BACKTEST` · `REGISTRY_NOT_WRITTEN` · `HOLDOUT_LOCKED` · `LIVE_OFF`.
