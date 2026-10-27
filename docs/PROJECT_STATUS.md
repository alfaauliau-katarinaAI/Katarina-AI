# Status Katarina AI

Satu-satunya sumber status proyek. **Snapshot operasional baru diperbarui 28 Oktober 2026.** Riwayat 23 Oktober dipertahankan di bagian bawah. Rincian per perubahan ada di
[CHANGELOG](../CHANGELOG.md); hasil CI terbaru di
[GitHub Actions](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions).

## Snapshot operasional terkini — 28 Oktober 2026, sekitar 03.43 WIB

**Laporan ini adalah snapshot, bukan dashboard live.** Baca [audit sistem lengkap untuk Claude](maintenance/CLAUDE_FULL_SYSTEM_AUDIT_20261028.md) dan [kriteria Tahap 0](maintenance/STAGE0_10DAY_ACCEPTANCE_20261028.md). Bagian historis di bawah berasal dari 23 Oktober dan tidak boleh dibaca sebagai status terkini. Kontrak kelulusan tetap di [ROADMAP](ROADMAP.md).

| Komponen | Bukti terbaru | Blocker / arahan |
|---|---|---|
| Wewenang | Level 0 / RESEARCH ONLY / LIVE OFF, 0 order | Tidak ada DEMO/LIVE approval atau strategi terpromosi. |
| Kode produksi | Main VPS masih d8b003a; task observer lama Ready/stopped | Tidak ada merge atau redeploy ke main. Jangan jalankan dua observer. |
| Kandidat trial | Worktree stage0-combined-acceptance-20261028; tree a48d8c3fad957f6d6236dbbc4f1dbe7168069d24, identik dengan [PR #208](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/208) (draft/open) | Bekukan kode pengujian; PR belum di-merge. |
| CI + tes | [CI #40574960082](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/40574960082) SUCCESS Body/Ubuntu/Windows. Lokal 78 tes tertarget dijalankan (77 pass/1 skip), manifest MATCH 306/306 | Lulus CI tidak berarti profit. |
| MT5 Stage 0 | Running sejak 28 Okt 03.12 WIB. Snapshot audit 31/31 siklus OK, 155/155 quote OK, 5 instrumen, UTC broker +2, 0 order; 5 keputusan terbaru WAIT | Masih **0/10 hari bursa penuh**; baru pengamatan awal. |
| Jam VPS | Semula selisih ~14,9 detik terhadap time.windows.com dan Local CMOS. Sekarang w32time Automatic, NTP time.windows.com,0x8, leap 0 / stratum 5, selisih ukur ~0,08 detik, preflight READY | Verifikasi setiap hari. Sejarah DST independen belum ada. |
| Kriteria data | PASS sementara: siklus/quote/duplikat/clock/no-order. NOT_MET: reconnect 0/3. NO_DATA: tick-hari dan rekonsiliasi; belum ada 1 hari penuh | Audit otomatis pada task Katarina-Stage0-Daily-Health pukul 07.30 WIB. |
| Cakupan instrumen | Pilot hanya 5 dari program inti 7 instrumen | Keputusan Claude/Owner diperlukan sebelum mengklaim kelulusan program 7 instrumen. |
| Strategi/AI | Semua lima kartu WAIT, tujuh blocker utama, trial memakai --no-fetch (berita live tidak diuji). Audit riset 13 Oktober: PF kandidat ~0,36 dan ~77% rugi setelah biaya | Belum ada edge BUY/SELL positif tervalidasi; lanjut shadow, WP4/WP8b/WP10. |
| Risk/DEMO | Risk Governor mandiri; batas utama DD 35%; DEMO overlay lebih ketat masih usulan, belum diaktifkan | Perlu persetujuan Owner, tahap valid, 100% rekonsiliasi demo. LIVE OFF. |
| Ketahanan reboot | Task observer baru menggunakan InteractiveToken/trigger logon; limit 72h dihapus, retry 10 kali/5 menit | Tidak dijamin pulih setelah reboot tanpa login Administrator. |
| PR overlap | #206, #207, #208 terbuka dan draft; #195/#204 draft, #205 terbuka belum merge | Review & urutan merge oleh Claude, hindari menerapkan perubahan ganda. |

**Tanggal evaluasi paling awal sekitar 11 November 2026 WIB**, hanya jika 10 hari bursa berturut-turut memenuhi seluruh kriteria; bisa mundur. Untuk UTC historis, bukti pada dua API MT5 dari broker yang sama belum menggantikan referensi independen.

---

## Riwayat status 23 Oktober 2026 — bukan status saat ini

### Ringkasan

| Bagian | Keadaan sekarang | Batas / catatan |
|---|---|---|
| Mode | Research-only, **LIVE OFF**. Tidak ada jalur kirim order ke akun riil | DEMO forward ada di kode, tetapi **tidak berjalan**; hanya observer read-only (lihat VPS) |
| Otak | Satu otak canonical `UnifiedKatarinaBrain` (`intelligence/cognition/unified_brain.py`): observer → market decision (regime, playbook, setup) → kartu BUY/SELL/WAIT → memori, laporan, Risk Governor | BUY/SELL hanya jika skor bukti ≥ 0,62 dan RR memenuhi. Di VPS **100% WAIT**: 7 pemblokir permanen (fail-closed `system_healthy=False`, riwayat forward kosong, berita segar kosong = blackout, entry teknis tidak menyala) — dibongkar lewat WP9 (roadmap Lampiran A; prioritas Owner 23 Okt) |
| Risiko | Risk Governor independen (`engines/risk.py`, `config/risk_governor_v2.json`): 1% default dan maks 5% per entry, 8% total risiko terbuka, **stop entry baru di drawdown harian 35%**, drawdown total 35%. Risiko adaptif dipangkas setengah mulai DD harian 5% / total 10% | Batas 35% disinkronkan di config, Risk Governor, tracker DD harian, gerbang risiko riset, dan dokumen; dijaga `tests/unit/engines/test_daily_drawdown_sync.py` |
| Riset / edge | **Edge belum terbukti.** Audit 13 Okt (17 instrumen): profit factor kandidat 0,36, 77% kandidat rugi setelah biaya. Backtest 2025–2026 (7 instrumen): tidak ada keluarga playbook yang ekspektansinya positif di kedua tahun | Biaya spread ≈ 0,24R vs gerak menguntungkan median ≈ 0,23R. Laporan aslinya ada di riwayat Git (dihapus saat perampingan 22 Okt) |
| VPS | Windows Server 2012 R2, RAM 2 GB, diakses lewat Desktop Commander. Python 3.12.10 di `C:\Katarina\python312`, checkout `main` di `C:\Katarina\code`; `setup`, `doctor`, uji sintetis lulus. MT5 build 6274 dipasang ulang 22 Okt | Observer read-only **berjalan** sejak 22 Okt 04:24 UTC (tugas `Katarina-Readonly-Observer`, akun demo, Algo Trading OFF, siklus 60 detik). Simbol: 5 (EURUSD, GBPUSD, USDJPY, XAUUSD, NAS100) sejak 23 Okt 00:16 UTC (WP6 setelah WP11); 7 setelah pemantauan. Kode VPS = `main` `d8b003a` (WP2, WP3, WP9a, WP11), manifest MATCH. **Quote observer berumur ±3 jam sampai WP12** (R1 T11). Tugas hanya jalan saat Administrator login (auto-start pasca-restart masih WP6) |
| Repository | `main` dilindungi (PR + Body CI wajib). Perampingan 22 Okt: ~1.211 → ~795 berkas, 11 workflow; tooling VPS lama, dokumen bertanggal, skrip riset sekali pakai, dan transport KAT1/ZMQ dipensiunkan | Repo masih **publik**; website masih di repo ini |
| Pengujian | Unit 1.255, static 71 (4 skip), integration 211 lulus (23 Okt, setelah WP2/WP3/WP9a/WP11) | Lulus tes sumber ≠ profitabilitas atau kesiapan live |

## Pekerjaan berikutnya

Pengembangan mengikuti **[Roadmap berbasis bukti](ROADMAP.md)** (ditetapkan Owner 22 Okt 2026): validasi adalah
hakim tertinggi, dan kewenangan Katarina bertambah hanya berdasarkan bukti.

1. **Tahap 0 — Observer & data** (sedang dikerjakan): alat repo selesai 22 Okt (ledger snapshot per siklus,
   pengunduh tick broker per hari, `scripts/ai/check_stage0_health.py`); observer VPS aktif sejak 22 Okt 04:24 UTC
   dengan 3 simbol, 5 simbol sejak 23 Okt 00:16 UTC; uji putus-sambung 3× lulus 22 Okt. **Temuan T11:** jam tick MT5
   adalah jam server (+3 jam), sehingga quote dan arsip tick tergeser 3 jam; WP12 memperbaikinya. 10 hari bursa
   berturut-turut dihitung **sejak WP12 diterapkan** (data sebelumnya hanya bukti operasional), dinilai dengan
   `check_stage0_health.py`.
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
