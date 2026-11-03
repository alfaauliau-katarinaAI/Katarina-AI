# Bukti sesi quote/trade per simbol — prosedur aman

**Status:** collector read-only siap secara kode, *jadwal sesi broker belum diambil*. Ini bukan otorisasi untuk mengubah Stage0 dan tidak termasuk deployment otomatis.

## Mengapa diperlukan

Audit 3 November mendapati 128/136 siklus bermasalah di jam ketika arsip tick XAUUSD.vx dan NAS100.vx tidak memiliki tick, bergeser 21:00 UTC sebelum berakhirnya DST AS ke 22:00 UTC sesudahnya. Jeda tick yang diamati **bukan otomatis bukti jadwal broker**. Instrumen forex lain masih dapat berquote; aturan tunggal untuk semua simbol terlalu kasar.

Platform MQL5 menyediakan fungsi *terpisah* untuk mengambil sesi **quote** (`SymbolInfoSessionQuote`) dan **trade** (`SymbolInfoSessionTrade`). Keduanya mengembalikan detik dari tengah malam dalam **waktu sesi broker**, bukan jam UTC. Maka, offset server, pergantian DST, dan tanggal efektif perlu dibuktikan terpisah sebelum mengubah aturan validasi.

## Alat

- Source: `tools/diagnostics/mt5/KatarinaBrokerSessionProbe.mq5`.
- **Disimpan di luar inventaris kode deployable** agar tidak ikut secara tidak sengaja saat rilis. Hanya memanggil `AccountInfoString`, `TimeTradeServer`, `TimeGMT`, `SymbolExist`, dan `SymbolInfoSessionQuote/Trade`; tidak memanggil `OrderSend`, `CTrade`, `WebRequest`, tidak mengubah konfigurasi, dan tidak memasang EA.
- Default lima simbol pengamatan: XAUUSD.vx, NAS100.vx, EURUSD.vx, GBPUSD.vx, USDJPY.vx.
- Mengeluarkan baris log lokal bertanda `KATARINA_SESSION_PROBE` dan `KATARINA_SESSION`, baik bila ada sesi maupun jika data tidak tersedia. **Tidak membuat keputusan open/closed jika data tidak ditemukan.**
- Syntax check MetaEditor Windows VPS (isolated path) **0 errors, 0 warnings**. Full compile berhasil, `EX5` sekitar 13 KB dalam folder staging terisolasi. **Belum dipasang atau dijalankan pada MT5 produksi.**

## Prosedur mengambil bukti dengan aman

1. Setelah Owner menyetujui penangkapan bukti, tempatkan hasil build script pada folder `MQL5/Scripts` terminal yang sedang terhubung; jangan jalankan terminal MT5 kedua di VPS RAM 2 GB.
2. Jalankan **satu kali secara manual** pada chart yang sudah ada, saat server sesuai konfigurasi privat. Script hanya membaca konfigurasi sesi dan menulis hasil ke log lokal; tidak mengubah posisi trading.
3. Simpan log lengkap di penyimpanan privat VPS. Beri timestamp, broker server, nama simbol, daftar sesi quote dan trade per hari, serta bukti waktu server dan UTC. **Jangan unggah log mentah dengan informasi akun ke GitHub**.
4. Bandingkan jam sesi server, batas perpindahan DST, dan arsip tick nol untuk Oktober–November. Periksa pula perubahan jadwal khusus hari libur secara terpisah.
5. Reviewer memvalidasi bukti dan menyetujui jadwal sesi tiap simbol. Bila tidak ada sesi/ada ambiguity, status **UNVERIFIED**, jangan buat jam fiktif.
6. Bila kemudian Owner menyetujui perubahan Stage0, terapkan hanya untuk **observasi masa depan** (UTC effective_at), tanpa mengubah status kegagalan lama, bukti tick, atau ambang 98% dan 10 hari.

## Guardrail

- Script ini hanya alat pendeteksi bukti; tidak boleh otomatis dipanggil pada observer atau scheduler.
- Output `TimeTradeServer` dan `TimeGMT` adalah snapshot waktu terminal yang tidak menggantikan verifikasi broker-clock independen.
- Sesi quote dan trade tidak sama; jadwal trading dapat berubah oleh broker/hari libur. Tidak adanya tick bisa berarti kondisi feed lain, bukan selalu sesi tutup.
- Jika data sudah tersedia, perubahan lanjutan dilakukan melalui PR terpisah, CI, review Claude, backup/rollback, dan persetujuan Owner; LIVE tetap OFF.

**Bukti rujukan internal:** [manager board #262](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/262), [review Claude #251](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/251), [audit 3 Nov #272](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/272).

**MQL5 referensi:** https://www.mql5.com/en/docs/marketinformation/symbolinfosessionquote dan https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade
