# CLAUDE.md — peta cepat repositori Katarina AI

Ringkasan untuk sesi berikutnya agar tidak perlu membaca ulang seluruh repo (~800 berkas setelah perampingan 22 Okt).
Diperbarui 22 Oktober 2026. Status rinci (satu sumber): `docs/PROJECT_STATUS.md`; **arah pengembangan: `docs/ROADMAP.md`** (wajib diikuti: tahap 0–5, kriteria kelulusan, gerbang promosi, aturan holdout); perubahan di `CHANGELOG.md`;
riwayat serah-terima lama ada di riwayat Git (folder `archive/` dihapus 21 Oktober).

## Apa ini

Sistem riset trading MT5 berbasis Python (bahasa dokumen utama: Indonesia).
**Research-only / LIVE OFF**: tidak ada jalur kirim order live. Mode DEMO forward dan
lab riset VPS ada, tetapi Risk Governor (`src/katarina/engines/risk.py`) independen dan
tidak boleh dilemahkan. Owner repo: `alfaauliau-katarinaAI`; `main` wajib PR + CI.

## Struktur

| Lokasi | Isi |
|---|---|
| `src/katarina/` | Paket utama. `intelligence/` (77 modul dalam 8 subpaket: `cognition/` otak canonical `cognition/unified_brain.py` → `UnifiedKatarinaBrain` beserta kemampuannya, `perception/` fitur/regime/playbook, `broker/` sensor read-only, `news/`, `demo/`, `shadow/` (buku prospektif), `lab/` riset offline, `operations/`), `engines/` (risk, setup quality, eksekusi riset), `monitoring/` (feed status/PnL/entry untuk website), `adapters/` (MT5 read-only, koneksi otomatis, dialog owner; transport KAT1/ZMQ dipensiunkan 22 Okt), `body/` (stage 11–40 "body framework", modul bernama fungsi; nomor→modul di `katarina.body.STAGE_MODULES` dan `docs/maintenance/BODY_STAGE_MAP.md`), `core/` (orchestrator), `memory/`, `persistence/`, `governance/`, `research/` |
| `katarina_pc.py` + `SETUP_/START_KATARINA.bat` | Entry point uji PC (Python 3.12): `setup, repair, test, doctor, observe, chat, ui, pretrial` |
| `scripts/ai/` | CLI tipis runtime/CI (logika di `src`): `run_contextual_market_observer.py` (observer canonical), demo worker, HF archive sync, publisher monitor, tombstone `run_market_brain.py`/`run_decision_brain_v3.py` |
| `scripts/research/` | Hanya 4 skrip yang dipakai workflow/operasional: `audit_private_alpha_holdout`, `run_adaptive_walkforward`, `run_autonomous_strategy_discovery`, `probe_current_market_analogs` |
| `scripts/governance/` | Audit CI: hygiene, dependency links, constitution guard, branch inventory |
| VPS (Windows Server 2012 R2) | Diakses lewat Desktop Commander. Runtime: `C:\Katarina\code` (checkout `main`), Python 3.12 di `C:\Katarina\python312`, peluncur observer `C:\Katarina\run-observer.ps1`. Tooling VPS lama dihapus 22 Okt |
| `scripts/pc/`, `scripts/deployment/` | Environment privat PC, redeploy + `release_manifest.py` |
| `mt5/` | EA dan include MQL5 (`Experts/`, `Include/`, `Tests/`) |
| `config/` | Konfigurasi JSON. `config/stages/stageNN.json` dibaca per nomor (jangan dihapus); config lain hanya boleh dihapus jika tidak ada kode yang memuat namanya |
| `protocol/` | Skema pesan KAT1 — kontrak validation/health engine (implementasi transport sudah dipensiunkan) |
| `website/` | Situs statis publik (Cloudflare Pages); JSON di dalamnya ditulis workflow |
| `sites/runtime-monitor/`, `functions/api/`, `oauth_gateway/`, `services/` | Worker monitor runtime, API Pages, gateway OAuth, relay monitor |
| `docs/` | `architecture/` + `adr/` (kontrak desain, dilindungi CODEOWNERS), `operations/` (panduan GitHub), `reviews/` (freeze record stage yang dibaca audit), `research/` + `validation/` (hanya bukti yang dirujuk config/tes), `deployment/`, `maintenance/` |
| `tests/` | `unit/` (~1.140), `static/` (69, termasuk `test_module_connectivity.py` yang memastikan semua modul dan import script tersambung), `integration/` (~200) |
| `.github/workflows/` | 11 workflow. Otomatis hanya `katarina-body-ci.yml` (push/PR; check wajib branch protection berasal dari sini — jangan ganti nama job-nya), `katarina-hotnews.yml` (jadwal), `stage35-tester-safety.yml` (path filter). Sisanya manual (`workflow_dispatch`); `stage06-09-clearance.yml` memilih job lewat input `check` |

## Menjalankan pengecekan (sama dengan Body CI)

```bash
pip install -r requirements-stage07.txt numpy
PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_*.py'
PYTHONPATH=src python -m unittest discover -s tests/static -p 'test_*.py'
PYTHONPATH=src python -m unittest discover -s tests/integration -p 'test_*.py'
python scripts/governance/audit_repo_hygiene.py --repo-root . --output build/repository-hygiene.json
python scripts/governance/audit_dependency_links.py --repo-root . --output build/validation/dependency-links.json
```

Hasil 22 Oktober 2026 (setelah perampingan A–E dan sinkronisasi DD 35%): unit 1.139 OK, static 69 OK (4 skip), integration 204 OK,
hygiene dan dependency links PASS.

## Aturan penting saat mengubah

- Jangan menghapus berkas hanya karena tidak ditemukan rujukan nama: `config/stages/stageNN.json` dimuat per nomor,
  workflow adalah entry point, website disajikan langsung, `scripts/ai/run_market_brain.py` dan
  `run_decision_brain_v3.py` sengaja jadi stub penolak (tombstone) legacy.
- Berkas yang tercatat di `ops/deployment/release-manifest.json` (291 berkas, dibuat ulang
  22 Oktober) diverifikasi saat redeploy. Setelah mengubah kode di `src/katarina`, `scripts/ai`,
  `scripts/deployment`, `scripts/memory` atau `mt5`, buat ulang dengan
  `python scripts/deployment/release_manifest.py --manifest ops/deployment/release-manifest.json --generate`
  lalu verifikasi tanpa `--generate` (harus `MATCH`).
- Berkas yang terbukti tidak dipakai (cek `RUNTIME_MODULE_MAP.md` + grep config/workflow) dihapus lewat PR;
  riwayatnya tetap ada di Git. Folder `archive/` sudah tidak ada.
- Jangan commit runtime state, data broker, kredensial, atau snapshot heartbeat VPS
  (`.gitignore` + `audit_repo_hygiene.py` menjaganya).
- Satu otak canonical: jangan menambah observer/worker paralel atau jalur eksekusi tersembunyi.
- Ikuti `docs/ROADMAP.md`: tidak ada strategi/parameter keputusan yang masuk sistem aktif tanpa catatan
  kelulusan validasi + persetujuan Owner; holdout hanya dibuka sekali per strategi final; kerjakan tahap berurutan.

## Aturan dan status perapian

Aturan wajib ada di `docs/maintenance/CLEANUP_PLAN.md` (diperbarui 22 Okt): tanpa perubahan perilaku,
satu kelompok perubahan satu PR, **yang tidak dipakai dihapus langsung — bukan diarsipkan** (keputusan Owner
22 Okt; tidak ada folder/branch/tag arsip baru), jaga daftar identitas Katarina di dokumen itu, perbarui
CLAUDE.md dan CHANGELOG. Rencana 8 tahap 21 Okt dan perampingan A–E 22 Okt sudah selesai; hanya Tahap 7
(website ke repo sendiri) yang menunggu Owner. Sisa yang diketahui juga tercatat di sana.

Peta modul dibuat ulang dengan
`python scripts/governance/runtime_import_map.py --output docs/maintenance/RUNTIME_MODULE_MAP.md`
(analisis statis; ikut membaca `config/stages` untuk modul body). Hasil 22 Okt: A=183, B=40, C=8, D=3. Sebagian besar B adalah modul tahap 11–40 (engines, governance, perception dasar, research) yang hanya diuji tes — itu identitas body Katarina, **jangan dihapus**. D = paket kosong `domain`, `entrypoints`, `ports` (tercantum di kontrak arsitektur beku `config/repository_architecture.json`).
Nama baru bekas otak berversi: `brain_observer` → `cognition/observer`, `market_decision_brain_v3` →
`cognition/market_decision`, `adaptive_brain_v2` → `cognition/adaptive_observation`, `multi_market_brain` →
`perception/screening`. Modul lain di `intelligence/` mempertahankan nama berkasnya di subpaket barunya.
`CHANGELOG` sengaja masih memakai path lama.

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
- 22 Okt (rampingkan C): 62 skrip riset sekali pakai, `research/safety`, tes replay/research, dan 25 tes khusus skrip riset dihapus.
- 22 Okt (rampingkan D): transport KAT1/ZMQ (codec, sesi, ZMQ/TCP, port transport, vektor golden, jembatan MT5 Stage07 + multi-symbol extension, workflow `stage07-transport`, tes, ADR/dokumen khusus) dihapus; skema `protocol/` dipertahankan.
- 22 Okt (rampingkan E): modul riset/shadow-paper yang yatim, 20 skrip `scripts/ai`/`mt5`/lainnya tanpa rujukan, 5 workflow manual yang mengulang Body CI, 15 config tanpa pemuat, dan dependensi `pyzmq`/`tornado` dihapus. Total repo turun dari ~1.211 berkas/174 ribu baris menjadi ~795 berkas/92 ribu baris.
