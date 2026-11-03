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
