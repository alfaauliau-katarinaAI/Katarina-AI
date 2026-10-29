# RIWAYAT PERBAIKAN — Katarina AI

Dokumen ini adalah **satu-satunya jurnal hasil perbaikan yang terverifikasi**: masalah yang ditemukan, akar penyebab yang dibuktikan, tindakan yang benar-benar diterapkan, berkas yang berubah, tes, bukti VPS, dan batas hasil. Disiapkan untuk dibaca Claude dan manager. **Bukan antrean pekerjaan**, bukan notula rapat, dan bukan status langsung.

## Batas tanggung jawab dokumen

| Pertanyaan | Sumber resmi |
|---|---|
| Apa tujuan, fase, prioritas, dependensi, dan kriteria kelulusan? | [ROADMAP.md](ROADMAP.md) |
| Apa yang masih dibahas, ditolak, atau menunggu keputusan? | [MEETING / ROADMAP_DISCUSSION.md](ROADMAP_DISCUSSION.md) |
| Perbaikan mana yang sudah dikerjakan, bagaimana, dan apa buktinya? | **REPAIR_HISTORY.md ini** |
| Bagaimana kondisi operasional terkini, termasuk blocker yang belum diperbaiki? | [PROJECT_STATUS.md](PROJECT_STATUS.md) |
| Apa yang berubah per commit/PR secara teknis? | [CHANGELOG.md](../CHANGELOG.md) dan deskripsi PR |
| Apa aturan tetap yang tidak boleh dilonggarkan? | [ROADMAP.md](ROADMAP.md) bagian 1–7 dan [KATARINA_CONSTITUTION.md](../KATARINA_CONSTITUTION.md) |

## Aturan untuk Claude dan pelaksana

1. Tambahkan **satu entri per perbaikan/insiden** hanya ketika perubahan atau langkah pemulihan memiliki **bukti konkret**. Jika masih investigasi, catat blocker di `PROJECT_STATUS.md`; jika memerlukan keputusan, bahas di `ROADMAP_DISCUSSION.md`. Jangan mengubah roadmap menjadi log aktivitas.
2. Setiap entri menyebut: ID, tanggal, gejala awal, akar masalah (**TERBUKTI** atau **BELUM TERBUKTI**), tindakan + jalur berkas, PR/commit, verifikasi CI dan/atau VPS, hasil, serta sisa risiko. Bukti baru boleh ditambahkan dalam entri yang sama, tidak membuka catatan duplikat.
3. Pisahkan **kode sudah di-merge**, **sudah dideploy**, **smoke test lolos**, dan **lulus kriteria roadmap**. Itu empat status yang berbeda; jangan tulis `SELESAI` untuk hal yang hanya lolos satu tahap.
4. `CHANGELOG.md` tetap mencatat ringkasan perubahan per PR; detail diagnosis dan hasil pemulihan hanya di sini, dengan tautan ke PR. `PROJECT_STATUS.md` hanya menyimpan kondisi saat ini dan merujuk ID perbaikan bila diperlukan.
5. Pengembangan lewat GitHub dan PR + CI. VPS hanya untuk pengujian yang diizinkan. Tidak ada perubahan yang mengaktifkan LIVE, order, membuka holdout, atau melemahkan Risk Governor tanpa keputusan Owner yang berlaku.

## RH-005 — Bukti jam bar historis WP8c dibuat fail-closed

**Tanggal:** 30 Oktober 2026 WIB
**Status:** **Kode riset MERGED + CI PASS**; tanpa bukti nyata (kalender rilis kosong), belum dipakai di VPS; tidak ada data development yang diekspor.

| Aspek | Bukti perbaikan |
|---|---|
| Sebelum | Lonjakan volume M5 diterima dengan ≥12 bar sekitar; segmen DST diberi `VERIFIED` dalam ±200 hari dari sampel; laporan cukup cocok dengan hash buatannya sendiri; `BarClockEvidenceAdapter` menerima timeline apa pun |
| Akar penyebab | **TERBUKTI pada review #230 (K-05):** verifikasi hanya memeriksa konsistensi internal, bukan asal sampel atau reproduktibilitas timeline |
| Perbaikan | `src/katarina/research/bar_clock_evidence.py`: 24 bar (12+12) wajib; segmen `VERIFIED` hanya dengan sampel di dalamnya; sampel wajib di kalender (`source_url` https) dengan `bars_sha256`; `verify_report_body` menghitung ulang hash dan timeline; adapter menerima laporan, bukan timeline. `scripts/research/export_dev_bars.py` disesuaikan |
| PR / commit | [#230](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/230) squash `93a2c67e84b388fb63ed2af12641449035a1744b` |
| Bukti tes | 15 tes WP8c termasuk timeline tulisan tangan/di-hash ulang, sampel di luar kalender, tepi data; unit/static/integration OK lokal; GitHub Body/Ubuntu/Windows PASS pada HEAD `2aa658b`; manifest MATCH |
| Deployment | Tidak dilakukan (alat riset manual) |
| Sisa risiko | `config/research/us_release_calendar.csv` masih header saja; belum ada CLI pembuat sampel dari bar M5 nyata. Sampai keduanya ada, ekspor development tetap ditolak |

## RH-004 — Profil spread WP10a: parser ketat dan basis jam

**Tanggal:** 30 Oktober 2026 WIB
**Status:** **Kode riset MERGED + CI PASS**; belum dijalankan di VPS.

| Aspek | Bukti perbaikan |
|---|---|
| Sebelum | Baris tick rusak dilewati diam-diam; hari arsip sebelum WP12 (jam server) ikut dihitung; quote per menit = baris terakhir, bukan timestamp terakhir; SQLite dibuka tanpa `query_only` |
| Akar penyebab | **TERBUKTI pada review #231 (K-06)** |
| Perbaikan | `research/context_export.py` `iter_verified_ticks` menolak baris rusak (`TICK_FILE_MALFORMED`); `research/spread_profile.py` membaca `server_shift_hours`, mengecualikan hari NULL ke `excluded_sources`, memilih timestamp terakhir per menit, URI `mode=ro` + `PRAGMA query_only=ON` |
| PR / commit | [#231](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/231) squash `ccdaec2d7b080d1df56173269ac9847dee103f60` |
| Bukti tes | Tes baru baris rusak dan hari pra-WP12; 21 tes spread/context OK; GitHub Body/Ubuntu/Windows PASS pada HEAD `ca22cfc`; manifest MATCH |
| Deployment | Tidak dilakukan |
| Sisa risiko | Profil hanya deskriptif dari data forward sejak 28 Okt; bukan bukti biaya final |

## RH-003 — Koreksi baseline biaya sisi acak dan validasi swap WP10b

**Tanggal:** 30 Oktober 2026 WIB  
**Status:** **Kode riset MERGED + CI PASS**; belum diterapkan/diuji di VPS, tidak ada klaim profitabilitas atau kelulusan Tahap 0/1.

| Aspek | Bukti perbaikan |
|---|---|
| Sebelum | Pembanding `random_side_same_timing.expected_expectancy_r` mengabaikan swap sisi acak ketika swap BUY ≠ SELL; biaya validasi lama belum menghitung swap rollover dan sensitivitas biaya |
| Akar penyebab | **TERBUKTI pada review PR #225:** perhitungan ekspektasi baseline semula mengambil `cost_r(trade)` dari sisi trade asli; perubahan tes timeout integrasi juga tidak terkait WP10b |
| Perbaikan | `src/katarina/research/validation.py`: baseline biaya BUY/SELL 50/50, swap long/short, rollover 17:00 New York termasuk DST/triple Rabu, sensitivitas 1,5×/2×; memakai ulang `_nth_sunday` dari `operations/data_health.py`. Perubahan timeout `tests/integration/test_unified_owner_surface.py` dipulihkan; tes `tests/unit/research/test_validation.py`, protokol biaya dan manifest diselaraskan |
| PR / commit | [WP10b #225](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/225) **merged**, squash `8cc3d677a883ff638f4360b24c3d8f7dc64cef18` |
| Bukti tes | GitHub Actions run `40939671190`: **Body PASS, Ubuntu PASS, Windows PASS**; manifest berubah bersama kode, tidak ada berkas trading/promosi yang disentuh |
| Deployment | **Tidak dilakukan**; VPS, broker, observer dan data privat tidak diakses |
| Sisa risiko | Nilai swap, spread, slippage dan komisi broker nyata belum dikalibrasi; hasil validasi strategi/holdout tidak otomatis menjadi positif; LIVE OFF dan Risk Governor tetap |

## RH-001 — File snapshot observer terkunci oleh Desktop Commander

**Tanggal:** 29–30 Oktober 2026 WIB  
**Status:** **Perbaikan kode MERGED + diterapkan pada VPS pengujian + smoke test awal LULUS**; observasi 10 hari bursa **BELUM LULUS**.

| Aspek | Bukti perbaikan |
|---|---|
| Sebelum | Observer berulang kali `BLOCKED` oleh `PermissionError` pada tahap `PUBLISH`; `latest.tmp` tertinggal, `latest.json` tidak diperbarui |
| Akar penyebab | **TERBUKTI:** pembukaan eksklusif `latest.json` ditolak karena dipakai proses lain; Windows Restart Manager mengidentifikasi Node.js **PID 3580**, child layanan **Desktop Commander akun kedua**, sebagai pemegang handle |
| Pemulihan operasional | Restart terkendali layanan Desktop Commander kedua melepaskan handle; pembukaan eksklusif kembali berhasil. Observer resmi dijalankan lewat `Katarina-Readonly-Observer`, bukan worker pengganti |
| Perubahan kode | `src/katarina/monitoring/snapshot_io.py`: durasi retry untuk konflik sementara diperpanjang, tetapi penulisan tetap `source.replace(target)` **atomik** dan izin permanen tetap fail-closed. `tests/unit/test_snapshot_io.py`: lima tes kasus retry, kegagalan permanen, dan galat lain |
| PR / merge | [#221](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/221) merged `e8031a4`; manifest rilis diselaraskan lewat [#222](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/222) merged `64497b5` |
| Bukti tes | CI Body/Linux/Windows kedua PR hijau; di VPS `test_snapshot_io.py` **5/5 PASS**; verifikasi manifest deployment **MATCH 304/304** |
| Deployment terverifikasi | Observer dihentikan secara anggun (`continuous.stop`, `STOPPED / OWNER_STOP_REQUEST`), checkout VPS di-`git pull --ff-only` ke `main` **`64497b5`**, manifest cocok, task resmi dijalankan ulang pada 29 Oktober 23:59 WIB |
| Bukti observasi awal | Setelah handle dilepas tetapi sebelum pembaruan: **14/14** siklus sukses; setelah kode baru terpasang: **3/3** siklus sukses, **5 simbol**, **0 order**, heartbeat dan snapshot diperbarui; `latest.tmp` tidak tertinggal |
| Pembatas hasil | Bukti tersebut hanya membuktikan **pemulihan dan stabilitas awal**, bukan bebas gagal selamanya, bukan 10 hari bursa lengkap, dan bukan izin trading |
| Pencegahan | Jangan membiarkan reader Desktop Commander memegang handle `latest.json` terus-menerus; inspeksi berkala memakai `continuous-status.json` atau shell baca-sekali. Uji kebocoran handle bila terulang |
| Tindak lanjut yang masih terbuka | Lanjutkan evaluasi hari bursa/simbol sesuai roadmap Tahap 0; bila muncul lock lagi, buka insiden baru atau tambahkan bukti di sini tanpa menutupi gap forward |

**Rujukan bukti utama:** [#221](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/221), [#222](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/222), status operasional di [PROJECT_STATUS.md](PROJECT_STATUS.md).

## RH-002 — Normalisasi timestamp tick broker MT5 (WP12)

**Tanggal penerapan:** 28 Oktober 2026 pukul 16:57 UTC  
**Status:** **Perbaikan WP12 diterapkan**; verifikasi lintas perubahan broker/DST dan evaluasi data setelah cutoff (**WP13**) masih **BELUM SELESAI**.

| Aspek | Bukti perbaikan |
|---|---|
| Sebelum | Timestamp tick MT5 menggunakan waktu server broker; quote observer terbaca seolah-olah berumur sekitar 3 jam dan pengarsipan tick berpotensi salah basis waktu |
| Perubahan | WP12 mengonversi tick dan jendela waktu dengan offset server broker yang terbukti, menolak basis waktu ambigu, dan menandai data campuran sebagai gap sesuai aturan data |
| PR / deployment | [#204](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/204); kode WP12 termasuk dalam `main` `18e2515` yang diterapkan ke VPS 28 Oktober 16:57 UTC |
| Bukti | Laporan proyek mencatat quote kembali merepresentasikan harga terkini setelah WP12; regresi legacy, arsip dan Windows tersedia pada PR/CHANGELOG |
| Sisa risiko | Quote basi akhir pekan, validasi offset independen terikat broker, pergantian DST, migrasi broker/VPS, dan audit Tahap 0 `--since` masih bagian **WP13, PR #219** (belum di-merge pada pemeriksaan 29 Okt) |
| Batas data | Data forward harga sebelum 28 Oktober 16:57 UTC **tidak dihitung** sebagai bukti harga Tahap 0; backfill tidak boleh menggantikan observasi forward |

**Rujukan:** [#204](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/204), [#219](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/219), [ROADMAP.md](ROADMAP.md) Tahap 0.

---

**Konvensi:** entri terbaru di atas; ID tetap (tidak didaur ulang). Untuk insiden baru yang belum diperbaiki, buat tugas di roadmap/status **bukan** entri perbaikan yang diklaim tuntas.
