# CLAUDE.md — peta cepat repositori Katarina AI

Ringkasan untuk sesi berikutnya agar tidak perlu membaca ulang seluruh repo (~1.400 berkas).
Diperbarui 21 Oktober 2026. Status rinci: `docs/PROJECT_STATUS.md`, `CHANGELOG.md`,
`docs/CURRENT_PROJECT_HANDOFF.md`.

## Apa ini

Sistem riset trading MT5 berbasis Python (bahasa dokumen utama: Indonesia).
**Research-only / LIVE OFF**: tidak ada jalur kirim order live. Mode DEMO forward dan
lab riset VPS ada, tetapi Risk Governor (`src/katarina/engines/risk.py`) independen dan
tidak boleh dilemahkan. Owner repo: `alfaauliau-katarinaAI`; `main` wajib PR + CI.

## Struktur

| Lokasi | Isi |
|---|---|
| `src/katarina/` | Paket utama. `intelligence/` (107 modul; otak canonical `unified_brain.py` → `UnifiedKatarinaBrain`), `engines/` (risk, setup quality, eksekusi riset), `monitoring/` (feed status/PnL/entry untuk website), `adapters/` (MT5, transport ZMQ/KAT1), `body/` (stage 11–40 "body framework"), `core/` (orchestrator), `memory/`, `persistence/`, `governance/`, `research/` |
| `katarina_pc.py` + `SETUP_/START_KATARINA.bat` | Entry point uji PC (Python 3.12): `setup, repair, test, doctor, observe, chat, ui, pretrial` |
| `scripts/ai/` | CLI runtime: `run_contextual_market_observer.py` (observer canonical), demo worker, HF archive sync, publisher monitor. `install_*_test*.py` = patch berpayload untuk VPS uji (tercatat di release manifest) |
| `scripts/research/` | Skrip riset/backtest aktif (dirujuk workflow/dokumen) |
| `scripts/governance/` | Audit CI: hygiene, dependency links, constitution guard, branch inventory |
| `scripts/vps/`, `scripts/vps2012/`, `ops/vps/` | Tooling VPS Windows (PowerShell); `scripts/vps/legacy/` masih dipakai tugas recovery |
| `scripts/pc/`, `scripts/deployment/` | Environment privat PC, redeploy + `release_manifest.py` |
| `mt5/` | EA dan include MQL5 (`Experts/`, `Include/`, `Tests/`) |
| `config/` | Konfigurasi JSON (dimuat lewat nama dinamis; `config/stages/stageNN.json` dibaca per nomor) — jangan hapus walau tampak tak dirujuk |
| `protocol/` | Skema pesan biner KAT1 |
| `website/` | Situs statis publik (Cloudflare Pages); JSON di dalamnya ditulis workflow |
| `sites/runtime-monitor/`, `functions/api/`, `oauth_gateway/`, `services/` | Worker monitor runtime, API Pages, gateway OAuth, relay monitor |
| `docs/` | `architecture/` + `adr/` (kontrak desain, dilindungi CODEOWNERS), `operations/`, `research/`, `validation/` (bukti bertanggal), `reviews/` (freeze record stage 02–09), `deployment/` |
| `tests/` | `unit/` (~1.500), `static/` (113), `integration/` (~210), `replay/` dan `research/` (tidak dijalankan Body CI) |
| `archive/` | Skrip/dokumen lama tak dirujuk, disimpan utuh — lihat `archive/README.md` |
| `.github/workflows/` | 39 workflow; utama `katarina-body-ci.yml` |

## Menjalankan pengecekan (sama dengan Body CI)

```bash
pip install -r requirements-stage07.txt numpy
PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_*.py'
PYTHONPATH=src python -m unittest discover -s tests/static -p 'test_*.py'
PYTHONPATH=src python -m unittest discover -s tests/integration -p 'test_*.py'
python scripts/governance/audit_repo_hygiene.py --repo-root . --output build/repository-hygiene.json
python scripts/governance/audit_dependency_links.py --repo-root . --output build/validation/dependency-links.json
```

Hasil 21 Oktober 2026: unit 1.503 OK, static 113 OK (4 skip), integration 211 OK (3 skip),
replay 11 OK, research 5 OK, hygiene dan dependency links PASS.

## Aturan penting saat mengubah

- Jangan menghapus berkas hanya karena tidak ditemukan rujukan nama: config dimuat dinamis,
  workflow adalah entry point, website disajikan langsung, `scripts/ai/run_market_brain.py` dan
  `run_decision_brain_v3.py` sengaja jadi stub penolak (tombstone) legacy.
- Berkas yang tercatat di `ops/deployment/release-manifest.json` (372 berkas, dibuat ulang
  21 Oktober) diverifikasi saat redeploy. Setelah mengubah kode di `src/katarina`, `scripts/ai`,
  `scripts/deployment`, `scripts/memory` atau `mt5`, buat ulang dengan
  `python scripts/deployment/release_manifest.py --manifest ops/deployment/release-manifest.json --generate`
  lalu verifikasi tanpa `--generate` (harus `MATCH`).
- Arsipkan dengan `git mv <path> archive/<path>` (pertahankan struktur asal), bukan hapus.
- Jangan commit runtime state, data broker, kredensial, atau snapshot heartbeat VPS
  (`.gitignore` + `audit_repo_hygiene.py` menjaganya).
- Satu otak canonical: jangan menambah observer/worker paralel atau jalur eksekusi tersembunyi.

## Riwayat perapian

- 15 Okt: `docs/operations/REPOSITORY_CLEANUP_20261015.md` (identitas repo, snapshot VPS dihapus).
- 21 Okt (pagi): 45 skrip riset + 27 output ke `archive/`, 3 modul yatim dan 226 import tak terpakai dihapus.
- 21 Okt (lanjutan): 58 dokumen lama tak dirujuk (riset 10–13 Okt, JSON validasi 10 Okt,
  handoff/maintenance/roadmap lama) dan `select_and_validate_strategies.py` dipindah ke `archive/`;
  `CLAUDE.md` ini ditambahkan.
