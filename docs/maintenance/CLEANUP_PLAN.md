# Aturan dan status perapian Katarina AI

Diperbarui 22 Oktober 2026. Rencana 8 tahap (21 Okt) sudah dijalankan, lalu Owner memutuskan
perampingan penuh pada 22 Okt: **yang tidak dipakai dihapus langsung, bukan diarsipkan.**
Riwayat setiap berkas tetap ada di Git.

## Aturan untuk setiap perapian

Tempel blok ini di awal sesi yang akan merapikan repo:

```
Baca CLAUDE.md dulu. Aturan perapian:
- Tanpa perubahan perilaku. Jangan mengubah logika trading, Risk Governor
  (src/katarina/engines/risk.py), config risk, EA MT5, atau flag live_execution.
- Yang terbukti tidak dipakai DIHAPUS langsung lewat PR. Jangan membuat folder
  archive/, branch arsip, atau tag arsip.
- Satu kelompok perubahan = satu branch = satu PR. Body CI wajib hijau sebelum merge.
- Sebelum menghapus, cek rujukan (nama berkas DAN nama dasar tanpa ekstensi) di
  src/, scripts/, tests/, config/, .github/workflows/, docs/, website/,
  katarina_pc.py, dan docs/maintenance/RUNTIME_MODULE_MAP.md.
- config/stages/stageNN.json dimuat per nomor: jangan dihapus. Config lain boleh
  dihapus hanya jika tidak ada kode yang memuat namanya.
- Jaga identitas Katarina (lihat daftar di bawah) walau tampak hanya dipakai tes.
- Setelah mengubah src/katarina, scripts/ai, scripts/deployment, scripts/memory
  atau mt5: buat ulang release manifest (harus MATCH) dan peta modul runtime.
- Perbarui CLAUDE.md dan CHANGELOG.md di setiap PR.
```

## Identitas Katarina yang dipertahankan

- `KATARINA_CONSTITUTION.md`, README, `docs/PROJECT_STATUS.md`.
- Otak canonical `UnifiedKatarinaBrain`, observer canonical, demo forward, buku shadow prospektif.
- Risk Governor dan config risiko (stop DD harian 35%, dijaga `test_daily_drawdown_sync.py`).
- Modul tahap 11–40 (`body/`, `engines/`, `governance/`, perception dasar, `research/`), walau sebagian
  hanya dipakai tes.
- Skema pesan `protocol/` (kontrak validation dan health engine), dokumen `architecture/` dan `adr/`.
- Paket kosong `domain`, `entrypoints`, `ports` (kontrak `config/repository_architecture.json`).
- Website publik, EA MT5 status dashboard dan bridge Stage 06.
- Tombstone `scripts/ai/run_market_brain.py` dan `run_decision_brain_v3.py`.

## Status

| Pekerjaan | Status |
|---|---|
| 1. Peta modul runtime | Selesai — `docs/maintenance/RUNTIME_MODULE_MAP.md` (dibuat ulang setiap perapian) |
| 2. Pensiunkan otak lama | Selesai — hanya `UnifiedKatarinaBrain` |
| 3. Subpaket `intelligence/` | Selesai — 77 modul dalam 8 subpaket |
| 4. Nama fungsi `body/stageNN` | Selesai — nomor→modul di `docs/maintenance/BODY_STAGE_MAP.md` |
| 5. Sederhanakan workflow | Selesai — 11 workflow (dari 39) |
| 6. Logika script ke `src` | Selesai |
| 7. Website ke repo sendiri | **Menunggu Owner** — `docs/deployment/STANDALONE_WEBSITE_EXTRACTION.md` |
| 8. Satu sumber status | Selesai — `docs/PROJECT_STATUS.md` |
| Perampingan A–E (22 Okt) | Selesai — tooling VPS lama, 116 dokumen bertanggal, 62 skrip riset, transport KAT1/ZMQ, sisa modul/skrip/workflow/config; ~1.211 → ~795 berkas |

## Sisa yang diketahui

- 20 tag `archive/2026-10-11/…` di GitHub (arsip lama, bertentangan dengan aturan hapus-langsung).
- `scripts/ai/run_readonly_decisions.py` masih menulis ke path VPS lama `C:\KatarinaDev\artifacts\decision-observer`.
- VPS: 15 folder lama terkunci di `C:\`, installer dan Python 3.8/3.13 yang tidak dipakai.

## Setelah perapian

Arahkan tenaga ke hal yang menentukan apakah bot bisa trading otomatis: bukti edge dari data forward
observer, uji out-of-sample, dan biaya broker riil. Lihat `docs/PROJECT_STATUS.md`.
