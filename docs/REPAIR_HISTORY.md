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

## RH-013 — Coding gate KAT-CG aktif, safe cleanup, dan tiga bug yang ditemukan gate

**Tanggal:** 4 November 2026 WIB
**Status:** **MERGED + CI PASS** (#283 gate/cleanup, #284 S0 + fix peta modul, #285 WP6 preflight, #286 tes P0). Alat repo/CI, sehingga tidak perlu deploy VPS. Launcher WP6 dan perubahan task **BELUM DITERAPKAN** (perlu izin Owner).

| Aspek | Bukti perbaikan |
|---|---|
| Sebelum | Tidak ada gate yang menghentikan perubahan rusak sebelum test suite, dan tidak ada pencatatan error berulang. Manifest `MATCH` tidak diwajibkan CI. Cleanup cache dilakukan manual. Launcher observer produksi tidak ada di Git |
| Perbaikan | `scripts/governance/code_change_gate.py` (KAT-CG-00..05, fail-fast, fingerprint + ledger `REPEATED_FAILURE_NEEDS_ROOT_CAUSE` exit 3). `scripts/governance/safe_cleanup.py` (`--check`/`--dry-run`/`--apply-safe`, allowlist, fail-closed). Body CI: langkah KAT-CG-00/01, KAT-CG-03 (manifest `MATCH` wajib), job agregat KAT-CG-04. Hook opsional `ops/git-hooks/pre-commit`. Panduan `docs/maintenance/CODING_GATE.md` |
| Bug ditemukan tes/gate (TERBUKTI) | (1) `safe_cleanup` crash `CalledProcessError` di folder non-root worktree → kini `NOT_A_GIT_WORKTREE_ROOT`. (2) Tes cleanup memakai `str(Path)`, sehingga di Windows kunci berisi backslash (KeyError, CI Windows #283) → `as_posix()`. (3) `runtime_import_map` menghitung nama modul yang disimpan sebagai data oleh alat analisis sebagai pemakaian (D=0 setelah G1; lima modul persepsi tampak dipakai script) → `ANALYSIS_ONLY`; tes RED `'A' != 'D'` pada kode lama, GREEN sesudah perbaikan |
| Bukti CI negatif | Commit `ab548622` (JSON rusak disengaja): Body merah di `KAT-CG-01` dengan `KAT-ERR-90d3601c P2 JSON_INVALID config/ci_negative_proof.json:4`; test suite tidak berjalan; `KAT-CG-04` merah. Revert `d5136d74`: semua hijau |
| Bukti cleanup | Fixture: dry-run tidak mengubah apa pun. Apply hanya menghapus allowlist; item terlacak, state/backups/private/logs/docs-governance, SQLite/WAL, arsip tick, symlink keluar, path escape, `main`, produksi, dan worktree yang berubah ditolak; idempotent. Worktree dev nyata: 54 target / 668 berkas cache dihapus, index Git dan berkas terlacak tidak berubah, ledger `build/code-gate` utuh, run kedua menghapus 0 |
| Bukti tes | Lokal `code_change_gate.py --full` PASS di setiap PR (unit ±1.490, static 98, integration 222; manifest MATCH; promotion gate PASS). CI Body/Ubuntu/Windows + `KAT-CG-04` PASS pada SHA final #283–#286. Di Windows, tes parse PowerShell dan symlink benar-benar berjalan |
| Batas hasil | Gate mencegah promosi kode yang terdeteksi salah, tetapi tidak menjamin semua bug tertangkap. Ledger perulangan bersifat lokal (CI per-run). CI PASS ≠ Tahap 0 PASS ≠ izin DEMO/LIVE |
| Rollback | `git revert` per merge commit; tidak ada state/data yang tersentuh |
| Sisa risiko | 49 kode P0 belum diuji secara literal (broker calibration/recovery, adapter cloud/dialog, demo_execution) |

## RH-012 — Perapian codebase menyeluruh (mandat Owner 3 Nov): jalur MT5 lama, DST tunggal, CI flaky, indeks reason code

**Tanggal:** 3–4 November 2026 WIB
**Status:** **Kode MERGED + CI PASS** (B1 #279, C1 #280, D1 #281, E1 dokumen); **BELUM DEPLOYED** (VPS tetap `fd6cff16`; deploy perlu izin Owner khusus); Tahap 0 **BELUM LULUS**.

| Aspek | Bukti perbaikan |
|---|---|
| Sebelum | Repo masih menyimpan observer kedua `run_readonly_decisions.py`, yang memanggil `mt5.initialize()` langsung dan menulis ke `C:\KatarinaDev` yang sudah pensiun. Ada juga EA `KatarinaResearchScalperEA` dengan `CTrade.Buy/Sell` yang tidak dipakai, aturan DST AS/EU yang ditulis ulang di 5 modul, tes Windows `test_unified_owner_surface` yang flaky (1 dari 24 run `main`, juga di #279), dan reason code tanpa peta ke sumber/tes |
| Akar penyebab | **TERBUKTI:** sisa jalur pra-observer canonical yang tidak dihapus saat perampingan 22 Okt (tercatat di `CLEANUP_PLAN.md`). DST disalin per fitur karena belum ada modul domain. Batas socket tes 5 s lebih pendek dari durasi satu siklus observer sintetis di runner Windows |
| Perbaikan | B1: 8 berkas dihapus dengan bukti per berkas; path `C:\KatarinaDev` dilarang di `scripts/`/`src/`. C1: `src/katarina/domain/market_calendar.py` menjadi satu sumber DST, dengan tes penjaga terhadap implementasi kedua; batas tes owner surface 30 s; `observer.py` mencatat fail-closed `CLOCK_BROKER_IDENTITY_MISSING`. D1: `scripts/governance/reason_code_index.py` + `docs/maintenance/REASON_CODE_INDEX.md` (540 kode → `file:line` → tes) dan tes literal kode jam live P0. Ledger: `docs/maintenance/CODEBASE_CLEANUP_20261103.md` |
| Commit | `main` `39fc0859` (B1), `a9dc9a36` (C1), `e186d3cc` (D1) |
| Bukti tes | Ekuivalensi DST lama vs baru: 107.892 momen 1990–2100 identik. Lokal di `e186d3cc`: unit 1.468, static 80 (4 skip), integration 222 OK; hygiene/dependency PASS; promotion gate PASS; manifest MATCH 312. CI Body/Ubuntu/Windows PASS pada setiap merge (B1 Windows lulus setelah dijalankan ulang satu kali karena flaky yang diperbaiki C1; C1 dan D1 lulus pada percobaan pertama) |
| Batas hasil | Tidak ada perubahan perilaku runtime yang diharapkan. C1 menyentuh `observation_ledger`/`data_health` (dipakai observer dan health harian) dengan hasil identik; perubahan ini belum berjalan di VPS sampai deploy berikutnya. Berkas promotion lock, Risk Governor, data, ledger dan state VPS tidak disentuh |
| Rollback | `git revert` per merge commit (#279/#280/#281). VPS tidak perlu rollback |
| Sisa risiko | 62 kode P0 belum diuji secara literal (mayoritas broker/adapter; daftar di indeks). Worktree/folder lama di VPS dan 10 branch PR tertutup hanya diinventaris (lihat ledger E1); penghapusan branch diblokir proxy dan perlu dilakukan Owner/manager |

## RH-011 — Deploy WP13 jam live tepercaya ke VPS + perbaikan Stage 0 `clock_shift_stable`

**Tanggal:** 3 November 2026 WIB (deploy 15:15–15:18 UTC)
**Status:** **Kode MERGED + CI PASS + DEPLOYED di VPS + smoke test LULUS**; Tahap 0 **BELUM LULUS**. Izin Owner di sesi Claude, 3 Nov 21:50 WIB.

| Aspek | Bukti perbaikan |
|---|---|
| Sebelum | VPS menjalankan `64497b5` (sebelum WP13). Jumat 30 Okt 23:55 UTC observer menerima shift **−1** dari quote beku setelah penutupan, lalu **−8** pada 31 Okt 06:57 UTC. Akibatnya kelima hari tick 30 Okt menjadi `GAP BROKER_SHIFT_CHANGED_DURING_DAY`. `clock_shift_stable` tetap **PASS** karena hanya mengecek "dalam ±3 hari dari DST" |
| Akar penyebab | **TERBUKTI:** `infer_clock_shift` lama memilih offset dari quote tanpa jam host tepercaya dan tanpa penutupan pasar (direproduksi dengan kode `64497b5`). Kriteria Tahap 0 tidak memeriksa besar perubahan shift |
| Perbaikan | WP13 (jam live = NTP host tepercaya + ≥ 3 tick bergerak, `FX_MARKET_CLOSED` setelah Jumat 20:00 UTC) sudah ada di `main`. Tes insiden [#275](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/275). `data_health.assess`: perubahan shift hanya diterima bila dekat DST **dan** tepat 1 jam (`dst_plausible`) [#276](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/276). Integrasi #265 (WP4/WP8b/WP14/BLS + review #266/#271), guard sesi K-02 #274 → #273 |
| Commit | `main` `fd6cff16` (#265), kemudian `034f1392` (#273). VPS dideploy pada **`fd6cff16`** |
| Bukti tes | Lokal: unit 1.446, static 76 (4 skip), integration 222 OK; manifest MATCH 317; promotion gate PASS. CI Body/Ubuntu/Windows PASS pada setiap SHA yang di-merge |
| Deploy terverifikasi | Prasyarat: RAM bebas 613 MB, NTP `State=2 (Sync)` dengan umur 5.630 s, status WAITING. `continuous.stop` → `STOPPED/OWNER_STOP_REQUEST` 15:15:32 UTC. Backup `sqlite3.backup()` ke `C:\Katarina\backups\20261103-pre-fd6cff16` (`integrity_check=ok`, 9.934 siklus, SHA-256 `eb65edf7…a768`, 44 arsip tick, JSON state). `git merge --ff-only` ke `fd6cff16`; berkas untracked governance utuh; manifest **MATCH 317**. Tes jam di VPS 27 OK; `inspect_host_clock()` = `NTP_SYNCHRONIZED time.windows.com` stratum 5, skew 0,03 s. Task dijalankan ulang 15:18:12 UTC |
| Smoke | Siklus 15:18:14 dan 15:19:21 UTC `OK`, shift 2,0, 0 order; `time_basis=LIVE_FEED_CLOCK`, `shift_evidence=TRUSTED_HOST_NTP_AND_PROGRESSING_TICKS`, `clock_audit.reason=LIVE_FEED_CLOCK_VERIFIED` (3 simbol bergerak); `research_candidates` 5 baris `RECORDED` |
| Batas hasil | Jeda observer 15:14:28 → 15:18:14 UTC (±4 menit, di dalam sesi) tercatat sebagai outage; tidak diisi. Dengan kriteria baru, data sejak 28 Okt menjadi `clock_shift_stable NOT_MET` (shift palsu akhir pekan tetap tercatat; tidak dihapus) |
| Rollback | `git -C C:\Katarina\code checkout 64497b5`, restore DB dari backup dengan `sqlite3.backup()`, jalankan ulang task |
| Sisa risiko | Task observer masih `LogonTrigger/Interactive` (WP6). Probe sesi MT5 belum dijalankan (perlu GUI terminal). Bukti jam bar historis butuh host riset terpisah (#255) |

## RH-010 — Audit gabungan WP14 / WP8b / WP4: pengamanan data dan koreksi akuntansi spread

**Tanggal bukti:** 2 November 2026 (WIB) · **Status:** hanya **BRANCH RISET TERINTEGRASI**, CI 3/3 PASS; belum merged ke `main` maupun dideploy.

| Aspek | Bukti verifikasi |
|---|---|
| Gejala dan akar masalah | **TERBUKTI pada review Claude/Manager:** WP14 membuka tick relatif dari CWD, bukan state-dir, dan file ada tanpa SHA dapat dianggap PASS; simulator SELL menggunakan BID untuk exit/TP/SL serta inkonsistensi exit timeout dan penghitungan spread dua kali pada harga yang bukan mid; tes isolasi ledger saat gagal belum tercakup. |
| Perbaikan sumber | `src/katarina/intelligence/operations/data_health.py` dan `scripts/ai/check_stage0_health.py`: path tick terhadap state-dir, hash hilang -> BLOCKED, tetap fail-closed `PASS+NO_DATA != PASS`; `src/katarina/research/setups/simulator.py`: BUY entry ASK/exit BID, SELL entry BID/exit ASK, timeout dan stop, simpan mid untuk `CostModel` tanpa double-charge; tes isolasi ledger/observer. |
| PR dan SHA | [#266](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/266) `ebd358b4` masuk **hanya ke branch integrasi riset** [#265](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/265) pada merge `cd3b576d42aeb98dd8cdadbbac849cc8b568ef44`. |
| Bukti tes | CI [41478763744](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/41478763744) dan **CI final gabungan** [41480635219](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/41480635219) **Body/Ubuntu/Windows sukses**. Test tambahan membandingkan P&L ASK/BID dengan `CostModel` untuk spread entry/exit berbeda; isolasi observer 0 order. |
| Perlindungan terhadap regresi source Jules | PR #259 HEAD `ce7c4074` sesudah versi fixed `f919d5c9` mengembalikan `PASS+NO_DATA -> PASS` dan menghapus sejumlah tes penutupan SQLite Windows. Branch itu **CLOSED UNMERGED**; kode terintegrasi mempertahankan helper fail-closed dan tesnya. |
| Batas hasil | Tidak ada approval manusia untuk merge `main`, tidak ada deploy, tidak ada bukti jam M5 broker sebelum cutoff, belum ada backtest nyata, Stage0 IN_PROGRESS dan LIVE OFF. |

## RH-009 — WP15 rollover New York nonretroaktif

**Tanggal:** 31 Oktober 2026 · **Status:** KODE MERGED + CI PASS; tanggal efektif `None` (nonaktif), VPS belum dideploy.
- **Masalah/akar:** aturan sesi Stage0 memakai rollover UTC tetap dan berisiko salah saat DST; override retroaktif dalam revisi PR dinilai tidak aman pada review (terbukti dalam diff/review).
- **Perbaikan:** `stage0_session_open` dan aturan DST dengan tes batas; mempertahankan `fx_session_open` untuk histori, `--since` WP13 tetap; tidak mengubah data lama atau mengaktifkan aturan historis.
- **Bukti:** [PR #244](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/244), merge `30962e6`; CI 3/3 PASS (batch/merge didokumentasikan di [#249](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/249)).
- **Sisa risiko:** tanggal efektif future dan rollout/restart memerlukan keputusan/izin terpisah; Stage0 tidak otomatis PASS.

## RH-008 — WP13 trusted host NTP + progressive tick dan Stage0 --since

**Tanggal:** 31 Oktober 2026 · **Status:** KODE MERGED + CI PASS; belum deploy.
- **Masalah/akar:** inferensi jam broker dari quote stale/fallback berisiko UTC palsu; laporan Stage0 perlu cutoff sejak WP12 (terbukti pada audit WP13 dan review).
- **Perbaikan:** `host_clock_probe.py`, `live_clock_probe.py`, `broker_clock_alignment.py`, `observer.py`, `data_health.py` dan CLI `--since` dengan fail-closed NTP/tick, alasan gagal yang tercatat, tes negatif.
- **Bukti:** [PR #233](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/233) merge `27bf40c`; CI Body/Ubuntu/Windows PASS run `41149786169`; manifest 308 entries pada main final.
- **Sisa risiko:** NTP runtime Windows dan hubungan broker nyata wajib diverifikasi beberapa interval sesudah izin deploy; observer lama berjalan di `64497b5`, Stage0 belum lulus.

## RH-007 — WP8d alat bukti jam bar historis .vx

**Tanggal:** 31 Oktober 2026 · **Status:** KODE MERGED + CI PASS; data/hasil broker nyata belum tersedia.
- **Masalah/akar:** CLI awal memetakan canonical symbol langsung, bukan simbol broker `.vx`; provenance bar perlu deterministik (terbukti review).
- **Perbaikan:** `research/bar_clock_evidence.py` + `scripts/research/build_bar_clock_evidence.py`, mapping `.vx`, kronologi bar, hash, reject bila tidak ada konsensus.
- **Bukti:** [PR #248](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/248) merge `94c058e`; CI Body/Ubuntu/Windows PASS run `41149221348`.
- **Sisa risiko:** kalender resmi BLS di repo masih header dan bar broker asli belum dijalankan/diuji; jangan klaim dataset dev terverifikasi.

## RH-006 — WP16 keamanan OAuth status

**Tanggal:** 31 Oktober 2026 · **Status:** KODE MERGED + CI PASS; deployment belum diaudit.
- **Masalah/akar:** respons `/oauth/status` dan bind sebelumnya bisa memperluas paparan profil (terbukti review sumber).
- **Perbaikan:** `oauth_gateway/server.js` menghapus profil dari status, default loopback `127.0.0.1`; tes statis negatif.
- **Bukti:** [PR #247](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/247) merge `b720563`; CI Body/Ubuntu/Windows PASS run `41148118046`.
- **Sisa risiko:** lokasi deploy eksternal dan konfigurasi gateway berjalan perlu audit; tidak menyatakan runtime otomatis aman.

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
