# Roadmap Katarina AI — berbasis bukti

Ditetapkan Owner (Project Manager) pada **22 Oktober 2026**; disempurnakan hari yang sama setelah review PM
(dua aliran data, paralel vs berurutan, celah holdout dan PENDING, profil DEMO vs Stage 38) dan dirapikan
23 Oktober 2026. Dokumen ini menjadi dasar pengembangan Katarina berikutnya.

> **Handoff teknis untuk Claude (27 Oktober 2026, DC akun kedua):** integrasi terisolasi WP12 (#204) + WP9b (#205) dan port selektif WP8a (#195) sudah diuji secara tertarget, **belum masuk `main`/VPS**. WP8a sekarang menolak arsip bar tanpa bukti per-chunk offset UTC independen, agar tidak salah melabeli jam server dan mencemari holdout. Langkah perbaikan, **69 tes tertarget yang lulus** (dan 2 tes statis terkendala dependensi VPS), tambahan loader WP8a streaming dengan batas eager 100.000 bar, reproduksi, konflik manifest/peta modul, blocker bukti historis DST, dan daftar periksa reviewer tercatat di [handoff integrasi 27 Oktober](maintenance/INTEGRATION_HANDOFF_20261027.md). **LIVE OFF; jangan deploy atau merge sebelum CI penuh dan review Claude.**

> **Audit jam Stage 0, 28 Oktober (untuk review Claude, belum merge):** pemeriksa lama salah memberi PASS untuk offset broker +3 → -4 → -7 → +2 jam karena seluruh perubahan dekat DST. Perbaikan memerlukan delta tepat 1 jam saat DST dan menolak offset noninteger. Replay ledger asli kini NOT_MET (3 transisi invalid); 18 tes unit PASS. Detail dan syarat perbaikan pemulihan observer di [handoff clock Stage 0](maintenance/STAGE0_CLOCK_HEALTH_HANDOFF_20261028.md). LIVE OFF, tidak ada perubahan VPS produksi. **Perbaikan portabilitas 28 Oktober:** tambahkan pemeriksa sinkronisasi NTP Windows/Linux sebelum membuka rute broker, quorum silang tick MT5 historical-UTC dan raw server tick, serta tolak inferensi offset dari tick basi akhir pekan. Pada VPS audit, sumber jam Windows masih `Local CMOS Clock` (tidak tersinkron), sebelum pemeliharaan NTP 28 Oktober. Perbaikan kode masih menunggu validasi gabungan. Langkah migrasi ada di [kontrak waktu MT5/VPS](operations/MT5_CLOCK_PORTABILITY.md).

> **Paket penerimaan 10 hari MT5, 28 Oktober:** source waktu VPS telah disinkronkan ke NTP dengan pemeriksaan silang eksternal (sebelumnya offset +14,9 detik, kini ~0,08 detik), backup SQLite dan Task Scheduler aman, dan satu pass broker asli di sandbox menghasilkan 5/5 simbol dengan offset +2 jam dan 0 order. Integrasi WP12 dan pemeriksaan portabilitas diuji dalam branch gabungan. **Belum otomatis menjadi satu hari kelulusan;** ketentuan dan pemeriksaan di [Stage0 10-Day Acceptance](maintenance/STAGE0_10DAY_ACCEPTANCE_20261028.md). Reviewer Claude harus cek CI gabungan, deployment tanpa order, dan mulai jendela forward baru yang bersih.

## Audit sistem menyeluruh — handoff Claude, 28 Oktober 2026

**Baca dahulu:** [Audit seluruh subsistem dan pekerjaan Claude](maintenance/CLAUDE_FULL_SYSTEM_AUDIT_20261028.md) → [PROJECT_STATUS](PROJECT_STATUS.md) → [paket penerimaan 10 hari](maintenance/STAGE0_10DAY_ACCEPTANCE_20261028.md). Audit ini memetakan arsitektur, MT5/NTP, ledger tick, berita, keputusan BUY/SELL/WAIT, shadow, memori/AI, biaya, risiko, CI, VPS, dan gerbang DEMO/LIVE. Setiap kelemahan dipasangkan dengan bukti, prioritas, dan syarat selesai.

- **Aturan Owner tidak berubah:** satu otak canonical, Risk Governor independen, Level 0/research only, LIVE OFF, holdout terlindung, gerbang Tahap 0–5 serta persetujuan Owner.
- **Pengujian 10 hari sudah berjalan pada worktree dan ledger terpisah**; keberhasilan 31 siklus awal bukan kelulusan satu hari penuh atau bukti profit. Target paling cepat evaluasi sekitar **11 November 2026 WIB jika semua kriteria tercapai**, bukan janji selesai otomatis.
- **P0 Claude:** audit harian, 3 reconnect teruji, broker tick-days dan rekonsiliasi, pemulihan boot/login, penentuan cakupan 5/7 simbol, bukti UTC historis independen, dan review konflik PR #206/#207/#208 tanpa mengubah worktree frozen. **P1:** alasan WAIT, strategi dan biaya secara shadow. **P2:** kesiapan DEMO, pemantauan dan tata kelola.
- Status operasional hanya di PROJECT_STATUS; log bukti di handoff, kode/tes di PR. **R5 yang belum diperbarui Claude tetap historis**, bukan izin merge atau promosi.

**Cara membaca dokumen ini**

- Bagian 1–7 adalah **aturan tetap**: prinsip, kewenangan, pemisahan data, gerbang promosi, dan kriteria kelulusan
  tiap tahap. Mengubahnya butuh persetujuan Owner dan catatan di `CHANGELOG.md`.
- **Lampiran A** adalah **rencana kerja berjalan** untuk pelaksana (AI lain atau manusia): urutan dan alur kerja (R0),
  temuan (R1), cara kerja standar (R2), peta berkas (R3), langkah per paket (R4), status (R5), perintah siap pakai
  (R6), daftar periksa review (R7), cara menulis kode (R8), aturan menulis dokumen/PR (R9), dan standar teknis (R10).
- Pembagian dokumen: roadmap = arah dan aturan; [PROJECT_STATUS](PROJECT_STATUS.md) = status terkini (satu-satunya
  sumber status operasional); deskripsi PR = bukti dan log kerja; [CHANGELOG](../CHANGELOG.md) = riwayat perubahan;
  [CLEANUP_PLAN](maintenance/CLEANUP_PLAN.md) = aturan perapian. **Log kerja tidak ditulis di roadmap.**

## Mulai di sini — untuk pelaksana AI (ChatGPT, Codex, atau AI lain)

Jika kamu diminta "baca roadmap dan kerjakan", ikuti urutan ini **persis**. Semua aturan yang perlu kamu ketahui
ada di dokumen ini dan di `CLAUDE.md`; jangan membuat aturan sendiri.

1. **Kenali proyeknya.** Katarina adalah sistem riset trading MT5 berbasis Python 3.12, **LIVE OFF**, satu otak
   canonical, Risk Governor independen dengan batas drawdown 35%. Baca `CLAUDE.md` (peta repo dan perintah
   pengecekan), lalu bagian 1–7 dokumen ini (aturan tetap). Jangan pernah melanggar bagian 5 (pemisahan data) dan 6
   (gerbang promosi).
2. **Pahami cara kerja.** Baca seluruh Lampiran A: R0 (alur dan urutan), R2 (cara kerja standar), R3 (peta berkas),
   R6.0 (aturan umum pelaksana — **berlaku walaupun tidak dikirim terpisah**), R7 (daftar periksa review), R8 (cara
   menulis kode), R9 (aturan menulis), R10 (standar teknis).
3. **Pilih satu paket** dengan aturan R5 "Cara mengambil paket": paket pertama di tabel R5 berstatus **Siap
   dikerjakan** yang prasyaratnya di R0 sudah di-merge dan belum diambil orang lain. Jika diberi paket tertentu,
   kerjakan paket itu saja.
4. **Kerjakan paket itu** sesuai sub-bagiannya di R4 dan perintahnya di R6 (blok "Perintah WPn"), dengan seluruh
   aturan R6.0 A–F. Satu paket, satu branch, satu PR.
5. **Berhenti setelah PR dibuka.** Claude meninjau (R7) dan melakukan merge; kamu tidak merge, tidak mengubah VPS,
   dan tidak memulai paket berikutnya sebelum diminta.

Jika ada yang tidak jelas, bertentangan, atau butuh keputusan Owner: tulis pertanyaannya di PR (atau balas Owner)
dan berhenti. Menebak dianggap kesalahan.

**Daftar isi**

1. [Prinsip utama](#prinsip-utama) · 2. [Empat keputusan Owner](#empat-keputusan-owner) ·
3. [Tangga kewenangan](#tangga-kewenangan) · 4. [Paralel dan berurutan](#paralel-dan-berurutan) ·
5. [Pemisahan data](#pemisahan-data) · 6. [Gerbang promosi](#gerbang-promosi) ·
7. [Urutan pengembangan dan kriteria kelulusan](#urutan-pengembangan-dan-kriteria-kelulusan) (Tahap 0–5) ·
8. [Sebelum akun riil](#sebelum-akun-riil-di-luar-roadmap-ini) ·
9. [Arah lanjutan](#arah-lanjutan) ·
Lampiran A — [Rencana kerja perbaikan](#lampiran-a--rencana-kerja-perbaikan-untuk-pelaksana) ·
[Mulai di sini untuk pelaksana AI](#mulai-di-sini--untuk-pelaksana-ai-chatgpt-codex-atau-ai-lain)

**Peta alat per tahap** (status operasional terkini — observer, VPS, tanggal, perkiraan — hanya di
[PROJECT_STATUS](PROJECT_STATUS.md); tabel ini hanya berubah bila alat baru masuk `main` atau sebuah tahap lulus)

| Tahap | Alat yang sudah ada di `main` | Kelulusan resmi menurut roadmap |
|---|---|---|
| 0 — Observer & data | Ledger siklus, tick broker harian, uji putus-sambung, `check_stage0_health.py`, simbol inti `--universe` (WP1) | Belum lulus (pengumpulan data berjalan) |
| 1 — Validasi ilmiah | `research/validation.py`, `validate_strategy.py`, [protokol](research/VALIDATION_PROTOCOL.md) | Belum lulus |
| 2 — Market intelligence | `research/market_intelligence.py` (`market-filter`), `research/context_export.py`, `research/blocker_ladder.py` (WP9a, diagnosis WAIT) | Belum lulus |
| 3 — Risk & execution | `research/demo_readiness.py` (`DemoRiskOverlay`), `check_demo_readiness.py` | Belum lulus |
| 4 — Adaptive strategy | Modul riset/adaptasi lama di `intelligence/`: `perception/adaptive_regime.py`, `lab/adaptive_strategy_library.py`, `lab/adaptive_walkforward.py`, `lab/autonomous_strategy_discovery.py` | Pembuktian resmi **belum dimulai** (butuh Tahap 0–3 dan kandidat terdaftar) |
| 5 — Confidence & riset mandiri | Modul riset lama di `intelligence/`: `lab/autonomous_research.py`, `lab/continuous_research_lab.py`, `lab/research_reports.py` | Pembuktian resmi **belum dimulai** (butuh ≥ 300 hasil out-of-sample) |

Modul yang sudah ada **bukan** bukti kelulusan: sebuah tahap lulus hanya bila kriteria di bagian 7 terpenuhi dengan
laporan yang dapat direproduksi dan disetujui Owner. Kewenangan saat ini: **Level 0** (mengamati dan mencatat);
LIVE OFF; batas drawdown utama 35%.

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
- Observer read-only kembali aktif di VPS pada **22 Okt 2026 04:24 UTC** (akun demo, Algo Trading OFF). CELAH holdout
  yang tercatat: **13 Okt 2026 00:00 UTC – 22 Okt 2026 04:24 UTC**; ledger Tahap 0 aktif sejak kode #173 dipasang.
- Audit holdout privat program 70 sel saat ini `BLOCKED_PRIVATE_INPUT_FILES_NOT_PROVIDED`; tidak ada klaim alpha lulus.
- Cakupan simbol observer forward: EURUSD/GBPUSD/USDJPY sejak 22 Okt 04:24 UTC (lubang 22 Okt 21:00–22:02 UTC);
  XAUUSD dan NAS100 22 Okt 19:58–21:00 UTC lalu sejak 23 Okt 00:16 UTC (WP6, setelah WP11); US30 dan JPN225 belum.
  Periode di luar cakupan = **CELAH** untuk simbol itu.
- **Jam tick (R1 T11):** sampai WP12 diterapkan, quote observer berumur ±3 jam dan arsip tick berbasis jam server.
  Data observer sebelum penerapan WP12 hanya bukti operasional (siklus, putus-sambung, memori), **bukan** bukti harga
  forward; baris tick tanpa `server_shift_hours` ditolak alat riset. Waktu penerapan WP12 dicatat di sini.
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
snapshot dalam satu tick size). Usulan WP2 di [PR #190](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/190) mengubah unduhan menjadi streaming per jam dengan hash dan rekonsiliasi terbatasi memori; belum merge atau diterapkan ke VPS. Uji putus-sambung dicatat dengan `scripts/ai/record_reconnect_test.py` (lulus bila
siklus OK berikutnya ≤ 10 menit setelah gangguan). `python scripts/ai/check_stage0_health.py --state-dir <state>` menilai kriteria di
bawah (PASS / NOT_MET / NO_DATA) secara read-only. Simbol inti dipilih dengan `--universe config/observer_universe.json` (WP1, #184): ketujuh simbol program diamati
setiap siklus dengan XAUUSD pertama; simbol inti yang tidak tersedia menjadi WAIT dan baris ledger `FAILED` beralasan
`CORE_SYMBOL_UNAVAILABLE`, tidak pernah diganti diam-diam; tanpa opsi, perilaku lama tetap.
Usulan WP3 di [PR #191](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/191) menambah diagnostik berita per sumber dan per siklus, tanpa mengubah keputusan atau kriteria Tahap 0; belum merge atau diterapkan ke VPS.
Statistik siklus memakai jendela konservatif Senin 00:00 – Jumat
20:00 UTC tanpa rollover 20:45–21:15 UTC. Status tahap: **belum lulus**; observer read-only berjalan di VPS sejak 22 Okt 2026 04:24 UTC.

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
ber-hash. Diperkuat #177: penolakan outcome masa depan, posisi melintasi CELAH, baseline tren tidak lengkap,
mismatch `code_sha256`, dan pemakaian ulang holdout oleh hipotesis pasca-pembukaan. Kriteria di bawah dibuktikan
oleh `tests/unit/research/test_validation.py`.

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

Alat (repo, 22 Okt 2026, #178/#181): `katarina.research.market_intelligence` dan `validate_strategy.py market-filter`
membandingkan sinyal sebelum/sesudah filter terdaftar memakai registry, split, biaya, dan laporan Tahap 1, dengan
alasan setiap WAIT. `scripts/research/export_market_contexts.py` (`research/context_export.py`) membangun
`contexts.jsonl` dari tick broker Tahap 0 yang terverifikasi hash, tanpa interpolasi celah. Panduan:
[Market Intelligence](research/MARKET_INTELLIGENCE.md). Filter aktif belum diubah.

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

Alat (repo, 22 Okt 2026, #179): `katarina.research.demo_readiness.DemoRiskOverlay` mempertahankan veto Risk Governor
dan hanya menurunkan anggaran risiko atau menghentikan entry; nilai batas wajib eksplisit (0,5%/3% masih usulan dan
parameter tes). `scripts/research/check_demo_readiness.py` membaca outbox secara baca-saja: expectancy bersih, profit
factor, drawdown terealisasi, win rate BUY/SELL per regime, biaya, slippage, alasan WAIT, order ditolak, dan
kelengkapan rekonsiliasi (data kosong tidak dianggap lulus; drawdown tidak mencakup posisi terbuka). Belum terhubung
ke worker aktif. Panduan: [DEMO readiness](research/DEMO_READINESS.md).

Kriteria kelulusan:
- Tes membuktikan profil DEMO hanya bisa **memperketat**, tidak pernah melonggarkan, keputusan Risk Governor;
  batas 35% dan tes sinkronisasinya tetap utuh.
- Ringkasan dapat dibuat ulang dari data mentah dengan hasil identik.
- Rekonsiliasi order demo **100%** (tidak ada status tak jelas yang tersisa).

### Tahap 4 — Adaptive Strategy Brain

Tujuan: strategi BUY dan SELL berbeda sesuai regime, dengan bukti.

Pekerjaan: mulai dari **XAUUSD dan satu instrumen pembanding**. Persiapan riset dari data pengembangan sebelum
13 Okt 2026 ada di Lampiran A WP8 (hasilnya riset, bukan kelulusan). Kandidat (mis. market structure,
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

## Arah lanjutan

Enam arah ini adalah **catatan pengembangan jangka panjang**, bukan izin mengubah strategi, menambah worker,
atau membuka tahap. Yang sudah punya paket kerja: arah 3 → WP9d, arah 4 → WP10 (Lampiran A R4). Arah lain baru
ditulis menjadi paket oleh Claude setelah prasyaratnya terpenuhi. Kriteria kelulusan Tahap 0–5 serta gerbang
promosi tetap berlaku.

1. **Autonomous Research (Tahap 5; terakhir).** Audit dahulu `run_autonomous_strategy_discovery` dan modul riset
   yang sudah ada; jangan membuat mesin paralel. Baru perluas setelah alur validasi stabil, setiap hipotesis
   **otomatis didaftarkan sebelum hasil dibaca** di `HypothesisRegistry`, setiap varian dihitung sebagai percobaan,
   dan koreksi banyak percobaan berlaku. Riset hanya data pengembangan; tidak boleh promosi otomatis.
2. **Market Intelligence (Tahap 2/4; setelah WP8a dan WP8b sesuai gerbangnya).** Bandingkan regime, sisi BUY/SELL,
   liquidity sweep, pullback, Fibonacci dan struktur pasar per instrumen, dengan data sebelum
   **13 Okt 2026 00:00 UTC** dan biaya penuh. Hipotesis didaftarkan lebih dahulu; hasil riset bukan filter aktif.
3. **Counterfactual Learning (Tahap 2/4; setelah WP8a, WP8b dan diagnosis WP9a).** WP9a pada kartu WAIT
   **forward/holdout** hanya boleh menghitung *frekuensi alasan*, tanpa markout untung-rugi untuk seleksi.
   Analisis keuntungan/kerugian 'seandainya penghambat X hilang' hanya memakai data **pengembangan sebelum cutoff**,
   dimulai dari pemblokir teknis kelas C. Jika berita/kalender historis yang dapat diverifikasi tidak ada,
   jangan melakukan counterfactual untung-rugi untuk pemblokir berita. Paket: WP9d.
4. **Trading Cost Intelligence (Tahap 1–2; setelah WP2 dan dataset pengembangan tersedia).** Perluas `CostModel`
   yang sudah mencakup spread/komisi dengan swap, slippage dan biaya broker terukur; tetap uji expectancy **neto**.
   **Pengecualian sempit:** distribusi spread dari tick observer forward boleh *diukur dan dilaporkan secara
   deskriptif* sebagai kondisi broker/diagnostik operasional, dengan sumber dan periode tercatat. Data tersebut
   **tidak boleh** digunakan untuk memilih strategi, mengkalibrasi ambang/filter/parameter, menentukan peringkat
   setup, atau memasukkan hasil forward ke validasi pengembangan. Untuk penyetelan model biaya/strategi, gunakan
   data pengembangan yang diizinkan. Aturan ini tidak membuka holdout untuk riset. Paket: WP10a (profil spread),
   WP10b (swap + sensitivitas biaya). Slippage tetap konstanta konservatif sampai ada fill DEMO (Tahap 3).
5. **Scientific Memory (Tahap 4–5; setelah ada strategi yang benar-benar lulus).** Gunakan `HypothesisRegistry`
   berantai hash yang sudah ada, bukan penyimpanan hipotesis kedua. Tambahkan alasan kegagalan terstruktur;
   deteksi penurunan kualitas (*drift*) hanya setelah tersedia bukti performa strategi tervalidasi yang memadai.
   Jangan melakukan pembelajaran ulang dari holdout yang sudah dibuka.
6. **Champion–Challenger (Tahap 4–5; setelah champion disetujui).** Perkuat alur kandidat, pengujian,
   walk-forward dan gerbang promosi yang sudah ada, bukan membangun engine baru. Sebelum ada strategi
   champion yang lulus, tidak ada promosi challenger. Penggantian strategi aktif mensyaratkan validasi terdaftar,
   holdout independen dan persetujuan eksplisit Owner.

**Prioritas terdekat:** WP2/WP3/WP8a/WP9a → WP9b, WP10a, WP10b → riset teknis pada data pengembangan (WP8b, WP9d)
→ memori/challenger sesudah ada bukti → riset otomatis terakhir. Arah ini tidak memberi kewenangan trading.

### Usulan untuk review Claude — pengembangan agentic AI

Dicatat atas permintaan Owner pada **27 Oktober 2026 (WIB)**. **Status: usulan, menunggu review Claude**;
bukan paket siap dikerjakan atau izin menaikkan kewenangan. Tujuan: Katarina dapat menemukan masalah,
merencanakan pekerjaan, memakai alat, menilai bukti dan menyimpan pelajaran secara terukur.
Gunakan observer, registry, memori, antrean dan gerbang yang sudah ada; jangan membangun otak/worker paralel.

**Lima fondasi yang perlu diperbaiki sebelum memperluas otonomi:**

| Fondasi | Usulan perbaikan | Bukti penerimaan yang perlu dirinci Claude |
|---|---|---|
| Waktu historis/DST | Kontrak waktu tunggal: timestamp mentah, UTC, offset dan asal bukti per periode; karantina periode tanpa bukti. Jangan memakai offset saat ini untuk seluruh sejarah. | Replay salinan data nyata sebelum/selama/sesudah +3 → +2: urutan, batas hari dan rekonsiliasi benar. |
| Keunggulan strategi | Hipotesis terdaftar sebelum eksperimen; development/validation/holdout terpisah, biaya penuh, baseline dan pencatatan seluruh percobaan. | Bukti out-of-sample dan forward memenuhi kriteria tahap yang sudah ditetapkan; CI hijau bukan bukti profit. |
| Jalur legacy | Inventaris entry point dan seluruh pembaca timestamp; adapter aktif memakai kontrak yang sama; jalur tanpa bukti tetap ditolak. Hapus hanya yang terbukti tidak digunakan. | Tes kontrak/penolakan data untuk setiap jalur aktif, tanpa melemahkan modul riset atau berkas terkunci. |
| Integritas data nyata | Audit salinan arsip secara offline: hash, skema, gap, duplikasi, urutan, cakupan simbol dan kecocokan snapshot. | Laporan per simbol/periode: layak, terbatas atau karantina dengan alasan; hash benar tidak otomatis berarti timezone benar. |
| Infrastruktur | VPS 2 GB difokuskan untuk observer; riset berat dan CI di cloud/GitHub, dengan antrean, batas sumber daya, checkpoint dan pembatalan. | Observer memenuhi anggaran siklus; pemulihan restart/koneksi diuji tersendiri; pekerjaan riset pulih tanpa kehilangan atau duplikasi hasil. |

**Kemampuan agentic yang perlu dipetakan ke modul existing:**

1. Perencana: tujuan → hipotesis/langkah, prasyarat, anggaran dan kondisi berhenti.
2. Alat dengan izin eksplisit: baca ledger, audit, replay, eksperimen dan usulan patch di sandbox;
   akses alat tidak otomatis memberi izin mengubah sumber data, runtime atau trading.
3. Evaluator terpisah dari pembuat usulan: kriteria ditetapkan sebelum eksperimen, pembandingan baseline,
   pemeriksaan kebocoran data, dan penolakan klaim tanpa bukti.
4. Memori terstruktur: versi kode/data, hipotesis, hasil termasuk kegagalan, alasan dan tingkat keyakinan;
   gunakan registry existing. Catatan operasional tidak boleh berubah menjadi pembelajaran strategi dari holdout.
5. Pengelola pekerjaan: checkpoint, deduplikasi, batas retry/CPU/RAM/waktu, pembatalan dan pemulihan.
6. Perubahan versi melalui PR: kandidat diuji di sandbox, dibandingkan dengan versi sebelumnya,
   direview dan memiliki rollback; tidak boleh mengubah Risk Governor atau promosi sendiri.
7. Evaluasi agen: ketepatan penyelesaian tugas, keterlacakan bukti, kepatuhan izin, biaya dan keberhasilan
   pemulihan; ambang penerimaan ditentukan sebelum uji, bukan berdasarkan kualitas narasi agen.

**Urutan usulan:** tuntaskan WP12 dan audit data → auditor data baca-saja → agen riset setelah gerbang tahap
terkait terpenuhi → usulan PR melalui CI/reviewer → evaluasi siklus lengkap dalam sandbox/shadow.
Target pertama: menemukan satu masalah data, membuktikannya, mengusulkan perbaikan, menjalankan tes dan
menyiapkan PR yang dapat direview tanpa mengganggu observer. Target ini tidak memerlukan izin trading.
Perkembangan dipisahkan menjadi pengetahuan operasional, kemampuan riset, dan perubahan kode/model;
pelatihan ulang model bukan prasyarat tahap pertama. Scientific Memory/riset strategi otomatis tetap mengikuti
prasyarat arah 1 dan 5 di atas; usulan ini tidak mempercepat pembukaan holdout atau Tahap 5.

**Permintaan review Claude:** petakan kemampuan yang sudah ada dan yang masih kurang; cek tumpang tindih WP,
pilih lingkup minimum auditor data, tetapkan dataset uji/izin/anggaran/kriteria lulus dan rollback, lalu usulkan
paket serta dependensinya kepada Owner. Bagian 1–7, status paket R5, runtime VPS dan LIVE OFF tetap berlaku;
pencatatan ini bukan persetujuan implementasi seluruh usulan, merge, deployment atau kenaikan kewenangan.

## Lampiran A — Rencana kerja perbaikan (untuk pelaksana)

Disusun Claude 22 Okt 2026 dari pemeriksaan VPS dan repo, ditambah usulan "Multi-Pair Opportunity Hunter" dari
review PM (Yura). Pelaksana (ChatGPT/Codex/AI lain) mengerjakan paket di bawah **berurutan** sesuai R0, memakai perintah siap pakai di R6; Claude meninjau dan
menyempurnakan setiap PR sebelum merge. Rencana ini **tidak** mengubah tahap, kriteria kelulusan, atau aturan lain
di dokumen ini. Bila ada yang bertentangan, aturan di bagian lain roadmap dan `CLAUDE.md` yang berlaku.

### R0. Urutan pengerjaan dan alur kerja (baca ini dulu)

**Siklus satu paket (selalu sama):**

```
1. Owner  → kirim ke pelaksana: blok R6.0 + blok "Perintah WPn" (R6)
2. Pelaksana → pahami (R6.0 A) → branch dari origin/main → tes dulu → kode → semua pengecekan R2.6 → PR
3. Owner  → kirim nomor PR ke Claude
4. Claude → review dengan R7 + R8 → perbaiki kecil langsung di branch PR, atau tulis komentar review
5. (bila ada komentar) Owner → kirim "Perintah perbaikan setelah review" (R6) ke pelaksana → kembali ke 3
6. Claude → selaraskan dengan main (merge commit, tanpa force-push) → CI hijau → squash-merge → isi baris R5
7. (paket yang menyentuh runtime) Claude → terapkan ke VPS sesuai WP6 → catat di PROJECT_STATUS
```

**Urutan paket.** Paket bernomor dikerjakan berurutan; paket berlabel "paralel" boleh berjalan bersamaan karena
berkasnya berbeda. Paket berikutnya dimulai setelah prasyaratnya **di-merge** (bukan hanya dibuka).

| Fase | Paket | Oleh | Prasyarat | Ukuran perkiraan | Status (rinci di R5) |
|---|---|---|---|---|---|
| 1 | WP1 — daftar simbol inti | Pelaksana → Claude | — | ±6 berkas | Selesai (#184) |
| 2 | WP2 — tick streaming hemat memori | Pelaksana | WP1 | ±2 berkas, ±250 baris | Selesai (#190) |
| 2 (paralel) | WP3 — diagnosis jalur berita | Pelaksana | WP1 (di-merge setelah WP2) | ±4 berkas, ±200 baris | Selesai (#191) |
| 2 (paralel) | WP8a — ekspor + dataset pengembangan | Pelaksana | — | ±4 berkas, ±300 baris | Perbaikan diminta (#195) |
| 2 (paralel, prioritas) | WP9a — peta tembok blokir (baca-saja) | Pelaksana | — | ±3 berkas, ±250 baris | Selesai (#196) |
| 3a (prioritas tertinggi) | WP12 — jam tick server → UTC | Pelaksana | — | ±8 berkas, ±350 baris | — |
| 3 | Review + merge WP2 → WP3 → WP8a → WP9a | Claude | PR siap review | — | WP2, WP3, WP9a selesai; WP8a menunggu perbaikan |
| 3b | WP9b — input keputusan jujur + evaluasi bayangan | Pelaksana | WP3 di-merge | ±6 berkas, ±400 baris | — |
| 3b (paralel) | WP10a — profil spread deskriptif | Pelaksana | WP2 di-merge | ±4 berkas, ±250 baris | — |
| 3b (paralel) | WP10b — swap + sensitivitas biaya di alat validasi | Pelaksana | WP8a di-merge | ±3 berkas, ±250 baris | — |
| 3c | Jalankan WP9a di VPS; aktifkan `measured_inputs` bila Owner setuju | Claude + Owner | WP9a, WP9b | — | — |
| 3b (paralel, prioritas) | WP11 — jam broker saat sebagian pasar tutup | Pelaksana | — (berkas berbeda dari WP2/WP3) | ±2 berkas, ±120 baris | Selesai (#201) |
| 4 | WP6 — terapkan 5 → 7 simbol di VPS | Claude | WP1 + WP11 di-merge | — | Tahap A dilanjutkan 23 Okt 00:16 UTC |
| 4 (paralel) | Ekspor dataset pengembangan + profil spread di VPS (akhir pekan, pasar tutup) | Claude | WP8a; WP10a | — | — |
| 5 | WP8b — setup BUY/SELL, simulasi, perbandingan | Pelaksana | WP8a (sebaiknya setelah WP10b) | ±8 berkas, ±600 baris | — |
| 5 (paralel) | WP4 — jurnal kandidat + replay sinyal | Pelaksana | WP6 tahap A berjalan | ±6 berkas, ±450 baris | — |
| 5b | WP9c — syarat bukti proporsional (berkas terkunci, gerbang promosi) | Pelaksana → Claude + Owner | WP9a + WP9b + ≥ 3 hari bursa data `decision_shadow` | ±3 berkas, ±250 baris | — |
| 6 | Review + merge WP8b, WP4; WP4 diterapkan ke VPS | Claude | PR dibuka | — | — |
| 6b | WP9d — detektor entry teknis + counterfactual kelas C (hipotesis, data pengembangan) | Claude menulis paket | WP4 + WP8b | — | — |
| 7 | Daftarkan hipotesis nyata + laporan perbandingan setup (riset) | Claude, disetujui Owner | WP8b + dataset | — | — |
| 8 | WP5 — hipotesis perankingan antarpair | Pelaksana | WP4 + ≥ 5 hari bursa data kandidat | ±4 berkas, ±350 baris | — |
| 9 | Review + merge WP5; hasil riset ke Owner | Claude | PR dibuka | — | — |
| kapan saja | WP7 — keputusan Owner | Owner | — | — | Menunggu |
| terus berjalan | Tahap 0 — observer VPS mengumpulkan 10 hari bursa | VPS | — | — | Lihat PROJECT_STATUS |

**Aturan alur:**
- Satu paket = satu branch dari `origin/main` = satu PR. Jangan menumpuk PR di atas PR lain.
- PR paralel hanya mengubah **baris paketnya sendiri** di tabel R5; konflik di dokumen diselesaikan Claude.
- Paket paralel bisa menyentuh berkas yang sama (WP2 dan WP3 sama-sama menambah ke `operations/observation_ledger.py`;
  semua PR membuat ulang `release-manifest.json`). Itu boleh: Claude me-merge berurutan (WP2 dulu, lalu WP3, lalu
  WP8a), menggabungkan `main` ke branch berikutnya, dan membuat ulang manifest/peta modul dengan alatnya — manifest
  tidak pernah diedit tangan. Pelaksana tidak perlu menyelaraskan PR satu sama lain.
- Pakai kosakata status R5 persis (Sedang dikerjakan · Dalam review · …); keterangan bebas masuk kolom catatan.
- Bila paket ternyata butuh berkas terkunci atau keputusan Owner, pelaksana berhenti dan menulis pertanyaan di PR.
- Kelulusan tahap tidak pernah dipercepat: pengembangan paralel, validasi berurutan.

### R1. Temuan yang mendasari (bukti 22 Okt, VPS `30d043c`, 600+ siklus; kolom Status diperbarui saat paket selesai)

| # | Temuan | Bukti / lokasi | Status |
|---|---|---|---|
| T1 | Observer hanya mengamati `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx`. Program holdout butuh 7 simbol; Tahap 4 mulai dari XAUUSD | `BrainObserver.run` memotong `resolve_broker_symbols(catalog).symbols[:max_symbols]`; urutan tetap `MAJORS, CROSSES, OPTIONAL_MARKETS` di `broker/broker_scan_universe.py`; `JPN225` tidak ada di universe | Sebagian: WP1 di `main`; VPS 5 simbol sejak 22 Okt 19:58 UTC (WP6 tahap A); 7 simbol menunggu cek |
| T2 | Ketujuh simbol tersedia dan bisa ditrade: `XAUUSD.vx`, `NAS100.vx`, `US30.vx`, `JPN225.vx`, `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx` (`trade_mode=4`). Versi tanpa `.vx` ada tetapi `trade_mode=0` | Probe baca-saja: baca 4 timeframe + tick 90 dtk ≈ 0,2–1,4 dtk/simbol (±5 dtk untuk 7); RAM bebas ±885 MB dari 2 GB; spread XAUUSD 0,33, NAS100 3,4, US30 3,3, JPN225 9,5 | Dipakai sebagai dasar WP1/WP6 |
| T3 | Tick satu hari XAUUSD ≈ 355 ribu (3 dtk). `collect_tick_days` menampung seluruh hari dalam dict/list sebelum menulis (±100–150 MB) | `operations/observation_ledger.py::_fetch_day`, `_write_ticks`, `reconcile` | Selesai: WP2 (#190), streaming per jam |
| T4 | 100% keputusan WAIT (381 baris) dengan 7 pemblokir di setiap baris: `system_unhealthy`, `insufficient_verified_forward_experience`, `no_verified_relevant_news`, `high_impact_news_blackout`, `macro_event_risk_too_high`, `macro_policy_transmission_not_verified`, `no_confirmed_closed_candle_entry` | Tabel `contextual_decisions` (`blockers_json`) | Terbuka → WP9 (a: peta, b: input jujur, c: syarat bukti terkunci, d: detektor) |
| T5 | Tanpa berita segar yang cocok, `MultiSourceNewsEngine.assess` mengembalikan `ready=False, blackout=True, risk=1.0`, walau kalender `calendar_verified_clear`. Artikel resmi tersimpan: 0; feed Fed/ECB/BoE terambil OK. `load_articles` melewati item yang lebih tua dari `FRESH_SECONDS` (6 jam) **tanpa mencatat diagnosis**, sehingga `full_article_checks` kosong | `news/news_intelligence.py` (cabang `if not matched`), `cognition/observer.py::load_articles`, `news/verified_policy_context.py` | Diagnosis: WP3 (#191, tabel `observer_news`); perbaikan: WP9b |
| T6 | Observer selalu mengirim `system_healthy=False` dan `resolved_experience=[]` (sengaja fail-closed); `technical_signal` tidak pernah BUY/SELL selama 10 jam di 3 pasangan | `cognition/observer.py` di sekitar `RiskSituation(...)`; logika di `cognition/contextual_decision_intelligence.py` (terkunci) | Terbuka → WP4 (replay sinyal), WP9b/9d |
| T7 | `engines/opportunity.py::MultiMarketOpportunityEngine` hanya dipakai tes; bobot skornya (0,65/0,35/0,55, penalti spread/korelasi/berita) belum divalidasi; membuang kandidat bila `news.ready` salah | `docs/maintenance/RUNTIME_MODULE_MAP.md` kategori B | Terbuka → WP5 (riset) |
| T8 | `KATARINA_ALL_MARKET_RESEARCH=1` merotasi simbol paling lama tak dikunjungi (`lab/continuous_research_lab.py::select_batch`) dan menyalakan `ResearchPool`, `NetworkDoctor`, koneksi broker tambahan. Tidak cocok untuk cakupan per siklus 7 simbol inti dan RAM 2 GB | `cognition/continuous_observation.py` | Ditangani WP1 (mode all-market ditolak bersama `--universe`) |
| T9 | VPS tertinggal dari `main`; tugas `Katarina-Readonly-Observer` hanya berjalan saat Administrator login (trigger logon) | Task Scheduler VPS | Sebagian: kode VPS = `main` 23 Okt; auto-start setelah restart VPS masih WP6 |
| T10 | Mode 5 simbol, 22 Okt 21:00–22:02 UTC: 7 siklus `FAILED BROKER_CLOCK_NOT_VERIFIED`, 0 data untuk **semua** simbol ±62 menit. XAUUSD/NAS100 jeda harian ±21:00–22:00 UTC (DST AS); hanya 3/5 quote segar = 60% < ambang 70% dari **semua** simbol. Dengan 7 simbol: 3/7. Backoff ×2 sampai 16 menit memperpanjang lubang | `broker/broker_clock_alignment.py::infer_clock_shift` (`frac=count/considered`), `cognition/observer.py` (raise bila tidak `suitable_for_readonly_snapshot`), `cognition/continuous_observation.py` (backoff) | Selesai: WP11 (#201); VPS 5 simbol lagi sejak 23 Okt 00:16 UTC (WP6) |
| T11 | **Jam tick MT5 = jam server broker (+3 jam), bukan UTC.** Probe baca-saja 23 Okt 00:19 UTC: `symbol_info_tick.time` dan `time_msc` dari `copy_ticks_range` sama-sama ≈ UTC+3 jam; bar `copy_rates_*` juga jam server (sudah dikoreksi `bars_for`). `last_past_quote(now)` mencari tick di [now−90 dtk, now] dalam koordinat server, sehingga quote observer berumur **±3 jam**: EURUSD 1.12124 vs 1.12221 sekarang, USDJPY 156.719 vs 156.162. Quote, `quote_age_seconds`, rekonsiliasi dan arsip tick Tahap 0 sejak 22 Okt 04:24 UTC tergeser 3 jam secara konsisten, sehingga pemeriksaan yang ada tidak mendeteksinya. XAUUSD/NAS100 `FAILED` 00:00–01:00 UTC = jeda harian 3 jam sebelumnya | `broker/causal_broker_quotes.py` (`last_past_quote`, `due_window_quote`, docstring "UTC"), `cognition/observer.py`, `operations/observation_ledger.py::_download_day`, `research/context_export.py`, `broker/data_recovery.py`, `demo/demo_forward.py` | Terbuka → WP12 (prioritas tertinggi) |

### R2. Cara kerja standar (wajib untuk setiap paket)

Ini cara Claude mengerjakan Katarina. Ikuti urutannya; jangan melompati langkah.

1. **Baca dulu**: `CLAUDE.md`, bagian ini, kriteria tahap terkait di roadmap, dan berkas yang disebut di paket.
   Telusuri alur pemanggilan dengan `grep -n "nama_fungsi" -r src scripts tests` sebelum mengubah apa pun.
2. **Branch** dari `origin/main` terbaru: `git fetch origin && git checkout -B <agent>/wpN-<ringkas>-YYYYMMDD origin/main`.
3. **Cek berkas terkunci**: `python scripts/governance/promotion_gate.py --hashes` menampilkan daftar berkas yang
   **tidak boleh** diubah. Jika paket butuh mengubahnya, berhenti dan tulis usulan di PR.
4. **Tulis tes dulu** (minimal satu tes yang gagal sebelum perubahan), lalu kode, lalu jalankan tes sampai hijau.
5. **Standar kode**:
   - Ikuti gaya berkas yang diubah; modul baru memakai gaya `operations/observation_ledger.py`: docstring modul
     yang menyebut tujuan, tahap roadmap, dan "read-only / nothing here sends orders"; `from __future__ import
     annotations`; fungsi kecil dengan nama jelas; konstanta di atas berkas dengan HURUF_BESAR.
   - Waktu selalu `datetime` ber-zona UTC; tolak waktu naif (`ValueError("aware_utc_datetime_required")`).
     Waktu pasar memakai `time_msc` MT5 (ms UTC), bukan jam VPS.
   - **Fail-closed**: input tidak valid → tolak/catat alasan, jangan diganti nilai tebakan. Tidak ada `except:`
     kosong; tangkap jenis spesifik, atau `except Exception` hanya di batas pemanggilan observer dengan alasan
     tercatat (`{"status": "FAILED", "error": type(ex).__name__}`). Jangan mencatat pesan exception mentah
     (bisa berisi akun/server).
   - Kode alasan berupa string `HURUF_BESAR_GARIS_BAWAH` yang stabil (dipakai tes dan laporan).
   - SQLite: `CREATE TABLE IF NOT EXISTS` di fungsi `setup(db)` yang idempoten; tulis di dalam `with db:`;
     parameter `?`, jangan format string SQL dengan nilai; pembaca memakai `mode=ro`.
   - Hasil deterministik: urutkan sebelum hash/menulis; JSON kanonik `sort_keys=True`; gzip `mtime=0` tanpa nama.
   - Tidak ada jaringan, MT5, atau jam nyata di tes: pakai broker palsu (`tests/integration/test_brain_owned_workflow.py::SyntheticBroker`,
     `tests/integration/test_automatic_connection.py::AccountBroker`) atau kelas palsu kecil di berkas tes; waktu
     disuntikkan lewat parameter `now`.
   - Jangan menambah dependensi pip. Jangan menambah observer/worker/thread baru; pekerjaan tambahan berjalan di
     thread pemilik dengan anggaran terbatas (contoh: `collect_tick_days(..., budget=1)`).
   - Tes yang membuka SQLite di direktori sementara wajib menutup koneksi (`contextlib.closing`) — Windows CI
     gagal menghapus direktori bila koneksi masih terbuka.
6. **Jalankan semua pengecekan** (sama dengan Body CI) dan salin ringkasannya ke deskripsi PR:
   ```bash
   PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_*.py'
   PYTHONPATH=src python -m unittest discover -s tests/static -p 'test_*.py'
   PYTHONPATH=src python -m unittest discover -s tests/integration -p 'test_*.py'
   python scripts/governance/audit_repo_hygiene.py --repo-root . --output build/repository-hygiene.json
   python scripts/governance/audit_dependency_links.py --repo-root . --output build/validation/dependency-links.json
   python scripts/governance/promotion_gate.py --check
   git add -A   # generator manifest ikut membaca berkas yang belum di-commit
   python scripts/deployment/release_manifest.py --manifest ops/deployment/release-manifest.json --generate
   python scripts/deployment/release_manifest.py --manifest ops/deployment/release-manifest.json   # harus MATCH
   python scripts/governance/runtime_import_map.py --output docs/maintenance/RUNTIME_MODULE_MAP.md
   ```
7. **Dokumen** — tulis di tempat yang benar, jangan menggandakan:
   - `CHANGELOG.md`: satu entri baru di atas (tanggal, judul, apa dan kenapa, "tidak ada berkas terkunci diubah;
     LIVE tetap OFF"), maksimal ±10 baris.
   - `CLAUDE.md`: hanya bila ada CLI/modul baru atau angka tes/peta modul berubah.
   - Roadmap: **hanya** (a) baris paket di tabel R5 (status, nomor PR, satu kalimat) dan (b) bila paket menambah
     CLI/modul untuk sebuah tahap, satu-dua kalimat di paragraf "Alat" tahap itu.
   - Log kerja, riwayat commit, hasil tes rinci, dan pelajaran ditulis di **deskripsi PR**, bukan di roadmap,
     PROJECT_STATUS, atau berkas lain. Jangan menambah sub-bagian baru ke roadmap (mis. "R5A").
8. **Commit dan PR**: satu paket satu PR ke `main`, judul `WPn: ...` (bahasa Indonesia). Deskripsi: Ringkasan,
   Keamanan (berkas terkunci tidak diubah, LIVE OFF, tanpa perubahan VPS), Pengujian (angka hasil langkah 6).
   `gh pr create` dapat diblokir; gunakan REST:
   `gh api -X POST repos/alfaauliau-katarinaAI/Katarina-AI/pulls -f title=... -f head=<branch> -f base=main -F body=@pr.md`.
9. **Jangan merge sendiri** dan jangan mengubah VPS. Tunggu review Claude.

### R3. Peta alur berkas observer (yang disentuh WP1–WP4)

```
VPS C:\Katarina\run-observer.ps1                       (peluncur; argumen CLI)
 └─ scripts/ai/run_contextual_market_observer.py main()
     ├─ --continuous → cognition/continuous_observation.py run_continuous(root, config, max_symbols, ...)
     │    ├─ adapters/automatic_connection.py local_factory(config) → BoundLocalBroker (cek akun/server, tanpa order_send)
     │    ├─ cognition/unified_brain.py UnifiedKatarinaBrain.observe_connected_market(root, broker, max_symbols, fetch_news)
     │    │    └─ cognition/observer.py BrainObserver.run(max_symbols, fetch_news)
     │    │         ├─ load_articles(...)  → news/verified_policy_context.py (FRESH_SECONDS)           [WP3]
     │    │         ├─ broker/broker_scan_universe.py resolve_broker_symbols(catalog) → symbols[:max_symbols] [WP1]
     │    │         ├─ per simbol: broker/causal_broker_quotes.py last_past_quote, adapters/mt5_readonly_market.py bars_for,
     │    │         │   prepare_news(...) → news/news_intelligence.py MultiSourceNewsEngine.assess        [WP3]
     │    │         │   brain.evaluate_contextually(...)  (TERKUNCI: cognition/contextual_decision_intelligence.py) → kartu
     │    │         │   journal.record(...)  (shadow/contextual_observation_journal.py)                   [WP4 di sini]
     │    │         ├─ operations/observation_ledger.py record_snapshot(...), collect_tick_days(...)       [WP2]
     │    │         └─ publish(root, report) → <state>/latest.json
     │    └─ close_ledger_cycle(context.db, result, fault) → observation_ledger.close_cycle
     └─ tanpa --continuous → adapters/automatic_connection.py run_connected → UnifiedKatarinaBrain.observe_once → observer.run
Pembaca: scripts/ai/check_stage0_health.py → operations/data_health.py assess(db, now)  (SQLite mode=ro)
```

Basis data: `<state>/context.sqlite3` (milik `ContextStore`; satu koneksi di thread pemilik, diakses lewat
`store.db` di observer dan `context.db` di loop kontinu). Laporan siklus: `<state>/latest.json`; status loop:
`<state>/continuous-status.json`.

### R4. Paket kerja

#### WP1 — Daftar simbol eksplisit untuk observer (Tahap 0, prioritas tertinggi)

Tujuan: 7 simbol program diamati **setiap siklus**, XAUUSD pertama, tanpa mengubah perilaku lama bila opsi tidak
dipakai.

1. Buat `config/observer_universe.json`:
   ```json
   {"schema_version": 1,
    "description": "Simbol inti observer Tahap 0 = simbol program holdout (config/research/alpha_regime_program_v1.json)",
    "core": ["XAUUSD.vx", "NAS100.vx", "US30.vx", "JPN225.vx", "EURUSD.vx", "GBPUSD.vx", "USDJPY.vx"],
    "rotating_slots": 0}
   ```
2. Modul baru `src/katarina/intelligence/broker/observer_universe.py`:
   - `@dataclass(frozen=True) class ObserverUniverse: core: tuple[str, ...]; rotating_slots: int = 0`
   - `load_universe(path) -> ObserverUniverse`: tolak (ValueError dengan kode) jika `core` kosong, duplikat,
     bukan string, `rotating_slots` bukan int 0–10, atau `len(core) + rotating_slots > 17`.
   - `select_symbols(universe, catalog, *, rotation=None) -> tuple[tuple[str, ...], tuple[str, ...]]` →
     `(dipilih, tidak_tersedia)`. Simbol core dipakai **persis** (nama broker), urutan dipertahankan, hanya jika ada
     di katalog dengan `trade_mode in (1, 2, 4)`; sisanya masuk `tidak_tersedia`. `rotation` adalah callable
     `(budget, exclude) -> list[str]` untuk slot rotasi (implementasi: `lab/continuous_research_lab.select_batch`
     dengan simbol core dikecualikan; tambahkan parameter `exclude=()` ke `select_batch` tanpa mengubah perilaku
     default).
   - Tes satu: konsistensi dengan program — `load_universe("config/observer_universe.json").core` harus sama
     dengan `symbols` di `config/research/alpha_regime_program_v1.json` (sebagai himpunan) dan XAUUSD pertama.
3. Teruskan parameter `universe` (default `None`) melalui seluruh rantai R3:
   `main()` (`--universe PATH`, dimuat dengan `load_universe`, error → `parser.error`) → `run_continuous(...,
   universe=None)` → `observe_connected_market(..., universe=None)` → `BrainObserver.run(..., universe=None)`;
   juga `run_connected` → `observe_once` untuk jalur satu-pass. Validasi argumen di tiap lapisan sama seperti
   `max_symbols`.
4. Di `BrainObserver.run`: jika `universe` tidak `None`, ganti baris `symbols=list(selection.symbols)[:max_symbols]`
   dengan hasil `select_symbols`; isi `report["unavailable_symbols"]` dengan simbol core yang tidak tersedia, dan
   tambahkan masing-masing ke `report["symbols"][sym]` sebagai kartu WAIT dengan `sensor_reason="CORE_SYMBOL_UNAVAILABLE"`
   (tambahkan kode ini ke `REASONS` di `broker/data_recovery.py`) agar ledger mencatat baris `FAILED` beralasan.
   `max_symbols` tidak memotong simbol core saat `universe` dipakai. Jika `universe` `None` → kode lama apa adanya.
   Mode `KATARINA_ALL_MARKET_RESEARCH` tidak boleh aktif bersamaan dengan `universe` (tolak dengan
   `ValueError("universe_and_all_market_research_exclusive")`).
5. Tes (unit `tests/unit/intelligence/test_observer_universe.py` + integration di
   `tests/integration/test_continuous_observation.py`):
   - urutan core dipertahankan; core tidak pernah dipilih ulang oleh rotasi; total ≤ 17;
   - simbol core yang hilang/`trade_mode=0` → baris ledger `FAILED` dengan alasan `CORE_SYMBOL_UNAVAILABLE`;
   - `run_continuous(..., universe=ObserverUniverse(("XAUUSD","EURUSD")))` dengan `SyntheticBroker` (katalognya
     `EURUSD, GBPUSD, XAUUSD`) mengamati tepat XAUUSD lalu EURUSD; tanpa `universe` hasil sama seperti sekarang;
   - fake brain di tes lama menerima `**options`, jadi parameter baru tidak memecahkan tes itu.
6. Dokumentasi: tambahkan contoh peluncur di Tahap 0 roadmap:
   `run_contextual_market_observer.py --continuous --universe config\observer_universe.json --connection-config ... --state-dir ... --interval-seconds 60`.

Kriteria selesai: semua tes lulus, perilaku tanpa `--universe` identik (tes lama tak diubah), tidak ada berkas
terkunci berubah.

#### WP2 — Pengunduh tick hemat memori (Tahap 0)

1. Ubah `observation_ledger._fetch_day` + `_write_ticks` menjadi satu fungsi streaming `_download_day(mt5, symbol,
   day_start, path) -> (ticks_count, first_ms, last_ms, sha256, gaps, hour_index)`:
   - per jam: ambil `copy_ticks_range`, saring `lower <= time_msc < upper`, dedup dan urutkan **dalam jam itu saja**
     (kunci `(time_msc, bid, ask)`), lalu tulis baris CSV ke `gzip.GzipFile(filename="", mtime=0)` yang sudah
     terbuka dan perbarui `hashlib.sha256()` dengan byte baris yang sama (header ditulis sekali di awal);
   - aturan celah tetap: `None` → `BROKER_HISTORY_UNAVAILABLE`, jam kosong di sesi → `BROKER_SERVER_EMPTY`,
     lebih dari `MAX_TICKS_PER_HOUR` → `TICK_HOUR_OVER_LIMIT`;
   - `hour_index`: per jam, waktu tick pertama/terakhir dan offset baris (untuk rekonsiliasi).
   - Tulis ke `*.tmp` lalu `os.replace`; jika tidak ada tick sama sekali hapus `*.tmp`.
2. `reconcile`: untuk tiap snapshot hari itu, baca ulang **hanya jam** yang memuat `tick_epoch` dari berkas gzip
   (memakai `hour_index`), lalu terapkan aturan cocok yang sama (bid/ask dalam satu tick size; beberapa tick dengan
   milidetik sama boleh salah satunya). Kelompokkan snapshot per jam agar setiap jam dibaca sekali.
3. Tes:
   - **byte-identik**: untuk input yang sama, berkas dan `sha256` baru sama persis dengan implementasi lama
     (simpan fungsi lama di tes sebagai pembanding, bukan di `src`);
   - 2.000.000 tick sintetis per hari: `tracemalloc` puncak < 50 MB;
   - semua tes lama di `tests/unit/intelligence/test_observation_ledger.py` tetap lulus tanpa diubah.

#### WP3 — Diagnosis jalur berita (Tahap 0–2; hanya observabilitas)

1. `cognition/observer.py::load_articles`: tambah penghitung untuk item yang dilewati karena basi:
   `diagnostics[source+"_items_older_than_window"] += 1`, item tanpa tanggal valid
   `source+"_item_invalid_time"`, dan catat `source+"_newest_item_age_hours"` (dibulatkan 1 desimal) dari item
   terbaru. Jangan mengubah urutan/aturan pengambilan.
2. Tambahkan ke laporan siklus `report["news_pipeline"]` (ringkas: per sumber jumlah item feed, umur item terbaru,
   item dalam jendela, artikel terverifikasi, kegagalan per jenis). Simpan ringkasan per siklus di tabel ledger baru
   `observer_news(cycle_id, source, feed_items, newest_age_hours, in_window, verified, failures_json)` lewat fungsi
   `observation_ledger.record_news(db, cycle_id, summary)`.
3. `operations/data_health.py`: tambah bagian informatif `report["news_pipeline"]` (bukan kriteria kelulusan, tidak
   memengaruhi `verdict`) yang menjawab: berapa persen siklus tanpa artikel karena **tidak ada rilis** vs karena
   **pengambilan gagal**.
4. **Dilarang** mengubah `MultiSourceNewsEngine`, ambang blackout, `FRESH_SECONDS`, atau logika keputusan.
5. Tes: feed dengan item basi menghasilkan `*_items_older_than_window`; kegagalan ambil menghasilkan
   `*_article_unavailable_*`; data_health memisahkan dua kasus itu; `verdict` tidak berubah.

#### WP4 — Jurnal kandidat riset, terpisah dari izin entry (Tahap 1–2)

Tujuan: bahan riset untuk Tahap 1/2 walau semua keputusan WAIT. **Tidak** mengubah `action` atau keputusan.

1. Modul baru `src/katarina/intelligence/operations/candidate_ledger.py` dengan tabel
   `research_candidates(cycle_id, symbol, closed_m5_utc, observed_utc, market_state, direction_bias,
   selected_method, technical_setup, technical_evidence_score, conditional_side, conditional_invalidation,
   conditional_target, after_spread_rr_geometry, spread, bid, ask, tick_epoch, blockers_json,
   UNIQUE(cycle_id, symbol))`. Semua nilai diambil dari kartu `ContextDecision` yang **sudah ada** (lihat field di
   `cognition/contextual_decision_intelligence.py`), tanpa menghitung ulang.
2. Panggil `candidate_ledger.record(store.db, cycle_id=ledger_cycle, cards=report["symbols"], quotes=latest_quotes)`
   di `observer.py` tepat setelah `ledger.record_snapshot`, dibungkus `try/except Exception` yang mencatat
   `report["research_candidates"]={"status":"FAILED","error":type(ex).__name__}`.
3. Diagnosis T6 (offline, baca-saja): `scripts/research/replay_technical_signals.py` memutar ulang
   `market_decision` (tanpa mengubahnya) pada bar historis MT5 yang diekspor (`--bars-dir`) dan menghitung
   frekuensi `technical_signal` BUY/SELL per simbol/regime/playbook. Keluaran JSON di `build/`. Ini menjawab
   apakah detektor entry memang hampir tidak pernah menyala.
4. Ekspor ke format `Trade` Tahap 1: `scripts/research/export_candidates.py` mengubah kandidat (yang punya
   `conditional_side` BUY/SELL atau `direction_bias` + invalidation/target) menjadi `trades.jsonl` dengan exit dari
   tick broker Tahap 0 (`<state>/broker-ticks`, verifikasi `sha256` di `broker_tick_days`). Aturan exit (target,
   invalidation, batas waktu) wajib dibaca dari spec hipotesis terdaftar, bukan default di kode.
   `data_until` = waktu candle tertutup terakhir, harus ≤ `entry_at`.
5. Tes: kandidat tercatat walau `action=WAIT`; `orders_submitted` tetap 0; ekspor menolak tick tanpa hash cocok;
   `data_until > entry_at` tidak mungkin dihasilkan.

#### WP5 — Hipotesis perankingan antarpair (Tahap 2, riset saja)

1. `scripts/research/rank_candidates.py`: baca `research_candidates` (WP4), bentuk `MarketCandidate`, jalankan
   `MultiMarketOpportunityEngine.rank` **atau** varian berparameter di `src/katarina/research/` (jangan mengubah
   `engines/opportunity.py`). Semua bobot (porsi skor, penalti spread/korelasi/berita, `min_score`, `limit`) dibaca
   dari `parameters` spec hipotesis yang terdaftar di `HypothesisRegistry`.
2. Hasilkan input `validate_strategy.py market-filter` (trades, contexts, outcomes) sehingga perbandingan
   "semua kandidat" vs "kandidat teratas per siklus" memakai alat Tahap 1 yang sama, termasuk jumlah percobaan.
3. Korelasi antarpair dari return M15 tertutup sebelum waktu entry (kausal); dokumentasikan rumusnya di
   `docs/research/MARKET_INTELLIGENCE.md`.
4. Tidak dipasang ke jalur keputusan. Pemasangan hanya lewat gerbang promosi setelah lulus Tahap 2/4 dan disetujui Owner.

#### WP6 — Penerapan VPS bertahap (dikerjakan Claude setelah WP1–WP3 merge)

1. `git fetch && git merge --ff-only origin/main` di `C:\Katarina\code`; manifest `MATCH`.
2. Hentikan observer dengan `continuous.stop`, ubah `run-observer.ps1` menambah `--universe C:\Katarina\code\config\observer_universe.json`.
3. Tahap A: core 5 (salinan privat `C:\Katarina\private\observer_universe_stage_a.json` = 3 sekarang + XAUUSD, NAS100)
   selama ≥ 2 jam. Lanjut ke 7 hanya jika: durasi siklus < 20 dtk, RAM bebas > 500 MB, 0 siklus gagal, dan unduhan
   tick hari penuh selesai tanpa error. Jika gagal, kembali ke 3 simbol.
4. Tugas terjadwal tetap hidup setelah restart VPS (trigger startup + MT5 login tersimpan, atau auto-logon), diuji
   sekali dengan restart terencana di akhir pekan.
5. Catat di roadmap tanggal mulai cakupan 7 simbol; periode sebelumnya untuk 4 simbol baru = CELAH.

#### WP8 — Riset historis setup BUY/SELL antarpair (data pengembangan saja; Tahap 1–2, persiapan Tahap 4)

Tujuan: sambil Tahap 0 mengumpulkan data forward, Katarina meneliti setup mana (liquidity sweep, pullback, Fibonacci,
struktur pasar) yang punya expectancy bersih positif per instrumen, per sisi, dan per kondisi pasar — memakai alat
Tahap 1 yang sama — tanpa memaksa entry dan tanpa menyentuh holdout. Hasil WP8 berstatus **riset**; tidak ada yang
masuk ke otak aktif tanpa holdout + gerbang promosi.

**Aturan data (wajib, ditegakkan kode):**
- Data pengembangan = bar broker **sebelum 13 Okt 2026 00:00 UTC** (`DEV_CUTOFF_UTC = 2026-10-13T00:00:00+00:00`).
  Setiap bar/tick dengan waktu ≥ cutoff ditolak saat ekspor **dan** saat dimuat (`ValidationError("holdout_data_forbidden")`).
- Data holdout (13 Okt 2026 – 30 Apr 2027) dan data observer forward Tahap 0 **tidak boleh** dipakai untuk memilih
  strategi, menyetel parameter, atau menentukan peringkat setup.
- Dataset dibekukan: setiap berkas punya SHA-256 di `manifest.json`; laporan menyertakan hash manifest.

**Aturan hipotesis:**
- BUY dan SELL **diuji terpisah**: satu hipotesis = satu instrumen + satu sisi + satu setup + satu set parameter
  (sesuai `REQUIRED_SPEC_FIELDS` di `research/validation.py`). Aturan BUY tidak harus cermin aturan SELL.
- Setiap varian (parameter berbeda) adalah percobaan baru di `HypothesisRegistry`; jumlah percobaan mengetatkan
  batas keyakinan otomatis.
- **Maksimal 5 hipotesis per instrumen per sisi** (batas Tahap 4). Ini **batas atas, bukan target**: jika hanya satu
  hipotesis yang masuk akal, uji satu. Daftarkan sebelum melihat hasil; jangan menambah varian setelah melihat hasil
  kecuali dicatat sebagai percobaan baru dengan alasan di spec (`rules`).

**Langkah:**
1. `scripts/research/export_dev_bars.py` (dijalankan Claude di VPS pada akhir pekan, baca-saja, dengan anggaran kecil):
   ekspor bar M5, M15, H1, H4 broker (`copy_rates_range`, termasuk kolom `spread` dalam point) untuk 7 simbol inti dari
   `config/observer_universe.json`, rentang yang ditentukan argumen `--start` (default 2024-01-01) sampai **sebelum**
   cutoff, ke `<out>/<SIMBOL>/<TF>.csv.gz` (gzip `mtime=0`, urut waktu, tanpa duplikat) + `manifest.json`
   (simbol, TF, jumlah bar, waktu pertama/terakhir, `point`, `trade_tick_size`, `trade_contract_size`, sha256).
   Celah data dicatat di manifest, tidak diisi. Tes dengan broker palsu; tolak bar ≥ cutoff.
   **Jam bar (wajib).** `time` dari `copy_rates_*` adalah jam server broker (lihat `adapters/mt5_readonly_market.py::bars_for`),
   sedangkan `time_msc` tick adalah jam pasar UTC. Untuk setiap batch dan simbol, ambil satu jam tick lewat
   `copy_ticks_range` yang tumpang tindih dengan bar M5 batch itu dan tentukan pergeseran jam bulat (−12…14) yang
   membuat open ≥ 3 bar M5 cocok dengan bid tick pertama di bar itu (toleransi `trade_tick_size`). Konversi
   `time_utc = time_server − shift`, simpan `shift_hours` per batch di manifest (`clock_evidence`), terapkan cutoff
   **setelah** konversi. Batch tanpa bukti → celah `BAR_CLOCK_NOT_VERIFIED`, tidak diekspor.
2. Modul `src/katarina/research/dev_dataset.py`: `load_dev_dataset(path)` memverifikasi semua hash manifest, menolak
   bar ≥ cutoff, mengembalikan bar tertutup per simbol/TF. Tidak ada akses MT5/jaringan.
3. Paket `src/katarina/research/setups/` (baru; **jangan** mengubah berkas terkunci — boleh mengimpor fungsi
   persepsi yang ada secara baca-saja): satu modul per keluarga setup — `liquidity_sweep.py`, `pullback.py`,
   `fibonacci.py`, `market_structure.py`. Setiap modul punya satu fungsi murni
   `detect(bars_by_tf, as_of, params, side) -> list[Signal]` yang hanya memakai bar yang **sudah tertutup** pada
   `as_of`. `Signal` memuat: waktu entry (`open` bar berikutnya), sisi, harga entry (mid), invalidation, target,
   `data_until` (waktu tutup bar terakhir yang dipakai), regime label kausal, dan `trend_side` kausal (untuk
   pembanding tren Tahap 1). Semua angka (panjang swing, level Fibonacci, RR minimum, dll.) dibaca dari `params`
   spec hipotesis — tidak ada default tersembunyi di kode.
4. `scripts/research/simulate_setups.py`: untuk hipotesis terdaftar, jalankan `detect` maju bar demi bar pada
   dataset pengembangan, simulasikan exit dari bar berikutnya (target, invalidation, batas waktu dari `params`; bila
   target dan invalidation tersentuh di bar yang sama, anggap **invalidation dulu**), satu posisi per hipotesis pada
   satu waktu, spread entry/exit dari kolom `spread` bar × `point`. Keluarannya `trades.jsonl` format `Trade`
   (`research/validation.py`) dengan `data_until ≤ entry_at`.
5. Uji tiap hipotesis dengan `validate_strategy.py development` (split: `development_start` = awal dataset,
   `development_end` = cutoff, holdout = periode program; biaya `costs.json` dengan slippage konservatif yang
   dicatat). Jangan pernah memanggil perintah `holdout` di WP8.
6. `scripts/research/compare_setups.py`: gabungkan laporan pengembangan menjadi satu tabel per instrumen × sisi ×
   setup × regime: trades, expectancy bersih, PF, batas bawah bootstrap, biaya rata-rata R, hasil vs semua
   pembanding, jumlah percobaan. Urutkan per instrumen; tulis `build/research/setup_comparison.json` + ringkasan
   Markdown. Label wajib: "RISET — data pengembangan, bukan kelulusan".
7. Tes: penolakan bar ≥ cutoff (ekspor dan muat), hash salah ditolak, detektor tidak memakai bar yang belum
   tertutup (tes dengan bar masa depan yang sengaja diubah tidak boleh mengubah sinyal), urutan invalidation-dulu,
   satu posisi per hipotesis, `trend_side` ada untuk semua trade, batas 5 hipotesis per instrumen per sisi
   ditolak pada pendaftaran ke-6, perbandingan deterministik.

Kriteria selesai: alat dan tes lulus; satu contoh hipotesis per keluarga setup (sintetis di tes, bukan klaim pasar).
Hipotesis nyata didaftarkan dan dijalankan oleh Claude/Owner setelah dataset diekspor (WP8b, bukan bagian PR).

#### WP9 — Membongkar "tembok blokir" keputusan (Tahap 0–2; prioritas Owner 23 Okt)

**Masalah (R1 T4–T6).** Di VPS 100% keputusan WAIT. Setiap kartu memuat tujuh pemblokir yang selalu muncul, sehingga
otak tidak pernah menghasilkan satu pun kandidat (bahkan untuk paper/riset). `ContextualDecisionIntelligence.evaluate`
(`cognition/contextual_decision_intelligence.py`, **terkunci**) mengumpulkan **semua** alasan lalu memberi
`action="WAIT"` bila ada satu saja (`PAPER_OBSERVATION_ONLY` bila kosong), jadi daftar `blocking_reasons` tiap kartu
lengkap dan bisa dianalisis.

**Klasifikasi pemblokir (dasar seluruh WP9):**

| Kelas | Pemblokir | Sumber | Sifat | Tindakan |
|---|---|---|---|---|
| A — input salah dari observer | `system_unhealthy` | `observer.py` mengirim `system_healthy=False` tetap | Pengaman kaku, bukan pengukuran | WP9b: hitung dari pemeriksaan nyata (tidak terkunci) |
| A | `high_impact_news_blackout`, `macro_event_risk_too_high` | `news_intelligence.py`: tanpa berita segar → `blackout=True, risk=1.0` walau kalender `calendar_verified_clear` | Ketiadaan berita diperlakukan sama dengan berita berbahaya | WP9b: blackout/risk hanya dari kalender atau berita berdampak nyata (tidak terkunci) |
| B — syarat bukti di logika terkunci | `no_verified_relevant_news`, `macro_policy_transmission_not_verified` | `contextual_decision_intelligence.py` mewajibkan berita/makro terverifikasi untuk **setiap** keputusan | Terlalu ketat untuk paper; berguna bila ada berita | WP9c: wajib hanya bila ada berita/makro relevan; lewat gerbang promosi |
| B | `insufficient_verified_forward_experience` | observer mengirim `resolved_experience=[]`; syarat ≥ 45 hasil forward terekonsiliasi | Benar untuk eksekusi, mustahil dipenuhi tanpa trade | WP9c: berlaku untuk tingkat eksekusi (demo/riil), tidak untuk `PAPER_OBSERVATION_ONLY`; lewat gerbang promosi |
| M — filter pasar yang sah | `spread_exceeds_M15_volatility_budget`, `uncertain_or_shock_regime`, `no_market_appropriate_playbook`, `stale_quote`, `broker_session_closed` dan sejenisnya | logika keputusan (terkunci) | Pengaman yang memang diinginkan (biaya/volatilitas/sesi) | Tidak dilonggarkan di WP9; hanya lewat Tahap 2 (filter terdaftar + validasi) |
| C — persepsi | `no_confirmed_closed_candle_entry` (+ `risk_reward_geometry_not_favorable`, `technical_evidence_not_sufficient`) | detektor entry di modul persepsi terkunci | Belum diketahui apakah terlalu ketat atau pasar memang tidak memberi setup | WP4 replay + WP8 riset; perubahan hanya lewat hipotesis → validasi → promosi (WP9d) |

**Aturan WP9 (tambahan R6.0):** tidak ada jalur order baru; Risk Governor dan batas 35% tidak disentuh; perubahan
kelas A berjalan di balik opsi yang default-nya perilaku lama; perubahan kelas B/C mengubah berkas terkunci dan
**hanya** di-merge bersama catatan promosi yang dibuat Claude setelah Owner menyetujui. Hasil terbaik WP9 adalah
`PAPER_OBSERVATION_ONLY` (kandidat paper untuk riset/belajar), **bukan** izin order.

**WP9a — Peta tembok blokir (baca-saja; boleh paralel sekarang)**
1. Modul `src/katarina/research/blocker_ladder.py` + CLI `scripts/research/blocker_ladder.py --state-dir DIR
   [--since ISO] --output build/research/blocker_ladder.json`. Membaca tabel `contextual_decisions` (`blockers_json`,
   symbol, method, observed_utc) dari `context.sqlite3` dengan `mode=ro`.
2. Laporan per simbol dan total: frekuensi tiap pemblokir; jumlah kartu yang **hanya** terblokir oleh kelas A;
   oleh A+B; oleh A+B+C (kelas M selalu dihitung terpisah dan tidak pernah dianggap "diperbaiki"; tangga kumulatif: "bila kelas X diperbaiki, berapa kartu tersisa yang masih terblokir dan
   oleh apa"); 10 kombinasi pemblokir terbanyak. Pemetaan kode → kelas berupa konstanta di modul (tabel di atas);
   kode yang tidak dikenal masuk kelas `UNKNOWN` dan dilaporkan, tidak dibuang.
3. Tes: data sintetis di SQLite sementara; hasil deterministik; kode tidak dikenal tercatat; koneksi ditutup.
4. Selesai bila: laporan bisa dijalankan Claude di VPS dan menjawab "pemblokir mana yang benar-benar mengikat".

**WP9b — Input keputusan yang jujur (tidak terkunci; setelah WP3 di-merge karena sama-sama mengubah `observer.py`)**
1. Config baru `config/decision_inputs.json`: `{"schema_version": 1, "mode": "legacy_fail_closed"}`; nilai lain yang
   sah hanya `"measured_inputs"`. Dimuat oleh `src/katarina/intelligence/cognition/decision_inputs.py`
   (`load_decision_inputs(path) -> DecisionInputs`, tolak nilai lain dengan `ValueError`).
2. `DecisionInputs.system_healthy(...)` pada mode `measured_inputs` bernilai `True` hanya bila **semua** benar:
   quote segar (`quote_fresh`), bar tertutup terbaru (`recent`), `trade_mode in (1,2,4)`, jam broker terverifikasi
   (`clock.suitable_for_readonly_snapshot`), dan siklus ledger sebelumnya tercatat. Mode `legacy_fail_closed` selalu
   `False` (perilaku sekarang).
3. `DecisionInputs.news_context(news, calendar)` pada mode `measured_inputs`: bila mesin berita tidak menemukan item
   segar yang cocok **dan** kalender `ready=True, blackout=False`, kembalikan `NewsContext` dengan `blackout=False`,
   `risk_score=0.0`, `ready=False`, alasan `no_fresh_relevant_news_calendar_clear` (tetap `ready=False` agar
   `no_verified_relevant_news` tetap muncul sampai WP9c). Bila ada item segar, atau kalender tidak siap/blackout,
   hasil mesin berita dipakai apa adanya. Jangan mengubah `news_intelligence.py`.
4. Observer: opsi CLI `--decision-inputs PATH` diteruskan sepanjang rantai R3 seperti `universe` di WP1 (default
   `None` = legacy). Setiap siklus, untuk tiap simbol, observer mengevaluasi **kedua** mode: kartu aktif memakai mode
   config; kartu mode lain dicatat di tabel ledger baru `decision_shadow(cycle_id, symbol, mode, action,
   conditional_side, blockers_json, UNIQUE(cycle_id, symbol, mode))` lewat `observation_ledger.record_decision_shadow`.
   Evaluasi kedua memakai fungsi yang sama (tanpa salinan logika) dan dibatasi waktu (tes durasi).
5. Tes: mode legacy identik dengan sekarang (kartu sama persis); mode measured hanya menghapus `system_unhealthy`,
   `high_impact_news_blackout`, `macro_event_risk_too_high` pada kondisi yang ditentukan dan tidak pada kondisi
   lain (kalender blackout, quote basi, jam tidak terverifikasi); tabel shadow terisi; 0 order.
6. Mengaktifkan `measured_inputs` di VPS **bukan** bagian PR: Claude melakukannya setelah Owner setuju (catat di R5).

**WP9c — Syarat bukti yang proporsional (berkas terkunci; setelah WP9a/9b memberi data)**
1. Di `contextual_decision_intelligence.py`: `no_verified_relevant_news` dan `macro_policy_transmission_not_verified`
   hanya ditambahkan bila **ada** item berita/makro relevan yang belum terverifikasi (berita relevan yang ada tetap
   wajib terverifikasi; ketiadaan berita + kalender bersih tidak memblokir).
2. `insufficient_verified_forward_experience` tetap dihitung, tetapi untuk keputusan paper dilaporkan sebagai
   `execution_gate_pending_forward_experience` di `confirming_evidence`/catatan, bukan pemblokir; tingkat eksekusi
   (demo/riil) tetap mewajibkannya (diperiksa di jalur eksekusi dan dibuktikan tes).
3. PR menyertakan: tes perilaku lama vs baru; laporan bukti (`build/research/wp9c_evidence.json`) dari WP9a + data
   `decision_shadow` VPS yang dibekukan hash; draf isi catatan promosi di deskripsi PR. **Jangan** menjalankan
   `promotion_gate.py --write-lock` atau membuat berkas di `docs/governance/promotions/`; CI gerbang promosi akan merah
   sampai Claude menambahkan catatan yang disetujui Owner. Tandai PR "menunggu persetujuan Owner".

**WP9d — Detektor entry teknis + counterfactual kelas C (setelah WP4 replay dan WP8b)**
- Tidak ada perubahan langsung. Usulan perbaikan detektor didaftarkan sebagai hipotesis (WP8). Semua varian
  dibandingkan **hanya** pada data pengembangan; holdout dibuka **satu kali** untuk satu kandidat final setelah
  pemilihan selesai (bagian 5), tidak pernah untuk membandingkan varian. Bila lulus, kandidat dipromosikan lewat
  gerbang promosi. Paket rinci ditulis Claude setelah hasil WP4/WP8 ada.
- Counterfactual ("seandainya detektor tidak memblokir"): varian detektor didaftarkan sebagai hipotesis dan
  disimulasikan **hanya** pada `dev_dataset` (< cutoff), dibandingkan dengan detektor asli pada periode yang sama.
  Kartu WAIT forward (`contextual_decisions`, `decision_shadow`) dan laporan WP9a **tidak boleh** dipakai untuk
  menghitung untung-rugi atau memilih varian. Counterfactual kelas A/B (berita, makro) tidak dilakukan selama data
  berita/kalender historis terverifikasi tidak ada.

#### WP10 — Biaya trading terukur (Tahap 1–2; arah lanjutan 4)

Tujuan: alat validasi menolak setup yang bagus secara teknis tetapi tidak ekonomis. `CostModel` sekarang hanya
memotong spread entry/exit, slippage konstan, dan komisi. WP10 menambah swap, sensitivitas biaya, dan profil spread
broker yang **deskriptif**. Tidak ada perubahan pada observer, keputusan, atau berkas terkunci.

**WP10a — Profil spread deskriptif (baca-saja; setelah WP2 di-merge)**
1. `research/context_export.py`: tambah fungsi publik `iter_verified_ticks(root, record)`. Pass 1 menghitung sha256
   isi terdekompresi secara streaming dan membandingkannya dengan `record["sha256"]` (`TICK_FILE_HASH_MISMATCH`);
   pass 2 menghasilkan `(time_msc, bid, ask)` dengan filter baris yang sama seperti `_ticks`. `_ticks` diubah memakai
   fungsi ini; keluarannya identik (tes pembanding). Jangan menulis pembaca tick kedua.
2. Modul `src/katarina/research/spread_profile.py` + CLI `scripts/research/spread_profile.py --state-dir DIR
   --since YYYY-MM-DD --until YYYY-MM-DD --output build/research/spread_profile.json`. Membaca `broker_tick_days`
   (SQLite `mode=ro`; hanya status di `USABLE_TICK_DAY_STATUSES` milik `context_export.py`) lalu berkas lewat
   `iter_verified_ticks`. Sampel = quote terakhir tiap menit UTC yang punya
   tick (bobot waktu, bukan bobot tick). Laporan per simbol × jam UTC 0–23 dan ringkasan per simbol: jumlah menit,
   spread p50/p90/p99/maks dalam satuan harga (persentil nearest-rank, deterministik). Satu berkas diproses sekali
   jalan tanpa menampung seluruh hari dalam list.
3. JSON wajib memuat `"usage": "DESCRIPTIVE_ONLY_NOT_FOR_TUNING"`, label "DESKRIPTIF — data forward, bukan untuk
   penyetelan", periode, dan daftar sumber (simbol, hari, sha256).
4. Pagar (tes statis): tidak ada berkas di `src/katarina/` dan `scripts/` selain CLI-nya yang mengimpor
   `research.spread_profile`. Profil tidak boleh dibaca otomatis oleh `costs.json`, filter, atau simulasi.
5. Tes: data sintetis; hash salah ditolak; satu sampel per menit; persentil deterministik; rentang tanggal dihormati;
   tracemalloc puncak < 50 MB untuk 2.000.000 tick; koneksi ditutup.
6. Menjalankan di VPS bukan bagian PR: Claude menjalankannya saat pasar tutup dan menyimpan hasil di luar repo
   (data broker).

**WP10b — Swap dan sensitivitas biaya di alat validasi (setelah WP8a di-merge)**
1. `CostModel` (`research/validation.py`, tidak terkunci) mendapat field baru berdefault 0:
   `swap_long_per_night`, `swap_short_per_night` (satuan harga per malam; ≥ 0 = biaya; kredit swap ditulis 0 —
   konservatif) dan `triple_swap_weekday` (default 2 = Rabu, `weekday()` Python dari tanggal New York).
2. Rollover = 17:00 New York: 21:00 UTC selama DST AS, 22:00 UTC di luar itu. Pakai ulang aturan DST AS yang sudah
   ada (`_nth_sunday` di `operations/data_health.py`; jadikan publik bila perlu, perilaku tetap); tanpa
   `zoneinfo`/tzdata. Satu malam dihitung untuk setiap rollover Senin–Jumat dengan `entry_at < t <= exit_at`;
   rollover pada `triple_swap_weekday` dihitung 3 malam.
3. `cost_r(trade, side=None)` menambah `malam × swap sisi`; `net_r` meneruskan sisi sehingga pembanding sisi acak
   memakai swap sisi yang ditarik. `market_intelligence.py` tidak diubah.
4. Laporan pengembangan dan holdout mendapat blok `cost_sensitivity`: `net_expectancy_r` pada pengali biaya 1,5 dan
   2,0; `breakeven_cost_multiple` = gross rata-rata / biaya rata-rata (null bila biaya 0 atau gross ≤ 0);
   `cost_verdict` ∈ `NO_GROSS_EDGE` (gross ≤ 0) · `NOT_ECONOMIC_AFTER_COSTS` (gross > 0, net ≤ 0) ·
   `POSITIVE_AFTER_COSTS`. Blok ini informasi saja: `verdict` dan aturannya **tidak berubah** (tes).
5. `costs.json` lama tanpa field baru tetap diterima dan menghasilkan angka identik (tes pembanding).
   `docs/research/VALIDATION_PROTOCOL.md`: paragraf biaya diperbarui — nilai swap diambil dari spesifikasi kontrak
   broker dengan sumber dan tanggal dicatat, tidak pernah dari hasil uji.
6. Tes: malam melintasi perubahan DST, akhir pekan, triple Rabu; kredit diabaikan; sisi acak memakai swap sisinya;
   blok sensitivitas dan `cost_verdict` untuk ketiga kasus; verdict lama tidak berubah.

#### WP11 — Jam broker saat sebagian pasar tutup (Tahap 0; prioritas; prasyarat WP6)

**Masalah (R1 T10).** `infer_clock_shift` menghitung pecahan mayoritas atas **semua** simbol yang punya quote. Saat emas
dan indeks jeda harian, quote FX yang segar tidak mencapai 70%, sehingga seluruh siklus gagal dan tidak ada data
untuk simbol mana pun. Perbaikan hanya di inferensi jam; keputusan, ledger, backoff, dan kriteria Tahap 0 tetap.

1. `src/katarina/intelligence/broker/broker_clock_alignment.py` (tidak terkunci): pecahan mayoritas dihitung atas
   simbol yang memberi suara segar (`sum(votes.values())`), bukan atas `considered`. Syarat lain tidak berubah:
   minimal `min_symbols` (3) suara untuk jam yang sama, `majority_fraction` 0,70, umur −15…180 detik, rentang
   −12…14 jam. `confidence_fraction` = suara jam terpilih / semua suara.
2. `ClockFinding` mendapat field terakhir `stale_symbols: tuple[str, ...] = ()` (urut abjad): simbol yang
   dipertimbangkan tetapi tidak memberi suara. Pemanggil lain tidak diubah.
3. Observer tidak diubah. Simbol yang sedang tutup tetap diamati: bila riwayat tick kausalnya masih ada, quote
   tercatat `OK`; bila tidak ada tick sama sekali, quote tercatat `FAILED` dengan alasan dan kartunya `WAIT` (jujur,
   tanpa tick buatan). Siklus tetap OK selama ≥ 3 simbol segar.
4. Tes (`tests/unit/intelligence/test_broker_clock_alignment.py`; tes lama tidak diubah dan tetap lulus):
   3 segar + 2 basi 1 jam → valid, shift benar, `stale_symbols` berisi 2; 3 segar + 4 basi → valid; 2 segar + 3 basi
   → tidak valid; 3 segar vs 2 segar dengan jam berbeda → tidak valid (0,6); 3 benar + 1 jam salah → valid dengan jam
   mayoritas. Tambah satu tes observer dengan MT5 palsu (pola `tests/integration/test_brain_owned_workflow.py`): 3 FX segar + 2 simbol basi → siklus OK,
   5 baris quote; tanpa riwayat tick, 3 `OK` + 2 `FAILED` beralasan.
5. Menerapkan di VPS bukan bagian PR: Claude melanjutkan WP6 (5 simbol, dipantau melewati 21:00–22:00 UTC, lalu 7).

#### WP12 — Jam tick MT5 adalah jam server (Tahap 0; prioritas tertinggi; R1 T11)

**Masalah.** Kode menganggap `time_msc` tick dan jendela `copy_ticks_range` dalam UTC. Di broker ini keduanya jam
server (+3 jam sekarang, berubah dengan DST). Akibatnya quote observer berumur ±3 jam, dan arsip tick tergeser 3 jam.
Bar sudah benar (`bars_for` mengurangi `clock_correction`). Perbaikan: satu konversi server ↔ UTC memakai pergeseran
yang sudah diverifikasi `infer_clock_shift` pada siklus yang sama; tanpa pergeseran terverifikasi → fail-closed.

1. `broker/causal_broker_quotes.py`: fungsi `server_epoch_to_utc(epoch, shift_hours)` dan
   `utc_to_server_datetime(dt, shift_hours)` (shift bilangan bulat −12…14, selain itu `ValueError`). Docstring yang
   menyebut "UTC" diperbaiki.
2. `last_past_quote(mt5, symbol, as_of_utc, *, server_shift_hours, lookback_seconds=90)` dan
   `due_window_quote(..., *, server_shift_hours)`: parameter **wajib tanpa default**; jendela query dikonversi ke jam
   server, `ts` hasil dikonversi ke UTC **sebelum** batas kausal dan umur. Semua pemanggil diperbarui:
   `cognition/observer.py` (memakai `offset` siklus), `broker/data_recovery.py`, `demo/demo_forward.py` (bila
   pergeseran tidak tersedia di sana: tidak ada quote, fail-closed; tidak mengubah berkas terkunci),
   `scripts/mt5/audit_readonly_quotes.py`. Report observer: `canonical_market_clock` =
   `MT5_TICK_SERVER_TIME_CONVERTED_TO_UTC`.
3. `operations/observation_ledger.py::collect_tick_days(..., server_shift_hours)`: hari UTC D diambil dengan jendela
   server [D + shift, D + 1 + shift); `time_msc` dikonversi ke UTC sebelum ditulis, dedup dan rekonsiliasi. Kolom
   baru `broker_tick_days.server_shift_hours` (migrasi `ALTER TABLE ... ADD COLUMN`, baris lama tetap `NULL`). Bila
   `observer_cycles.clock_shift_hours` hari D punya lebih dari satu nilai, hari itu dicatat `GAP` dengan alasan
   `BROKER_SHIFT_CHANGED_DURING_DAY` (tidak menebak DST). Observer meneruskan `offset` siklus.
4. `research/context_export.py`: tolak baris `broker_tick_days` dengan `server_shift_hours IS NULL`
   (`TICK_CLOCK_BASIS_UNKNOWN`). Data lama **tidak** ditulis ulang atau dikonversi.
5. Audit pemakai lain `time_msc`/`symbol_info_tick().time` (`broker/auto_calibration.py`,
   `perception/screening.py`, `lab/continuous_research_lab.py`, `scripts/ai/run_readonly_decisions.py`): yang ada di
   jalur aktif observer dikonversi dengan fungsi butir 1; sisanya didaftar di deskripsi PR, tidak diubah.
6. Tes: broker palsu yang meniru bukti T11 (tick dan bar berlabel jam server +3, snapshot +3) → quote observer adalah
   harga **sekarang**, bukan 3 jam lalu; tanpa pergeseran → tidak ada quote; jendela unduhan hari UTC benar dan isi
   arsip ber-epoch UTC; hari dengan dua pergeseran → `GAP`; baris lama `NULL` ditolak `context_export`. Broker palsu
   lama yang memberi `time_msc` UTC (`tests/integration/test_brain_owned_workflow.py::SyntheticBroker`, tes WP11,
   `adapters/pc_simulation.py`) **boleh** diubah ke jam server karena asumsinya terbukti salah; catat di PR.
7. Bukan bagian PR: Claude menerapkan ke VPS, memverifikasi quote = `symbol_info_tick` dalam satu tick size, dan
   mencatat waktu penerapan sebagai awal data forward yang sah (bagian 5).

#### WP7 — Keputusan Owner (bukan kode)

- Profil DEMO final Tahap 3 (usulan 0,5%/trade, 3%/hari sebagai lapisan pengetat di atas batas utama 35%).
- Aturan berita: apakah "tidak ada rilis resmi" boleh dibedakan dari blackout. Menyentuh logika keputusan; hanya
  lewat hipotesis + validasi + catatan promosi setelah data WP3/WP4 tersedia.
- Repo private atau tidak; status issue lama #21, #24, #29, #31.

### R5. Status paket

**Cara mengambil paket** (untuk pelaksana yang diminta "baca roadmap dan kerjakan"):
1. Pilih baris teratas berstatus **Siap dikerjakan** yang prasyaratnya di R0 sudah di-merge.
2. Pastikan belum diambil: tidak ada PR terbuka atau branch `*/wpN-*` untuk paket itu
   (`git ls-remote --heads origin "*wpN*"` dan daftar PR terbuka). Jika sudah ada, pilih paket lain.
3. Langsung buka PR draft dengan bagian "Pemahaman" (R6.0 A3) dan ubah baris paket itu menjadi
   **Sedang dikerjakan — <agen>, PR #N**. Status lain hanya diubah Claude (review/merge) atau Owner.

Status yang dipakai: Siap dikerjakan · Sedang dikerjakan · Dalam review · Selesai (merge) · Menunggu prasyarat ·
Menunggu Owner · Dikerjakan Claude.

| Paket | Status | PR | Catatan review Claude |
|---|---|---|---|
| WP1 | Selesai (merge); penerapan VPS di WP6 | [#184](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/184) | Diterima. Perbaikan review: path tes absolut, catatan `CLAUDE.md` dipindah, log kerja R5A dikeluarkan dari roadmap (aturan R2 langkah 7) |
| WP2 | Selesai (merge); penerapan VPS di WP6 | [#190](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/190) | Diterima. Hasil sama dengan algoritme lama (dedup/urut per jam setara per hari karena jam terpisah), rekonsiliasi identik; manifest dibuat ulang dengan generator |
| WP3 | Selesai (merge); penerapan VPS di WP6 | [#191](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/191) | Diterima. Hanya diagnosis: seleksi artikel, ambang dan verdict tidak berubah; `published_utc=None` kini dihitung `item_invalid_time` alih-alih error. Manifest dibuat ulang dengan generator |
| WP4 | Menunggu prasyarat (WP9b; sama-sama mengubah `observer.py`) | – | – |
| WP5 | Menunggu prasyarat (WP4 + ≥ 5 hari bursa data kandidat) | – | – |
| WP6 | Sedang dikerjakan — Claude: 5 simbol sejak 23 Okt 00:16 UTC | – | Tahap A (22 Okt): RAM bebas 853 MB, siklus 1–4 dtk; gagal saat jeda emas/indeks (T10) → WP11. 7 simbol setelah WP12 dan pemantauan melewati 21:00–22:00 UTC. Jalan mundur: ganti nama `C:\Katarina\private\observer_universe.json` |
| WP8a | Sedang dikerjakan — ChatGPT, PR #195 (perbaikan diminta) | [#195](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/195) | Dua butir wajib di komentar PR: (1) `import io` hilang, 7 tes error di HEAD; (2) jam bar server belum diverifikasi → butir "Jam bar" di WP8 langkah 1. Kirim "Perintah perbaikan setelah review" |
| WP8b | Menunggu prasyarat (WP8a) | – | – |
| WP9a | Selesai (merge); laporan VPS oleh Claude (fase 3c) | [#196](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/196) | Diterima. Semua kode alasan di `contextual_decision_intelligence.py` terpetakan; kode baru → `UNKNOWN`. SQLite `mode=ro` + `query_only`. Manifest dibuat ulang dengan generator |
| WP9b | Sedang dikerjakan — ChatGPT, PR #205 | [#205](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/205) | Masukan `legacy_fail_closed` vs `measured_inputs` dan decision shadow; default lama, belum mengaktifkan VPS |
| WP9c | Menunggu prasyarat (WP9a, WP9b, data shadow) + persetujuan Owner | – | – |
| WP9d | Menunggu prasyarat (WP4, WP8b) | – | – |
| WP10a | Siap dikerjakan (paralel) | – | – |
| WP10b | Menunggu prasyarat (WP8a) | – | – |
| WP12 | Koreksi inti diuji; **ditunda atas instruksi Owner**, review Claude belum selesai | [#204](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/204) | Bukti VPS: tick server ≈ UTC+3j (5 simbol; `copy_ticks_range` 3 FX); tes WP12 3/3 PASS; manifest resmi MATCH 302/302 pada clone terisolasi. **Evaluasi berikutnya (Claude):** audit `perception/screening.py` dan `scripts/ai/run_readonly_decisions.py` (timestamp mentah, tentukan pemanggil aktif dan perbaiki/karantina); uji offset historis/DST, harga tick dan batas kausal; regresi penuh Linux/Windows (suite lokal VPS 2 GB dihentikan, bukan PASS), review PR sebelum merge/deploy. Observer VPS tidak diubah, LIVE OFF. Bukti rinci di komentar PR #204. |
| WP11 | Selesai (merge); penerapan VPS di WP6 | [#201](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/201) | Diterima. `FAILED` beralasan untuk pasar yang benar-benar tutup adalah perilaku benar; kriteria R4 butir 3–4 dikoreksi. Manifest dibuat ulang dengan generator (tidak diedit tangan). Dampak ke `quote_every_cycle` (≥ 98%) diukur di WP6 |
| WP7 | Menunggu Owner | – | – |

### R6. Perintah siap pakai untuk pelaksana

Salin **dua blok** ke pelaksana: blok **R6.0 Aturan umum** (selalu) lalu blok perintah paket yang dikerjakan.
Pelaksana yang hanya diminta "baca roadmap" tetap terikat R6.0 dan memakai blok paket sebagai instruksinya.
Keduanya berdiri sendiri; pelaksana tidak perlu konteks percakapan lain.

**R6.0 Aturan umum (selalu dikirim bersama perintah paket)**
```text
Kamu pelaksana untuk repo GitHub alfaauliau-katarinaAI/Katarina-AI (sistem riset trading MT5 berbasis Python,
dokumen berbahasa Indonesia). Standar kerja ditetapkan Claude di docs/ROADMAP.md "Lampiran A". Patuhi urutan ini:

A. PAHAMI DULU, JANGAN LANGSUNG MENULIS KODE.
   1. Baca CLAUDE.md, docs/ROADMAP.md bagian "Mulai di sini", bagian 1–7, dan Lampiran A: R0, R1, R2, R3, sub-bagian
      paket yang ditugaskan di R4, R5, R7, R8, R9, R10.
   2. Baca seluruh isi setiap berkas yang disebut paket itu (bukan potongan). Telusuri pemanggil dan yang dipanggil
      dengan grep sampai kamu bisa menjelaskan alurnya.
   3. Buat PR draft lebih dulu (atau tulis di awal deskripsi PR) bagian "Pemahaman" berisi: tujuan paket dengan
      kata-katamu sendiri, daftar berkas yang AKAN diubah, daftar berkas yang TIDAK BOLEH disentuh (hasil
      `python scripts/governance/promotion_gate.py --hashes`), tes yang akan ditambah, dan risiko yang kamu lihat.
   4. Jika ada yang ambigu atau tampak bertentangan dengan roadmap, JANGAN MENEBAK: tulis pertanyaannya di PR dan
      berhenti sampai Owner/Claude menjawab.

B. KERJAKAN SESUAI R2 (cara kerja standar) DAN R8 (cara Claude menulis kode), langkah demi langkah:
   tes dulu (harus gagal sebelum perubahan), lalu kode minimal yang membuat tes lulus, tanpa memperluas cakupan.
   Ikuti gaya berkas yang diubah. Jangan refactor, rename, atau "rapikan" kode di luar paket.

C. LARANGAN MUTLAK: mengubah berkas di config/promotion_lock.json, membuat catatan promosi, mengubah Risk Governor
   atau batas 35%, mengaktifkan DEMO/LIVE atau jalur order, menambah observer/worker/thread, menambah dependensi,
   akses jaringan/MT5 di tes, mengubah VPS atau berkas di luar repo, merge sendiri, force-push, menonaktifkan tes.

D. SEBELUM MEMBUKA/MENANDAI PR SIAP:
   1. Jalankan SEMUA perintah R2 langkah 6. Semua harus lulus; manifest harus MATCH. Jika ada yang gagal karena
      lingkungan (mis. numpy tidak terpasang), perbaiki lingkungannya dan ulangi; jangan melaporkan "lulus sebagian".
   2. Periksa diri sendiri dengan daftar R7 butir 1–6, 8 dan 9, lalu salin daftarnya ke deskripsi PR dengan tanda [x] hanya
      untuk butir yang benar-benar kamu verifikasi.
   3. Dokumen sesuai R2 langkah 7 dan R9: roadmap HANYA baris paket di tabel R5 (+ satu-dua kalimat paragraf "Alat"
      bila ada CLI/modul baru). Jangan menambah sub-bagian atau log kerja ke roadmap. Tulis singkat dan faktual.
   4. Periksa diff sendiri dengan pertanyaan R8 butir 6 dan hapus baris yang tidak dibutuhkan paket.

E. DESKRIPSI PR memakai templat ini (bahasa Indonesia):
   ## Pemahaman      (dari langkah A3)
   ## Perubahan      (tabel: berkas | apa yang diubah | alasan)
   ## Keamanan       (berkas terkunci tidak berubah; LIVE OFF; tanpa perubahan VPS; tanpa dependensi baru)
   ## Pengujian      (angka persis: unit/static/integration, audit, promotion gate, manifest; tes baru apa saja
                      dan bukti bahwa tes itu gagal sebelum perubahan)
   ## Daftar periksa R7   (butir [x]/[ ])
   ## Belum yakin / pertanyaan
   Kegagalan yang ditemui dan cara memperbaikinya ditulis singkat di sini (R9), tidak di berkas repo.
   Panjang deskripsi ±40–80 baris; tabel lebih baik daripada paragraf; jangan mengulang isi roadmap.

F. Setelah PR dibuka: berhenti. Jangan mulai paket berikutnya. Tunggu review Claude.
```

**Perintah WP1**
```text
Kamu mengerjakan repo GitHub alfaauliau-katarinaAI/Katarina-AI (Python, dokumen berbahasa Indonesia).
1. Baca berurutan: CLAUDE.md, lalu docs/ROADMAP.md "Lampiran A — Rencana kerja perbaikan" sub-bagian R1, R2, R3 dan
   "WP1 — Daftar simbol eksplisit untuk observer". Ikuti R2 langkah demi langkah tanpa melompat.
2. Kerjakan HANYA WP1, satu PR ke main berjudul "WP1: daftar simbol eksplisit untuk observer".
3. Ikuti seluruh R6.0 Aturan umum (A–F): pemahaman dulu, larangan, pengecekan, templat PR, dan berhenti setelah PR.
4. Isi HANYA baris WP1 di tabel R5 docs/ROADMAP.md (status "PR dibuka", nomor PR, satu kalimat).
```

**Perintah WP2**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP1 sudah di-merge).
1. Baca CLAUDE.md, lalu docs/ROADMAP.md "Lampiran A — Rencana kerja perbaikan": R2, R3 dan "WP2 — Pengunduh tick hemat
   memori". Baca seluruh src/katarina/intelligence/operations/observation_ledger.py dan
   tests/unit/intelligence/test_observation_ledger.py sebelum mengubah apa pun.
2. Kerjakan HANYA WP2, satu PR "WP2: pengunduh tick streaming hemat memori".
3. Wajib: hasil berkas dan sha256 byte-identik dengan implementasi lama (buktikan dengan tes pembanding yang menyalin
   fungsi lama ke berkas tes), tracemalloc puncak < 50 MB untuk 2.000.000 tick/hari, tes lama tidak diubah.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris paket ini di tabel R5.
```

**Perintah WP3**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
1. Baca CLAUDE.md, lalu docs/ROADMAP.md "Lampiran A — Rencana kerja perbaikan": R1 (T5), R2, R3 dan "WP3 — Diagnosis jalur
   berita". Baca fungsi load_articles dan prepare_news di src/katarina/intelligence/cognition/observer.py,
   src/katarina/intelligence/news/news_intelligence.py dan src/katarina/intelligence/operations/data_health.py.
2. Kerjakan HANYA WP3, satu PR "WP3: diagnosis jalur berita observer".
3. Wajib: hanya menambah penghitung/laporan/tabel ledger; logika blackout, ambang, FRESH_SECONDS dan keputusan TIDAK
   berubah; verdict data_health tidak berubah (buktikan dengan tes).
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris paket ini di tabel R5.
```

**Perintah WP4**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP1–WP3 sudah di-merge).
1. Baca CLAUDE.md, lalu docs/ROADMAP.md "Lampiran A — Rencana kerja perbaikan": R1 (T4, T6), R2, R3 dan "WP4 — Jurnal
   kandidat riset". Baca dataclass ContextDecision di
   src/katarina/intelligence/cognition/contextual_decision_intelligence.py (JANGAN diubah; berkas terkunci),
   src/katarina/research/validation.py (format Trade) dan src/katarina/research/context_export.py (cara membaca tick
   Tahap 0 yang terverifikasi hash).
2. Kerjakan HANYA WP4, satu PR "WP4: jurnal kandidat riset dan replay sinyal teknis".
3. Wajib: action/keputusan observer tidak berubah (tes membuktikan kartu sama sebelum/sesudah), orders_submitted 0,
   data_until <= entry_at selalu, aturan exit dibaca dari spec hipotesis terdaftar (tanpa default di kode),
   replay hanya membaca bar yang diekspor dan menulis ke build/.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris paket ini di tabel R5.
```

**Perintah WP5**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP4 sudah di-merge).
1. Baca CLAUDE.md, docs/ROADMAP.md "Lampiran A — Rencana kerja perbaikan": R2, R3, "WP5 — Hipotesis perankingan antarpair",
   docs/research/VALIDATION_PROTOCOL.md, docs/research/MARKET_INTELLIGENCE.md, src/katarina/engines/opportunity.py
   (JANGAN diubah) dan src/katarina/research/market_intelligence.py.
2. Kerjakan HANYA WP5, satu PR "WP5: hipotesis perankingan antarpair (riset)".
3. Wajib: semua bobot dan ambang dibaca dari parameters spec yang terdaftar di HypothesisRegistry; setiap varian
   bobot adalah hipotesis baru (jumlah percobaan bertambah); korelasi dihitung kausal dari data sebelum entry;
   tidak ada perubahan pada jalur keputusan observer.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris paket ini di tabel R5.
```

**Perintah WP8a (ekspor + dataset pengembangan)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
1. Baca R6.0, CLAUDE.md, docs/ROADMAP.md Lampiran A: R2, R3, dan "WP8 — Riset historis" (aturan data, aturan
   hipotesis, langkah 1–2, dan tes langkah 7 yang terkait ekspor/dataset). Baca juga src/katarina/research/validation.py,
   src/katarina/research/context_export.py, config/observer_universe.json dan
   src/katarina/adapters/mt5_readonly_market.py.
2. Kerjakan HANYA langkah 1–2 WP8 (export_dev_bars.py + research/dev_dataset.py + tesnya), satu PR
   "WP8a: ekspor dan dataset pengembangan historis".
3. Wajib: semua bar >= 2026-10-13T00:00:00Z ditolak saat ekspor DAN saat dimuat; manifest ber-hash diverifikasi;
   tes memakai broker palsu, tanpa MT5/jaringan. Jangan menjalankan ekspor ke VPS.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris paket ini (WP8a/WP8b) di tabel R5.
```

**Perintah WP8b (setup, simulasi, perbandingan)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP8a sudah di-merge).
1. Baca R6.0, CLAUDE.md, docs/ROADMAP.md Lampiran A: R2, R3, "WP8 — Riset historis" (semua aturan dan langkah 3–7),
   docs/research/VALIDATION_PROTOCOL.md, src/katarina/research/validation.py dan src/katarina/research/dev_dataset.py.
   Jalankan `python scripts/governance/promotion_gate.py --hashes`: berkas persepsi yang terkunci boleh DIIMPOR,
   tidak boleh diubah.
2. Kerjakan HANYA langkah 3–7 WP8, satu PR "WP8b: setup BUY/SELL, simulasi dan perbandingan antarpair (riset)".
   Boleh dipecah menjadi dua PR (setup+simulasi; perbandingan) bila lebih dari ±600 baris.
3. Wajib: BUY dan SELL terpisah; semua angka dari params spec (tanpa default tersembunyi); detektor hanya memakai bar
   tertutup (buktikan dengan tes bar masa depan); invalidation-dulu bila target dan stop di bar sama; trend_side untuk
   semua trade; batas 5 hipotesis per instrumen per sisi; tidak pernah memanggil perintah holdout; keluaran berlabel
   "RISET — data pengembangan, bukan kelulusan".
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris paket ini (WP8a/WP8b) di tabel R5.
```

**Perintah WP9a (peta tembok blokir)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
1. Baca R6.0, "Mulai di sini", CLAUDE.md, docs/ROADMAP.md Lampiran A: R1 (T4–T6), R2, R3, R8, R9, R10 dan
   "WP9 — Membongkar tembok blokir" (tabel klasifikasi, aturan WP9, WP9a). Baca fungsi `evaluate` di
   src/katarina/intelligence/cognition/contextual_decision_intelligence.py (TERKUNCI, jangan diubah) dan
   src/katarina/intelligence/shadow/contextual_observation_journal.py (skema tabel contextual_decisions).
2. Kerjakan HANYA WP9a, satu PR "WP9a: peta tembok blokir keputusan (baca-saja)".
3. Wajib: baca-saja (SQLite mode=ro); pemetaan kode→kelas sebagai konstanta sesuai tabel WP9; kode tak dikenal
   dilaporkan sebagai UNKNOWN; tangga kumulatif A → A+B → A+B+C; deterministik; tanpa perubahan observer.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris WP9a di tabel R5.
```

**Perintah WP9b (input keputusan jujur + evaluasi bayangan)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP3 sudah di-merge).
1. Baca R6.0, "Mulai di sini", CLAUDE.md, docs/ROADMAP.md Lampiran A: R1, R2, R3, R8, R9, R10, "WP1" (contoh cara
   meneruskan opsi lewat rantai R3) dan "WP9" (tabel, aturan, WP9b). Baca seluruh cognition/observer.py,
   news/news_intelligence.py, operations/observation_ledger.py, dan dataclass RiskSituation/NewsContext.
   Jalankan promotion_gate.py --hashes: berkas terkunci tidak boleh diubah.
2. Kerjakan HANYA WP9b, satu PR "WP9b: input keputusan terukur dan evaluasi bayangan".
3. Wajib: default = perilaku lama (tes membuktikan kartu identik); mode measured_inputs hanya menghapus tiga
   pemblokir kelas A pada kondisi yang ditulis di WP9b dan tidak pada kondisi lain; evaluasi kedua memakai fungsi
   yang sama (tanpa menyalin logika); tabel decision_shadow; tanpa jalur order; tidak mengubah news_intelligence.py
   atau berkas terkunci; tidak mengaktifkan mode baru di VPS.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris WP9b di tabel R5.
```

**Perintah WP9c (syarat bukti proporsional — berkas terkunci)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP9a dan WP9b sudah di-merge; Claude sudah
menyerahkan laporan WP9a dan data decision_shadow ber-hash).
1. Baca R6.0, "Mulai di sini", CLAUDE.md, bagian 6 "Gerbang promosi", Lampiran A: R2, R8, R9, R10 dan "WP9"
   (aturan, WP9c). Baca seluruh cognition/contextual_decision_intelligence.py dan tesnya.
2. Kerjakan HANYA WP9c, satu PR "WP9c: syarat bukti proporsional (menunggu persetujuan Owner)".
3. Wajib: perubahan hanya dua butir WP9c; tes lama vs baru; syarat pengalaman forward tetap ditegakkan untuk
   eksekusi (buktikan dengan tes); laporan bukti build/research/wp9c_evidence.json; draf catatan promosi di
   deskripsi PR. DILARANG menjalankan promotion_gate.py --write-lock atau membuat berkas di
   docs/governance/promotions/. CI gerbang promosi boleh merah; tulis "menunggu persetujuan Owner" di PR.
4. Ikuti seluruh R6.0 Aturan umum (A–F) kecuali butir D1 untuk gerbang promosi (merah yang disengaja);
   isi HANYA baris WP9c di tabel R5.
```

**Perintah WP10a (profil spread deskriptif)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP2 sudah di-merge).
1. Baca R6.0, "Mulai di sini", CLAUDE.md, bagian 5 "Pemisahan data", "Arah lanjutan" butir 4, Lampiran A: R2, R8,
   R9, R10 dan "WP10" (tujuan, WP10a). Baca seluruh src/katarina/research/context_export.py dan tesnya, serta
   fungsi setup/collect_tick_days di src/katarina/intelligence/operations/observation_ledger.py (skema broker_tick_days).
2. Kerjakan HANYA WP10a, satu PR "WP10a: profil spread broker deskriptif (baca-saja)".
3. Wajib: iter_verified_ticks memverifikasi hash sebelum menghasilkan baris; _ticks keluarannya identik; sampel per
   menit; JSON berlabel DESCRIPTIVE_ONLY_NOT_FOR_TUNING; tes statis bahwa hanya CLI-nya yang mengimpor
   research.spread_profile; SQLite mode=ro; tanpa MT5/jaringan; tidak dijalankan ke VPS.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris WP10a di tabel R5.
```

**Perintah WP10b (swap dan sensitivitas biaya)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP8a sudah di-merge).
1. Baca R6.0, "Mulai di sini", CLAUDE.md, Lampiran A: R2, R8, R9, R10 dan "WP10" (tujuan, WP10b). Baca seluruh
   src/katarina/research/validation.py, scripts/research/validate_strategy.py, docs/research/VALIDATION_PROTOCOL.md,
   tests/unit/research/test_validation.py dan fungsi DST di src/katarina/intelligence/operations/data_health.py.
2. Kerjakan HANYA WP10b, satu PR "WP10b: swap dan sensitivitas biaya di alat validasi".
3. Wajib: field baru berdefault 0 sehingga costs.json lama menghasilkan angka identik (tes pembanding); rollover
   17:00 New York memakai ulang aturan DST yang ada (tanpa zoneinfo/tzdata); kredit swap = 0; pembanding sisi acak
   memakai swap sisinya; blok cost_sensitivity hanya informasi — verdict dan aturannya tidak berubah;
   market_intelligence.py tidak diubah.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris WP10b di tabel R5.
```

**Perintah WP11 (jam broker saat sebagian pasar tutup)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
1. Baca R6.0, "Mulai di sini", CLAUDE.md, Lampiran A: R1 (T10), R2, R3, R8, R9, R10 dan "WP11". Baca seluruh
   src/katarina/intelligence/broker/broker_clock_alignment.py dan tesnya, serta bagian infer_clock_shift di
   src/katarina/intelligence/cognition/observer.py dan tests/integration/test_brain_owned_workflow.py (MT5 palsu).
2. Kerjakan HANYA WP11, satu PR "WP11: jam broker tetap terverifikasi saat sebagian pasar tutup".
3. Wajib: hanya penyebut pecahan mayoritas yang berubah (suara segar, bukan semua simbol); min 3 suara, 70%, jendela
   umur dan rentang jam tetap; field stale_symbols; observer, backoff dan data_health tidak diubah; tes lama tidak
   diubah; tes baru sesuai WP11 butir 4.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris WP11 di tabel R5.
```

**Perintah WP12 (jam tick server → UTC)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru. Paket ini prioritas tertinggi.
1. Baca R6.0, "Mulai di sini", CLAUDE.md, bagian 5 "Pemisahan data", Lampiran A: R1 (T10, T11), R2, R3, R8, R9, R10
   dan "WP12". Baca seluruh src/katarina/intelligence/broker/causal_broker_quotes.py,
   broker/broker_clock_alignment.py, adapters/mt5_readonly_market.py (contoh koreksi bar yang sudah benar),
   cognition/observer.py, operations/observation_ledger.py, research/context_export.py dan tes-tesnya.
   Jalankan promotion_gate.py --hashes: berkas terkunci tidak boleh diubah.
2. Kerjakan HANYA WP12, satu PR "WP12: konversi jam tick MT5 server ke UTC".
3. Wajib: satu fungsi konversi; parameter server_shift_hours wajib tanpa default; konversi sebelum batas kausal;
   tanpa pergeseran terverifikasi tidak ada quote; data lama tidak ditulis ulang; baris tick lama ditolak
   context_export; broker palsu meniru jam server; tidak ada jalur order; tidak mengubah VPS.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris WP12 di tabel R5.
```

**Perintah perbaikan setelah review**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Buka PR #<nomor> dan baca semua komentar review.
Perbaiki setiap poin di branch PR yang sama (commit baru, jangan force-push), ikuti R6.0 Aturan umum dan R2,
jalankan ulang semua pengecekan R2 langkah 6, perbarui bagian Pengujian dan Daftar periksa R7 di deskripsi PR, lalu
balas setiap komentar dengan apa yang diubah (atau alasan bila tidak diubah). Jangan memperluas cakupan PR.
```

### R7. Daftar periksa review Claude (dipakai saat meninjau PR pelaksana)

1. Diff tidak menyentuh berkas di `config/promotion_lock.json`; `promotion_gate.py --check` PASS.
2. Perilaku tanpa opsi baru identik; tes lama tidak diubah kecuali paket memintanya.
3. Tidak ada jalur order, thread/worker baru, jaringan di tes, atau dependensi baru.
4. Waktu UTC ber-zona, fail-closed dengan kode alasan, SQLite di `with db:`, hasil deterministik; standar R10
   (Python 3.12, Linux + Windows, encoding, batas VPS, penamaan, tes) dipenuhi.
5. Tes baru benar-benar gagal tanpa perubahan (diverifikasi dengan membalik perubahan secara lokal).
6. CI Body, Portable Ubuntu dan Windows hijau; manifest `MATCH`; CHANGELOG, CLAUDE.md dan tabel R5 diperbarui
   sesuai R2 langkah 7 (tanpa log kerja di roadmap).
7. Untuk paket yang diterapkan ke VPS: rencana WP6 dan batas pemantauan dipenuhi sebelum dinaikkan.
8. Diff minimal (R8 butir 2): tidak ada refactor/format ulang di luar paket, tidak ada abstraksi spekulatif.
9. Dokumen dan PR mengikuti R9: tanpa log di roadmap, CHANGELOG ≤ 10 baris, deskripsi PR faktual dan ringkas.

### R8. Cara Claude menulis kode (standar yang harus ditiru pelaksana)

Prinsipnya: **perubahan terkecil yang benar, dibuktikan tes, dijelaskan singkat.** Uraian per kebiasaan:

**1. Pahami sebelum menulis.**
- Baca berkas yang akan diubah **utuh**, lalu pemanggil dan yang dipanggilnya (`grep -n "nama" -r src scripts tests`).
- Cari pola yang sudah ada dan ikuti; modul baru meniru modul sejenis terdekat (gaya, penamaan, cara error).
- Cek data nyata bila menyangkut perilaku runtime (laporan VPS, ledger) sebelum menyimpulkan penyebab.

**2. Ubah sesedikit mungkin.**
- Tambah parameter opsional dengan default yang mempertahankan perilaku lama; jangan mengubah tanda tangan yang
  sudah dipakai.
- Jangan refactor, rename, memformat ulang, atau "merapikan" kode di luar paket. Diff harus bisa dibaca baris demi baris.
- Jangan membuat abstraksi untuk kebutuhan yang belum ada (kelas basis, plugin, konfigurasi "untuk nanti").

**3. Tes membuktikan, bukan menghias.**
- Tulis tes yang **gagal** dulu, lalu kode sampai lulus. Satu tes = satu perilaku; nama tes menyebut perilakunya
  (`test_missing_core_is_wait_with_failed_quote_ledger_reason`).
- Uji jalur gagal dan batas (data kosong, duplikat, waktu naif, nilai di luar rentang), bukan hanya jalur sukses.
- Tes deterministik: waktu disuntikkan, tanpa jaringan/MT5, tanpa `sleep`, berkas sementara ditutup.
- Jangan mengubah tes lama agar lulus; bila tes lama harus berubah, jelaskan alasannya di PR.

**4. Kode yang mudah diaudit.**
- Fungsi pendek (sasaran ≤ 40 baris) dengan satu tugas; nama menjelaskan isi; konstanta bernama di atas berkas.
- Komentar menjelaskan **mengapa**, bukan mengulang apa yang dilakukan kode. Docstring modul: tujuan, tahap
  roadmap, dan batas keamanan dalam 2–5 baris.
- Kesalahan: tolak dengan kode alasan stabil; tangkap jenis exception spesifik; tidak ada `except:` kosong,
  `print` debug, kode mati, atau TODO tanpa nomor paket.
- Angka keputusan/riset tidak pernah di-hardcode diam-diam: konstanta bernama, atau dibaca dari spec/config.

**5. Akar masalah, bukan tambalan.**
- Bila tes/CI gagal, cari penyebabnya sampai bisa dijelaskan dalam satu kalimat; jangan menambah `retry`, `sleep`,
  atau mengendurkan pemeriksaan agar hijau. Contoh benar dari WP1: tes gagal karena broker sintetis kurang simbol
  untuk kuorum jam → fixture tes diperbaiki, pemeriksaan jam tidak dilonggarkan.
- Masalah lingkungan (paket tidak terpasang, path Windows) diperbaiki di lingkungan, bukan di kode produksi.

**6. Periksa diff sendiri sebelum PR** (`git diff origin/main`), dengan pertanyaan:
- Apakah ada baris yang tidak dibutuhkan paket? Hapus.
- Apakah perilaku tanpa opsi baru identik? Buktikan dengan tes lama yang lulus tanpa diubah.
- Apa yang membuat CI Windows gagal (path, koneksi SQLite terbuka, CRLF)? Apa yang membuat VPS RAM 2 GB berat?
- Apakah ada jalur order, worker, jaringan, atau berkas terkunci yang tersentuh? Harus tidak.

### R9. Aturan menulis dokumen dan PR (singkat, padat, tidak berulang)

| Tempat | Isi | Batas |
|---|---|---|
| Roadmap | Baris status paket di R5; satu-dua kalimat di paragraf "Alat" tahap terkait | Tanpa sub-bagian baru, tanpa log |
| `CHANGELOG.md` | Apa yang berubah dan mengapa, satu entri per PR | ≤ 10 baris |
| `CLAUDE.md` | Hanya bila CLI/modul baru atau angka tes/peta modul berubah | ≤ 2 baris per perubahan, di tabel/baris yang tepat |
| Deskripsi PR | Templat R6.0 E | ±40–80 baris; tabel lebih baik daripada paragraf |
| Komentar review/jawaban | Apa yang diubah atau alasan tidak diubah | Beberapa kalimat |
| Pesan commit | Kalimat perintah singkat dalam bahasa Indonesia, lalu baris kosong dan alasan bila perlu | Judul ≤ 72 karakter |

Cara menulis:
- Tulis fakta yang dapat diperiksa (nama berkas, fungsi, angka hasil tes), bukan klaim umum ("sudah aman",
  "sangat robust").
- Satu fakta ditulis di satu tempat; tempat lain cukup merujuk. Jangan menyalin isi roadmap ke PR atau sebaliknya.
- Hapus kalimat pembuka/penutup yang tidak berisi informasi, pengulangan larangan yang sudah ada di R6.0, dan daftar
  "yang tidak dilakukan" yang panjang; cukup satu baris Keamanan.
- Kegagalan ditulis jujur dan singkat: apa yang gagal, penyebab, apa yang dilakukan.

Contoh buruk (jangan ditiru): sub-bagian "R5A" sepanjang ±150 baris di roadmap berisi riwayat commit, daftar seluruh
berkas, dan narasi proses. Contoh baik: satu baris R5 — `| WP1 | Selesai (merge) | #184 | path tes absolut; log
dikeluarkan dari roadmap |` — dan rincian prosesnya di deskripsi PR.

### R10. Standar teknis lengkap (pelengkap R2 dan R8)

**Lingkungan**
- Python **3.12** (CI dan VPS). Jangan memakai fitur yang hanya ada di 3.13+. Dependensi hanya yang sudah ada
  (`requirements-stage07.txt` + `numpy`; paket `MetaTrader5` hanya di VPS, tidak pernah diimpor di tes).
- Kode harus jalan di **Linux dan Windows** (CI menjalankan keduanya; VPS Windows Server 2012 R2):
  `pathlib.Path` untuk path, `encoding="utf-8"` di setiap open/read/write teks, `newline="\n"` saat menulis berkas
  yang di-hash, tanpa symlink, tanpa perintah shell khusus satu OS, koneksi SQLite/berkas selalu ditutup.
- Batas VPS (RAM 2 GB, observer 60 detik/siklus): pekerjaan di thread observer harus terbatas (anggaran per
  siklus, ≤ ±5 detik tambahan); data besar diproses per potong (streaming), bukan dimuat utuh.

**Struktur dan penamaan**
- Logika di `src/katarina/...`; skrip di `scripts/...` hanya CLI tipis (argparse → panggil fungsi `src`), dengan
  `sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))` seperti skrip yang ada.
- Tes: `tests/unit/<area>/test_<modul>.py` untuk logika murni; `tests/integration/test_<fitur>.py` untuk alur
  observer/CLI dengan broker sintetis. Kelas `unittest.TestCase`; path berkas repo di tes dihitung dari
  `Path(__file__).resolve().parents[N]`, tidak bergantung direktori kerja.
- Nama: modul dan fungsi `snake_case`, kelas `PascalCase`, konstanta `HURUF_BESAR`, kode alasan
  `HURUF_BESAR_GARIS_BAWAH`. Nama menjelaskan isi (`collect_tick_days`, bukan `process`).
- Modul baru wajib tersambung (diimpor oleh kode/skrip/tes) agar `tests/static/test_module_connectivity.py` lulus.

**Data dan waktu**
- Waktu: `datetime` ber-zona UTC; simpan sebagai ISO 8601 (`.isoformat()`); waktu pasar dari `time_msc` MT5.
- Uang/harga: `float` dengan pemeriksaan `math.isfinite`; satuan selalu disebut (price, point, R).
- Format berkas: JSON kanonik (`sort_keys=True`), JSON lines untuk baris data, CSV gzip (`mtime=0`, tanpa nama)
  untuk data besar; setiap dataset/laporan yang dipakai keputusan punya SHA-256.
- Tidak pernah commit data broker, state runtime, kredensial, nomor akun, atau nama server ke repo.

**Git dan PR**
- Branch: `<agen>/wpN-<ringkas>-YYYYMMDD` dari `origin/main` terbaru. Commit kecil dan bermakna; tanpa force-push;
  bila `main` bergerak, gabungkan dengan merge commit.
- Commit: judul kalimat perintah bahasa Indonesia ≤ 72 karakter (mis. `WP2: tulis tick per jam secara streaming`),
  baris kosong, lalu alasan singkat bila perlu.
- PR memakai templat R6.0 E; satu PR hanya satu paket; deskripsi berisi angka hasil pengecekan R2 langkah 6.

**Keamanan (tidak bisa ditawar)**
- Tidak ada `order_send`, jalur eksekusi, atau perubahan kewenangan; observer tetap 0 order.
- Berkas di `config/promotion_lock.json` tidak disentuh; perubahan perilaku keputusan selalu lewat hipotesis →
  validasi → catatan promosi → persetujuan Owner.
- Data holdout (≥ 13 Okt 2026 00:00 UTC) tidak dipakai untuk memilih/menyetel apa pun.
