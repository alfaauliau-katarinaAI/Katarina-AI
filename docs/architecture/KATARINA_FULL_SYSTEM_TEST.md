# Katarina — penerimaan sistem terhadap diagram

Acuan: hasil rapat 16 Oktober 2026. Dokumen ini melengkapi acuan tersebut;
status software, bukti host, kualitas model, alpha dan izin eksekusi berbeda.
Target diagram adalah arah pengembangan, bukan bukti semua fitur telah siap.

## Integrasi satu otak

CLI observer yang sama mendukung dialog sambil melakukan observasi berulang:

```text
python scripts/ai/run_contextual_market_observer.py --continuous --no-fetch --max-symbols 3 --interval-seconds 60 --state-dir PRIVATE_REAL_STATE --connection-config PRIVATE_CONNECTION --owner-model-config PRIVATE_MODEL --owner-access-config PRIVATE_ACCESS
```

Server HTTP diproses pada thread foreground yang sama di sela observasi. Tidak
ada otak, thread worker, MemoryStore atau database kedua. Request tidak dapat
berjalan bersamaan dengan siklus sensor. Tool model dibatasi oleh server: Owner
status/riset lokal, analis hanya status. Owner dapat memberikan folder dengan
`--owner-workspace` dan daftar sumber HTTPS dengan `--owner-sources-config`;
bacaan file/sumber membawa digest dan tidak menjadi izin trading. Persetujuan metode dan perubahan risiko
tetap melalui jalur Owner terpercaya; dialog tidak memiliki tool pengiriman order.
Observer tetap dapat berjalan tanpa antarmuka/model. Hilangkan `--no-fetch` untuk
refresh sumber berita/kalender gratis yang sudah ditetapkan; kualitas/freshness
sumber tetap diperiksa dan kegagalan tidak memberi izin entry. `continuous.stop` menghentikan
keduanya. Status, checkpoint dan lock tetap dimiliki proses yang sama.

Dialog/model yang lambat menunda siklus berikutnya; tidak ada klaim analisis tanpa
latensi. Request dibatasi ukuran, jumlah langkah, timeout jaringan dan TLS handshake.
Server tidak membuat siklus susulan untuk mengejar keterlambatan. Default bind adalah
loopback. Untuk akses HP jarak jauh, gunakan `--owner-bind`, `--owner-cert`, dan
`--owner-key` dengan TLS yang dipercaya perangkat. Jangan membuka port HTTP publik.

## Kredensial Owner dan analis

Jalankan pada konsol privat host, bukan log CI atau job yang mengekspor stdout:

```text
python scripts/pc/manage_owner_access.py issue --config PRIVATE_ACCESS --id owner --role owner
python scripts/pc/manage_owner_access.py issue --config PRIVATE_ACCESS --id analyst1 --role analyst
python scripts/pc/manage_owner_access.py revoke --config PRIVATE_ACCESS --id analyst1
```

Token acak ditampilkan sekali di konsol privat. File hanya menyimpan SHA-256;
jangan masukkan file/token ke source GitHub. Simpan di folder dengan ACL privat
Owner/SYSTEM pada Windows; chmod bukan pengganti ACL Windows. ID yang pernah dibuat
tidak dapat dipakai ulang; buat ID baru untuk rotasi. Owner aktif terakhir tidak
dapat dicabut sebelum ada pengganti. Kebijakan dimuat ulang setiap request sehingga
pencabutan langsung berlaku. Sesi diturunkan server dari ID kredensial dan label
sesi: analis tidak dapat mengambil riwayat Owner dengan mengirim session_id owner.

Kredensial ini bukan persetujuan pembelajaran intervensi atau aktivasi strategi.
Koleksi intervensi lintas pengguna tetap tidak aktif sampai jalur izin, penghapusan
dan pengujian isolasinya lengkap. Antarmuka ini bukan admin Risk Governor.

## Matriks pengujian

| Target diagram | Perilaku yang diuji | Bukti nyata tambahan sebelum produksi |
|---|---|---|
| Satu otak + memori | Sensor, dialog, tool, ACK dan checkpoint pada satu instance/thread/store; restart dan lock | Ketahanan host dan sesi Windows |
| Fast / Deep | Routing, batas langkah, kesalahan provider | Model nyata, mutu jawaban dan latensi |
| Persepsi pasar | Candle tertutup, waktu kausal, harga broker terikat akun | Cakupan sejarah tiap instrumen, sesi dan DST |
| Riset + belajar | Shadow, provenance, integritas, rollback, threshold proposals | Outcome prospektif cukup; quote bukan fill |
| Kandidat metode | Versi immutable, trial gagal, digest evaluasi, review Owner | Kebijakan penerimaan dan persetujuan versi tertentu |
| Drift/adaptasi | Gate bukti, biaya, regime, stop tanpa bukti | Ambang yang diuji dan disetujui; tanpa bypass risk |
| Risk Governor | Veto independen dan alasan penolakan | Risiko portofolio/riwayat loss nyata |
| Proteksi + recovery | Profit Lock, modal, state recovery, larangan modifikasi posisi manual | Putus koneksi, partial fill dan rekonsiliasi di demo |
| Hands / MT5 | Jalur lokal/cloud, akun terikat, WAIT/ACK, penolakan order | Banyak akun/perangkat nyata dan proteksi lokal |
| Antarmuka | Auth, pencabutan, peran, isolasi sesi, batas transport | HTTPS terpercaya dan akses HP tujuan |
| Laporan | Rekap tujuh hari, pemisahan jenis bukti dan kegagalan | Rekap aktivitas nyata; tidak ada pengiriman otomatis |
| Model sendiri | Lab belajar/evaluasi proposal dengan bukti kausal | Training/evaluasi model trading; alpha belum terbukti |

## Menjalankan penerimaan lengkap

Dari checkout source penuh dengan Python 3.12 dan dependensi proyek:

```text
python scripts/pc/run_system_acceptance.py --state-dir PRIVATE_TEST_STATE --observer-state PRIVATE_REAL_STATE
```

Runner menjalankan seluruh unit, static dan integration suite di subprocess
bertimeout (default 300 detik per suite; host lambat dapat memakai
`--timeout-seconds 900`, maksimum 1800), mencatat SHA dan kebersihan source serta log privat per grup. Database
uji berada di direktori uji tersendiri; runner hanya membaca snapshot observer
aktif dan tidak membuka database/lock otak. Snapshot dibatasi umur, ukuran dan
penanda keamanan. Snapshot segar bukan bukti identitas proses atau source: cocokkan
PID/run ID/SHA melalui controller GitHub. Jangan gunakan test state untuk broker.

`PASS_SOFTWARE_ONLY_DESTINATION_GATES_REMAIN` berarti software lulus. Ini bukan
status siap live, bukan alpha, bukan hasil uji HP, model nyata atau fill broker.
Uji semua kelompok walaupun satu kelompok gagal, agar laporan tidak menyembunyikan
kegagalan berikutnya. Mode discovery/model smoke yang dilewati CI tidak boleh
berubah menjadi klaim koneksi model terverifikasi.

## Urutan uji Owner

1. Lulus seluruh suite dan CI Linux/Windows/macOS pada SHA tepat.
2. Stop observer lewat controller; sinkron clean main; jalankan penerimaan sintetis
   pada state terpisah; resume dan verifikasi sensor nyata pada state semula.
3. Sediakan model nyata, kredensial privat dan HTTPS terpercaya; uji Fast/Deep,
   tool, revocation, latensi dan akses HP pada host tujuan.
4. Uji riset dengan data kausal, jumlah trial tercatat, walk-forward, holdout belum
   disentuh, biaya broker dan stress; pisahkan bukti yang saling berkorelasi.
5. Setujui versi metode serta kebijakan demo sebelum uji pengiriman order demo.
   Rekonsiliasi fill, slippage, spread, swap, intervensi, disconnect dan recovery.
6. Review mingguan; aktivasi real trading adalah gerbang tersendiri. Modal Owner
   siap rugi bukan alasan melepas proteksi atau mempercepat kelulusan bukti.

## Runtime portable dan checkout kanonis

Di VPS sekarang (22 Okt 2026) Python 3.12 terpasang di `C:\Katarina\python312`, source kanonis
(checkout `main`) di `C:\Katarina\code`, dan state di `C:\Katarina\state`. Root instalasi bukan
root source. Untuk Python embeddable, `scripts/pc/bind_portable_runtime.py` mengutamakan checkout kanonis dalam `python312._pth`, menyimpan
backup berdasarkan hash dan mempertahankan stdlib/site packages serta path lama.
Perubahan file path saja bukan bukti impor: jalankan probe proses Python baru dan
pastikan modul yang terimpor berada di checkout yang disetujui. Hentikan otak dan
selesaikan test aktif sebelum mengganti pengikatan runtime.

Python embeddable tidak menyertakan modul `venv`. Observer dapat memakainya,
tetapi pengujian pemulihan environment PC membutuhkan instalasi Python 3.12 penuh.
Instalasi penuh harus terpisah, dependensi diverifikasi, dan baru kemudian dipakai
controller. Binder mendukung `.pth` khusus pada instalasi penuh serta `_pth` pada
embedded; jangan mengisi stdlib secara manual hanya agar test terlihat lulus.
Penolakan HTTP membaca hanya body terbatas sebelum menutup koneksi, agar response
403 tidak hilang karena TCP reset pada Windows.
