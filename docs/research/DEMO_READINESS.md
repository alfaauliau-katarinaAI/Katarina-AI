# Persiapan Tahap 3 — batas DEMO dan laporan eksekusi

Tahap 3 dapat disiapkan sambil Tahap 0 mengumpulkan bukti. Modul
`katarina.research.demo_readiness` menyediakan adapter pembatas yang kompatibel dengan
`DemoExecutionBoundary` dan pembaca outbox demo yang sudah ada. Tidak ada worker, koneksi broker,
skema database, atau jalur kirim order baru. Runtime aktif dan berkas terkunci tidak berubah.

## Adapter risiko tambahan

`DemoRiskOverlay(governor, DemoRiskLimits(per_trade_fraction, daily_stop_fraction))`
memanggil governor yang diberikan **lebih dahulu**, lalu:

1. Mempertahankan keputusan REJECT/PAUSE beserta alasannya.
2. Menolak hasil governor atau bukti drawdown yang tidak valid.
3. Menghentikan entry baru bila DD harian mencapai batas DEMO.
4. Mengambil minimum anggaran yang disetujui governor dan batas per-trade DEMO.

Tidak ada nilai default. `0.005` per trade dan `0.03` DD harian hanya digunakan pada **tes sintetis**
sebagai usulan roadmap; nilai produksi final belum ditetapkan. Adapter tidak mengubah profil utama
atau batas 35%. Risiko yang disetujui lebih rendah tetap dipertahankan, termasuk pemangkasan oleh
governor karena exposure, ketidakpastian, kesehatan, dan rekonsiliasi.

Tes menghubungkan adapter ke `DemoExecutionBoundary` yang sama memakai broker palsu. Boundary tetap
memeriksa identitas akun demo, harga proteksi, lot, kerugian cash, freshness dan outbox. Adapter tidak
menaikkan lot minimum, mengirim order, atau mengganti keputusan exit. Jangan memasangnya pada worker
aktif sebelum nilai final, bukti validasi, persetujuan dan gerbang promosi yang relevan terpenuhi.

## Laporan outbox, sepenuhnya baca-saja

```bash
python scripts/research/check_demo_readiness.py \
  --outbox /private/demo-outbox.sqlite3 --currency USD \
  --regimes /private/regimes.json --decisions /private/decisions.jsonl \
  --output /private/demo-readiness.json
```

`--regimes` dan `--decisions` opsional. Sumber SQLite dibuka dengan `mode=ro`, `query_only=ON`, dalam
satu transaksi baca, lalu koneksi ditutup. Output tidak boleh menimpa salah satu input. Tidak ada
penulisan ke outbox, pengambilan posisi broker, atau pemanggilan rekonsiliasi dari CLI ini.

- Satu laporan harus memakai **satu outbox, satu akun, satu mata uang native**. `--currency` adalah
  deklarasi pemanggil karena outbox existing tidak menyimpan kolom mata uang; alat tidak memverifikasinya.
  Jangan mencampur USD dan akun cent atau mengonversi angka tanpa data kurs yang sah.
- `regimes.json`: objek privat `{ "intent-id": "TREND" }`; hanya ID yang ada pada outbox diperbolehkan.
  Label harus berasal dari snapshot keputusan saat entry. Tanpa label, regime ditampilkan null dan
  jumlah yang hilang dicatat; alat tidak menebak regime dari outcome.
- `decisions.jsonl`: satu baris per keputusan, misalnya
  `{"decision_id":"d1","action":"WAIT","reasons":["SPREAD_TOO_HIGH"]}`. Action BUY/SELL/WAIT,
  ID wajib unik, WAIT wajib memiliki alasan. Ini input terpisah karena WAIT tidak selalu masuk outbox.
  Jumlah baris disajikan agar ketiadaan input tidak disalahartikan sebagai nol WAIT sesungguhnya.

## Metrik dan batas interpretasi

- **Rekonsiliasi tersimpan:** OPEN/CLOSED/REJECTED/CHECK_REJECTED/CANCELLED/NOT_FILLED dianggap status
  terselesaikan menurut outbox. ACCEPTED, PARTIAL, UNKNOWN, status review atau status yang tidak dikenali
  tetap unresolved. OPEN/CLOSED memerlukan position ID unik; CLOSED juga memerlukan outcome valid,
  volume positif, minimal dua deal, dan flag hasil broker prospektif.
- Data kosong menghasilkan NO_DATA, bukan 100%. Outcome rusak atau posisi ganda tidak dihitung sebagai
  profit nol; keduanya dilaporkan sebagai masalah dan menghalangi rekonsiliasi COMPLETE.
- **Expectancy/profit factor/win rate:** hanya dari CLOSED valid. Net P/L sudah termasuk komisi, swap,
  dan fee broker; komponen biaya ditampilkan dengan tanda aslinya dan **tidak dikurangi lagi**.
  Tanpa loss, profit factor null dengan status NO_LOSSES; tidak dipaksakan menjadi angka tak hingga.
- **Drawdown:** penurunan P/L strategi terealisasi menurut urutan `closed_observed_at` (tie-break intent ID).
  Ini bukan equity drawdown akun, tidak memasukkan posisi terbuka, deposit/WD, atau mengklaim waktu fill
  historis yang tidak tersedia. Jangan gunakan angka ini sebagai input pengganti Risk Governor.
- **BUY/SELL per regime:** statistik dikelompokkan juga per simbol. `win_rate_net` adalah frekuensi hasil
  positif setelah biaya, bukan akurasi prediksi atau probabilitas terkalibrasi.
- **Slippage:** rata-rata entry slippage per simbol; positif berarti adverse. Sampel hilang dicatat,
  tidak diisi nol. Slippage antar simbol tidak dicampur karena satuan harganya berbeda. Spread telah
  masuk harga fill tetapi tidak tersedia sebagai komponen cash terpisah dari schema existing.
- Hash input/laporan deterministik untuk snapshot dan metadata yang sama. Laporan mengeluarkan agregat,
  tanpa login, server, nomor order, position ID atau intent ID mentah. Tetap simpan output secara privat.

COMPLETE hanya berarti seluruh baris snapshot memiliki status terselesaikan menurut aturan di atas,
**bukan audit broker terkini**. Laporan selalu menyatakan `stage_clearance_granted=false`,
`demo_execution_authorized=false`, `live_execution_authorized=false`.

## Status dan pekerjaan berikutnya

Adapter, laporan, CLI dan tes tersedia sebagai persiapan. Belum ada perubahan worker aktif,
pengiriman order demo nyata, penetapan profil final atau kelulusan Tahap 3. Kelulusan tetap memerlukan
bukti tahap sebelumnya dan rekonsiliasi broker nyata; pengembangan Tahap 4–5 bisa dipersiapkan paralel
tanpa memakai holdout atau menaikkan kewenangan.
