# KATARINA AI — Perintah penutupan kendala untuk Claude
**Ditetapkan oleh Owner melalui Yura (Project Manager) · 3 November 2026**

> **Tujuan tunggal:** tutup kendala Katarina AI v0.1 yang sudah ada, **bukan membangun fitur atau strategi baru**. Dokumen ini adalah **instruksi siap dikirim kepada Claude**; keberadaannya di GitHub **tidak berarti sesi Claude berjalan atau telah mengakui tugas**. Baca `CLAUDE.md` dan `docs/ROADMAP.md` bagian 1–7 sebelum bertindak.

**Aturan sumber kebenaran:** `docs/ROADMAP.md` menetapkan kriteria/gate, `docs/PROJECT_STATUS.md` berisi snapshot operasional, `docs/REPAIR_HISTORY.md` mencatat **perbaikan yang benar-benar selesai**, dan [Issue #251](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/251) menjadi tempat laporan eksekusi Claude. [Issue #262](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/262) adalah manager board; [Issue #255](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/255) adalah blocker data/host riset. Dokumen ini adalah **antrian penutupan kendala**, bukan roadmap kedua atau status live.

## 0. Perintah pembuka untuk Claude (salin langsung)

> **Claude, kerjakan penutupan semua kendala Katarina AI dalam dokumen ini, satu per satu, tanpa menambahkan fitur atau strategi.** Mulai dengan ACK di Issue #251 berisi identitas sesi, SHA aktual tiap branch, status CI terbaru, ruang lingkup yang bisa dilakukan, dan bukti akses. Audit masalah, lakukan **perbaikan kode/test/dokumen hanya pada branch isolasi/PR yang sesuai setelah aku menginstruksikan eksekusi**, jalankan tes serta CI, lalu laporkan tiap kendala sebagai **CLOSED_VERIFIED** atau **BLOCKED dengan bukti yang hilang**. Jangan hanya membuat rencana; sertakan diff, file:line, commit SHA, output tes, dan review yang nyata. Jangan klaim review independen dari komentar manajer. **Dilarang merge ke main, deploy/restart VPS, mengeksekusi script di MT5, mengirim order, mengubah status Stage 0 historis, memindahkan data rahasia, membuka holdout, atau mengaktifkan DEMO/LIVE tanpa persetujuan Owner yang terpisah.**

## 1. Snapshot dasar yang sudah diverifikasi — jangan kerjakan ulang tanpa alasan

| Bukti/pekerjaan | Kondisi | Batas klaim |
|---|---|---|
| [PR #269](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/269) | **MERGED ke branch PR #265** | Belum merged ke `main` |
| [PR #271](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/271) | Commit `37bbe7d242ce642e37199457f3a976dbf327de18`; **Ready for Review**, CI Body/Ubuntu/Windows **3/3 PASS**; perbaikan test Stage 0 (focused 7/7) dan manifest **MATCH 317/317**, 57/57 focused tests PASS, promotion gate PASS | Bukan hasil APPROVED reviewer atau bukti deploy |
| [PR #272](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/272) | Dokumentasi audit disanitasi, 2 berkas pada snapshot awal, CI **3/3 PASS setelah retry Windows**; review Yura hanya COMMENTED | PR masih terbuka. **Perubahan dokumen ini akan memicu CI ulang**, cek HEAD terbaru |
| [PR #273](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/273) | Diagnostik sesi broker dan simulasi per simbol, CI **3/3 PASS**, 10/10 tes lokal PASS, MQL5 compile **0 error/0 warning** | Draft, belum ada bukti jadwal broker dari eksekusi script |
| VPS produksi, snapshot 3 Nov 20:11 WIB | Checkout `64497b5`, satu observer aktif 5 simbol, status WAITING, heartbeat berjalan, 0 error beruntun, 0 order, **LIVE OFF** | Versi aktif **berbeda** dari kandidat, jangan sinkron otomatis |
| MT5 | `KatarinaBrokerSessionProbe.mq5/.ex5` **sudah disiapkan** di `MQL5/Scripts` milik terminal aktif, hash sumber/build cocok | **BELUM DIJALANKAN** dan belum menghasilkan jadwal asli broker |
| Worktree kandidat terpisah | `C:\Katarina\_release_candidate_v01_20261103` checkout bersih pada `37bbe7d`, manifest dan 57 tes lulus; produksi tidak disentuh | Belum deploy, belum backup/rollback penuh |

**Catatan data Stage 0 (snapshot audit read-only 3 Nov):** sejak `2026-10-28T16:57:00Z` (WP12), ada **4.339 counted cycles, 4.203 OK, 123 SOME_SYMBOLS_WITHOUT_QUOTE, 12 BROKER_CLOCK_NOT_VERIFIED, 1 LOCAL_CONNECT_FAILED**. Sukses **96,87%** (kurang dari 98%). **128/136** kegagalan bertepatan dengan jendela satu jam tanpa tick XAUUSD.vx/NAS100.vx (21:00 UTC pada 28/29 Okt, 22:00 UTC pada 2 Nov). Korelasi **bukan** bukti sesi tutup, bukan alasan menghapus gagal clock, dan bukan PASS Tahap 0. Jendela WP15 awal 45 menit juga **tidak otomatis menjelaskan jeda 60 menit**.

## 2. Antrean perbaikan wajib, satu kendala hingga benar-benar tertutup

### K-01 · P0 — Closeout kode integrasi dan temuan reviewer
**Claude kerjakan sekarang (tanpa MT5):** bandingkan exact HEAD [#265](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/265) `9204e54f284abc5d8fd55358f6bf3fd542d0eea7` dengan fix [#271](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/271) `37bbe7d`. Verifikasi dua temuan P1 Claude sebelumnya: **WP14 hash/path audit verdict harus fail-closed**, dan **SELL bid/ask simulator**; cek causal M5 closed-bar/next-open, no-lookahead, biaya, snapshot, idempotensi, serta no-order. Lakukan review ulang pada **HEAD terakhir**, bukan review commit lama.
**Selesai jika:** setiap temuan P0/P1 ada file:line, tes adversarial, FIXED/OPEN beserta PR jika diperlukan; CI Body/Ubuntu/Windows lulus di SHA final; review formal independen berlaku untuk SHA tersebut. Bila masih gagal, **perbaiki dalam branch/PR**, jangan tutup dengan penjelasan saja.
**Ketergantungan:** bebas dari bukti broker untuk pengujian kode; tidak boleh merge produksi tanpa approval.

### K-02 · P0 — Jam broker dan jadwal quote/trade per simbol
**Claude kerjakan sekarang:** audit mekanisme `SymbolInfoSessionQuote` vs `SymbolInfoSessionTrade` dalam [#273](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/273), dan periksa kode rollover di `src/katarina/intelligence/operations/observation_ledger.py` serta `data_health.py`. Tambah/perbaiki **tes yang diperlukan**, bukan fitur: DST AS, jam server broker, sesi lintas tengah malam, Jumat/akhir pekan, holiday, pergantian simbol, quote berbeda forex/metal/index, missing/expired evidence. Jangan menyamakan timeout/no ticks dengan closed session.
**Selesai bagian kode jika:** kandidat aturan **per-symbol** fail-closed, evidence missing = **UNVERIFIED/NOT_MET**, tanpa backfill; seluruh tes deterministik dan review lulus.
**BLOCKED bagian data asli sampai:** Owner mengizinkan **eksekusi satu kali** script read-only di terminal MT5 yang sudah ada dan log sesi nyata divalidasi privat. Izin pemasangan file sebelumnya **bukan izin eksekusi**. Hanya sesudah itu boleh diusulkan tanggal efektif UTC **ke depan**; perubahan kebijakan perlu persetujuan Owner.

### K-03 · P0 — Bukti waktu broker independen dan integritas arsip tick
Audit sumber clock server-specific, interval valid, hash provenance, DST dan bukti host clock tepercaya; cek lima symbol-day `GAP` pada 30 Okt ketika broker shift berubah. Jangan pernah membuat evidence dari voting quote sendiri lalu menandainya independen.
**Selesai jika:** verifier fail-closed untuk missing/corrupt/expired/wrong-server evidence, uji GAP dan reconciler PASS dengan sumber asli yang bisa diaudit; atau laporkan **BLOCKED_SOURCE_REQUIRED** lengkap dengan sumber/bukti yang harus diperoleh.

### K-04 · P0 — Pemulihan observer dan kelulusan Stage 0
Audit `--since` terhadap cutoff WP12, satu observer kanonis, 0 order, quote/tick reconciliation, pemulihan tanpa login/restart, **3 recovery pasca-cutoff** dan **10 hari bursa berturut-turut** dengan sukses **≥98%**. Boleh menulis/fix tes dan skrip health report **di branch terisolasi**.
**Selesai bagian kode jika:** pemeriksaan gagal-terbuka tertutup dan tes lengkap; **Stage 0 hanya CLOSED_VERIFIED bila bukti lapangan memenuhi seluruh gate**. Jangan memotong masa pengamatan, memodifikasi ledger, menghapus failure, atau menganggap 10 unit tests sama dengan 10 hari bursa.

### K-05 · P0 — Konsistensi rilis GitHub–VPS, backup, rollback
Audit branch `main`, dependensi #265/#269/#271, manifest 317/317 dan `promotion_gate`. Susun checklist snapshot SQLite yang konsisten **termasuk WAL**, tick gzip, recovery task scheduler, single MT5, smoke test, batas RAM VPS 2 GB serta rollback yang bisa dibuktikan. Pastikan file untracked lokal `docs/governance/MASTER_BLUEPRINT_GOVERNANCE_DRAFT.md` tidak terhapus saat sinkronisasi.
**Selesai preflight jika:** manifest/gate/CI/test pada SHA kandidat cocok, seluruh langkah backup/rollback mempunyai command, bukti dan titik abort jelas. **Deploy tetap BLOCKED** hingga approval Owner, review, backup tervalidasi dan jadwal aman. Jangan menjalankan backup besar, restart, kerja database, atau merombak runtime tanpa izin.

### K-06 · P1 — Review dan perapian PR/dokumentasi
Review #272, #273, dependensi #265/#271, perhatikan #269 sudah terintegrasi pada branch saja. Periksa `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/REPAIR_HISTORY.md` dan branch/PR lama; tandai redundant/stale **tanpa menghapus**. Telusuri flaky CI Windows `tests/unit/test_agent_dashboard_client.py::test_failed_or_missing_auth_clears_previously_valid_evidence` (Node.js subprocess timeout 20 detik; retry PASS); usulkan perbaikan minimal dengan tes bila terbukti.
**Selesai jika:** keputusan KEEP/MERGE_AFTER_APPROVAL/CLOSE_SUPERSEDED untuk tiap PR, reviewer independen untuk SHA terakhir, tidak ada dua status kanonis dan tidak ada secret/raw broker data di GitHub. **Jangan menggabungkan PR hanya karena CI hijau**.

### K-07 · P1 — Validasi strategi BUY/SELL dan backtest sah
Audit kode empat setup riset yang sudah ada (termasuk pullback/liquidity sweep/Fibonacci/market structure) serta spread, slippage, commission, swap, equity/risk, no-lookahead, closed bars, out-of-sample, holdout lock dan jumlah sampel. **Jangan menambahkan strategi baru.**
**Selesai bagian kode jika:** tes deterministic dan data provenance/validation gate aman. **BLOCKED bagian hasil broker** bila historis M5 tepercaya dan **Windows research host terpisah** belum tersedia ([Issue #255](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/255)). Tidak boleh menjalankan backtest berat atau MT5 kedua di VPS produksi, dan tidak boleh mengarang winrate, PF atau DD.

## 3. Tata cara eksekusi dan laporan Claude
1. **ACK nyata:** verifikasi akses repo, lokasi branch/HEAD aktual, bacaan `CLAUDE.md` dan roadmap; laporkan di #251. Jika HEAD bergeser, **berhenti dan perbarui referensi** sebelum mereview; jangan asal cherry-pick.
2. **Satu kendala per langkah:** reproduksi → tentukan severity dan bukti → perbaiki hanya jika aman dalam branch PR terkait → tambahkan tes regresi → jalankan lint/static/unit/integration/CI yang relevan → review independen → status dengan bukti. **Jangan membuka PR baru untuk masalah yang sudah diperbaiki** atau membuat commit tak terkait.
3. **Laporan tiap K-xx:** `status CLOSED_VERIFIED / CODE_FIXED_PENDING_REVIEW / BLOCKED_EVIDENCE / NOT_STARTED`, root cause, daftar file:line berubah, commit SHA, perintah dan hasil tes, risiko sisa, keputusan Owner yang diperlukan, serta tautan PR/CI.
4. **Dokumentasi:** update satu komentar rangkuman pada #251 saat selesai batch; Yura mempertahankan tracking ringkas di #262. Perbaikan nyata **baru** masuk `docs/REPAIR_HISTORY.md` setelah review/acceptance; perubahan gerbang Owner wajib dicatat di `CHANGELOG.md` dengan izin. Jangan membuat roadmap paralel, laporan status palsu, atau push raw log/token/tick/SQLite.
5. **Pemisahan gerbang:** CODE PASS ≠ REVIEW APPROVED ≠ DEPLOYED ≠ STAGE0 PASS ≠ STRATEGY PROFITABLE ≠ DEMO/LIVE AUTHORIZED.

## 4. Pembatas keputusan Owner — jangan dijalankan otomatis
- **Izin eksekusi (diperbarui):** Owner memberikan **mandat luas untuk audit, perbaikan, penghapusan, pemindahan, penggabungan, dan perampingan kode/file di repository Katarina AI** menurut Bagian 5 di bawah. Tidak perlu meminta persetujuan untuk setiap file **sepanjang bukti penggunaan dan tes aman dipenuhi**. Ini tetap **bukan** izin mengubah aturan Stage 0 historis, merger melewati gate repo, mengeksekusi script MT5, restart/deploy VPS aktif, menghapus data operasional atau trading.
- **Sesi broker:** perlu persetujuan khusus untuk menjalankan script yang **sudah terpasang** pada terminal aktif; hasil mentah tetap di VPS privat.
- **Release:** perlu approval reviewer pada SHA final, backup/rollback tervalidasi, bukti clock independen, dan keputusan go/no-go Owner.
- **Trading:** level riset read-only tetap default; DEMO/LIVE, risk governor dan holdout tidak boleh diubah.
- **Bukti waktu/data:** syarat 10 hari, 98%, 3 recovery, 0 order, dan data OOS tidak bisa dipercepat lewat manipulasi konfigurasi atau penghitungan masa lalu.

**Definition of done keseluruhan:** semua K-01 sampai K-07 berstatus **CLOSED_VERIFIED** sesuai scope, atau **BLOCKED_EVIDENCE** dengan bukti eksternal yang nyata dan keputusan pemilik. Claude wajib melaporkan **apa yang belum selesai**, bukan mengklaim Katarina siap live hanya karena semua CI lulus.

## 5. MANDAT TAMBAHAN OWNER — Claude boleh merapikan codebase secara menyeluruh (3 November 2026)

**Mandat ini lebih baru daripada pembatasan tugas administrasi awal pada dokumen ini, khusus untuk pekerjaan _coding dan cleanup repository_.** Owner ingin pekerjaan teknis dibereskan sampai Katarina **rapi, terarah, mudah ditelusuri ketika error, dan siap melanjutkan tahap berikutnya**. Claude **tidak perlu meminta izin satu per satu** untuk perubahan kode/file dalam cakupan di bawah. Perintah ini **tidak otomatis menjalankan sesi Claude**; Owner akan meneruskannya kepada Claude.

### 5.1 Hak tindakan Claude — DIPERBOLEHKAN

1. **Menghapus file** yang terbukti tidak dipakai, duplikat non-kontrak, stale, atau usang; **memindahkan/rename** file ke lokasi yang lebih logis; menggabungkan modul yang memiliki fungsi tumpang-tindih; memecah file/fungsi yang terlalu rumit; dan merapikan dependensi, import, CLI, konfigurasi, dokumentasi, serta tes. Riwayat perubahan wajib dapat di-rollback di Git; jangan membuat folder arsip baru.
2. **Memperbaiki bug serta masalah coding yang ditemukan sepanjang audit** termasuk error handling, race condition, penanganan timezone/DST, path/portabilitas, integritas data, fail-closed, performa dan keterbacaan. Boleh menambah **tes, tooling audit, lint, dokumentasi, dan adapter kompatibilitas seperlunya** untuk memastikan kualitas — **bukan menambah strategi atau fitur trading baru**.
3. **Mengubah banyak file terkait dalam satu perbaikan** apabila perubahan itu memang diperlukan untuk menyelesaikan satu masalah lintas modul; pecah ke PR kecil per kelompok tanggung jawab agar akar perubahan dan regresi dapat diperiksa.
4. **Menyusun standar penelusuran error** yang konsisten di runtime, riset, CLI, logs dan tests dengan memakai **reason code stabil yang sudah ada** (misalnya protokol `protocol/reason_codes_v1.json` tidak boleh diubah artinya). Untuk setiap error, tunjukkan **ID temuan, area, severity, alasan, sumber bukti, timestamp UTC, simbol/cycle jika ada, referensi tes dan commit**. Pertahankan format/API lama bila masih digunakan; hindari kebocoran data privat.
5. **Menentukan sendiri urutan perbaikan teknis** berdasarkan dampak serta ketergantungan; tidak wajib menunggu instruksi Owner tiap commit, dengan syarat tidak melewati batas keamanan dan gate rilis.

### 5.2 Syarat wajib sebelum menghapus atau memindahkan file

- Awali dengan **inventaris HEAD `main` aktual**, bandingkan VPS dan repo serta status issue/PR yang **sudah merged**. Audit lama pada SHA sebelumnya bukan kebenaran terbaru.
- Cek pemanggil langsung maupun **dinamis**: import, `__init__`, stage registry, reflection, config `config/stages/stageNN.json`, Windows scheduled tasks, launcher .bat/.ps1, GitHub workflows, scripts, contract/protocol, website, dokumentasi, tests dan release manifest.
- Untuk masing-masing usulan hapus, catat **file / alasan tidak digunakan / bukti pencarian / dependensi / tes / rollback commit**. Jika tak dapat dibuktikan aman, labeli `UNVERIFIED_KEEP`, **jangan hapus**. File yang hanya dipakai tes **belum otomatis tidak berguna**.
- **Jaga kontrak arsitektur** `domain`, `entrypoints`, `ports`, tombstone `run_market_brain.py`/`run_decision_brain_v3.py` dan risk controls sesuai `docs/maintenance/CLEANUP_PLAN.md` sampai pengujian membuktikan perubahan kontrak aman dan keputusan Owner yang relevan diberikan. Duplikasi hash saja bukan bukti aman dihapus.
- Peta awal audit manager: **894 file terlacak** pada snapshot, **575 file Python parse AST tanpa error**, **43 lokasi broad `except Exception` di source/script** yang perlu triase, **9 file dengan rujukan `C:\KatarinaDev`**, **3 paket kontrak** tidak terjangkau secara statis. Ini **kandidat pemeriksaan**, bukan daftar file yang harus dihapus. Pastikan hitungan diulang pada HEAD terakhir.
- Area `C:\Katarina\state`, SQLite + WAL/SHM, arsip tick, log bukti, backup, private config, secrets, akun MT5, dan file governance lokal **di luar mandat hapus/pindah otomatis**. Worktree/staging VPS lama hanya diinventaris dan diusulkan untuk cleanup terpisah, bukan langsung dihapus.

### 5.3 Guardrail yang tidak dapat dilewati secara implisit

**Mandat luas _coding_ bukan mandat tanpa batas untuk tindakan operasional/finansial.** Tidak boleh mengirim order, menyalakan DEMO/LIVE, mengubah Risk Governor, promotion lock, holdout, memanipulasi data historis, menurunkan gate Stage 0 (10 hari/98%/3 recovery/0 order), menjalankan script MT5 di terminal produksi, menghapus database/bukti, merestart/deploy VPS, atau merombak keputusan tetap Owner tanpa izin Owner khusus.

Untuk codebase: lakukan commit/PR menurut `CLEANUP_PLAN.md`; semua perubahan behavioral harus dijelaskan, dites, dan direview. **Jangan merge otomatis tanpa syarat CI dan review yang berlaku di repository.** Tidak boleh force-push atau memutus history. **Jangan menganggap CI PASS = siap trading.**

### 5.4 Tahapan eksekusi dan bukti yang wajib ditinggalkan

| Gelombang | Pekerjaan | Bukti selesai |
|---|---|---|
| A — Baseline dan peta | SHA aktif, status GitHub/VPS, dependency graph, audit error/konfigurasi, daftar KEEP/REFACTOR/DELETE_CONFIRMED/PROTECTED | Inventaris bertanggal dan prioritas P0/P1/P2 |
| B — Buang yang terbukti tak berguna | Hapus/rename/move file dan dependency yang tidak dipakai, perbarui references, release manifest dan `RUNTIME_MODULE_MAP.md` | PR diff per file + bukti no-regression + kemungkinan rollback |
| C — Sederhanakan kode | Pecah file/fungsi terlalu kompleks, konsolidasikan implementasi ganda, perbaiki broad exception yang menelan error, path lama, CI flaky bila terbukti | Tes RED/GREEN, code review, kontrak dan perilaku tetap benar |
| D — Penelusuran error | Selaraskan pesan dan kode alasan yang sudah ada, tabel area/severity/tes, korelasi log → sumber kode → perbaikan | Satu cara efektif untuk menemukan P0/P1/P2 tanpa mengumbar rahasia |
| E — Gate akhir | Unit + static + integration, Body/Ubuntu/Windows, manifest MATCH, promotion gate, review final; perbarui dokumentasi canonical | Ringkasan sebelum/sesudah, PR/SHA, daftar CLOSED/OPEN/BLOCKED, keputusan `READY_FOR_NEXT_STAGE` atau `NOT_READY` |

**Kriteria selesai audit/perapian:** kode lebih ramping dan mudah dicari, seluruh penghapusan dapat dibuktikan aman, jalur runtime dan tes koheren, tidak ada regressions P0/P1, reason/error terpetakan, CI final dan gate manifest lulus, dokumentasi dan status versi benar. Jika gate terpenuhi, laporkan **`CODEBASE_READY_FOR_NEXT_STAGE`** dan rekomendasi tahap lanjutan sesuai `docs/ROADMAP.md`. Jika masih ada blocker eksternal (bukti jam broker asli, host M5 riset terpisah, 10 hari Stage0, 3 recovery), laporkan **`CODEBASE_CLEAN_BUT_STAGE_GATE_BLOCKED`**, jangan mengklaim Stage0/strategi/live telah lulus.

**Laporan Claude ke [Issue #251](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/251)** dan ringkasan ke [Manager Board #262](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/262): `ID | prioritas | file:line | alasan | aksi delete/move/refactor/fix | bukti referensi | SHA PR | tes | hasil | sisa blocker`. Catat perbaikan yang telah terverifikasi ke `docs/REPAIR_HISTORY.md`; perbarui `CLAUDE.md`, `CHANGELOG.md`, dan `docs/PROJECT_STATUS.md` sesuai peran dokumennya. Setelah itu **hentikan pekerjaan perapian dan minta keputusan Owner untuk memulai tahap berikutnya**, bukan menambah fitur tanpa arah.
