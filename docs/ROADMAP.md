# Roadmap Katarina AI — berbasis bukti

Ditetapkan Owner (Project Manager) pada **22 Oktober 2026**; disempurnakan hari yang sama setelah review PM
(dua aliran data, paralel vs berurutan, celah holdout dan PENDING, profil DEMO vs Stage 38). Dokumen ini menjadi dasar pengembangan
Katarina berikutnya. Status harian ada di [PROJECT_STATUS](PROJECT_STATUS.md); aturan perapian di
[CLEANUP_PLAN](maintenance/CLEANUP_PLAN.md).

## Prinsip utama

> **Katarina boleh terus mencari ilmu tanpa batas, tetapi kewenangannya untuk mengubah keputusan trading
> harus bertambah berdasarkan bukti, bukan berdasarkan banyaknya pengetahuan.**

Masalah utama Katarina saat ini bukan kekurangan strategi atau kecerdasan, melainkan **belum adanya bukti**
bahwa keputusannya menghasilkan keuntungan bersih secara konsisten setelah biaya transaksi
(audit 13 Okt 2026: profit factor kandidat 0,36; backtest 2025–2026 tanpa playbook yang positif di kedua tahun).

## Empat keputusan Owner

1. **Validasi adalah hakim tertinggi.** Tidak ada strategi, hasil riset AI, atau perubahan parameter yang masuk
   ke sistem aktif sebelum lulus pengujian yang ditetapkan di dokumen ini.
2. **Manfaatkan arsitektur yang sudah ada.** Observer, Market Decision Brain, Risk Governor, antrean order demo,
   buku shadow prospektif, Neuro-Link, dan `self_evolution_lab` diperkuat — tidak dibangun ulang, dan tidak
   ditambah subsistem paralel.
3. **Belajar mandiri tetap boleh, tetapi dipisah dari kewenangan.** Menemukan pengetahuan, menguji hipotesis,
   dan menerapkan perubahan adalah tiga langkah terpisah. Katarina boleh menemukan pengetahuan baru tanpa
   otomatis mengubah strategi aktif.
4. **Batas drawdown harian 35% tidak diubah.** Profil DEMO menjadi lapisan pembatas tambahan yang hanya boleh
   lebih ketat. Sebelum akun riil, batas 35% wajib dievaluasi ulang memakai hasil pengujian.

## Tangga kewenangan

Kewenangan naik satu anak tangga hanya jika kriteria kelulusan tahap terkait terpenuhi **dan** Owner menyetujui.

| Level | Kewenangan | Syarat |
|---|---|---|
| 0 | Mengamati pasar, mencatat data, menulis kartu keputusan dan alasan WAIT | Berlaku sekarang |
| 1 | Mengusulkan hipotesis ke antrean riset | Tahap 1 lulus |
| 2 | Menguji hipotesis di shadow/paper dengan data pengembangan | Tahap 1 lulus |
| 3 | Mengirim order ke **akun demo** dengan profil DEMO | Tahap 0–3 lulus + strategi lulus gerbang promosi |
| 4 | Akun riil risiko mikro | Di luar roadmap ini: gerbang tersendiri (Stage 38) + otorisasi eksplisit Owner |

Katarina tidak pernah boleh menaikkan kewenangannya sendiri, mengubah kode trading, atau melonggarkan batas risiko.

## Paralel dan berurutan

Pengembangan boleh berjalan **paralel**: alat validasi Tahap 1 (dan persiapan tahap lain) boleh dibangun selama
Tahap 0 mengumpulkan data. Yang wajib **berurutan** adalah **kelulusan tahap dan pemberian kewenangan**. Pekerjaan
paralel tidak boleh membuka holdout, mengubah strategi aktif, atau melonggarkan Risk Governor.

## Pemisahan data

- **Periode pengembangan** dan **periode holdout** ditentukan berdasarkan tanggal sebelum data dilihat, dan
  dicatat di repo beserta hash definisinya.
- Holdout 70 sel yang dibekukan (periode 13 Okt 2026 – 30 Apr 2027, issue #29) **belum pernah terisi** karena
  observer tidak berjalan sejak 16 Okt; independensinya masih utuh dan wajib dijaga.
- Periode tanpa data observer asli — sejak awal holdout 13 Okt 2026 (observer berhenti 16 Okt dan datanya tidak
  lagi ada di VPS) sampai observer kembali aktif — dicatat sebagai **CELAH**, kecuali ada salinan data observer asli
  yang terverifikasi hash-nya untuk sebagian periode itu. Data riwayat yang diunduh ulang (backfill) untuk periode
  itu **tidak pernah** dihitung sebagai pengamatan forward.
- Jika sampai akhir periode holdout jumlah sampel belum memenuhi kriteria, hasilnya **PENDING** — tidak boleh
  dinyatakan lulus, diperpanjang diam-diam, atau dilengkapi dengan data dari periode lain.
- Holdout hanya boleh dibuka **satu kali per strategi yang sudah final**. Setiap pembukaan dicatat (strategi,
  tanggal, hasil). Hasil holdout tidak boleh dipakai untuk memilih, menyetel, atau memperbaiki strategi; strategi
  yang diubah setelah melihat holdout dianggap strategi baru dan harus menunggu holdout baru.
- Data yang dipakai riset otomatis (`self_evolution_lab`, Neuro-Link) hanya data pengembangan.
- Jumlah total percobaan (strategi/varian yang pernah diuji) dicatat, dan ambang kelulusan dikoreksi untuk jumlah
  percobaan tersebut.

## Gerbang promosi

Strategi atau perubahan parameter hanya boleh masuk ke sistem aktif jika:

1. Ada **catatan kelulusan** yang dihasilkan alat validasi (Tahap 1) untuk versi kode dan definisi strategi yang
   sama persis (hash), dan
2. Ada **persetujuan Owner** yang tercatat untuk catatan tersebut.

Penegakan oleh CI (berlaku sejak 22 Okt 2026):

- `config/promotion_lock.json` mengunci hash SHA-256 berkas yang menentukan keputusan dan risiko aktif: otak
  keputusan (`market_decision`, pipeline, contextual decision, explainable decision, adaptive observation),
  persepsi regime/struktur/setup/entry/exit, strategi demo, Risk Governor, risiko adaptif/manual/akun, batas
  eksekusi demo, gerbang risiko riset, serta `config/risk_governor_v2.json` dan `config/katarina_unified_v1.json`.
- Kunci harus menunjuk catatan promosi di `docs/governance/promotions/`. Catatan `PROMOTION` wajib memuat
  `validation.status = PASS`, laporan validasi yang ada di repo dengan hash cocok, dan `owner_approval`.
  Satu-satunya pengecualian adalah baseline `P-0000` (keadaan saat gerbang diperkenalkan, **bukan** klaim performa).
- Body CI menjalankan `python scripts/governance/promotion_gate.py --check` dan `tests/static/test_promotion_gate.py`;
  perubahan berkas terkunci tanpa catatan sah membuat CI gagal.
- Prosedur: (1) laporan validasi Tahap 1 untuk versi baru, (2) catatan promosi dengan persetujuan Owner,
  (3) `python scripts/governance/promotion_gate.py --write-lock <catatan>`, (4) PR seperti biasa.
- Menambah berkas ke daftar kunci boleh kapan saja; mengeluarkan berkas dari daftar memerlukan persetujuan Owner.

## Urutan pengembangan dan kriteria kelulusan

Angka di bawah adalah **nilai awal** yang ditetapkan 22 Okt 2026. Perubahan angka membutuhkan persetujuan Owner
dan dicatat di CHANGELOG. "Lulus" berarti semua kriteria terpenuhi dan dibuktikan dengan laporan yang dapat
direproduksi — bukan sekadar program berjalan atau backtest profit.

### Tahap 0 — Observer & pengumpulan data

Tujuan: data pasar dan eksekusi yang dapat dipercaya. Status ONLINE saja tidak cukup.

Ada dua aliran data yang **wajib dibedakan** dan disimpan terpisah:
- **Snapshot observer**: bid/ask/spread dan candle tertutup yang dibaca setiap siklus (60 detik). Dipakai untuk
  keputusan dan sebagai catatan apa yang Katarina "lihat" saat memutuskan. Ini **bukan** data tick.
- **Tick broker**: seluruh tick bid/ask dari riwayat MT5, diunduh per periode setelah periode itu selesai. Dipakai
  untuk riset biaya eksekusi, spread aktual, dan validasi.

Pekerjaan: login akun demo di MT5 VPS (Algo Trading OFF), konfigurasi koneksi privat, aktifkan observer read-only,
pengunduh tick broker per periode, dan pemeriksa kesehatan data untuk kedua aliran.

Alat (repo, 22 Okt 2026): `katarina.intelligence.operations.observation_ledger` mencatat setiap siklus observer
(tabel `observer_cycles`, `observer_quotes`, termasuk WAIT; kegagalan selalu dengan alasan) dan, dengan anggaran satu
simbol-hari per siklus, mengunduh tick broker hari UTC yang sudah selesai dan memang diamati ke
`<state>/broker-ticks/SIMBOL/YYYY-MM-DD.csv.gz` (`broker_tick_days`, celah di `data_gaps`, rekonsiliasi dengan
snapshot dalam satu tick size). `python scripts/ai/check_stage0_health.py --state-dir <state>` menilai kriteria di
bawah (PASS / NOT_MET / NO_DATA) secara read-only. Statistik siklus memakai jendela konservatif Senin 00:00 – Jumat
20:00 UTC tanpa rollover 20:45–21:15 UTC. Status tahap tetap **belum lulus** sampai observer berjalan di VPS.

Kriteria kelulusan:
- Observer berjalan **≥ 10 hari bursa berturut-turut**.
- **≥ 98%** siklus selesai tanpa error saat pasar buka; setiap kegagalan punya alasan tercatat.
- **0** catatan duplikat; timestamp naik monoton per simbol.
- Selisih jam broker vs jam VPS tercatat dan stabil (perubahan hanya saat pergantian DST yang terdeteksi).
- Bid, ask, dan spread tercatat di setiap siklus untuk setiap simbol yang diamati.
- Uji putus-sambung MT5 lulus **≥ 3 kali** tanpa data hilang atau ganda, dan observer pulih sendiri.
- Tick broker tersimpan untuk setiap hari bursa yang diamati; setiap **celah** (tick tidak tersedia, koneksi
  putus, server broker kosong) dicatat dengan rentang waktu dan alasannya — tidak pernah diisi interpolasi.
- Pemulihan celah diverifikasi: tick yang diunduh ulang setelah putus-sambung cocok dengan snapshot observer di
  waktu yang sama (bid/ask dalam toleransi satu tick size), dan hasil verifikasinya dicatat.
- 0 order terkirim.

### Tahap 1 — Validasi ilmiah

Tujuan: satu alat uji yang menjadi hakim untuk semua tahap berikutnya.

Pekerjaan: protokol pengujian tertulis; pendaftaran hipotesis sebelum diuji (definisi, instrumen, sisi BUY/SELL,
regime, hash); walk-forward; penguncian holdout yang ditegakkan kode; model biaya dari spread teramati plus
slippage dan komisi; pembanding baseline (tidak trading, entry acak dengan exit yang sama, aturan tren sederhana);
pencatatan jumlah percobaan.

Alat (repo, 22 Okt 2026): `katarina.research.validation` + `scripts/research/validate_strategy.py`, protokol tertulis
di [`docs/research/VALIDATION_PROTOCOL.md`](research/VALIDATION_PROTOCOL.md): registry hipotesis berantai hash (jumlah
percobaan), pemisahan pengembangan/holdout/CELAH ber-hash, `HoldoutVault` (dibuka sekali, tercatat), model biaya dari
spread teramati, penolakan kebocoran, tiga pembanding, walk-forward, bootstrap blok mingguan terkoreksi, laporan
ber-hash. Kriteria di bawah dibuktikan oleh `tests/unit/research/test_validation.py`.

Kriteria kelulusan:
- Hasil uji deterministik: dijalankan dua kali pada data dan kode yang sama menghasilkan angka identik.
- Holdout tidak bisa dibaca tanpa membuat catatan pembukaan (dibuktikan dengan tes).
- Kebocoran data dicegah: uji sengaja dengan informasi masa depan harus ditolak alat (dibuktikan dengan tes).
- Laporan selalu memuat expectancy bersih setelah biaya, interval keyakinan, jumlah trade, jumlah percobaan,
  dan perbandingan dengan semua baseline.

### Tahap 2 — Market Intelligence

Tujuan: Katarina tahu kapan pasar tidak layak ditradingkan, walau pola entry terlihat menarik.

Pekerjaan: perkuat filter yang ada (biaya terhadap range, rasio spread terhadap risiko) dengan spread aktual,
sesi pasar, volatilitas, dan likuiditas dari data Tahap 0.

Kriteria kelulusan:
- Filter didefinisikan hanya dari data pengembangan dan didaftarkan sebelum diuji.
- Pada data pengembangan, rasio biaya terhadap gerak menguntungkan pada sinyal yang lolos filter **lebih baik**
  daripada tanpa filter, diukur dengan alat Tahap 1.
- Setiap WAIT karena filter memiliki alasan tercatat.

### Tahap 3 — Risk & Execution Intelligence

Tujuan: pembatas DEMO dan umpan balik hasil yang jujur.

Pekerjaan: profil DEMO sebagai lapisan tambahan di atas Risk Governor (usulan awal: **0,5% per trade, stop entry
baru di drawdown harian 3%**; nilai final ditetapkan Owner). Profil utama tetap satu untuk backtest, demo, dan riil
(lihat [profil risiko](architecture/RISK_PROFILE_V2.md)); profil DEMO hanya menambah batas, tidak menggantikannya; ringkasan hasil: expectancy bersih, profit factor,
drawdown, akurasi BUY/SELL per regime, alasan WAIT, slippage, biaya, dan order ditolak.

Kriteria kelulusan:
- Tes membuktikan profil DEMO hanya bisa **memperketat**, tidak pernah melonggarkan, keputusan Risk Governor;
  batas 35% dan tes sinkronisasinya tetap utuh.
- Ringkasan dapat dibuat ulang dari data mentah dengan hasil identik.
- Rekonsiliasi order demo **100%** (tidak ada status tak jelas yang tersisa).

### Tahap 4 — Adaptive Strategy Brain

Tujuan: strategi BUY dan SELL berbeda sesuai regime, dengan bukti.

Pekerjaan: mulai dari **XAUUSD dan satu instrumen pembanding**. Kandidat (mis. market structure,
supply-demand, liquidity sweep, pullback) didaftarkan dulu; **maksimal 5 kandidat per instrumen per sisi**.

Kriteria kelulusan (gerbang promosi ke DEMO), per strategi:
- Data pengembangan: expectancy bersih > 0 dan mengalahkan semua baseline.
- Holdout (dibuka satu kali): expectancy bersih > 0 dengan **batas bawah interval keyakinan 95% > 0**
  (bootstrap per blok mingguan), dikoreksi untuk jumlah percobaan.
- Minimal **100 trade** di holdout; profit factor bersih **≥ 1,2**.
- Drawdown simulasi tetap di dalam profil DEMO.
- Stabil di sesi dan kondisi spread yang berbeda (tidak bergantung pada satu periode).

### Tahap 5 — Confidence & Autonomous Research

Tujuan: probabilitas yang terkalibrasi dan riset mandiri yang aman.

Pekerjaan: kalibrasi skor keputusan menjadi probabilitas dari hasil out-of-sample; antrean hipotesis riset mandiri.

Kriteria kelulusan:
- Kalibrasi hanya dimulai setelah **≥ 300** hasil out-of-sample berlabel.
- Brier score lebih baik daripada baseline frekuensi dasar; reliability per bin (bin dengan ≥ 30 sampel) dalam
  **±10 poin persen**.
- Jika kualitas bukti rendah, keputusan tetap WAIT.
- Riset mandiri hanya menulis ke antrean hipotesis; promosi selalu lewat gerbang promosi.

## Sebelum akun riil (di luar roadmap ini)

Tidak termasuk tujuan roadmap ini, tetapi syarat minimum yang sudah disepakati:
DEMO forward **≥ 3 bulan** dan **≥ 200 trade** dengan expectancy bersih positif (batas bawah interval keyakinan > 0),
rekonsiliasi dan kepatuhan risiko 100%, evaluasi ulang batas 35% berdasarkan hasil tersebut, dan otorisasi
eksplisit Owner. LIVE tetap OFF sampai semua itu terpenuhi.
