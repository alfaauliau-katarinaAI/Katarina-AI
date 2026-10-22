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

Disusun Claude dari pemeriksaan VPS dan repo 22 Okt malam, ditambah usulan "Multi-Pair Opportunity Hunter" dari
review PM (Yura). Pelaksana (ChatGPT/Codex/AI lain) mengerjakan paket di bawah **berurutan** sesuai R0, memakai perintah siap pakai di R6; Claude meninjau dan
menyempurnakan setiap PR sebelum merge. Rencana ini **tidak** mengubah tahap, kriteria kelulusan, atau aturan lain
di dokumen ini. Bila ada yang bertentangan, aturan di bagian lain roadmap dan `CLAUDE.md` yang berlaku.

### R0. Urutan pengerjaan (baca ini dulu)

Owner cukup mengirim perintah siap pakai di **R6** ke pelaksana, satu paket per kali, sesuai urutan berikut.
Paket berikutnya baru dimulai setelah PR paket sebelumnya **di-merge** (bukan hanya dibuka), kecuali disebut paralel.

| Urutan | Paket | Dikerjakan oleh | Syarat mulai | Perkiraan ukuran PR | Hasil yang diserahkan |
|---|---|---|---|---|---|
| 1 | WP1 — daftar simbol eksplisit | Pelaksana | — | ±6 berkas, ±300 baris | PR `WP1: ...` hijau |
| 2 | Review WP1 | Claude | PR WP1 dibuka | — | Perbaikan/komentar, lalu merge |
| 3 | WP2 — tick streaming | Pelaksana | WP1 di-merge | ±2 berkas, ±250 baris | PR `WP2: ...` hijau |
| 4 | WP3 — diagnosis berita | Pelaksana | boleh paralel dengan WP2 (berkas berbeda) | ±4 berkas, ±200 baris | PR `WP3: ...` hijau |
| 5 | Review WP2 dan WP3 | Claude | PR dibuka | — | Merge |
| 6 | WP6 — terapkan ke VPS bertahap | Claude | WP1–WP3 di-merge | — | Laporan 5→7 simbol, catatan roadmap |
| 7 | WP4 — jurnal kandidat riset + replay sinyal | Pelaksana | WP6 tahap A berjalan | ±6 berkas, ±450 baris | PR `WP4: ...` hijau |
| 8 | Review WP4 lalu terapkan ke VPS | Claude | PR WP4 dibuka | — | Merge + restart observer |
| 9 | WP5 — hipotesis perankingan antarpair | Pelaksana | WP4 di-merge dan ≥ 5 hari bursa data kandidat | ±4 berkas, ±350 baris | PR `WP5: ...` hijau |
| 10 | Review WP5 | Claude | PR WP5 dibuka | — | Merge; hasil riset dilaporkan ke Owner |
| — | WP7 — keputusan Owner | Owner | kapan saja | — | Keputusan tertulis di roadmap |

Aturan alur: bila review Claude meminta perubahan, Owner meneruskan komentar review ke pelaksana dengan perintah
"Perbaiki PR #N sesuai komentar review, ikuti R2" lalu Claude meninjau ulang. Bila pelaksana menemukan bahwa paket
memerlukan berkas terkunci, ia berhenti dan menuliskannya di PR; Owner meneruskan ke Claude.

### R1. Temuan yang mendasari (bukti 22 Okt, VPS `30d043c`, 600+ siklus)

| # | Temuan | Bukti / lokasi |
|---|---|---|
| T1 | Observer hanya mengamati `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx`. Program holdout butuh 7 simbol; Tahap 4 mulai dari XAUUSD | `BrainObserver.run` memotong `resolve_broker_symbols(catalog).symbols[:max_symbols]`; urutan tetap `MAJORS, CROSSES, OPTIONAL_MARKETS` di `broker/broker_scan_universe.py`; `JPN225` tidak ada di universe |
| T2 | Ketujuh simbol tersedia dan bisa ditrade: `XAUUSD.vx`, `NAS100.vx`, `US30.vx`, `JPN225.vx`, `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx` (`trade_mode=4`). Versi tanpa `.vx` ada tetapi `trade_mode=0` | Probe baca-saja: baca 4 timeframe + tick 90 dtk ≈ 0,2–1,4 dtk/simbol (±5 dtk untuk 7); RAM bebas ±885 MB dari 2 GB; spread XAUUSD 0,33, NAS100 3,4, US30 3,3, JPN225 9,5 |
| T3 | Tick satu hari XAUUSD ≈ 355 ribu (3 dtk). `collect_tick_days` menampung seluruh hari dalam dict/list sebelum menulis (±100–150 MB) | `operations/observation_ledger.py::_fetch_day`, `_write_ticks`, `reconcile` |
| T4 | 100% keputusan WAIT (381 baris) dengan 7 pemblokir di setiap baris: `system_unhealthy`, `insufficient_verified_forward_experience`, `no_verified_relevant_news`, `high_impact_news_blackout`, `macro_event_risk_too_high`, `macro_policy_transmission_not_verified`, `no_confirmed_closed_candle_entry` | Tabel `contextual_decisions` (`blockers_json`) |
| T5 | Tanpa berita segar yang cocok, `MultiSourceNewsEngine.assess` mengembalikan `ready=False, blackout=True, risk=1.0`, walau kalender `calendar_verified_clear`. Artikel resmi tersimpan: 0; feed Fed/ECB/BoE terambil OK. `load_articles` melewati item yang lebih tua dari `FRESH_SECONDS` (6 jam) **tanpa mencatat diagnosis**, sehingga `full_article_checks` kosong | `news/news_intelligence.py` (cabang `if not matched`), `cognition/observer.py::load_articles`, `news/verified_policy_context.py` |
| T6 | Observer selalu mengirim `system_healthy=False` dan `resolved_experience=[]` (sengaja fail-closed); `technical_signal` tidak pernah BUY/SELL selama 10 jam di 3 pasangan | `cognition/observer.py` di sekitar `RiskSituation(...)`; logika di `cognition/contextual_decision_intelligence.py` (terkunci) |
| T7 | `engines/opportunity.py::MultiMarketOpportunityEngine` hanya dipakai tes; bobot skornya (0,65/0,35/0,55, penalti spread/korelasi/berita) belum divalidasi; membuang kandidat bila `news.ready` salah | `docs/maintenance/RUNTIME_MODULE_MAP.md` kategori B |
| T8 | `KATARINA_ALL_MARKET_RESEARCH=1` merotasi simbol paling lama tak dikunjungi (`lab/continuous_research_lab.py::select_batch`) dan menyalakan `ResearchPool`, `NetworkDoctor`, koneksi broker tambahan. Tidak cocok untuk cakupan per siklus 7 simbol inti dan RAM 2 GB | `cognition/continuous_observation.py` |
| T9 | VPS tertinggal dari `main`; tugas `Katarina-Readonly-Observer` hanya berjalan saat Administrator login (trigger logon) | Task Scheduler VPS |

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
7. **Dokumen**: entri baru di atas `CHANGELOG.md` (tanggal, judul, apa dan kenapa, "tidak ada berkas terkunci
   diubah; LIVE tetap OFF"); perbarui `CLAUDE.md` bila ada CLI/modul baru atau angka tes/peta modul berubah;
   isi baris paket di tabel R5.
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

#### WP7 — Keputusan Owner (bukan kode)

- Profil DEMO final Tahap 3 (usulan 0,5%/trade, 3%/hari sebagai lapisan pengetat di atas batas utama 35%).
- Aturan berita: apakah "tidak ada rilis resmi" boleh dibedakan dari blackout. Menyentuh logika keputusan; hanya
  lewat hipotesis + validasi + catatan promosi setelah data WP3/WP4 tersedia.
- Repo private atau tidak; status issue lama #21, #24, #29, #31.

### R5. Status paket

| Paket | Status | PR | Catatan review Claude |
|---|---|---|---|
| WP1 | PR dibuka (menunggu review) | [#184](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/184) | Menunggu review Claude, belum merge/deploy |
| WP2 | Belum dimulai | – | – |
| WP3 | Belum dimulai | – | – |
| WP4 | Belum dimulai | – | – |
| WP5 | Belum dimulai | – | – |
| WP6 | Menunggu WP1–WP3 | – | – |
| WP7 | Menunggu Owner | – | – |


### R5A. Log pekerjaan pelaksana untuk diperiksa Owner — 23 Oktober 2026 WIB

**Jenis catatan:** audit pekerjaan nyata dari GitHub dan uji pada checkout VPS **terpisah**, bukan klaim kelulusan
tahap. Waktu commit GitHub memakai UTC 22 Oktober 2026 (23 Oktober dini hari WIB).
Catatan ini ditulis **pada branch PR #184**, sehingga baru akan muncul pada `main` setelah PR direview
dan digabung sesuai R0/R2. Rujukan lengkap: [PR #184](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/184),
[daftar commit PR #184](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/184/commits),
[CI WP1 terakhir](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/39824790896).
**Tidak ada approval Owner atau review Claude yang diasumsikan.**

#### 1. Apa yang diminta dan batas otoritas

Owner meminta seluruh pekerjaan roadmap dijalankan, dengan tujuan Katarina dapat mencari peluang terbaik
di berbagai pair **tanpa entry paksa**. Roadmap versi `main` yang ditinjau sudah menetapkan urutan
WP1 → review/merge → WP2 dan WP3 → review/merge → WP6 → WP4 → WP5; WP7 memerlukan
keputusan Owner. Karena itu **WP1 saja** yang boleh diserahkan sekarang.
Cakupan WP1 adalah **tujuh simbol inti program holdout per siklus**, **bukan**
klaim pemindaian/setup optimal seluruh pair broker, dan **bukan** izin trading.

Hal yang tetap: satu `UnifiedKatarinaBrain`, observer canonical, aturan keputusan BUY/SELL/WAIT,
semua file yang dilindungi `config/promotion_lock.json`, Risk Governor dan batas drawdown 35%,
ketentuan holdout, profil DEMO (masih usulan), serta **LIVE OFF / tidak mengirim order**.
Tidak ada perubahan pada terminal MT5, peluncur observer aktif, atau checkout `C:\Katarina\code` yang berjalan.

#### 2. Riwayat PR, branch, dan alasan perubahan arah

| Bukti | Status / penjelasan |
|---|---|
| Baseline `main` | `69de5a3f00925173f5e3163946e29ff657bbf195`; roadmap WP1–WP7 masuk melalui [#182](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/182) |
| Eksperimen awal [#183](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/183) | Menambahkan survei quote seluruh simbol broker secara bergiliran, opsi lingkungan, tes dan panduan. **DITUTUP tanpa merge** ketika diketahui roadmap terbaru mewajibkan WP1 terlebih dahulu. Kode eksperimen **tidak masuk main atau VPS aktif** |
| Branch kerja WP1 | `feat/wp1-observer-universe-20261022`, dibuat dari `main` `69de5a3` |
| [PR #184 — WP1](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/184) | **OPEN, belum merge**. Review Claude belum tercatat pada saat pemeriksaan ini. Semua perubahan WP1 masih di branch PR |
| Batas paket berikutnya | WP2 belum dimulai karena WP1 belum merge; WP3–WP6 mengikuti prasyarat R0; WP7 tetap keputusan Owner |

**Pelajaran dari #183:** prototipe riset yang secara teknis lulus beberapa tes tidak otomatis
selaras dengan urutan roadmap. Prototipe sengaja tidak dipromosikan dan tidak disatukan dengan WP1.

#### 3. Daftar lengkap berkas yang berubah pada PR #184

Berikut seluruh **16 berkas** yang ditampilkan oleh GitHub pada diff PR sebelum log ini
diperpanjang (penambahan catatan audit ini tetap berada di `docs/ROADMAP.md`).

| Berkas | Apa yang dilakukan dan alasannya |
|---|---|
| `config/observer_universe.json` **(baru)** | Mendaftarkan simbol persis milik broker: `XAUUSD.vx`, `NAS100.vx`, `US30.vx`, `JPN225.vx`, `EURUSD.vx`, `GBPUSD.vx`, `USDJPY.vx`; XAUUSD pertama, `rotating_slots=0`. Cocok dengan simbol program holdout |
| `src/katarina/intelligence/broker/observer_universe.py` **(baru)** | `ObserverUniverse`, `load_universe`, `select_symbols`; validasi JSON, core tidak kosong/duplikat, batas 17, nama broker persis, mode trade yang layak, pelaporan core yang hilang, pembatas slot rotasi |
| `src/katarina/intelligence/cognition/observer.py` | Opsi `universe` memilih semua core yang tersedia tanpa pemotongan `max_symbols` lama; yang hilang masuk kartu `WAIT` dengan `sensor_reason=CORE_SYMBOL_UNAVAILABLE` dan ledger quote `FAILED`. Tanpa `universe`, jalur lama dipertahankan |
| `src/katarina/intelligence/cognition/continuous_observation.py` | Meneruskan konfigurasi ke satu observer existing; menolak kombinasi `universe` dan `KATARINA_ALL_MARKET_RESEARCH=1` **sebelum** worker dimulai |
| `src/katarina/intelligence/cognition/unified_brain.py` | Meneruskan `universe` pada one-pass dan observer terhubung; validasi jenis dan mempertahankan satu otak |
| `src/katarina/adapters/automatic_connection.py` | Meneruskan `universe` melalui jalur koneksi broker baca-saja; jalur tanpa opsi tetap kompatibel |
| `scripts/ai/run_contextual_market_observer.py` | Menambah CLI `--universe PATH`, validasi config, dan penolakan bentrok dengan mode all-market-research |
| `src/katarina/intelligence/broker/data_recovery.py` | Menambah kode alasan stabil `CORE_SYMBOL_UNAVAILABLE` supaya kegagalan sensor tidak kehilangan sebab |
| `src/katarina/intelligence/lab/continuous_research_lab.py` | `select_batch(..., exclude=())` agar slot rotasi tidak mengulang core. Nilai default tidak mengubah perilaku lama |
| `tests/unit/intelligence/test_observer_universe.py` **(baru)** | Memeriksa kesamaan dengan program holdout, urutan core, simbol tidak tersedia/nontradeable, konfigurasi invalid, exclude, pembatas slot saat core hilang |
| `tests/integration/test_wp1_observer_universe.py` **(baru)** | Memakai broker sintetis untuk memeriksa alur observer dan ledger `FAILED`, mode lama, urutan core, penolakan mode worker bentrok, dan 0 order |
| `docs/ROADMAP.md` | Contoh CLI `--universe` dan status R5 WP1, kemudian log kerja R5A ini |
| `CLAUDE.md` | Memperbarui peta modul/CLI dan mencatat WP1 belum dideploy |
| `CHANGELOG.md` | Mencatat perubahan material WP1, alasan, batas keamanan dan nomor PR |
| `docs/maintenance/RUNTIME_MODULE_MAP.md` | Regenerasi peta impor runtime setelah penambahan modul |
| `ops/deployment/release-manifest.json` | Regenerasi hash inventaris deployable sesuai kode WP1; pemeriksaan `MATCH` |

Tidak ada berkas `config/promotion_lock.json`, strategi aktif, `market_decision`,
`contextual_decision_intelligence`, konfigurasi risiko atau eksekusi yang disentuh.
`core` tepat 7 adalah syarat data Tahap 0; masih perlu pembuktian kinerja broker di WP6.

#### 4. Cara pelaksana mengerjakan, urutan dan pembuktian

1. **Pemeriksaan awal baca-saja:** membaca `CLAUDE.md`, roadmap `R0–R7`, file observer,
   jalur CLI → koneksi → `run_continuous` → `UnifiedKatarinaBrain` → `BrainObserver.run`,
   daftar simbol holdout, dan file yang dikunci gerbang promosi. Dikonfirmasi bahwa observer
   VPS sedang mengamati 3 simbol default.
2. **Branch aman:** membuat branch WP1 dari `main` terbaru, tanpa checkout branch
   pada direktori kode produksi VPS.
3. **Tes lebih dahulu (RED):** commit [`ee75949`](https://github.com/alfaauliau-katarinaAI/Katarina-AI/commit/ee75949ad4466c3be462224be0da6badf5bc623f)
   menambahkan tes WP1. Pelaksanaan pertama memang gagal `ModuleNotFoundError` karena
   `observer_universe.py` belum ada — kegagalan yang disengaja untuk membuktikan tes efektif.
4. **Implementasi inti:** menambahkan daftar core eksplisit dan `ObserverUniverse`,
   menghubungkan parameter melalui **jalur yang sudah ada**, mempertahankan default,
   menambahkan alasan WAIT untuk core hilang, dan opsi rotasi terpisah dari core.
5. **Tes integrasi dan diagnosis:** pengujian awal untuk core yang tidak tersedia gagal
   sebelum publikasi `latest.json`, ternyata broker sintetis hanya memiliki dua simbol
   untuk verifikasi jam. Ledger menunjukkan `BROKER_CLOCK_NOT_VERIFIED`.
   **Tes diperbaiki** agar tetap menyediakan tiga simbol sah untuk kuorum jam
   dan satu simbol core tambahan yang hilang. Tidak mengendurkan pengecekan waktu broker
   atau membuat data sintetis menjadi bukti pasar nyata.
6. **Audit regresi tambahan:** ditemukan bentrok `universe` + `ALL_MARKET_RESEARCH` baru
   ditolak terlalu lambat (worker mungkin mulai terlebih dahulu). Ditambah tes RED lalu
   dipindah menjadi penolakan awal **sebelum host lock / worker startup**
   (commit [`b727d5a`](https://github.com/alfaauliau-katarinaAI/Katarina-AI/commit/b727d5a1976d50c7308b7f088b115a45dbc7d6a9)).
7. **Batas rotasi diperbaiki:** jika beberapa core hilang, perhitungan lama bisa memasukkan
   simbol rotasi melebihi `rotating_slots`. Tes regresi baru dan perbaikan
   `selected_rotating` memastikan batas yang dikonfigurasi selalu dihormati
   (commit [`9018dee`](https://github.com/alfaauliau-katarinaAI/Katarina-AI/commit/9018dee898eb0f2cc93ae79f208c220d78a0918b)).
8. **Dokumentasi dan hash:** memperbarui roadmap, changelog, peta untuk Claude,
   regenerasi `RUNTIME_MODULE_MAP.md` dan `release-manifest.json`. Penyesuaian
   dilakukan pada branch PR, **bukan** memodifikasi konfigurasi trader aktif.
9. **Pengujian dan review:** menjalankan tes pada
   `C:\Katarina\_roadmap_validation\wp1-pr` (Git worktree terpisah),
   audit repo/dependensi/promosi, serta CI Body + portable Ubuntu/Windows GitHub.
   PR dibuka untuk review Claude, **tidak di-merge sendiri**, dan WP2 tidak dimulai.

#### 5. Hasil pengujian, termasuk kegagalan yang tidak disembunyikan

| Uji / sumber | Hasil yang dapat diperiksa |
|---|---|
| Unit + integrasi khusus WP1 pada Python VPS, setelah dua perbaikan | **12 tes lulus**, sekitar 3 detik, 0 kegagalan; tes baru dan fixture memakai data sintetis, bukan bukti hasil trading |
| GitHub Actions commit terakhir sebelum audit ini | [Run **39824790896**](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/39824790896): **Body PASS, Portable Ubuntu PASS, Portable Windows PASS**; job opsional tanpa konfigurasi yang sesuai berstatus SKIPPED |
| Audit hygiene | **PASS_REPOSITORY_HYGIENE**: `forbidden=0`, `tracked_junk=0`, `empty_source=0` |
| Audit link dependensi | **PASS_LOCAL_DEPENDENCY_LINKS** pada checkout uji |
| Gerbang promosi | **PASS_PROMOTION_GATE**; file strategi/risk terkunci tetap tidak diubah |
| Manifest | **MATCH**, **301** berkas kode, tidak ada berkas hilang, berubah tanpa manifest, atau tambahan tak tercatat pada pemeriksaan |
| Full unit suite Python pada VPS terpisah | **1227 tes dijalankan; FAILED: 1 failure, 3 errors, 2 skipped**. Hasil ini **bukan PASS**: lingkungan Python VPS yang dipakai uji tidak memiliki `numpy`, dua pengujian menemui file SQLite sementara terkunci di Windows, dan satu tes gagal karena perbedaan representasi path 8.3 `ADMINI~1` vs `Administrator`. CI terpisah GitHub lulus. Tidak mengubah paket production untuk menutupi kegagalan tersebut |
| Kelulusan Tahap 0, uji broker 7 simbol aktual | **BELUM**. Tes kode tidak menggantikan 10 hari bursa observasi, bukti unduhan tick lengkap atau pemantauan sumber daya WP6 |

Audit ini mencatat hasil sesuai saat diperiksa, **bukan** mengklaim semua tes manual VPS,
demonstrasi broker tujuh simbol, atau profit factor strategi sudah lulus. CI pada commit
dokumentasi sesudahnya perlu diperiksa ulang bila review mensyaratkan.

#### 6. Keadaan VPS aktif dan batas pemasangan

Pada pemeriksaan baca-saja terakhir sebelum catatan ini, `C:\Katarina\code` masih di
`30d043c`; status observer pada **22 Oktober 2026 17:34 UTC (23 Oktober 00:34 WIB)**
menunjukkan **749 siklus berhasil, 3 simbol berdata, 0 kegagalan beruntun, 0 order,
`live_execution_authorized=false`**. Snapshot tersebut adalah **rekaman pada waktu itu**,
bukan klaim status real-time berkelanjutan.

Pekerjaan yang dilakukan pada VPS hanya berupa **checkout/worktree uji terpisah**
(`C:\Katarina\_roadmap_validation\...`), fetch Git untuk mengambil branch,
pengujian sintetis, serta generator dokumentasi/manifest pada worktree.
Tidak ada merge, restart observer, perubahan `run-observer.ps1`, aktivasi Algo Trading,
atau perubahan file produksi Katarina. Runtime masih harus melalui WP6 dengan syarat
monitor 5→7 simbol, beban RAM, durasi siklus, dan kualitas tick.

#### 7. Yang belum dikerjakan, urutan dan tindakan pemeriksaan

| Paket/tahap | Status objektif | Prasyarat berikutnya |
|---|---|---|
| WP1 | Kode + tes + dokumentasi pada [PR #184](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/184); **belum review/merge/deploy** | Claude review diff, berkas terkunci, tes, dan manifest; perbaiki komentar pada branch yang sama |
| WP2 | **Belum mulai** | WP1 harus merge, lalu pengunduh tick streaming dengan bukti byte-identik dan puncak memori sesuai R4 |
| WP3 | **Belum mulai** | Mulai sesuai urutan R0 (boleh paralel WP2), hanya diagnosis berita tanpa mengubah blackout/keputusan |
| WP6 | **Belum mulai** | WP1–WP3 merge dan CI hijau; uji VPS core 5 selama ≥ 2 jam baru 7 bila kriteria aman |
| WP4 | **Belum mulai** | WP6 tahap A berjalan; jurnal kandidat/replay teknis tanpa perubahan action atau order |
| WP5 | **Belum mulai** | WP4 merge dan ≥ 5 hari bursa data kandidat; ranking hanya riset, diuji alat Tahap 1 |
| WP7 | **Belum diputuskan** | Owner menetapkan profil DEMO, aturan berita bila diusulkan, dan status repo/issue |
| Tahap 0–5 | **Belum ada kelulusan keseluruhan** | Evaluasi data pasar, holdout, forward test, dan approval sesuai kriteria tiap tahap; tidak bisa dilompati |

**Cara Owner memeriksa:** buka [PR #184 → Files changed](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/184/files)
untuk seluruh diff, **Commits** untuk sejarah perbaikan, **Checks** untuk CI,
dan bagian R5A ini pada [ROADMAP branch WP1](https://github.com/alfaauliau-katarinaAI/Katarina-AI/blob/feat/wp1-observer-universe-20261022/docs/ROADMAP.md).
Status di `main` boleh berbeda sampai PR disetujui dan digabung; **jangan anggap isi
branch sudah aktif di VPS**.


### R6. Perintah siap pakai untuk pelaksana

Salin satu blok utuh ke pelaksana. Setiap blok berdiri sendiri; pelaksana tidak perlu konteks percakapan lain.

**Perintah WP1**
```text
Kamu mengerjakan repo GitHub alfaauliau-katarinaAI/Katarina-AI (Python, dokumen berbahasa Indonesia).
1. Baca berurutan: CLAUDE.md, lalu docs/ROADMAP.md bagian "Rencana kerja perbaikan" sub-bagian R1, R2, R3 dan
   "WP1 — Daftar simbol eksplisit untuk observer". Ikuti R2 langkah demi langkah tanpa melompat.
2. Kerjakan HANYA WP1, satu PR ke main berjudul "WP1: daftar simbol eksplisit untuk observer".
3. Dilarang: mengubah berkas di config/promotion_lock.json, membuat catatan promosi, mengubah Risk Governor atau batas
   35%, mengaktifkan DEMO/LIVE, menambah observer/worker/thread, menambah dependensi, mengubah VPS, merge sendiri.
4. Sebelum membuka PR jalankan semua perintah di R2 langkah 6; semua harus lulus dan manifest MATCH.
5. Deskripsi PR: Ringkasan, daftar berkas diubah beserta alasannya, Keamanan (berkas terkunci tidak berubah, LIVE OFF,
   tanpa perubahan VPS), Pengujian (salin jumlah tes dan hasil audit), dan hal yang belum yakin.
6. Isi baris WP1 di tabel R5 docs/ROADMAP.md: status "PR dibuka", nomor PR.
Jika ada langkah yang tidak bisa dikerjakan tanpa melanggar butir 3, berhenti dan tulis alasannya di PR.
```

**Perintah WP2**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP1 sudah di-merge).
1. Baca CLAUDE.md, lalu docs/ROADMAP.md bagian "Rencana kerja perbaikan": R2, R3 dan "WP2 — Pengunduh tick hemat
   memori". Baca seluruh src/katarina/intelligence/operations/observation_ledger.py dan
   tests/unit/intelligence/test_observation_ledger.py sebelum mengubah apa pun.
2. Kerjakan HANYA WP2, satu PR "WP2: pengunduh tick streaming hemat memori".
3. Wajib: hasil berkas dan sha256 byte-identik dengan implementasi lama (buktikan dengan tes pembanding yang menyalin
   fungsi lama ke berkas tes), tracemalloc puncak < 50 MB untuk 2.000.000 tick/hari, tes lama tidak diubah.
4. Larangan, pengecekan, isi PR dan pembaruan tabel R5 sama seperti perintah WP1 butir 3–6.
```

**Perintah WP3**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru.
1. Baca CLAUDE.md, lalu docs/ROADMAP.md bagian "Rencana kerja perbaikan": R1 (T5), R2, R3 dan "WP3 — Diagnosis jalur
   berita". Baca fungsi load_articles dan prepare_news di src/katarina/intelligence/cognition/observer.py,
   src/katarina/intelligence/news/news_intelligence.py dan src/katarina/intelligence/operations/data_health.py.
2. Kerjakan HANYA WP3, satu PR "WP3: diagnosis jalur berita observer".
3. Wajib: hanya menambah penghitung/laporan/tabel ledger; logika blackout, ambang, FRESH_SECONDS dan keputusan TIDAK
   berubah; verdict data_health tidak berubah (buktikan dengan tes).
4. Larangan, pengecekan, isi PR dan pembaruan tabel R5 sama seperti perintah WP1 butir 3–6.
```

**Perintah WP4**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP1–WP3 sudah di-merge).
1. Baca CLAUDE.md, lalu docs/ROADMAP.md bagian "Rencana kerja perbaikan": R1 (T4, T6), R2, R3 dan "WP4 — Jurnal
   kandidat riset". Baca dataclass ContextDecision di
   src/katarina/intelligence/cognition/contextual_decision_intelligence.py (JANGAN diubah; berkas terkunci),
   src/katarina/research/validation.py (format Trade) dan src/katarina/research/context_export.py (cara membaca tick
   Tahap 0 yang terverifikasi hash).
2. Kerjakan HANYA WP4, satu PR "WP4: jurnal kandidat riset dan replay sinyal teknis".
3. Wajib: action/keputusan observer tidak berubah (tes membuktikan kartu sama sebelum/sesudah), orders_submitted 0,
   data_until <= entry_at selalu, aturan exit dibaca dari spec hipotesis terdaftar (tanpa default di kode),
   replay hanya membaca bar yang diekspor dan menulis ke build/.
4. Larangan, pengecekan, isi PR dan pembaruan tabel R5 sama seperti perintah WP1 butir 3–6.
```

**Perintah WP5**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Mulai dari origin/main terbaru (WP4 sudah di-merge).
1. Baca CLAUDE.md, docs/ROADMAP.md bagian "Rencana kerja perbaikan": R2, R3, "WP5 — Hipotesis perankingan antarpair",
   docs/research/VALIDATION_PROTOCOL.md, docs/research/MARKET_INTELLIGENCE.md, src/katarina/engines/opportunity.py
   (JANGAN diubah) dan src/katarina/research/market_intelligence.py.
2. Kerjakan HANYA WP5, satu PR "WP5: hipotesis perankingan antarpair (riset)".
3. Wajib: semua bobot dan ambang dibaca dari parameters spec yang terdaftar di HypothesisRegistry; setiap varian
   bobot adalah hipotesis baru (jumlah percobaan bertambah); korelasi dihitung kausal dari data sebelum entry;
   tidak ada perubahan pada jalur keputusan observer.
4. Larangan, pengecekan, isi PR dan pembaruan tabel R5 sama seperti perintah WP1 butir 3–6.
```

**Perintah perbaikan setelah review**
```text
Repo alfaauliau-katarinaAI/Katarina-AI. Buka PR #<nomor> dan baca semua komentar review.
Perbaiki setiap poin di branch PR yang sama (commit baru, jangan force-push), ikuti docs/ROADMAP.md R2, jalankan
ulang semua pengecekan R2 langkah 6, lalu balas setiap komentar dengan apa yang diubah (atau alasan bila tidak diubah).
```

### R7. Daftar periksa review Claude (dipakai saat meninjau PR pelaksana)

1. Diff tidak menyentuh berkas di `config/promotion_lock.json`; `promotion_gate.py --check` PASS.
2. Perilaku tanpa opsi baru identik; tes lama tidak diubah kecuali paket memintanya.
3. Tidak ada jalur order, thread/worker baru, jaringan di tes, atau dependensi baru.
4. Waktu UTC ber-zona, fail-closed dengan kode alasan, SQLite di `with db:`, hasil deterministik.
5. Tes baru benar-benar gagal tanpa perubahan (diverifikasi dengan membalik perubahan secara lokal).
6. CI Body, Portable Ubuntu dan Windows hijau; manifest `MATCH`; CHANGELOG, CLAUDE.md dan tabel R5 diperbarui.
7. Untuk paket yang diterapkan ke VPS: rencana WP6 dan batas pemantauan dipenuhi sebelum dinaikkan.

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

Untuk WP1, penentuan tujuh simbol inti boleh memakai config eksplisit setelah review dan
penerapan WP6, tanpa mengubah opsi lama. Contoh peluncur (belum diaktifkan di VPS):
`run_contextual_market_observer.py --continuous --universe config\\observer_universe.json --connection-config PRIVATE_CONFIG --state-dir PRIVATE_STATE --interval-seconds 60`.
Jika simbol inti tidak tersedia pada broker, simpan kartu WAIT dan alasan
`CORE_SYMBOL_UNAVAILABLE` pada ledger; data yang hilang tidak diisi secara sintetis.

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
