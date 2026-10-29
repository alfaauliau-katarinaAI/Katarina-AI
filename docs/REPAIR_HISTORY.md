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
