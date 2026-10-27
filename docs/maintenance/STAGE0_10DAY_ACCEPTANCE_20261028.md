# Stage0 - 10 hari bursa read-only MT5

Tanggal 28 Oktober 2026. Status: kandidat gabungan WP12/WP9b/WP8a dan guard portabilitas. LIVE OFF.

## Bukti kesiapan teknis

- Awal pemeriksaan VPS W32Time masih Local CMOS, stratum 0, leap 3 dan selisih ~14,9 detik terhadap time.windows.com.
- Setelah observer berhenti tertib (STOPPED/OWNER_STOP_REQUEST), database context + cognitive memory dibackup konsisten dengan SQLite quick_check=ok. Backup konfigurasi W32Time dan task observer tersimpan privat pada C:\Katarina\_roadmap_validation\maintenance-20261028.
- Service w32time disetel Automatic, peer time.windows.com,0x8, interval polling ~1024s. Status setelah resync: Leap Indicator 0, Stratum 5, waktu sinkron terakhir tersedia; stripchart ~0,08s. Preflight script scripts/ai/check_host_clock.py = READY.
- Kontrak WP12 dan portabilitas digabung: kandidat server shift disimpulkan dari latest tick 3 simbol, historical copy_ticks_range dibaca memakai server_shift_hours kandidat lalu dikonversi ke UTC. Dua API dari satu broker adalah bukti konsistensi internal, bukan bukti independen jam sejarah/DST.
- Uji langsung MT5 read-only, mode satu siklus, state terpisah C:\Katarina\_roadmap_validation\mt5-smoke-20261028 sekitar 02:51 WIB: 5 simbol teramati, 5 data pasar diterima, offset broker +2 jam, koneksi lokal dan identitas terverifikasi, 5 WAIT, order 0, tanpa error. Uji satu siklus ini bukan satu hari uji yang lengkap.

## Syarat memulai penghitung 10 hari

1. Hasil CI gabungan di Linux, Windows dan Body lulus; Claude/Owner mereview cara deploy dan rollback. Versi candidate dan hash release manifest tercatat.
2. NTP terus sehat. Tidak ada sumber waktu lokal CMOS dan UTC dibandingkan dengan layanan waktu eksternal.
3. Hanya satu observer foreground atau scheduled task read-only yang aktif pada state baru, bukan ledger lama. Semua koneksi broker menolak izin trading; LIVE OFF, tidak ada order.
4. Timestamp awal adalah siklus data valid pertama setelah build disetujui dan ditempatkan. Data pra-WP12/NTP tidak termasuk.
5. 10 hari bursa berturut-turut dengan >=90% cakupan menit sesi per hari; siklus sukses >=98%; quote coverage >=98%; tanpa duplikat, regresi timestamp, transisi jam tidak wajar, mismatch tick snapshot, atau order. Ini adalah kriteria Tahap 0 dalam roadmap, bukan waktu kalender 10 hari tanpa syarat.
6. Dashboard menyimpan alasan WAIT/DEGRADED/BLOCKED dan operator memeriksa status NTP, hari tertutup, heartbeat observer dan Stage0 health tiap hari.
7. Jika outage terjadi, periode dihitung hanya menurut evidence valid; jangan menghapus kegagalan atau backfill gap.

## Perintah audit (hanya baca)

- python scripts/ai/check_host_clock.py
- python scripts/ai/check_stage0_health.py --state-dir PATH_STATE_BARU
- w32tm /query /status
- schtasks /query /tn Katarina-Readonly-Observer /fo LIST /v

Batas: clock historical DST memerlukan referensi independen; keberhasilan satu siklus tidak membuktikan profit atau DEMO. Boot tanpa login masih belum dibuktikan, Task Scheduler sekarang principal InteractiveToken.
