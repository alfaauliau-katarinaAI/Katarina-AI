# Katarina AI — Current Project Handoff

Updated: **2026-10-16 (Asia/Jakarta)**.

Mulai dari [status proyek terkini](PROJECT_STATUS.md),
[changelog](../CHANGELOG.md), dan
[aturan GitHub-first](operations/GITHUB_FIRST_DEVELOPMENT.md).

Arsitektur canonical terbaru: `UnifiedKatarinaBrain`, satu instance observer,
17 modul dalam registry dan satu memori bersama untuk Fast/Deep. Management,
11 spesialis, workplan, script dan workflow pemanggil sudah dihapus berdasarkan
instruksi Owner 15 Oktober 2026. Risk Governor tetap independen.

Pengujian perubahan: 1.270 unit, 113 static (4 skipped), 110 integration.
Tidak ada order atau live execution. GitHub dan checkout kerja disamakan pada
commit hasil merge; checkout, memori dan proses VPS belum diverifikasi.

Repository publik tetap dimiliki akun `alfaauliau-katarinaAI`; main wajib PR dan
CI, dengan larangan force-push/penghapusan. Seluruh 42 branch awal selain main
sudah diselesaikan melalui PR #85/#86 dan guarded cleanup. Hanya main tersisa;
seluruh head lama dipertahankan sebagai ancestor main. Neuro-Link recall dan
riset offline ditambahkan; engine produksi dan Risk Governor tidak diubah.

Akses CLI lintas perangkat: [panduan dan batas autentikasi](operations/GITHUB_ACCESS.md).
Jangan menyalin token aplikasi ChatGPT, cookie browser, atau kredensial ke source,
Actions artifact, issue maupun chat. Jangan menonaktifkan proteksi untuk mengatasi
hambatan akses.

Dokumen terdahulu disimpan sebagai [arsip 10 Oktober](handoff/PROJECT_HANDOFF_20261010.md)
dan [checkpoint sampai 13 Oktober](handoff/KATARINA_START_NEXT_CHAT_20261013.md).
Catatan host lama di dalamnya bukan keadaan VPS saat ini.

Patokan arsitektur kini [diagram satu otak 16 Oktober](architecture/KATARINA_SINGLE_BRAIN_WORKFLOW_20261016.md).
Otak memiliki observer, monitoring, modal/recovery offline dan gerbang OFF;
Risk Governor tetap di luar. Entry point legacy menolak start. Tidak ada
migrasi state broker, scheduler, deployment VPS atau aktivasi live dari perubahan ini.

## Portabilitas host — 16 Oktober 2026

Otak dapat menjalankan satu siklus riset lokal tanpa VPS/MT5 melalui
`run_contextual_market_observer.py --offline-research`. `--doctor` memeriksa host;
lokasi state mengikuti konfigurasi/OS, anggaran observasi mengikuti kapasitas.
Lihat [panduan host portabel](architecture/KATARINA_PORTABLE_HOST.md). Tidak ada migrasi state legacy otomatis,
Cloud Hands lintas host belum terverifikasi, live tetap OFF.

## Koneksi otomatis baca-saja — 16 Oktober 2026

Launcher memilih local/cloud/offline menurut konfigurasi akun yang diizinkan.
Retry terbatas mengulang seluruh pass; tanpa koneksi valid tetap riset lokal.
Sensor HTTPS baru memerlukan pemasangan dan kredensial sekali; belum diuji pada
MT5/cloud nyata. Lihat [kontrak koneksi otomatis](architecture/KATARINA_AUTOMATIC_CONNECTION.md). Risk Governor independen, live OFF.

## Paket uji PC — 16 Oktober 2026

Peluncur utama START_KATARINA sekarang menjalankan acceptance sintetis sekali,
bukan supervisor VPS background. SETUP_KATARINA membuat environment privat.
Laporan HTML/JSON lokal memisahkan hasil demo dari observasi broker dan tidak
menganggap fallback offline sebagai kelulusan broker. Lihat [panduan PC](QUICKSTART_PC.md).
Paket source-only bermanifest commit disediakan artifact CI; live OFF.

## Pemulihan environment privat — 16 Oktober 2026

Startup memeriksa dependensi dan menguji kandidat pengganti sebelum memilihnya.
Environment lama, strategi, Risk Governor dan memori tetap dipertahankan; tidak
ada perubahan source atau izin trading. Panduan: [pemulihan environment](architecture/KATARINA_ENVIRONMENT_RECOVERY.md). Live OFF.
