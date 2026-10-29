# Katarina AI — audit kelemahan dan handoff tugas Claude (30 Oktober 2026)

**Owner:** pemilik proyek; **manager:** ChatGPT/Yura; **coding GitHub:** Google Jules; **eksekusi/review independen:** Claude.  
**Jenis dokumen:** temuan, status terkini, prioritas dan acceptance untuk reviewer Claude; **BUKAN** bukti bug sudah diperbaiki, laporan profitabilitas, atau izin trading.  
**Basis audit:** repo GitHub, review kode/PR per SHA, CI dan pemeriksaan read-only VPS hingga **30 Okt 2026 05:25 WIB**. Kondisi VPS bersifat snapshot sesaat; audit ulang sebelum tindakan.

## Bacaan pertama untuk Claude

1. [Roadmap kanonis](../ROADMAP.md): aturan tetap bagian 1–7, lalu Lampiran A R0/R4/R5/R6/R7/R8/R9/R10. Jangan mengubah kriteria Owner secara diam-diam.
2. [Laporan mendalam WP13/jam MT5](WP13_CLOCK_CLAUDE_HANDOFF_20261030.md), termasuk bukti broker, kode yang pernah diperbaiki lalu regresi, dan syarat deployment.
3. [Status operasional](../PROJECT_STATUS.md); [MEETING](../ROADMAP_DISCUSSION.md) hanya keputusan tertunda; [REPAIR_HISTORY](../REPAIR_HISTORY.md) hanya perbaikan yang benar-benar sudah diterapkan dengan bukti.
4. PR aktif [#233 WP13](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/233), [#230 WP8c](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/230), [#231 WP10a](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/231). **Jangan merge PR lama #219** yang sudah digantikan.

## A. Ringkasan fakta yang diverifikasi

| Fakta | Bukti terakhir / batas klaim |
|---|---|
| Keamanan operasi | Research-only / LIVE OFF / satu observer resmi; **0 order** pada pemeriksaan VPS. Tidak ada izin mengirim order, DEMO trade, atau mengubah Risk Governor, promotion lock dan holdout. |
| VPS terkini | **30 Okt 05:25 WIB**: `Katarina-Readonly-Observer` **Running**, `continuous-status.json` **WAITING**, `cycles=298`, `successful_cycles=292`, `consecutive_failures=0`, `orders_submitted=0`, heartbeat `2026-10-29T22:24:25.607802Z`; checkout **`64497b5`**. Angka siklus bukan 10 hari bursa. |
| Degradasi sebelumnya | **30 Okt ~04:59 WIB**: `DEGRADED`, reason `BROKER_CLOCK_NOT_VERIFIED`, satu kegagalan beruntun. Pemulihan ke WAITING pada 05:25 tidak menghapus gap/failure sebelumnya. |
| Waktu host | UTC dan WIB host menunjukkan perbedaan normal +7 jam; tidak ada bukti jam sistem VPS meleset dua atau tiga jam. |
| Jam broker | Sampel tiga forex sebelumnya menunjukkan selisih timestamp raw terhadap host sekitar **+2 jam**. Ini **hanya observasi empiris**; bukan sumber independen tentang server dan transisi DST. |
| Sumber jam privat | `C:\Katarina\state\readonly-observer\broker-clock-evidence.json` **belum ada** pada pemeriksaan 05:25; jangan membuat evidence atau hash fiktif dari inferensi quote sendiri. |
| Data Tahap 0 | Sejak WP12 cutoff **28 Okt 2026 16:57 UTC**; masih **BELUM LULUS** target ≥10 hari bursa berturut-turut, ≥98% siklus, audit tick/quote, rekonsiliasi, recovery dan 0 order. Jangan backfill dijadikan forward. |
| WP10b | [PR #225](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/225) **MERGED ke main** (kode swap BUY/SELL + sensitivitas). CI sebelumnya lulus; **belum membuktikan edge/profitabilitas atau deployment VPS**. |
| Handoff jam | [PR #234](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/234) dan [#235](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/235) **MERGED ke main** sebagai dokumen. #235 full Body/Ubuntu/Windows CI PASS. |
| Jules | WP13, WP8c dan WP10a memiliki PR tetapi **belum selesai/merged**. Review formal GitHub berstatus COMMENTED dengan **CHANGES REQUIRED** karena GitHub tidak mengizinkan akun pembuat PR me-review dirinya sebagai REQUEST_CHANGES. |
| Status tugas Jules | UI Owner masih menunjukkan **Needs review**; tugas #225 sudah merged di GitHub tetapi **belum diverifikasi telah ditandai Completed/Archived di Jules**. Browser eksternal yang tersedia belum login ke akun Jules; jangan mengklaim klik atau perubahan UI. |

## B. Daftar kelemahan menurut prioritas dan langkah pembaruan

| ID | Prioritas | Kelemahan yang terbukti | Tindakan Claude/Jules dan kriteria selesai |
|---|---|---|---|
| K-01 | **P0** | **Jalur canonical observer dapat menebak jam:** HEAD [#233](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/233) saat audit `f6726480` memanggil `infer_clock_shift(...evidence=evidence, broker_server=broker_server)` **tanpa `require_evidence=True`**. Saat file tidak ada, fallback voting quote bisa melabeli `CLOCK_VERIFIED` palsu. | **Kembalikan keselamatan dari patch `2e504d3` atau setara** di PR #233; canonical path wajib evidence valid dan fail-closed. Bukti hilang/invalid menghasilkan `FAILED/NO_EVIDENCE` beralasan di ledger, **bukan** quote/tick UTC terverifikasi; worker tetap dapat pulih; tes regresi kode observer dan no-order PASS. |
| K-02 | **P0** | **Tidak ada bukti clock broker independen di VPS.** `ClockEvidence.valid_at` pada #233 memeriksa bentuk SHA tetapi belum selalu membuktikan hash konten sumber broker, server-specific provenance dan interval DST. | Claude/operator **mencari dan memverifikasi sumber broker yang nyata** (dokumen broker atau pengamatan independen yang bisa diaudit) dengan server identity, interval valid, DST, SHA sumber, reviewer; simpan hanya di state privat. Jika tak ada: `PENDING_INDEPENDENT_BROKER_EVIDENCE`, **jangan deploy** meski CI hijau. |
| K-03 | **P0** | **Regresi commit & tes WP13.** Commit aman `2e504d3` sempat dibuat tetapi HEAD Jules berikutnya menghilangkan guard. CI Ubuntu run `40957973876` job `123743617390` pernah gagal 13 tes FakeBroker karena fixture tanpa evidence. Pada pemeriksaan terakhir PR #233 `mergeable=false`, HEAD final belum memiliki CI sukses yang berlaku. | Jangan menambal dengan `require_evidence=False` atau bypass lingkungan produksi. Perbaiki fixture **test-only** dengan server mock, evidence+sidecar SHA sesuai, serta tes missing/corrupt/expired/wrong server/DST/quote stale/recovery/--since; rebase main, manifest MATCH, Body/Ubuntu/Windows PASS pada SHA final; review Claude independen baru merge. |
| K-04 | **P0** | **Tahap 0 belum terbukti:** keberhasilan siklus sesaat tidak mengesahkan integritas harian; terdapat degradasi 04:59 dan pengujian forward sejak cutoff belum memenuhi 10 hari/rekonsiliasi. | Gunakan `scripts/ai/check_stage0_health.py --since 2026-10-28T16:57:00+00:00` hanya setelah kode benar dan tervalidasi; nilai semua kriteria **secara terpisah**, hari parsial, waktu DST dan data gap; buktikan ≥10 hari bursa, ≥98%, tick/quote, ≥3 recovery, 0 order. Tidak boleh mengklaim PASS akibat unit tests. |
| K-05 | **P1** | **WP8c #230 berisiko 'bukti historis palsu'.** `build_evidence_report` bisa membangun `VERIFIED` dari `samples` manual dan self-hash, bukan bukti M5 + kalender resmi; `shift_timeline` memperluas segmen ±200 hari; `release_shift` menerima 12 bar padahal spesifikasi mensyaratkan 24; adapter menerima timeline arbitrer. PR konflik. | Ikat rilis resmi BLS ke hash bar volume M5 nyata, tidak melewati celah/ganti DST tanpa bukti, tolak forged report/adapter bypass, 24 bar dan timestamp M5 valid, regresi adversarial; saat belum ada sumber: `NO_EVIDENCE`. Rebase + CI semua OS sebelum merge. Jangan menciptakan tanggal rilis/volume palsu. |
| K-06 | **P1** | **WP10a #231: parser dan memori.** `iter_verified_ticks` mengubah kontrak 4 kolom menjadi ≥3 kolom, mengabaikan beberapa malformed rows; `symbol_records` dan `minute_quotes` menampung seluruh periode; 'last quote/minute' mengikuti urutan file, bukan timestamp maksimum; koneksi SQLite URI belum escaping/query_only. PR konflik. | Perbaiki parity strict parser, fail saat input rusak, streaming bounded dengan **uji 2 juta tick multi-hari <50MB**, pilih timestamp terbesar per menit UTC, path URI aman+mode=ro dan `query_only`; CI Body/Ubuntu/Windows HEAD final; hasil tetap **DESCRIPTIVE_ONLY_NOT_FOR_TUNING**. |
| K-07 | **P1** | **Ketahanan VPS dan drift deployment:** kode VPS `64497b5` tertinggal dari main; reboot/start otomatis tanpa login belum dibuktikan, host Windows Server 2012 R2 ±2GB, 5 simbol saat ini; data instrumen tertentu kadang stale. | Audit WP6 boot/recovery **tanpa memutus observer resmi**, backup+rollback, satu worker; lakukan deploy terkendali **hanya bila syarat evidence jam terpenuhi**, kemudian verifikasi SHA VPS, ledger, heartbeat, 0 order. Jangan sekaligus menambah 5→7 simbol sebelum bukti clock dan jendela 21:00–22:00 UTC sah. |
| K-08 | **P1** | **Kontrol review/otomasi belum end-to-end.** GitHub review berbeda dengan status Jules; akun pembuat PR tidak bisa `REQUEST_CHANGES` untuk PR sendiri; Cloud Browser belum login Jules. Risiko PR berubah/rebase dan kembali menghapus guard; perubahan status UI tidak sinkron otomatis. | Tetapkan reviewer independen (Claude/akun berbeda), satu paket satu PR; cek invariant kode dan CI per HEAD saat merge, kunci branch protection. Tandai `Completed/Archived` di Jules **hanya setelah** PR merge dan tes lolos melalui sesi Jules terautentikasi; bila tidak tersedia, laporkan sebagai **NOT_MARKED** bukan membuat klaim otomatis. Pantau Google Jules/layanan alternatif agar workflow tidak bergantung satu UI. |
| K-09 | **P2** | **Belum ada strategi terbukti menghasilkan profit bersih.** Audit historis 13 Okt dalam status proyek mencatat kandidat profit factor **0,36** dan 77% rugi setelah biaya; edge BUY/SELL belum terverifikasi dan kartu keputusan sebelumnya 100% WAIT. | Sesudah data dan waktu valid: WP4 jurnal kandidat + replay BUY/SELL, WP8b, WP9c/d, WP5 sesuai dependensi; biaya/swap/spread nyata, holdout tidak dipakai tuning. Tahap 4 memerlukan sampel holdout dan expectancy/PF sesuai Roadmap. Bukan alasan mengaktifkan order saat ini. |
| K-10 | **P2** | **Kebersihan dokumentasi/status:** beberapa baris Roadmap menyebut WP13 belum mendapat sesi padahal #233 sudah terbuka; PROJECT_STATUS masih mengandung kalimat Jules belum mulai meskipun PR selesai; perbedaan antara coding/merged/deployed/Stage0 mudah menyesatkan. | Perbarui hanya bagian status dan antrean Roadmap, status snapshot PROJECT_STATUS, arahkan CLAUDE.md ke laporan ini; jangan menulis hasil review ke REPAIR_HISTORY sebelum benar-benar diperbaiki dan diuji di VPS; gunakan SHA dan tanggal untuk setiap klaim. |

## C. Perubahan dan pekerjaan yang sudah dilakukan manajer

| Tindakan | Bukti GitHub atau operasi |
|---|---|
| WP10b: kode swap dan cost sensitivity selesai/merged | PR #225 + docs status PR #232 |
| WP8c: coding awal dan review mendalam, belum merge | Issue #226; PR #230; review resmi COMMENTED/CHANGES REQUIRED, khusus lineage palsu/segmen terlalu luas |
| WP10a: coding awal dan review mendalam, belum merge | Issue #227; PR #231; review resmi COMMENTED/CHANGES REQUIRED, khusus parser/memory/timestamp |
| WP13: Issue Jules aktif, PR pengganti dan perbaikan bolak-balik | Issue #228, PR #233, referensi patch safety `2e504d3`; PR #219 lama tidak boleh di-merge |
| Audit jam dan laporan untuk Claude | PR #234 dan #235 merged; laporan detail `WP13_CLOCK_CLAUDE_HANDOFF_20261030.md` ada di main |
| Pengamatan VPS real read-only | +2 jam empiris dan file evidence tidak ada; status 04:59 DEGRADED lalu 05:25 WAITING 298 cycles/292 successful/0 order, kode VPS `64497b5` |
| Tugas coding berikutnya disiapkan | Issue WP4 #229; WP14 setelah WP13 + WP8c; WP6 recovery di Roadmap |
| Review Jules vs UI | Review GitHub sudah dikirim; tugas yang belum merge **tidak** ditandai selesai; penandaan Jules melalui browser tertahan karena sesi tidak terautentikasi |
| Monitor otomatis | Pemantauan GitHub/Jules per jam aktif, tetapi **bukan** bukti bahwa klik Review/Archive di UI Jules telah terjadi |

## D. Urutan eksekusi yang wajib dipakai Claude

**P0 (satu jalur fokus):** Pulihkan invariant jam canonical di PR #233 **tanpa mematahkan observer**, perbaiki 13 fixture tes, review perubahan code+CI final; cari sumber jam independen *nyata* untuk server di VPS privat; baru rencanakan uji/deploy saat bukti siap, dan lakukan audit Tahap 0 terpisah. Jika sumber jam tidak ada, **STOP deployment**, tandai blocker nyata dan teruskan penelitian sumber. Jangan mencoba menyembunyikan status DEGRADED.

**P1 setelah P0 aman:** Selesaikan WP8c #230 (bukti historis, fail closed) dan WP10a #231 (parser streaming); keduanya membutuhkan rebase/CI. Uji WP6 startup/reboot dengan rencana yang tidak merusak 10 hari forward. Hindari tugas yang menyentuh jalur observer paralel sebelum konflik WP13 selesai.

**P2 setelah dependensi:** WP4 #229 jurnal kandidat, WP14 auditor read-only setelah WP13+WP8c, kemudian validasi strategi dengan holdout sesuai protokol. Persetujuan Owner tetap diperlukan untuk setiap peningkatan kewenangan trading.

## E. Acceptance matrix untuk Claude (jangan beri label selesai lebih dini)

| Gerbang | Syarat | Status per audit |
|---|---|---|
| Review code WP13 | `require_evidence=True` canonical, provenance+server+DST, fail-closed recoverable, fixture/regression PASS | **BLOCKED** |
| Merge WP13 ke main | Tanpa conflict, manifest MATCH, CI Body/Ubuntu/Windows hijau HEAD final, review independen | **BLOCKED** |
| Deploy WP13 ke VPS | Merge-ready + bukti privat asli + backup/rollback + uji tanpa mengganggu worker, 0 order | **BLOCKED (bukti sumber belum ada)** |
| Tahap 0 | ≥10 hari bursa valid pasca cutoff, ≥98%, tick+quote+reconciliation+recovery, 0 order | **BELUM LULUS** |
| WP8c / WP10a | Review blocker teratasi, CI HEAD final dan merge | **DALAM REVIEW** |
| UI Jules completion | PR merged+tes PASS, aksi Completed/Archive benar-benar tercatat di akun Jules | **BELUM DIKONFIRMASI** |

## F. Format laporan balik Claude yang diminta

Untuk tiap pekerjaan, kembalikan **PR/commit SHA yang diuji**, hasil CI Body/Ubuntu/Windows, daftar invariant/regression yang terbukti, status merge, apakah ada perubahan VPS (kalau ada: backup, SHA sebelum/sesudah, heartbeat, ledger, 0 orders), bukti clock privat **tanpa menyalin identitas/rahasia broker ke repo**, dan sisa blocker. Gunakan label terpisah **CODE DONE / MERGED / DEPLOYED / STAGE0 PASSED**; jangan pernah menyatukannya.

**Batas keselamatan:** tidak mengubah Risk Governor, `promotion_lock.json`, data holdout, persyaratan Owner, konfigurasi live, atau mengeksekusi order. Jangan menghapus ledger/gap/tick forward lama; lakukan evaluasi yang bisa diaudit.
