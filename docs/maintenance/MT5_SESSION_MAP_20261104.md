# Peta sesi quote broker dari arsip tick Tahap 0 — 4 November 2026

**Status:** bukti empiris, baca-saja. **Bukan** jadwal sesi resmi broker. Ambang, denominator dan data
ledger tidak diubah. LIVE OFF, 0 order.

## Metode

- **Sumber.** Arsip tick broker observer: `C:\Katarina\state\readonly-observer\broker-ticks\<SIMBOL>\<YYYY-MM-DD>.csv.gz`, dibuat oleh `observation_ledger.collect_tick_days`.
- **Basis waktu.** UTC: `time_msc` dikurangi `server_shift_hours` per hari.
- **Skrip.** Skrip sekali pakai di VPS (`C:\Katarina\state\session_map_20261104.py`, prioritas rendah, tanpa MT5, tanpa tulis DB) membaca setiap berkas secara streaming. Skrip mencatat tick pertama/terakhir dan setiap celah > 5 menit.
- **Hasil.** `C:\Katarina\state\session-map-20261104.json` (tidak di-commit: turunan data broker).

**Batas basis waktu.**

| Rentang tanggal | Keadaan arsip | Dipakai untuk kesimpulan? |
|---|---|---|
| 22–23 Okt | Dibuat kode lama, masih dalam waktu server (tick terakhir Jumat 23:55 = 20:55 UTC) | Tidak |
| 26 Okt | Memakai shift yang salah (bug pra-WP13, RH-011) | Tidak |
| 27–29 Okt | Konsisten dengan 17:00 New York EDT | Pendukung |
| 2–3 Nov | Dibuat dengan jam live terverifikasi WP13, AS sudah waktu standar | **Dasar kesimpulan** |

## Hasil (UTC, waktu standar AS sejak 1 Nov)

| Simbol | Jeda harian tanpa quote | Dalam waktu New York | Catatan |
|---|---|---|---|
| EURUSD.vx, GBPUSD.vx, USDJPY.vx | **21:54–22:00** (±5 menit) | 16:54–17:00 | Sesudahnya quote tipis; GBPUSD 3 Nov masih ada celah 22:05–22:10 dan 22:15–22:26 |
| XAUUSD.vx | **21:54–23:00** (65 menit) | 16:54–18:00 | Sama pada 27–29 Okt (20:54–22:00 UTC = 16:54–18:00 EDT) |
| NAS100.vx | **21:57–23:01** (63 menit) | 16:57–18:01 | Sama pada 27–29 Okt |
| Buka mingguan (1 Nov) | FX 22:00 UTC, XAU/NAS 23:00 UTC | Minggu 17:00 / 18:00 | — |

Jeda mengikuti jam New York (bergeser satu jam bersama DST AS). Ini konsisten dengan temuan investigasi Tahap 0 (`STAGE0_FAILURE_INVESTIGATION_20261104.md`).

## Implikasi untuk D8 (untuk keputusan Owner, bukan perubahan)

Jendela pengecualian yang diputuskan **WP15 −15/+30**, efektif 5 Nov 2026 00:00 UTC:

- mencakup jeda FX: 21:45–22:30 UTC;
- **tidak** mencakup sisa jeda XAU/NAS 22:30–23:01 UTC.

Siklus pada 22:30–23:00 UTC tetap gagal (`SOME_SYMBOLS_WITHOUT_QUOTE`/`STALE_QUOTES`) karena broker memang tidak mengirim quote CFD. Tampilan diagnostik investigasi memberi 97,83 % untuk −15/+30 (di bawah 98 %) dan 99,85 % untuk −15/+60. Ini diajukan sebagai **D9** di MEETING. **Diputuskan Owner 10 Nov:** −15/+60 mulai 11 Nov 2026 00:00 UTC (RH-015).

## Yang belum terbukti

- Jadwal sesi **resmi** broker (MT5 *Specification → Sessions*, `SymbolInfoSessionQuote`) belum dibaca. Membacanya butuh GUI terminal (Owner) atau menjalankan skrip MQL di terminal produksi, yang tidak dilakukan.
- Hari libur dan jadwal khusus (mis. Thanksgiving, akhir tahun) tidak terlihat dalam 10 hari data.
