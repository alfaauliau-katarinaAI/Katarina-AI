# Katarina AI — D10-K27: inspeksi langsung data asli XAUUSD.vx dari terminal MT5 yang sudah aktif

**Tanggal:** 5 November 2026 WIB · **Jenis:** actual broker feed / historical **read-only evidence** · **Pengambil:** Yura via Remote Desktop Commander pada terminal MT5 yang telah berjalan · **Status:** `SAMPLE_AVAILABLE`, **belum** `FULL_DATASET_VERIFIED`, **belum** backtest.

## Izin dan batas

Owner secara eksplisit meminta **riset dengan data asli** dan mengizinkan memakai **MT5 yang sama**, mengubah keputusan D10-K26 sebatas inspeksi market data read-only. Akses memakai satu `terminal64.exe` yang sudah berjalan; Python MetaTrader5 `initialize(path=existing_terminal,timeout=4000)`, pemanggilan hanya `terminal_info, account_info, symbol_info, copy_ticks_from, copy_rates_range`, lalu `shutdown()`. **Tidak** memanggil `order_send`, `order_check`, `positions` mutation, memasang/menjalankan EA/MQL5 script, meluncurkan MT5 kedua, menulis file observer, mengubah kode, menulis registry, atau membaca holdout untuk riset P/L.

**Keadaan terminal saat inspeksi:** `terminal_info.connected=True`, `terminal_info.trade_allowed=False`, mode akun `ACCOUNT_TRADE_MODE_DEMO`. Data berasal dari feed broker pada terminal demo, **bukan trade live beruang nyata**, namun BID/ASK historis asli yang ditarik dari MT5 tersebut. Nama server/nomor akun/log mentah sengaja tidak dipublikasikan di repo.

## Hasil pemeriksaan BID/ASK historis sebelum cutoff

Sumber: `MetaTrader5.copy_ticks_from(XAUUSD.vx, from_datetime_UTC, 1200, COPY_TICKS_ALL)`; setiap request dimulai **12:00 UTC** pada tanggal tabel. `time_msc` bersumber dari feed MT5; klaim bahwa offset historis benar terhadap UTC **belum lolos bukti jam independen**.

| Tanggal | Tick | Timestamp tick pertama–terakhir menurut MT5 (UTC) | Spread median | Min–maks spread | Duplicate `time_msc` | ASK<=BID |
|---|---:|---|---:|---:|---:|---:|
| 2026-09-15 | 1.200 | 12:00:00.161–12:03:47.320 | 0.29 | 0.29–0.33 | 0 | 0 |
| 2026-09-30 | 1.200 | 12:00:00.092–12:03:58.139 | 0.29 | 0.29–0.33 | 0 | 0 |
| 2026-10-08 | 1.200 | 12:00:00.040–12:03:52.657 | 0.29 | 0.29–0.33 | 0 | 0 |
| 2026-10-12 | 1.200 | 12:00:00.020–12:04:38.346 | 0.29 | 0.29–0.33 | 0 | 0 |

**Total empat window:** **4.800 tick**; tidak ada duplicate millisecond timestamp *di dalam masing-masing sampel* dan tidak ada nonpositif spread pada sampel. Spread **dalam unit harga XAUUSD**, poin broker `0.01`: 0.29–0.33 unit harga = 29–33 point. **Bukan** statistik sepanjang hari/tahun atau bukti harga benar pada event trading.

SHA-256 atas `numpy.ndarray.tobytes()` yang dikembalikan MT5 pada request 1.200 tick tersebut (hasil fetch ulang, dihitung in-memory; **raw files tidak diarsipkan** sehingga hash di bawah bukan bukti arsip dataset final):
- 15 Sep: `788cce1199ce65f07acd530f25ff1ecb24a44273750fad81cffc06873bbc370c`
- 30 Sep: `cb8c09dbdba1803610afd30989dfe85ed90d839443c2bfdadc6930cb2923495e`
- 8 Okt: `b928d506f819a14a2a38d986651601a137a3c4605390213cbdcf5ddb797e30e1`
- 12 Okt: `6b324950f20d5b476b810e57799d77f0374e210f5c5c2f378acfdd37bd6b7ddc`

### Batas historis yang diuji

- Query **100 tick** dari `2026-01-15T12:00:00Z` dan `2026-04-15T12:00:00Z` **tidak mengembalikan data pada tanggal permintaan**; dua-duanya justru dimulai pada `2026-06-04T01:00:01.873Z` menurut `time_msc` MT5. **Jangan** menganggap tick Jan–Apr tersedia; earliest yang teramati dalam pencarian ini Juni 4, bukan bukti broker secara keseluruhan hanya memiliki sejak Juni.
- Query `copy_rates_range(TIMEFRAME_M5)` pada jendela 12:00–13:00 UTC untuk **15 Jan, 15 Apr, 15 Jul, dan 8 Okt 2026** masing-masing mengembalikan **13 bar** termasuk batas akhir. MT5 memberi OHLC historis untuk Jan/Apr, tetapi **bar saja tidak cukup** untuk kontrak tick replay D10-K23; bar akhir 13:00 belum tentu sudah tutup pada timestamp permintaan dan tidak boleh dipakai sebagai sinyal lookahead.
- Jadi **data tick XAUUSD.vx development sebagian tersedia langsung di terminal** dan data OHLC lebih tua tersedia; **kelengkapan per-tahun/per-jam, gap, clock, sequence order, dan sumber biaya belum terbukti**.

## Snapshot simbol dari `symbol_info(XAUUSD.vx)` (waktu audit)

| Field | Snapshot |
|---|---:|
| `digits`, `point`, `trade_tick_size` | 2, 0.01, 0.01 |
| `trade_contract_size` | 100.0 |
| `trade_stops_level` | 31 point = 0.31 unit harga |
| `trade_freeze_level` | 0 point |
| `spread` | 29 point pada waktu snapshot, **tidak konstan** |
| `volume_min`, `volume_step` | 0.01, 0.01 |
| `swap_long`, `swap_short`, `swap_mode` | −23.7, 0.0, 1 (nilai MT5; **belum dijadikan biaya USD/posisi tanpa konversi/sumber**) |
| `swap_rollover3days`, `currency_profit` | 3, USD |
| `trade_tick_value` | 1.0 dalam snapshot simbol, sesuai kontrak perlu diverifikasi terhadap server dan tanggal efektif |
| `trade_allowed` terminal | False |
| Jenis akun | Demo |

**Implikasi teknis:** SL struktural + buffer yang telah disetujui juga harus lolos validasi `trade_stops_level=31` point pada kondisi broker; jangan memindahkan SL otomatis demi memenuhi broker jika melanggar desain. Bila invalid, hasil `WAIT:INVALID_BROKER_STOP_GEOMETRY`. Komisi, biaya swap per lot/rollover, slippage, dan sesi resmi Quote/Trade **belum lengkap** walau metadata awal berhasil diambil.

## Status evidence gates sesudah riset asli

| Gate | Status baru |
|---|---|
| E1 tick historical | **PARTIAL_OBSERVED** untuk empat window Sep/Oct pre-cutoff dan beberapa tanggal lebih awal; **FULL_DEVELOPMENT_ARCHIVE_UNVERIFIED** |
| E2 broker symbol specs | **CURRENT_SNAPSHOT_OBSERVED**; model komisi/slippage/swap historis masih **UNVERIFIED** |
| E3 quote & trade session resmi | **MISSING**; gap tick bukan jadwal broker. MQL5 session probe **belum dijalankan** |
| E4 host isolation | Owner mengizinkan pembacaan dari terminal produksi yang sudah aktif untuk bukti; **research-execution host isolation belum disetujui/terbukti**, exporter development lama **tidak dijalankan** |
| E5 split/costs/source frozen | **UNVERIFIED**; sampel tidak disimpan sebagai dataset ber-manifest |
| G8 simulator keenam kandidat | **NOT IMPLEMENTED**; `main` masih simulator OHLC/TP RR lama. **Tidak ada win rate, PF, DD atau klaim edge** |

### Kelanjutan yang masuk akal tanpa melanggar batas

1. Audit sumber tick historis **sebelum cutoff 2026-10-13** secara berbatas/sumber asli dan buat manifest ke penyimpanan bukti privat, dengan **persetujuan terpisah sebelum pengambilan batch besar** yang berpotensi membebani VPS 2GB.
2. Peroleh broker actual session `SymbolInfoSessionQuote/Trade` via probe read-only yang disetujui untuk terminal aktif (belum dijalankan), serta fee/swap/komisi berdasarkan jenis akun & tanggal historis.
3. Verifikasi offset server→UTC historis dengan sumber independen, report gap/coverage, `costs.json`, `split.json`, kemudian ajukan izin pengembangan simulator offline. Jangan membuka holdout.
4. **Tidak** memakai arsip observer 22 Okt–3 Nov 2026 sebagai development sebelum 13 Okt; tetap `HOLDOUT_LOCKED`.

`D10-K27_REAL_MT5_READ_ONLY_INSPECTION` · `FOUR_REAL_TICK_WINDOWS_OBSERVED` · `SOME_HISTORICAL_BARS_AVAILABLE` · `COST_MODEL_UNVERIFIED` · `SESSIONS_NOT_VERIFIED` · `NO_BACKTEST` · `NO_ORDERS` · `HOLDOUT_LOCKED`.
