# Tahap 0 — survei seluruh simbol broker (research-only)

**Tujuan:** menemukan pasar yang patut diteliti tanpa memaksa entry pada
XAUUSD atau pasangan default. Ini pelengkap observer canonical, **bukan**
sub-sistem trading baru, bukan perubahan playbook, dan bukan kelulusan Tahap 2–4.

Kode: `katarina.intelligence.broker.market_discovery.discover_quote_batch`.

- Broker `symbols_get()` menentukan universe. Hanya mode BUY, SELL, atau FULL
  yang ikut dipindai; simbol dengan nama/akses tidak valid dilewati.
- Saat `KATARINA_DISCOVER_ALL_BROKER_MARKETS=1`, satu observer yang sudah
  ada menyurvei **12 simbol setiap siklus**. Antrean adil persisten memakai
  `continuous_research_lab.select_batch`; penelusuran seluruh broker
  berlangsung **bertahap**, bukan seluruh simbol dianalisis berat sekaligus.
- Untuk tiap simbol, gunakan tick broker dan 24 candle **M1 tertutup**.
  Bandingkan spread dengan median range M1 hanya untuk prioritas riset
  **deskriptif**, bukan prediksi peluang profit atau syarat entry.
  Tick yang usang, tidak sah, atau tidak didukung broker gagal tertutup.
- Hasil masuk `latest.json` dalam `broker_market_discovery`: jumlah
  pasar broker, yang disurvei, alasan penolakan, dan prioritas riset sementara.
  Tidak masuk catatan snapshot **Tahap 0** atau holdout, karena tick discovery
  tidak sama dengan pengamatan kausal pasar yang sudah diverifikasi.
- Analisis multi-timeframe yang ada dan batas **3 simbol** di VPS 2 GB
  **tidak berubah**. Modul pemeringkat belum digunakan untuk mengotorisasi
  transaksi. `LIVE OFF`, `DEMO OFF`, dan Risk Governor tidak disentuh.

**Perlu sebelum digunakan sebagai pemilih setup:** akumulasi sinyal berbasis
candle tertutup pada seluruh market; perbandingan BUY/SELL dan regime yang
divalidasi menurut Tahap 1–2; evaluasi biaya dan korelasi; strategi terdaftar
dan persetujuan Owner sebelum promosi ke demo. Syarat pengamatan 10 hari
bursa, verifikasi tick harian, dan gerbang holdout tidak berubah.

**Uji sebelum aktif di VPS:** jalankan unit test discovery, integration
observer yang ada, audit keamanan/CI; nyalakan flag hanya setelah pengukuran
beban satu-siklus aman di VPS. Nonaktifkan flag untuk rollback instan bila
pengamatan canonical terpengaruh.
