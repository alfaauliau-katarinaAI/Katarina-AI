# Status Katarina AI

Satu-satunya sumber status proyek. Diperbarui **22 Oktober 2026**. Rincian per perubahan ada di
[CHANGELOG](../CHANGELOG.md); hasil CI terbaru di
[GitHub Actions](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions).

## Ringkasan

| Bagian | Keadaan sekarang | Batas / catatan |
|---|---|---|
| Mode | Research-only, **LIVE OFF**. Tidak ada jalur kirim order ke akun riil | DEMO forward ada di kode, tetapi **tidak berjalan** (lihat VPS) |
| Otak | Satu otak canonical `UnifiedKatarinaBrain` (`intelligence/cognition/unified_brain.py`): observer → market decision (regime, playbook, setup) → kartu BUY/SELL/WAIT → memori, laporan, Risk Governor | BUY/SELL hanya jika skor bukti ≥ 0,62 dan RR memenuhi; selain itu WAIT |
| Risiko | Risk Governor independen (`engines/risk.py`, `config/risk_governor_v2.json`): 1% default dan maks 5% per entry, 8% total risiko terbuka, **stop entry baru di drawdown harian 35%**, drawdown total 35%. Risiko adaptif dipangkas setengah mulai DD harian 5% / total 10% | Batas 35% disinkronkan di config, Risk Governor, tracker DD harian, gerbang risiko riset, dan dokumen; dijaga `tests/unit/engines/test_daily_drawdown_sync.py` |
| Riset / edge | **Edge belum terbukti.** Audit 13 Okt (17 instrumen): profit factor kandidat 0,36, 77% kandidat rugi setelah biaya. Backtest 2025–2026 (7 instrumen): tidak ada keluarga playbook yang ekspektansinya positif di kedua tahun | Biaya spread ≈ 0,24R vs gerak menguntungkan median ≈ 0,23R. Laporan aslinya ada di riwayat Git (dihapus saat perampingan 22 Okt) |
| VPS | Windows Server 2012 R2, RAM 2 GB, diakses lewat Desktop Commander. Python 3.12.10 di `C:\Katarina\python312`, checkout `main` di `C:\Katarina\code`; `setup`, `doctor`, uji sintetis lulus. MT5 build 6274 dipasang ulang 22 Okt | Observer **belum jalan**: menunggu Owner login akun demo di MT5 (Algo Trading OFF) dan konfigurasi koneksi privat. Tugas `Katarina-Readonly-Observer` disiapkan dalam keadaan Disabled |
| Repository | `main` dilindungi (PR + Body CI wajib). Perampingan 22 Okt: ~1.211 → ~795 berkas, 11 workflow; tooling VPS lama, dokumen bertanggal, skrip riset sekali pakai, dan transport KAT1/ZMQ dipensiunkan | Repo masih **publik**; website masih di repo ini |
| Pengujian | Unit ~1.140, static 69, integration ~204 lulus di Body CI | Lulus tes sumber ≠ profitabilitas atau kesiapan live |

## Pekerjaan berikutnya

Pengembangan mengikuti **[Roadmap berbasis bukti](ROADMAP.md)** (ditetapkan Owner 22 Okt 2026): validasi adalah
hakim tertinggi, dan kewenangan Katarina bertambah hanya berdasarkan bukti.

1. **Tahap 0 — Observer & data** (sedang dikerjakan): alat repo selesai 22 Okt (ledger snapshot per siklus,
   pengunduh tick broker per hari, `scripts/ai/check_stage0_health.py`). Sisa: Owner login akun demo di MT5 VPS
   (Algo Trading OFF), konfigurasi koneksi privat, observer read-only diaktifkan, lalu 10 hari bursa data.
2. **Tahap 1 — Validasi ilmiah:** protokol uji, walk-forward, holdout terkunci, biaya bersih, baseline.
3. Tahap 2–5 (market intelligence, risk & execution, strategi adaptif, kalibrasi & riset mandiri) berurutan,
   masing-masing dengan kriteria kelulusan di roadmap.
4. Keputusan Owner di luar roadmap: repo private atau pemisahan website (Tahap 7 perapian), 15 folder lama
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
