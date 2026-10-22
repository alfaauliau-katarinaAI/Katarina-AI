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

## Catatan implementasi — 22 Oktober 2026

Pekerjaan berikut sudah direview dan digabung ke `main` (22 Okt 2026, merge #177 → #178 → #179).
Ini kemajuan perangkat lunak, bukan
kelulusan tahap, bukti profit, atau izin mengirim order. Pengumpulan ≥ 10 hari bursa Tahap 0
tetap berjalan; persiapan tahap berikutnya tidak perlu menunggu pengumpulan tersebut selesai.

| Tahap | Perubahan yang tersedia | Bukti / PR | Status |
|---|---|---|---|
| 0–1 | Deduplicasi pemulihan reconnect, timeout sejak kegagalan pertama; penolakan outcome masa depan, CELAH, baseline tidak lengkap, mismatch hash kode dan penggunaan ulang holdout pasca-paparan | [#177](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/177) | Penguatan alat; bukan kelulusan observasi/strategi |
| 2 | Eksperimen filter pasar pada data pengembangan memakai registry, split, biaya dan validasi Tahap 1; alasan WAIT dan perbandingan sebelum/sesudah filter. Ekspor `contexts.jsonl` ber-lineage dari tick broker Tahap 0 (`export_market_contexts.py`) | [#178](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/178), [panduan](research/MARKET_INTELLIGENCE.md) | Persiapan riset; filter aktif belum diubah |
| 3 | Adapter pembatas risiko DEMO dan laporan deterministik dari outbox existing secara baca-saja | [#179](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/179), [panduan](research/DEMO_READINESS.md) | Implementasi persiapan diuji; belum dihubungkan ke worker aktif |


Rincian Tahap 3 untuk review:

- `src/katarina/research/demo_readiness.py`: `DemoRiskOverlay` mempertahankan veto Risk Governor,
  hanya menurunkan anggaran risiko atau menghentikan entry. Nilai batas wajib eksplisit;
  **0,5% per trade / 3% stop harian masih usulan dan parameter tes**, bukan profil final Owner.
- `scripts/research/check_demo_readiness.py`: laporan expectancy bersih, profit factor, drawdown
  terealisasi menurut urutan observasi, win rate BUY/SELL per regime, biaya, slippage per simbol,
  alasan WAIT, order ditolak dan status rekonsiliasi tersimpan. Win rate bukan akurasi probabilitas.
- Hanya CLOSED valid masuk metrik hasil. Status tak jelas, outcome invalid, dan posisi duplikat
  membuat rekonsiliasi tidak lengkap. Data kosong tidak dianggap lulus. Laporan ini bukan audit broker
  langsung atau bukti bahwa rekonsiliasi demo nyata sudah 100%; drawdown tidak mencakup posisi terbuka.
- Bukti implementasi commit `c0f90edddc5ff4ae57aea2936e1f86332386d890`: 13 tes baru;
  regresi lokal 1.218 unit, 71 static (4 skip), 205 integration lulus.
  [CI 39729427927](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/39729427927)
  lulus untuk Body, portable Windows dan Ubuntu. Bukti ini merujuk commit implementasi sebelum
  penambahan catatan roadmap ini.

Yang masih harus dibuktikan: kelulusan data Tahap 0, hasil validasi/filter dari data yang sah,
profil DEMO final dari Owner, dan rekonsiliasi broker nyata sesuai kriteria tahap.
Holdout privat tetap `BLOCKED_PRIVATE_INPUT_FILES_NOT_PROVIDED`; tidak ada klaim alpha lulus.
Kelulusan tahap dan promosi tetap berurutan; LIVE OFF dan batas utama 35% tetap berlaku.

## Rencana kerja perbaikan — 22 Oktober 2026 (untuk pelaksana)

Disusun dari pemeriksaan VPS dan repo 22 Okt malam, plus usulan "Multi-Pair Opportunity Hunter" dari review PM
(Yura). Pelaksana (ChatGPT/Codex) mengerjakan paket di bawah **berurutan**; Claude meninjau dan menyempurnakan
setiap PR sebelum merge. Rencana ini tidak mengubah tahap, kriteria kelulusan, atau aturan di dokumen ini.

### Temuan yang mendasari (bukti 22 Okt, VPS `30d043c`, 600+ siklus)

| # | Temuan | Bukti |
|---|---|---|
| T1 | Observer hanya mengamati `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx`. Program holdout butuh 7 simbol; Tahap 4 mulai dari XAUUSD | `--max-symbols 3` memotong urutan tetap `MAJORS` di `broker/broker_scan_universe.py`; `JPN225` tidak ada di universe sama sekali |
| T2 | Ketujuh simbol tersedia dan bisa ditrade di broker: `XAUUSD.vx`, `NAS100.vx`, `US30.vx`, `JPN225.vx`, `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx` (`trade_mode=4`; versi tanpa `.vx` `trade_mode=0`) | Probe baca-saja: baca 4 timeframe + tick 90 dtk ≈ 0,2–1,4 dtk/simbol (±5 dtk untuk 7); RAM bebas ±885 MB dari 2 GB |
| T3 | Tick satu hari penuh XAUUSD ≈ 355 ribu; `collect_tick_days` menampung seluruh hari di memori (±100–150 MB) sebelum menulis | `operations/observation_ledger.py::_fetch_day` |
| T4 | 100% keputusan WAIT dengan 7 pemblokir permanen: `system_unhealthy`, `insufficient_verified_forward_experience`, `no_verified_relevant_news`, `high_impact_news_blackout`, `macro_event_risk_too_high`, `macro_policy_transmission_not_verified`, `no_confirmed_closed_candle_entry` | Tabel `contextual_decisions`, 381 baris |
| T5 | "Tidak ada berita segar yang cocok" diperlakukan sebagai blackout dengan risiko 1,0, padahal kalender `calendar_verified_clear`. Artikel resmi tersimpan: 0 (feed Fed/ECB/BoE terambil OK 41×); kemungkinan karena tidak ada rilis dalam jendela 6 jam, belum terdiagnosis | `news/news_intelligence.py::assess` (cabang `if not matched`), `cognition/observer.py::load_articles`, `news/verified_policy_context.py::FRESH_SECONDS` |
| T6 | Observer selalu mengirim `system_healthy=False` dan `resolved_experience=[]` (sengaja fail-closed). Akibatnya jurnal tidak pernah berisi kandidat BUY/SELL untuk riset | `cognition/observer.py` sekitar `RiskSituation(...)` |
| T7 | `engines/opportunity.py::MultiMarketOpportunityEngine` hanya dipakai tes; bobot skornya (0,65/0,35/0,55/…) belum pernah divalidasi dan ia membuang kandidat bila `news.ready` salah | Peta modul kategori B |
| T8 | Mode `KATARINA_ALL_MARKET_RESEARCH` merotasi 3 simbol per siklus dari 73 (paling lama tak dikunjungi) dan menyalakan worker riset + koneksi tambahan; memutus data per siklus 7 simbol inti dan berat untuk RAM 2 GB | `lab/continuous_research_lab.py::select_batch`, `cognition/continuous_observation.py` |
| T9 | VPS tertinggal dari `main`; tugas observer hanya jalan saat Administrator login | `git log` VPS, Task Scheduler (trigger logon) |

### Aturan untuk pelaksana (wajib)

1. Satu paket = satu PR ke `main`, judul diawali `WPn:`. Jangan menggabungkan paket.
2. **Dilarang** mengubah berkas di `config/promotion_lock.json`, membuat catatan promosi, mengubah Risk
   Governor/batas 35%, mengaktifkan DEMO/LIVE, atau menambah observer/worker paralel. Jika sebuah paket ternyata
   membutuhkan perubahan berkas terkunci, berhenti dan tulis usulan di deskripsi PR.
3. Setiap PR menjalankan dan mencantumkan hasil: tiga suite tes (lihat `CLAUDE.md`), `audit_repo_hygiene.py`,
   `audit_dependency_links.py`, `promotion_gate.py --check`, dan manifest rilis dibuat ulang lalu `MATCH`
   (jalankan `git add` dulu; generator ikut membaca berkas yang belum di-commit).
4. Perbarui `CHANGELOG.md`, `CLAUDE.md` (bila struktur/CLI berubah) dan bagian status paket di tabel bawah.
5. Tidak ada perubahan VPS di PR. Penerapan ke VPS dilakukan Claude setelah merge (paket WP6).
6. Tes memakai broker palsu; tidak ada akses jaringan atau MT5 di tes.

### Paket kerja

**WP1 — Daftar simbol eksplisit untuk observer (Tahap 0, prioritas tertinggi)**
- Tambah `config/observer_universe.json`: `core` = 7 simbol program dengan urutan
  `XAUUSD.vx, NAS100.vx, US30.vx, JPN225.vx, EURUSD.vx, GBPUSD.vx, USDJPY.vx` (salin dari
  `config/research/alpha_regime_program_v1.json`, jangan diketik ulang berbeda), `rotating_slots` = 0 (default).
- `run_contextual_market_observer.py`: opsi `--universe PATH`. Bila dipakai, observer mengamati **semua** simbol
  `core` setiap siklus (tidak dipotong `--max-symbols`) ditambah `rotating_slots` simbol lain via `select_batch`
  yang **tidak** menyertakan simbol core. Tanpa `--universe`, perilaku lama tidak berubah.
- Validasi ke katalog broker: simbol harus ada dan `trade_mode in (1,2,4)`; simbol core yang hilang/nonaktif
  dicatat di laporan siklus (`unavailable_symbols`) dan di ledger sebagai baris `FAILED` beralasan, tidak diganti
  diam-diam.
- Batas: total simbol per siklus ≤ 17 (aturan yang sama dengan `max_17_broker_markets`).
- Tes: urutan core dipertahankan; core tidak ikut rotasi; simbol hilang menjadi FAILED beralasan; tanpa
  `--universe` hasil sama seperti sekarang; `test_module_connectivity` tetap lulus.
- Kriteria selesai: tes di atas + `--universe` terdokumentasi di Tahap 0 roadmap.

**WP2 — Pengunduh tick hemat memori (Tahap 0)**
- `observation_ledger._fetch_day`/`_write_ticks`: tulis per jam secara streaming ke gzip (urut, dedup per jam,
  tanpa menampung seluruh hari), hitung SHA-256 dari isi CSV tak terkompresi secara bertahap; hasil harus
  **byte-identik** dengan implementasi sekarang untuk input yang sama (tambahkan tes pembanding).
- Rekonsiliasi snapshot tetap benar tanpa memuat semua tick (mis. baca ulang per jam atau indeks waktu per jam).
- Tes: 2 juta tick sintetis/hari tetap lulus dengan memori puncak terukur (`tracemalloc`) < 50 MB.

**WP3 — Diagnosis jalur berita (Tahap 0–2, hanya diagnosis + observabilitas)**
- Catat di laporan siklus untuk tiap sumber: jumlah item feed, item terbaru `published_utc`, jumlah yang masuk
  jendela `FRESH_SECONDS`, jumlah percobaan ambil artikel, hasil (OK/HTTP/parse/backoff).
- Tambah kriteria informatif (bukan kriteria kelulusan) di `data_health`: `news_pipeline` dengan angka di atas.
- **Jangan** mengubah logika blackout atau ambang. Keluaran paket ini adalah laporan yang membedakan
  "tidak ada rilis resmi" dari "pengambilan gagal".

**WP4 — Jurnal kandidat riset terpisah dari izin entry (Tahap 1–2)**
- Modul baru `intelligence/operations/candidate_ledger.py`, dipanggil observer setelah keputusan dibuat:
  untuk setiap simbol catat sinyal teknis mentah yang **sudah ada** di kartu (sisi, `selected_method`, regime,
  `evidence_score`, `rr_after_spread_estimate`, invalidation/target, spread, waktu candle tertutup) beserta
  daftar pemblokir. Tidak ada logika keputusan baru, tidak ada skor baru, tidak memengaruhi `action`.
- Ekspor ke format `Trade` Tahap 1 (`research/validation.py`) dengan exit dari tick broker Tahap 0 (aturan
  exit harus didaftarkan sebagai hipotesis; contoh di dokumen, bukan default aktif).
- Tes: kandidat tercatat walau `action=WAIT`; observer tetap 0 order; `data_until ≤ entry_at` dijamin.

**WP5 — Hipotesis perankingan antarpair (Tahap 2, riset saja)**
- Script `scripts/research/rank_candidates.py` yang membaca jurnal WP4, menerapkan
  `MultiMarketOpportunityEngine` (atau varian berparameter) **dalam mode riset**, dan menyiapkan input
  `validate_strategy.py market-filter`. Bobot ranking, filter korelasi dan batas portofolio didaftarkan sebagai
  hipotesis di registry (jumlah percobaan tercatat) sebelum dijalankan.
- Tidak dipasang ke jalur keputusan. Pemasangan hanya lewat gerbang promosi setelah lulus Tahap 2/4 dan disetujui
  Owner.

**WP6 — Penerapan VPS bertahap (dikerjakan Claude setelah WP1–WP3 merge)**
- Tarik `main`, manifest `MATCH`, restart observer dengan `--universe`.
- Tahap A: core 5 simbol (3 sekarang + XAUUSD, NAS100) selama ≥ 2 jam; lanjut ke 7 hanya jika durasi siklus
  < 20 dtk, RAM bebas > 500 MB, 0 siklus gagal, dan unduhan tick hari penuh selesai tanpa error.
- Ubah tugas terjadwal agar observer tetap jalan setelah VPS restart (trigger startup + sesi MT5 yang login
  otomatis, atau auto-logon) dan uji sekali dengan restart terencana di akhir pekan.
- Catat di ROADMAP: tanggal mulai cakupan 7 simbol (periode sebelumnya untuk 4 simbol baru = CELAH).

**WP7 — Keputusan Owner (bukan kode)**
- Profil DEMO final Tahap 3 (usulan 0,5%/trade, 3%/hari sebagai lapisan pengetat di atas batas utama 35%).
- Aturan berita: apakah "tidak ada rilis resmi" boleh dibedakan dari blackout. Perubahan ini menyentuh logika
  keputusan; hanya boleh lewat hipotesis + validasi + catatan promosi setelah data WP3/WP4 tersedia.
- Repo private atau tidak; status issue lama #21, #24, #29, #31.

### Status paket

| Paket | Status | PR | Catatan review Claude |
|---|---|---|---|
| WP1 | Belum dimulai | – | – |
| WP2 | Belum dimulai | – | – |
| WP3 | Belum dimulai | – | – |
| WP4 | Belum dimulai | – | – |
| WP5 | Belum dimulai | – | – |
| WP6 | Menunggu WP1–WP3 | – | – |
| WP7 | Menunggu Owner | – | – |

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
snapshot dalam satu tick size). Uji putus-sambung dicatat dengan `scripts/ai/record_reconnect_test.py` (lulus bila
siklus OK berikutnya ≤ 10 menit setelah gangguan). `python scripts/ai/check_stage0_health.py --state-dir <state>` menilai kriteria di
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
