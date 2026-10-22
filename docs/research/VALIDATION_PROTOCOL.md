# Protokol validasi Katarina (Tahap 1)

Diterbitkan 22 Oktober 2026 sebagai bagian dari [roadmap berbasis bukti](../ROADMAP.md). Alatnya:
`katarina.research.validation` dan CLI `scripts/research/validate_strategy.py`. Alat ini adalah satu-satunya hakim
untuk tahap berikutnya; laporan PASS hanyalah bukti riset dan tetap membutuhkan catatan promosi yang disetujui Owner
(`docs/governance/promotions/`).

Perintah `market-filter` menyiapkan eksperimen [Market Intelligence Tahap 2](MARKET_INTELLIGENCE.md)
di atas alat yang sama. Pengembangan alat ini boleh berjalan selama Tahap 0 mengumpulkan data;
laporan perbandingan pengembangan tidak memberi kelulusan tahap atau kewenangan trading.

## 1. Daftarkan sebelum menguji

- Setiap hipotesis didaftarkan di `registry.jsonl` **sebelum** diuji. Isi wajib: `name`, `symbol`, `side`
  (`BUY` atau `SELL`, satu sisi per hipotesis), `regime`, `playbook`, `rules`, `parameters`, dan sebaiknya
  `code_sha256`.
- ID hipotesis = SHA-256 dari definisi kanonik. Mengubah satu parameter berarti hipotesis **baru** dan percobaan
  baru. Mendaftarkan definisi yang sama dua kali tidak menambah percobaan.
- Registry dan catatan pembukaan holdout berantai hash; perubahan manual terdeteksi dan alat menolak bekerja.
- **Jumlah percobaan** = jumlah hipotesis di registry. Batas keyakinan dikoreksi Bonferroni: α = 0,05 / percobaan.

## 2. Pemisahan data

- `split.json` menetapkan periode pengembangan dan holdout berdasarkan tanggal sebelum data dilihat, plus daftar
  **CELAH** (`gaps`). Hash definisinya (`split_sha256`) ada di setiap laporan.
- Trade dimiliki periode tempat entry terjadi. Trade yang exit-nya melewati akhir periode, entry di CELAH, atau di
  luar periode ditolak. Posisi yang melintasi CELAH juga ditolak; baris CELAH dalam periode penilaian tetap
  masuk laporan penolakan, tidak dibuang diam-diam.
- Holdout program 70 sel (13 Okt 2026 – 30 Apr 2027) tetap mengikuti aturan roadmap; periode tanpa observer asli
  sejak 13 Okt dicatat sebagai CELAH, dan backfill tidak pernah dihitung forward.

## 3. Holdout terkunci

- Trade holdout hanya bisa keluar lewat `HoldoutVault.open` (`evaluate_holdout`): hipotesis harus terdaftar, periode
  holdout harus sudah selesai, pembuka dan alasannya wajib diisi, dan pembukaan dicatat di `holdout-openings.jsonl`.
- Satu hipotesis hanya boleh membuka holdout **satu kali**. Hipotesis yang diubah setelah melihat holdout adalah
  hipotesis baru dan harus menunggu holdout baru. Alat menolak hipotesis yang didaftarkan sesudah pembukaan
  sebelumnya jika rentang holdout bertumpang tindih, termasuk jika hash split berubah. Receipt lama tanpa
  rentang tanggal ditolak secara konservatif untuk hipotesis pasca-pembukaan.
- Laporan pengembangan tidak pernah membaca trade holdout.
- CLI holdout menunda pembacaan berkas trade hingga pemeriksaan selesai dan receipt pembukaan tersimpan.
  Kegagalan membaca berkas setelah receipt tetap menghabiskan pembukaan; jangan menghapus receipt untuk mencoba lagi.
- Gunakan berkas pengembangan dan holdout **terpisah**, registry dan ledger pembukaan yang sama secara berkelanjutan,
  serta satu proses penulis. Ledger berantai hash mendeteksi perubahan isi, tetapi bukan pengganti kontrol akses
  filesystem dan backup: penghapusan/penggantian seluruh ledger atau akses langsung berkas berada di luar batas alat.

## 4. Pencegahan kebocoran

Trade ditolak (dan laporan menjadi FAIL) jika: data yang dipakai keputusan lebih baru dari waktu entry
(`LOOKAHEAD_DATA_AFTER_ENTRY`), hasil diketahui sebelum exit, posisi tumpang tindih, ID ganda, sisi tidak sesuai
pendaftaran, atau harga tidak valid.
Hasil dengan `known_at` sesudah waktu laporan juga ditolak. Trade yang ditolak selalu menghasilkan FAIL,
termasuk ketika jumlah sampel holdout kurang dari 100; PENDING hanya berlaku pada sampel yang tidak rusak.
Waktu pendaftaran tidak boleh sesudah waktu evaluasi. Jika definisi mendaftarkan `code_sha256`, berikan
`--code-sha256` yang sama saat evaluasi; nilai hilang/tidak cocok ditolak sebelum membuka holdout.

## 5. Biaya dan R bersih

R kotor = arah × (mid exit − mid entry) / jarak stop. Biaya (dalam R) = (½ spread teramati saat entry + ½ spread saat
exit + 2 × slippage per sisi + komisi pulang-pergi) / jarak stop. Spread berasal dari ledger Tahap 0 atau tick broker;
slippage dan komisi ditetapkan di `costs.json` sebelum pengujian.

## 6. Pembanding

Setiap laporan memuat: tidak trading (0R), sisi acak dengan timing, exit, dan biaya yang sama (nilai harapan dan
simulasi deterministik), serta aturan tren sederhana (label `trend_side` kausal saat entry). Strategi harus
mengalahkan semuanya.
Label tren harus tersedia untuk **semua** trade yang diterima; pembanding kosong/sebagian tidak boleh dilewati
untuk menghasilkan PASS.

## 7. Statistik dan keputusan

- Expectancy bersih, profit factor, win rate, drawdown maksimum, jumlah trade, jumlah minggu.
- Batas bawah keyakinan 95% (dikoreksi jumlah percobaan) dengan bootstrap per blok mingguan; seed deterministik dari
  ID hipotesis, periode, dan hash pemisahan.
- Walk-forward pada periode pengembangan: lipatan 28 hari berurutan tanpa tumpang tindih.
- Pengembangan: PASS jika expectancy bersih > 0, mengalahkan semua pembanding, dan tidak ada trade ditolak.
- Holdout (gerbang promosi ke DEMO, Tahap 4): ditambah minimal **100 trade**, profit factor bersih **≥ 1,2**, dan batas
  bawah bootstrap > 0. Sampel kurang dari 100 di akhir holdout = **PENDING_INSUFFICIENT_SAMPLE**, tidak pernah PASS.
- Data dan kode yang sama selalu menghasilkan laporan identik (`report_sha256`). `write_report` mengembalikan hash
  berkas yang dipakai `validation.report_sha256` pada catatan promosi.
