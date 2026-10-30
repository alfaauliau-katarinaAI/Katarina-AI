# Roadmap Katarina AI — berbasis bukti

Ditetapkan Owner (pemilik proyek) pada **22 Oktober 2026**; disempurnakan hari yang sama setelah review PM
(dua aliran data, paralel vs berurutan, celah holdout dan PENDING, profil DEMO vs Stage 38) dan dirapikan
23, 29, dan 30 Oktober 2026. Dokumen ini menjadi dasar pengembangan Katarina berikutnya.

**Cara membaca dokumen ini**

- Bagian 1–7 adalah **aturan tetap**: prinsip, kewenangan, pemisahan data, gerbang promosi, dan kriteria kelulusan
  tiap tahap. Mengubahnya butuh persetujuan Owner dan catatan di `CHANGELOG.md`.
- **Lampiran A** adalah **rencana kerja berjalan** untuk pelaksana (AI lain atau manusia): urutan dan alur kerja (R0),
  temuan (R1), cara kerja standar (R2), peta berkas (R3), langkah per paket (R4), status (R5), perintah siap pakai
  (R6), daftar periksa review (R7), cara menulis kode (R8), aturan menulis dokumen/PR (R9), dan standar teknis (R10).
- **Fungsi roadmap ini: perjalanan Katarina.** Isi hanya tujuan, tahap, gerbang kelulusan, milestone, antrean
  paket, dependensi, dan progres paket/keputusan yang **sudah disahkan**. Bukan notula, arsip perbaikan, atau log kerja.
- **Tiga jalur Owner (30 Okt 2026):** [ROADMAP](ROADMAP.md) = perjalanan dan pekerjaan yang disetujui;
  [MEETING](ROADMAP_DISCUSSION.md) = usulan, pertanyaan, dan keputusan yang masih dibahas;
  [REPAIR_HISTORY](REPAIR_HISTORY.md) = perbaikan nyata, berkas yang berubah, tes, bukti, serta risiko tersisa.
- Dokumen pendukung tidak digandakan: [PROJECT_STATUS](PROJECT_STATUS.md) = status operasional terkini;
  [CHANGELOG](../CHANGELOG.md) = ringkasan teknis per PR/commit; deskripsi PR = detail diff/review;
  [CLEANUP_PLAN](maintenance/CLEANUP_PLAN.md) = aturan perapian. **Tidak ada log kerja atau transkrip rapat di roadmap.**

## Mulai di sini — untuk pelaksana AI (ChatGPT, Codex, atau AI lain)

**Peran (keputusan Owner, 29 Okt 2026):** Owner → **ChatGPT = manager** → **Claude = eksekutor**. ChatGPT memegang
arah kerja: menyusun dan mengubah roadmap, antrean, spesifikasi paket dan prioritas, membagi tugas, me-review dan
me-merge, serta memakai repo dan VPS sepenuhnya. Claude mengeksekusi rencana ChatGPT (kode, PR, CI, penerapan VPS)
dan melaporkan hasil, risiko teknis, dan bukti; keberatan teknis disampaikan di rapat, bukan dengan menahan pekerjaan.

**Langkah kerja**
1. Baca `CLAUDE.md`, bagian 1–7 (aturan tetap Owner), lalu Lampiran A sesuai kebutuhan.
2. ChatGPT menentukan paket berikutnya di tabel "Antrean kerja" (boleh mengubah urutan atau isinya) dan siapa yang
   mengerjakan (ChatGPT sendiri atau Claude).
3. Pelaksana mengerjakan sesuai R4/R6 dan standar R2/R8/R10, lalu membuka PR dari `origin/main`.
4. PR di-merge setelah CI hijau oleh ChatGPT atau Claude; Claude menerapkan ke VPS bila diminta dan mencatat di
   PROJECT_STATUS.

**Antrean kerja (urut; ditetapkan ChatGPT, diperbarui setiap merge)**

**Audit kelemahan dan pembaruan 30 Okt 2026:** [Laporan Claude — kelemahan dan tugas perbaikan](maintenance/KATARINA_WEAKNESSES_CLAUDE_REVIEW_20261030.md) mencatat prioritas K-01 s.d. K-10 serta status code/CI/VPS; status real-time di [PROJECT_STATUS](PROJECT_STATUS.md).

**Urgensi disepakati Owner, 30 Oktober 2026:** stabilkan bukti observasi 10 hari bursa dan validasi jam broker **lebih dulu**. Penyelesaian kode, merge, deployment, serta kelulusan hari bursa **empat status terpisah**. Detail diagnosis/hasil perbaikan ada di [REPAIR_HISTORY](REPAIR_HISTORY.md), status mesin sesaat di [PROJECT_STATUS](PROJECT_STATUS.md). Google Jules hanya menulis kode GitHub; tidak mengoperasikan VPS.

| # | Paket / alur | Prioritas dan keluaran yang harus terbukti | Pelaksana dan status |
|---|---|---|---|
| 0 | **Tahap 0 — observasi 10 hari bursa** | Jaga satu observer resmi read-only; audit per hari/simbol sejak 28 Okt 16:57 UTC (cutoff WP12), target streak 10 hari, sukses siklus ≥98%, rekonsiliasi tick/snapshot, cakupan dan gap, restart otomatis dan **0 order**. Jangan menghitung backfill sebagai forward atau mengklaim lulus sebelum bukti. | **P0 / berjalan** — Yura pantau, Claude verifikasi bukti VPS; **belum lulus** |
| 1 | **WP13 — jam broker MT5 dan `--since`** | [PR #233](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/233): jam live = NTP host tepercaya + ≥ 3 tick bergerak (D6/D7), siklus gagal tercatat `FAILED` + alasan, `--since` untuk Tahap 0. Spesifikasi terbaru di R4 WP13. | **P0 / MERGE BLOCKED** — HEAD `3532399` (bot Jules, 30 Okt 17:28 UTC) menghapus guard NTP; pulihkan dari `76ce7e8` oleh manager/Claude (D7-M8), task Jules WP13 di-pause (D7-M12), lalu review ulang SHA final. **Bukan tugas Jules.** NTP VPS `MaxPollInterval` 13 sejak 31 Okt (D7-M13); deploy WP13 tetap butuh izin terpisah |
| 1b | **WP15 — rollover Tahap 0 ikut 17:00 New York** | Jendela pengecualian rollover di statistik Tahap 0 mengikuti 17:00 `America/New_York` (DST AS berakhir 1 Nov 2026), tanpa mengubah ledger, arsip tick, atau penilaian sebelum tanggal berlaku. | **P1 / Siap — Jules** (Owner D7-M15). Mendesak: sejak 1 Nov rollover pindah ke 22:00 UTC |
| 2 | **WP8c — asal waktu bar historis** | Bukti UTC bar memakai rilis NFP yang terverifikasi dan tes deterministik; jangan ekspor data development tanpa bukti jam atau sentuh holdout. | **Kode selesai (merge #230, 30 Okt)** — fail-closed diperbaiki Claude; kalender rilis resmi + laporan sampel belum ada, jadi ekspor tetap ditolak |
| 3 | **WP10b — swap & sensitivitas biaya** | CostModel swap BUY/SELL, rollover New York/DST dan sensitivitas 1,5×/2×; perbaikan baseline random-side; tidak mengubah gate promosi. | **P1 / kode MERGED [PR #225](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/225)** — CI Body/Linux/Windows PASS; belum validasi broker/VPS atau strategi |
| 4 | **Tata kelola PR** | Aturan `main`: ≥ 1 approval independen, CI Body/Ubuntu/Windows wajib, approval usang gugur saat HEAD berubah, tanpa force-push. | **Disetujui Owner (D7-M14), belum aktif** — butuh admin repo; #216/#218 merged 30 Okt |
| 5 | **WP6 — pemulihan setelah reboot** | Verifikasi scheduled task observer yang kini hanya saat login; uji recovery dengan risiko observasi minimal. Penambahan 5→7 simbol tetap **menunggu WP13 + bukti jam 21:00–22:00 UTC**, tidak boleh mendahului kelulusan data. | **P1 / belum terverifikasi** — Claude |
| 6 | **WP10a** | Profil spread broker deskriptif dari tick forward terverifikasi, bukan penyetelan strategi. | **Selesai (merge #231, 30 Okt)**; belum dijalankan di VPS |
| 7 | **WP4** | Jurnal kandidat riset + replay sinyal teknis tanpa mengubah keputusan aktif. | **P2 / antrean [Issue #229](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/229)** — tunggu WP13 dan kapasitas Jules |
| 8 | **WP14** | Auditor data baca-saja dengan keluaran PASS/BLOCKED/NO_DATA yang bersumber. | **P2 / menunggu WP13 dan WP8c** |
| 9 | **WP8d — CLI sampel bukti jam bar** | Alat yang mengubah kalender rilis resmi + bar M5 broker di sekitar rilis menjadi laporan bukti WP8c (`bars_sha256` per sampel); fail-closed bila konsensus kurang. | **P2 / Siap — Jules**; dijalankan Claude di VPS saat pasar tutup setelah kalender BLS diisi |
| 10 | **WP16 — OAuth gateway tanpa paparan profil** | `/oauth/status` tidak lagi mengembalikan profil MQL5; bind default `127.0.0.1`; tes statis. | **P2 / Siap — Jules** (manager D7-M4: perbaiki, bukan hapus) |
| – | **WP8b, WP9c, WP9d, WP5** | Setup, syarat bukti, entry, dan perankingan; hanya setelah prasyarat R0 terpenuhi. | **Menunggu prasyarat** |

**Handoff Google (31 Okt):** WP10b #225, WP8c #230, WP10a #231 merged. Jules **tidak** mengerjakan WP13 lagi: dua kali (`686d1e7`, `3532399`) bot Jules memublikasikan pohon sandbox lama ke PR #233 dan menghapus guard yang dipulihkan manager. Paket Jules berikutnya: **WP15 → WP8d → WP16**, lalu WP4 dan WP14 setelah WP13 merge. Perintah induk Jules ada di **R6.J**; aturan anti-regresi wajib. Jules tidak memiliki akses VPS, data broker privat, merge, atau kewenangan promosi.


**Akses**

| Peserta | Akses |
|---|---|
| ChatGPT (manager) | Penuh: seluruh repo termasuk `docs/ROADMAP.md`, antrean, Lampiran A, rapat; membuat/me-merge PR; VPS lewat Desktop Commander; menugasi Claude |
| Claude (eksekutor) | Penuh untuk mengeksekusi: kode, PR, merge setelah CI hijau, VPS; mengikuti rencana ChatGPT dan melaporkan hasil |
| Owner | Di atas keduanya; satu-satunya yang mengubah bagian 1–7 dan menyetujui promosi/kenaikan kewenangan |

**Aturan tetap Owner** (bagian 1–7, berlaku untuk semua peserta, hanya Owner yang mengubah): LIVE OFF; Risk
Governor independen dan batas drawdown 35%; berkas di `config/promotion_lock.json` berubah hanya dengan catatan promosi
yang disetujui Owner (ditegakkan CI); holdout dibuka sekali per strategi final dan tidak dipakai menyetel; kenaikan
tangga kewenangan (DEMO/LIVE) hanya dengan persetujuan Owner.

**Kebiasaan kerja yang terbukti mencegah masalah** (saran teknis Claude, bukan larangan): satu paket satu PR;
manifest dibuat dengan generator; perubahan VPS dicatat di PROJECT_STATUS dan dilakukan satu per satu dengan
observer resmi tetap berjalan (27–28 Okt observer resmi sempat mati ±21 jam saat diganti worker uji).

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
  forward; baris tick tanpa `server_shift_hours` ditolak alat riset. **WP12 diterapkan 28 Okt 2026 16:57 UTC** (`main`
  `18e2515`); data forward harga yang sah dimulai di sini. Observer resmi berhenti 27 Okt 19:35 – 28 Okt 16:57 UTC
  (CELAH); data worker uji terpisah (`state\stage0-10day-20261028`, kode belum di-merge) bukan bukti.
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
snapshot dalam satu tick size), streaming per jam (WP2). Waktu tick MT5 (jam server) dikonversi ke UTC dengan offset
terverifikasi siklus itu (WP12); hari dengan dua offset dicatat `GAP`. Uji putus-sambung dicatat dengan `scripts/ai/record_reconnect_test.py` (lulus bila
siklus OK berikutnya ≤ 10 menit setelah gangguan). `python scripts/ai/check_stage0_health.py --state-dir <state>` menilai kriteria di
bawah (PASS / NOT_MET / NO_DATA) secara read-only. Simbol inti dipilih dengan `--universe config/observer_universe.json` (WP1, #184): ketujuh simbol program diamati
setiap siklus dengan XAUUSD pertama; simbol inti yang tidak tersedia menjadi WAIT dan baris ledger `FAILED` beralasan
`CORE_SYMBOL_UNAVAILABLE`, tidak pernah diganti diam-diam; tanpa opsi, perilaku lama tetap.
Diagnostik berita per sumber dan per siklus ada di tabel `observer_news` (WP3); keputusan mode alternatif di `decision_shadow` (WP9b).
Statistik siklus memakai jendela konservatif Senin 00:00 – Jumat
20:00 UTC tanpa rollover 20:45–21:15 UTC. Status tahap: **belum lulus**; hitungan 10 hari dimulai saat WP12 diterapkan (28 Okt 2026 16:57 UTC).

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

**Prioritas terdekat:** lihat "Antrean kerja" di awal dokumen. Arah ini tidak memberi kewenangan trading.

### Usulan agentic AI (Owner 27 dan 29 Okt; ditinjau Claude 29 Okt)

**Keputusan review:** diterima sebagai arah. Tidak ada subsistem baru: setiap kemampuan memakai modul yang sudah ada.
Satu paket baru: WP14 (auditor data baca-saja), **disetujui Owner 29 Okt**, masuk antrean setelah WP13 dan WP8c.
Antrean kerja, gerbang promosi, LIVE OFF, Risk Governor dan batas 35% tidak berubah.

| Kelemahan | Sudah ada | Belum terbukti | Perlu dibangun |
|---|---|---|---|
| P1 integritas waktu/data | WP12 (jam tick → UTC), ledger + `check_stage0_health.py` harian, WP9a | Tahap 0 belum lulus; offset akhir pekan (T12); jam bar historis | WP13, WP8c (antrean); WP14 auditor |
| P2 keunggulan setelah biaya | Alat Tahap 1: registry berantai hash, pembanding, bootstrap, `HoldoutVault` | Belum ada satu strategi pun yang lulus | WP10b (biaya), WP8b (setup) — sudah di roadmap |
| P3 tugas jangka panjang | Modul lama `lab/continuous_research_lab.py`, `lab/autonomous_research.py` | Checkpoint, anggaran, pemulihan belum diuji | Paket baru **setelah** Tahap 1 lulus untuk satu strategi |
| P4 bukti virtual vs eksekusi | Tangga kewenangan memisahkan paper/DEMO; `decision_shadow`; `demo_readiness.py` | Belum ada fill DEMO | Tidak ada paket baru; ikuti Tahap 3 |
| P5 kesiapan operasional | Kriteria Tahap 0–3, WP6 butir 4 (restart), bagian "Sebelum akun riil" | Restart VPS tanpa login; Tahap 0–3 belum lulus | WP6 butir 4 (Claude) |

**Jawaban pertanyaan 3:** ya. Auditor data baca-saja boleh disiapkan setelah WP13 dan WP8c tanpa menunggu Tahap 1,
karena hanya membaca data dan tidak memilih atau menyetel strategi.

Spesifikasi WP14 ada di Lampiran A R4.

**Keputusan visi Owner, 29 Okt 2026 — Katarina agentic AI yang mandiri:** tujuan jangka panjangnya
bukan sekadar menghasilkan sinyal, melainkan mampu mengamati, mencari informasi, bernalar, meneliti,
menguji, mengingat hasil, dan mengusulkan peningkatan secara berulang tanpa instruksi per eksperimen.
Sasaran kinerja adalah **expectancy/keuntungan bersih yang konsisten setelah seluruh biaya, dengan
risiko terkendali dan bukti independen**; belum ada klaim strategi menguntungkan atau jaminan profit.

**Kemampuan yang dituju (gunakan otak serta modul yang sudah ada, jangan buat sistem paralel):**
1. **Riset informasi mandiri:** kumpulkan data pasar dan berita ekonomi (FOMC, NFP, bank sentral, geopolitik)
   melalui sumber yang sah, dengan sumber, waktu publikasi, relevansi instrumen, kesegaran dan verifikasi;
   informasi yang tidak valid tidak boleh dipakai sebagai fakta keputusan.
2. **Penalaran & riset strategi:** amati regime dan peluang BUY/SELL berbeda; daftarkan hipotesis
   liquidity sweep, pullback, Fibonacci, struktur pasar atau alternatif **sebelum** eksperimen;
   uji hanya pada data pengembangan yang diizinkan, dengan biaya, pembanding dan koreksi banyak percobaan.
3. **Memori ilmiah:** pakai `HypothesisRegistry` dan memori canonical yang sudah ada untuk menyimpan
   versi, dataset/hash, keputusan, bukti, kegagalan, dan alasan; jangan membuat memori kedua.
4. **Evaluasi diri:** audit kualitas waktu/data, kebocoran, overfitting, expectancy bersih, risiko,
   dan kemampuan reproduksi; hasil lemah atau belum lengkap harus dilabeli WAIT/BLOCKED/PENDING.
5. **Perbaikan diri terkendali:** boleh menghasilkan rekomendasi perubahan dan PR GitHub dengan tes,
   alasan, rollback, dan hasil audit. Tidak boleh mengubah strategi aktif, mempromosikan model,
   mengirim order, memakai modal, atau menaikkan kewenangan tanpa gerbang validasi dan persetujuan Owner.

**Siklus target:** OBSERVE → RESEARCH/REASON → REGISTER HYPOTHESIS → VALIDATE →
EVALUATE → REMEMBER → PROPOSE IMPROVEMENT → ulangi.
Kemandirian berlaku untuk **riset dan pengusulan**, bukan otorisasi finansial.
**Urutan realisasi:** selesaikan WP13 dan WP8c, lalu WP14; riset mandiri memanfaatkan alat yang ada
sesuai gerbang Tahap 1–5. Tidak membuat WP baru sebelum audit gap dan keputusan rapat lanjutan.
Tidak mengubah antrean aktif, LIVE OFF, Risk Governor, pemisahan holdout, atau gerbang promosi.

**Urutan:** WP13 → WP8c → WP14 → pembuktian Tahap 1 (WP10b, WP8b, holdout sekali) → agent riset
berkelanjutan (setelah Tahap 1 lulus) → DEMO terbatas (Tahap 0–3 lulus + Owner) → LIVE (gerbang terpisah + Owner).

**Ukuran keberhasilan** diterima dengan angka: laporan deterministik (hash sama pada input sama); 100% kesimpulan
punya sumber; tugas gagal tercatat dengan alasan dan dapat diulang tanpa duplikasi; tidak pernah ada promosi atau
kenaikan kewenangan otomatis; perbaikan strategi hanya diakui pada data evaluasi independen setelah biaya penuh.

## Lampiran A — Rencana kerja perbaikan (untuk pelaksana)

Disusun Claude 22 Okt 2026 dari pemeriksaan VPS dan repo, ditambah usulan "Multi-Pair Opportunity Hunter" dari
review PM (Yura); sejak 29 Okt dikelola ChatGPT sebagai manager, dieksekusi Claude atau ChatGPT sesuai R0. Rencana ini **tidak** mengubah tahap, kriteria kelulusan, atau aturan lain
di dokumen ini. Bila ada yang bertentangan, aturan di bagian lain roadmap dan `CLAUDE.md` yang berlaku.

### R0. Urutan pengerjaan dan alur kerja (baca ini dulu)

**Siklus satu paket (selalu sama):**

```
1. ChatGPT (manager) → pilih paket dan pelaksana (ChatGPT atau Claude); tulis/ubah spesifikasi di R4 bila perlu
2. Pelaksana → branch dari origin/main → tes dulu → kode → semua pengecekan R2.6 → PR
3. Reviewer (ChatGPT, atau Claude bila diminta) → review dengan R7 + R8 → perbaikan di branch PR
4. ChatGPT atau Claude → selaraskan dengan main → CI hijau → squash-merge → isi baris R5
5. (paket yang menyentuh runtime) Claude atau ChatGPT → terapkan ke VPS → catat di PROJECT_STATUS
```

**Urutan paket.** Paket bernomor dikerjakan berurutan; paket berlabel "paralel" boleh berjalan bersamaan karena
berkasnya berbeda. Paket berikutnya dimulai setelah prasyaratnya **di-merge** (bukan hanya dibuka).

Selesai (rincian di R5 dan riwayat Git): WP1, WP2, WP3, WP8a, WP9a, WP9b, WP11, WP12, WP10b, WP10a, WP8c (kode).

| Fase | Paket | Oleh | Prasyarat | Ukuran perkiraan | Status (rinci di R5) |
|---|---|---|---|---|---|
| 1 (prioritas) | WP13 — jam live NTP + tick bergerak, `--since` | Manager/Claude (bukan Jules) | — | 34 berkas | MERGE BLOCKED; pulihkan `76ce7e8` |
| 1 (paralel) | WP15 — rollover Tahap 0 ikut 17:00 New York | Jules, review Claude | — | ±3 berkas, ±200 baris | Siap |
| 2 | WP8d — CLI sampel bukti jam bar | Jules, review Claude | WP8c (selesai) | ±3 berkas, ±300 baris | Siap |
| 2 (paralel) | WP16 — OAuth gateway tanpa paparan profil | Jules, review Claude | — | ±2 berkas, ±60 baris | Siap |
| 3 | WP4 — jurnal kandidat + replay sinyal | Pelaksana | WP9b (selesai) | ±6 berkas, ±450 baris | Siap |
| 3b | WP14 — auditor data baca-saja | Pelaksana | WP13 + WP8c | ±4 berkas, ±350 baris | — |
| terus | WP6 — 5 → 7 simbol di VPS | Claude | WP13 + pemantauan 21:00–22:00 UTC | — | Berjalan (5 simbol) |
| terus | Laporan WP9a di VPS; usul `measured_inputs` ke Owner | Claude + Owner | ≥ 3 hari bursa `decision_shadow` | — | Mengumpulkan data |
| 4 | Isi kalender NFP, buktikan jam bar, ekspor dataset pengembangan (pasar tutup) | Claude | WP8c | — | — |
| 4 (paralel) | Jalankan profil spread di VPS | Claude | WP10a | — | — |
| 5 | WP8b — setup BUY/SELL, simulasi, perbandingan | Pelaksana | WP8c + dataset diekspor (sebaiknya setelah WP10b) | ±8 berkas, ±600 baris | — |
| 5b | WP9c — syarat bukti proporsional (berkas terkunci) | Pelaksana → Claude + Owner | WP9b + ≥ 3 hari bursa `decision_shadow` | ±3 berkas, ±250 baris | — |
| 6 | WP9d — detektor entry + counterfactual kelas C | Claude menulis paket | WP4 + WP8b | — | — |
| 7 | Daftarkan hipotesis nyata + laporan perbandingan setup | Claude, disetujui Owner | WP8b + dataset | — | — |
| 8 | WP5 — hipotesis perankingan antarpair | Pelaksana | WP4 + ≥ 5 hari bursa data kandidat | ±4 berkas, ±350 baris | — |
| kapan saja | WP7 — keputusan Owner | Owner | — | — | Menunggu |

**Aturan alur** (ditetapkan ChatGPT sebagai manager; isi awal dari praktik yang sudah berjalan):
- Satu paket = satu branch dari `origin/main` = satu PR; manifest dan peta modul dibuat ulang dengan alatnya.
- Bila beberapa PR menyentuh berkas yang sama, di-merge berurutan dan `main` digabungkan ke branch berikutnya.
- Perubahan VPS dicatat di PROJECT_STATUS; observer resmi tetap satu dan tetap berjalan selama perubahan.
- Bagian 1–7 dan gerbang promosi hanya diubah dengan persetujuan Owner. Kelulusan tahap tidak dipercepat.

### R1. Temuan yang mendasari (bukti 22 Okt, VPS `30d043c`, 600+ siklus; kolom Status diperbarui saat paket selesai)

| # | Temuan | Bukti / lokasi | Status |
|---|---|---|---|
| T1 | Observer hanya mengamati `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx`. Program holdout butuh 7 simbol; Tahap 4 mulai dari XAUUSD | `BrainObserver.run` memotong `resolve_broker_symbols(catalog).symbols[:max_symbols]`; urutan tetap `MAJORS, CROSSES, OPTIONAL_MARKETS` di `broker/broker_scan_universe.py`; `JPN225` tidak ada di universe | Sebagian: WP1 selesai; VPS 5 simbol; 7 simbol setelah WP13 (WP6) |
| T2 | Ketujuh simbol tersedia dan bisa ditrade: `XAUUSD.vx`, `NAS100.vx`, `US30.vx`, `JPN225.vx`, `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx` (`trade_mode=4`). Versi tanpa `.vx` ada tetapi `trade_mode=0` | Probe baca-saja: baca 4 timeframe + tick 90 dtk ≈ 0,2–1,4 dtk/simbol (±5 dtk untuk 7); RAM bebas ±885 MB dari 2 GB; spread XAUUSD 0,33, NAS100 3,4, US30 3,3, JPN225 9,5 | Dipakai sebagai dasar WP1/WP6 |
| T3 | Tick satu hari XAUUSD ≈ 355 ribu (3 dtk). `collect_tick_days` menampung seluruh hari dalam dict/list sebelum menulis (±100–150 MB) | `operations/observation_ledger.py::_fetch_day`, `_write_ticks`, `reconcile` | Selesai: WP2 (#190), streaming per jam |
| T4 | 100% keputusan WAIT (381 baris) dengan 7 pemblokir di setiap baris: `system_unhealthy`, `insufficient_verified_forward_experience`, `no_verified_relevant_news`, `high_impact_news_blackout`, `macro_event_risk_too_high`, `macro_policy_transmission_not_verified`, `no_confirmed_closed_candle_entry` | Tabel `contextual_decisions` (`blockers_json`) | Sebagian: WP9a, WP9b selesai; WP9c, WP9d menunggu prasyarat |
| T5 | Tanpa berita segar yang cocok, `MultiSourceNewsEngine.assess` mengembalikan `ready=False, blackout=True, risk=1.0`, walau kalender `calendar_verified_clear`. Artikel resmi tersimpan: 0; feed Fed/ECB/BoE terambil OK. `load_articles` melewati item yang lebih tua dari `FRESH_SECONDS` (6 jam) **tanpa mencatat diagnosis**, sehingga `full_article_checks` kosong | `news/news_intelligence.py` (cabang `if not matched`), `cognition/observer.py::load_articles`, `news/verified_policy_context.py` | Diagnosis: WP3 (#191, tabel `observer_news`); perbaikan: WP9b |
| T6 | Observer selalu mengirim `system_healthy=False` dan `resolved_experience=[]` (sengaja fail-closed); `technical_signal` tidak pernah BUY/SELL selama 10 jam di 3 pasangan | `cognition/observer.py` di sekitar `RiskSituation(...)`; logika di `cognition/contextual_decision_intelligence.py` (terkunci) | Terbuka → WP4 (replay sinyal), WP9b/9d |
| T7 | `engines/opportunity.py::MultiMarketOpportunityEngine` hanya dipakai tes; bobot skornya (0,65/0,35/0,55, penalti spread/korelasi/berita) belum divalidasi; membuang kandidat bila `news.ready` salah | `docs/maintenance/RUNTIME_MODULE_MAP.md` kategori B | Terbuka → WP5 (riset) |
| T8 | `KATARINA_ALL_MARKET_RESEARCH=1` merotasi simbol paling lama tak dikunjungi (`lab/continuous_research_lab.py::select_batch`) dan menyalakan `ResearchPool`, `NetworkDoctor`, koneksi broker tambahan. Tidak cocok untuk cakupan per siklus 7 simbol inti dan RAM 2 GB | `cognition/continuous_observation.py` | Ditangani WP1 (mode all-market ditolak bersama `--universe`) |
| T9 | VPS tertinggal dari `main`; tugas `Katarina-Readonly-Observer` hanya berjalan saat Administrator login (trigger logon) | Task Scheduler VPS | Sebagian: VPS = `main` 28 Okt; auto-start setelah restart VPS masih WP6 butir 4 |
| T10 | Mode 5 simbol, 22 Okt 21:00–22:02 UTC: 7 siklus `FAILED BROKER_CLOCK_NOT_VERIFIED`, 0 data untuk **semua** simbol ±62 menit. XAUUSD/NAS100 jeda harian ±21:00–22:00 UTC (DST AS); hanya 3/5 quote segar = 60% < ambang 70% dari **semua** simbol. Dengan 7 simbol: 3/7. Backoff ×2 sampai 16 menit memperpanjang lubang | `broker/broker_clock_alignment.py::infer_clock_shift` (`frac=count/considered`), `cognition/observer.py` (raise bila tidak `suitable_for_readonly_snapshot`), `cognition/continuous_observation.py` (backoff) | Selesai: WP11 (#201); VPS 5 simbol lagi sejak 23 Okt 00:16 UTC (WP6) |
| T11 | **Jam tick MT5 = jam server broker (+3 jam), bukan UTC.** Probe baca-saja 23 Okt 00:19 UTC: `symbol_info_tick.time` dan `time_msc` dari `copy_ticks_range` sama-sama ≈ UTC+3 jam; bar `copy_rates_*` juga jam server (sudah dikoreksi `bars_for`). `last_past_quote(now)` mencari tick di [now−90 dtk, now] dalam koordinat server, sehingga quote observer berumur **±3 jam**: EURUSD 1.12124 vs 1.12221 sekarang, USDJPY 156.719 vs 156.162. Quote, `quote_age_seconds`, rekonsiliasi dan arsip tick Tahap 0 sejak 22 Okt 04:24 UTC tergeser 3 jam secara konsisten, sehingga pemeriksaan yang ada tidak mendeteksinya. XAUUSD/NAS100 `FAILED` 00:00–01:00 UTC = jeda harian 3 jam sebelumnya | `broker/causal_broker_quotes.py` (`last_past_quote`, `due_window_quote`, docstring "UTC"), `cognition/observer.py`, `operations/observation_ledger.py::_download_day`, `research/context_export.py`, `broker/data_recovery.py`, `demo/demo_forward.py` | Selesai: WP12 (#204), diterapkan 28 Okt 16:57 UTC; quote = harga sekarang |
| T12 | Akhir pekan, quote basi dengan umur hampir kelipatan jam menghasilkan offset palsu yang "terverifikasi" (−4 pada 24 Okt 03:57 UTC, −7 pada 06:55 UTC; ≥ 3 simbol berhenti pada saat yang sama) | `broker/broker_clock_alignment.py::infer_clock_shift` (umur dihitung setelah pembulatan jam); ledger `observer_cycles` 24 Okt | Arsip tick: diabaikan sejak WP12 review (`NO_MARKET_DATA`); akar masalah → WP13 |
| T13 | Jam VPS sempat berjalan dari CMOS (selisih ±15 dtk); kini NTP `time.windows.com`. Poll semula 32.768 dtk (±9,1 jam) melebihi batas umur sync WP13 14.400 dtk | `w32tm /query /status /verbose`; laporan harian `host-time-daily.txt` | `MaxPollInterval` 15 → 13 (8.192 dtk) 31 Okt (D7-M13, backup + rollback di VPS). WP13 menuntut `State Machine: 2 (Sync)`; 31 Okt 01:25 WIB terbaca `1 (Hold)` setelah resync — pantau beberapa interval sebelum deploy |

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

Spesifikasi paket yang sudah selesai (WP1, WP2, WP3, WP11, WP12; WP8a langkah 1–2; WP9a; WP9b) dihapus dari
sini setelah merge; isinya ada di riwayat Git dan deskripsi PR-nya. Paket yang tersisa:

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

#### WP6 — Penerapan VPS bertahap (hanya Claude; berjalan)

1. `git fetch && git merge --ff-only origin/main` di `C:\Katarina\code`; manifest `MATCH`.
2. Hentikan observer dengan `continuous.stop`, ubah `run-observer.ps1` menambah `--universe C:\Katarina\code\config\observer_universe.json`.
3. Tahap A (berjalan): 5 simbol (`C:\Katarina\private\observer_universe.json`). Tahap B ke 7 simbol hanya setelah
   WP13 diterapkan dan satu malam 21:00–22:00 UTC terpantau: durasi siklus < 20 dtk, RAM bebas > 500 MB, tidak ada
   siklus gagal di luar jeda pasar, unduhan tick hari penuh tanpa error. Jika gagal, kembali ke 5 simbol.
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
   **Jam bar (wajib).** `time` bar dan `time_msc` tick MT5 sama-sama jam server (R1 T11), jadi mencocokkan keduanya
   tidak membuktikan UTC. Setiap batch wajib membawa bukti pergeseran dari sumber UTC **independen**
   (`clock_evidence`: `shift_hours`, `time_basis = INDEPENDENT_UTC`, `source_sha256`); tanpa itu ekspor ditolak
   `BROKER_BAR_CLOCK_NOT_VERIFIED`. Cara memperoleh bukti: WP8c. Cutoff diterapkan setelah konversi ke UTC.
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

#### WP8c — Bukti jam historis bar dari rilis resmi (Tahap 1; prasyarat ekspor WP8a)

**Masalah.** Bar MT5 berlabel jam server (+3 musim panas, +2 musim dingin; ledger VPS mencatat +3 → +2 pada
24–25 Okt, cocok dengan aturan DST Eropa). Pergeseran historis harus dibuktikan dari sumber UTC independen, bukan
ditebak dari pergeseran sekarang. Sumber yang dipakai: jam rilis resmi US Employment Situation (NFP, 08:30 New York),
yang menimbulkan lonjakan tick volume M5 di EURUSD, USDJPY dan XAUUSD.

1. Berkas `config/research/us_release_calendar.csv` (`release_date, release_utc, source_url`) diisi **Claude** dari
   jadwal resmi BLS untuk rentang data pengembangan; pelaksana tidak mengarang tanggal. Hash berkas dicatat.
2. Modul `src/katarina/research/bar_clock_evidence.py`, fungsi murni tanpa MT5:
   `release_shift(bars_m5_server, release_utc)` → shift bulat −12…14 bila bar M5 dengan tick volume tertinggi dalam
   ±4 jam dari `release_utc + shift` (untuk shift kandidat) tepat jatuh di menit rilis dan volumenya ≥ 3× median 24 bar
   di sekitarnya; selain itu `None`. Satu rilis sah bila ≥ 2 dari 3 simbol memberi shift yang sama.
3. `shift_timeline(samples)`: urutan rilis dengan shift sah → segmen. Perubahan shift di antara dua rilis harus tepat
   pada satu transisi aturan DST (Eropa atau AS, pakai `operations/data_health.py`); aturan yang konsisten dengan
   **semua** sampel dipilih; bila tidak ada atau keduanya cocok untuk suatu rentang, rentang itu tanpa bukti.
4. Adapter `verified_historical_bar_shift(symbol, timeframe, start, end)` untuk `export_dev_bars`: mengembalikan
   `{"verified": True, "shift_hours", "time_basis": "INDEPENDENT_UTC", "source_sha256"}` hanya bila seluruh batch ada
   di satu segmen terbukti; `source_sha256` = hash kalender + laporan bukti. CLI ekspor mendapat `--clock-evidence PATH`.
5. Tes sintetis: bar server +3/+2 dengan lonjakan di menit rilis → shift benar; lonjakan bergeser 5 menit atau terlalu
   kecil → `None`; satu simbol saja → tidak sah; perubahan shift di luar tanggal transisi → rentang tanpa bukti;
   batch melintasi batas segmen → ditolak; hasil deterministik.
6. Bukan bagian PR: Claude mengisi kalender, menjalankan pembuktian dan ekspor di VPS saat pasar tutup.

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

**WP9a (selesai, #196)** — `research/blocker_ladder.py`. **WP9b (selesai, #205)** — `cognition/decision_inputs.py`,
`config/decision_inputs.json` (`legacy_fail_closed` default), tabel `decision_shadow`. Mengaktifkan `measured_inputs`
di VPS hanya setelah Owner setuju.

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

#### WP13 — Jam live dari NTP host + tick bergerak; penilaian Tahap 0 sejak tanggal (Tahap 0; R1 T12–T13; D6/D7)

Pemilik: **manager/Claude** di PR #233 (bukan Jules, D7-M8/M12). Acuan desain: tree `76ce7e8f`.

1. `broker/host_clock_probe.py`: parser ketat `w32tm /query /status /verbose` (field wajib sekali; sumber dari allowlist;
   `Leap=0`, `State=2`, `Last Sync Error=0`; umur sync ≤ 14.400 dtk; `|offset|` ≤ 1 dtk; deteksi lompatan UTC vs
   monotonic). Probe yang gagal tidak pernah menghasilkan sync palsu.
2. `broker/live_clock_probe.py`: dua sampel `time_msc` (atau siklus sebelumnya pada server yang sama ≤ 300 dtk); ≥ 3
   simbol harus bergerak dan segar (−15…180 dtk terhadap offset jam bulat, mayoritas ≥ 70%); identitas server di-hash;
   server baru tidak mewarisi offset; lompatan offset dikarantina. Tiga tick = konfirmasi feed, bukan tiga sumber jam.
3. `cognition/observer.py` memakai jalur ini; alasan gagal (`NO_TRUSTED_HOST_CLOCK`, `STALE_QUOTES`, `FX_MARKET_CLOSED`,
   ...) masuk `RECOVERABLE_SENSOR`; siklus ditutup `FAILED` + alasan tanpa quote/snapshot; audit `live_feed_clock_audit_v1`.
4. `check_stage0_health.py --since ISO` / `data_health.assess(..., since=None)`: zona waktu wajib, tidak di masa depan,
   batas atas `now`, hari parsial dikecualikan; default perilaku lama.
5. Tes negatif wajib: NTP tidak sinkron/basi/sumber asing; tiga quote basi; 3 segar + 2 basi; akhir pekan; server
   berganti; lompatan offset; fixture sintetis hanya berlingkup tes. Tes WP11 tidak diubah.
6. Deploy hanya dengan izin terpisah setelah NTP VPS terbukti `Sync` beberapa interval (D7-M2/M13).

#### WP14 — Auditor data baca-saja (Tahap 0–1; disetujui Owner 29 Okt; setelah WP13 dan WP8c)

Tujuan: satu laporan yang menunjukkan data mana yang layak menjadi bukti dan mana yang tidak, dengan alasan dan
sumber. Memperluas `operations/data_health.py` dan `scripts/ai/check_stage0_health.py`; **bukan** alat paralel.

1. `check_stage0_health.py --audit --since ISO [--dataset DIR] --output build/research/data_audit.json`. Membaca
   `context.sqlite3` dengan `mode=ro` + `PRAGMA query_only`, dan (opsional) manifest dataset pengembangan WP8a.
2. Pemeriksaan: siklus (status, alasan, celah antar siklus), quote (kosong, umur, spread negatif), offset jam (lebih
   dari satu nilai per hari di luar `NO_MARKET_DATA`), hari tick (status, `server_shift_hours`, sha256 berkas cocok),
   celah `data_gaps`, rekonsiliasi (`snapshots_matched/snapshots_checked`), `decision_shadow` (baris per siklus ×
   simbol), dataset (hash manifest, `clock_evidence` lengkap per batch).
3. Setiap temuan: `{"check", "status": PASS|BLOCKED|NO_DATA, "reason", "source": {"table"|"file", "key"|"sha256"}}`.
   Ringkasan per simbol × hari: layak / terbatas / karantina. Laporan memuat `report_sha256`.
4. Kriteria terima: input sama → laporan byte-identik; 100% temuan punya `source`; tidak ada penulisan ke state
   observer (tes membandingkan hash database sebelum/sesudah); tes sintetis per jenis masalah (quote hilang, offset
   campuran, hash berkas salah, `clock_evidence` hilang, baris shadow kurang); tidak memakai MT5/jaringan.
5. Menjalankan di VPS bukan bagian PR (Claude, pada salinan data).

#### WP15 — Rollover Tahap 0 mengikuti 17:00 New York (Tahap 0; Owner D7-M15)

Masalah: `fx_session_open` mengecualikan rollover tetap 20:45–21:15 UTC. Data VPS 28–30 Okt: 23 siklus dengan < 3 simbol
bergerak, 16 di 21:00–21:29 UTC. Setelah DST AS berakhir (1 Nov 2026) rollover = 22:00 UTC, seluruhnya di dalam sesi.

1. `operations/observation_ledger.py`: fungsi baru `stage0_session_open(moment)`. Untuk `moment ≥ ROLLOVER_RULE_EFFECTIVE_UTC`:
   Senin 00:00 – Jumat 20:00 UTC, kecuali jendela rollover `[17:00 NY − ROLLOVER_BEFORE_MINUTES, 17:00 NY +
   ROLLOVER_AFTER_MINUTES)` (konstanta 15 dan 30). 17:00 NY = 21:00 UTC selama DST AS, 22:00 UTC di luar itu, dihitung
   dengan aturan DST AS yang sudah ada (minggu ke-2 Maret 07:00 UTC – minggu ke-1 November 06:00 UTC), tanpa
   `zoneinfo`/tzdata dan tanpa impor melingkar (pindahkan helper `_nth_sunday` ke `observation_ledger.py`;
   `data_health` tetap mengekspor nama lama). Sebelum tanggal berlaku: hasil identik dengan `fx_session_open`.
2. `fx_session_open` **tidak berubah** (dipakai klasifikasi celah arsip tick). `data_health.assess` memakai
   `stage0_session_open` dan menulis `session_rule` yang menyebut kedua segmen + `rollover_rule_effective_utc`.
3. `ROLLOVER_RULE_EFFECTIVE_UTC` tidak boleh lebih awal dari waktu merge; nilai di PR adalah usulan, manager
   menetapkannya sebelum merge. Tidak ada perubahan ledger, failure lama, atau data historis.
4. Tes: sebelum/sesudah 1 Nov 2026 dan 8 Mar 2026; Senin–Kamis tepi jendela (menit −16/−15/+29/+30); Jumat ≥ 20:00 dan
   akhir pekan; batas tanggal berlaku; ledger sintetis dengan kegagalan `STALE_QUOTES` 22:05 UTC setelah DST
   (aturan lama menghitung, aturan baru mengecualikan) dan laporan denominator; tes `fx_session_open`, WP11, WP13 lama
   tetap lulus tanpa diubah.

#### WP8d — CLI sampel bukti jam bar dari rilis resmi (Tahap 1; prasyarat ekspor WP8a; setelah WP8c)

1. `research/bar_clock_evidence.py`: fungsi murni `collect_release_samples(broker, calendar_rows, *, symbols=CORE_SYMBOLS,
   timeframe)` yang, per rilis, mengambil bar M5 jendela cukup lebar untuk shift −12…+14 jam ± 4 jam (+ 12 bar konteks)
   lewat `copy_rates_range`, menjalankan `release_shift`, dan hanya menambah sampel bila hasilnya bilangan bulat.
   `bars_sha256` = SHA-256 JSON kanonik bar mentah yang dipakai (semua simbol, urut). Rilis tanpa konsensus dicatat di
   `rejected` dengan alasan, tidak diisi tebakan.
2. CLI `scripts/research/build_bar_clock_evidence.py --calendar config/research/us_release_calendar.csv --out FILE`
   (CLI tipis; MT5 hanya diimpor di `main()`; baca-saja; batas rilis per jalan `--max-releases`, default kecil). Keluaran
   = `build_evidence_report` + daftar `rejected`; `--out` wajib di luar repo (tolak path di dalam repo).
3. Tes dengan broker palsu: +2/+3 di sekitar DST, konsensus kurang → ditolak, `bars_sha256` deterministik, laporan lolos
   `load_evidence_report`, path keluaran di dalam repo ditolak. Tanpa jaringan/MT5.
4. Mengisi kalender BLS dan menjalankan CLI di VPS bukan bagian PR (Claude, pasar tutup).

#### WP16 — OAuth gateway tanpa paparan profil (keamanan; manager D7-M4)

1. `oauth_gateway/server.js`: `lastAuth` tidak menyimpan profil (`{ok, at, error}`); `/oauth/status` hanya
   `ok`, `at`, `error`; `server.listen(PORT, HOST)` dengan `HOST = process.env.HOST || '127.0.0.1'`.
2. Tes statis `tests/static/test_oauth_gateway_guard.py` (baca teks `server.js`): tidak ada `profile` di respons status,
   default host loopback, token tidak pernah dikirim di respons.
3. Tidak mengubah alur OAuth lain; tanpa dependensi npm; audit lokasi deploy lain dilakukan manager.

#### WP7 — Keputusan Owner (bukan kode)

- Profil DEMO final Tahap 3 (usulan 0,5%/trade, 3%/hari sebagai lapisan pengetat di atas batas utama 35%).
- Aturan berita: apakah "tidak ada rilis resmi" boleh dibedakan dari blackout. Menyentuh logika keputusan; hanya
  lewat hipotesis + validasi + catatan promosi setelah data WP3/WP4 tersedia.
- Repo private atau tidak; status issue lama #21, #24, #29, #31.

### R5. Status paket

**Cara mengambil paket** (untuk pelaksana yang diminta "baca roadmap dan kerjakan"):
1. Pilih baris teratas tabel "Antrean kerja" (awal dokumen) yang berstatus Siap; urutannya sama dengan tabel di bawah.
2. Pastikan belum diambil: tidak ada PR terbuka atau branch `*/wpN-*` untuk paket itu
   (`git ls-remote --heads origin "*wpN*"` dan daftar PR terbuka). Jika sudah ada, pilih paket lain.
3. Langsung buka PR draft dengan bagian "Pemahaman" (R6.0 A3) dan ubah baris paket itu menjadi
   **Sedang dikerjakan — <agen>, PR #N**. Status lain diubah ChatGPT (manager), Claude saat merge, atau Owner.

Status yang dipakai: Siap dikerjakan · Sedang dikerjakan · Dalam review · Selesai (merge) · Menunggu prasyarat ·
Menunggu Owner · Dikerjakan Claude.

| Paket | Status | PR | Catatan review Claude |
|---|---|---|---|
| WP13 | **MERGE BLOCKED P0** — HEAD `3532399` (bot Jules) mengembalikan voting quote-only; review Claude hanya untuk `76ce7e8` | **PR #233** | Pulihkan tree `76ce7e8` dengan commit baru (tanpa force-push), pertahankan D7, CI 3 job + review baru pada SHA final (D7-M7–M9). Deploy setelah NTP VPS `Sync` terbukti |
| WP8c | **CODE DONE (merge)** — 30 Okt 2026, review Claude | #230 | 24 bar sekitar wajib; segmen VERIFIED hanya dengan sampel di dalamnya (tanpa ±200 hari); sampel wajib di kalender + `bars_sha256`; adapter menghitung ulang timeline/hash. Sisa: isi `us_release_calendar.csv` dari sumber resmi BLS dan buat laporan sampel dari bar nyata (belum ada alat CLI) |
| WP10b | **Selesai (merge)** — 30 Okt 2026 | #225 | Squash `8cc3d677`; Body/Linux/Windows PASS; hanya alat riset, tidak mengesahkan hasil strategi/VPS |
| WP10a | **Selesai (merge)** — 30 Okt 2026, review Claude | #231 | Perbaikan review: parser ketat 4 kolom (baris rusak → `TICK_FILE_MALFORMED`, tidak dilewati), hari tanpa `server_shift_hours` (sebelum WP12) dikecualikan dan dilaporkan, quote terakhir per menit menurut timestamp, SQLite URI aman + `query_only`. Uji 2 juta tick < 50 MB lulus. Belum dijalankan di VPS |
| WP4 | Menunggu WP13 merge (sama-sama mengubah `observer.py`) — Jules | Issue #229 | Jangan aktifkan sebelum prioritas P0 |
| WP14 | Menunggu prasyarat (WP13, WP8c) | – | – |
| WP15 | Siap dikerjakan — Jules | – | Owner D7-M15; jangan ubah `fx_session_open` atau data lama |
| WP8d | Siap dikerjakan — Jules | – | Hasil dijalankan Claude di VPS; laporan bukti di luar repo |
| WP16 | Sedang dikerjakan — Jules | – | Minimalisasi paparan status, bind loopback 127.0.0.1, tes statis guard |
| WP6 | Berjalan 5 simbol; **startup pasca-reboot belum terbukti** | – | 7 simbol setelah WP13 dan pemantauan 21:00–22:00 UTC. Jalan mundur: ganti nama `C:\Katarina\private\observer_universe.json` |
| WP8b | Menunggu prasyarat (WP8c + dataset diekspor) | – | – |
| WP9c | Menunggu prasyarat (≥ 3 hari bursa `decision_shadow`) + persetujuan Owner | – | – |
| WP9d | Menunggu prasyarat (WP4, WP8b) | – | – |
| WP5 | Menunggu prasyarat (WP4 + ≥ 5 hari bursa data kandidat) | – | – |
| WP7 | Menunggu Owner | – | – |
| Selesai | WP1 #184 · WP2 #190 · WP3 #191 · WP8a #195 · WP9a #196 · WP9b #205 · WP11 #201 · WP12 #204 · WP10b #225 · WP10a #231 · WP8c #230 (kode) | – | Catatan review ada di deskripsi/komentar PR masing-masing |

### R6. Perintah siap pakai untuk pelaksana

Salin **dua blok** ke pelaksana: blok **R6.0 Aturan umum** (selalu) lalu blok perintah paket yang dikerjakan.
Untuk **Google Jules** salin **tiga blok**: R6.J (perintah induk, anti-regresi), R6.0, lalu blok paket.
Perintah paket yang sudah selesai (WP8c, WP10a, WP10b) dihapus; teksnya ada di riwayat Git.
Pelaksana yang hanya diminta "baca roadmap" tetap terikat R6.0 dan memakai blok paket sebagai instruksinya.
Keduanya berdiri sendiri; pelaksana tidak perlu konteks percakapan lain.

**R6.J Perintah induk Google Jules (salin utuh ke task Jules; satu task = satu paket)**
```text
Kamu Google Jules, pelaksana coding untuk repo GitHub alfaauliau-katarinaAI/Katarina-AI (riset trading MT5,
Python 3.12, dokumen bahasa Indonesia). Manager = ChatGPT/Yura, reviewer = Claude, keputusan akhir = Owner.
Kamu hanya menulis kode di GitHub: tanpa akses VPS, MT5, data broker, merge, atau kewenangan promosi. LIVE OFF.

1. PILIH PAKET
   - Ambil paket teratas berstatus "Siap — Jules" di tabel "Antrean kerja" docs/ROADMAP.md, urutan saat ini:
     WP15 -> WP8d -> WP16, lalu WP4 dan WP14 setelah WP13 merge (keduanya menyentuh berkas WP13).
     Jangan mengambil WP13 (PR #233), WP9c, WP9d, WP6.
   - Cek belum diambil: tidak ada PR terbuka atau branch untuk paket itu. Satu task Jules = satu paket = satu PR.
   - Setelah PR dibuka, BERHENTI dan tunggu review. Paket berikutnya hanya setelah PR sebelumnya merged
     (atau manager menyuruh lanjut).

2. MULAI BERSIH (anti-regresi; wajib, pelajaran PR #233)
   - Setiap task mulai dari `git fetch origin && git checkout -B jules/wpN-<ringkas>-YYYYMMDD origin/main`.
     Jangan memakai ulang sandbox, branch, atau patch lama dari task lain.
   - Jangan pernah push ke PR yang dibuat/diubah orang lain. Bila remote branch PR-mu punya commit yang tidak ada di
     riwayat lokalmu: BERHENTI, jangan push, tulis komentar di PR.
   - Sebelum SETIAP push: `git fetch origin`, lalu `git diff --name-status origin/main...HEAD`. Daftar itu hanya
     boleh berisi berkas yang kamu umumkan di bagian "Pemahaman". Berkas berstatus D (dihapus) atau berkas yang
     tidak kamu rencanakan = kesalahan; perbaiki sebelum push. Tanpa force-push; bila main bergerak, merge commit.
   - Jangan menyentuh docs/ROADMAP_DISCUSSION.md, docs/REPAIR_HISTORY.md, docs/PROJECT_STATUS.md, berkas laporan di
     docs/maintenance/, atau berkas paket lain. Di roadmap hanya baris paketmu di tabel R5.

3. PAHAMI SEBELUM MENULIS (cara kerja Claude, R2 + R8)
   - Baca CLAUDE.md, docs/ROADMAP.md "Mulai di sini", bagian 1-7, Lampiran A R0-R2, sub-bagian paketmu di R4, R5,
     R6.0, R7, R8, R9, R10, lalu blok "Perintah WPn" paketmu di R6.
   - Baca utuh setiap berkas yang disebut paket, lalu pemanggil dan yang dipanggilnya (grep -rn).
   - Buka PR draft lebih dulu dengan bagian "Pemahaman" (R6.0 A3): tujuan dengan kata-katamu, berkas yang akan
     diubah, berkas terkunci dari `python scripts/governance/promotion_gate.py --hashes`, tes yang akan ditambah,
     risiko. Bila ambigu atau bertentangan dengan roadmap: tulis pertanyaan di PR dan BERHENTI.

4. CARA MENULIS KODE (sama dengan Claude)
   - Perubahan terkecil yang benar. Parameter baru opsional dengan default perilaku lama. Tanpa refactor, rename,
     format ulang, atau abstraksi spekulatif di luar paket. Ikuti gaya berkas yang diubah.
   - Tes dulu: tulis tes yang GAGAL, baru kode sampai lulus. Satu tes = satu perilaku; uji jalur gagal dan batas.
     Tes deterministik: waktu disuntikkan, tanpa jaringan/MT5/sleep, koneksi SQLite ditutup (contextlib.closing).
   - Fail-closed dengan kode alasan HURUF_BESAR stabil; tangkap exception spesifik; tanpa except kosong, print debug,
     kode mati, TODO tanpa nomor paket. Waktu = datetime ber-zona UTC; tolak waktu naif.
   - SQLite: parameter ?, tulis dalam `with db:`, pembaca mode=ro. JSON kanonik sort_keys=True; gzip mtime=0.
   - Linux + Windows: pathlib, encoding="utf-8", tanpa perintah shell khusus OS. Tanpa dependensi baru, tanpa
     thread/worker/observer baru, tanpa jalur order. Angka keputusan = konstanta bernama atau dari spec/config.
   - Berkas di config/promotion_lock.json tidak boleh diubah. Risk Governor dan batas 35% tidak dilemahkan.
     Holdout (>= 13 Okt 2026 00:00 UTC) tidak dipakai. Jangan melonggarkan pemeriksaan agar tes/CI hijau:
     cari akar masalah (R8 butir 5).

5. PENGECEKAN (standar Claude; semua harus lulus sebelum PR ditandai siap)
   a. R2 langkah 6 lengkap: unit, static, integration, audit_repo_hygiene, audit_dependency_links,
      promotion_gate --check, `git add -A` lalu release_manifest --generate, verifikasi manifest = MATCH,
      runtime_import_map. Kegagalan lingkungan diperbaiki di lingkungan; jangan lapor "lulus sebagian".
   b. Bukti tes bermakna: kembalikan sementara perubahan kode (bukan tes) dan tunjukkan tes baru GAGAL; pulihkan
      kode dan tunjukkan LULUS. Tulis nama tes dan hasil dua kondisi itu di PR.
   c. Tes lama tidak diubah kecuali paket memintanya (sebutkan alasannya).
   d. Diff sendiri (`git diff origin/main...HEAD`): tidak ada baris yang tidak dibutuhkan paket; tidak ada berkas
      terhapus; perilaku tanpa opsi baru identik.
   e. CI GitHub Body, Portable Ubuntu, Portable Windows hijau pada SHA terakhir. Bila merah: perbaiki akar masalah
      di branch yang sama (commit baru); maksimal dua percobaan, setelah itu tulis analisis di PR dan berhenti.
   f. Daftar periksa R7 butir 1-11 disalin ke PR dengan [x] hanya untuk yang benar-benar diverifikasi.

6. DOKUMEN DAN PR
   - CHANGELOG.md satu entri baru (<= 10 baris). CLAUDE.md hanya bila ada CLI/modul baru. Roadmap hanya baris R5.
   - Deskripsi PR = templat R6.0 E (Pemahaman, Perubahan, Keamanan, Pengujian dengan angka persis, Daftar periksa R7,
     Belum yakin). Judul "WPn: ..." bahasa Indonesia; commit kalimat perintah <= 72 karakter.
   - Setelah review: perbaiki setiap poin di branch yang sama (commit baru), balas tiap komentar, jalankan ulang
     langkah 5, perbarui bagian Pengujian. Jangan memperluas cakupan PR.
```

**R6.0 Aturan umum pelaksana (ChatGPT boleh mengubahnya sebagai manager)**
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

C. ATURAN TETAP OWNER: berkas di config/promotion_lock.json hanya dengan catatan promosi yang disetujui Owner;
   Risk Governor dan batas 35% tidak dilemahkan; DEMO/LIVE tidak diaktifkan tanpa persetujuan Owner; holdout tidak
   dipakai menyetel. Selebihnya mengikuti arahan ChatGPT sebagai manager.

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

F. Setelah PR dibuka: lanjutkan sesuai arahan ChatGPT (manager).
```

**Perintah WP4**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
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

**Perintah WP13 (hanya manager/Claude; Jules tidak mengerjakan)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI, PR #233 yang sama (jangan buat PR baru). Tree acuan = 76ce7e8f.
1. Pulihkan tree 76ce7e8f di atas HEAD PR dengan commit baru (tanpa force-push), lalu merge origin/main
   (pertahankan docs/ROADMAP_DISCUSSION.md D7 dan dokumen kanonis milik main).
2. Ikuti R4 WP13 butir 1–6; jalankan R2 langkah 6; manifest MATCH; promotion gate PASS.
3. Tunggu CI Body/Ubuntu/Windows pada SHA final, minta review independen baru. Merge ≠ deploy ≠ Tahap 0 PASS.
```

**Perintah WP14 (auditor data baca-saja)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP13 dan WP8c sudah di-merge).
1. Baca R6.0, "Mulai di sini", CLAUDE.md, bagian 5 "Pemisahan data", Lampiran A: R1 (T10–T13), R2, R8, R9, R10 dan
   "WP14". Baca seluruh src/katarina/intelligence/operations/data_health.py, observation_ledger.py (skema tabel),
   scripts/ai/check_stage0_health.py, src/katarina/research/dev_dataset.py dan tes-tesnya.
2. Kerjakan HANYA WP14, satu PR "WP14: auditor data baca-saja".
3. Wajib: memperluas data_health/check_stage0_health (bukan modul paralel); SQLite mode=ro + query_only; laporan
   deterministik dengan report_sha256; setiap temuan punya source; tes hash database sebelum/sesudah; tanpa MT5/jaringan;
   verdict kriteria Tahap 0 yang ada tidak berubah tanpa --audit.
4. Ikuti seluruh R6.0 Aturan umum (A–F); isi HANYA baris WP14 di tabel R5.
```

**Perintah WP15 (rollover Tahap 0 ikut 17:00 New York)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
1. Baca R6.J, R6.0, CLAUDE.md, bagian "Tahap 0", Lampiran A: R1 (T10, T13), R2, R8, R9, R10 dan "WP15". Baca seluruh
   src/katarina/intelligence/operations/observation_ledger.py, operations/data_health.py, scripts/ai/check_stage0_health.py,
   tests/unit/intelligence/test_observation_ledger.py dan semua tes yang memanggil fx_session_open (grep).
2. Kerjakan HANYA WP15, satu PR "WP15: rollover Tahap 0 mengikuti 17:00 New York".
3. Wajib: fx_session_open tidak berubah; aturan baru hanya untuk moment >= ROLLOVER_RULE_EFFECTIVE_UTC; DST tanpa
   zoneinfo/tzdata; tanpa impor melingkar; tes lama tidak diubah; laporan menyebut kedua segmen aturan.
4. Ikuti seluruh R6.J dan R6.0 (A–F); isi HANYA baris WP15 di tabel R5.
```

**Perintah WP8d (CLI sampel bukti jam bar)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
1. Baca R6.J, R6.0, CLAUDE.md, bagian 5 "Pemisahan data", Lampiran A: R1 (T11), R2, R8, R9, R10, "WP8", "WP8c" dan
   "WP8d". Baca seluruh src/katarina/research/bar_clock_evidence.py, research/dev_dataset.py,
   scripts/research/export_dev_bars.py dan tes-tesnya.
2. Kerjakan HANYA WP8d, satu PR "WP8d: CLI sampel bukti jam bar dari rilis resmi".
3. Wajib: fungsi murni teruji dengan broker palsu; MT5 hanya diimpor di main(); tidak mengarang tanggal rilis dan
   tidak mengisi config/research/us_release_calendar.csv; laporan ditulis di luar repo; release_shift tidak dilonggarkan.
4. Ikuti seluruh R6.J dan R6.0 (A–F); isi HANYA baris WP8d di tabel R5.
```

**Perintah WP16 (OAuth gateway tanpa paparan profil)**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
1. Baca R6.J, R6.0, CLAUDE.md, Lampiran A: R2, R8, R9, R10 dan "WP16". Baca seluruh oauth_gateway/server.js dan
   oauth_gateway/package.json.
2. Kerjakan HANYA WP16, satu PR "WP16: OAuth gateway tanpa paparan profil".
3. Wajib: status tanpa profil, bind default 127.0.0.1, tes statis Python; tanpa dependensi npm; alur OAuth lain tetap.
4. Ikuti seluruh R6.J dan R6.0 (A–F); isi HANYA baris WP16 di tabel R5.
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
10. Anti-regresi: `git diff --name-status origin/main...HEAD` hanya berisi berkas yang diumumkan di "Pemahaman";
    tidak ada berkas terhapus atau dokumen milik orang lain (rapat, REPAIR_HISTORY, PROJECT_STATUS) yang berubah.
11. Riwayat PR tidak menimpa commit orang lain (bandingkan dengan HEAD review sebelumnya); review hanya berlaku
    untuk SHA yang ditinjau, dan HEAD baru selalu ditinjau ulang.

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
| `ROADMAP.md` | Tahapan perjalanan, kriteria lulus, prioritas, dependensi; status paket di R5 | Tanpa notula atau daftar commit; tidak mengulang detail perbaikan |
| `ROADMAP_DISCUSSION.md` (**MEETING**) | Pertanyaan, usulan, tanggapan dan keputusan yang masih menunggu; ringkasan keputusan terakhir | Bukan aturan atau antrean kedua; topik selesai ditutup |
| `REPAIR_HISTORY.md` | Satu entri per perbaikan terverifikasi: sebelum, akar masalah, perubahan berkas, PR/commit, tes, deployment, risiko tersisa | Tidak mencatat ide, progres pengerjaan harian, atau klaim stabil tanpa bukti |
| `PROJECT_STATUS.md` | Kondisi operasional terkini, blocker dan bukti terakhir | Snapshot; bukan arsip kronologis |
| `CHANGELOG.md` | Ringkasan teknis apa berubah dan mengapa, satu entri per PR | ≤ 10 baris; untuk detail hasil perbaikan cukup tautkan `REPAIR_HISTORY.md` |
| `CLAUDE.md` | Peta baca dan panduan kode | ≤ 2 baris per perubahan kecil, tidak menggandakan isi dokumen |
| Deskripsi PR | Templat R6.0 E dan bukti diff/CI/review | ±40–80 baris; tabel lebih baik daripada paragraf |
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
