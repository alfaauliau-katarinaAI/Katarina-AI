# CLAUDE.md — peta cepat repositori Katarina AI

Ringkasan untuk sesi berikutnya agar tidak perlu membaca ulang seluruh repo (~1.400 berkas).
Diperbarui 21 Oktober 2026. Status rinci (satu sumber): `docs/PROJECT_STATUS.md`; perubahan di `CHANGELOG.md`;
riwayat serah-terima lama ada di riwayat Git (folder `archive/` dihapus 21 Oktober).

## Apa ini

Sistem riset trading MT5 berbasis Python (bahasa dokumen utama: Indonesia).
**Research-only / LIVE OFF**: tidak ada jalur kirim order live. Mode DEMO forward dan
lab riset VPS ada, tetapi Risk Governor (`src/katarina/engines/risk.py`) independen dan
tidak boleh dilemahkan. Owner repo: `alfaauliau-katarinaAI`; `main` wajib PR + CI.

## Struktur

| Lokasi | Isi |
|---|---|
| `src/katarina/` | Paket utama. `intelligence/` (100 modul dalam 8 subpaket: `cognition/` otak canonical `cognition/unified_brain.py` → `UnifiedKatarinaBrain` beserta kemampuannya, `perception/` fitur/regime/playbook, `broker/` sensor read-only, `news/`, `demo/`, `shadow/`, `lab/` riset offline, `operations/`), `engines/` (risk, setup quality, eksekusi riset), `monitoring/` (feed status/PnL/entry untuk website), `adapters/` (MT5, transport ZMQ/KAT1), `body/` (stage 11–40 "body framework", modul bernama fungsi; nomor→modul di `katarina.body.STAGE_MODULES` dan `docs/maintenance/BODY_STAGE_MAP.md`), `core/` (orchestrator), `memory/`, `persistence/`, `governance/`, `research/` |
| `katarina_pc.py` + `SETUP_/START_KATARINA.bat` | Entry point uji PC (Python 3.12): `setup, repair, test, doctor, observe, chat, ui, pretrial` |
| `scripts/ai/` | CLI tipis runtime/CI (logika di `src`): `run_contextual_market_observer.py` (observer canonical), demo worker, HF archive sync, publisher monitor. `install_*_test*.py` = patch berpayload untuk VPS uji (tercatat di release manifest) |
| `scripts/research/` | Skrip riset/backtest aktif (dirujuk workflow/dokumen) |
| `scripts/governance/` | Audit CI: hygiene, dependency links, constitution guard, branch inventory |
| VPS (Windows Server 2012 R2) | Diakses lewat Desktop Commander. Runtime: `C:\Katarina\code` (checkout `main`), Python 3.12 di `C:\Katarina\python312`, peluncur observer `C:\Katarina\run-observer.ps1`. Tooling VPS lama dihapus 22 Okt |
| `scripts/pc/`, `scripts/deployment/` | Environment privat PC, redeploy + `release_manifest.py` |
| `mt5/` | EA dan include MQL5 (`Experts/`, `Include/`, `Tests/`) |
| `config/` | Konfigurasi JSON (dimuat lewat nama dinamis; `config/stages/stageNN.json` dibaca per nomor) — jangan hapus walau tampak tak dirujuk |
| `protocol/` | Skema pesan biner KAT1 |
| `website/` | Situs statis publik (Cloudflare Pages); JSON di dalamnya ditulis workflow |
| `sites/runtime-monitor/`, `functions/api/`, `oauth_gateway/`, `services/` | Worker monitor runtime, API Pages, gateway OAuth, relay monitor |
| `docs/` | `architecture/` + `adr/` (kontrak desain, dilindungi CODEOWNERS), `operations/`, `research/`, `validation/` (bukti bertanggal), `reviews/` (freeze record stage 02–09), `deployment/` |
| `tests/` | `unit/` (~1.500), `static/` (115, termasuk `test_module_connectivity.py` yang memastikan semua modul dan import script tersambung), `integration/` (~210), `replay/` dan `research/` (tidak dijalankan Body CI) |
| `.github/workflows/` | 17 workflow. Otomatis hanya `katarina-body-ci.yml` (push/PR; check wajib branch protection berasal dari sini — jangan ganti nama job-nya), `katarina-hotnews.yml` (jadwal), `stage35-tester-safety.yml` (path filter). Sisanya manual (`workflow_dispatch`); `stage07-transport.yml` dan `stage06-09-clearance.yml` memilih job lewat input `check` |

## Menjalankan pengecekan (sama dengan Body CI)

```bash
pip install -r requirements-stage07.txt numpy
PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_*.py'
PYTHONPATH=src python -m unittest discover -s tests/static -p 'test_*.py'
PYTHONPATH=src python -m unittest discover -s tests/integration -p 'test_*.py'
python scripts/governance/audit_repo_hygiene.py --repo-root . --output build/repository-hygiene.json
python scripts/governance/audit_dependency_links.py --repo-root . --output build/validation/dependency-links.json
```

Hasil 21 Oktober 2026 (setelah penghapusan 231 berkas tak terpakai): unit 1.395 OK, static 115 OK (4 skip), integration 207 OK (3 skip),
replay 11 OK, research 5 OK, hygiene dan dependency links PASS.

## Aturan penting saat mengubah

- Jangan menghapus berkas hanya karena tidak ditemukan rujukan nama: config dimuat dinamis,
  workflow adalah entry point, website disajikan langsung, `scripts/ai/run_market_brain.py` dan
  `run_decision_brain_v3.py` sengaja jadi stub penolak (tombstone) legacy.
- Berkas yang tercatat di `ops/deployment/release-manifest.json` (368 berkas, dibuat ulang
  21 Oktober) diverifikasi saat redeploy. Setelah mengubah kode di `src/katarina`, `scripts/ai`,
  `scripts/deployment`, `scripts/memory` atau `mt5`, buat ulang dengan
  `python scripts/deployment/release_manifest.py --manifest ops/deployment/release-manifest.json --generate`
  lalu verifikasi tanpa `--generate` (harus `MATCH`).
- Berkas yang terbukti tidak dipakai (cek `RUNTIME_MODULE_MAP.md` + grep config/workflow) dihapus lewat PR;
  riwayatnya tetap ada di Git. Folder `archive/` sudah tidak ada.
- Jangan commit runtime state, data broker, kredensial, atau snapshot heartbeat VPS
  (`.gitignore` + `audit_repo_hygiene.py` menjaganya).
- Satu otak canonical: jangan menambah observer/worker paralel atau jalur eksekusi tersembunyi.

## Rencana perapian bertahap

Rencana 8 tahap Owner ada di `docs/maintenance/CLEANUP_PLAN.md` (aturan wajib di bagian atasnya:
tanpa perubahan perilaku, satu tahap satu PR, arsipkan bukan hapus, perbarui CLAUDE.md dan CHANGELOG).

| Tahap | Status |
|---|---|
| 1. Peta modul runtime | Selesai 21 Okt — `docs/maintenance/RUNTIME_MODULE_MAP.md` |
| 2. Pensiunkan otak lama | Selesai: `intelligence/brain.py` (`KatarinaAIBrain`) + dependennya diarsipkan (2a); otak berversi diganti nama kemampuan di Tahap 3 |
| 3. Subpaket `intelligence/` | Selesai: modul dipindah dan semua rujukan aktif diganti (3a); shim lokasi lama dihapus (3b). Import `katarina.intelligence.<nama_lama>` kini gagal — pakai path subpaket |
| 4. Nama fungsi `body/stageNN` | Selesai: `body/stageNN.py` → nama fungsi (mis. `stage16` → `risk_governor`), manifest `implementation_module` diperbarui, nama file manifest tetap. Alias `katarina.body.stageNN` sudah dihapus 21 Okt |
| 5. Sederhanakan workflow | Selesai: 12 workflow `stage07-*` → `stage07-transport.yml`, 4 workflow stage06/08/09 → `stage06-09-clearance.yml` (pemicu manual, tidak digabung ke Body CI karena pemicunya beda). Lima workflow riset lama tanpa run 30 hari (v9, v10, tournament, replay, frozen-xau) → `archive/.github/workflows/` |
| 6. Logika script ke `src` | Selesai: `verify_unified_katarina` → `katarina.governance.unified_verification`, `audit_self_evolution_runner` → `katarina.governance.self_evolution_audit`; script tinggal CLI tipis. Dikecualikan: `hf_archive_sync.py` (layanan mandiri stdlib, dimuat lewat path dari venv HF terpisah, systemd, installer), `mt5_shadow_lab.py` (sudah CLI argparse yang mendelegasikan ke `src`). `scripts/research` tidak diubah logikanya; 3 script dari workflow riset yang diarsipkan ikut diarsipkan |
| 7. Website ke repo sendiri | Disiapkan, **menunggu Owner**: `scripts/deployment/export_website_repo.py` + langkah di `docs/deployment/STANDALONE_WEBSITE_EXTRACTION.md`. Pembuatan repo via integrasi GitHub ditolak 403; `website/` dkk. tetap di sini sampai Cloudflare Pages terbukti deploy dari repo baru |
| 8. Satu sumber status | Selesai: `docs/PROJECT_STATUS.md` ditulis ulang sebagai satu-satunya status; README hanya ringkas + tautan; status 16 Okt, `CURRENT_PROJECT_HANDOFF.md`, handoff 10/13 Okt, snapshot 11 Okt → `archive/docs/` |

Peta modul dibuat ulang dengan
`python scripts/governance/runtime_import_map.py --output docs/maintenance/RUNTIME_MODULE_MAP.md`
(analisis statis; ikut membaca `config/stages` untuk modul body). Hasil setelah penghapusan 21 Okt: A=223, B=13, C=29, D=2 (paket kosong `domain`, `entrypoints` — dipertahankan karena tercantum di kontrak arsitektur beku `config/repository_architecture.json`).
Nama baru bekas otak berversi: `brain_observer` → `cognition/observer`, `market_decision_brain_v3` →
`cognition/market_decision`, `adaptive_brain_v2` → `cognition/adaptive_observation`, `multi_market_brain` →
`perception/screening`. Modul lain di `intelligence/` mempertahankan nama berkasnya di subpaket barunya.
Dokumen bertanggal, `CHANGELOG`, arsip, dan payload `scripts/ai/install_*` (patch untuk checkout VPS yang
dipatok) sengaja masih memakai path lama.

## Riwayat perapian

- 15 Okt: `docs/operations/REPOSITORY_CLEANUP_20261015.md` (identitas repo, snapshot VPS dihapus).
- 21 Okt (pagi): 45 skrip riset + 27 output ke `archive/`, 3 modul yatim dan 226 import tak terpakai dihapus.
- 21 Okt (malam): `archive/` (168 berkas), 30 alias `body/stageNN.py`, 8 modul yang hanya dipakai test
  beserta test-nya, dan 17 script riset tak dirujuk dihapus (231 berkas).
- 21 Okt (lanjutan): 58 dokumen lama tak dirujuk (riset 10–13 Okt, JSON validasi 10 Okt,
  handoff/maintenance/roadmap lama) dan `select_and_validate_strategies.py` dipindah ke `archive/`;
  `CLAUDE.md` ini ditambahkan.
- 22 Okt: tujuh branch usang dicatat di `docs/maintenance/BRANCH_ARCHIVE_20261022.md` untuk dihapus;
  yang tersisa hanya `main` dan `claude-vps-bridge`.
- 22 Okt (rampingkan A): tooling VPS lama (agent remote, runner self-hosted, BAT, workflow, dokumen, tes) dihapus.
- 22 Okt (rampingkan B): 116 dokumen bertanggal/usang yang tidak dirujuk dihapus.
