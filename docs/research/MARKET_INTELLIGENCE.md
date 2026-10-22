# Tahap 2 — eksperimen filter Market Intelligence

Alat ini memungkinkan pengembangan **sekarang**, sambil Tahap 0 mengumpulkan data. Modul
`katarina.research.market_intelligence` dipanggil oleh CLI validasi yang sudah ada; bukan observer,
worker, atau otak baru. Filter runtime aktif tidak berubah. Kelulusan tahap dan kenaikan kewenangan
tetap berurutan sesuai [roadmap](../ROADMAP.md).

## Alur kerja

1. Pilih hanya dataset **pengembangan** yang periodenya ditentukan sebelum pengujian. Simpan berkas
   holdout terpisah; jangan berikan berkas holdout pada perintah ini. Backfill tetap data historis,
   bukan bukti forward Tahap 0.
2. Siapkan `split.json`, `costs.json`, dan definisi hipotesis sesuai
   [protokol Tahap 1](VALIDATION_PROTOCOL.md). Tambahkan `data_split_sha256` (nilai `DataSplit.sha256`)
   serta `parameters.market_filter` di bawah. Instrumen dan sisi BUY/SELL harus tunggal per hipotesis.
3. Daftarkan hipotesis **sebelum** menguji filter. Setiap perubahan threshold, jam, atau aturan
   menghasilkan ID baru dan menambah jumlah percobaan. Jangan memilih threshold memakai holdout.
4. Jalankan perbandingan. Alat Tahap 1 yang sama menilai kelompok lengkap dan kelompok yang lolos
   filter, dengan split, biaya, hipotesis, serta jumlah percobaan yang sama.

```bash
python scripts/research/validate_strategy.py register --workspace W --spec spec.json
python scripts/research/validate_strategy.py market-filter --workspace W --hypothesis ID \
  --trades development.jsonl --contexts contexts.jsonl --outcomes outcomes.jsonl \
  --code-sha256 HASH_KODE_TERDAFTAR
```

`--code-sha256` wajib cocok jika didaftarkan dalam definisi. Laporan ber-hash ditulis ke
`W/reports/market-filter-*.json`. Tidak ada koneksi broker, order, atau pembukaan holdout.
Registry dan ledger tetap tunduk pada ketentuan satu penulis dan kontrol akses di protokol Tahap 1.

## Parameter yang harus didaftarkan

Semua nilai eksplisit; tidak ada nilai default produksi atau pemilihan threshold otomatis.

| Field `parameters.market_filter` | Makna |
|---|---|
| `max_spread_r` | Maksimum spread entry / jarak stop |
| `max_cost_to_range` | Maksimum estimasi biaya pulang-pergi saat entry / range terdahulu |
| `min_atr_r`, `max_atr_r` | Rentang ATR terdahulu / jarak stop |
| `min_ticks_per_minute` | Minimum aktivitas tick pada jendela terdahulu |
| `max_context_age_seconds` | Usia maksimum konteks pada saat entry |
| `utc_hours` | Daftar jam UTC yang diperbolehkan (0–23, unik); aturan DST diputuskan sebelum eksperimen |

Estimasi biaya pada saat keputusan = spread entry + 2 × slippage per sisi + komisi pulang-pergi.
Spread exit tidak digunakan untuk memilih sinyal. Evaluasi hasil memakai biaya aktual entry/exit
melalui `CostModel` Tahap 1. Aktivitas tick hanya **proksi aktivitas pasar**, bukan kedalaman order book
atau bukti likuiditas eksekusi.

## Kontrak berkas input (JSON lines)

`development.jsonl` memakai skema `Trade` Tahap 1. Berikan **seluruh** kelompok sinyal awal, termasuk
yang diperkirakan akan WAIT. Trade rusak, duplikat, overlap, memakai masa depan, atau masuk holdout
ditolak sebelum filter; WAIT tidak bisa menyembunyikan kesalahan data.

Setiap baris `contexts.jsonl` memakai field berikut:

```json
{"trade_id":"contoh-1","symbol":"XAUUSD","window_start":"2026-01-05T07:50:00+00:00","observed_at":"2026-01-05T08:00:00+00:00","range_price":10.0,"atr_price":5.0,"tick_count":100,"source_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
```

Angka dan hash di atas adalah **contoh sintetis**, bukan data broker atau parameter rekomendasi.
Range dan ATR dihitung dari candle yang sudah tutup, aktivitas dari tick broker, semuanya tersedia
paling lambat pada `observed_at <= entry_at`. `window_start` harus mencakup **seluruh lookback** yang
digunakan untuk range, ATR, dan tick. Jendela wajib berada di pengembangan dan tidak melintasi CELAH.
Range, ATR, spread, dan jarak stop memakai satuan harga instrumen yang sama.

`source_sha256` merujuk artefak sumber yang disimpan privat. Alat memvalidasi format dan merekam hash,
tetapi tidak mengunduh atau membuktikan keaslian sumber tersebut. Penghasil dataset bertanggung jawab
atas lineage, candle tertutup, kelengkapan tick, dan konversi waktu broker ke UTC. Konteks hilang
menghasilkan `WAIT_MISSING_CONTEXT` dan `INCOMPLETE_CONTEXT`, bukan bukti perbaikan filter.

### Menghasilkan `contexts.jsonl` dari data Tahap 0

`scripts/research/export_market_contexts.py` (logika di `katarina.research.context_export`) membangun baris
konteks dari file tick broker yang dikumpulkan ledger Tahap 0, dengan lineage yang bisa diperiksa:

```bash
python scripts/research/export_market_contexts.py --state-dir C:\Katarina\state\readonly-observer \
  --workspace W --symbol XAUUSD --trades development.jsonl \
  --lookback-minutes 60 --bar-minutes 5 --atr-bars 6 --output W/contexts.jsonl
```

- Hanya hari tick berstatus `STORED`/`STORED_WITH_GAPS` di `broker_tick_days` yang dipakai, dan SHA-256 isi
  file wajib sama dengan yang dicatat ledger (`TICK_FILE_HASH_MISMATCH` bila tidak).
- Hanya tick **sebelum** entry; `observed_at` = tick terakhir sebelum entry. Range dan ATR dari bar
  `--bar-minutes` yang sudah tutup; bar kosong memutus deret ATR, tidak diisi. `tick_count` = semua tick di jendela.
- Jendela yang menyentuh `data_gaps` tick broker, CELAH split, atau keluar dari periode pengembangan **tidak
  diberi konteks**; alasannya dicatat (`BROKER_TICK_GAP_IN_WINDOW`, `WINDOW_OUTSIDE_DEVELOPMENT_OR_IN_GAP`,
  `TICK_DAY_NOT_STORED`, `TOO_FEW_TICKS`, `INSUFFICIENT_COMPLETE_BARS`, `ZERO_RANGE`).
- `source_sha256` mengikat konteks ke hash file tick dan parameter ekspor. `<output>.manifest.json` mencatat
  sumber, sinyal tanpa konteks beserta alasannya, dan hash hasil. Database ledger dibuka read-only; output
  tidak boleh ditulis di dalam folder state observer.
- Parameter ekspor (lookback, bar, jumlah bar ATR) termasuk definisi eksperimen: tetapkan sebelum melihat hasil
  dan jangan dioptimalkan pada data yang sama.

Setiap baris `outcomes.jsonl` terpisah dari konteks keputusan:

```json
{"trade_id":"contoh-1","favorable_move_price":12.0,"known_at":"2026-01-05T09:00:00+00:00"}
```

`favorable_move_price` adalah maximum favorable excursion harga **mid** antara entry dan exit:
BUY memakai maksimum kenaikan, SELL maksimum penurunan; minimum nol. Gunakan jalur harga asli yang
lengkap, jangan menginterpolasi celah atau menganggap profit exit sebagai MFE. Nilai ini wajib tidak
lebih kecil daripada gerak menguntungkan pada exit. `known_at >= exit_at` dan tidak melebihi waktu
evaluasi. Outcome tidak pernah masuk fungsi pemilihan filter.

## Cara membaca laporan

- `decisions`: `KEEP_FOR_RESEARCH` atau WAIT, alasan dan metrik per sinyal. KEEP bukan izin entry.
- `wait_reasons`: jumlah alasan biaya/range, spread/risiko, sesi, volatilitas, aktivitas tick, atau konteks.
- `comparison`: jumlah sinyal, total biaya R, total MFE R, dan **sum(biaya R) / sum(MFE R)** untuk kedua kelompok.
  Rasio tak terdefinisi bila total MFE nol; itu bukan perbaikan. Kelompok yang sama persis tidak dianggap membaik.
- `stage1`: dua laporan lengkap (expectancy bersih, baseline, walk-forward, bootstrap, jumlah percobaan).
  Perbaikan rasio biaya saja tidak membuktikan expectancy positif atau strategi layak dipromosikan.
- `input_sha256`, `report_sha256`: reproduksi input dan hasil, termasuk outcome; waktu evaluasi yang sama
  diperlukan untuk hash identik. Urutan baris input tidak memengaruhi hasil.

Verdict `DEVELOPMENT_IMPROVEMENT` hanya menyatakan rasio kelompok terfilter lebih kecil pada dataset
pengembangan itu. Verdict lain: `NO_IMPROVEMENT`, `NO_DATA`, `INCOMPLETE_CONTEXT`. Tidak ada verdict
PASS promosi: `stage_clearance_granted`, `promotion_authorized`, `demo_execution_authorized`, dan
`live_execution_authorized` selalu false. Ini belum membuktikan efek pada data baru atau mengoreksi
pemilihan filter berulang di luar registry; semua percobaan harus dicatat.

## Status implementasi

Alat, CLI, dan tes sintetis siap diuji tanpa menunggu 10 hari bursa. Penilaian pada data pasar asli,
integrasi filter ke keputusan aktif, dan kelulusan Tahap 2 belum dilakukan. Ekspor konteks ber-lineage
(`export_market_contexts.py`) sudah tersedia; langkah berikutnya adalah mengumpulkan cukup hari tick Tahap 0,
menetapkan sinyal kandidat dan parameter ekspor, lalu mendaftarkan eksperimen sebelum menjalankannya.
Persiapan pembatas DEMO Tahap 3 juga dapat dikembangkan sambil observasi berjalan; nilai akhirnya
tetap memerlukan keputusan Owner seperti yang tercantum di roadmap.
