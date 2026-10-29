# Peta dokumentasi Katarina AI — sumber tunggal

**Keputusan Owner, 29 Oktober 2026:** GitHub adalah sumber resmi kode dan dokumentasi. VPS hanya untuk testing; deployment atau migrasi VPS baru perlu persetujuan Owner. Gunakan berkas yang sudah ada, hindari duplikasi.

## Urutan baca hemat token

1. [CLAUDE.md](../CLAUDE.md) — orientasi singkat dan aturan pelaksana.
2. [PROJECT_STATUS.md](PROJECT_STATUS.md) — **satu-satunya status operasional**; baca bagian relevan.
3. [ROADMAP.md](ROADMAP.md) — **satu-satunya antrean pekerjaan, prioritas dan acceptance**; baca paket aktif.
4. [ROADMAP_DISCUSSION.md](ROADMAP_DISCUSSION.md) — rapat, opsi, keputusan tertunda; **bukan daftar kerja kedua**.
5. [CHANGELOG.md](../CHANGELOG.md) — perubahan terverifikasi, dengan bukti commit/PR.
6. [KATARINA_CONSTITUTION.md](../KATARINA_CONSTITUTION.md) — aturan tertinggi, FROZEN.

## Batas fungsi dokumen

| Informasi | Dokumen kanonis |
|---|---|
| Misi dan prinsip risiko beku | `KATARINA_CONSTITUTION.md` |
| Spesifikasi yang telah disetujui | Bagian tetap `ROADMAP.md`, `architecture/`, `adr/` |
| Pekerjaan, prioritas, dependensi, acceptance | `ROADMAP.md` |
| Agenda rapat dan alternatif belum final | `ROADMAP_DISCUSSION.md` |
| Status aktual, blocker dan langkah berikutnya | `PROJECT_STATUS.md` |
| Riwayat perubahan kecil, alasan, file, tes, rollback, commit | `CHANGELOG.md` dan riwayat PR |

**Alur:** rapat di ROADMAP_DISCUSSION → persetujuan Owner untuk perubahan besar → keputusan final ditulis sekali di dokumen kanonis → implementasi melalui PR dan CI → bukti di CHANGELOG, status singkat di PROJECT_STATUS. Tidak ada DONE tanpa bukti. Perubahan kecil boleh dilakukan tanpa persetujuan baru hanya bila tidak mengubah aturan yang dibekukan dan wajib tercatat.

**Master Blueprint:** belum dibuat. Jangan menduplikasi persyaratan, arsitektur, atau acceptance yang sudah tercatat. Satu dokumen blueprint baru hanya boleh dibuat setelah pemetaan isi dan review Owner.

## Peta berkas teknis yang dipertahankan

- `architecture/`, `adr/`: kontrak dan keputusan arsitektur.
- `research/`, `validation/`, `reviews/`: protokol, hasil dan bukti pengujian.
- `governance/`: gerbang promosi dan governance teknis.
- `operations/`, `deployment/`: panduan operasional dan rencana deployment, **bukan izin deploy**.
- [CLEANUP_PLAN.md](maintenance/CLEANUP_PLAN.md), [RUNTIME_MODULE_MAP.md](maintenance/RUNTIME_MODULE_MAP.md): peta modul dan prosedur perapian.

Jangan memindahkan atau menghapus berkas sebelum memeriksa referensi kode, CI, dan bukti validasi. Jangan menaruh dokumentasi induk di VPS.
