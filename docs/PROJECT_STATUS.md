# Status Katarina AI — snapshot operasional

**Diperiksa:** 30 Oktober 2026 sekitar **00:28 WIB**. Ini **satu-satunya sumber kondisi aktual** pada waktu pemeriksaan, bukan jurnal perubahan atau dokumen prioritas. Urutan tugas dan acceptance hanya ada di [ROADMAP.md](ROADMAP.md); bukti perbaikan yang sudah terlaksana di [REPAIR_HISTORY.md](REPAIR_HISTORY.md); pembahasan yang belum diputuskan di [MEETING](ROADMAP_DISCUSSION.md).

## Ringkasan terverifikasi

| Aspek | Kondisi saat diperiksa | Batas bukti / tindak lanjut |
|---|---|---|
| Mode & kewenangan | **Research-only, LIVE OFF, Level 0**; observer read-only, tanpa izin order nyata | Persetujuan Owner dan gerbang promosi tetap wajib; tidak ada aktivasi DEMO/LIVE |
| Observer di VPS | Task `Katarina-Readonly-Observer` **Running**; status `WAITING`; **27/27 siklus sukses** sejak restart resmi sekitar 29 Okt 23:59 WIB; lima simbol menerima data; `consecutive_failures=0`, `orders_submitted=0`, heartbeat **29 Okt 17:27:44 UTC** | **Lolos smoke test awal saja**, bukan bukti stabilitas 10 hari bursa atau status real-time selamanya. Jangan membaca `latest.json` dengan handle yang ditahan lama. |
| Perbaikan lock | Sumber `PermissionError` tahap PUBLISH terbukti terkait handle `latest.json` yang dipegang child Node.js Desktop Commander; DC dipulihkan, patch retry atomik dan tes masuk `main` | Detail dan bukti lengkap: [RH-001](REPAIR_HISTORY.md#rh-001--file-snapshot-observer-terkunci-oleh-desktop-commander); pantau bila kambuh |
| Deployment kode VPS | Checkout `C:\Katarina\code` `main` **`64497b5`**, manifest `MATCH 304/304` saat deploy sebelumnya; `test_snapshot_io.py` **5/5 PASS** | `main` GitHub sudah berkembang dengan perubahan **dokumentasi saja** setelah commit tersebut; jangan mengartikan beda SHA dokumen sebagai perubahan runtime |
| Tahap 0 — 10 hari bursa | **BELUM LULUS**. Data forward harga yang sah menurut WP12 dimulai **28 Okt 16:57 UTC**; pengamatan perlu hari bursa berurutan, kelengkapan simbol, 0 order, audit gap dan rekonsiliasi | Laporan harian terakhir yang diperiksa dibuat **29 Okt 07:30 WIB**, belum difilter `--since` WP12: `cycle_success_rate` 97,0111% vs 98% **NOT_MET**; 10 hari berurutan **NOT_MET**; tick/snapshot reconciliation **NOT_MET**. Angka lama tidak boleh dipakai sebagai kelulusan periode setelah WP12. |
| Jam broker MT5 | **WP12 diterapkan** (tick/jendela broker ke UTC), tetapi **WP13 belum selesai** | [PR #219](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/219) OPEN, `mergeable=false`; penolakan quote basi, offset independen, DST, pindah broker/VPS dan audit `--since` belum ditutup dengan bukti deployment |
| Reboot & perangkat | VPS Windows Server 2012 R2 RAM ±2 GB; observer task menggunakan akun Administrator dengan **Interactive Logon** | Auto-start setelah reboot tanpa login belum terbukti; WP6 harus diuji aman tanpa mengorbankan evidence 10 hari |
| Coding Google | GitHub [Issue #220](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/220) bertanda `jules`; **0 komentar Jules, belum ada PR yang terverifikasi** | Google Jules **belum dianggap mulai bekerja**. Owner perlu login/otorisasi Jules–GitHub untuk repo; satu paket WP10b, review Claude; Jules tidak diberi akses VPS |
| Antrean PR aktif | [#219 WP13](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/219) konflik; [#218 agentic docs](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/218) konflik; [#216 rapat docs](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/216) draft | Tumpang tindih dengan dokumen yang sudah menjadi kanonis: selaraskan atau tutup PR duplikat setelah review, jangan kehilangan keputusan |
| Validasi strategi | **Belum ada edge/profitabilitas konsisten yang terbukti**; audit historis 13 Okt: profit factor kandidat 0,36 dan 77% kandidat rugi setelah biaya | Lulus source tests ≠ edge; WP10b biaya dan Tahap 1 masih perlu bukti nyata sebelum promosi |
| Keputusan trading | Snapshot audit sebelumnya mencatat kartu **100% WAIT** dengan pemblokir fail-closed; WP9a/WP9b sudah menyediakan alat diagnosis bayangan | Menunggu ≥3 hari bursa `decision_shadow` dan hasil peta blocker; perubahan mode aktif hanya setelah keputusan Owner pada agenda D2 |
| Risiko | Risk Governor independen, batas drawdown harian 35% sesuai keputusan Owner; repo masih publik | Batas 35% bukan klaim aman untuk live; tidak boleh dilonggarkan. Repo private/pemisahan website tetap keputusan Owner |

## Blocker yang belum selesai

**P0:** Bukti kelulusan Tahap 0 (10 hari bursa valid, audit gap/tick, recovery) dan WP13 waktu MT5 yang masih konflik.  
**P1:** Pembuktian jam historis WP8c, aktivasi akses Google Jules untuk WP10b, tahan restart/reboot WP6, dan konsolidasi PR dokumentasi yang bertumpuk.  
**P2:** Profil spread WP10a, jurnal kandidat WP4, auditor data WP14 setelah prasyarat, serta pembuktian edge/agentic. **Urutan dan penugasan kanonis hanya di [ROADMAP.md](ROADMAP.md) — jangan jadikan bagian ini antrean kedua.**

## Pemeriksaan dan pelaporan

- Setelah perbaikan diverifikasi, catat bukti sebelum/sesudah di [REPAIR_HISTORY.md](REPAIR_HISTORY.md), ringkasan teknis per PR di [CHANGELOG.md](../CHANGELOG.md).
- Setelah keputusan pada [MEETING](ROADMAP_DISCUSSION.md) disahkan, pindahkan hasilnya ke roadmap dan tutup topik rapat.
- Observer tetap **LIVE OFF**, satu worker resmi, tanpa menghapus ledger/gap atau mengganti data forward dengan backfill.
- Semua angka di sini adalah **snapshot historis pada waktu yang tertulis**, bukan janji monitor terus-menerus.
