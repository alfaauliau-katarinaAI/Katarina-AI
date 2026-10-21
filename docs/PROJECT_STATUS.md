# Status Katarina AI

Satu-satunya sumber status proyek. Diperbarui **21 Oktober 2026**. Rincian per perubahan ada di
[CHANGELOG](../CHANGELOG.md); hasil CI terbaru di
[GitHub Actions](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions). Status sebelumnya
(16 Oktober) dan dokumen serah-terima lama tersedia di riwayat Git (folder `archive/` dihapus 21 Oktober).

## Ringkasan

| Bagian | Keadaan | Batas |
|---|---|---|
| Mode | Research-only; DEMO forward di VPS uji; **LIVE OFF** | Tidak ada jalur kirim order live |
| Otak | Satu otak canonical `UnifiedKatarinaBrain` (`intelligence/cognition/unified_brain.py`) dengan 17 modul terdaftar | Versi otak lama sudah dipensiunkan/diganti nama (perapian Tahap 2–3) |
| Risiko | Risk Governor independen (`engines/risk.py`); stop harian Owner 35% berlaku di setiap entry baru; drawdown ekstrem fail-closed meski quote risiko basi | Konfigurasi risk tidak diubah oleh perapian |
| Riset | Lab riset broker memakai spread tipikal per candle H1; instrumen dengan biaya > 20% range ditandai `COST_PROHIBITIVE`; guard seleksi v26 (riset saja) | **Edge belum terbukti**; belum ada uji out-of-sample/forward yang cukup |
| Data & arsip | Arsip riset privat HF terverifikasi dengan tooling redeploy; Gemini dipakai untuk riset artikel publik di VPS | Kredensial disediakan ulang per host, tidak pernah di repo |
| Website | Posisi/PnL DEMO, aktivitas riset, dan terminal operasi 3D tampil di situs Katarina | Situs masih di repo ini (pemisahan repo = Tahap 7, butuh langkah Owner di Cloudflare) |
| Pengujian | Unit ~1.450, static 113, integration ~210 lulus di Body CI; replay dan research lulus lokal | Lulus tes sumber ≠ profitabilitas atau kesiapan live |
| Repository | `main` dilindungi (PR + Body CI wajib); perapian 8 tahap sedang berjalan | Lihat [rencana perapian](maintenance/CLEANUP_PLAN.md) dan status tahap di `CLAUDE.md` |

## Pekerjaan berikutnya

1. Bukti edge: ulang riset setelah perbaikan spread, uji out-of-sample, dan hasil DEMO forward yang
   cukup lama dan konsisten. Ini penentu apakah bot boleh trading otomatis.
2. Verifikasi read-only checkout, fingerprint modul, memori, dan proses VPS sebelum menyatakan VPS
   sinkron dengan `main`.
3. Pemisahan website ke repo sendiri setelah project Cloudflare Pages dan token publisher disiapkan Owner.

## Panduan terkait

- [Uji di PC](QUICKSTART_PC.md) · [redeploy](deployment/KATARINA_REDEPLOY.md) ·
  [akses GitHub](operations/GITHUB_ACCESS.md) · [aturan pengembangan](operations/GITHUB_FIRST_DEVELOPMENT.md)
- Arsitektur: [diagram satu otak](architecture/KATARINA_SINGLE_BRAIN_WORKFLOW_20261016.md),
  [host portabel](architecture/KATARINA_PORTABLE_HOST.md),
  [koneksi otomatis](architecture/KATARINA_AUTOMATIC_CONNECTION.md),
  [pemulihan environment](architecture/KATARINA_ENVIRONMENT_RECOVERY.md),
  [pretrial AI trading](architecture/KATARINA_AI_TRADING_PRETRIAL.md)
- Peta kode: [modul runtime](maintenance/RUNTIME_MODULE_MAP.md), [stage body](maintenance/BODY_STAGE_MAP.md)
