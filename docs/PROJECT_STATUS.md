# Status Katarina AI

Satu-satunya sumber status proyek. Diperbarui **29 Oktober 2026**. Rincian per perubahan ada di
[CHANGELOG](../CHANGELOG.md); hasil CI terbaru di
[GitHub Actions](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions).

## Ringkasan

| Bagian | Keadaan sekarang | Batas / catatan |
|---|---|---|
| Mode | Research-only, **LIVE OFF**. Tidak ada jalur kirim order ke akun riil | DEMO forward ada di kode, tetapi **tidak berjalan**; hanya observer read-only (lihat VPS) |
| Otak | Satu otak canonical `UnifiedKatarinaBrain` (`intelligence/cognition/unified_brain.py`): observer → market decision (regime, playbook, setup) → kartu BUY/SELL/WAIT → memori, laporan, Risk Governor | BUY/SELL hanya jika skor bukti ≥ 0,62 dan RR memenuhi. Di VPS **100% WAIT**: 7 pemblokir permanen (fail-closed `system_healthy=False`, riwayat forward kosong, berita segar kosong = blackout, entry teknis tidak menyala) — dibongkar lewat WP9 (roadmap Lampiran A; prioritas Owner 23 Okt) |
| Risiko | Risk Governor independen (`engines/risk.py`, `config/risk_governor_v2.json`): 1% default dan maks 5% per entry, 8% total risiko terbuka, **stop entry baru di drawdown harian 35%**, drawdown total 35%. Risiko adaptif dipangkas setengah mulai DD harian 5% / total 10% | Batas 35% disinkronkan di config, Risk Governor, tracker DD harian, gerbang risiko riset, dan dokumen; dijaga `tests/unit/engines/test_daily_drawdown_sync.py` |
| Riset / edge | **Edge belum terbukti.** Audit 13 Okt (17 instrumen): profit factor kandidat 0,36, 77% kandidat rugi setelah biaya. Backtest 2025–2026 (7 instrumen): tidak ada keluarga playbook yang ekspektansinya positif di kedua tahun | Biaya spread ≈ 0,24R vs gerak menguntungkan median ≈ 0,23R. Laporan aslinya ada di riwayat Git (dihapus saat perampingan 22 Okt) |
| VPS | Windows Server 2012 R2, RAM 2 GB, diakses lewat Desktop Commander. Python 3.12.10 di `C:\Katarina\python312`, checkout `main` di `C:\Katarina\code`; `setup`, `doctor`, uji sintetis lulus. MT5 build 6274 dipasang ulang 22 Okt | Observer read-only **berjalan** sejak 22 Okt 04:24 UTC (tugas `Katarina-Readonly-Observer`, akun demo, Algo Trading OFF, siklus 60 detik). Simbol: 5 (EURUSD, GBPUSD, USDJPY, XAUUSD, NAS100). Kode VPS = `main` `18e2515` (WP12 jam tick → UTC, WP9b, WP8a) sejak **28 Okt 16:57 UTC**, manifest MATCH; quote kini = harga sekarang. Observer resmi sempat dihentikan pelaksana 27 Okt 19:35 – 28 Okt 16:57 UTC (diganti worker uji dari kode belum di-merge; dihapus, datanya disimpan terpisah). NTP host aktif (T13); laporan harian Tahap 0 07:30 WIB. Tugas hanya jalan saat Administrator login (auto-start pasca-restart masih WP6) |
| Repository | `main` dilindungi (PR + Body CI wajib). Perampingan 22 Okt: ~1.211 → ~795 berkas, 11 workflow; tooling VPS lama, dokumen bertanggal, skrip riset sekali pakai, dan transport KAT1/ZMQ dipensiunkan | Repo masih **publik**; website masih di repo ini |
| Pengujian | Body CI + suite penuh Windows lulus (28 Okt, setelah WP12/WP9b/WP8a) | Lulus tes sumber ≠ profitabilitas atau kesiapan live |

## WP13 — waktu broker MT5 (catatan 29 Oktober 2026)

- **Status kode GitHub:** [PR #219](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/219) pada
  branch `chatgpt/wp13-clock-since-20261029` masih **OPEN / BELUM MERGED** saat diperiksa. Jangan menyamakan
  pengujian lokal atau kabar penerapan dengan perubahan yang sudah masuk `main`.
- **Perbaikan dalam PR:** validasi offset berdasarkan bukti independen yang terikat server broker dan masa berlaku,
  penolakan quote basi/ambiguitas waktu, serta pemeriksaan Tahap 0 dengan opsi `--since`. Detail perubahan teknis
  ada di deskripsi PR dan [CHANGELOG](../CHANGELOG.md), bukan disalin ke roadmap.
- **Verifikasi belum ditutup:** pastikan seluruh CI wajib lulus dan cek MT5 read-only saat pasar aktif, market close,
  quote serentak basi, pergantian DST, pindah broker serta pindah VPS/deployment. Pastikan tidak ada order terkirim;
  jika bukti jam tidak sah, observer harus menolak data ambigu (fail-closed) tanpa mengarang offset.
- **Status VPS:** laporan percakapan menyebut pembaruan sudah diterapkan tanpa mematikan observer, **tetapi belum
  diverifikasi secara independen terhadap SHA/manifest dan output MT5 nyata** pada pemeriksaan dokumentasi ini.
  Oleh sebab itu WP13 **belum boleh dinyatakan tuntas secara operasional**. LIVE OFF; Tahap 0 belum lulus.


## Audit lintas sistem — 29 Oktober 2026 (untuk Claude)

**Ruang lingkup dan batas bukti:** telaah roadmap, status proyek, PR #218/#219, dan pemeriksaan read-only VPS pada 29 Okt. Ini **audit status dan risiko berbasis sampel**, bukan audit setiap baris kode, setiap pengujian, atau bukti kelulusan produksi. Temuan lama di bawah berasal dari dokumen proyek; temuan baru diberi tanggal. Jangan menyimpulkan sebuah masalah telah ditutup hanya dari adanya modul atau tes sintetis.

| Prioritas | Temuan / kelemahan | Bukti dan status | Aksi Claude / syarat penutupan |
|---|---|---|---|
| P0 | Observer forward rentan berhenti | Pada 29 Okt 09:14 UTC status `BLOCKED`, `PermissionError` di `pathlib.py:1376`, siklus 906 / sukses 901, `orders_submitted=0`. Snapshot `latest.tmp` tertinggal. Task kemudian dijalankan ulang 29 Okt 16:29 UTC dan melaporkan `OBSERVING`, tetapi saat dicek baru 0 siklus; **pemulihan berkelanjutan belum terbukti** | Identifikasi operasi dan path yang gagal, kemungkinan file-lock/atomic replace/ACL/antivirus; tambahkan regression test dan retry aman di repo, satu PR; verifikasi > beberapa siklus, restart, ledger dan heartbeat tanpa gap tersembunyi. Jangan menghapus data bukti. |
| P0 | Kebenaran waktu MT5 belum portabel dan tervalidasi | WP12 di VPS commit `18e2515`; PR #219 WP13 masih OPEN dan `mergeable=false` pada pemeriksaan 29 Okt; VPS belum memakai WP13 | Selesaikan konflik PR #219, tes CI, verifikasi offset berbasis bukti broker, quote stale, DST, akhir pekan, pindah broker/VPS; deployment **hanya untuk pengujian** sesudah merge dan persetujuan alur; catat SHA serta hasil nyata. |
| P0 | Belum ada alpha positif yang dapat direproduksi | Audit lama 13 Okt: PF kandidat 0,36; 77% kandidat rugi setelah biaya; backtest 2025–2026 tidak konsisten lintas tahun | Jangan promosikan strategi; validasi biaya penuh, data development/holdout, PF bersih dan stabilitas out-of-sample sesuai roadmap. |
| P1 | Tahap 0 belum memenuhi kelulusan 10 hari bursa | Celah data historis dan downtime 29 Okt; task pernah berhenti. Restart **bukan** bukti sepuluh hari | Hitung hanya hari bursa dengan data valid dari ledger, laporkan PASS/BLOCKED/NO_DATA per hari/simbol; gap tidak diisi backfill sebagai forward; ulang hari yang tidak memenuhi syarat sesuai aturan roadmap. |
| P1 | Jalur keputusan belum menghasilkan bukti BUY/SELL yang layak | Status proyek: 100% WAIT; beberapa blocker permanen; WP9 masih bagian perbaikan | Uji ladder blocker dengan data yang valid; pisahkan WAIT yang benar (fail-closed) dari bug logika; jangan melonggarkan gate tanpa bukti dan persetujuan. |
| P1 | Biaya trading dan kesiapan DEMO belum tervalidasi nyata | WP10b swap/sensitivitas biaya belum selesai; DemoRiskOverlay masih sintetis, belum worker aktif | WP10b melalui issue #220/Jules bila terotorisasi; Claude review PR, cek swap/triple rollover dan tes biaya; verifikasi komisi/slippage broker sebelum DEMO. |
| P1 | Ketahanan VPS dan portability belum tuntas | Windows Server 2012 R2 RAM 2 GB; task observer hanya saat Administrator login; downtime dan PermissionError tercatat | Uji startup pasca-reboot, privilege minimum, recovery crash, kapasitas disk/RAM, perbedaan broker/host; jangan jadikan VPS lokasi pengembangan atau penyimpanan sumber kode utama. |
| P1 | Risiko operasional dan eksposur repository | Repo masih publik; website dan kode dalam repo sama. Batas DD harian 35% adalah keputusan Owner, bukan bukti aman live | Audit rahasia/izin/repo exposure tanpa menampilkan kredensial; pertahankan LIVE OFF; evaluasi risiko sebelum izin akun riil (keputusan Owner). |
| P2 | Koordinasi agent/PR berpotensi tumpang tindih | PR #218 agentic docs OPEN, #219 clock OPEN, #216 draft lama (audit sebelumnya); issue #220 berlabel Jules, belum ada bukti agen mulai | Satu paket satu PR; verifikasi assignment Jules, bandingkan #216/#218 sebelum merge, perbarui status hanya dari CI/merge dan bukti nyata. |
| P2 | Riset agentic masih berupa kemampuan, bukan otonomi terbukti | Roadmap Tahap 4–5 belum memenuhi syarat; modul discovery/research sudah ada namun promosi tetap terkunci | Audit koneksi modul dan trace keputusan secara read-only; uji hipotesis, reproduksibilitas, anti-leakage, batas kewenangan; jangan aktifkan self-modification trading. |

**Urutan eksekusi:** (1) stabilkan observer + bukti siklus sukses, (2) selesaikan WP13, (3) audit Tahap 0 per hari/simbol, (4) WP10b/biaya dan blocker WAIT, (5) kesiapan DEMO/agentic. Pekerjaan coding di GitHub, VPS hanya pengujian. Tidak membuat dokumen/roadmap baru. Tidak ada perubahan LIVE atau Risk Governor.

**Catatan integritas:** Bagian ringkasan di atas adalah snapshot historis, bukan klaim keadaan observer saat ini. Setelah restart 29 Okt 16:29 UTC, status terakhir yang terbukti adalah `OBSERVING` dengan **0 siklus selesai**, sehingga keberlanjutan belum dikonfirmasi. Periksa ulang sebelum mengubah status menjadi sehat. PR ini belum masuk `main`; laporan ini hanya tersedia di branch PR #219 sampai merge.

## Pekerjaan berikutnya

Pengembangan mengikuti **[Roadmap berbasis bukti](ROADMAP.md)** (ditetapkan Owner 22 Okt 2026): validasi adalah
hakim tertinggi, dan kewenangan Katarina bertambah hanya berdasarkan bukti.

1. **Tahap 0 — Observer & data** (sedang dikerjakan): alat repo selesai 22 Okt (ledger snapshot per siklus,
   pengunduh tick broker per hari, `scripts/ai/check_stage0_health.py`); observer VPS aktif sejak 22 Okt 04:24 UTC
   dengan 3 simbol, 5 simbol sejak 23 Okt 00:16 UTC; uji putus-sambung 3× lulus 22 Okt. Jam tick MT5 = jam server
   (T11) diperbaiki WP12, diterapkan **28 Okt 16:57 UTC**: 10 hari bursa berturut-turut dihitung sejak itu (paling cepat
   ±11 Nov). WP13 (T12 dan `--since`) dalam PR #219; status operasional tetap menunggu bukti CI dan pasar normal.
2. **Tahap 1 — Validasi ilmiah:** alat dan protokol selesai 22 Okt (`katarina.research.validation`,
   [protokol](research/VALIDATION_PROTOCOL.md)); kriterianya dibuktikan tes. Dipakai untuk semua strategi berikutnya.
3. Tahap 2–5 (market intelligence, risk & execution, strategi adaptif, kalibrasi & riset mandiri) berurutan,
   masing-masing dengan kriteria kelulusan di roadmap.
   **Persiapan Tahap 2:** alat eksperimen filter tersedia di `katarina.research.market_intelligence` dan
   perintah `validate_strategy.py market-filter`; membandingkan biaya/MFE dan dua laporan Tahap 1,
   mencatat alasan WAIT serta menolak kebocoran. Tes sintetis bukan kelulusan pasar. `export_market_contexts.py`
   membangun `contexts.jsonl` dari tick broker Tahap 0 yang terverifikasi hash (tanpa interpolasi celah);
   dataset pengembangan nyata (butuh tick Tahap 0 yang cukup) dan promosi filter aktif masih belum tersedia; panduan: [Market Intelligence](research/MARKET_INTELLIGENCE.md).
   Pengembangan alat tahap berikutnya boleh berjalan bersamaan dengan observasi Tahap 0.
   **Persiapan Tahap 3:** adapter pembatas tambahan `DemoRiskOverlay` diuji terhadap governor dan boundary
   demo existing dengan broker sintetis; CLI `check_demo_readiness.py` membaca outbox untuk laporan P/L,
   biaya, slippage, WAIT dan kelengkapan rekonsiliasi. Belum terpasang pada worker aktif; nilai profil final
   dan bukti broker nyata masih diperlukan. Panduan: [DEMO readiness](research/DEMO_READINESS.md).
4. **Rencana kerja perbaikan WP1–WP7** (22 Okt) ada di [roadmap](ROADMAP.md#lampiran-a--rencana-kerja-perbaikan-untuk-pelaksana):
   WP1 selesai (#184); berikutnya WP2–WP3 (ChatGPT) dan, paralel, WP8 riset historis setup BUY/SELL antarpair
   dari data pengembangan sebelum 13 Okt 2026.
5. Keputusan Owner di luar roadmap: repo private atau pemisahan website (Tahap 7 perapian), 15 folder lama
   terkunci di `C:\` VPS.

## Panduan terkait

- [Uji di PC](QUICKSTART_PC.md) · [redeploy](deployment/KATARINA_REDEPLOY.md) ·
  [akses GitHub](operations/GITHUB_ACCESS.md) · [aturan pengembangan](operations/GITHUB_FIRST_DEVELOPMENT.md)
- Arsitektur: [diagram satu otak](architecture/KATARINA_SINGLE_BRAIN_WORKFLOW_20261016.md),
  [profil risiko](architecture/RISK_PROFILE_V2.md),
  [host portabel](architecture/KATARINA_PORTABLE_HOST.md),
  [koneksi otomatis](architecture/KATARINA_AUTOMATIC_CONNECTION.md),
  [pemulihan environment](architecture/KATARINA_ENVIRONMENT_RECOVERY.md),
  [pretrial AI trading](architecture/KATARINA_AI_TRADING_PRETRIAL.md)
- Peta kode: [modul runtime](maintenance/RUNTIME_MODULE_MAP.md), [stage body](maintenance/BODY_STAGE_MAP.md)
