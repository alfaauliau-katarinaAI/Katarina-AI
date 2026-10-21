# Perubahan material Katarina AI

## 2026-10-22 — rampingkan repo (C): skrip riset sekali pakai

- Dihapus 62 skrip `scripts/research` yang hanya dirujuk tesnya sendiri, `research/safety/reselection_guard.py`,
  registri regime 11 Okt, `tests/replay`, `tests/research`, dan 25 tes unit yang hanya menguji skrip tersebut.
- Dipertahankan 4 skrip yang dipakai workflow/operasional. Tidak ada modul runtime yang kehilangan tes.

## 2026-10-22 — rampingkan repo (B): dokumen bertanggal dan usang

- Dihapus 116 dokumen yang tidak dirujuk kode, config, tes, workflow, maupun dokumen inti: laporan riset,
  validasi, dan review bertanggal 10–21 Oktober beserta output-nya, catatan operasi bertanggal/usang, dan
  dokumen root lama (roadmap, runtime HP, akses gratis, dll.). Riwayatnya tetap di Git.
- Dipertahankan: arsitektur + ADR (identitas desain), freeze record stage yang dibaca audit, bukti yang
  dirujuk config/tes, status proyek, quickstart, panduan GitHub/deployment.

## 2026-10-22 — rampingkan repo (A): pensiunkan tooling VPS lama

- Dihapus: agent/remote-lab VPS lama (`scripts/vps`, `scripts/vps2012`, `ops/vps`, `ops/github-vps`,
  `ops/bridge`, `vps_bridge`, `scripts/windows`), tiga workflow self-hosted VPS, tiga launcher `VPS_*.bat`,
  `config/vps_remote_lab_policy.json`, dokumen dan tes khususnya. Akses VPS kini lewat Desktop Commander;
  runtime VPS memakai `katarina_pc.py` + observer canonical dari checkout `main`.
- Body CI tidak lagi menjalankan audit rilis VPS lama. Tidak ada perubahan otak, risiko, atau observer; LIVE tetap OFF.

## 2026-10-22 — guarded branch cleanup: daftar branch usang yang sudah ditinjau

- `scripts/governance/guarded_branch_cleanup.py` kini juga menerima branch yang tercatat di
  `docs/maintenance/superseded-branches.json`, **hanya** selama branch itu masih menunjuk ke commit yang
  dicatat persis. Penjaga lama tetap berlaku: bukan `main`, tidak diproteksi, tidak dipakai PR terbuka,
  SHA dicek ulang sesaat sebelum hapus, maksimal 10 per run, mode dry-run default.
- Daftar berisi tujuh branch dari `BRANCH_ARCHIVE_20261022.md`. `claude-vps-bridge` sengaja tidak masuk.
  Workflow tetap satu-satunya yang punya hak tulis; tidak ada perubahan perilaku trading, live tetap OFF.

## 2026-10-22 — arsip branch usang

- Tujuh branch diperiksa per berkas terhadap `main`: isinya sudah ada di `main` (PR #139/#152, pindah ke
  subpaket baru) atau sengaja dihapus. Commit terakhir dan alasannya dicatat di
  `docs/maintenance/BRANCH_ARCHIVE_20261022.md` sebelum branch dihapus. `claude-vps-bridge` dipertahankan
  sebagai kanal pesan GitHub↔VPS. Tidak ada perubahan kode, perilaku, atau risiko; live tetap OFF.

## 2026-10-21 — jalur order demo: penolakan pasti, pengiriman yang tak pernah terisi, slippage dan biaya

- Retcode broker yang menyatakan order **tidak dieksekusi** (requote, reject, price changed/off, invalid
  volume/price/stops, market closed, no money, dll.) kini dicatat `REJECTED` (final), bukan `UNKNOWN`.
  Sebelumnya satu requote membuat outbox demo terkunci permanen, karena `UNKNOWN` tanpa deal tidak pernah selesai.
- `reconcile()` menandai kiriman `SUBMITTING`/`UNKNOWN` sebagai `NOT_FILLED` hanya jika sudah lebih dari 15 menit,
  tidak ada deal dengan komentar intent tersebut, dan tidak ada pending order dengan komentar itu. Timeout dan
  error yang ambigu tetap memblokir sampai terbukti.
- Outcome posisi yang tutup kini mencatat slippage entry (positif berarti merugikan), serta komisi, swap, dan fee
  secara terpisah. Data ini menjadi bahan model biaya riset dari histori demo.
- Tidak ada retry otomatis. Setelah `REJECTED`, produsen boleh mengirim intent baru dengan harga segar
  lewat Risk Governor seperti biasa. Hanya untuk akun demo; live tetap OFF.

## 2026-10-21 — lab riset: holdout prospektif, exit SL/TP, dan swap

- **Holdout prospektif.** Kandidat pertama yang lolos aturan untuk suatu instrumen dicatat sekali di
  `lab_nominations` (metode, sisi, exit, dan stempel bar terakhir saat lolos). Setelah itu, kandidat itu
  hanya dinilai dengan trade yang sinyalnya muncul *sesudah* stempel tersebut: `FORWARD_PENDING` (< 30 trade),
  `FORWARD_CONFIRMED` (rata-rata positif, t ≥ 1,65), atau `FORWARD_FAILED`. Nominasi tidak pernah diganti.
  Hanya `FORWARD_CONFIRMED` yang memberi `next_step=DEMO_FORWARD_TEST`; `live_authorized` tetap false.
- **Exit kedua.** Selain tutup di bar ke-12, setiap pola juga diuji dengan bracket ATR (SL 1 ATR, TP 1,5 ATR,
  maksimal 12 bar). Kalau satu bar menyentuh SL dan TP sekaligus, dicatat sebagai SL (asumsi konservatif).
- **Swap.** Kalau broker memakai swap dalam poin (`swap_mode=1`), setiap malam broker yang dilewati dihitung
  sebagai biaya (atau kredit). Mode swap lain belum dimodelkan, begitu juga komisi dan swap tiga kali lipat.
- Karena kandidat kini 12 per run, ambang t pengembangan dinaikkan ke 2,65 (Bonferroni satu sisi 5% untuk 12).
  Perubahan ini dilakukan sebelum ada hasil v3 di VPS, jadi aturannya tetap terkunci sebelum hasil keluar.
- Status publik menampilkan jenis exit, status forward, dan jumlah nominasi.

## 2026-10-21 — lab riset: aturan lolos dikunci sebelum hasil (`broker-lab-v3`)

- Setiap kandidat kini mencatat t-stat pengembangan dan review. Kandidat terpilih diberi `verdict`
  dengan aturan yang ditetapkan sebelum ada hasil v3: minimal 30 trade per bagian, t pengembangan ≥ 2,4
  (Bonferroni satu sisi 5% untuk 6 kandidat), dan sepertiga terakhir harus positif setelah biaya dengan t ≥ 1,65.
- Lolos hanya berarti `next_step=DEMO_FORWARD_TEST`; `live_authorized` tetap false.
- Uji: 200 random walk tanpa drift seluruhnya ditolak; drift persisten lolos.
- Status publik (`research_lab_status`) kini ikut menampilkan t-stat dan `verdict` (nilai di luar daftar putih dibuang).
- Label biaya diperbaiki ke `TYPICAL_SPREAD_PLUS_0.20_ATR_PROXY` (sebelumnya masih menyebut kutipan saat ini).
- Versi naik ke `broker-lab-v3`, sehingga lab VPS menghitung ulang semua dataset dengan biaya spread
  yang benar dan aturan baru. Hasil v2 tetap tersimpan.

## 2026-10-21 — hapus 231 berkas tak terpakai (atas persetujuan Owner)

- Dihapus: seluruh `archive/` (168 berkas), 30 alias `katarina.body.stage11–40`, 8 modul yang hanya dipakai
  test beserta test-nya (`engines.setup_quality`, `news.news_consensus`, `lab.regime_research_router`,
  `lab.strategy_selector`, `perception.flow_efficiency_index`, `research.experimental_strategy_evidence_portfolio`,
  `research.owner_structure_candidate`, `research.real_tick`), dan 17 script riset yang tidak dirujuk di mana pun.
- Dipertahankan: tooling VPS (`scripts/ai/install_*`, `scripts/vps*`), `config/`, Risk Governor, dan
  `adapters.transport.kat1_execution` (fondasi jalur kirim order).
- Release manifest dan `RUNTIME_MODULE_MAP.md` dibuat ulang (B=13, D=2). Semua berkas tetap ada di riwayat Git.
- Tidak ada perubahan perilaku runtime, strategi, atau flag live.

## 2026-10-21 — penjaga konektivitas antar file

- Audit jalur: 305 modul `katarina` ter-import tanpa error, dan semua import `katarina.*` di `scripts/`
  serta `katarina_pc.py` mengarah ke modul/nama yang ada. Unit, static, integration, hygiene, dependency
  links, dan release manifest lulus.
- Tes statis baru `tests/static/test_module_connectivity.py` menjaga dua hal itu di Body CI (proses
  terpisah, sekitar 1 detik), supaya pemindahan/penggantian nama berikutnya tidak memutus jalur diam-diam.
- Tidak ada perubahan perilaku, strategi, Risk Governor, atau flag live.

## 2026-10-21 — persiapan pemisahan website (perapian tahap 7, belum selesai)

- `scripts/deployment/export_website_repo.py` (+ tes) mengekspor berkas situs publik ke layout repo mandiri
  dengan manifest SHA-256. Panduan `docs/deployment/STANDALONE_WEBSITE_EXTRACTION.md` ditulis ulang dengan
  langkah Owner.
- Repo baru belum dibuat (integrasi GitHub menolak dengan 403) dan Cloudflare Pages belum dipindah, jadi
  `website/` dan kawan-kawan tetap di repo ini. Tidak ada perubahan perilaku situs.

## 2026-10-21 — satu sumber status (perapian tahap 8)

- `docs/PROJECT_STATUS.md` ditulis ulang sebagai satu-satunya dokumen status (per 21 Oktober, mencakup
  perubahan 17–21 Oktober). README tinggal ringkasan dan tautan; bagian bertanggal 16 Oktober yang
  menduplikasi dokumen arsitektur dihapus dari README.
- Diarsipkan ke `archive/docs/`: status 16 Oktober, `CURRENT_PROJECT_HANDOFF.md`, handoff 10 dan 13 Oktober,
  dan snapshot status GitHub-first 11 Oktober.

## 2026-10-21 — logika verifier dipindah ke `src` (perapian tahap 6, tanpa perubahan perilaku)

- `scripts/ai/verify_unified_katarina.py` → `katarina.governance.unified_verification` dan
  `scripts/ai/audit_self_evolution_runner.py` → `katarina.governance.self_evolution_audit`. Kedua script
  kini CLI tipis yang mengekspor ulang nama lama; output verifier identik (selain cap waktu yang memang
  berubah tiap run). Workflow, tes, dan `verify_master_design_traceability` mengimpor dari `src`.
- Tidak dipindah: `hf_archive_sync.py` (layanan mandiri stdlib yang dimuat lewat path dari venv HF
  terpisah, systemd, dan installer) dan `mt5_shadow_lab.py` (sudah CLI yang mendelegasikan ke `src`).
- Script riset tidak diubah logikanya. `broker_entry_diagnostics_v9`, `broker_multitf_risk_v10`,
  `frozen_xau_sell_tick_verdict` (hanya dipanggil workflow yang diarsipkan di tahap 5, tanpa tes) diarsipkan.

## 2026-10-21 — workflow CI disederhanakan (perapian tahap 5, tanpa perubahan perilaku)

- 12 workflow manual `stage07-*` digabung menjadi `stage07-transport.yml`; `stage06-static`,
  `stage06-modern-compile`, `stage08-validation`, `stage09-health-safety` menjadi `stage06-09-clearance.yml`.
  Input `check` memilih satu job atau `all`. Langkah tiap job identik (diverifikasi lewat YAML); env tingkat
  workflow dipindah ke job, nama tampilan job = nama workflow lama.
- Tidak digabung ke `katarina-body-ci.yml` karena pemicunya berbeda (manual vs push/PR). Nama job Body CI
  yang menjadi check wajib tidak berubah.
- Workflow riset `broker-entry-research-v9`, `broker-multitf-research-v10`, `public-strategy-tournament`,
  `katarina-strategy-replay`, `frozen-xau-tick-verdict` tidak pernah dipicu dalam 30 hari terakhir dan dipindah
  ke `archive/.github/workflows/` (tidak aktif di luar `.github/`). Jumlah workflow 39 → 20.

## 2026-10-21 — modul body bernama fungsi (perapian tahap 4, tanpa perubahan perilaku)

- `src/katarina/body/stageNN.py` (11–40) diganti nama sesuai fungsinya, mis. `stage16` → `risk_governor`,
  `stage35` → `strategy_tester`. Tabel lengkap: `docs/maintenance/BODY_STAGE_MAP.md`.
- `implementation_module` di `config/stages/stageNN.json` dan `SPEC` modul memakai nama baru; nama file
  manifest tetap karena dimuat per nomor. Konstanta `katarina.body.STAGE_MODULES` dan tes konsistensinya
  ditambahkan; tes dan audit lintas-stage memakai konstanta itu.
- Alias `katarina.body.stageNN` (`sys.modules` + `DeprecationWarning`) dipertahankan satu rilis.
- Generator `upgrade_functional_body.py` menulis berkas sesuai manifest (hasilnya identik). Bootstrap
  sekali pakai `scripts/body/bootstrap_fast_body.py`, yang membuat ulang layout lama, diarsipkan.

## 2026-10-21 — shim lokasi lama `intelligence/` dihapus (perapian tahap 3b)

- 104 shim `katarina.intelligence.<nama_lama>` dari tahap 3a dihapus; semua rujukan aktif sudah memakai
  subpaket baru. Pemanggil luar repo (mis. checkout VPS lama) harus memakai path baru atau tetap pada
  commit sebelum perubahan ini.

## 2026-10-21 — `intelligence/` dikelompokkan ke 8 subpaket (perapian tahap 3a, tanpa perubahan perilaku)

- 104 modul dipindah ke `cognition/`, `perception/`, `broker/`, `news/`, `demo/`, `shadow/`, `lab/`,
  `operations/`. Empat modul berversi diberi nama kemampuan: `brain_observer` → `cognition.observer`,
  `market_decision_brain_v3` → `cognition.market_decision`, `adaptive_brain_v2` →
  `cognition.adaptive_observation`, `multi_market_brain` → `perception.screening`. Isi modul tidak berubah
  kecuali `demo_forward`: pencarian `config/risk_governor_v2.json` kini `parents[4]` karena satu level lebih dalam.
- Semua import, string patch tes, path di config, workflow, launcher dan dokumen aktif diganti ke lokasi baru.
- Lokasi lama berisi shim (`sys.modules` alias + `DeprecationWarning`) untuk pemanggil di luar repo;
  dihapus di tahap 3b. Dokumen bertanggal, arsip, dan payload `scripts/ai/install_*` tidak diubah.

## 2026-10-21 — pensiun `KatarinaAIBrain` lama (perapian tahap 2a, tanpa perubahan perilaku)

- `intelligence/brain.py` beserta seluruh dependennya dipindah ke `archive/`: modul riset
  `independent_audit`, `indicator_combinations`, `mt5_journal`, `loss_diagnostics`; CLI
  `scripts/ai/validate_brain.py`, `validate_mt5_journal.py`; empat eksperimen zone/scalp/strategi
  10 Oktober; delapan berkas tes; dua dokumen operasi yang menjelaskan CLI tersebut.
  Tidak satu pun terjangkau dari entry point runtime atau workflow.
- Satu tes integrasi brain dipisah dari `test_strategy_selector.py` ke arsip; tes selector lainnya tetap.
- `multi_market_brain` dipertahankan: modul ini library fitur/screening yang dipakai 40+ berkas aktif.
- Penelusur peta modul kini mengenali import nama polos lewat `sys.path`; manifest rilis dibuat ulang.

## 2026-10-21 — peta modul runtime (perapian tahap 1, tanpa perubahan perilaku)

- `scripts/governance/runtime_import_map.py` menelusuri import secara statis dari entry point runtime,
  launcher (.bat/.ps1/.sh/service), dan workflow, termasuk modul body yang dimuat dari `config/stages`.
- Hasilnya `docs/maintenance/RUNTIME_MODULE_MAP.md`: A=214 dipakai runtime/workflow, B=19 hanya tests,
  C=35 hanya script riset, D=2. Tidak ada berkas yang dipindah atau dihapus.
- Rencana perapian 8 tahap dicatat di `docs/maintenance/CLEANUP_PLAN.md`.

## 2026-10-21 — biaya riset memakai spread tipikal

- Memori riset VPS 19 Oktober (11.516 eksperimen) menunjukkan instrumen menjelaskan 99% variasi
  hasil dan biaya tersirat ~1,26 range H1 per trade: spread diambil dari satu kutipan saat
  rollover/kutipan basi.
- Lab riset (`broker-lab-v2`) kini memakai median spread per candle H1 dari broker (minimal 100
  sampel); kutipan saat ini hanya cadangan. Sumber, jumlah sampel, kutipan saat ini, dan rasio
  spread/median range dicatat di setiap run.
- Instrumen dengan spread tipikal > 20% median range H1 ditandai `COST_PROHIBITIVE` dan tidak
  diuji worker. Cadangan slippage 0,2 range dan kriteria lolos tidak berubah.

## 2026-10-21 — perapian repositori (tanpa perubahan perilaku)

- 45 skrip riset sekali pakai dan 27 output riset 12 Oktober yang tidak dirujuk lagi
  dipindah utuh ke `archive/` (lokasi asal dipertahankan di bawahnya; lihat `archive/README.md`).
- Tiga modul yatim beserta tesnya dihapus: `adapters/mt5_ticks`, `intelligence/brain_gateway`,
  `research/validation_suite` (tidak dipakai runtime, dokumen, maupun konfigurasi desain).
  Modul yang hanya diuji tetapi tercatat di arsitektur/traceability tetap dipertahankan.
- 226 import tak terpakai dihapus; lima nama anotasi di `market_decision_brain_v3` kini diimpor
  lewat `TYPE_CHECKING`; enam variabel lokal sisa yang tidak berefek dihapus.
- Di `scripts/research` hanya import tak terpakai yang dihapus; logika riset tidak diubah agar hasil tercatat tetap dapat direproduksi.
- `ops/deployment/release-manifest.json` dibuat ulang setelah perapian (372 berkas, status MATCH).

## 2026-10-16 — jalur runtime sesuai diagram patokan Owner

- Catat diagram sebagai kontrak arsitektur dan pindahkan observer ke kemampuan
  internal otak. CLI menjadi delegasi; helper candle berpindah dari entry point
  legacy ke adapter broker read-only yang diinjeksi.
- Otak memiliki context/memori/journal/shadow, urutan settle/learn/propose,
  monitoring/foundation, publikasi, core tester serta modal/recovery offline.
- Tambahkan checkpoint dan audit internal; restore atomik mempertahankan reserve
  dan inflight tanpa replay order, migrasi modal broker atau perubahan posisi manual.
- Gerbang pengiriman memerlukan Risk Governor eksternal dan tetap menolak semua
  order nyata, termasuk ketika penilaian simulasi menyetujui review.
- Tutup dua CLI observer legacy agar tidak menyalakan loop atau otak paralel.
- Perbaiki import `replace` pada konteks berita yang terungkap lewat uji alur penuh.
- Lokal: 1.270 unit, 113 static (4 skipped), 61 integration. CI tetap wajib sebelum
  merge. Source engine trading/Risk Governor/MT5 tidak berubah; VPS belum diverifikasi.

## 2026-10-15 — satu otak; Management dan 11 spesialis dihapus

- Hapus tiga workflow Management/team, enam script, workplan, roadmap dan
  enam suite unit yang hanya menguji sistem spesialis yang telah dihapus.
  Hapus pula sembilan job spesialis/Management dari Body CI.
- Satu `UnifiedKatarinaBrain` menghubungkan persepsi pasar, kognisi, Neuro-Link
  dan sintesis riset entry/exit. Observer memakai instance yang sama setelah
  settlement dan sebelum proposal virtual, tanpa worker/scheduler baru.
- Neuro-Link mempertahankan waktu pertama ingest, dedup, checksum dan quarantine;
  Fast/Deep berbagi memori dan checkpoint. Rollback Owner memblokir sampling.
- Tambah tujuh regresi integrasi untuk restart/idempotensi, preview tanpa tulis,
  pemisahan outcome quote dari bukti broker, causal time, tampering dan rollback.
- Registry 14 modul; 1.270 unit, 109 static (4 skipped), 49 integration lulus lokal.
  CI GitHub tetap menjadi syarat merge. Batas produksi/broker/VPS tetap eksplisit.
- Engine trading, Risk Governor, konfigurasi risiko dan MT5 tidak diubah.

## 2026-10-15 — seluruh branch disatukan ke main

- PR #85 menyatukan ancestry 34 branch yang patch-nya sudah terwakili di main
  atau seluruh blob file perubahannya identik dengan main.
- PR #86 mengintegrasikan Neuro-Link recall, riset shadow paper/replay dan
  penelitian portfolio; varian engine eksperimen dipisahkan ke modul research.
  Jalur recall baru tetap memakai pemeriksaan checksum payload yang ada.
- Empat branch lama memakai main yang sudah lebih lengkap/diperkuat. Ekstraksi
  website didokumentasikan tanpa menghapus 799 file inti dari repository unified.
- Body CI PR dan main lulus: 1.309 unit, 110 static (4 skipped), 42 integration.
- Guarded cleanup menghapus seluruh 42 branch awal selain main dalam lima batch:
  10 + 10 + 10 + 10 + 2. Daftar branch diverifikasi setelah tiap eksekusi.
- Seluruh 42 head awal tersimpan sebagai ancestor main; main tetap dilindungi.
  Engine produksi, Risk Governor, konfigurasi risiko dan MT5 tidak berubah;
  live trading tidak diaktifkan. Sinkronisasi VPS belum diverifikasi.
- README, status proyek dan handoff diperbarui dengan tautan audit/receipt.

## 2026-10-15 — repository, akses dan status (snapshot sebelumnya)

- PR #81 menghapus empat snapshot VPS kedaluwarsa, menyamakan default repository
  pada installer/bridge, memindahkan dua dokumen, dan menambah guard kebersihan.
- PR #82 memulihkan executable bit agent Termux yang terdeteksi berubah saat
  publikasi. Source agent tidak diubah oleh koreksi metadata tersebut.
- PR #83 memperbaiki CODEOWNERS, mempin lima Actions resmi ke commit SHA,
  menghapus dispatch audit ganda, membatasi izin dan memperkuat guarded cleanup.
- Main dilindungi: wajib PR/body CI/up-to-date/resolved conversations, admin ikut
  aturan, force push dan penghapusan main ditolak. Tidak ada kolaborator tambahan.
- Secret scanning, push protection, dependency graph, Dependabot alerts dan
  pelaporan kerentanan privat diaktifkan. Approval bot dinonaktifkan.
- Cleanup terverifikasi menghapus 10 lalu 2 branch ancestor, menyisakan main dan
  42 branch unik. Dry-run penutup tidak menemukan kandidat.
- Scheduled news menghasilkan artifact untuk publikasi yang direview, bukan
  mendorong langsung ke main. Workflow stage/research manual dipertahankan.
- Verifikasi offline unified brain: 10 komponen terintegrasi, tidak ada order,
  live execution false. Strategi/Risk Governor tidak diubah.
- Dokumentasi status kini dipusatkan di `docs/PROJECT_STATUS.md`; handoff lama
  dipindahkan ke arsip bertanggal dan panduan CLI dipisahkan dari koneksi Work.

Angka pengujian dan tautan bukti ada di [status proyek](docs/PROJECT_STATUS.md).
Perubahan ini tidak mengklaim sinkronisasi VPS atau profitabilitas strategi.

## 2026-10-16 — portable host

- Replace fixed Windows observer state default with explicit/env/OS resolution.
- Add local host preflight and visible bounded observation budgets.
- Add broker-free, brain-owned local evidence lifecycle with checkpoint/lock.
- Test portable lifecycle on Linux, Windows and macOS in CI; retain live OFF.

## 2026-10-16 — automatic read-only connections

- Bind allowed broker account/server before selecting local or HTTPS sensor routes.
- Retry bounded whole passes and retain offline research when routes are unavailable.
- Add explicitly installed authenticated TLS sensor bridge; no execution APIs.
- Test route selection, disconnect/session recovery, real loopback TLS and data pipeline.

## 2026-10-16 — direct PC acceptance kit

- Replace default VPS supervisor launcher with one-pass PC acceptance.
- Add private Python 3.12 environment setup and optional Windows MT5 dependency.
- Separate invented demo state from bound read-only broker observation and report locally.
- Build source-only kit with commit/checksum manifest; test extracted kit on three OSes.

## 2026-10-16 — guarded PC environment recovery

- Validate private dependency environments at startup and build isolated replacements.
- Require actual synthetic acceptance before atomic selection; preserve old environments.
- Add validated previous-environment fallback, lock, failure cooldown and local redacted audit.
- Prove recovery from an unavailable interpreter in extracted packages on three OSes.

## 2026-10-16 — AI trading pretrial foundation

- Add configured JSON model dialog, heuristic Fast/Deep routing and bounded read tools to the single brain.
- Share dialog, Neuro-Link and market observation memory under one host lock.
- Add an authenticated foreground browser surface; require TLS for remote access.
- Add nonexecuting MT5/Hands WAIT feedback with account checks, TTL, dedup and receipts.
- Add portable pretrial acceptance; distinguish scripted fixtures from real model/broker proof.
- Local regression: 1,270 unit; 113 static (4 skips); 132 integration. Linux, Windows and macOS packaged CI passed (Actions run 38811219852).
- Trading/risk/MT5 source unchanged, real execution OFF. Owner authorized public GitHub publication, PR, CI and merged-branch cleanup; cross-platform results are recorded in the pretrial validation evidence.

### Repository maintenance

- Owner-authorized main-only Actions maintenance disables active workflow registrations whose YAML source is absent at the exact current main commit.
- Preserve source-backed workflows, built-in Dependency Graph, run history and artifacts.
- Verify main SHA again before mutation; default script execution is dry-run.
- Four maintenance safety tests pass; total unit suite is 1,274.
