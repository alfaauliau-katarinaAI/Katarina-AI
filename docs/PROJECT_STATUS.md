# Status Katarina AI — snapshot operasional

> **Perapian codebase 4 November 2026 (Claude, mandat Owner #278):** status **`CODEBASE_CLEAN_BUT_STAGE_GATE_BLOCKED`**. Codebase rapi dan seluruh gate CI/manifest/promotion lulus; tahap berikutnya tertahan bukti eksternal (Tahap 0 10 hari, jam bar historis, probe sesi MT5). Rincian: [RH-012](REPAIR_HISTORY.md) dan [ledger perapian](maintenance/CODEBASE_CLEANUP_20261103.md).

> **Deploy 3 November 2026 15:18 UTC (Claude, izin Owner):** VPS `C:\Katarina\code` = `main` **`fd6cff16`** (WP13 jam live NTP + tick bergerak, WP4/WP8b/WP14, K-04). Bukti, backup dan rollback: [RH-011](REPAIR_HISTORY.md). Laporan K-01..K-07: [Issue #251](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/251).

> **Instruksi eksekusi Claude (3 November 2026, belum otomatis dijalankan):** [tutup kendala Katarina AI v0.1, langkah dan acceptance K-01 s.d. K-07](maintenance/CLAUDE_BLOCKER_CLOSURE_20261103.md). Ini adalah daftar tugas *perbaikan yang sudah ada*, bukan fitur/roadmap baru atau izin deployment; Claude harus memberikan ACK nyata dan bukti di [Issue #251](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/251).

> **Pembaruan bukti 3 November 2026:** [konsolidasi audit VPS Yura](maintenance/YURA_AUDIT_CONSOLIDATED_20261103.md) memuat keadaan observer, temuan Stage 0, penelusuran quote, PR/CI dan pembagian arsip. Angka pada tabel di bawah tetap **snapshot 30 Oktober**, bukan status terbaru. Untuk keputusan/antrean tetap ikuti [ROADMAP](ROADMAP.md); jangan gunakan laporan audit sebagai izin deployment atau trading.

**Diperiksa:** 30 Oktober 2026 pukul **06:08 WIB** untuk observer VPS (Claude, baca-saja: Running/WAITING, 339 siklus, 333 sukses, 0 gagal beruntun, 0 order, 5 simbol, checkout `64497b5`, `broker-clock-evidence.json` tidak ada); [laporan perapian PR Claude](maintenance/CLAUDE_PR_CLEANUP_REPORT_20261030.md); PR GitHub dan review terkini diperiksa pada sesi sama. **Audit kelemahan dan instruksi Claude:** [laporan lengkap](maintenance/KATARINA_WEAKNESSES_CLAUDE_REVIEW_20261030.md). Audit jam rinci: [WP13 clock handoff](maintenance/WP13_CLOCK_CLAUDE_HANDOFF_20261030.md). Angka VPS adalah snapshot, bukan janji kondisi saat file dibaca nanti. Urutan kerja/acceptance ada di [ROADMAP](ROADMAP.md); perbaikan nyata di [REPAIR_HISTORY](REPAIR_HISTORY.md); keputusan terbuka di [MEETING](ROADMAP_DISCUSSION.md).

## Ringkasan terverifikasi

| Aspek | Kondisi saat diperiksa | Batas bukti / tindak lanjut |
|---|---|---|
| Mode & kewenangan | **Research-only, LIVE OFF, Level 0**; observer read-only, tanpa izin order nyata | Persetujuan Owner dan gerbang promosi tetap wajib; tidak ada aktivasi DEMO/LIVE |
| Observer di VPS | Task `Katarina-Readonly-Observer` **Running** sejak 3 Nov 15:18:12 UTC pada `fd6cff16`, status **WAITING**, 5 simbol, 0 order; siklus pertama `LIVE_FEED_CLOCK_VERIFIED` (NTP `time.windows.com` stratum 5 + 3 tick bergerak), `research_candidates` tercatat | Trigger masih **LogonTrigger/Interactive**: tidak jalan setelah reboot tanpa login (WP6) |
| Perbaikan lock | Sumber `PermissionError` tahap PUBLISH terbukti terkait handle `latest.json` yang dipegang child Node.js Desktop Commander; DC dipulihkan, patch retry atomik dan tes masuk `main` | Detail dan bukti lengkap: [RH-001](REPAIR_HISTORY.md#rh-001--file-snapshot-observer-terkunci-oleh-desktop-commander); pantau bila kambuh |
| Deployment kode VPS | **`fd6cff16`**, manifest **MATCH 317/317**; backup pra-deploy `C:\Katarina\backups\20261103-pre-fd6cff16` (`integrity_check=ok`) | Rollback: checkout `64497b5` + restore DB (RH-011). `main` sesudahnya: #273, #272 (dokumen/diagnostik, tidak memengaruhi observer) |
| Tahap 0 — 10 hari bursa | **BELUM LULUS**. Sejak 28 Okt 16:57 UTC (3 Nov sebelum deploy): streak 2/10 hari, sukses 96,96% (< 98%), recovery 1/3, rekonsiliasi 11.314/11.314, 0 order; `clock_shift_stable` **NOT_MET** setelah K-04 (shift palsu −1/−8 akhir pekan 30–31 Okt) | Observasi berlanjut dengan jam WP13; data lama tidak diubah. Keputusan cutoff baru = Owner/manager |
| Jam broker MT5 | **WP13 DEPLOYED** 3 Nov: snapshot hanya dengan NTP host tepercaya (umur ≤ 14.400 s) + ≥ 3 tick bergerak; setelah Jumat 20:00 UTC `FX_MARKET_CLOSED`. NTP `MaxPollInterval` 13 | Jam bar historis tetap BLOCKED (#255); probe sesi MT5 belum dijalankan |
| Reboot & perangkat | VPS Windows Server 2012 R2 RAM ±2 GB; observer task menggunakan akun Administrator dengan **Interactive Logon** | Auto-start setelah reboot tanpa login belum terbukti; WP6 harus diuji aman tanpa mengorbankan evidence 10 hari |
| Codebase | **`CODEBASE_CLEAN_BUT_STAGE_GATE_BLOCKED`** (4 Nov 2026, `main` `e186d3cc`+E1): perapian B1/C1/D1 merged — jalur MT5 lama dihapus, satu kalender DST (`domain/market_calendar.py`), tes Windows flaky diperbaiki, indeks reason code ([REASON_CODE_INDEX](maintenance/REASON_CODE_INDEX.md)); unit 1.468 / static 80 / integration 222 OK, manifest MATCH, promotion gate PASS | Bukti: [RH-012](REPAIR_HISTORY.md), ledger [CODEBASE_CLEANUP_20261103](maintenance/CODEBASE_CLEANUP_20261103.md). Perubahan C1 belum dideploy (identik secara perilaku; deploy perlu izin Owner) |
| Antrean PR aktif | Hanya [#278](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/278) (dokumen mandat Owner). WP13 #233, integrasi #265 dan K-01..K-07 sudah **MERGED**; Jules tidak sedang mengerjakan branch aktif | 10 branch milik PR tertutup belum dihapus (proxy Claude menolak hapus ref; daftar SHA di ledger E1) |
| Validasi strategi | **Belum ada edge/profitabilitas konsisten yang terbukti**; audit historis 13 Okt: profit factor kandidat 0,36 dan 77% kandidat rugi setelah biaya | Lulus source tests ≠ edge; WP10b #225 code merged, tetapi Tahap 1 masih perlu bukti strategi independen sebelum promosi |
| Keputusan trading | Snapshot audit sebelumnya mencatat kartu **100% WAIT** dengan pemblokir fail-closed; WP9a/WP9b sudah menyediakan alat diagnosis bayangan | Menunggu ≥3 hari bursa `decision_shadow` dan hasil peta blocker; perubahan mode aktif hanya setelah keputusan Owner pada agenda D2 |
| Risiko | Risk Governor independen, batas drawdown harian 35% sesuai keputusan Owner; repo masih publik | Batas 35% bukan klaim aman untuk live; tidak boleh dilonggarkan. Repo private/pemisahan website tetap keputusan Owner |

## Blocker yang belum selesai

**P0:** Tahap 0 **belum lulus** (10 hari bursa, sukses ≥ 98%, 3 recovery, 0 order); data sejak 28 Okt `clock_shift_stable NOT_MET` karena shift palsu akhir pekan 30 Okt–1 Nov (terbukti, RH-011). Ini gate data/waktu, bukan bug codebase.
**P1:** Bukti jam bar historis M5 butuh host riset MT5 terpisah (#255; RAM VPS ±615 MB). Probe sesi MT5 belum dijalankan (perlu GUI terminal oleh Owner). WP6 auto-start tanpa login belum diuji.
**P2:** 62 reason code P0 belum diuji secara literal ([indeks](maintenance/REASON_CODE_INDEX.md)); cleanup worktree/folder lama VPS (inventaris di ledger E1); validasi edge menurut gerbang Roadmap. **Prioritas/antrean tunggal hanya [ROADMAP.md](ROADMAP.md)**.

## Pemeriksaan dan pelaporan

- Setelah perbaikan diverifikasi, catat bukti sebelum/sesudah di [REPAIR_HISTORY.md](REPAIR_HISTORY.md), ringkasan teknis per PR di [CHANGELOG.md](../CHANGELOG.md).
- Setelah keputusan pada [MEETING](ROADMAP_DISCUSSION.md) disahkan, pindahkan hasilnya ke roadmap dan tutup topik rapat.
- Observer tetap **LIVE OFF**, satu worker resmi, tanpa menghapus ledger/gap atau mengganti data forward dengan backfill.
- Semua angka di sini adalah **snapshot historis pada waktu yang tertulis**, bukan janji monitor terus-menerus.
