# Peta dokumentasi Katarina AI — sumber tunggal

**Keputusan Owner, 29 Oktober 2026:** GitHub adalah sumber resmi kode dan dokumentasi. VPS hanya untuk testing; deployment atau migrasi VPS baru perlu persetujuan Owner. Gunakan berkas yang sudah ada, hindari duplikasi.

## Tiga jalur utama perjalanan proyek (keputusan Owner, 30 Oktober 2026)

| Kebutuhan | Satu tempat | Tidak boleh ditaruh di sini |
|---|---|---|
| **Perjalanan Katarina** — tujuan, tahap, milestone, urutan paket, dependensi, acceptance, progres gerbang | [ROADMAP.md](ROADMAP.md) | Transkrip meeting, diagnosis harian, log perubahan per commit |
| **MEETING** — ide, usulan, keberatan dan pertanyaan yang **belum diputuskan** | [ROADMAP_DISCUSSION.md](ROADMAP_DISCUSSION.md) | Antrean pengerjaan paralel, klaim perbaikan selesai |
| **HASIL PERBAIKAN** — masalah sebelum/sesudah, akar penyebab, kode yang diubah, PR/commit, CI/VPS, sisa risiko | [REPAIR_HISTORY.md](REPAIR_HISTORY.md) | Ide belum disetujui, pekerjaan yang belum dikerjakan, status heartbeat saat ini |

**Dokumen pendukung tetap dipertahankan:** [PROJECT_STATUS.md](PROJECT_STATUS.md) = **satu-satunya status operasional terakhir**; [CHANGELOG.md](../CHANGELOG.md) = ringkasan teknis perubahan **per PR/commit**; [CLAUDE.md](../CLAUDE.md) = instruksi cepat untuk pelaksana; [KATARINA_CONSTITUTION.md](../KATARINA_CONSTITUTION.md) = aturan beku. Ketiganya tidak menjadi arsip perbaikan kedua.

## Urutan baca hemat token

1. [CLAUDE.md](../CLAUDE.md) — orientasi singkat dan batas kewenangan.
2. [PROJECT_STATUS.md](PROJECT_STATUS.md) — kondisi operasional terbaru, bukan sejarah.
3. [ROADMAP.md](ROADMAP.md) — tahap perjalanan, paket prioritas dan acceptance yang sudah disetujui.
4. [ROADMAP_DISCUSSION.md](ROADMAP_DISCUSSION.md) — baca hanya agenda meeting yang belum final.
5. [REPAIR_HISTORY.md](REPAIR_HISTORY.md) — riwayat perbaikan dan bukti sebelum/sesudah.
6. [CHANGELOG.md](../CHANGELOG.md) — ringkasan perubahan teknis bila perlu detail commit.
7. [KATARINA_CONSTITUTION.md](../KATARINA_CONSTITUTION.md) — aturan tertinggi, FROZEN.

**Alur tunggal:** usulan belum final → **MEETING** → keputusan berwenang → **ROADMAP** (target/paket) → PR + CI → **REPAIR_HISTORY** (bila benar ada perbaikan dengan bukti) dan **CHANGELOG** (ringkasan teknis) → **PROJECT_STATUS** (snapshot kondisi saat ini). Tidak ada DONE tanpa bukti. Keputusan tidak diubah lewat meeting saja; aturan beku tetap membutuhkan persetujuan Owner.

**Master Blueprint:** belum dibuat. Jangan menduplikasi persyaratan, arsitektur, atau acceptance yang sudah tercatat. Satu dokumen blueprint baru hanya boleh dibuat setelah pemetaan isi dan review Owner.

## Peta berkas teknis yang dipertahankan

- `architecture/`, `adr/`: kontrak dan keputusan arsitektur.
- `research/`, `validation/`, `reviews/`: protokol, hasil dan bukti pengujian.
- `governance/`: gerbang promosi dan governance teknis.
- `operations/`, `deployment/`: panduan operasional dan rencana deployment, **bukan izin deploy**.
- [CLEANUP_PLAN.md](maintenance/CLEANUP_PLAN.md), [RUNTIME_MODULE_MAP.md](maintenance/RUNTIME_MODULE_MAP.md): peta modul dan prosedur perapian.

Jangan memindahkan atau menghapus berkas sebelum memeriksa referensi kode, CI, dan bukti validasi. Jangan menaruh dokumentasi induk di VPS.
