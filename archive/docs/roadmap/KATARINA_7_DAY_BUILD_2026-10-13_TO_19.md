# KATARINA AI — 7-Day Build Lock
**Periode:** Selasa 13 – Senin 19 Oktober 2026 (WIB)  
**Target:** Katarina AI V1 *research release candidate*, dapat direproduksi dan siap diuji di GitHub-hosted runner.  
**Scope freeze:** Tidak menambah fitur baru di luar backlog tujuh hari ini kecuali perbaikan blocker.

## Baseline yang sudah diverifikasi pada 13 Oktober
- Head: `7e6666a40e415b9fbec839048397309e47a81e4b`.
- Autonomous Strategy Discovery V1: 34 kombinasi dieksplorasi, 3 kandidat *riset* pada data sintetis; 9 unit tests serta GitHub Body CI lulus.
- Evidence Risk Governor, shadow observer, learner dan adapter review multi-model tersedia.
- Dua panggilan model eksternal **belum terverifikasi end-to-end berhasil**.
- Profitabilitas, real broker fills, MT5 deployment/VPS terbaru **belum lulus verifikasi**; live execution tetap OFF.

## Rencana terkunci (tidak berputar)
| Hari | Tanggal WIB | Deliverable satu-satunya | Gate kelulusan | Jika gagal |
|---|---|---|---|---|
| D1 | 13 Okt | Audit integrasi, daftar blocker, freeze scope & baseline Git SHA | Satu matriks komponen + prioritas P0/P1; tidak ada perubahan VPS | Catat blocker, lanjut hanya perbaikan P0 |
| D2 | 14 Okt | Selesaikan koneksi dua *author* model eksternal GitHub Models; structured review | Artifact berisi dua respons nyata terparsing + review yang terkait SHA/receipt; izin write/order=0 | Ganti model yang tersedia jika perlu, jangan palsukan koneksi |
| D3 | 15 Okt | Import dan validasi OHLC/tick historis real terarsip ke *offline* runner; tanggal, spread, sumber | Audit sumber, UTC, duplikat, missing candles, gap dan pembagian kronologis | Jika input nyata tidak ada, blokir klaim market validation; fixture sintetis bukan pengganti |
| D4 | 16 Okt | Strategy Discovery pada data riil dan metode BUY/SELL terpisah; walk-forward + friksi biaya | Output JSON kandidat, train/validation/OOS, spread+komisi+slippage stress, leakage checks; status jujur | Candidate boleh nihil; tidak dipaksa profit |
| D5 | 17 Okt | Closed-loop improvement sandbox: propose → run tests → independent AI/code review → queue perubahan | Setiap proposal punya diff/receipt dan alasan; gagal CI otomatis ditolak; NO auto-merge/push live | Nonaktifkan agen yang gagal, simpan bukti |
| D6 | 18 Okt | Gabungkan jalur Brain → Discovery → Risk → Review → artifact; full regression | Body CI dan workflow khusus hijau, semua keputusan live=OFF, tidak ada critical blocker | Perbaiki hanya blocker release |
| D7 | 19 Okt | Freeze rilis V1-RC dan tulis final release report/operator guide | Commit SHA + tautan Actions/artifact + daftar PASS/BLOCKED + langkah uji MT5 selanjutnya | Laporkan RC **belum lulus**, jangan menyebutnya selesai |

## Definition of Done — apa arti “selesai”
1. Seluruh kode riset dan konfigurasi *reproducible* di GitHub, commit tertentu dan CI hijau.
2. AI eksternal dari dua keluarga/penyedia menghasilkan respons sungguhan yang lulus parser dan safety gate, **atau** dilabel BLOCKED jika quota/izin tidak tersedia (bukan klaim palsu).
3. Mesin mampu menghasilkan hipotesis strategi baru tanpa bergantung pada rekomendasi LLM: *genome* aturan price-action, evolusi, train/validation/OOS dan analisis friksi.
4. Setidaknya satu eksperimen berbasis data historis pasar yang sumber dan integritasnya jelas. Tanpa data itu, status **engine built, market validation blocked**.
5. Mekanisme proposal perbaikan otak tidak otomatis menerapkan strategi, mengedit produksi, merge ke main, atau melakukan trading.
6. Laporan final memisahkan **PASS / BLOCKED / NOT STARTED**, menautkan bukti, menyebut risiko dan berikutnya.

## Tidak dijanjikan minggu ini
- Profit konsisten / winrate tertentu, karena perlu data dan verifikasi yang independen.
- Trading real yang aman, MT5-VPS deployment tanpa akses dan full broker forward-test.
- Self-modifying production code yang bisa melewati review manusia.
- Memindahkan atau menghapus file VPS yang masih berjalan.

## Aturan eksekusi dan pelaporan
- **Satu pekerjaan kritis per hari**. Tidak ada penambahan tool/framework hanya karena populer.
- Gunakan GitHub-hosted runner; resource-heavy tasks di VPS tidak dijalankan.
- Tiap tugas selesai hanya jika ada commit + Actions run + artifact yang bisa diperiksa.
- Kegagalan dilaporkan spesifik dan tidak diubah menjadi status PASS.
- Pekerjaan berjalan hanya saat workflow/jalannya eksekusi memang dipicu; roadmap sendiri tidak membuat AI bekerja terus-menerus.
- Pada 19 Okt hasil dapat berupa V1-RC **PASS** atau **BLOCKED** dengan bukti, bukan janji profit.
