# Investigasi kegagalan Tahap 0 — 4 November 2026

Claude, baca-saja (SQLite `mode=ro` + `PRAGMA query_only`). Data ledger VPS tidak diubah; cutoff, denominator dan
klasifikasi resmi tidak diubah. Alat yang bisa diulang: `python scripts/ai/check_stage0_health.py --state-dir DIR
--since 2026-10-28T16:57:00+00:00 --breakdown` (modul `src/katarina/intelligence/operations/stage0_breakdown.py`).

## Status resmi (checker kode deploy `fd6cff16`, `--since 2026-10-28T16:57Z`, as-of 4 Nov 11:18 UTC)

| Kriteria | Hasil |
|---|---|
| Hari bursa beruntun | **3/10** (30 Okt, 2 Nov, 3 Nov). 29 Okt tidak tercakup karena outage observer 09:13–16:44 UTC (27.079 s) |
| Sukses siklus | **5.375/5.575 = 96,41 %** (syarat ≥ 98 %). Gagal: `SOME_SYMBOLS_WITHOUT_QUOTE` 140, `STALE_QUOTES` 47, `BROKER_CLOCK_NOT_VERIFIED` 12, `LOCAL_CONNECT_FAILED` 1 |
| `clock_shift_stable` | **NOT_MET**. Shift palsu 2 → −1 → −8 → 2 (30 Okt 23:55 – 1 Nov 22:07 UTC) dari kode pra-WP13 (RH-011) tetap tercatat |
| Recovery | 3/3 spontan (PASS); `passed_tests` = 0, belum ada uji putus-sambung formal |
| Lainnya | duplikat 0, kutipan per siklus 98,9 %, tick harian PASS, rekonsiliasi 11.314/11.314, **0 order** |

**Laporan harian di VPS saling bertentangan.** `stage0-health-daily.json` memakai kode deploy tanpa `--since`, sedangkan
`stage0-health-since-wp12-daily.json` dijalankan oleh `run-stage0-health-since-wp12.ps1` dari checkout terpin
`b3fd2e6` (sebelum K-04). Sidecar itu masih menulis `clock_shift_stable PASS` dan `rollover dst_plausible` tidak ada.
Usulan: arahkan sidecar ke checker `C:\Katarina\code` setelah deploy berikutnya. Ini perubahan skrip VPS, jadi perlu izin Owner.

## Akar penyebab kegagalan siklus

| Fase pasar (DST-aware, 17:00 New York) | Gagal | Rincian |
|---|---|---|
| `DAILY_BREAK_NY17` = [−15, +60) menit dari 17:00 NY, yaitu 20:45–22:00 UTC (musim panas AS) dan **21:45–23:00 UTC (musim dingin, sejak 1 Nov)** | **192/200** | XAUUSD.vx/NAS100.vx tidak punya quote (`no_past_broker_bidask_quote`) selama jeda harian CFD broker; FX nyaris tidak bergerak dalam 60 detik |
| Lainnya dalam sesi | 8 | 2 `STALE_QUOTES` (3 Nov 21:29 dan 21:37 UTC, likuiditas tipis 16:29 NY), 5 `SOME_SYMBOLS_WITHOUT_QUOTE` di tepi jeda (22:00–23:00 UTC), 1 `LOCAL_CONNECT_FAILED` (3 Nov 07 UTC, pulih sendiri siklus berikutnya) |

Detail 3 Nov (musim dingin, kode WP13 baru):
- 21:56–23:00 UTC hampir setiap siklus gagal, dengan dua pola bergantian.
- Pola pertama: `PARTIAL` (FX bergerak, XAU/NAS tanpa quote).
- Pola kedua: `STALE_QUOTES` (< 3 simbol bergerak, sehingga probe jam menolak dengan benar).
- Audit `live_feed_clock_audit_v1`: 94 penolakan, semuanya `STALE_QUOTES`, 84 di antaranya pada jam 22 UTC. Pada 22:00 tidak satu pun dari 5 simbol bergerak dalam 61 detik.
- 23:01 UTC semua simbol normal kembali.

**Penyebabnya fase pasar/broker, bukan bug program.** Jendela sesi Tahap 0 yang aktif (`fx_session_open`) hanya
mengecualikan 20:45–21:15 UTC tetap (rollover musim panas, 30 menit, tidak DST-aware). Akibatnya sejak 1 Nov
jeda harian 21:45–23:00 UTC ikut dihitung sebagai kegagalan. Aturan DST-aware WP15 (`stage0_session_open`,
17:00 NY −15/+30) sudah ada di `main` tetapi **nonaktif** (`ROLLOVER_RULE_EFFECTIVE_UTC = None`), dan jendela
+30 menit pun belum mencakup jeda CFD sampai 23:00 UTC.

Yang diperiksa dan **bukan** penyebab:
- Timestamp: umur quote XAU p50 0,67 s / p95 1,38 s, NAS p50 0,65 s / p95 1,18 s; 0 regresi waktu tick; offset 2,0 konsisten sejak 1 Nov 22:07 UTC.
- Duplikat: 0.
- Order: 0.
- Retry probe jam dalam siklus yang sama memakai baseline 0,4 s sehingga hampir pasti `STALE_QUOTES`. Ini tidak efisien tetapi fail-closed. Melebarkan baseline berarti melonggarkan kesegaran, jadi **tidak diubah**.

## Tampilan prospektif (diagnostik, BUKAN kriteria; tidak menghapus kegagalan historis)

| Aturan sesi | Siklus | OK | Rate sejak cutoff | Rate sejak deploy WP13 (3 Nov 15:18 UTC) |
|---|---|---|---|---|
| Resmi (legacy 20:45–21:15 UTC) | 5.574 | 5.374 | **96,41 %** | 94,04 % |
| WP15 bila diaktifkan (17:00 NY −15/+30) | 5.527 | 5.407 | 97,83 % | 96,98 % |
| Diagnostik jeda harian (17:00 NY −15/+60) | 5.415 | 5.407 | 99,85 % | 99,71 % |

## Keputusan yang dibutuhkan Owner (dicatat sebagai D8 di `docs/ROADMAP_DISCUSSION.md`)

1. Aktifkan aturan rollover DST-aware secara **prospektif**, yaitu `ROLLOVER_RULE_EFFECTIVE_UTC` pada waktu UTC sesudah persetujuan (tidak retroaktif).
2. Pilih lebar jendela: WP15 (−15/+30) atau jeda CFD penuh (−15/+60). Pilihan kedua bisa juga berupa jadwal sesi per simbol dari broker (probe sesi MT5, Owner).
3. `clock_shift_stable` tidak akan pernah PASS selama jendela penilaian dimulai sebelum deploy WP13. Perlu keputusan apakah hitungan 10 hari dimulai ulang dari 3 Nov 15:18 UTC (deploy WP13). Data lama tetap disimpan.
4. Jadwalkan uji putus-sambung formal (`record_reconnect_test.py`) agar recovery tidak hanya spontan.
