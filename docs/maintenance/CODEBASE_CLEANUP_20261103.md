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
