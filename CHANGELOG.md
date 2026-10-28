# Perubahan material Katarina AI

## 2026-10-28 - daftar perbaikan dan agenda rapat Owner–Claude

- Tambahkan ke `docs/ROADMAP.md` daftar aksi FIX-01..FIX-14 (P0/P1/P2) dan keputusan DEC-01..DEC-08 (agenda rapat Owner/Claude): pemilik, bukti, kriteria selesai, urutan dan dampak terhadap Stage0 frozen.
- Tindak lanjut CI PR #209 run #40583029343: Windows integration test antarmuka Owner timeout, sementara Body/Ubuntu PASS. Root cause belum terbukti, sehingga dilabelkan P0 verification blocker, bukan klaim regresi pasti.
- Sinkronkan `docs/PROJECT_STATUS.md` agar kegagalan CI terbaru tidak tersembunyi; hanya perubahan dokumentasi, tidak mengubah task/MT5/ledger/trading.

## 2026-10-28 - audit keseluruhan untuk review Claude (dokumentasi saja)

- Tambahkan audit menyeluruh per subsistem, matriks tahap 0-5, pemisahan bukti kode/CI/MT5/alpha dan daftar tindakan prioritas P0/P1/P2 di docs/maintenance/CLAUDE_FULL_SYSTEM_AUDIT_20261028.md; tautkan pada roadmap, PROJECT_STATUS dan CLAUDE.md.
- Snapshot pengujian terpisah yang diaudit: PR #208 CI sukses, 31/31 siklus pertama OK, 155 quote OK, broker UTC+2, 5 simbol, 0 order; 0/10 hari penuh tervalidasi, reconnect 0/3, broker tick-days/reconciliation belum tersedia. Seluruhnya hasil sementara, bukan bukti strategi profitable.
- Tidak mengubah Risk Governor, observasi frozen, task Windows, kredensial, keputusan trading atau file holdout. R5 tetap milik Claude setelah review.


## 2026-10-28 - Penerimaan MT5 jam NTP dan penggabungan dua kontrak waktu

- W32Time VPS awalnya Local CMOS Clock, offset terhadap NTP +14,9 detik; observer berhenti tertib dan database SQLite dibackup, service W32Time dibuat Automatic dengan peer time.windows.com,0x8. Status sinkron normal; stripchart sekitar +0,08 detik; host preflight READY.
- Gabungkan WP12 yang memakai server-shift pada historical copy_ticks_range dengan pemeriksa time reference per perangkat; satu pass MT5 read-only: 5/5 simbol, offset +2, 5 WAIT, 0 order, tanpa error. Bukti pada docs/maintenance/STAGE0_10DAY_ACCEPTANCE_20261028.md; uji 10 hari baru dimulai setelah review CI dan penempatan versi gabungan.

## 2026-10-28 — Stage 0 clock false-PASS guard (untuk review, belum merge)

- Audit read-only ledger VPS: 4.437/4.550 siklus OK (97,5165%, target 98%), streak 2/10 hari bursa. Jam broker +3→-4→-7→+2 (delta -7/-3/+9) salah dianggap PASS karena hanya dekat DST.
- Perbaiki `data_health.py` agar hanya menerima offset integer finite -12..14 dan perubahan tepat 1 jam pada jendela DST; tambah diagnostik `invalid_transitions` dan `valid_step`. Tes tambahan 3 RED pada baseline, lalu total 18 unit GREEN; replay data asli `clock_shift_stable=NOT_MET`.
- Task observer masih InteractiveToken/logon-only, belum diuji unattended boot; runtime dan trading tidak disentuh. Detail dan langkah review Claude di `docs/maintenance/STAGE0_CLOCK_HEALTH_HANDOFF_20261028.md`.

## 2026-10-27 — integrasi terisolasi DC akun kedua (belum merge/deploy)

- Gabungkan perbaikan UTC broker WP12 (#204) dan shadow decision WP9b (#205) di worktree terpisah, tetap `legacy_fail_closed`, 0 order; tes tertarget 5+2+5+2 PASS.
- Port hanya 3 berkas WP8a (#195) dari branch berbasis `main` lama agar tidak menghapus WP2/WP3/WP9a/WP11; tambah prasyarat bukti offset bar historis per chunk (`INDEPENDENT_UTC`, hash sumber), query server dan cutoff setelah normalisasi; 15 tes WP8a PASS termasuk dua chunk shift DST berbeda, loader streaming O(1) bar, batas 100.000 bar pada eager loader, dan validasi akhir arsip; gabungan 69 tes tertarget PASS.
- Bukti offset historis/DST broker independen **belum tersedia**; ekspor MT5 asli sengaja fail-closed. Static suite VPS 71 tes: 69 PASS, 2 FAIL karena Python VPS belum memiliki numpy untuk modul lama historical_analog_memory; full CI GitHub dan penerapan VPS belum dilakukan. Handoff dan urutan review di [docs/maintenance/INTEGRATION_HANDOFF_20261027.md](docs/maintenance/INTEGRATION_HANDOFF_20261027.md).

## 2026-10-27 — usulan agentic AI untuk review Claude

- Atas permintaan Owner, catat lima fondasi perbaikan, kemampuan agentic dan target auditor data di roadmap.
- Usulan belum menjadi paket implementasi; gerbang tahap/promosi tetap, tanpa perubahan runtime, LIVE OFF.

## 2026-10-23 — WP12: jam tick MT5 server ke UTC (#204)

- Konversi timestamp dan jendela tick menggunakan offset jam broker yang terverifikasi, tanpa menebak saat bukti hilang.
- Fixture tes Windows menutup koneksi SQLite dan membandingkan path kanonik; assertion fungsional tetap.
- Regresi dua jalur legacy, integritas arsip +3 setelah peralihan +2, dan suite Windows lengkap ditambahkan; berkas terkunci tidak diubah.
- Arsip hari ber-offset campuran ditandai GAP; konteks riset menolak hari lama tanpa basis waktu; LIVE OFF.

## 2026-10-23 — status setelah merge; temuan T11 dan paket WP12

- WP2, WP3, WP9a, WP11 di-merge dan diterapkan ke VPS (`d8b003a`, manifest MATCH); 5 simbol sejak 00:16 UTC.
- Temuan T11: jam tick MT5 = jam server (+3 jam); quote observer berumur ±3 jam. Paket WP12 (prioritas tertinggi);
  data forward sebelum WP12 hanya bukti operasional; 10 hari Tahap 0 dihitung sejak WP12 diterapkan.
- WP8a diminta perbaikan (`import io`, verifikasi jam bar); temuan VPS lama diberi nomor T9, temuan jam parsial T10.

## 2026-10-23 — WP9a: peta pemblokir keputusan baca-saja (#196)

- Tambah `research/blocker_ladder.py` + CLI laporan SQLite mode=ro dari `contextual_decisions`.
- Kelompokkan alasan A/B/C/M/UNKNOWN, hitung frekuensi, 10 kombinasi terbanyak dan tangga kumulatif
  per simbol/total; M/UNKNOWN tidak dianggap pulih. Tes sintetis membuktikan determinisme.
- Diagnostic-only: keputusan, Risk Governor, live/DEMO dan VPS tidak diubah.

## 2026-10-23 — WP3: diagnosis jalur berita observer (#191)

- Catat item feed usang/tanggal invalid, umur item terbaru, serta kegagalan artikel tanpa mengubah pemilihan atau blackout.
- Ringkasan per siklus disimpan di `observer_news`; laporan Tahap 0 memisahkan tanpa rilis vs gagal ambil.
- Tes sintetis memastikan `data_health.verdict` dan keputusan tetap; berkas terkunci tak berubah, LIVE OFF, VPS tak diubah.

## 2026-10-23 — WP11: verifikasi jam sebagian pasar tutup (#201)

- Mayoritas jam MT5 dihitung dari quote yang bersuara segar, bukan semua simbol; minimum 3 dan ambang 70% tetap.
- Tambah daftar simbol basi terurut di `ClockFinding`; keputusan observer, risk dan backoff tidak diubah.
- Tes jam dan siklus broker palsu memeriksa 3 FX segar + 2 snapshot basi; LIVE OFF, VPS tidak disentuh.

## 2026-10-23 — WP2: tick broker streaming per jam (PR #190)

- Mengganti koleksi tick sehari dalam RAM dengan `_download_day`: satu jam per batch, CSV gzip deterministik,
  dedup, SHA-256, indeks baris per jam dan file sementara atomik; alasan gap dipertahankan.
- Rekonsiliasi snapshot hanya mendekode jam relevan, tanpa menampung semua tick satu hari.
- Tes pembanding terhadap penulis sebelum WP2 dan uji memori dua juta tick ada di PR.
  Tidak ada berkas terkunci diubah; LIVE tetap OFF, VPS tidak diubah.

## 2026-10-23 — roadmap: holdout WP9d satu kali, R5 WP8a/WP9a sinkron

- WP9d: varian detektor hanya dibandingkan pada data pengembangan; holdout dibuka satu kali untuk kandidat final.
- R5: WP8a dan WP9a ditandai sedang dikerjakan (#195, #196) agar tidak diambil dua kali.

## 2026-10-23 — WP6 dijeda; WP11 jam broker saat sebagian pasar tutup

- Mode 5 simbol di VPS (22 Okt 19:58–22:02 UTC): RAM dan durasi siklus aman, tetapi 21:00–22:02 UTC semua siklus
  gagal `BROKER_CLOCK_NOT_VERIFIED` karena emas/indeks jeda harian (R1 T9). VPS kembali ke 3 simbol.
- Lampiran A: temuan T9, paket WP11 (pecahan mayoritas jam dihitung atas suara segar) dengan perintah R6; WP6
  menunggu WP11. PROJECT_STATUS dan cakupan simbol di "Pemisahan data" diperbarui.

## 2026-10-23 — roadmap: WP10 biaya trading, counterfactual di WP9d, R0 dirapikan

- Lampiran A ditambah WP10: WP10a profil spread broker deskriptif (label `DESCRIPTIVE_ONLY_NOT_FOR_TUNING`,
  pagar impor) dan WP10b swap + sensitivitas biaya di `CostModel` (default 0, verdict tidak berubah); perintah R6.
- WP9d memuat aturan counterfactual kelas C: hanya `dev_dataset`, kartu WAIT forward dilarang untuk untung-rugi.
- Tabel R0 diurutkan per fase; status WP8a (#195) dan WP9a (#196); "Arah lanjutan" menunjuk WP9d/WP10.

## 2026-10-23 — roadmap: enam arah lanjutan dengan batas data dan prasyarat

- Tambahkan arah Autonomous Research, Market Intelligence, Counterfactual, Cost Intelligence,
  Scientific Memory dan Champion–Challenger sebagai panduan, **bukan** paket kerja baru.
- Tegaskan counterfactual untung-rugi hanya dari data pengembangan sebelum 13 Okt 2026,
  sedangkan kartu WAIT forward/holdout hanya untuk frekuensi pemblokir.
- Izinkan pengukuran spread forward **deskriptif saja**, tanpa penyetelan strategi atau filter.
  Prasyarat dan gerbang promosi tidak berubah; tidak ada perubahan kode, VPS atau trading.

## 2026-10-23 — roadmap: WP9 membongkar tembok blokir keputusan

- Lampiran A ditambah WP9 (prioritas Owner): klasifikasi pemblokir (A input observer, B syarat bukti terkunci,
  C persepsi, M filter pasar sah), WP9a peta tembok blokir baca-saja, WP9b input keputusan terukur + evaluasi
  bayangan di balik opsi (default perilaku lama), WP9c syarat bukti proporsional di berkas terkunci lewat gerbang
  promosi, WP9d detektor entry lewat hipotesis. Perintah siap pakai WP9a–WP9c di R6; R0/R1/R5 diperbarui.
  Hasil terbaik WP9 adalah kandidat paper, bukan izin order. Tidak ada perubahan kode.

## 2026-10-23 — WP6 tahap A di VPS; status roadmap diperbarui

- VPS: kode = `main` 23 Okt (manifest MATCH); `run-observer.ps1` memakai `--universe` bila
  `C:\Katarina\private\observer_universe.json` ada; observer mengamati 5 simbol (+XAUUSD, NAS100) sejak 22 Okt
  19:58 UTC. WP6 dimajukan sebelum WP2 karena RAM terukur cukup; jalan mundur dengan mengganti nama berkas itu.
- Roadmap: kolom Status di R1, status WP6 di R0/R5, cakupan simbol forward + CELAH per simbol di "Pemisahan data".
  PROJECT_STATUS: 100% WAIT dan penyebabnya, cakupan simbol, angka tes terbaru.

## 2026-10-23 — roadmap: aturan PR paralel yang menyentuh berkas sama

- R0: WP2 dan WP3 sama-sama mengubah `observation_ledger.py` dan semua PR membuat ulang manifest; Claude me-merge
  berurutan (WP2 → WP3 → WP8a) dan membuat ulang manifest/peta modul dengan alatnya. Kosakata status R5 wajib dipakai
  persis. Status WP2 (#190) dan WP3 (#191) diperbarui; rujukan basi di `CLAUDE.md` diperbaiki. Tidak ada perubahan kode.

## 2026-10-23 — roadmap: titik masuk pelaksana AI, cara mengambil paket, standar teknis (R10)

- Bagian baru "Mulai di sini — untuk pelaksana AI" di awal roadmap: lima langkah dari membaca aturan sampai berhenti
  setelah PR; R6.0 berlaku walau tidak dikirim terpisah. `CLAUDE.md` menunjuk ke bagian ini.
- R5: cara mengambil paket (pilih "Siap dikerjakan", cek belum diambil, tandai lewat PR draft) dan status baku;
  WP8 dipecah WP8a/WP8b. R10: standar teknis (Python 3.12, Linux + Windows, batas VPS, struktur/penamaan, data dan
  waktu, Git/PR, keamanan). R7 merujuk R10. Tidak ada perubahan kode.

## 2026-10-23 — roadmap: alur kerja lengkap, cara menulis kode (R8) dan dokumen (R9)

- Lampiran A R0 ditulis ulang: siklus tujuh langkah satu paket (Owner → pelaksana → Claude review → merge → VPS) dan
  urutan fase terkini (WP2, WP3, WP8a paralel; WP6 dan ekspor dataset; WP8b dan WP4; hipotesis nyata; WP5).
- R8 menjelaskan cara Claude menulis kode (pahami dulu, diff minimal, tes gagal dulu, kode mudah diaudit, akar
  masalah, periksa diff sendiri). R9 menetapkan tempat dan batas panjang dokumen/PR, dengan contoh buruk (R5A) dan
  contoh baik. R6.0 dan R7 merujuk R8/R9. Tidak ada perubahan kode.

## 2026-10-23 — roadmap: WP8 riset historis setup BUY/SELL antarpair

- Lampiran A ditambah WP8 (paralel dengan WP2/WP3): ekspor bar broker pengembangan ber-hash (WP8a), detektor setup
  liquidity sweep/pullback/Fibonacci/struktur pasar per sisi, simulasi ke format `Trade`, uji dengan alat Tahap 1, dan
  tabel perbandingan antarpair setelah biaya (WP8b). Data hanya sebelum 13 Okt 2026 00:00 UTC (ditolak kode bila
  melewati), BUY/SELL terpisah, tiap varian = percobaan, maks. 5 hipotesis per instrumen per sisi (batas, bukan
  target), hasil berlabel riset. Perintah siap pakai WP8a/WP8b di R6. Masukan review PM. Tidak ada perubahan kode.

## 2026-10-23 — roadmap: peta alat per tahap, status hanya di PROJECT_STATUS

- Tabel "Posisi saat ini" di roadmap diganti "Peta alat per tahap" tanpa tanggal/perkiraan; status operasional
  (observer, VPS, perkiraan kelulusan) dipindah ke `docs/PROJECT_STATUS.md`. Tahap 4–5 kini menyebut modul
  riset/adaptasi yang sudah ada dan menegaskan bahwa yang belum dimulai adalah **pembuktian resmi**. Pembagian peran
  dokumen (roadmap, PROJECT_STATUS, PR, CHANGELOG) ditulis di bagian cara membaca. Masukan review PM.

## 2026-10-23 — WP1: daftar simbol inti observer (PR #184)

- Menambah `config/observer_universe.json` dengan tujuh simbol program holdout (XAUUSD pertama),
  serta `observer_universe` yang mempertahankan nama broker persis dan mencatat simbol hilang.
- Opsi `--universe` diteruskan melalui observer canonical, tanpa mengubah perilaku bila tidak dipakai.
  Slot rotasi dikecualikan dari core, dan simbol tidak tersedia menjadi kartu WAIT dengan ledger FAILED.
- Tes unit dan integrasi baru menjaga batas read-only serta tidak ada order.
  Tidak ada berkas terkunci diubah; LIVE tetap OFF. VPS aktif tidak diubah.

## 2026-10-23 — roadmap dirapikan

- `docs/ROADMAP.md` disusun ulang: aturan tetap (prinsip, kewenangan, pemisahan data, gerbang promosi, Tahap 0–5)
  di depan, rencana kerja pelaksana menjadi **Lampiran A** di akhir. Ditambah cara membaca, daftar isi, dan tabel
  posisi saat ini. Bagian "Catatan implementasi 22 Okt" dilebur ke paragraf "Alat" Tahap 2 dan 3 (rinciannya sudah
  ada di CHANGELOG); kalimat basi Tahap 0 diperbarui.
- Aturan dokumentasi pelaksana (R2 langkah 7, R6, R7): log kerja dan hasil tes rinci ditulis di deskripsi PR, bukan
  di roadmap; roadmap hanya diubah di tabel R5 dan paragraf "Alat" tahap terkait. Isi aturan dan kriteria tahap
  tidak berubah. R6 diberi blok "R6.0 Aturan umum" (pahami dulu, larangan, pengecekan wajib, templat PR,
  daftar periksa R7, berhenti setelah PR) yang selalu dikirim bersama perintah paket; rujukan bagian diperbaiki.

## 2026-10-22 — rencana kerja perbaikan di roadmap

- `docs/ROADMAP.md`: bagian "Rencana kerja perbaikan" berisi temuan VPS 22 Okt (3 simbol saja, 100% WAIT dengan 7
  pemblokir permanen, jalur berita tanpa artikel, pengunduh tick memakan memori) dan paket kerja WP1–WP7 untuk
  pelaksana (daftar simbol eksplisit 7 simbol inti, tick streaming, diagnosis berita, jurnal kandidat riset,
  hipotesis perankingan antarpair, penerapan VPS bertahap, keputusan Owner), cara kerja standar Claude untuk
  pelaksana (urutan kerja, standar kode, pengecekan, PR), peta alur berkas observer, urutan pengerjaan (R0),
  perintah siap pakai per paket (R6) dan daftar periksa review (R7). Tidak ada perubahan kode.

## 2026-10-22 — ekspor konteks Tahap 2 ber-lineage dari tick broker Tahap 0

- `katarina.research.context_export` + `scripts/research/export_market_contexts.py` membangun `contexts.jsonl`
  untuk `validate_strategy.py market-filter` dari file tick broker ledger Tahap 0: hanya hari `STORED`/
  `STORED_WITH_GAPS` dengan hash file cocok, hanya tick sebelum entry, range/ATR dari bar tertutup, dan
  `source_sha256` yang mengikat ke file tick + parameter. Jendela yang menyentuh celah tick, CELAH split, atau
  keluar dari periode pengembangan tidak diberi konteks; alasannya dicatat di manifest. Tidak ada interpolasi.
- 8 tes alat. Tidak ada berkas terkunci yang diubah; tidak ada akses broker atau order.

## 2026-10-22 — review dan penggabungan alat roadmap Tahap 0–3

- PR #177 (penguatan reconnect/validasi), #178 (eksperimen filter Tahap 2), #179 (pembatas DEMO + laporan outbox
  Tahap 3) direview dan digabung berurutan; PR #176 (alat filter alternatif) ditutup sebagai duplikat #178.
- Catatan "belum digabung" di roadmap dan CLAUDE.md diperbarui; peta script di CLAUDE.md mencakup
  `validate_strategy.py market-filter` dan `check_demo_readiness.py`. Tidak ada perubahan kode.

## 2026-10-22 — catatan roadmap untuk review Claude/Owner

- Roadmap mencatat implementasi PR #177–#179, urutan integrasi, branch review, bukti tes/CI
  Tahap 3 dan pekerjaan yang belum terbukti. CLAUDE.md menunjuk catatan tersebut.
- Status persiapan alat dibedakan dari kelulusan tahap; kriteria roadmap dan kebijakan risiko tetap.

## 2026-10-22 — persiapan Tahap 3: pembatas DEMO dan laporan outbox

- Adapter `DemoRiskOverlay` mempertahankan veto governor lalu membatasi anggaran dan DD harian lebih ketat;
  nilai wajib eksplisit, usulan 0,5%/3% hanya dipakai tes. Boundary existing tetap menolak volume berlebih.
- `check_demo_readiness.py` membaca outbox existing secara read-only: expectancy/PF/P&L bersih, drawdown
  strategi terealisasi menurut waktu observasi, kelompok simbol/BUY/SELL/regime, biaya, slippage dan WAIT.
- Status tak jelas, outcome invalid dan position ID ganda menghalangi kelengkapan rekonsiliasi; data kosong
  bukan kelulusan. Laporan tidak memuat ID broker mentah dan tidak menghitung biaya dua kali.
- Tes sintetis dan panduan disertakan. Worker aktif, governor utama, berkas promosi dan VPS tidak diubah;
  profil final dan kelulusan berdasarkan bukti tetap diperlukan sebelum aktivasi.

## 2026-10-22 — persiapan Tahap 2 selama pengumpulan data Tahap 0

- `research/market_intelligence.py` dan perintah `validate_strategy.py market-filter` membandingkan kelompok
  pengembangan lengkap vs terfilter menggunakan alat Tahap 1, registry hipotesis dan split ber-hash yang sama.
- Filter eksperimen memakai spread/risiko, biaya/range, jam UTC, ATR/risiko, usia konteks dan aktivitas tick.
  Semua threshold wajib terdaftar; outcome dan spread exit tidak dipakai untuk memilih sinyal.
- Laporan memuat alasan WAIT, rasio biaya/MFE, dua laporan validasi, dan hash input. Menolak holdout, CELAH,
  konteks masa depan, outcome belum tersedia, duplikat, serta mismatch instrumen/split/kode.
- Dokumentasi dan tes sintetis disertakan. Ini persiapan alat, bukan kelulusan Tahap 2 atau aktivasi strategi;
  pengembangan berlanjut sambil observer mengumpulkan bukti Tahap 0.

## 2026-10-22 — verifikasi Tahap 0–1: cegah bukti kelulusan palsu

- Pemeriksa Tahap 0 menghitung satu pemulihan hanya sekali meskipun beberapa catatan uji menunjuk siklus OK
  yang sama. Pemulihan spontan dibatasi 10 menit sejak kegagalan pertama, bukan retry terakhir.
- Validasi Tahap 1 menolak outcome yang belum diketahui pada waktu laporan, posisi melintasi CELAH, pembanding
  tren tidak lengkap, kode yang tidak cocok dengan hash terdaftar, dan pendaftaran dari masa depan. Baris CELAH
  tetap terlihat sebagai penolakan; data rusak menghasilkan FAIL walau sampelnya sedikit.
- Hipotesis yang didaftarkan setelah paparan holdout tidak boleh memakai rentang holdout yang bertumpang tindih.
  CLI baru membaca berkas holdout setelah receipt tersimpan; `--code-sha256` mengikat evaluasi ke definisi kode.
- Tes regresi memakai data sintetis. Ini perbaikan alat bukti, bukan kelulusan strategi, promosi, atau verifikasi VPS.

## 2026-10-22 — Tahap 0: uji putus-sambung tercatat; observer VPS aktif

- Observer read-only berjalan di VPS sejak 22 Okt 04:24 UTC (akun demo, Algo Trading OFF); CELAH holdout
  13–22 Okt dicatat di roadmap.
- `observation_ledger.record_reconnect_test` + `scripts/ai/record_reconnect_test.py`: mencatat waktu mulai uji
  putus-sambung MT5. `data_health` menilai tiap uji dari ledger (siklus OK ≤ 10 menit setelah gangguan) dan
  menghitungnya bersama pemulihan spontan. Observer yang menyalakan ulang terminal sendiri tanpa siklus gagal kini
  terhitung lulus.

## 2026-10-22 — Tahap 1: alat validasi ilmiah

- `katarina.research.validation`: registry hipotesis append-only berantai hash (ID = hash definisi; definisi berubah =
  percobaan baru), `DataSplit` pengembangan/holdout/CELAH ber-hash, `HoldoutVault` (holdout hanya keluar lewat
  pembukaan tercatat, satu kali per hipotesis, setelah periode selesai), `CostModel` (½ spread entry + ½ spread exit +
  slippage + komisi → R bersih), penolakan kebocoran (data setelah entry, lintas batas periode, CELAH, tumpang
  tindih), pembanding tanpa trade / sisi acak / tren sederhana, walk-forward 28 hari, bootstrap blok mingguan dengan
  koreksi Bonferroni, laporan deterministik ber-hash. Holdout: ≥100 trade, PF ≥1,2, batas bawah >0; sampel kurang =
  PENDING.
- `scripts/research/validate_strategy.py` (register / development / holdout) dan protokol
  `docs/research/VALIDATION_PROTOCOL.md`. Tidak ada strategi baru dan tidak ada berkas terkunci yang diubah.

## 2026-10-22 — Tahap 0: ledger observasi, tick broker, pemeriksa kesehatan data

- `katarina.intelligence.operations.observation_ledger`: observer mencatat bid/ask/spread setiap simbol setiap siklus
  (WAIT ikut dicatat; simbol gagal dengan alasan) dan jam broker; loop kontinu menutup setiap siklus dengan status
  `OK`/`PARTIAL`/`NO_MARKET_DATA`/`FAILED` beserta alasan. Tick broker hari UTC yang selesai dan diamati diunduh per
  jam (maks satu simbol-hari per siklus, di thread pemilik), disimpan gzip CSV deterministik, celah dicatat tanpa
  interpolasi, dicoba ulang 3 kali, lalu direkonsiliasi dengan snapshot observer.
- `katarina.intelligence.operations.data_health` + `scripts/ai/check_stage0_health.py`: menilai sembilan kriteria
  Tahap 0 dari ledger secara read-only dengan hash laporan deterministik. Tidak ada berkas terkunci yang diubah;
  keputusan dan risiko tidak berubah; LIVE tetap OFF.

## 2026-10-22 — gerbang promosi ditegakkan CI

- `config/promotion_lock.json` mengunci SHA-256 19 berkas yang menentukan keputusan dan risiko aktif (otak keputusan,
  persepsi, strategi demo, Risk Governor, risiko adaptif/manual/akun, batas eksekusi demo, gerbang risiko riset,
  config risiko dan unified). Baseline `docs/governance/promotions/P-0000-baseline-20261022.json` = keadaan `main`
  saat gerbang diperkenalkan, disetujui Owner, **bukan** klaim performa.
- `katarina.governance.promotion_gate` + `scripts/governance/promotion_gate.py` (`--check`, `--hashes`, `--write-lock`):
  catatan `PROMOTION` wajib validasi PASS dengan laporan ber-hash dan persetujuan Owner. Body CI menjalankan
  `--check`; tes statis dan unit (manipulasi laporan, perubahan berkas, CRLF) ditambahkan. CODEOWNERS mencakup kunci
  dan folder promosi. Tidak ada perubahan perilaku trading; LIVE tetap OFF.

## 2026-10-22 — roadmap disempurnakan; dokumen lama disinkronkan

- `docs/ROADMAP.md`: Tahap 0 membedakan **snapshot observer** dan **tick broker** (disimpan terpisah, celah dicatat
  tanpa interpolasi, pemulihan diverifikasi); aturan **paralel vs berurutan** (pengembangan boleh paralel, kelulusan
  dan kewenangan tetap berurutan); periode tanpa data observer asli sejak 13 Okt dicatat sebagai **CELAH**, backfill
  tidak pernah dihitung forward, sampel kurang di akhir holdout = **PENDING**; profil DEMO ditegaskan sebagai lapisan
  tambahan di atas profil utama.
- `docs/architecture/RISK_PROFILE_V2.md`: hubungan profil DEMO dengan profil tunggal dan Stage 38.
- Dokumen/config yang masih menggambarkan transport ZeroMQ/TCP (`KATARINA_FINAL_WORKFLOW.md`,
  `config/transport_policy.json`, `config/execution_workflow.json`, draf bridge MT5) ditandai dipensiunkan dan
  menyebut jalur sekarang (paket MetaTrader5 Python); `KATARINA_ENVIRONMENT_RECOVERY.md` tidak lagi menyebut
  `pyzmq`/`tornado`. Tidak ada perubahan perilaku.

## 2026-10-22 — roadmap berbasis bukti

- `docs/ROADMAP.md` ditetapkan Owner sebagai dasar pengembangan: prinsip "kewenangan bertambah berdasarkan bukti",
  empat keputusan Owner, tangga kewenangan (level 0–4), aturan pemisahan data dan holdout sekali-buka, gerbang
  promosi (catatan kelulusan validasi + persetujuan Owner), serta Tahap 0–5 dengan kriteria kelulusan berangka.
- Batas drawdown harian 35% tidak berubah; profil DEMO direncanakan sebagai lapisan tambahan yang hanya memperketat.
- `PROJECT_STATUS.md`, README, dan CLAUDE.md menautkan roadmap. Tidak ada perubahan kode.

## 2026-10-22 — aturan perapian baru dan path VPS di dokumen

- `docs/maintenance/CLEANUP_PLAN.md` ditulis ulang: aturan "arsipkan, jangan hapus" diganti keputusan Owner
  "hapus langsung lewat PR, riwayat di Git", daftar identitas Katarina yang dipertahankan, status semua tahap,
  dan sisa perapian yang diketahui. Bagian perapian di CLAUDE.md dan aturan `config/` disesuaikan.
- Tiga dokumen arsitektur (full system test, portable host, unified cognitive cycle) kini memakai layout VPS
  sekarang (`C:\Katarina\code`, `C:\Katarina\python312`, `C:\Katarina\state`) alih-alih `C:\KatarinaDev`.
  Tidak ada perubahan kode.

## 2026-10-22 — sinkronisasi stop drawdown harian 35% dan status proyek

- Stop entry baru di drawdown harian **35%** (keputusan Owner) kini sama di semua tempat: `config/risk_governor_v2.json`,
  `RiskGovernor`, `DailyDrawdownTracker`, `EvidenceRiskGate` (riset; sebelumnya 2%), manifest tahap 01–40 dan dokumen
  operational hardening (sebelumnya menulis 10% harian / 20% total; config sebenarnya 35% / 35%).
- Tes baru `tests/unit/engines/test_daily_drawdown_sync.py` menggagalkan CI jika salah satu tempat berbeda.
- `docs/PROJECT_STATUS.md` dan README ditulis ulang sesuai kondisi nyata: observer VPS belum berjalan (menunggu login
  akun demo), DEMO forward tidak berjalan, edge belum terbukti, VPS dan repo setelah perampingan. LIVE tetap OFF.

## 2026-10-22 — rampingkan repo (E): sisa yang tidak terpakai

- Dihapus modul yang yatim setelah A–D: lab riset (replay kausal, rekonsiliasi tick, forensik bar, scalp
  intraday, setup precommitted, diagnostik biaya, readiness/ablation/intraday gate), perception riset
  (playbook alternatif, kalender historis, kandidat pola scalp, cost expectancy, multi-pair arbitrator) dan
  subsistem shadow/paper lama (journal, paper book, manifest, hypotheses, evidence, drift, siklus MT5 shadow,
  `mt5_shadow_lab`), beserta tesnya.
- Dihapus 20 skrip tanpa rujukan (patch VPS `install_*`, installer observer lama, skrip MT5 Stage06 interaktif,
  audit stage 01–40 dan 11–40, dll.), 5 workflow manual yang mengulang Body CI, 15 config tanpa pemuat, serta
  dependensi `pyzmq`/`tornado` (`requirements-stage07.txt` kini kosong; cek environment PC disesuaikan).
- Dipertahankan: otak canonical, observer, demo forward, Risk Governor, modul tahap 11–40, buku shadow
  prospektif (dipakai Body CI), website, EA MT5 dashboard dan bridge Stage 06. LIVE tetap OFF.

## 2026-10-22 — rampingkan repo (D): pensiunkan transport KAT1/ZMQ

- Dihapus: `adapters/transport` (codec, sesi, ZMQ, TCP, recovery), `ports/transport`, `scripts/stage07`,
  `scripts/protocol`, vektor golden, workflow `stage07-transport`, jembatan MT5 Stage07 + multi-symbol extension
  (EA, include, tes MQL5), config draft komunikasi/bridge, ADR 0009/0011/0012, dan dokumen/tes khusus transport.
- Dipertahankan: skema pesan `protocol/` (kontrak validation & health engine), EA status dashboard, EA bridge Stage 06,
  audit stage 08–10. Observer tetap memakai paket MetaTrader5 Python; tidak ada perubahan perilaku. LIVE tetap OFF.

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
