# Katarina V2.6 — koreksi seleksi setelah audit gap (research only)

Tanggal: 19 Oktober 2026. **Trading LIVE tetap OFF. Tidak ada perubahan source order/EA.**

## Kesalahan yang ditemukan

1. V2.4 memilih satu konfigurasi per pair memakai simulator yang menutup posisi pada jeda candle. V2.5 memperbaiki exit, tetapi tidak mengulang seluruh proses pemilihan memakai hasil simulator baru. Status `dev_pass` lama jadi tidak valid.
2. Fallback diagnostik `n_complete`/jumlah eksekusi pada keseluruhan dataset berpotensi memasukkan data review 2024–2026 ke pemilihan **ketika tidak ada kandidat development yang valid**. V2.6 hanya memakai jumlah entry **2022 dan 2023** untuk fallback; fallback tetap `ABSTAIN`, bukan trade.
3. Dua tahun rata-rata positif dan 20 entry/tahun belum cukup sebagai bukti edge, apalagi setelah mencoba 144 konfigurasi per pair. Biaya proxy dan lintasan harga saat sesi tutup masih tidak pasti.

## Eksperimen per pair dengan **anggaran sama, strategi berbeda**

- Delapan pair: XAUUSD, CADCHF, GBPCHF, AUDCHF, AUDNZD, EURGBP, AUDCAD, EURAUD.
- Setiap pair: **8 strategi asal miliknya sendiri × 2 ambang × 3 filter kondisi × 3 exit = 144**, total **1.152**.
- Perbandingan **Januari–September** pada 2022–2026, hanya 2022/2023 menentukan calon; 2024–2026 adalah review **yang telah dipakai berkali-kali**, bukan holdout murni.
- Dengan simulator yang membiarkan posisi melewati jeda sesi, 4/8 pair lolos syarat nominal pengembangan (XAUUSD, AUDCHF, AUDNZD, EURAUD). **0/8** lolos pemeriksaan ketat tambahan: batas bawah bootstrap bulanan >0 pada kedua tahun development serta hasil bertahan pada skenario gap adversarial. Ini adalah stress bound, bukan simulasi tick sebenarnya.
- Dalam review Jan–Sep 2026, 7/8 kandidat terpilih ulang memiliki rerata net model negatif, XAUUSD hanya sekitar **+0,020R** sebelum tambahan biaya, dengan ketidakpastian besar.
- Shadow watchdog dengan rata-rata 8 trade virtual sebelumnya dan downsize 1% → 0,25% dapat menurunkan drawdown simulasi sebagian pair, tetapi tidak membuktikan return positif/target 10–35% tiap bulan. Tidak boleh dipromosikan sebagai kemampuan live.
- Data dasar OHLC H1 memiliki volume=0; harga bid/ask tick, komisi, swap, slippage, margin dan harga intragap belum diverifikasi.

## Perlindungan di PR ini

`research/safety/reselection_guard.py` adalah pemilih deterministik **khusus penelitian**, tidak terkoneksi order, dan tidak mengubah strategi utama. `tests/research/test_reselection_guard_v26.py` memeriksa pemisahan dev/review, fallback tanpa lookahead, dan bahwa bahkan seluruh pemeriksaan terlewati **tidak mengotorisasi live trading**.

Sebelum sebuah strategi dipromosikan tetap diperlukan: broker true-tick bid/ask yang direkonsiliasi, kalibrasi biaya per pair, data prospektif setelah parameter dikunci, verifikasi drawdown nyata, review branch protection dan persetujuan eksplisit pengguna. Jangan menggunakan rasio profit dari backtest sebagai proyeksi keuntungan.
