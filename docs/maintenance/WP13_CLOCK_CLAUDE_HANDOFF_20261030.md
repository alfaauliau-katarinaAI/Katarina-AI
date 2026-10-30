# WP13 — Handoff audit jam MT5 untuk Claude (30 Oktober 2026)

**Penanggung jawab:** Yura/ChatGPT (manager), Jules (coding PR), Claude (review independen dan penerapan setelah persetujuan).  
**Status:** **BELUM TUNTAS — penyelidikan operasional terverifikasi; revisi PR #233 belum di-merge; VPS belum dideploy.**  
**Dokumen ini adalah laporan audit dan instruksi review; bukan keputusan promosi atau catatan perbaikan selesai.** Setelah kode dan penerapan terbukti, tulis hasil di `docs/REPAIR_HISTORY.md` (RH-002) dan status terbaru di `docs/PROJECT_STATUS.md`.

## 1. Ruang lingkup / sumber kanonis

- Roadmap: `docs/ROADMAP.md` Tahap 0 dan Lampiran A R4 WP13 / R6 / R7; LIVE OFF, Risk Governor dan holdout terkunci.
- **PR pengganti yang harus diaudit:** [#233 — WP13](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/233), Jules [task 5365169223632429294](https://jules.google.com/task/5365169223632429294). **JANGAN merge PR #219** (versi lama konflik).
- Revisi WP13 berupa waktu broker/quote basi/sesi FX dan `check_stage0_health.py --since`. Perubahan coding, merge, deployment dan kelulusan Tahap 0 adalah **empat status berbeda**.

## 2. Bukti VPS yang diperiksa langsung, read-only

Pemeriksaan **30 Okt 2026 sekitar 04:04–04:14 WIB**, melalui Desktop Commander akun kedua di VPS `WIN-4TTT19K3CL8`, tanpa order/restart/edit konfigurasi/ubah status observer:

| Fakta | Bukti / arti |
|---|---|
| Jam Windows/NTP | UTC dan WIB berbeda **+7 jam** sesuai zona Asia/Jakarta. `w32tm /query /status`: `Leap Indicator: 0`, `Stratum: 5`, sumber `time.windows.com,0x8`, sinkron terakhir **30 Okt 03:03:14 waktu lokal**. Tidak terlihat bukti jam VPS meleset beberapa jam. |
| MT5 tersambung | `mt5.initialize(timeout=2500)` berhasil. `account_info().trade_mode == ACCOUNT_TRADE_MODE_DEMO` (**akun DEMO** meskipun nama server mengandung 'Live'); `terminal_info().trade_allowed == False`; terminal tersambung. Identitas broker/server lengkap **tetap di VPS privat**, tidak dicetak ke repo publik. |
| Quote server vs host UTC | Sampel `MetaTrader5.symbol_info_tick` dari forex sekitar 04:13 WIB: **EURUSD raw +7190,9 detik**, **GBPUSD +7175,9 detik**, **USDJPY +7186,9 detik** relatif ke UTC host (sekitar **UTC+2 jam**). XAUUSD dan NAS100 terdeteksi lebih lama; **jangan anggap semua simbol segar hanya karena tiga forex cocok**. Data ini observasi broker vs host, **BELUM bukti independen aturan DST / UTC lintas migrasi**. |
| Ledger | SQLite `observer_cycles.clock_shift_hours` menunjukkan **+2,0** pada siklus terakhir yang dicek, dan `observer_quotes.tick_epoch` setelah normalisasi berada dekat `observed_utc`. Offset inferensi lama **tidak boleh dicap VERIFIED hanya karena konsisten**. |
| Bukti private | Berkas `C:\\Katarina\\state\\readonly-observer\\broker-clock-evidence.json` **TIDAK ADA** saat pemeriksaan. Jangan menciptakan sumber/hashing palsu untuk mengisi file. |
| Kesehatan observer | `Katarina-Readonly-Observer` **Running**, `continuous-status.json` saat 04:04: **229 siklus, 0 consecutive_failures, 0 orders, status WAITING**. Checkout VPS `C:\\Katarina\\code` masih `64497b5` menurut cek sebelumnya; tidak ada deploy PR #233. Ini BUKAN kelulusan 10 hari bursa. |

**Batas bukti:** pengamatan `+2 jam` saat ini adalah fakta empiris, namun belum ada dokumen resmi broker untuk timezone/DST spesifik server. Jangan menyalin aturan `GMT+2/+3` dari broker lain. Bukti broker yang independen dan dapat diaudit tetap **PENDING**.

## 3. Akar masalah coding WP13 yang HARUS ditutup

**P0:** Pada HEAD PR #233 yang diperiksa (hingga commit `ee9aefc0`; cek ulang HEAD sebelum review):

- `src/katarina/intelligence/cognition/observer.py` memanggil `load_clock_evidence(root / "broker-clock-evidence.json")`, tetapi `infer_clock_shift(... evidence=evidence, broker_server=broker_server)` **tidak menyalakan** `require_evidence=True`.
- Default `require_evidence=False` di `src/katarina/intelligence/broker/broker_clock_alignment.py` menerima *fallback* penentuan offset dari kesesuaian quote saat file bukti tidak ada atau invalid. Dengan demikian **ketiadaan bukti bisa menghasilkan CLOCK_VERIFIED palsu**.
- Menambahkan `require_evidence=True` tanpa memikirkan kegagalan tidak cukup. `BrainObserver.run` saat ini melempar `BROKER_CLOCK_NOT_VERIFIED` **sebelum** mencatat snapshot. `continuous_observation.py` menangkap kegagalan recoverable dan `close_ledger_cycle` dapat mencatat FAILED, namun melakukan backoff eksponensial. Verifikasi bahwa worker tetap hidup, alasan ditulis spesifik, **tidak ada quote/tick berjam palsu** dan tidak ada report `success` palsu.
- `ClockEvidence.valid_at` baru mengecek bentuk SHA-256 dan interval tanggal, belum membuktikan **asal sumber** / bukti spesifik server / tanggal pergantian DST. Hash format benar bukan sertifikat independen.

## 4. Tugas konkret Claude dan Jules untuk menutup WP13

1. **Perbaiki PR #233 yang sama**, bukan PR baru berulang. Wajibkan evidence terverifikasi pada **jalur observer canonical**, dengan penolakan missing/corrupt/expired/wrong server/DST unproven. Default lama hanya boleh tetap untuk konsumen riset lama yang dengan sadar memilih itu. **Bukan fallback sah untuk data Tahap 0**.
2. **Lindungi observasi:** bila tidak ada evidence, worker tetap hidup, mencatat cycle `FAILED/NO_EVIDENCE` + alasan tepat, tetapi **tidak** mencatat quote valid atau mengarsipkan tick forward dari waktu yang ditebak. Jangan mengakali tingkat keberhasilan siklus atau menaikkan durasi tanpa audit gap; restart/recovery otomatis harus teruji dengan fixture sintetis.
3. **Buktikan sumber independen:** bukti asli operator/broker yang spesifik terhadap **server dan interval waktu**, hash konten asli, kapan dan siapa meninjau, serta aturan DST/tanggal kedaluwarsa. Simpan bukti detail **di state VPS privat, bukan repo publik**, terikat ke server identity hash. Jika belum ada bukti resmi/mandiri, keluaran tetap `PENDING_INDEPENDENT_BROKER_EVIDENCE`; jangan mengklaim UTC terverifikasi.
4. **Tes regresi:** tiga quote basi; tiga fresh + dua stale; penutupan FX akhir pekan/rollover; offset berbeda; missing/invalid/expired/wrong broker; source-hash buatan; batas DST dan migrasi VPS/broker; uji `--since 2026-10-28T16:57:00+00:00` terhadap **seluruh** kriteria stage0, cutoff hari parsial, NO_DATA; 0 order. Cek juga `continuous_observation.close_ledger_cycle` dan `ledger.collect_tick_days`.
5. **CI + governance:** manifest rilis MATCH, unit/static/integration, GitHub Body/Ubuntu/Windows **pada HEAD final**, tidak menyentuh `config/promotion_lock.json`, Risk Governor, holdout, deployment tanpa izin.
6. **Setelah review kode lulus**, Claude menjadwalkan uji deploy terkendali **hanya setelah bukti clock private siap**: backup status/manifest, uji dry-run read-only pada fixture, validasi server identity + offset + sample aged quote, terapkan tanpa menambah worker, cek heartbeat/ledger/0 order/restart recovery. **Jangan memutus 10-day run saat evidence belum siap**; catat gap ke status bila ada.
7. Setelah semua bukti ada, update `docs/REPAIR_HISTORY.md` (RH-002), `docs/PROJECT_STATUS.md`, dan Roadmap R5 secara singkat. Catat SHA merge, SHA VPS, hasil CI, timestamp, bukti sebelum/sesudah dan risiko tersisa. **Jangan tulis Tahap 0 PASS sebelum 10 hari bursa yang valid**.

## 5. Kriteria keputusan

- **MERGE-READY** = bukti trust boundary di kode+tes, tidak ada fallback, regresi lulus, CI final hijau, reviewer independen setuju.
- **DEPLOY-READY** = MERGE-READY **dan** bukti clock independen khusus server tersedia, diverifikasi di state privat; rencana restart tanpa kehilangan data.
- **STAGE0-PASS** = uji lengkap ≥10 hari bursa berturut-turut sejak cutoff WP12, ≥98% siklus, tick/snapshot audit dan rekonsiliasi, 3 uji recovery, 0 order. Status saat laporan ini **BELUM LULUS**.
- **LIVE** = tetap **OFF**. Tidak ada izin DEMO order/akun riil, promosi, atau melonggarkan risiko.

### Instruksi singkat agar Claude tidak mengulang audit dari nol

Baca file ini → `docs/ROADMAP.md` WP13 dan aturan Tahap0 → PR [#233](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/233) terbaru → `src/katarina/intelligence/cognition/observer.py` dan `broker_clock_alignment.py` → verifikasi hasil tes/CI → cek VPS hanya read-only dahulu. Jika hasil coding sudah berubah, **audit HEAD baru**, bukan asumsi commit sebelumnya. Catat hasil terverifikasi, bukan klaim Jules semata.

## 6. Pembaruan manager — 30 Okt 2026 pukul 04:57–04:59 WIB

**Status akhir pemeriksaan: WP13 masih BLOCKED, belum aman di-merge atau diterapkan.** Ini adalah hasil audit baru, bukan konfirmasi bahwa perbaikan telah selesai.

### Bukti GitHub terbaru

- PR [#233](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/233), HEAD saat dicek: `cd52d4a3ea62df233ba036ef688f28178f8ee224`, `mergeable=false`, **belum memiliki run CI untuk SHA tersebut**.
- Commit patch pengamanan manager **`2e504d3`** sempat menambahkan `require_evidence=True` di jalur observer, validasi sumber evidence privat beserta SHA dan batas DST, serta penanganan kegagalan yang dapat dipulihkan. Namun versi HEAD PR terbaru **tidak mempertahankan patch tersebut**: canonical observer kembali memanggil `infer_clock_shift` dengan argumen `evidence` dan `broker_server` saja. Apabila evidence file tidak ada, default `require_evidence=False` membuka fallback voting quote tanpa bukti.
- Ubuntu CI **run 40957973876 / job 123743617390** sebelumnya gagal pada 13 test integrasi/PC yang menjalankan `FakeBroker` tanpa fixture evidence/source. Perbaikannya adalah fixture sintetis **hanya untuk tes**, tidak boleh menonaktifkan guard runtime.
- Instruksi perbaikan baru kepada Jules ada pada [komentar manager #233](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/233#issuecomment-6509287195). Jangan mengulang siklus revert/fix: audit diff HEAD terhadap `2e504d3` sebelum merge.

### Bukti VPS paling mutakhir (read-only)

Pada pemeriksaan **30 Oktober sekitar 04:59 WIB**:

| Parameter | Nilai |
|---|---|
| Scheduled task | `Katarina-Readonly-Observer` **Running** |
| Kode VPS | `C:\Katarina\code` commit **`64497b5`** (belum di-deploy WP13) |
| Total siklus tercatat | **274** |
| Status observer | **DEGRADED** |
| Penyebab yang tercatat | **`BROKER_CLOCK_NOT_VERIFIED`** |
| Kegagalan beruntun | **1** |
| Heartbeat | **2026-10-29T21:57:52.653100+00:00** |
| Order terkirim | **0** |
| Evidence file privat | **TIDAK ADA** di state observer resmi |

Status DEGRADED adalah snapshot sesaat, bukan bukti kegagalan permanen. Windows UTC dan WIB sebelumnya menunjukkan selisih yang tepat; offset broker empiris +2 jam **belum** mengesahkan DST atau asal waktu secara independen. Jangan menghasilkan evidence produksi dari angka tebakan ini.

### Acceptance dan instruksi Claude yang belum boleh dilewati

1. **Review & perbaiki HEAD WP13 PR #233 yang sama.** Pastikan canonical observer menegakkan `require_evidence=True`, memvalidasi sumber evidence asli (bukan format SHA saja), broker identity, validitas waktu dan DST. Bila tidak ada evidence, beri status beralasan `CLOCK_EVIDENCE_MISSING_OR_INVALID` atau `PENDING_INDEPENDENT_BROKER_EVIDENCE`; jangan menulis snapshot/tick sebagai UTC terverifikasi. Worker resmi harus tetap dapat pulih/menulis ledger kegagalan, tanpa menjalankan order.
2. **Pulihkan tes integrasi melalui fixture valid**, termasuk FakeBroker, tanpa bypass runtime. Uji tidak ada/korup/expired/wrong-broker/source palsu/DST/universe, restart dan recovery; validasi `--since 2026-10-28T16:57:00+00:00` agar semua kriteria Stage0 benar memfilter cutoff. Setelah itu regenerasi manifest, pastikan CI Body/Ubuntu/Windows **pada HEAD final**, mergeable=true, review independen bersih.
3. **Tidak ada deployment WP13 sampai bukti broker privat spesifik server dan masa berlaku benar-benar diperoleh dan direview**, lalu rencanakan backup dan deployment terkendali agar run 10 hari tidak terputus tanpa catatan. Risiko 10 hari forward dan rekonsiliasi tidak dapat diselesaikan hanya oleh Jules.
4. Setelah merge+deploy aman dan hasil nyata tersedia, isi `docs/REPAIR_HISTORY.md`, `docs/PROJECT_STATUS.md`, dan tabel R5 Roadmap dengan SHA CI, SHA code VPS, status ledger, waktu, dan sisa blocker. **Jangan mengklaim PASS Tahap 0 ataupun membuka DEMO/LIVE** hanya karena CI lulus.

**Putusan manager:** `CODE_REVIEW_BLOCKED` + `DEPLOY_BLOCKED_PENDING_PRIVATE_BROKER_EVIDENCE`. Tugas coding Jules masih aktif. Claude dapat menggunakan dokumen ini sebagai handoff tanpa menebak progress.
