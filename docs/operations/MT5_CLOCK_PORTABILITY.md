# Kontrak waktu MT5-VPS portabel

Tanggal: 28 Oktober 2026. Status: draft untuk review Claude, BELUM deploy. LIVE OFF.

## Prinsip

KATARINA memakai UTC aware (datetime.now(timezone.utc)) untuk semua batas waktu. Zona lokal perangkat (Jakarta atau lainnya) hanya untuk tampilan. Jam server broker tetap boleh berbeda +2/+3 atau nilai lain; yang penting identitas, offset, periode dan bukti konversi tidak disalahartikan.

- MT5 symbol_info_tick().time mungkin menunjukkan jam server; nilai ini HANYA kandidat offset saat ini.
- infer_clock_shift memerlukan minimal 3 simbol dan quorum 70%, serta menolak perubahan inferensi pada akhir pekan FX dan Jumat setelah 20 UTC untuk menghindari tick basi.
- corroborate_clock_with_utc_history mewajibkan tick copy_ticks_range dari batas datetime UTC-aware, tiga simbol, usia maksimal 90 detik, dan perbedaan ke kandidat offset maksimal 45 detik. Ketiadaan tick atau konflik = FAIL CLOSED, jangan menerbitkan snapshot.
- Candle harus selesai berdasarkan jam tick peristiwa yang tervalidasi; jam host bukan bukti candle sudah tutup.
- Sumber MT5 real-time dan historical adalah dua API dari broker yang sama, BUKAN otoritas UTC eksternal yang sepenuhnya independen. Dokumentasi resmi dan praktik broker dapat berbeda. Validasi terhadap sumber NTP luar masih dibutuhkan.
- Konversi historis dan DST tidak boleh memakai offset terbaru. Pertahankan guard WP8a dengan bukti offset UTC independen per batch; bila tidak ada, ekspor ditolak.

## Preflight jam host per perangkat

Windows: w32tm /query /status
Linux systemd: timedatectl show -p NTPSynchronized --value
Dari kode project: python scripts/ai/check_host_clock.py

Kondisi yang wajib ditolak:
- Windows Source Local CMOS Clock atau free-running, Leap Indicator bukan 0, Stratum 0, Last Successful Sync Time tidak tersedia/tidak bisa dibaca/lebih dari 2 jam.
- Linux yang tidak melaporkan NTPSynchronized=yes atau tool status tidak tersedia.

Guard berjalan otomatis untuk rute produksi lokal + cloud di siklus canonical dan inisialisasi MetaTrader5 native, sehingga cloud fallback tidak boleh mem-bypass status NTP host. Gangguan singkat verifikasi silang UTC ditandai sebagai sensor DEGRADED dengan retry terbatas tanpa snapshot; hilangnya sinkronisasi NTP host memberi status BLOCKED yang eksplisit dan tidak boleh di-bypass. Test doubles via injected factories tidak mengakses broker dan tidak menjalankan pemeriksaan OS.

Caveat: status OS NTP baik hanya prasyarat operasional, bukan sertifikat independen bahwa UTC absolut benar. Administrator harus memeriksa peer NTP tepercaya dan pembanding waktu eksternal saat migrasi.

## Hasil audit VPS pada 28 Oktober

Zona waktu Windows: SE Asia Standard Time (+07). NTP Windows:
- Source: Local CMOS Clock
- Stratum: 0
- Leap Indicator: 3
- Last Successful Sync Time: unspecified

Pemeriksa baru mengembalikan BLOCKED / HOST_UTC_NOT_SYNCHRONIZED pada VPS. Menambah atau memindahkan zona waktu tidak memperbaiki NTP. Jangan deploy guard produksi sebelum sinkronisasi host pada maintenance window; kode baru memang memblokir pembacaan broker saat kondisi ini. Jam sistem saat audit TIDAK diubah, observer produksi tidak dihentikan dan tidak restart.

## Checklist migrasi device / broker

1. Backup state/manifest dan private connection config lewat media privat yang disetujui; LIVE OFF. Jangan commit kredensial ke GitHub publik.
2. Jadwalkan maintenance dan hentikan observer sebelum penyesuaian waktu OS. Konfigurasikan peer NTP tepercaya pada sistem target sesuai kebijakan administrator; verifikasi terhadap UTC independen. Jangan paksa w32tm /resync saat worker MT5 masih membuat ledger.
3. Pastikan Python/MT5 versi, account/server identity, core symbols, contract size/tick size dan manifest release konsisten.
4. Jalankan check_host_clock.py. Status BLOCKED = jangan memulai forward valid. Saat pasar benar-benar buka, uji >=3 quote dan UTC copy_ticks_range; bila broker tak menyediakan bukti lintas API yang konsisten, jangan mengarang offset.
5. Uji kembali setelah reboot, perubahan DST, pergantian broker atau OS timezone. Catat first valid cycle pada host baru, serta cek monotonisitas, gap, clock_shift_stable, no_duplicates dan zero_orders.
6. Arsip sebelum jam tervalidasi tidak boleh di-backfill sebagai bukti forward. Untuk kalender DST historis diperlukan sumber UTC eksternal dan hash bukti per batch.
7. Task Scheduler sekarang LogonTrigger + InteractiveToken, bukan boot yang teruji; jangan menambah BootTrigger tanpa menguji MT5 GUI, otorisasi akun/sesi dan rollback.

## Pengujian

- tests/unit/intelligence/test_host_clock_portability.py: Windows/Linux, CMOS, NTP stale, timezone +7 vs UTC, tick basi weekend, quorum 3, migrasi native.
- tests/unit/intelligence/test_broker_clock_alignment.py: acuan UTC, evidence expiry, perubahan offset.
- tests/integration/test_brain_owned_workflow.py: ketika sejarah UTC tidak ada, stop fail-closed; tidak membuat snapshot palsu.
- tests/integration/test_continuous_observation.py: worker lifecycle satu jalur.
- CI Ubuntu+Windows pada PR harus lulus sebelum merge. Test koneksi numpy pada Python minimal VPS terhalang dependensi yang belum terpasang.

Lihat docs/maintenance/STAGE0_CLOCK_HEALTH_HANDOFF_20261028.md untuk temuan +3 -> -4 -> -7 -> +2 dan false PASS pada pemeriksa sebelum patch. Tidak ada promosi DEMO / LIVE.
