# Status Katarina AI

Satu-satunya sumber status proyek. Diperbarui **23 Oktober 2026**. Rincian per perubahan ada di
[CHANGELOG](../CHANGELOG.md); hasil CI terbaru di
[GitHub Actions](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions).

## Ringkasan

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
