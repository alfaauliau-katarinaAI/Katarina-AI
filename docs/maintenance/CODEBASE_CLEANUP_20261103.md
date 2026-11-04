# Audit dan perampingan codebase — mandat Owner 3 November 2026

Sumber mandat: `docs/maintenance/CLAUDE_BLOCKER_CLOSURE_20261103.md` bagian 5 (PR #278) dan instruksi Owner 3 Nov 23:05 WIB.
Aturan perapian tetap mengikuti `docs/maintenance/CLEANUP_PLAN.md`. Laporan per PR dikirim ke Issue #251.
Batas: LIVE OFF, 0 order. Risk Governor, promotion lock, holdout, data broker, database, backup, state VPS dan gate Tahap 0 tidak disentuh.

## A — Baseline (3 Nov 2026, `main` `b723666e`)

| Aspek | Temuan |
|---|---|
| Berkas terlacak | 900 (577 Python). Semua Python lolos parse AST lewat unittest discover |
| VPS | `C:\Katarina\code` di `fd6cff16`; selisih ke `main` hanya docs, tes, `scripts/governance/session_hypothesis.py` dan probe MQL5 diagnostik, sehingga runtime observer identik. Untracked: `docs/governance/MASTER_BLUEPRINT_GOVERNANCE_DRAFT.md` (milik Owner, dibiarkan) |
| Task VPS | `Katarina-Readonly-Observer` (`run-observer.ps1` → `run_contextual_market_observer.py`), `Katarina-Stage0-Daily-Health` (`check_stage0_health.py`). Tidak ada task yang memakai `run_readonly_decisions.py`, HF archive, atau `C:\KatarinaDev` |
| MT5 VPS | Hanya `Scripts\KatarinaBrokerSessionProbe.ex5` milik Katarina; tidak ada EA Katarina yang terpasang |
| Peta modul | A=191, B=40, C=23, D=3. B = modul tahap 11–40 (identitas body, **dipertahankan**); D = kontrak `domain`/`entrypoints`/`ports` (**dilindungi**) |
| `C:\KatarinaDev` | 9 berkas merujuk (3 script aktif, 1 launcher .cmd, 1 PowerShell stage35, sisanya docs/JSON validasi historis) |
| Broad `except` | 93 lokasi di `src`/`scripts`. Triase: sebagian besar fail-closed dengan reason code, beberapa `pass` best-effort pada shutdown/tampilan. Rincian di gelombang C |
| CI flaky | Pada `main`, 1 dari 24 run Body CI terakhir gagal: `test_unified_owner_surface` timeout socket 5 s di Windows. Kegagalan lain di branch WIP sudah diperbaiki sebelum merge |

Label: `DELETE_CONFIRMED` = dihapus dengan bukti; `PROTECTED` = kontrak/identitas; `UNVERIFIED_KEEP` = tidak dapat dibuktikan aman, dipertahankan.

## B1 — jalur MT5 lama dan berkas tak terpakai

| ID | Berkas | Label | Alasan dan bukti | Tindakan pengganti |
|---|---|---|---|---|
| B1-01 | `scripts/ai/run_readonly_decisions.py` | DELETE_CONFIRMED | Observer kedua yang memanggil `mt5.initialize()` langsung ke terminal produksi (melanggar "satu otak canonical" dan larangan initialize di terminal observer); menulis ke `C:\KatarinaDev` yang sudah pensiun; tidak dipanggil task VPS mana pun; tercatat sebagai sisa di `CLEANUP_PLAN.md` | Observer canonical `run_contextual_market_observer.py` |
| B1-02 | `scripts/ai/RUN_READONLY_DECISIONS.cmd` | DELETE_CONFIRMED | Launcher B1-01 dengan path `C:\KatarinaDev\brain-runtime` yang tidak ada di VPS | — |
| B1-03 | `scripts/ai/smoke_closed_market_decision.py` | DELETE_CONFIRMED | Hanya diimpor oleh B1-01; membuka MT5 langsung | — |
| B1-04 | `scripts/ai/install_hf_archive_test.py` | DELETE_CONFIRMED | Installer uji sekali pakai: mengunduh kode dari raw GitHub, path `C:\KatarinaDev` dan kunci `gemini-private`; tidak ada tes; hanya di-`py_compile` workflow manual | `scripts/deployment/install_hf_storage.py` (installer canonical, dites) |
| B1-05 | `mt5/Experts/KatarinaResearchScalperEA.mq5` | DELETE_CONFIRMED | EA dengan 10 metode entry dan `CTrade.Buy/Sell`: "otak trading kedua" di MT5 yang dilarang `mt5/README.md`; tidak dirujuk kode/tes/docs (hanya manifest); tidak terpasang di terminal VPS; bukan identitas (identitas = status dashboard + bridge Stage 06) | Riset setup ada di `src/katarina/research/setups` (Python, offline) |
| B1-06 | `mt5/Include/Katarina/ResearchExtraFeatures.mqh`, `ResearchZoneScalp.mqh` | DELETE_CONFIRMED | Hanya di-include B1-05 | — |
| B1-07 | `tests/fixtures/ohlc/synthetic_regimes.csv` | DELETE_CONFIRMED | Tidak dirujuk berkas mana pun (nama, folder, `ohlc/`) | — |
| B1-08 | `tests/integration/test_legacy_clock_wp12.py::test_legacy_decisions_remain_wait…` | DELETE_CONFIRMED | Menguji B1-01; diganti tes penjaga bahwa script lama tidak kembali | Tes `test_removed_legacy_observer_scripts_stay_removed` |
| B1-09 | `tests/static/test_workspace_path_resolution.py::test_windows_readonly_launcher_uses_its_location` | DELETE_CONFIRMED | Menguji B1-02 | Tes path diperketat (lihat C-01) |

Perbaikan path pada PR yang sama:

| ID | Lokasi | Perbaikan | Tes |
|---|---|---|---|
| C-01 | `scripts/ai/hf_archive_sync.py` default Windows, `scripts/stage35/Run-KatarinaStage35Tester.ps1` default `OutputRoot` | `C:\KatarinaDev\…` → `C:\Katarina\private\hf-storage`, `C:\Katarina\state\readonly-observer`, `C:\Katarina\private\hf-client`, `C:\Katarina\state\stage35`. Config eksplisit tetap menang | `test_no_retired_katarinadev_layout_in_scripts_or_source` (RED sebelum perbaikan, GREEN sesudah) sekarang menolak `KatarinaDev` di `scripts/`, `src/`, `katarina_pc.py` |

Dokumen ikut diperbarui: `docs/architecture/EXPLAINABLE_MARKET_DECISION_V1.md` (petunjuk launcher lama dihapus), `docs/README.md` (tautan `KATARINA_REDEPLOY.md` yang sebelumnya yatim), `CLEANUP_PLAN.md` (sisa diselesaikan).

Rollback: `git revert <SHA merge B1>` mengembalikan semua berkas; tidak ada data/state yang tersentuh.

`UNVERIFIED_KEEP` dari pemindaian B1: `website/deployment-check.json`, `website/PUBLIC_UPDATES_POLICY.md` (disajikan langsung oleh Pages), `SECURITY.md` (kebijakan GitHub), semua `docs/adr` dan `docs/architecture` (PROTECTED), workflow manual (entry point), `docs/validation/2026-10-10-*.json` (bukti historis yang dirujuk), `ops/deployment/katarina-hf-storage.*` (template arsip HF portabel, dirujuk installer dan dokumen redeploy).

B1 di-merge sebagai `main` `39fc0859` (PR #279). CI: Body, Ubuntu PASS; Windows gagal satu kali pada tes flaky `test_unified_owner_surface` (diperbaiki di C1), lalu PASS saat dijalankan ulang.

## C1 — konsolidasi DST dan tes flaky

| ID | Lokasi | Masalah | Perbaikan | Bukti/tes |
|---|---|---|---|---|
| C1-01 | `intelligence/operations/observation_ledger.py` (`_nth_sunday`, `_is_us_dst`), `intelligence/operations/data_health.py` (`_nth_sunday`, `_last_sunday`, `dst_transitions`), `intelligence/perception/symbol_playbooks.py` (`_nth_sunday`, `_last_sunday` + 2 aturan inline), `research/bar_clock_evidence.py` (`is_us_dst`, `is_eu_dst`), `research/validation.py` (`is_us_dst`) | Aturan zona waktu/DST ditulis ulang 5 kali; dua modul riset mengimpor helper privat `_nth_sunday` dari `data_health` | Satu modul murni `src/katarina/domain/market_calendar.py` (`nth_sunday`, `last_sunday`, `dst_transitions`, `is_us_dst`, `is_eu_dst`); pemanggil memakai modul ini, API publik lama dipertahankan | Skrip ekuivalensi (kode lama vs baru, 107.892 momen 1990–2100: `_ny_open_utc_minutes`, `_london_start_utc_hour`, `stage0_session_open`, `is_us_dst`/`is_eu_dst`, `dst_transitions`) = identik. `tests/unit/domain/test_market_calendar.py` (6 tes: tanggal, batas half-open, offset non-UTC, naive ditolak, penjaga implementasi kedua) |
| C1-02 | `config/repository_architecture.json` paket `domain` | Paket kontrak kosong | Diisi logika murni stdlib sesuai `DEPENDENCY_RULES.md` (`domain` → stdlib saja). Kontrak tidak diubah; `entrypoints`/`ports` tetap kosong | Peta modul: D 3 → 2 |
| C1-03 | `intelligence/cognition/observer.py:330` | `except Exception: pass` tanpa jejak | `broker_server = None` + komentar: ditolak hilir dengan `CLOCK_BROKER_IDENTITY_MISSING` (`live_clock_probe.py:41`) | Perilaku sama; tes jam WP13 tetap OK |
| C1-04 | `tests/integration/test_unified_owner_surface.py` | Flaky Windows: socket timeout 5 s (run 40969779432, #279) | Konstanta `OWNER_SURFACE_TIMEOUT = 30` dengan alasan tertulis | 9 tes OK lokal; CI Windows |

Triase broad `except` (93 lokasi): tidak ada yang menelan error pada jalur keputusan. Polanya: (a) fail-closed dengan reason code (`ConnectionUnavailable('LOCAL_READ_FAILED')`, `SHADOW_EVALUATION_FAILED_<Type>`, `RETRY_PENDING`, `BOUNDARY_ERROR`, dll.), (b) menutup koneksi lalu `raise` ulang, (c) best-effort tanpa dampak keputusan: shutdown MT5 (`automatic_connection.py:147`, `demo_forward.py:299`, `scripts/mt5/audit_readonly_quotes.py:180`), tampilan dashboard (`mt5_dashboard.py:76`), snapshot berita lama rusak (`scripts/update_hot_news.py:85`, aman karena diganti). Pesan exception mentah sengaja tidak disimpan (hanya nama tipe) agar kredensial tidak bocor. Tidak ada perubahan lebih lanjut.
C1 di-merge sebagai `main` `a9dc9a36` (PR #280); CI Body/Ubuntu/Windows PASS pada percobaan pertama.

## D1 — penelusuran error lewat reason code

| ID | Lokasi | Perubahan | Tes |
|---|---|---|---|
| D1-01 | `scripts/governance/reason_code_index.py` (baru) | Indeks statis: kode → severity (P0/P1/P2 menurut area) → `file:line` sumber → tes yang menyebut kode. Kode keluarga dinamis (`'PREFIX_' + x`, `f'PREFIX_{x}'`) dicatat sebagai `PREFIX_*`. `--find KODE` untuk satu kode (contoh: `--find SHADOW_EVALUATION_FAILED_KeyError` → `observer.py:465`). Kode protokol `protocol/reason_codes_v1.json` hanya ditampilkan; maknanya tidak diubah | `tests/static/test_reason_code_index.py` (5 tes) |
| D1-02 | `docs/maintenance/REASON_CODE_INDEX.md` (baru, hasil generate) | 540 kode: P0 101, P1 229, P2 210; 176 disebut di tes | Dokumen dibuat ulang setiap perapian, seperti `RUNTIME_MODULE_MAP.md` |
| D1-03 | `tests/unit/intelligence/test_live_clock_probe.py` | Kode P0 jam live yang dipakai produksi belum diuji secara literal: `LIVE_FEED_CLOCK_VERIFIED` (status sukses VPS) dan `CLOCK_BROKER_IDENTITY_MISSING` (jalur C1-03) | 2 assert + 1 tes baru (None, kosong, spasi → fail-closed, tanpa hash identitas, 0 order) |

Alur penelusuran baku (ditulis di kepala indeks): kode dari log → `--find` → sumber `file:line` + tes → perbaikan wajib menyertakan tes yang menyebut kode itu → dicatat di `docs/REPAIR_HISTORY.md`.
Format/API lama tidak diubah. Tidak ada kode yang diganti nama: kode yang sudah ada di ledger VPS dan laporan bersifat stabil.

Temuan terbuka (OPEN, bukan blocker codebase): 62 kode P0 belum disebut literal di tes. Sebarannya: `intelligence.broker` 29, `adapters.readonly_cloud` 9, `adapters.automatic_connection` 9, `engines.demo_execution` 8 (DEMO belum aktif), `adapters.dialog_model` 6, `continuous_owner_surface` 1. Banyak di antaranya diuji lewat perilaku (status FAILED/BLOCKED), bukan string kode. Daftar lengkap ada di indeks (kolom Tes = `—`). Disarankan ditambah per paket saat area itu disentuh, terutama sebelum Tahap 3 DEMO.

D1 di-merge sebagai `main` `e186d3cc` (PR #281); CI Body/Ubuntu/Windows PASS pada percobaan pertama.

## E1 — gate akhir dan keputusan

| Gate (pada `main` `e186d3cc`) | Hasil |
|---|---|
| Unit / static / integration | 1.468 OK / 80 OK (4 skip) / 222 OK |
| Hygiene, dependency links | PASS / PASS |
| Promotion gate | PASS (tidak ada berkas terkunci yang berubah di B1–E1) |
| Release manifest | MATCH 312 |
| CI GitHub | Body + Portable brain Ubuntu/Windows PASS pada #279 (Windows dijalankan ulang 1×), #280, #281 |
| Peta modul | A=193, B=40 (identitas body, PROTECTED), C=23 (alat riset Tahap 1–3), D=2 (`entrypoints`, `ports` kontrak) |
| Berkas | 900 → 899 terlacak (8 dihapus; 7 ditambah: kalender domain, 2 tes, alat indeks + tes + indeks, ledger ini) |

Sebelum → sesudah: 0 jalur MT5 di luar observer canonical (sebelumnya 2: `run_readonly_decisions.py`, EA scalper); 0 rujukan `C:\KatarinaDev` di kode (sebelumnya 5 berkas); 1 implementasi DST (sebelumnya 5); 0 tes flaky yang diketahui di `main` (sebelumnya 1); reason code terpetakan ke sumber dan tes (sebelumnya tidak ada).

### Inventaris di luar mandat hapus otomatis (usulan, belum dieksekusi)

VPS (`C:` bebas 12,4 / 39,2 GB). Semua folder ini di luar `code`/`state`/`private`/`backups`/`logs` dan tidak dipakai task mana pun. Usulan hapus perlu izin Owner sesuai §5.2:
- Worktree review lama di `C:\Katarina`: `wp13-ci-review-20261030b` (7,1 MB), `wp13-review-20261030` (7,7 MB), `_audit_20261103_main`, `_release_candidate_v01_20261103`, `_repair_fixture_20261103`, `_review_pr265`, `_review_pr269` (masing-masing ±6 MB), 6 worktree `prunable` di `_roadmap_validation`, `_sync_staging` (97,8 MB), `downloads` (104,9 MB), `_archive`/`_validation_sessionprobe` (kosong). Bersihkan dengan `git -C C:\Katarina\code worktree remove`/`prune`, bukan hapus manual.
- Folder lama di `C:\`: 13 folder riset bertanggal 16–17 Okt, `KatarinaDev`, `KatarinaGitBridge`, `KatarinaGitTest-4e14b098`, `KatarinaCleanup20261029`, `DNSTT-Test` (18,7 MB) beserta task `DNSTT-Test-AutoCleanup`, dan task uji `ChatGPTUserTest`.

GitHub: 10 branch milik PR tertutup. Isinya sudah masuk lewat integrasi #265 atau PR penggantinya. Penghapusan ref ditolak proxy sesi Claude (HTTP 403), jadi perlu dilakukan Owner/manager. Commit tetap bisa dijangkau lewat `refs/pull/N/head` dan SHA berikut:

| Branch | SHA |
|---|---|
| `chatgpt/wp13-clock-since-20261029` | `892c48a02bf4` |
| `feat/roadmap-stage0-broker-discovery-20261022` | `5a894de62f04` |
| `jules/wp10b-swap-cost-sensitivity-20261030-4394559798710015484` | `f36cc7fe2484` |
| `jules-3382505266733406840-c6557a2a` | `d0db291e338d` |
| `manager/roadmap-meeting-repair-sync-20261102` | `4ae1cdd609bb` |
| `manager/wp4-candidate-ledger-20261102` | `59d1679906e9` |
| `manager/wp8-bls-official-calendar-20261102` | `3a31210c0713` |
| `manager/wp8b-pure-setups-20261102` | `ad92a832ccdc` |
| `wp4-research-candidate-ledger-replay-9483643892799621328` | `36e674d589f8` |
| `wp14-readonly-data-auditor-1946873786857947257` | `ce7c4074ee3a` |

Dipertahankan: `main`, `claude-vps-bridge` (CLAUDE.md), `claude-openai-mcp` (UNVERIFIED_KEEP, tanpa PR), branch #278. Ada juga 20 tag `archive/2026-10-11/…` (sisa lama di `CLEANUP_PLAN.md`) yang menunggu keputusan Owner.

### Keputusan

**`CODEBASE_CLEAN_BUT_STAGE_GATE_BLOCKED`.** Codebase rapi, koheren, dan seluruh gate lulus. Tidak ada regresi P0/P1 yang diketahui. Tahap berikutnya masih tertahan bukti eksternal, bukan kode:
1. Tahap 0: 10 hari bursa, sukses ≥ 98%, 3 recovery, 0 order. Data sejak 28 Okt masih `clock_shift_stable NOT_MET`, jadi hitungan harus berjalan dari data bersih pasca-deploy WP13.
2. Bukti jam bar historis M5 (#255) butuh host riset MT5 terpisah.
3. Probe sesi MT5 butuh GUI terminal (Owner).
4. WP6 auto-start tanpa login.

Rekomendasi tahap lanjutan sesuai `docs/ROADMAP.md`: jangan menambah fitur. Biarkan observasi Tahap 0 berjalan. Deploy C1 hanya dilakukan bersama perubahan runtime berikutnya dan dengan izin Owner (perilakunya identik, jadi tidak mendesak). Pengembangan Tahap 1–2 boleh berlanjut offline dengan alat yang sudah ada, menunggu data bersih. Perapian dihentikan di sini; tahap berikutnya menunggu keputusan Owner.
