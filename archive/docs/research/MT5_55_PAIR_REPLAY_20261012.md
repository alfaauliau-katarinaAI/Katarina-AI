# KATARINA — MT5 multi-pair replay (12 Oktober 2026)

**Status: SELESAI DIUJI, TIDAK LOLOS UNTUK LIVE.**

Riset ini dikerjakan di VPS Windows menggunakan MT5 dengan trading otomatis dinonaktifkan. Source versi GitHub yang digunakan tersedia pada commit [40ef9c5](https://github.com/alfaauliau-katarinaAI/Katarina-AI/commit/40ef9c59f9fe615ec34608867cdb211a7b286cad).

## Cakupan

| Komponen | Hasil |
| --- | ---: |
| Instrumen broker | 55 |
| Candle MT5 M15 yang diekspor | 275.000 (5.000 per simbol) |
| Timeframe | M15, M30, H1 |
| Instrumen × timeframe | 165 |
| Kombinasi model dievaluasi | 23.760 |
| Tidak ada kandidat pengembangan sesuai batas sampel | 69 |
| Gagal stabilitas/biaya stres/persyaratan sampel lanjutan | 96 |
| Lulus seluruh gerbang penelitian | **0** |

Strategi meliputi trend pullback, trend breakout, sideways range fade, RSI reversal, volatility breakout, liquidity sweep. Filter candle: tanpa tambahan, body kuat 55%, pin bar. Stop loss: 0,8/1,2 ATR; risk-reward 1,5/2,5; exit waktu setelah 8/16 candle.

Setelan dipilih pada 60% data awal secara kronologis. Evaluasi dilakukan pada 20% berikutnya, diagnostik pada 20% terakhir; untuk memilih kandidat dibutuhkan sedikitnya 8 transaksi pada data pengembangan. Biaya memakai spread historis OHLC dan asumsi 0,05R plus tambahan 0,10R saat stress test.

Tanggal histori berakhir 9 Oktober 2026, dengan tanggal mulai berbeda untuk setiap instrumen (pada sebagian simbol sekitar Juni–September 2026). Data ini sudah pernah dilihat pada riset lain, sehingga **bukan independent unseen out-of-sample**.

## Temuan contoh

- XAUUSD H1 trend breakout: rata-rata data pengembangan +1,142R dari 11 transaksi, tetapi segmen berikutnya -1,050R dan segmen terakhir minim sinyal.
- NAS100 M30 range fade: +0,978R pengembangan (13 transaksi), +0,935R pada segmen validasi, namun hanya +0,087R pada segmen terakhir sebelum biaya stres tambahan. Tidak memenuhi semua batas.
- GBPNZD H1 trend pullback: +1,253R pada delapan transaksi pengembangan, namun -1,050R pada evaluasi berikutnya.

Contoh dipilih sebagai ilustrasi, **bukan rekomendasi parameter**. Kinerja pengembangan tinggi dari sampel kecil sangat rentan overfitting.

## Cara mengulang di GitHub

[GitHub Actions: KATARINA Strategy Replay](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/workflows/katarina-strategy-replay.yml) → Run workflow. Job GitHub-hosted menguji kode replay secara otomatis menggunakan CSV sintetis yang ada di repo, lalu mengunggah file JSON hasil ke Artifacts. Commit ulang file workflow, pengujian, fixture, atau engine replay juga memicu job.

**Batas kemampuan:** GitHub-hosted runner tidak tersambung ke MT5 VPS. CSV broker asli berukuran sekitar 18 MB disimpan lokal pada VPS di `C:\KatarinaDev\private-market-data\mt5_20261012_m15.csv` karena repository ini publik, dan hak redistribusi data broker belum dikonfirmasi. Untuk mengulang data asli tetap perlu VPS, atau runner privat yang diotorisasi dan dikonfigurasi dengan benar. Jangan menganggap CI sintetis sebagai bukti profit broker.

## Status risiko

- Tidak ada order dari script pengujian.
- Trading live tetap **OFF**.
- Tidak ada pengaturan produksi risk governor yang diubah.
- Semua strategi: **NO-GO live**, membutuhkan out-of-sample baru, true tick/ask-bid, slippage, swap, margin, batas lot, dan forward demo.
