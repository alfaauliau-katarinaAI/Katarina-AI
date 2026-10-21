# Perubahan material Katarina AI

## 2026-10-21 — perapian repositori (tanpa perubahan perilaku)

- 45 skrip riset sekali pakai dan 27 output riset 12 Oktober yang tidak dirujuk lagi
  dipindah utuh ke `archive/` (lokasi asal dipertahankan di bawahnya; lihat `archive/README.md`).
- Tiga modul yatim beserta tesnya dihapus: `adapters/mt5_ticks`, `intelligence/brain_gateway`,
  `research/validation_suite` (tidak dipakai runtime, dokumen, maupun konfigurasi desain).
  Modul yang hanya diuji tetapi tercatat di arsitektur/traceability tetap dipertahankan.
- 226 import tak terpakai dihapus; lima nama anotasi di `market_decision_brain_v3` kini diimpor
  lewat `TYPE_CHECKING`; enam variabel lokal sisa yang tidak berefek dihapus.
- Di `scripts/research` hanya import tak terpakai yang dihapus; logika riset tidak diubah agar hasil tercatat tetap dapat direproduksi.
- `ops/deployment/release-manifest.json` sengaja tidak dibuat ulang; perbarui saat rilis berikutnya.

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
