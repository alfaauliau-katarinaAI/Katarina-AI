# MEETING — rapat dan keputusan terbuka Katarina AI

**Tempat tunggal untuk hal yang masih kita rapatkan**, termasuk usulan, alternatif, keberatan teknis, keputusan
yang masih menunggu Owner/manager, dan tindak lanjut yang belum disahkan. Peserta: Owner, ChatGPT/Yura
(manager), Claude (eksekutor), serta pelaksana AI. **Berkas ini bukan roadmap, bukan antrean kerja kedua, dan
bukan log perbaikan**.

Setelah keputusan dibuat, hasil final ditulis **sekali** di [ROADMAP.md](ROADMAP.md) pada bagian yang berwenang;
topik rapat ditutup, lalu keputusan ringkas masuk "Keputusan terakhir". Hasil perbaikan yang benar-benar
diterapkan dicatat di [REPAIR_HISTORY.md](REPAIR_HISTORY.md), kondisi berjalan di
[PROJECT_STATUS.md](PROJECT_STATUS.md). Bukti kode/tes tinggal di PR dan CHANGELOG.

## Peserta dan kewenangan

| Peserta | Peran di rapat | Memutuskan |
|---|---|---|
| Owner | Pemilik proyek | Semua hal; satu-satunya untuk bagian 1–7 roadmap, gerbang promosi, kewenangan trading |
| ChatGPT / Yura | **Satu peran manager proyek** (Yura adalah nama manager dalam percakapan, bukan peserta terpisah) | Roadmap, antrean, spesifikasi paket, pembagian tugas, review/merge, koordinasi VPS |
| Claude | Eksekutor | Mengerjakan paket yang disetujui; menyampaikan bukti dan keberatan teknis |
| Pelaksana AI lain | Pelaksana paket yang didelegasikan | Menyampaikan hasil/risiko; tidak mengubah aturan Owner |

## Cara rapat

1. **Membuka topik.** Siapa pun menambah topik di "Agenda" dengan format di bawah. ChatGPT lewat PR yang hanya
   mengubah berkas ini (judul `docs(rapat): ...`) atau langsung bersama perubahan roadmap. Owner/Yura boleh menulis
   langsung di GitHub atau mengirimkannya ke ChatGPT/Claude untuk dituliskan.
2. **Menanggapi.** Tambah satu baris di bagian "Tanggapan" topik itu, diawali `[Owner]`, `[Yura/ChatGPT]`, `[Claude]` atau nama pelaksana dan tanggal. Singkat, dengan bukti
   (berkas, PR, angka). `[Yura]` dan `[ChatGPT]` merujuk **manager yang sama**, bukan dua suara. Tidak
   mengubah tanggapan orang lain.
3. **Memutuskan.** Peserta yang berwenang (tabel di atas) mengisi baris "Keputusan". ChatGPT atau Claude lalu
   memindahkan hasilnya ke `docs/ROADMAP.md`, mencatat satu baris di "Keputusan terakhir", dan menghapus topik dari
   agenda (riwayat lengkap ada di Git).
4. **Bentuk.** ±40 baris per topik. Hanya topik **belum final** yang bertahan di Agenda; histori keputusan
   singkat tetap pada bagian "Keputusan terakhir" dan commit Git. Tanpa laporan teknis perbaikan atau log kerja.
   Aturan tetap Owner (LIVE OFF, Risk Governor, batas 35%, gerbang promosi, holdout) hanya berubah dengan keputusan Owner.

**Format topik**

```
### Dn — <judul>
Pengusul · tanggal · status: Terbuka | Menunggu Owner | Diputuskan | Ditolak
Usulan: <apa dan kenapa, 1–5 baris, dengan bukti>
Pertanyaan: 1. ... 2. ...
Tanggapan:
- [Peserta tanggal] ...
Keputusan: <diisi peserta berwenang>
Tindak lanjut: <paket/PR/pemilik>
```

## Agenda

### D2 — Mengaktifkan `measured_inputs` di VPS
Claude · 29 Okt 2026 · status: Terbuka (data dikumpulkan)
Usulan: WP9b sudah berjalan dalam mode bayangan; tabel `decision_shadow` mencatat keputusan mode `measured_inputs`
sejak 28 Okt 16:57 UTC. Setelah ≥ 3 hari bursa, Claude menjalankan peta pemblokir (WP9a) untuk kedua mode dan
melaporkan di sini berapa kartu yang tidak lagi diblokir pemblokir kelas A.
Pertanyaan: 1. Owner setuju mode aktif diganti ke `measured_inputs` bila laporan menunjukkan perubahan hanya pada
tiga pemblokir kelas A? (Hasil terbaik tetap `PAPER_OBSERVATION_ONLY`, bukan izin order.)
Tanggapan:
Keputusan:
Tindak lanjut: Claude (laporan ±2 Nov), Owner (keputusan).

### D3 — Sisa 19 berkas terkunci di VPS
Claude · 29 Okt 2026 · status: Menunggu Owner
Usulan: 19 berkas (0,9 MB) di `C:\Katarina\_roadmap_validation` diberi larangan akses oleh pelaksana pada 27–28 Okt
dan tidak bisa dihapus dari sesi Desktop Commander. Tidak mengganggu observer.
Pertanyaan: 1. Owner menghapusnya sendiri lewat Remote Desktop sebagai Administrator (klik kanan → Properties →
Security → Advanced → ganti pemilik, lalu hapus folder)?
Tanggapan:
Keputusan:
Tindak lanjut: Owner.

### D4 — Target Agentic AI Katarina: fase, bukti kelulusan, dan batas kewenangan
Owner/Yura (usulan untuk review Claude) · 29 Okt 2026 · status: Terbuka
Usulan: Tujuan akhir adalah agent riset yang dapat merencanakan, menggunakan alat, menguji, menyimpan pembelajaran,
melanjutkan tugas, dan mempertanggungjawabkan hasil secara mandiri. Otonomi riset **bukan** izin mengubah strategi,
kode trading, Risk Governor, holdout, atau kewenangan order. Prioritaskan komponen existing; jangan membuat engine paralel.

**Lima prinsip yang diminta dibahas:**
1. Audit kemampuan existing dan buktikan gap sebelum membangun modul baru.
2. Benchmark agentic (ketepatan tugas/alat/bukti/recovery) terpisah dari uji keunggulan trading setelah biaya.
3. WP14 auditor data baca-saja tetap prioritas agentic pertama setelah WP13 dan WP8c (sudah masuk antrean).
4. Memori ilmiah dan checkpoint memakai storage/registry existing; wajib hash, jejak sumber, idempotensi, restart aman.
5. Agent DEMO hanya sesudah Tahap 0–3, gerbang strategi, dan persetujuan Owner; LIVE perlu gerbang terpisah.

**Fase dan hasil yang ingin diuji:**
- A — WP14: audit ledger/tick, jam broker UTC/DST, kesegaran, gap, duplikat, integritas hash dan rekonsiliasi.
  Keluaran PASS/BLOCKED/NO_DATA/PENDING harus sesuai kontrak alat resmi, deterministik, disertai bukti/sumber dan
  alasan; tes data sehat/rusak/kosong/basi; hanya membaca, tidak mengubah observer atau verdict promosi.
- B — Autonomous Research (setelah Tahap 1 lulus untuk setidaknya satu strategi): (1) planner tujuan→tugas→
  dependensi/anggaran, (2) pemilihan alat dari allowlist, (3) evaluator ilmiah independen (baseline, walk-forward,
  biaya, statistik, anti-lookahead/anti-leak), (4) memori hipotesis/hasil negatif/sumber/hash,
  (5) checkpoint/recovery yang menolak input, izin, atau versi tidak cocok; tanpa eksperimen ganda.
- C — Benchmark & Controlled DEMO: (6) tugas benchmark dibekukan dan terpisah dari holdout strategi; ukur
  penyelesaian benar, reproduktibilitas, biaya, kegagalan, izin, dan pemulihan versus baseline; (7) DEMO hanya
  dengan approval Owner setelah syarat roadmap, pembatas Risk Governor dan bukti fill/slippage/komisi/swap broker.
  Hasil shadow/paper bukan bukti fill dan bukan bukti profitabilitas.

**Kriteria usulan:** 100% temuan penting punya sumber; input+versi sama menghasilkan keluaran sama;
nol tindakan di luar izin; recovery tidak menggandakan hasil; tugas gagal menjelaskan alasannya;
peningkatan agentic teruji independen; expectancy bersih dan risiko strategi divalidasi terpisah.
Ambang statistik/sampel benchmark ditentukan setelah audit dan tidak boleh disamakan dengan kelulusan tahap trading.

Pertanyaan: 1. Modul existing apa yang sudah/belum memenuhi tujuh kemampuan beserta bukti dan tes gap?
2. Bagaimana spesifikasi paket minimum, ketergantungan, kontrak laporan, anggaran, dan benchmark independen?
3. Apakah ada konflik dengan kriteria Tahap 0–5 atau aturan Owner yang harus diputuskan sebelum implementasi?
Tanggapan:
- [ChatGPT/Yura 29 Okt] Rekomendasi PM: WP14 dulu; tahapan lain tetap usulan, bukan persetujuan implementasi/promosi.
- [Claude 30 Okt] Pemetaan modul sudah ada di roadmap "Arah lanjutan → Usulan agentic AI" (tabel P1–P5). Fase A =
  WP14 (spesifikasi R4, antrean #6). Fase B butuh paket baru setelah Tahap 1 lulus untuk satu strategi; modul lama
  `lab/continuous_research_lab.py` dan `lab/autonomous_research.py` belum punya tes checkpoint/recovery, jadi audit gap
  dilakukan saat itu. Tidak ada konflik dengan Tahap 0–5 selama otonomi = riset + usulan, bukan otorisasi finansial.
Keputusan: Menunggu pembahasan Claude dan keputusan pihak berwenang.
Tindak lanjut: Claude audit existing dan berikan opsi paket serta tes; Owner memutuskan perubahan gerbang/kewenangan.

### D5 — Perapian branch lama dan disiplin PR tanpa tumpukan
Owner/Yura (usulan untuk review Claude) · 29 Okt 2026 · status: Terbuka
Usulan: Pertahankan satu basis `main` untuk PR baru, hindari PR bergantung pada branch PR lain, dan hapus branch
yang terbukti tidak digunakan setelah audit commit/PR. Jangan merge gabungan perubahan lama untuk sekadar bersih-bersih.
Audit 29 Okt: PR terbuka 0 saat diperiksa; kandidat sisa branch PR ditutup tanpa merge adalah
`chatgpt/docs-pr-review-blockers-20261023`, `chatgpt/dc2-repair-review-20261027`,
`chatgpt/stage0-clock-audit-20261028`, `chatgpt/mt5-stage0-10day-readonly-20261028`,
`chatgpt/claude-full-system-audit-20261028`; branch uji izin `chatgpt/write-permission-check-20261029`
identik dengan `main`. Kelima branch lama masih mengandung commit unik, bukan otomatis aman dihapus.
Pertanyaan: 1. Apakah seluruh commit unik sudah diganti/ditolak dengan alasan atau perlu dipecah menjadi paket baru?
2. Apakah WP13, bridge MCP/VPS, dan broker discovery masih digunakan dan siapa pemiliknya?
Tanggapan:
- [ChatGPT/Yura 29 Okt] Jangan hapus branch aktif/bernilai tanpa verifikasi; tidak mengubah runtime VPS.
- [Claude 30 Okt] Audit: kelima branch `chatgpt/*` lama sudah terhapus; `chatgpt/write-permission-check-20261029`
  tidak ada lagi. Sisa yang aman dihapus: `chatgpt/wp13-clock-since-20261029` (#219 ditutup, digantikan #233) dan
  `feat/roadmap-stage0-broker-discovery-20261022` (#183 ditutup tanpa merge; discovery seluruh broker digantikan
  universe eksplisit WP1/T8). Sesi Claude tidak diizinkan menghapus branch (403) → manager/Owner menghapusnya lewat
  tombol "Delete branch" di #219 dan #183. `claude-vps-bridge` dan `claude-openai-mcp`
  (jembatan MCP Claude↔OpenAI, tanpa PR, tidak dipakai runtime) dibiarkan sampai Owner memutuskan.
Keputusan: Menunggu verifikasi dan keputusan pembersihan.
Tindak lanjut: Claude audit dependensi dan commit unik; manager menyetujui penghapusan kandidat terverifikasi lewat mekanisme GitHub.

### D6 — Bukti jam broker untuk observer live: NTP + tick segar sudah independen
Claude · 30 Okt 2026 · status: Terbuka
Usulan: K-01/K-02 meminta observer canonical menolak semua siklus sampai ada dokumen jam resmi broker. Untuk data
**live** itu tidak perlu dan akan menghentikan Tahap 0: jam VPS kini disinkron NTP (`time.windows.com`, T13), jadi
selisih `symbol_info_tick` terhadap jam host **adalah** pengukuran langsung dari sumber UTC independen (30 Okt:
+7176–7191 dtk = +2 jam bulat, 3 FX segar). Dokumen broker/DST hanya penting untuk data **historis** (WP8c).
Bukti VPS: sejak WP12 (28 Okt 16:57 UTC) 1.223 siklus, offset konsisten 2,0; hari tick 28 Okt rekonsiliasi
379/379, 334/334 (cocok sempurna); 0 order. Bila `require_evidence=True` dari berkas yang tidak ada, semua siklus
`FAILED` → 0 data forward sampai dokumen itu ada (mungkin tidak pernah).
Usulan teknis: (a) bukti live = host NTP tersinkron (status `w32tm` dicatat per hari) + ≥ 3 tick segar sepakat
pada jam bulat + WP13 (buang quote basi, tutup akhir pekan); simpan basis ini di ledger per siklus;
(b) berkas bukti broker tetap wajib untuk WP8c (historis) dan sebagai penguat bila tersedia; (c) siklus tanpa NTP
tersinkron dicatat `NO_TRUSTED_HOST_CLOCK`, bukan diam-diam OK.
Pertanyaan: 1. Manager setuju jalur (a) menggantikan syarat dokumen broker untuk observer live? 2. Bila tidak,
dari mana dokumen jam resmi broker akan diperoleh, dan siapa yang mengambilnya?
Tanggapan:
- [Yura/ChatGPT, 30 Okt 2026] Analisis Claude diterima **sebagai arah desain untuk diuji bersama Jules nanti**, bukan penerimaan otomatis seluruh data sebagai valid. NTP host merupakan referensi UTC independen; tiga quote dari **satu broker** hanya cross-check offset, bukan tiga sumber jam independen. Setiap siklus wajib mencatat status kesehatan NTP, usia tick dan timestamp penerimaan, identitas/hash server, offset integer dan konsensus, serta alasan penolakan; wajib fail-closed pada NTP tidak terpercaya, quote stale, ketidakcocokan offset, market closed, DST ambigu, atau pergantian broker/VPS yang belum terverifikasi. Jangan mengganti/menurunkan guard produksi hanya untuk menjaga angka success. Untuk bar historis WP8c tetap diperlukan provenance historis terpisah. 
- [Owner, 30 Okt 2026] "Oke, catat dulu dan kerjakan bersama nanti di Jules." Implementasi WP13 **ditunda** untuk sesi kerja bersama Jules; tidak ada otorisasi merge/deploy dari catatan ini.
Keputusan: **Arah desain dicatat untuk penelaahan dan pengujian lanjutan**, belum berlaku sebagai perubahan acceptance WP13 atau pengecualian bukti jam. Sebelum implementasi, bandingkan jalur NTP+tick dengan syarat fail-closed R4, siapkan tes adversarial dan dapatkan persetujuan review hasil. LIVE OFF.
Tindak lanjut: Yura siapkan spesifikasi/tes bersama Jules pada sesi berikutnya dalam PR #233 yang sama; Claude review independen. Jangan membuat PR WP13 baru, jangan mengubah runtime VPS/observer sekarang.

### D7 — Audit struktur 30 Okt (A-01–A-11): verifikasi dan urutan tindak lanjut
Yura/ChatGPT (laporan `KATARINA_AI_AUDIT_STRUKTUR_2026-10-30.md`, dilampirkan Owner) · 31 Okt 2026 · status: Terbuka
Usulan: audit baca-saja `main` `85f8aef` + #233 `76ce7e8`; 2 P0 (WP13 belum merge, Tahap 0 belum lulus),
6 P1 (WP8c bukti, WP6 reboot, OAuth `/oauth/status`, reviewer independen, dokumen status usang, WP10a di VPS), 3 P2.
Verifikasi Claude (31 Okt 00:20 WIB, GitHub + VPS baca-saja):
| ID | Hasil cek | Bukti / catatan |
|---|---|---|
| A-01 | **Benar** + temuan baru | #233 HEAD `76ce7e8`: CI Body/Ubuntu/Windows PASS, `mergeable_state=clean`, 34 berkas, tidak menyentuh `promotion_lock`. Observer kini memakai `inspect_host_clock` + dua sampel tick; siklus gagal tetap ditulis `FAILED` + alasan (`close_ledger_cycle`). Review Claude di #233 (`f672648`) sudah usang |
| A-01 baru | **Penghalang deploy** | WP13 menolak NTP bila `Time since Last Good Sync Time` > **14.400 s**. VPS: `Poll Interval: 15 (32768s)` (±9,1 jam), saat cek **27.146 s** sejak sinkron terakhir → `NTP_SYNC_STALE`. Bila #233 dideploy apa adanya, sebagian besar siklus `FAILED` dan Tahap 0 gagal `cycle_success_rate`. Butuh `MaxPollInterval` ≤ 13 (8.192 s) atau resync terjadwal — **perubahan setelan sistem VPS, perlu izin Owner**; jangan melonggarkan batas di kode |
| A-02 | Benar | Hitungan sejak 28 Okt 16:57 UTC; `--since` baru ada di #233 |
| A-03 | Benar | `us_release_calendar.csv` hanya header; belum ada CLI pembuat sampel (RH-005) |
| A-04 | Benar | Task observer memakai Interactive Logon; reboot tanpa login belum diuji |
| A-05 | Benar di kode, **tidak aktif di VPS** | `server.js` baris 151–156 mengembalikan `profile` (user_info MQL5) tanpa auth; `listen(PORT,'0.0.0.0')`. Tidak ada proses node `oauth_gateway` di VPS. Lokasi deploy lain belum diketahui |
| A-06 | Benar | `CODEOWNERS` hanya owner; PR 30 Okt bisa di-merge tanpa approval → review tidak diwajibkan proteksi branch |
| A-07 | Benar sebagian | `PROJECT_STATUS` (#239) masih menulis #233 "konflik + blocker P0"; usang sejak `76ce7e8`. Diperbarui saat #233 merge (#233 sendiri mengubah berkas itu) |
| A-08 | Benar | WP10a belum dijalankan di VPS |
| A-09–A-11 | Setuju, tidak mendesak | A-10: paket kosong `domain/ports/entrypoints` sudah tercatat di peta modul (D=3); jangan refactor sebelum Tahap 1 |
Koreksi kecil: tabel subsistem menyebut "7 simbol inti masih rencana"; observer VPS saat ini menerima **5 simbol** per siklus.
Pertanyaan: 1. Manager: urutan WP13 = review independen `76ce7e8` → merge → izin Owner ubah poll NTP VPS → deploy terkendali?
2. Owner: izinkan `w32tm` MaxPollInterval 13 (atau resync terjadwal) sebelum deploy WP13? 3. Owner: wajibkan ≥1 approval
di branch protection (A-06)? 4. Owner/manager: `oauth_gateway/` diperbaiki (tanpa `profile`, bind `127.0.0.1`) atau dihapus
bersama ekstraksi website?
Tanggapan:
- [Claude 31 Okt 2026] Audit akurat. Prioritas tertinggi baru adalah syarat NTP: tanpa itu WP13 yang benar justru
  menggagalkan Tahap 0. Claude siap melakukan review independen `76ce7e8` bila manager meminta (tanpa merge/deploy).
Keputusan (Manager, 31 Okt 2026; [komentar keputusan PR #240](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/240#issuecomment-6528911795)):
1. **D7-M1 — Urutan WP13 disetujui bersyarat:** minta **Claude melakukan review independen sekarang** terhadap
   PR #233 pada HEAD `76ce7e8f0bf8645217c6800f2df462441e7ed61a`. Audit aktual mencakup sumber UTC
   host NTP tepercaya, ≥3 tick progresif (bukan tiga sumber jam independen), perubahan offset/DST dan broker,
   alasan FAILED yang recoverable tanpa publikasi UTC palsu, Stage0 `--since`/hari parsial/`NO_DATA`/0 order,
   kesesuaian manifest, FakeBroker/tes negatif, dan scope. **Review lama `f6726480` tidak mencakup HEAD ini.**
   Merge kode **hanya setelah** review independen menyetujui SHA final, CI Body/Ubuntu/Windows PASS pada SHA
   yang sama, `mergeable=true`, dan tidak ada blocker P0. `MERGED` tidak berarti `DEPLOYED` atau Tahap 0 PASS.
2. **D7-M2 — Perubahan NTP VPS belum diizinkan:** selisih batas bukti WP13 (umur sync ≤14.400 detik) dan
   poll VPS 32.768 detik merupakan **blocker deployment P0**. Pertahankan batas fail-closed kode; jangan
   meningkatkan tingkat keberhasilan dengan menurunkan guard. Siapkan rencana W32Time `MaxPollInterval=13`
   (8.192 detik) **atau** sinkron ulang terjadwal, tetapi nilai poll bukan bukti sync berhasil.
   Wajib periksa sumber NTP independen, waktu sync aktual, umur, stratum, offset, kegagalan, interval
   berulang, kompatibilitas OS, backup konfigurasi serta rollback. **Izin eksplisit Owner diperlukan
   sebelum mengubah setelan VPS**, dan deployment/restart observer memerlukan persetujuan terpisah.
3. **D7-M3 — Tata kelola PR:** Manager merekomendasikan minimal **satu approval reviewer independen**,
   required CI Body/Ubuntu/Windows, invalidasi approval usang saat HEAD berubah, dan larangan force-push
   pada `main`. Belum ada izin mengaktifkan/mengubah aturan proteksi; tunggu keputusan Owner.
4. **D7-M4 — OAuth MQL5:** Manager memilih **perbaiki, jangan langsung hapus**, jika gateway masih
   diperlukan. Hindari paparan anonim `lastAuth.profile`, batasi akses, bind loopback
   `127.0.0.1` secara default dan audit kemungkinan deployment di luar VPS. Perubahan kode
   dikerjakan sebagai paket terpisah setelah prioritas P0; bila ternyata obsolete, usulkan
   penghapusan setelah audit dependensi.
5. **D7-M5 — Pencatatan jujur:** status `docs/PROJECT_STATUS.md` / Roadmap diperbarui setelah
   merge #233 yang benar-benar terverifikasi. Riwayat perbaikan hanya mencatat bukti yang telah
   terjadi; bukti Stage0 10 hari dan dataset historis WP8c tetap terpisah.
6. **D7-M6 — Batas operasi tidak berubah:** LIVE OFF, 0 order; tidak ada deployment,
   restart observer, perubahan Risk Governor, promotion lock, atau pembukaan holdout.

Tindak lanjut:
- **Claude:** lakukan review independen formal pada HEAD #233, laporkan temuan/kesimpulan ke manager;
  jangan merge atau deploy berdasarkan review lama.
- **Owner (menunggu keputusan):** (a) izin atau tolak perubahan sinkronisasi NTP VPS dengan rencana
  backup/rollback, (b) izin atau tolak pengaturan minimal satu reviewer independen di `main`.
- **Manager:** evaluasi review SHA final; merge hanya sesudah seluruh gerbang terverifikasi,
  lalu koordinasikan pencatatan dokumen tanpa menandai Stage0 PASS/deployed.
- **PR #240 (dokumen rapat saja):** dapat di-merge setelah CI HEAD final Body/Ubuntu/Windows PASS
  dan `mergeable=true`; tidak membawa perubahan runtime atau izin operasi.


#### D7 — Keputusan Owner dan closeout batch (31 Okt 2026)

Bagian ini menggantikan checkpoint berulang sebelumnya; detail riwayat tetap tersedia di Git.
Koordinasi teknis dan bukti per SHA: [Issue #249](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/249).

| Keputusan | Ketentuan yang tetap berlaku |
|---|---|
| D7-M7 | Regresi WP13 `35323998` fail-open tidak boleh di-merge; CI hijau tidak menggantikan pemeriksaan guard |
| D7-M8 | Pulihkan pada PR #233 yang sama dengan commit biasa, pertahankan D7, tanpa force-push atau PR duplikat |
| D7-M9 | Review harus mengikat SHA final: NTP nyata, ≥3 tick progresif, identitas broker, karantina offset, ledger failure/recovery, `--since`, tes negatif, manifest dan CI |
| D7-M10 | Rollover 17:00 New York merupakan paket terpisah; hasil historis/ledger tidak boleh diubah retroaktif |
| D7-M11 | Guard umur NTP 14.400 detik tidak dilonggarkan; izin sistem NTP dan governance kemudian ditegaskan D7-M13/M14 |
| D7-M12 — Owner SETUJU | Hentikan writer task Jules WP13; jangan delete/resume sandbox lama. Penutupan batch juga mencakup WP15/WP8d/WP16 |
| D7-M13 — Owner SETUJU | Perubahan konfigurasi NTP dengan backup/rollback dan verifikasi; bukan izin deploy, restart observer/MT5 atau trading |
| D7-M14 — Owner SETUJU | ≥1 approval independen sah, required CI Body/Ubuntu/Windows, stale approvals gugur, tanpa force-push; implementasi pengaturan memerlukan admin yang berwenang |
| D7-M15 — Owner SETUJU | Implementasi/pengujian rollover terpisah, DST dan denominator diuji; tanggal aktivasi resmi harus disahkan dan tidak mendahului merge |

**Status closeout:**

- **WP13 #233 `dd6d9b50`:** kode produksi sama baseline aman `76ce7e8f`; review Claude dan konfirmasi delta Manager tersedia. Body/Ubuntu/Windows PASS. Belum ada APPROVED independen.
- **WP15 #244 `b437fe13`:** jalur override retroaktif di CLI/assessor dihapus, default aktivasi `None`; legacy `fx_session_open` dipertahankan. Uji lokal unit 1.329, static 72 (4 skip), integration 216 PASS; manifest MATCH 306. CI final dan review revisi masih harus diverifikasi.
- **WP8d #248 `ca17f7f0`:** mapping canonical→broker `.vx`, sorting timestamp kronologis dan provenance tanpa path privat diperbaiki. Uji lokal unit 1.332, static 72 (4 skip), integration 216 PASS; manifest MATCH 306. CI final dan review revisi masih harus diverifikasi.
- **WP16 #247 `99c06da7`:** status tanpa profil, bind loopback default; tes statis ulang 4/4 PASS, CI 3/3 PASS. Belum ada APPROVED independen; belum deploy.
- **Writer:** CI Auto-Fixer Jules OFF terverifikasi setelah reload. WP13 dan WP16 pernah diverifikasi paused persisten; WP15/WP8d belum mempertahankan pause secara konsisten. Jangan menyamakan Ready for review dengan Paused. Manager memegang penulisan revisi, Claude diminta read-only; pembaruan branch memakai fast-forward dengan expected SHA. Konflik HEAD wajib direkonsiliasi, bukan ditimpa.
- **NTP (bukti historis, bukan pengukuran baru):** MaxPollInterval 15→13 telah diterapkan dengan backup/rollback. Dua pengamatan 30 Okt 19:28:31 dan 19:38:36 UTC menunjukkan State=Sync, source tepercaya, stratum 5, leap/error 0 dan usia sync berkurang. Tidak ada pemeriksaan/perubahan VPS pada closeout Work Mode ini; bukti tersebut bukan Tahap 0 PASS atau izin deploy.
- **Governance:** review GitHub yang diperiksa berstatus COMMENTED, bukan APPROVED independen. Koneksi GitHub tidak membuktikan pengaturan branch protection aktif; verifikasi admin masih tertunda. PR #241 tetap belum merged, dan perubahan dokumen ini memerlukan CI/review pada SHA baru.

**Yang masih memerlukan keputusan/verifikasi:** penghentian persisten WP15/WP8d, review independen sah pada SHA final, penerapan/verifikasi branch protection oleh admin, dan tanggal efektif rollover di masa depan. Kalender rilis resmi/bar historis broker tetap belum tersedia untuk validasi operasional WP8d. Aktivasi rollover tidak dilakukan dalam batch ini.

**Batas Owner terbaru:** LIVE OFF, zero orders, tanpa deploy VPS atau aktivasi trading. Risk Governor, promotion_lock, holdout dan data/ledger historis tetap. MERGED ≠ DEPLOYED ≠ STAGE0 PASSED. Tidak ada izin operasional tambahan dari closeout ini.

### D10 — RAPAT OWNER: bukti observasi 10 hari bursa (dibuka 4 Nov 2026, Yura)

**Status: DISKUSI TERBUKA; TIDAK ADA perubahan kode, cutoff, atau kelulusan yang disahkan oleh catatan ini.**
Owner meminta menyelesaikan blocker Stage 0, WP6, sesi broker D9 dan 49 tes error P0, lalu membahas arti bukti 10 hari bursa secara ilmiah. **Tidak boleh menyatakan 10 hari terpenuhi tanpa 10 hari riil**, memalsukan data, atau mengecualikan kegagalan di jam pasar yang benar-benar buka.

#### KEPUTUSAN D10-K1 — Dua jalur paralel (Owner SETUJU, 4 November 2026)

Owner memilih **Stage 0 dan riset kemampuan trading dijalankan paralel**, dengan **kelulusan yang wajib terpisah**. Ini keputusan manajemen jadwal kerja, **bukan** perubahan ambang Stage 0, izin mengaktifkan order, membuka holdout, deploy, atau promosi tahap.

- **Jalur A — Keandalan sistem:** observasi Stage 0 tetap mengikuti ≥10 hari bursa berturut-turut, ≥98% siklus, 9 kriteria kesehatan, validasi sesi D9, serta 0 order. Ledger Stage 0 tidak dipakai untuk mencari/menyetel parameter trading.
- **Jalur B — Validasi trading offline:** gunakan alat `katarina.research.validation` dan `scripts/research/validate_strategy.py` yang sudah ada. Validasi *awal* dapat menggunakan data historis development yang sah dan alat sintetis untuk menguji determinisme, biaya, baseline, no-lookahead, dan walk-forward. Riset strategi BUY dan SELL didaftarkan sebagai hipotesis terpisah per simbol dan regime, sesuai `docs/research/VALIDATION_PROTOCOL.md`; tidak membaca holdout atau data forward Stage 0 sebagai data pengembangan.
- **Gerbang trading berbeda:** expectancy bersih development positif dan mengalahkan 3 baseline; holdout hanya setelah prasyarat dan izin, minimal 100 trade, PF ≥1,2, lower 95% corrected CI >0, risiko DEMO memenuhi batas; sebelum LIVE masih mensyaratkan DEMO forward ≥3 bulan/200 trade dan otorisasi Owner (roadmap).
- **Penanggung jawab:** Yura memeriksa integritas bukti dan scorecard terpisah; Claude mempersiapkan riset offline, test & PR yang aman; Owner memutuskan instrumen pembanding, prioritas kandidat, host riset terpisah, dan izin penilaian/promotion yang relevan.
- **Status:** `PARALLEL_WORK_APPROVED` / `STAGE0_IN_PROGRESS` / `TRADING_EDGE_UNPROVEN`. PR rapat tidak mengubah produksi atau kriteria.

#### KEPUTUSAN D10-K2 — BUY/SELL dipisah, logika boleh berbeda (Owner SETUJU, rapat 4 Nov 2026)

Owner menyetujui **BUY dan SELL diuji sebagai hipotesis terpisah**; aturan masuk, kondisi pasar, pengelolaan keluar, serta kriteria pembatalan dapat berbeda sesuai bukti. Tidak boleh memaksakan simetri BUY=SELL. Ini keputusan desain riset, **bukan** penerimaan strategi, parameter, kandidat tertentu, atau izin trading.

**Kandidat pembahasan (BELUM disetujui untuk uji final):** mulai dari XAUUSD pada data development historis yang sah, dengan maksimal 5 hipotesis per instrumen per sisi sebagaimana roadmap. Disarankan paket awal 3 BUY dan 3 SELL (semuanya independen dan belum teruji):
- BUY B1: sweep likuiditas sisi bawah lalu reclaim/rejection yang terkonfirmasi secara kausal, invalidasi di bawah sweep.
- BUY B2: pullback trend naik menuju area demand/support yang terdefinisi, konfirmasi pembalikan, invalidasi di bawah struktur.
- BUY B3: breakout resistansi terkonfirmasi body lalu retest bertahan, invalidasi bila kembali ke bawah breakout.
- SELL S1: sweep likuiditas sisi atas lalu rejection/reclaim ke bawah, invalidasi di atas sweep.
- SELL S2: pullback trend turun menuju supply/resistance, konfirmasi pelemahan, invalidasi di atas struktur.
- SELL S3: breakdown support terkonfirmasi body lalu retest gagal, invalidasi bila kembali di atas support.

**Belum menentukan** timeframe, lookback, ambang sweep, ukuran candle/volume, stop/TP, universe pembanding, strategi kandidat yang benar-benar dipilih, ataupun prioritas eksekusi; semuanya harus ditetapkan dan didaftarkan **sebelum mengukur hasil**. Tidak menguji semua variasi parameter gratis: setiap variasi yang berubah = hipotesis baru dan menambah jumlah percobaan.

**Batas validasi yang tidak berubah:**
1. Hipotesis registry terpisah per `symbol/side/regime/playbook/rules/parameters/code_sha256`; data training/development sebelum cutoff riset; **jangan baca holdout atau gunakan observasi forward Stage 0 untuk optimasi**.
2. Evaluasi kausal di waktu entry; stop/exit dan biaya broker spread, slippage, komisi, swap ditentukan sebelum pengujian; sensitivity biaya 1,5x/2x.
3. Walk-forward pengembangan lipatan 28 hari, tiga baseline, expectancy **bersih** > 0 dan mengalahkan baseline; tes determinisme, data gap/no-lookahead dan laporan semua kegagalan.
4. Gerbang holdout/DEMO kelak: minimal 100 trade holdout, PF net ≥1,2, batas bawah CI 95% >0 setelah koreksi jumlah percobaan, drawdown dalam profil DEMO; pembukaan holdout sekali sesuai governance, **bukan sekarang**.
5. Tiap sisi melaporkan jumlah trade, expectancy net, PF net, drawdown, winrate, CI, jam/regime, spread/slippage, dan failure reasons terpisah; evaluasi juga risiko korelasi jika suatu saat kedua sisi digabung.
6. Sampai semua gate dan izin Owner terpenuhi: **Level 0, LIVE OFF, 0 order**. Penelitian offline pada host terpisah jika membutuhkan MT5/data M5 broker; dilarang mengganggu VPS Stage 0.

**Agenda yang masih terbuka:** Owner memilih daftar kandidat awal dan instrumen pembanding; Claude kemudian menyusun pre-registration, prasyarat dataset dan tes mekanisme pada branch/PR review, bukan mengeksekusi trading. **Status: `BUY_SELL_SEPARATE_APPROVED` / `CANDIDATES_UNDECIDED` / `EDGE_UNPROVEN`.**

#### KEPUTUSAN D10-K3 — Uji tiga pasangan sebagai enam hipotesis terpisah (Owner SETUJU, 4 Nov 2026)

Owner memilih **seluruh tiga pasangan kandidat** untuk diteliti secara terpisah, bukan otomatis menggabungkan entry BUY/SELL. Keputusan ini menetapkan *cakupan dan urutan evaluasi*, **belum** menetapkan aturan angka, parameter, timeframe, data yang sah, pelaksanaan backtest, atau mengesahkan profit.

**Kandidat terpilih untuk dirancang (XAUUSD):** `B1` BUY liquidity sweep bawah, `S1` SELL liquidity sweep atas; `B2` BUY trend pullback demand, `S2` SELL trend pullback supply; `B3` BUY breakout+retest, `S3` SELL breakdown+retest. Semua enam memiliki ID hipotesis dan kartu hasil sendiri. Tidak ada asumsi bahwa pasangan sisi simetris. Batas roadmap maksimal 5 hipotesis per instrumen per sisi tetap.

**Aturan registrasi sebelum pengujian (mengikuti `docs/research/VALIDATION_PROTOCOL.md`):**
1. **Audit data dahulu.** Pastikan dataset *development* historis yang diizinkan, catat `dataset_sha256`, metadata broker `.vx`, server-to-UTC, zona DST, harga bid/ask dan gap; `split.json` dan `split_sha256` ditetapkan sebelum hasil terlihat. **Data Stage 0 forward dan holdout tidak boleh dipakai untuk menyetel.**
2. Untuk **setiap** `B1/S1/B2/S2/B3/S3`, definisikan tepat satu sisi `BUY` atau `SELL`, `symbol`, `regime`, `playbook`, `rules`, `parameters`, serta `code_sha256`: lookback, timeframe, konfirmasi candle (hanya candle tertutup), kondisi entry, invalidasi, stop/exit, maksimum holding, syarat WAIT, biaya. Jangan meniru harga hasil masa depan. Nilai parameter **belum diputuskan pada rapat ini**.
3. **Freeze batch enam hipotesis sebelum melihat P/L kandidat pertama** menggunakan registry hash berantai `registry.jsonl`; ID = SHA-256 definisi kanonik. Catat seluruh percobaan di registry yang sama. Perubahan parameter/logika setelah melihat hasil = **ID dan percobaan baru**, bukan overwrite atau membuang kegagalan. Batas maksimum 5/instrumen/sisi berlaku pada kandidat yang diterima untuk riset; setiap varian tambahan harus dipertimbangkan menurut batas dan aturan governance.
4. **Freeze biaya** dalam `costs.json` (spread aktual dari sumber sah, komisi, slippage konservatif, swap long/short) dan jalankan sensitivitas 1,5x/2x. Jika sumber biaya belum valid = `BLOCKED_EVIDENCE`, bukan angka nol atau asumsi harga ask=bid.
5. **Uji mekanisme terlebih dahulu dengan fixture sintetis** untuk membuktikan kausalitas/no-lookahead, determinisme, invalidasi yang benar, gap handling, alasan WAIT. Ini **bukan** bukti strategi profit.

**Urutan eksekusi sesudah registry dan data valid (semua enam sudah terkunci sebelumnya):**
- **Gelombang 1 — B1 dan S1:** liquidity sweep, **dua laporan independen**.
- **Gelombang 2 — B2 dan S2:** trend pullback, **dua laporan independen**.
- **Gelombang 3 — B3 dan S3:** breakout/breakdown-retest, **dua laporan independen**.
- Urutan ini hanyalah urutan komputasi untuk menghemat sumber daya, **bukan seleksi kandidat pemenang setelah melihat hasil**. Semua enam tetap dievaluasi pada split, periode, pengaturan biaya, baseline dan anggaran komputasi yang sebanding; setiap gagal/NO_TRADE/NO_DATA dilaporkan.
- Pengembangan: walk-forward 28 hari, tiga baseline wajib (tidak trade, random same timing+exit, simple trend); laporan per sisi mencakup trade count, expectancy **net**, PF net, max DD, winrate, CI, spread, biaya, sensitivitas, variasi sesi/regime, alasan WAIT, jumlah attempts. Pengembangan lolos hanya jika expectancy net >0, mengalahkan baseline, tak ada penolakan data.
- **Tidak membuka holdout pada gelombang ini.** Sesudah Stage 0 dan prasyarat validasi terpenuhi, hanya kandidat yang didaftarkan dan sah yang dapat diusulkan kepada Owner untuk holdout sekali; syarat Tahap 4: ≥100 trade, PF net ≥1,2, batas bawah CI 95% >0 terkoreksi atas **semua** percobaan yang terdaftar (Bonferroni `alpha=0.05/N_total`), dan risiko sesuai profil DEMO. Tidak mengoptimalkan kandidat pada holdout.
- Jika pada saat registrasi ada 6 percobaan keseluruhan, ilustrasi `alpha=0.05/6≈0.00833`; nilai nyata berdasarkan seluruh percobaan di registry, bukan menganggap enam percobaan bebas koreksi.

**Pelaksana:** Claude menyiapkan preregistration template dan tes mekanisme di branch riset, Yura memeriksa dataset/provenance/split/costs/gate, Owner menyetujui parameter final dan host riset terpisah sebelum backtest historis broker. Tidak ada eksekusi MT5 di VPS observer, deploy, LIVE, demo order, atau aktivasi risk. **Status: `SIX_CANDIDATES_SELECTED_FOR_DESIGN`, `HYPOTHESES_NOT_REGISTERED`, `EDGE_UNPROVEN`.**

#### KEPUTUSAN D10-K4 — Timeframe fleksibel per strategi, wajib dikunci sebelum backtest (Owner SETUJU, rapat 4 November 2026)

Owner menyetujui **kombinasi timeframe berbeda antar strategi**, sepanjang setiap kombinasi terdaftar dan dikunci sebelum ada hasil P/L. Keputusan ini **belum** menetapkan kombinasi final atau entry/SL/TP. Rancangan di bawah merupakan opsi awal untuk disepakati, tanpa klaim win rate atau profitability.

**Proposal desain (belum difreeze):**

| Kandidat | Timeframe konteks → sinyal | Entry (semua kondisi memakai candle selesai dan data yang telah diketahui) | SL / invalidasi awal | Exit proposal |
|---|---|---|---|---|
| B1 BUY sweep bawah | M15 struktur → M5 konfirmasi | Harga sapu low M15 sebelumnya, close M5 kembali di atas level, next bar entry BUY jika spread valid | Di bawah ekstrem sweep + buffer spread/volatilitas yang ditetapkan dulu | TP dasar 2R; time exit jika tak mencapai dalam N candle |
| S1 SELL sweep atas | M15 struktur → M5 konfirmasi | Harga sapu high M15 sebelumnya, close M5 kembali di bawah level dan penolakan bearish, next bar entry SELL | Di atas ekstrem sweep + buffer terdaftar | TP dasar 2R; time exit N candle |
| B2 BUY pullback demand | H1 konteks tren → M15 konfirmasi | Trend H1 bullish terdefinisi pada candle H1 tertutup, koreksi ke area demand terdaftar, konfirmasi bullish M15 tertutup, next bar BUY | Di bawah swing/demand invalidation | TP dasar 2R; time exit N candle M15 |
| S2 SELL pullback supply | H1 konteks tren → M15 konfirmasi | Trend H1 bearish terdefinisi, koreksi ke supply, M15 close rejection bearish, next bar SELL | Di atas swing/supply invalidation | TP dasar 2R; time exit N candle M15 |
| B3 BUY breakout/retest | H1 breakout → M5 retest | Close H1 valid di atas resistance yang dikenal sebelum breakout, M5 retest bertahan lalu close bullish, next bar BUY | Di bawah low retest/level terdaftar | TP dasar 2R; time exit N candle M5 |
| S3 SELL breakdown/retest | H1 breakdown → M5 retest | Close H1 valid di bawah support yang dikenal sebelum breakdown, M5 gagal reclaim dan close bearish, next bar SELL | Di atas high retest/level terdaftar | TP dasar 2R; time exit N candle M5 |

**Alasan desain:** penggunaan TF yang sama di dalam pasangan *untuk baseline perbandingan* tidak menghapus pemisahan BUY/SELL. Jika kelak ada alasan teoritis berbeda pada SELL dibanding BUY, definisikan hipotesis tambahan **sebelum tes**, hitung sebagai percobaan baru. Jangan mengganti timeframe setelah melihat strategi mana yang paling profitable.

**Parameter yang WAJIB disepakati dan dibekukan pada `registry.jsonl` sebelum backtest:**
1. Panjang lookback swing M15/H1, definisi level dan zona supply/demand, syarat sweep (penetrasi minimal) dan reclaim, syarat tren (misal H1 EMA50/200 jika dipilih Owner), ukuran candle/konfirmasi, batas umur level dan maksimum tunggu retest.
2. Cara entry next-bar dengan bid/ask yang benar, struktur SL serta buffer, target TP **2R masih proposal**, batas waktu `N` per TF, no overlapping trades, dan aturan penolakan sinyal jika stop tidak valid.
3. Filter sesi broker sah per simbol, batas spread maksimum yang didefinisikan *tanpa melihat hasil*, komisí/swap/slippage konservatif, batas gap, dan perilaku market closed/rollover. D9 untuk Stage 0 masih keputusan berbeda dan belum boleh dicampurkan ke optimisasi.
4. Semua indikator dan level dihitung hanya dari **bar yang selesai sebelum sinyal**; masuk pada tick/bar setelah konfirmasi, bukan memakai high/low masa depan atau fill ideal di harga close yang tak dapat dieksekusi.
5. Dataset development, asal UTC/dst, split/gaps dan hash sebelum hasil; semua 6 kandidat diregistrasikan dulu. Laporan dua lapis: uji mekanisme sintetis (boleh sekarang) dan backtest development historis (setelah dataset sah & parameter final). Jangan mengakses holdout atau menjadikan data Stage 0 forward sebagai data tuning.
6. Evaluasi semua 6 dengan walk-forward 28 hari, 3 baseline, model biaya penuh, sensitivitas 1,5x/2x, deterministic repeat, scoreboard BUY/SELL dan seluruh percobaan (gagal atau belum ada data tetap dilaporkan). Jika rumus 2R atau timeframe diganti setelah hasil, **ID baru** dan hitung lagi di koreksi multiple trials.

**Status keputusan:** `TIMEFRAME_FLEXIBLE_APPROVED`; `SIX_STRATEGY_DESIGNS_PROPOSED`; `TF_ENTRY_EXIT_PARAMETERS_NOT_FROZEN`; `NO_BACKTEST_AUTHORIZED_BY_THIS_MEETING`; `HOLDOUT_LOCKED`; `LIVE_OFF`. Diskusikan daftar angka/lookback dan definisi supply/demand, sweep, breakout, target serta time exit sebelum freeze dan instruksi coding.

#### KEPUTUSAN D10-K5 — SL struktural + TP dinamis berbasis struktur (Owner SETUJU, rapat 4 Nov 2026)

Owner memilih **SL berdasarkan invalidasi struktur** dan **TP dinamis menuju sasaran struktur pasar** untuk seluruh enam kandidat B1/S1/B2/S2/B3/S3. **Ini keputusan arah desain, bukan persetujuan parameter numerik ataupun perintah trading/backtest.** Setiap kandidat mempunyai aturan pemilihan target dan invalidasi sendiri, tidak boleh dipilih atau direvisi berdasarkan hasil P/L yang sudah dilihat. Rujukan: `docs/research/VALIDATION_PROTOCOL.md` (preregistration, biaya, no-lookahead, baseline, walk-forward).

**Aturan kausal yang wajib dipakai sebelum pengujian:**
1. Saat *bar konfirmasi selesai*, ambil hanya **bar dan zona yang sudah selesai/terdaftar saat itu**. Bekukan snapshot `entry_decision_at_utc`, `level_discovered_at_utc`, `target_origin_bars`, `entry_reference`, `stop_reference`, `target_reference`, `code_sha256`, `dataset_sha256`. Untuk H1/M15/M5 multi-TF, hanya gunakan bar TF tinggi yang telah tutup. Target tidak boleh dibuat dari swing/level *setelah* entry atau dari MFE trade.
2. Entry pada quote eksekusi realistis *setelah* sinyal: BUY di ask, exit/SL BUY di bid; SELL di bid, exit/SL SELL di ask. Asumsikan stop-market bisa mengalami slippage dan gap, TP limit bisa tak terisi bila hanya sekilas menyentuh. Tick data dan prioritas event harus dinyatakan; jika hanya OHLC dan SL+TP berada dalam bar yang sama, penilaian konservatif (SL terlebih dahulu) atau `BLOCKED_UNRESOLVED_INTRABAR`, **jangan otomatis pilih TP**.
3. Bentuk SL = level invalidasi struktural dari bar yang diketahui + buffer volatilitas/spread *yang telah ditetapkan*. Stop tidak boleh berada di sisi salah, jarak nol, atau disesuaikan setelah melihat harga masa depan.
4. Target harus berada di sisi profit relatif terhadap **harga eksekusi**, tidak di antara entry dan SL; pilih **target eligible terdekat** menurut aturan pra-daftar. Penggunaan target lebih jauh hanya jika kategori/urutan struktur telah dipraregistrasikan—dilarang melompati target dekat sekadar menaikkan RR uji.
5. Snapshot menghitung jarak risiko `R = |entry_price - stop_price|` (setelah memeriksa spesifikasi simbol), potensi reward hingga target, RR *bersih setelah biaya* dari spread/komisi/slippage/swap yang dibekukan sebelum backtest; minimum RR belum diputuskan Owner. Jika tidak ada target eligible, reward tidak menutupi biaya, RR kurang dari threshold yang kelak diputuskan, spread tidak valid, pasar tutup, atau data kurang: **WAIT/NO_TRADE dengan reason**, bukan target 2R fiktif atau menghapus sinyal dari denominator penelitian.
6. TP/SL dibekukan saat posisi dibuka untuk uji awal. Pergerakan TP, trailing, partial close, BE atau recovery adalah **varian hipotesis terpisah** yang harus didaftarkan sebelum hasil; tidak dimasukkan diam-diam ke baseline ini. Jika perlu `time exit`, N dan TF-nya wajib ditentukan sebelumnya; exit dengan quote realistis.
7. Uji fixture *causality*: geser harga setelah `entry_decision_at_utc` atau append bar masa depan tanpa mengubah data hingga sinyal → target dan stop awal **harus identik**; uji data gap/revision, konflik SL+TP, bid/ask, level invalid dan pelanggaran timestamp, determinisme lintas OS. Dua kali run sama `code/data/split/seed` = laporan dan hash identik.
8. Semua enam kandidat dinilai dengan biaya broker lengkap, sensitivitas 1,5x/2x, walk-forward 28 hari, tiga baseline, registrasi seluruh percobaan, BUY/SELL terpisah dan penguncian holdout. Belum ada bukti profit; LIVE OFF, 0 order, Stage 0 terpisah.

**Sasaran struktur yang diajukan untuk dibahas dan dibekukan (belum dianggap fakta trading):**

| Kartu | Kandidat TP utama yang diketahui saat entry | SL struktur |
|---|---|---|
| B1 BUY sweep bawah | Resistance/swing high M15 terakhir yang *sudah tervalidasi* dan di atas entry; opsi berikutnya buy-side liquidity bila pra-daftar | Low sweep minus buffer |
| S1 SELL sweep atas | Support/swing low M15 terakhir yang diketahui dan di bawah entry; opsi berikutnya sell-side liquidity bila pra-daftar | High sweep plus buffer |
| B2 BUY trend pullback | Supply/H1 resistance atau previous H1 swing high terdekat yang sudah terbentuk | Di bawah demand/swing low yang menyebabkan entry |
| S2 SELL trend pullback | Demand/H1 support atau previous H1 swing low terdekat yang sudah terbentuk | Di atas supply/swing high |
| B3 BUY breakout+retest | Resistance/swing high H1 berikutnya yang diketahui sebelum breakout; bukan level yang baru dibentuk setelahnya | Di bawah level retest/low yang sudah terbentuk |
| S3 SELL breakdown+retest | Support/swing low H1 berikutnya yang diketahui sebelum breakdown | Di atas level retest/high yang sudah terbentuk |

**Pertanyaan rapat terbuka:**
- `D10-K5-A`: batas minimal RR *bersih* untuk menerima entry? Proposal diskusi 1,5R atau 2R, **bukan angka teruji**.
- `D10-K5-B`: bila tidak ada level target terverifikasi dalam arah profit, **WAIT** (rekomendasi untuk baseline bersih) atau aturan fallback yang dipraregistrasikan?
- `D10-K5-C`: time exit dinamis vs fixed bar count per strategi; definisi panjang lookback/konfirmasi zona dan buffer. Tidak boleh memilih setelah melihat hasil uji.

**Status:** `DYNAMIC_STRUCTURAL_TP_APPROVED_AS_DESIGN` / `EXECUTION_PARAMETERS_NOT_FROZEN` / `NO_BACKTEST_YET` / `EDGE_UNPROVEN`. Catatan ini tidak mengubah produk trading, konfigurasi risiko, data historis, atau gate Stage 0.

#### KEPUTUSAN D10-K6 — Tidak ada batas RR minimum; TP hanya ke level struktur sah (Owner SETUJU, rapat 4 November 2026)

Owner menolak **filter minimum risk-to-reward** untuk keenam kandidat. Setiap sinyal yang memenuhi aturan struktural dasar tetap dipertimbangkan meskipun reward kecil relatif terhadap risiko; angka RR **dicatat untuk analisis, bukan dipakai menyaring entry**. TP harus menunjuk **level struktur kausal yang telah ada saat keputusan entry**, bukan TP RR tetap atau target yang dibuat setelah melihat profit. Ini **tidak menghapus** pemeriksaan invalid stop, harga eksekusi bid/ask, asal data, biaya penuh, Risk Governor, dan sinyal `WAIT` ketika tidak ada target struktur yang valid. Perbedaan penting: jangan menyelundupkan filter baru seperti `net RR > 0` atau `TP > biaya` dalam implementasi tanpa keputusan Owner; jika kerugian neto mungkin akibat biaya tinggi, **tetap dilaporkan apa adanya** pada uji development, bukan dikeluarkan berdasarkan hasil.

**Proposal definisi objektif untuk pembahasan, belum di-freeze:**

| Aspek | Definisi yang diusulkan | Batas kausal |
|---|---|---|
| Swing high/low | Fractal pivot `L=2` candle tertutup sebelah kiri dan `R=2` candle tertutup sebelah kanan; high lebih tinggi / low lebih rendah *secara ketat* dari tetangga (equal high/low tidak otomatis menjadi pivot) | Pivot baru **diketahui 2 candle setelah candle ekstrem**, bukan pada timestamp ekstrem; jangan menggunakannya sebelum tanggal `confirmed_at` |
| Demand H1 untuk B2 | Candle bearish H1 terakhir yang sudah selesai, tepat sebelum dorongan bullish **H1 close di atas swing high H1 yang sudah confirmed**; zona harga **low→high candle asal** (full wick), tidak memakai candle belum tertutup | `origin_at`, `confirmed_at`, swing ref semuanya sudah ≤ waktu keputusan; definisi dorongan/masa berlaku masih perlu diputuskan |
| Supply H1 untuk S2 | Simetris: candle bullish H1 terakhir sebelum dorongan bearish H1 close di bawah swing low H1 confirmed; zona full wick asal | Sama, memakai bar tertutup; tidak ada zona yang muncul retroaktif |
| Resistansi/support untuk TP | Level swing confirmed dan/atau zona sisi lawan yang eligible, dipilih **yang paling dekat di arah profit dari harga eksekusi**; aturan tie/overlap harus tetap & deterministik | Level yang belum confirmed pada `entry_decision_at` tidak eligible; `target_id`, `confirmed_at` disimpan |
| SL struktur | BUY di bawah low sweep/demand/swing retest terkonfirmasi, SELL di atas high sweep/supply/swing retest terkonfirmasi, ditambah buffer yang dihitung dari data saat keputusan | Dilarang SL berpindah setelah entry dalam baseline; invalidasi dan eksekusi dicek bid/ask & tick size |
| Buffer SL | Opsi diskusi pertama `max(1 tick broker, spread pada keputusan, k × ATR(14) TF entry)` dengan `k` ditetapkan Owner sebelum uji; alternatif buffer tick tetap; semuanya dari bar/quote kausal | Nilai `k` / opsi belum diputuskan; ATR(14) memakai candle tertutup saja; sesuaikan pembulatan tick size ke luar risiko |
| Target tak ada/invalid | `WAIT:NO_VALID_STRUCTURAL_TARGET`; jangan mengganti TP 2R atau memakai level masa depan | Tidak ada minimum RR tetapi target harus secara geometris berada di arah profit dari entry |
| Prioritas event | Entry pada quote setelah konfirmasi; jika data OHLC tidak mengurutkan SL/TP dalam bar sama, pilih aturan konservatif atau minta tick, bukan TP-first | Catat semua sinyal tersaring dan gap secara eksplisit; hasil harus deterministik |

**Batas penelitian tetap:** hipotesis B1/S1/B2/S2/B3/S3 terpisah, `registry.jsonl` sebelum melihat P/L, dataset development sah dan split/gaps/hash, biaya penuh serta sensitivitas 1,5x/2x, baseline dan 28-day walk-forward; holdout tetap terkunci; Stage 0 dan data forward tidak digunakan untuk tuning. Hasil yang tampak jelek **tidak boleh dihapus**. RR dilaporkan distribusinya (gross dan net) tetapi bukan filter yang mengubah denominator sinyal.

**Keputusan yang masih terbuka dalam rapat:**
1. Pivot swing: `2 kiri + 2 kanan` atau `3 kiri + 3 kanan` (keduanya kausal setelah konfirmasi).
2. Demand/supply: `full wick high-low` asal atau body-only, serta usia maksimum zona dan aturan zona batal.
3. Buffer: `max(tick, spread, k×ATR14)` dan nilai `k` versus fixed ticks; time exit masih belum diputuskan.
4. Jika satu bar dan dua struktur cocok sebagai TP, aturan prioritas target terdekat dan level stale harus ditetapkan sebelum pengujian.

**Status:** `NO_MIN_RR_APPROVED` / `STRUCTURAL_TARGET_ONLY_APPROVED` / `SWING_ZONE_BUFFER_UNDECIDED` / `NO_BACKTEST_AUTHORIZED_YET` / `LIVE_OFF`.

#### KEPUTUSAN D10-K7 — Swing fractal 2 kiri + 2 kanan (Owner SETUJU, rapat 4 November 2026)

Owner memilih definisi **swing high/low dengan 2 candle tertutup di kiri dan 2 candle tertutup di kanan** untuk rancangan keenam kandidat BUY/SELL. Pivot valid **baru setelah candle kedua di kanan ditutup**; `confirmed_at` tidak boleh diberi timestamp candle pivot, dan level tidak boleh dipakai pada candle sebelum konfirmasi. Untuk tie/equal highs/lows, usulan awal **strict comparison** (nilai sama bukan swing) agar deterministik. Definisi swing ini sudah disetujui sebagai desain; implementasi, tes, registrasi hipotesis dan backtest **belum dilakukan**.

#### KEPUTUSAN D10-K8a — Buffer SL 0,10 × ATR14 dipilih Owner (rapat 4 Nov 2026)

Owner memilih **koefisien k = 0,10** dalam usulan rumus buffer SL, dengan **batas minimum tick size dan spread saat keputusan**, untuk seluruh kandidat yang menggunakan SL struktural:

`buffer_price = ceil_to_tick_size(max(tick_size, spread_at_decision, 0.10 * ATR14_closed_entry_TF))`.

- ATR14 menggunakan hanya candle timeframe entry yang **telah tutup** saat keputusan; spread menggunakan bid/ask faktual dan tick size terverifikasi. Rincian ATR (Wilder), kesalahan data, spread yang hilang, rounding, dan batas minimum stop broker wajib diuji fail-closed. Harga stop BUY dibulatkan ke bawah dan SELL ke atas pada grid tick yang benar.
- Ini **pilihan desain sebelum pengujian**, **bukan bukti k=0,10 optimal**, tidak mengesahkan backtest, perubahan kode, order, atau membuka holdout. Tidak ada minimum RR sesuai D10-K6.
- Usulan k=0,15 yang masih tertulis di agenda D10-K8 di bawah adalah **riwayat opsi lama dan telah digantikan oleh keputusan ini**; jangan implementasikan 0,15 sebagai default. Varian 0,15/0,20 hanya boleh dicoba sebagai hipotesis baru dengan persetujuan, preregistration dan koreksi multiple trials.
- **Fresh zone, masa berlaku 48 H1, metode sentuhan, invalidasi zona, dan time exit MASIH TERBUKA** untuk rapat; jangan menganggap paket D10-K8 telah disetujui otomatis.

#### KEPUTUSAN D10-K9/K10 — Hybrid, first visit, usia zona (Owner SETUJU)

Owner telah menyetujui:
- **Invalidasi hybrid:** ketika harga valid melewati batas zona plus buffer secara intrabar, entry baru diblokir segera; penutupan H1 menentukan invalidasi struktur. Posisi yang sudah ada tetap mengikuti SL masing-masing.
- **First visit satu kesempatan:** zona hanya dapat menghasilkan sinyal dalam episode kunjungan pertama; bila keluar tanpa sinyal, status menjadi CONSUMED dan tidak dipakai ulang.
- **Pernah breach tidak kembali fresh:** jika H1 menutup di luar batas zona, INVALID; jika H1 kembali masuk, CONSUMED. Zona lama tidak kembali FRESH; hanya zona baru yang terbentuk secara independen bisa menjadi fresh.
- **Usia maksimum:** 48 candle H1 valid dan selesai sejak zona dikonfirmasi; setelah itu EXPIRED. Jam akhir pekan dan candle yang tidak tersedia tidak boleh dihitung sebagai candle valid. Jika ada gap data, tandai dan jangan menebak kontinuitas.
- **Buffer yang telah dipilih:** max(tick size, spread, 0,10 x ATR14), memakai data saat keputusan; swing 2 kiri + 2 kanan, tanpa minimum RR dan TP struktural.
- Berlaku sebagai **spesifikasi riset**, bukan izin mengubah runtime, menguji holdout, atau menyalakan trading. Parameter time exit masih dibahas; seluruh desain harus dicatat sebelum backtest.

#### KEPUTUSAN D10-K15 — Sweep/reclaim satu candle M5 B1/S1 (Owner SETUJU)

Owner secara eksplisit memilih **sweep dan reclaim harus terjadi dalam candle M5 yang sama** untuk B1 BUY / S1 SELL. Sumber swing menggunakan **M15 pivot 2 kiri + 2 kanan**, dan pivot harus terkonfirmasi sebelum candle M5 yang menjadi sinyal dimulai; tidak boleh menentukan swing dari bar kanan yang belum tertutup.

- **B1 BUY:** M5 low < confirmed M15 swing low; M5 close > swing low dan M5 close > M5 open. **S1 SELL:** M5 high > confirmed M15 swing high; M5 close < swing high dan M5 close < M5 open. Sweep dan close harus terjadi dalam satu candle M5 yang telah selesai. Entry disimulasikan memakai quote eksekutabel berikutnya, SL ekstrem sweep + buffer D10-K8a, TP struktur berlawanan yang telah confirmed sebelum entry.
- **Batas minimum penetrasi sweep 1 tick masih PROPOSAL, bukan keputusan Owner.** Sama halnya dengan umur swing, urutan memilih beberapa swing, konflik candle dan posisi bertumpuk; seluruhnya harus ditentukan sebelum preregistration.
- Time exit B1/S1: 12 M5/90m/pra-tutup 15m telah dipilih D10-K14; tanpa minimum RR, TP struktural dan persetujuan terpisah bagi eksekusi nyata tetap.

#### KEPUTUSAN D10-K16 — B2/S2 H1 structure trend + M15 confirmation (Owner SETUJU)

Owner menyetujui baseline **B2 BUY** memakai **HH + HL H1** dan **S2 SELL** memakai **LH + LL H1**, dengan swing fractal 2 kiri / 2 kanan yang sudah fully confirmed. Proposal definisi deterministik untuk implementasi: dua confirmed swing high dan dua confirmed swing low H1 terakhir sama-sama meningkat secara ketat (BUY) atau menurun secara ketat (SELL), semuanya sudah confirmed pada waktu keputusan entry. Bila tak lengkap, `WAIT:TREND_UNCONFIRMED`; tanpa EMA tambahan dalam baseline ini.

Owner juga menyetujui **candle M15 searah** yang menyentuh zona lalu close **keluar zona**: B2 M15 low mencapai demand dan close bullish **di atas batas atas** demand; S2 M15 high mencapai supply dan close bearish **di bawah batas bawah** supply, dengan candle sudah selesai sebelum entry. Sinyal hanya dari episode *first-visit* H1 zona valid 48 bar dan tidak pernah breach (Hybrid). Entry pada quote berikut setelah close M15. SL struktural + max(tick size, spread, 0.10*ATR14 M15) dan TP struktur terdekat valid, tanpa RR minimum; time-exit B2/S2 12 M15 / 240 menit / 30 menit pra-tutup sudah disepakati.

**Yang belum dikunci untuk preregistration B2/S2:** aturan memilih candle asal bila beberapa bar memenuhi, tie-breaking zona beririsan, deteksi batas episode visit dari tick bid/ask, lebar zona minimal/maksimal dan harga referensi bid/ask, prioritas target, definisi ATR Wilder dan source spread, jam sesi broker resmi, data/split/cost/code hash. Semua ini bukan izin coding/tes atau klaim strategi profitable.

#### KEPUTUSAN D10-K21 — TTL swing, invalidasi close dan TP level terdekat (Owner SETUJU, 4 November 2026)

Owner menyetujui parameter struktur untuk keenam kandidat XAUUSD sebagai **baseline sebelum preregistration**:
- TTL confirmed swing **M15 = 96 candle M15 tertutup**, **H1 = 72 candle H1 tertutup**, terhitung dari `confirmed_at`, bukan `pivot_at`. Zona H1 punya usia terpisah **48 candle H1** yang sudah disetujui; candle gap/market closed tidak dibuat fiktif dan gap yang merusak penilaian ditandai `BLOCKED_DATA_GAP`.
- **Support swing low dibatalkan** jika candle **timeframe asal** yang sudah selesai memiliki `close <= swing_low - 1*tick_size`; **resistance swing high dibatalkan** jika `close >= swing_high + 1*tick_size`. Penetrasi wick saja bukan pembatalan swing. Tidak memakai masa depan untuk mengetahui validitas.
- **Pengecualian B3/S3:** close H1 breakout/breakdown yang secara sah mematahkan swing tidak menghapus setup tersebut; level ditandai `BROKEN_RETEST_ELIGIBLE` untuk maksimal satu episode retest **6 candle M5** sesuai D10-K17, kemudian tidak dapat dipakai ulang sebagai support/resistance lama maupun TP belum ditembus.
- **TP struktur valid terdekat di sisi keuntungan dari harga fill**, tanpa minimum RR. Untuk kandidat B1/S1 prioritas swing lawan M15; B2/S2 swing H1 atau zona lawan H1 yang eligible; B3/S3 swing lawan H1 yang belum broken. Jika jarak sama, **lebih baru `confirmed_at` menang**, kemudian ID stabil sebagai tie-break teknis. Jika tidak ada target eligible: `WAIT:NO_VALID_STRUCTURAL_TARGET`. Perlu keputusan lanjutan mengenai harga *proximal* zona target, tipe/overlap zona, dan referensi bid/ask; jangan ubah himpunan level diam-diam pasca-hasil.

**Klarifikasi status:** klausul angka 96/72 dan invalidasi/TP yang tertulis sebagai *usulan* di bawah pada bagian D10-K20 **sudah disetujui dan digantikan oleh keputusan D10-K21 ini**. `D10-K21_APPROVED`, `ZONE_ORIGIN_PENDING`, `REGISTRY_NOT_WRITTEN`, `NO_BACKTEST`, `HOLDOUT_LOCKED`, `LIVE_OFF`.

#### KEPUTUSAN D10-K22 — Zona Demand/Supply H1 dipilih; agenda G4 eksekusi & G8 simulator (Owner SETUJU, 4 November 2026)

**Diputuskan oleh Owner:** B2 demand dari **candle bearish H1 terakhir** di antara **12 H1 tertutup sebelum BOS H1 bullish** minimal **1 tick melewati confirmed swing high H1**; S2 supply dari **candle bullish H1 terakhir** di antara 12 H1 sebelum BOS H1 bearish minimal 1 tick melewati swing low. Level swing BOS diketahui sebelum candle BOS dimulai; batas zona **full wick high–low candle origin**; zona terkonfirmasi hanya setelah close H1 BOS. Satu episode first touch, **satu candle M15 yang memuat first touch** untuk candle konfirmasi arah serta close di luar zona; bila gagal CONSUMED, tanpa mengulang. TP B2 BUY pada **batas bawah supply H1**, S2 SELL pada **batas atas demand H1** yang valid dan paling dekat dalam arah profit, dibanding swing H1 valid, tie level terbaru. Zona first visit, invalidasi hybrid, umur 48 H1 dan tanpa RR min sesuai keputusan lain.

**Konsolidasi dokumen:** [spesifikasi 6 kandidat](research/SIX_CANDIDATE_PREREGISTRATION_SPEC_20261104.md) diperbarui, dan [kontrak eksekusi/simulator baru](research/SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md) dibuat pada branch dokumen PR #293. Semua file adalah spesifikasi/rencana riset, **bukan** hasil implementasi source code.

**Audit blocker yang dilakukan dalam agenda:**
- **G3 inti zona disetujui; detail quote overlap belum diputuskan.**
- **G4 execution masih terbuka:** sumber BID vs ASK pada touch/breach, urutan SL dan TP dalam satu candle bila tanpa tick, time-exit intents tanpa quote, treatment event bersamaan, gap/missing data, overlap posisi antarkandidat, dan data sesi valid. Usulan prefer tick replay kronologis dan fail closed untuk OHLC intrabar ambiguity, dengan fallback SL-first hanya jika disetujui terpisah. Satu posisi per kandidat tetap disetujui.
- **G8 simulator BLOCKED:** `src/katarina/research/setups/core.py` masih `target_rr/min_rr`; `simulator.py` hanya M5,H1, OHLC stop-first dan fixed `max_hold_bars`; detektor sweep/pullback/breakout belum sesuai 6 hipotesis. Butuh refaktor **offline research only** dan fixture deterministik sebelum freeze `code_sha256`.
- **G6/G7 di luar penyelesaian agenda ini:** hash data dev/clock/split/costs belum dikonfirmasi; jadwal resmi `SymbolInfoSessionQuote/Trade` broker XAUUSD.vx belum tersedia. **Tidak boleh menyimpulkan preregistration siap** hanya karena G3 disetujui.
- **Tidak dilakukan:** registrasi hipotesis, test P/L, perubahan `src/` atau `scripts/`, eksekusi script MT5, akses data holdout atau perubahan konfigurasi VPS.

**Pilihan yang diminta pada agenda D10-K23:** (A) tetapkan penelitian **event replay tick kronologis**, chart OHLC dan touch BID, BUY fill ASK/SELL fill BID, bila tick urutan tak diketahui `BLOCKED_INTRABAR_ORDER`, serta **evaluasi 6 kandidat secara independen** (rekomendasi manajemen); (B) izinkan fallback OHLC dengan SL-first sebagai baseline bila tick tak lengkap dengan laporan keterbatasan, sambil tetap mengevaluasi kandidat terpisah; atau (C) bahas satu per satu quote touch, ambiguity, dan kebijakan overlap antarkandidat. **Belum boleh menganggap A/B dipilih**, dan A tidak mengizinkan mengambil tick VPS produksi tanpa prosedur/otorisasi.

`D10-K22_APPROVED`; `EXECUTION_POLICY_PENDING`; `SIMULATOR_CODE_MISMATCH`; `G6_DATA_COST_UNVERIFIED`; `G7_SESSION_EVIDENCE_MISSING`; `NOT_REGISTERED`; `NO_BACKTEST`; `HOLDOUT_LOCKED`; `LIVE_OFF`.

#### AGENDA D10-K22 — Pembentukan demand/supply yang deterministik (BELUM DIPUTUSKAN)

**Proposal baseline Owner untuk dipilih**, tidak dikunci otomatis:
1. Demand B2: pada H1 candle BOS yang selesai `close >= confirmed_swing_high + tick_size`, cari **candle bearish H1 terakhir** di antara **12 candle H1 tertutup sebelumnya**, urut paling baru; itu `zone_origin`. Supply S2: BOS bearish `close <= confirmed_swing_low - tick_size`, cari **candle bullish H1 terakhir** dengan jendela serupa. Swing BOS wajib confirmed **sebelum candle BOS dimulai**. Bila tak ada origin, `WAIT:NO_VALID_ZONE_ORIGIN`. Tidak menyeleksi zona berdasarkan profit berikutnya.
2. Area zona **full wick high-low candle origin**, dalam unit harga terkuantisasi tick; definisi harga chart (proposal: BID OHLC dan BID quote untuk mendeteksi sentuhan) wajib seragam, sementara eksekusi BUY ask/SELL bid. `origin_at`, `bos_confirmed_at`, `zone_confirmed_at`, `zone_id`, `first_touch_at` dicatat; zona baru berlaku setelah close BOS.
3. First visit satu kesempatan sudah disetujui; **proposal definisi episode** agar M15 bisa konfirmasi: saat quote valid pertama memasuki interval zona, mulai episode `FIRST_VISIT`. Evaluasi **satu candle M15 penuh yang mengandung first touch** setelah candle M15 tersebut selesai; jika candle memenuhi aturan B2/S2 dan tak ada hybrid breach, entry pada quote berikut. Jika gagal, `CONSUMED` dan tak boleh mengulang. Detail bagaimana first-touch persis pada perbatasan 15 menit ditangani harus di-fixture.
4. Hybrid: intrabar breach distal+buffer kapan pun sebelum entry → `BREACH_LOCKED`, entry diblokir; H1 close di luar distal → `INVALID`, H1 close kembali di dalam → `CONSUMED`; tidak `FRESH` lagi. Zona belum tersentuh kedaluwarsa setelah 48 **valid closed H1** sejak confirm, bukan setelah 48 jam kalender.
5. Jika **beberapa zona valid beririsan**, proposal pilih yang batas proximal-nya paling dekat dengan quote saat first touch; tie pilih `zone_confirmed_at` terbaru lalu `zone_id` stabil. Jangan mengubah pemilihan saat hasil P/L terlihat.
6. Target zona lawan untuk B2/S2: harga proximal boundary yang terdekat pada arah profit dan sudah diketahui pada saat entry (BUY: batas **bawah supply**; SELL: batas **atas demand**); bila sudah ditembus dan expired, tidak eligible. Bandingkan semua target swing H1 dan zona lawan pada daftar valid, ambil yang terdekat di arah profit sesuai D10-K21.

**Hal yang tetap blocked walau Owner menyetujui proposal G3:** bukti sesi quote/trade MT5 resmi, dataset development hash/split, model costs, simulator offline yang belum sesuai, definisi level overlap dan event intrabar, fixture. Tidak ada registrasi atau backtest sampai seluruh syarat siap.

#### KEPUTUSAN D10-K20 — Swing terbaru tetapi dibatasi usia (Owner SETUJU)

Owner memilih hanya swing **terbaru yang masih valid dan belum kedaluwarsa** untuk acuan entry; level target struktur juga harus memenuhi batas validitas dan usia sebelum dipakai. Keputusan ini menetapkan prinsip *age-bounded*, **belum menetapkan angka TTL ataupun aturan pembatalan swing**. Tidak ada backtest/registrasi/aktivasi trading yang disetujui oleh keputusan ini.

**Parameter yang Yura ajukan untuk persetujuan berikutnya, BELUM dikunci:**
- TTL swing M15 **96 candle M15 selesai** sejak `confirmed_at`; TTL swing H1 **72 candle H1 selesai** sejak `confirmed_at`. Berbeda dari masa hidup zona H1 yang telah diputuskan 48 candle. Ini angka desain, bukan hasil optimasi; untuk menghitung pivot 2+2 harus menyediakan konteks candle yang lebih tua dan melaporkan data GAP sebagai unverifiable.
- **Pembatalan swing**: swing low support dibatalkan bila candle pada TF asal **close >= 1 tick di bawah level**; swing high resistance bila candle asal **close >= 1 tick di atas level**. Wick saja tidak membatalkan swing, agar sweep-reclaim satu M5 tetap bisa terjadi. Periksa status sebelum setup, tidak retrospektif.
- **Pengecualian breakout B3/S3:** close H1 melewati level adalah kejadian breakout yang **mengubah status level menjadi `BROKEN_RETEST_ELIGIBLE` untuk satu episode maksimal 6 M5**, bukan menghapus pemicu sebelum retest; level yang sudah broken tidak dipakai lagi sebagai target resistance/support lama.
- **TP struktural:** B1/S1 pilih swing M15 lawan terdekat di arah profit; B2/S2 pilih di antara swing H1 lawan dan *proximal boundary* zona lawan H1 yang valid; B3/S3 pilih swing H1 lawan terdekat yang belum broken. Di antara level eligible: jarak harga profit terkecil; tie = `confirmed_at` paling baru, lalu ID stabil. BUY: target harus lebih tinggi dari harga fill ask; SELL: lebih rendah dari fill bid. Tidak ada minimum RR; jika tidak ada target valid, WAIT. Kelayakan zona dan definisi harga proximal masih perlu dibekukan.
- Setiap perubahan angka TTL, pembatalan atau himpunan target setelah melihat P/L = hipotesis baru dan dihitung dalam koreksi percobaan. Data Stage0/holdout tidak dipakai untuk tuning.

**Agenda keputusan berikutnya:** Owner memilih menerima paket angka dan metode pembatalan/TP yang diusulkan atau merevisinya **sebelum freeze**. `BOUNDED_LATEST_SWING_APPROVED`, `TTL_INVALIDATION_TARGET_POLICY_PENDING`, `NOT_REGISTERED`, `NO_BACKTEST`, `LIVE_OFF`.

#### KEPUTUSAN D10-K19 — Lima aturan teknis baseline disetujui; draf spesifikasi enam kandidat disusun (Owner SETUJU)

Owner menyetujui lima ketentuan dasar untuk batch XAUUSD B1/S1/B2/S2/B3/S3:
1. **B1/S1 kedalaman minimal sweep = 1 tick** dari swing M15 terkonfirmasi; pilih **swing M15 terkonfirmasi terbaru** yang masih valid, dengan age/TTL dan interpretasi validitas masih harus didefinisikan sebelum freeze.
2. **Target TP** = struktur valid terdekat pada sisi profit; bila jarak sama, prioritaskan level **lebih baru terkonfirmasi**. Jenis level, proximal/distal dan validitas umur masih memerlukan penegasan deterministik.
3. **ATR14 Wilder** memakai hanya candle penuh TF entry yang telah ditutup, untuk buffer SL `max(tick_size,spread,0.10*ATR14)` dan pembulatan konservatif; aturan warm-up/gaps perlu fixture.
4. **Maksimal satu posisi aktif per kandidat**; perilaku overlap **antar-kandidat** harus diputuskan terpisah sebelum penggunaan dalam simulator/validator.
5. **Fail-closed**: quote, spread, struktur, timestamp, broker tick size atau urutan fill tak valid → `WAIT` / `BLOCKED` dengan reason, tidak membuat harga/candle/fill sintetis dan tidak menghapus sampel tidak menguntungkan.

Atas instruksi Owner, manager menyusun **[spesifikasi konsolidasi enam kandidat](research/SIX_CANDIDATE_PREREGISTRATION_SPEC_20261104.md)** pada branch draft PR #293. Draf memisahkan semua keputusan yang disetujui dari blocker `G1–G8`: detail validitas swing/target dan tie-break, pembentukan zona H1/touch, event-order dan ATR/stops, riwayat setup, verifikasi dataset/clock/split/cost, bukti sesi MT5 per simbol/server, dan mismatch simulator offline lama (`target_rr`+`min_rr`, M5/H1, exit fixed bars).

**Penilaian gate:** `BASELINE_5_RULES_APPROVED`; `SIX_CANDIDATES_SPEC_DRAFTED`; **`PREREGISTRATION_NOT_READY`** sampai G1–G8 ditutup, code_sha256 dan inputs difreeze, dan fixture mekanisme lulus; `REGISTRY_NOT_WRITTEN`; `NO_BACKTEST`; `HOLDOUT_LOCKED`; `LIVE_OFF`. Keputusan ini **bukan** persetujuan otomatis atas parameter G1–G8 atau izin menjalankan tools ke VPS produksi.

#### KEPUTUSAN D10-K17 — Breakout H1 dan retest satu candle M5 (Owner SETUJU, 4 November 2026)

Owner menyetujui B3 BUY / S3 SELL baseline: breakout/breakdown dikonfirmasi dengan candle **H1 tertutup** melewati swing H1 yang sudah terkonfirmasi sebesar **setidaknya 1 tick** (BUY close >= swing_high + tick; SELL close <= swing_low - tick); sejak H1 close, tunggu **maksimal enam candle M5 yang telah selesai**, dengan **retest dan close konfirmasi pada satu candle M5 yang sama**, bukan dua candle. Interpretasi proposal baseline B3: M5 low menyentuh level lama dan close bullish di atasnya; S3: high menyentuh level dan close bearish di bawahnya. Entry baru dilakukan pada quote berikutnya sesudah konfirmasi. Jika tidak terjadi dalam enam candle, `WAIT:RETEST_TIMEOUT`. Semua level harus sudah confirmed sebelum H1 breakout dimulai, dan M5 yang eligible harus mulai setelah atau tepat di waktu close H1. Syarat kedalaman retest, tie-break level, dan konflik jadwal/data masih perlu keputusan sebelum freeze.

#### Audit preregistration D10-K18 — enam kandidat (AUDIT; bukan persetujuan parameter baru)

**Disetujui dalam agenda sebelumnya:** B1/S1 sweep+reclaim dalam candle M5 yang sama terhadap confirmed swing M15 2+2; B2/S2 HH+HL atau LH+LL H1 confirmed 2+2 dan satu M15 candle searah menyentuh lalu close melewati batas fresh zone H1; B3/S3 retest satu candle M5 <=6 bars dan H1 breakout >=1 tick; TP struktur valid terdekat yang diketahui di entry tanpa minimum RR; SL buffer max(tick, spread, 0.10×ATR14) dan struktural; first-visit saja, hybrid breach terminal non-fresh, 48 closed H1; time-exit B1/S1 12 M5/90min/preclose15min, B2/S2 12 M15/240min/preclose30min, B3/S3 24 M5/180min/preclose20min.

**Belum selesai sebagai input spesifikasi (jangan menebak dan jangan auto-freeze):**
1. B1/S1 minimum kedalaman sweep (opsi 1 tick masih proposal), pemilihan swing pemicu dan kondisi pembatalan yang tepat;
2. level umur/validitas swing dan retest; bila beberapa zona/swing eligible atau target sama dekat, urutan terdaftar dan tie-break tetap; kriteria breakout false/overlap, target TP terdekat;
3. prioritas pembentukan zona jika terdapat beberapa candle asal; harga sentuh zona berbasis bid/ask dan episode first-visit, cara memperlakukan tick hilang;
4. rumus ATR14 (misal Wilder), rounding tick/stops level server, definisi quote tepat entry/exit dan order event ketika SL/TP/time exit bersamaan, jumlah posisi simultan, spread invalid/no quote;
5. event counter 6 M5 dan 12/24 M5 atau 12 M15 setelah entry (hanya bar lengkap), penutupan sesi/simbol yang **belum diverifikasi**, dan pencatatan exit pending saat quote tidak tersedia;
6. `name,symbol,side,regime,playbook,rules,parameters,code_sha256` untuk **setiap** B1/S1/B2/S2/B3/S3, ditambah dataset/manifest hash, `split.json` dengan gaps, `costs.json` spesifikasi broker, jam server→UTC independen; penelitian development hanya sebelum **13 Okt 2026 UTC**, terpisah dari forward Stage0/holdout.

**Mismatch kode nyata (audit read-only `main`):**
- `src/katarina/research/setups/core.py::signal` masih menghitung target sebagai RR tetap (`target_rr`) dengan filter `min_rr>=0.01`, bertentangan dengan keputusan Owner tanpa RR minimum dan TP struktur.
- `src/katarina/research/setups/simulator.py` hanya mengolah M5+H1 dan `max_hold_bars`, belum M15 pullback / hybrid clock & preclose / zona first visit / ATR adaptif.
- `src/katarina/research/setups/liquidity_sweep.py` berbasis range M5, belum swing terkonfirmasi M15; `pullback.py` mean M5 bukan demand/supply M15; `market_structure.py` close-break M5 bukan H1 breakout dengan M5 retest.
- Registrasi tersedia melalui `scripts/research/register_setup_hypothesis.py` dan protokol `docs/research/VALIDATION_PROTOCOL.md`, batas maksimal 5/symbol/side dan Bonferroni; adanya tooling tidak berarti enam hipotesis sudah bisa didaftarkan. `docs/maintenance/MT5_SESSION_MAP_20261104.md` hanya peta empiris tick, **bukan** bukti resmi `SymbolInfoSessionQuote/Trade`.

**Gate yang disimpulkan:** `D10-K17_DESIGN_APPROVED`, `REGISTRATION_BLOCKED_SPEC_INCOMPLETE`, `SIMULATOR_MISMATCH`, `BLOCKED_SESSION_EVIDENCE`, `DATA_COST_NOT_VERIFIED`, `NO_BACKTEST`, `HOLDOUT_LOCKED`, `LIVE_OFF`. Tidak mengubah kode, runtime, data, sesi Stage0 ataupun izin trading. Setelah Owner menyetujui rincian residual dan kode offline telah sesuai, uji fixture tanpa P/L → freeze code/data/split/costs → registrasi keenam sebelum evaluasi profit.

#### AGENDA D10-K17 — B3/S3 Breakout/Breakdown & Retest H1→M5 (USULAN; OWNER BELUM MEMUTUSKAN)

**Proposal sinyal baseline yang dapat diaudit kausal:**
- Level referensi B3 adalah **confirmed swing high H1**; untuk S3 **confirmed swing low H1**, memakai 2 kiri + 2 kanan. Level harus sudah confirmed **sebelum bar H1 breakout dimulai**. Abaikan level masa depan atau hasil high/low H1 breakout yang baru terbentuk.
- **B3 BUY breakout:** H1 candle sudah selesai dan **close > resistance + 1 tick**; **S3 SELL breakdown:** H1 candle sudah selesai dan **close < support - 1 tick**. Break perlu body close, bukan wick-only. Min breakout 1 tick adalah **usulan**, bukan putusan.
- Setelah H1 breakout close, hanya candle M5 **yang mulai pada/ setelah waktu konfirmasi H1** boleh mencari retest. **Usulan maksimum 6 candle M5 tertutup (30 menit)**; satu episode retest pertama untuk sinyal B3/S3; bila tidak ada yang memenuhi, `WAIT:RETEST_TIMEOUT`, dan breakout itu dianggap selesai, tidak memancing setup berulang.
- **Konfirmasi satu candle M5 (usulan baseline):** B3 retest candle M5 `low <= broken_level`, `close > broken_level`, `close > open`. S3 `high >= broken_level`, `close < broken_level`, `close < open`. Level yang ditembus ditahan kembali saat close; jika sesi close/quote hilang, no trade. Memastikan harga benar-benar dapat bergerak di sekitar level dengan toleransi tick/spread masih perlu aturan terdaftar. Retest yang lebih dalam tidak otomatis berhak entry bila data invalid.
- Entry pada quote eksekutabel berikut setelah M5 konfirmasi; SL B3 di bawah low retest, S3 di atas high retest, dengan max(tick_size, spread, 0.10*ATR14 M5) dibulatkan benar. TP **struktur H1 valid terdekat di sisi profit** yang telah diketahui pada waktu entry; bila tidak ada level geometris valid, `WAIT:NO_VALID_STRUCTURAL_TARGET`, bukan menambahkan TP RR tetap. Tanpa minimum RR. Time exit 24 M5 / 180 menit / 20 menit pra-tutup sesuai D10-K14.
- Jika H1 sudah ditutup kembali di sisi lama breakout **sebelum M5 retest/entry**, blokir sinyal dan tandai `BREAKOUT_INVALIDATED`; tidak memakai H1 yang belum ditutup untuk pembatalan struktur retrospektif, dan stop yang sudah tersentuh tetap dihitung. Urutan event M5/H1 dan gap wajib deterministik.

**Keputusan diminta Owner:** (A) satu candle M5 retest & close kembali di sisi breakout, maksimal 6 candle M5 sejak H1 confirm (rekomendasi baseline); atau (B) dua tahap touch dahulu, baru close konfirmasi pada candle M5 berikutnya, dengan maksimum 6 candle M5; atau (C) bahas lookback/penetrasi dan durasi secara terpisah. Angka 1 tick, 6 M5 dan toleransi sentuh masih proposal sampai Owner memilih. Semua enam kandidat tetap belum diregistrasi/test, `HOLDOUT_LOCKED`, `LIVE_OFF`.

#### AGENDA D10-K16 — Tren H1 dan konfirmasi M15 B2/S2 (BELUM DIPUTUSKAN)

Rekomendasi desain yang dapat dibuat deterministik tanpa mengoptimalkan hasil:
1. **Tren H1 berbasis struktur:** B2 BUY hanya jika **dua swing high terkonfirmasi terakhir** dan **dua swing low terkonfirmasi terakhir** meningkat secara ketat (HH+HL); S2 SELL jika keduanya menurun (LH+LL). Masing-masing swing H1 memakai pivot 2 kiri/2 kanan dan *confirmed_at* dua bar H1 setelah pivot. Selain itu WAIT:TREND_UNCONFIRMED. Ini opsi A rekomendasi; EMA50/200 atau kombinasi EMA hanya alternatif yang harus ditetapkan sebelum uji.
2. **Zona H1:** pakai first-visit full-wick 48 valid H1 dan hybrid breach D10-K9/K10; `zone_confirmed_at` harus mendahului kunjungan; jika quote intrabar melewati distal+buffer saat mencari entry, blokir; jika H1 close di luar distal INVALID, jika kembali ke dalam CONSUMED. Satu episode kunjungan, bukan jumlah sentuh tick. Pilih satu zona eligible dengan aturan prioritas deterministik sebelum tes.
3. **Konfirmasi M15 proposed baseline:** pada episode sentuhan pertama, satu candle M15 tertutup berwarna searah yang **berawal/menyentuh zona dan close melewati proximal edge keluar di arah tren** (BUY close > zone_high; SELL close < zone_low); tidak memerlukan engulfing atau indikator masa depan. Candle harus benar-benar ditutup ketika zona masih eligible dan belum breach; entry pada quote berikut. Alternatif: engulfing M15 atau break high/low sebelumnya—masing-masing hipotesis berbeda jika dibandingkan.
4. **Risk & exit:** SL BUY di bawah zone_low atau low pembentuk struktur yang sudah ditentukan, SL SELL di atas zone_high (buffer min tick/spread, 0.10×ATR14 M15); TP struktur H1 valid terdekat pada sisi profit, tanpa minimum RR; Time Exit 12 M15 / 240m / pra-tutup 30m sesuai keputusan.
5. **Bukan keputusan final:** aturan terakhir ini merupakan proposal untuk Owner. Belum di-freeze, belum didaftarkan, belum digunakan untuk backtest. Parameter zone origin tie-break, jam entry/quote sesi sah, ATR history/gaps, level TTL lain, dan harga tick vs OHLC perlu fixture.

Kandidat B3/S3 akan dibahas setelah pilihan aturan B2/S2. `B1_S1_ONE_BAR_RECLAIM_APPROVED`, `B2_S2_TREND_CONFIRM_PENDING`, `PREREGISTRATION_NOT_READY`, `HOLDOUT_LOCKED`, `LIVE_OFF`.

#### KEPUTUSAN D10-K14 — Hybrid Time Exit batas candle dan UTC disetujui; audit preregistration (Owner, rapat 4 Nov 2026)

Owner menyetujui **baseline awal** untuk enam hipotesis XAUUSD:
- `B1/S1 liquidity sweep`: **12 candle M5 tertutup** atau **90 menit UTC dari fill**, atau **15 menit pra-penutupan broker** (D10-K13), mana yang terjadi paling awal;
- `B2/S2 trend pullback`: **12 candle M15** atau **240 menit UTC**, atau **30 menit pra-penutupan**;
- `B3/S3 breakout/breakdown retest`: **24 candle M5** atau **180 menit UTC**, atau **20 menit pra-penutupan**.
Pemicu exit hanya menghasilkan permintaan eksekusi; tanpa quote eksekutabel, `EXIT_PENDING_NO_QUOTE` bukan fill. SL/TP yang lebih dahulu tersentuh tetap berlaku. Perhitungan candle harus menggunakan bar yang **sepenuhnya mulai setelah fill**; weekend/data gap tidak menghasilkan bar fiktif. Menit berdasarkan timestamp UTC, bukan menit bar. Untuk batas sesi, bukti jadwal quote/trade per simbol/server serta DST masih wajib; angka ini tidak mengotorisasi runtime atau backtest.

**AUDIT KESIAPAN PREREGISTRATION (read-only review repo main pada 4 Nov 2026, belum registrasi):**

- **Kebijakan eksperimen: AVAILABLE.** `docs/research/VALIDATION_PROTOCOL.md` menetapkan fields spec (`name,symbol,side,regime,playbook,rules,parameters` + `code_sha256` direkomendasikan), `registry.jsonl` berantai hash, `split.json` dengan gaps, `costs.json`, koreksi `alpha=.05/N`, walk-forward 28 hari, baseline tiga arah, dan holdout hanya sekali. `scripts/research/register_setup_hypothesis.py` memblokir lebih dari 5 per simbol/sisi. **Keenam B1/S1/B2/S2/B3/S3 BELUM didaftarkan sebagai hipotesis final**, karena parameter/mesin tidak cocok dan dataset/biaya belum diaudit.
- **Simulator yang ada BELUM SESUAI dengan keputusan rapat.** `src/katarina/research/setups/simulator.py` sekarang hanya memuat `M5` + `H1`, menghitung `max_hold_bars` pada M5, belum menetapkan M15 entry untuk B2/S2, belum hybrid clock+preclose, dan belum status zona first-visit/hybrid breach. `src/katarina/research/setups/core.py::signal` memakai `target_rr` tetap dan memerlukan `min_rr >= .01`, padahal Owner menetapkan **TP struktur dan tanpa minimum RR**. `pullback.py` sekarang hanya mean-pullback M5, bukan H1 demand/supply dengan konfirmasi M15; `market_structure.py` M5 close-break, bukan H1 breakout diikuti M5 retest; `liquidity_sweep.py` referensi range M5, bukan confirmed pivot M15 (2+2) disusul M5 reclaim. **Jangan memakai simulator lama sambil mengklaim keenam desain telah diuji.**
- **Definisi entry kandidat belum lengkap:** jendela lookback dan umur swing/level target (di luar zona H1 48-bar); jarak tembus minimal sweep, definisi reclaim/konfirmasi bullish/bearish, kriteria H1 tren, definisi level resistance/support dan breakout, batas maksimum tunggu retest, tepatnya pembentukan origin zone terakhir jika beberapa candle memenuhi, tie-breaking overlap/zona, spread limit dan sesi eligible; setiap aturan harus deterministik, causal dan terdokumentasi dengan fixture.
- **Data & infrastruktur belum terverifikasi untuk praregistration aktual:** diperlukan arsip development historis broker sah serta manifest/hash, penyesuaian jam server→UTC independen, tick/bid-ask dan gap; `split.json`, `costs.json` broker (spread, komisi, slippage, swap), `code_sha256`, registry workspace yang tidak tercampur holdout, dan host riset terisolasi yang disetujui. `scripts/research/export_dev_bars.py` sendiri melarang dijalankan pada VPS observer produksi, memerlukan research terminal terpisah, dan mengunci cutoff data **sebelum 13 Okt 2026** (lihat `DEV_CUTOFF_UTC`). Jangan akses holdout atau menggunakan forward Stage0 untuk tuning.
- **Jadwal sesi resmi belum tersedia:** `docs/maintenance/MT5_SESSION_MAP_20261104.md` menyatakan arsip tick hanya indikasi empiris, bukan bukti `SymbolInfoSessionQuote/Trade`; `docs/maintenance/BROKER_SYMBOL_SESSION_EVIDENCE_20261103.md` menyiapkan probe read-only yang belum pernah dieksekusi. Klaim kesiapan full preclose harus **BLOCKED_SESSION_EVIDENCE**, bukan memakai waktu hasil tick sebagai jadwal broker resmi.
- **Tanpa minimum RR tetap berlaku**: jangan selundupkan filter `min_rr` atau seleksi net reward; target hanya struktur geometris yang kausal. Invalid SL/TP dan missing target = WAIT dengan reason; trade berbiaya tinggi tetap dianalisis dan dilaporkan. Stop k=0.10 ATR14 dan usia first-visit 48 H1 adalah keputusan yang disetujui.
- **Tahap berikutnya sebelum registry:** tulis spesifikasi lengkap dan fixture per kandidat; perbaiki simulator *offline research branch* agar sesuai desain, dengan audit tick/quote, no-lookahead, determinisme, cost + event order; verifikasi/siapkan input data development dan sesi. Baru freeze code+dataset+split+costs dan registrasi keenam hipotesis sekaligus **sebelum** hasil P/L apa pun. Host riset bukan terminal produksi. Tidak ada hak untuk install/run MT5 script pada VPS produksi tanpa persetujuan khusus.
- **Kesimpulan pemeriksaan:** `DESIGN_APPROVED_TIME_EXIT` / `PREREGISTRATION_NOT_READY` / `SIMULATOR_MISMATCH` / `SESSION_EVIDENCE_BLOCKED` / `HOLDOUT_LOCKED` / `LIVE_OFF` / `NO_BACKTEST`.

#### KEPUTUSAN D10-K13 — Batas pra-penutupan 15 / 30 / 20 menit sebagai baseline awal (Owner SETUJU, rapat 4 November 2026)

Owner menyetujui **nilai awal untuk 6 hipotesis XAUUSD** sebelum backtest, ditetapkan atas dasar desain dan tidak boleh dipilih ulang dari hasil profit:
- `B1/S1` Liquidity Sweep: **15 menit** sebelum akhir sesi efektif simbol;
- `B2/S2` Trend Pullback: **30 menit**;
- `B3/S3` Breakout/Breakdown Retest: **20 menit**.

Pada masing-masing jendela: **blokir entry baru dan upayakan exit posisi aktif** berdasarkan quote bid/ask yang memang eksekutabel. Kedua tindakan ini disetujui sebagai *desain parameter awal*; **aktivasi bergantung verifikasi** jam quote+trade MT5 pada broker dan simbol yang tepat (termasuk DST, jeda harian, holiday dan daya eksekusi close). Tanpa bukti sesi: `BLOCKED_SESSION_EVIDENCE`, tidak boleh mengarang jadwal atau menyatakan exit terlaksana. Status `EXIT_PENDING_NO_QUOTE` dipertahankan sampai ada quote yang benar-benar memenuhi model fill; risiko gap tetap dilaporkan. Jangan mengubah hasil historis ketika jadwal terverifikasi berbeda.

**AGENDA LANJUTAN D10-K14 — Batas candle + waktu nyata (BELUM DIPUTUSKAN):**

| Kandidat | Proposal batas jumlah candle lengkap setelah entry | Proposal batas waktu nyata sejak fill | Pra-penutupan (SUDAH dipilih) |
|---|---|---|---|
| B1/S1 Sweep | 12 bar M5 | 90 menit | 15 menit |
| B2/S2 Pullback | 12 bar M15 | 240 menit | 30 menit |
| B3/S3 Breakout | 24 bar M5 | 180 menit | 20 menit |

Metodologi yang perlu dikunci bersamaan dengan angka:
1. Hitung bar hanya bila candle dari TF entry **benar-benar selesai setelah fill**, termasuk definisi apakah bar parsial saat fill dihitung (usulan: hanya bar yang `bar_open >= fill_at` dan `bar_close > fill_at`). Jangan buat candle akhir pekan atau menganggap data gap sebagai bukti tidak terjadi pergerakan.
2. Deadline waktu nyata = `fill_at_utc + N*60s`, selalu berjalan saat sesi tutup; event eksekusi ditentukan oleh quote setelah trigger. Waktu menunjukkan **exit intent**, bukan fill yang dijamin.
3. Tiga batas hybrid bersaing secara temporal. Pada event yang lebih awal antara SL/TP struktural, jumlah candle, deadline waktu, dan pra-penutupan broker, lakukan penilaian sesuai quote nyata dan urutan tick. Tidak ada pemilihan outcome terbaik jika SL/TP bertabrakan dalam OHLC bar.
4. Tanggal/sesi resmi broker per symbol, server offset, DST dan cutover dari dataset diaudit, bukan tebakan. Jika informasi tidak tersedia, fixture sintetis boleh dipakai menguji logika, tetapi backtest penuh yang memerlukan kebijakan close-session tetap blocked.
5. Semua nilai yang kelak disetujui menjadi satu set parameter per hipotesis; jika diubah setelah melihat P/L maka hipotesis baru (ID hash, hitungan Bonferroni, batas maksimum 5 per sisi per simbol). Jangan menambahkan variasi hanya untuk mencari profit.

Keputusan D10-K13 adalah **persetujuan nilai pra-penutupan untuk spesifikasi awal, bukan klaim telah memvalidasi sesi/hasil**. `CANDLE_AND_CLOCK_LIMITS_PENDING`, `NO_BACKTEST_AUTHORIZED`, `HOLDOUT_LOCKED`, `LIVE_OFF`.

#### KEPUTUSAN D10-K12 — Kebijakan pra-penutupan berbeda per strategi/simbol (Owner SETUJU, 4 Nov 2026)

Owner memilih **opsi C**: aturan entry block dan upaya penutupan sebelum sesi tutup **boleh berbeda menurut strategi dan simbol**, asalkan dipraregistrasikan dan dikunci sebelum pengujian. Keputusan ini **hanya menetapkan kebijakan desain**, bukan menit final, izin backtest/live, atau aturan sesi broker yang belum dibuktikan.

**Usulan baseline untuk dibahas (BELUM DISETUJUI):** seluruh 6 kandidat pertama memakai XAUUSD.vx; referensi adalah penutupan sesi quote/trade server yang terverifikasi, bukan jam kalender universal.

| Kelompok | Blokir entry + upayakan exit sebelum sesi berakhir | Status |
|---|---|---|
| B1/S1 Liquidity Sweep | 15 menit | Proposal |
| B2/S2 Trend Pullback | 30 menit | Proposal |
| B3/S3 Breakout/Breakdown Retest | 20 menit | Proposal |

Jika instrumen kedua ditambahkan, sesi dan parameter harus didefinisikan **per simbol** dalam hipotesis tersendiri, bukan menerapkan parameter XAUUSD diam-diam. Verifikasi sesi MT5 per simbol/server (trade **dan** quote), DST, break, kalender libur, serta kecukupan quote sebelum/bagi exit wajib sebelum pemeriksaan ini dapat dianggap berlaku.

**Aturan fail-closed:** jika bukti sesi broker hilang, status `BLOCKED_SESSION_EVIDENCE` dan tidak boleh menebak jam; jika sudah masuk jendela pra-penutupan, tidak ada entry baru dan exit diajukan; exit hanya diakui bila quote fill realistis, jika tidak tersedia catat `EXIT_PENDING_NO_QUOTE` beserta risiko posisi. SL, TP, batas candle dan batas waktu UTC diputuskan berdasarkan event aktual yang terjadi paling awal; tidak ada P/L buatan pada data gap.

**Pengendalian overfitting / jumlah percobaan:** keenam `B1/S1/B2/S2/B3/S3` = 6 hipotesis awal (`3 per sisi XAUUSD` dari maksimum 5 per instrumen per sisi di roadmap), **bukan** 6 percobaan gratis per varian. Semua konfigurasi berbeda pada `symbol × side × entry/exit/timeframe/preclose` yang ditetapkan sebagai hipotesis dihitung sebagai eksperimen sendiri; jika nilai 15/30/20 diubah setelah melihat hasil, buat ID baru dan jumlahnya tetap masuk registry. Total `N` untuk koreksi Bonferroni dihitung dari seluruh percobaan registry, tidak hanya yang lolos. Batas maksimal 5 per simbol/sisi tidak boleh dilampaui tanpa keputusan governance baru. Jangan menguji beberapa preclose lalu mengambil yang paling profitable secara tersembunyi.

**Masih terbuka:** angka 15/30/20 menit, parameter 12 M5/90m, 12 M15/240m, 24 M5/180m, cara membaca sesi quote/trade resmi, instrumen pembanding, serta prasyarat dataset pengembangan. `PRE_CLOSE_PER_STRATEGY_SYMBOL_APPROVED`; `NUMERIC_PRE_CLOSE_NOT_FROZEN`; `NO_BACKTEST`; `HOLDOUT_LOCKED`; `LIVE_OFF`.

#### KEPUTUSAN D10-K11 — Hybrid Time Exit dipilih Owner (rapat 4 Nov 2026)

Owner menyetujui **pendekatan hybrid**: penutupan posisi simulasi dipicu oleh kejadian paling awal dari (a) jumlah candle entry-TF sah yang ditentukan, (b) deadline waktu nyata UTC yang ditentukan, atau (c) batas pra-penutupan sesi quote broker resmi yang terverifikasi. **Nilai dan tata cara masih agenda, bukan parameter final.** Tidak mengaktifkan trading, tidak melakukan backtest, tidak membuka holdout. SL/TP struktur tetap independen dan tidak boleh dikalahkan oleh exit waktu yang datang belakangan.

**Pilihan angka untuk dibahas, bukan keputusan:** B1/S1 sweep = 12 bar M5 / 90 menit; B2/S2 pullback = 12 bar M15 / 240 menit; B3/S3 breakout = 24 bar M5 / 180 menit. Batas clock sedikit lebih lama daripada durasi nominal bar agar berfungsi sebagai pengaman ketika bar tidak tersedia. Bandingkan dengan usulan lama 12 M5/60 menit, 12 M15/180 menit, dan 24 M5/120 menit: itu hampir identik pada data kontinu dan bukan hybrid yang bermakna. Jangan memilih angka berdasarkan P/L. Semua enam kandidat dan angkanya harus didaftarkan sebelum tes historis.

**Kausalitas & mekanisme penutupan (proposal):**
- Catat `entry_utc`, `exit_deadline_utc`, `eligible_closed_bars_since_entry`, `broker_quote_session_close_utc`, `exit_trigger` dan `first_executable_quote_utc`. Candle dihitung hanya bila candle telah benar-benar tutup; hari libur/akhir pekan tidak membuat bar fiktif. Batas waktu UTC tetap berjalan ketika pasar tutup.
- Trigger timeout adalah *niat untuk keluar*, bukan bukti fill. Jika deadline bertepatan dengan pasar tutup, tanpa quote valid, atau data GAP, catat `EXIT_PENDING_NO_QUOTE`/status data yang valid; jangan menciptakan harga penutupan atau profit. Eksekusi simulasi hanya bila bid/ask eksekutabel berikutnya benar-benar tersedia; gap dan slippage harus tercermin dalam hasil.
- Broker `quote/trade sessions` harus dibuktikan per simbol/server, termasuk DST dan hari libur. Opsi *pra-tutup* (misal 15 menit sebelum akhir quote session) belum disetujui. Jika evidence sesi belum tersedia, uji jadwal dengan fixture tetapi jangan mengklaim perlindungan sesi siap di trading nyata. Jangan menggunakan jeda D9 buatan untuk memperbaiki angka hasil.
- Jika stop, TP, atau exit waktu bertabrakan, penentu adalah urutan event tick terverifikasi; ketika OHLC tidak menjelaskan kejadian dalam bar yang sama, gunakan asumsi konservatif yang dibekukan atau `BLOCKED_UNRESOLVED_INTRABAR`. Tidak boleh memilih outcome terbaik pasca-fakta. Wajib uji reverse replay, gap, dan event tie.
- Semua variasi batas candle, menit, pre-close, dan perlakuan weekend menjadi ID hipotesis baru jika berubah setelah baseline. Tidak ada revisi berdasarkan hasil holdout; data Stage 0 forward tidak dijadikan data tuning.
- Sesi pasar harus aman: bila posisi tidak bisa keluar sebelum quote berhenti, status risiko terbuka tidak dipalsukan menjadi flat. Risk Governor, LIVE OFF dan zero orders tidak berubah.

**Masih perlu keputusan Owner:**
1. Apakah angka 12 M5/90 menit (sweep), 12 M15/240 menit (pullback), 24 M5/180 menit (breakout) diterima sebagai *parameter awal*, atau diubah sebelum freeze?
2. Apakah *pra-penutupan* diterapkan 15 menit sebelum sesi quote resmi per simbol, dan apakah melarang entry baru pada jendela itu?
3. Jika sesi broker resmi belum terbukti, apakah pengujian baseline sementara ditandai `BLOCKED_SESSION_EVIDENCE` (rekomendasi), alih-alih menebak jadwal?

**Status:** `HYBRID_TIME_EXIT_APPROVED`, `TIME_CAPS_NOT_FROZEN`, `SESSION_CLOSE_NOT_VERIFIED`, `HOLDOUT_LOCKED`, `LIVE_OFF`.

#### AGENDA D10-K11 — TIME EXIT (USULAN, BELUM DIPUTUSKAN)

Exit waktu menjadi batas maksimum holding bila TP struktural dan SL tidak tersentuh. Opsi: (1) N candle tertutup berdasarkan TF entry, (2) batas jam nyata, atau (3) kombinasi keduanya. Semua membutuhkan definisi praregistrasi, data waktu yang benar, dan model eksekusi bid/ask/biaya. TP/SL yang lebih dahulu tersentuh mengakhiri trade; jangan gunakan informasi setelah waktu kejadian untuk memilih exit yang terbaik. Usulan N awal untuk pembahasan: B1/S1 = 12 M5; B2/S2 = 12 M15; B3/S3 = 24 M5. Angka belum disetujui dan bukan hasil optimasi. Perlu putuskan penghitungan jeda pasar, akhir pekan, ketentuan flat menjelang tutup sesi, dan apakah variasi N dicatat sebagai eksperimen baru.

#### Pembahasan lanjutan D10-K8 — First-touch dan invalidasi (belum diputuskan)

Perlu memisahkan **status zona** dari **stop posisi**: batas H1 yang belum selesai tidak boleh menjadi alasan mengabaikan stop yang tersentuh. Usulan state machine deterministik `FRESH → FIRST_VISIT → CONSUMED/INVALID/EXPIRED`. Proposal "first visit" berarti **satu episode kunjungan** setelah konfirmasi zona (bukan hanya satu tick); deteksi masuk zona dari quote broker yang valid dan penerapan entry dari candle M15 selesai. Setelah harga keluar dari zona, kunjungan berikutnya tidak lagi fresh. Jika tidak ada konfirmasi pada kunjungan pertama, harus diputuskan apakah status menjadi `CONSUMED` (rekomendasi untuk menghindari cherry-picking) atau diizinkan retest berikutnya sebagai hipotesis berbeda.

Opsi invalidasi sebelum entry:
- **I1 — Close H1 di luar distal**: cocok sebagai konfirmasi struktur, tetapi selama candle H1 terbentuk, harga dapat menembus jauh ke sisi salah dan kembali; state butuh `PROVISIONAL_BREACH` serta kebijakan risiko yang jelas.
- **I2 — Intrabar breach distal + buffer dengan quote broker**: membatalkan zona segera sebelum entry, lebih ketat dan menghindari penggunaan zona yang tertembus jauh sebelum candle H1 close; namun sensitif spike/spread dan perlu aturan feed/tick serta sumber bid/ask yang sah.
- **I3 — Hybrid**: invalidasi struktur H1 ketika close distal, **larang entry baru segera** begitu quote melewati distal + buffer sampai keadaan diklarifikasi; untuk posisi terbuka tetap SL dieksekusi berdasarkan quote stop, tidak menunggu H1 close. Harus dirumuskan tanpa lookahead.
Semua perlu uji data gap, event order, dan perbedaan bid/ask. Belum ada yang disetujui.

#### Agenda D10-K8 — Fresh demand/supply, invalidasi, dan buffer SL (USULAN; BELUM DIPUTUSKAN)

**Rancangan mekanisme zona yang dapat diuji** untuk B2/S2 pada H1:
1. `demand`: candle bearish terakhir yang telah selesai sebelum dorongan bullish dengan **close H1 di atas swing high H1 yang sudah confirmed**. `supply`: candle bullish terakhir sebelum dorongan bearish dengan **close H1 di bawah confirmed swing low**. Candle asal harus sudah selesai; zona **full wick high-to-low** dari candle asal untuk baseline; timestamp `zone_origin_at`, `zone_confirmed_at` (break of structure), `swing_confirmed_at` dicatat.
2. **Fresh**: sejak `zone_confirmed_at` hingga pertama kali harga kembali memasuki zona, belum ada bar/tick **setelah konfirmasi** yang menyentuh batas zona. Sentuhan pertama membuat status `FIRST_TOUCH`; konfirmasi entry dalam episode kunjungan pertama ini boleh, dan saat entry selesai status `CONSUMED`. Kunjungan berikutnya tidak fresh, tidak memunculkan sinyal kandidat yang sama. Riwayat sebelum confirmation tidak boleh digunakan retroaktif untuk membuat zona tampak lebih fresh.
3. **Kedaluwarsa**: batas maksimum usia zona H1 yang diputuskan sebelum tes, usulan **48 candle H1 tertutup** sejak konfirmasi; setelahnya `EXPIRED`. Bila banyak zona, pilih eligible yang paling dekat terhadap harga, dengan tie-break `zone_confirmed_at` lalu `zone_id`, keduanya konsisten. Ini usulan bukan angka terbukti.
4. **Invalidasi pra-entry**: usulan `close` H1 yang sudah selesai **di luar distal boundary** (demand: close di bawah `zone_low`; supply: close di atas `zone_high`), atau bukti tick menembus batas SL struktural yang telah dihitung pada saat sinyal. Satu close di luar distal boundary membuat `INVALID`, tidak bisa dipakai ulang. Jangan menunggu bar H1 yang belum tertutup untuk memutuskan; bila ada harga bergerak menembus stop pada bar belum tertutup, perlakukan dengan manajemen risiko fail-safe, bukan menyatakan zona belum invalid.
5. Untuk sinyal `B1/S1` sweep dan `B3/S3` breakout-retest, invalidasi tetap memakai **ekstrem sweep atau ekstrem retest yang sudah diketahui**. Fresh zone supply/demand H1 **tidak otomatis menjadi syarat** keenam strategi: hanya digunakan jika tercatat dalam definisi hipotesis tertentu.

**Proposal buffer SL** (belum diputuskan, jangan dianggap nilai optimal):
- `ATR14` memakai candle TF entry **yang sudah ditutup sebelum keputusan** (M5 atau M15). `spread_at_decision` dari bid/ask broker, `tick_size` dari spesifikasi symbol yang diverifikasi.
- `buffer = ceil_to_tick(max(1*tick_size, spread_at_decision, 0.15 * ATR14))` untuk eksperimen baseline **jika Owner menyetujui k=0.15**, dengan pembulatan menjauh dari entry (BUY SL ke bawah, SELL SL ke atas). Definisi ATR dan pembulatan harus diuji dengan fixture deterministik; buffer mengubah SL/risiko, bukan target struktural. Jangan mengganti `k` setelah melihat hasil; bila mengganti => hipotesis baru, hitung semua attempts.
- Usulan perbandingan: `k=0.10` (lebih rapat) atau `k=0.20` (lebih longgar) adalah **alternatif pilihan sebelum backtest**, bukan sweep parameter saat memilih hasil; masing-masing jika diuji harus diregistrasikan sebagai hipotesis tambahan.
- Stop invalid, nol/negatif, atau tidak dapat diletakkan karena batas broker => `WAIT` dengan reason, bukan SL fiktif atau memindahkan stop diam-diam.
- **Tanpa minimum RR**, sesuai D10-K6; jangan memasukkan filter RR lewat kriteria lain. TP harus valid secara geometri dan kausal; hasil net setelah biaya dilaporkan meskipun negatif.

**Keputusan terbuka untuk Owner:** (A) fresh=kunjungan pertama saja + full-wick zone + kadaluarsa 48 H1, (B) invalidasi zona dengan close H1 di luar distal boundary, dan (C) buffer `max(tick, spread, 0.15×ATR14)`, atau minta revisi angka/definisi sebelum freeze. **Saat ini baru definisi swing 2+2 yang disetujui**, tiga komponen lain masih usulan. `NO_BACKTEST_YET`, `HOLDOUT_LOCKED`, `LIVE_OFF`.

#### A. Bukti yang disepakati untuk tiap hari

Sumber fakta tetap ledger SQLite observer read-only dan arsip tick broker, bukan ringkasan chat. Gunakan satu ID dan cutoff yang direkam (saat ini `2026-11-03T15:18:14Z` pasca-WP13; pengecualian DST-aware D8 baru efektif `2026-11-05T00:00:00Z`). Simpan kedua tanggal secara terpisah dan hindari retroaktif.

Kondisi kelulusan **yang sudah ada, tidak diubah**:
1. Minimal 10 **hari bursa berturut-turut** yang benar-benar selesai; tiap hari dilihat dari **≥90% coverage menit sesi** berdasarkan jam broker/simbol sah, dengan hari parsial dan Sabtu/Minggu tidak dihitung sebagai hari lulus.
2. **≥98% siklus OK saat sesi sah** di keseluruhan jendela; alasan untuk setiap non-OK, dengan denominator dan status RAW tidak diubah.
3. Nol duplikat dan timestamp monoton; clock broker stabil & kredibel; bid/ask/spread tercatat & coverage quote ≥98%; **≥3 pemulihan terverifikasi dalam 10 menit**; tick setiap hari disimpan atau GAP diberi alasan dan direkonsiliasi; **0 order** dan LIVE OFF.
4. Pisahkan status `CODE/CI PASS`, `DEPLOYED`, `STAGE0 PASS`, dan `TRADING EDGE PROVEN`. Tidak satu pun menggantikan yang lain.

**Snapshot langsung VPS 4 Nov 2026 sekitar 21:27 WIB**, checker sejak cutoff resmi: `IN_PROGRESS`, 0/10 hari lengkap; 1.183/1.247 OK = **94,8677%**; 47 STALE_QUOTES dan 17 SOME_SYMBOLS_WITHOUT_QUOTE; clock `PASS` (+2 h), recovery 3 tes formal PASS (+2 spontan), quote 99,45%, duplikat 0, orders 0; tick & reconciliation `NO_DATA` pada jendela baru karena hari jatuh tempo belum ada. Dataset historis WP12 tetap utuh (tidak dihapus). Diagnostik tanpa memengaruhi laporan resmi: dari 64 gagal, 61 terjadi dalam jendela jeda NY 17:00, 3 di luar jendela.

#### B. Agenda D9 — cara memperlakukan jeda CFD secara adil

Peta tick empiris `docs/maintenance/MT5_SESSION_MAP_20261104.md` membuktikan **gap quote**, bukan jadwal resmi broker. Selama musim dingin AS 2026, FX terhenti ~21:54–22:00 UTC, XAUUSD.vx ~21:54–23:00, NAS100.vx ~21:57–23:01. Situs Valetax hanya menampilkan simbol/spesifikasi kontrak; **jam quote/trade per server `.vx` tetap harus dibaca dari terminal MT5 (Specification → Sessions atau diagnostik `SymbolInfoSessionQuote`)**. Jangan pakai jam broker lain.

**Pilihan untuk Owner, belum ada yang disetujui:**
- **A: Pertahankan D8 −15/+30**. Kelebihan: kriteria lama tetap jelas. Risiko: penilaian akan terus menghitung sebagian jeda ketika XAU/NAS benar-benar tidak punya quote; kegagalan hampir pasti walau koneksi normal.
- **B: Perpanjang semua simbol secara global menjadi −15/+60**. Kelebihan: sederhana, selaras dengan gap CFD; diagnostik menghasilkan ~99,75% pada snapshot terbaru. Risiko: FX yang sudah buka pada 17:00–18:00 NY ikut dikecualikan; **berisiko mempermudah metrik tanpa justifikasi per simbol**, sehingga tidak dianjurkan sebelum bukti resmi.
- **C (rekomendasi Yura untuk dibahas): pakai jadwal quote/trade broker PER SIMBOL** dari MT5, validasi terhadap tick, tanggal efektif prospektif setelah keputusan. Sesi saat FX buka tetap dinilai, simbol yang secara resmi tutup diberi reason `SESSION_CLOSED`/non-countable sesuai kontrak yang diuji; tidak membuat quote palsu. **Butuh kajian denominator, 3 simbol bergerak pada clock probe, dan tes DST/special holidays** sebelum aktivasi. Tidak otomatis dinilai PASS.

Bukti minimum sebelum D9 diputuskan: 5 simbol dari terminal aktif, tanggal/waktu broker, `server_shift_hours` terverifikasi, jadwal `quote` dan `trade` harian termasuk jeda, asal data, cross-check tick/gap, lalu regression test fail-closed untuk pasar tutup vs broker outage. Bukti per akun/server disimpan privat; report yang dipublikasikan bersih dari akun/password.

#### C. Agenda kredibilitas 10 hari

- **Opsi hitungan**: tetap cutoff WP13 3 Nov 15:18:14Z menurut keputusan D8; atau mulai seri prospektif baru sesudah perubahan aturan D9 bila dianggap perubahan material pada definisi sesi. Jangan mengubah tanggal diam-diam. Data lama boleh dibandingkan sebagai baseline dengan label `LEGACY`, bukan bukti forward untuk aturan baru.
- **Dua scorecard terpisah:** `historical/legacy` untuk analisis akar kegagalan; `official/forward` untuk status tahapan. Tiap hari tampilkan tanggal UTC, coverage menit sesi per simbol, OK/total/success %, reason counts, clock shift/source, jumlah tick/gap dan matching, reconnect evidence, duplicate, 0 order dan SHA laporan.
- **Hari bursa pertama:** 4 Nov adalah hari penuh pertama *yang berpotensi dinilai* karena cutoff WP13 ada pada 3 Nov sore UTC, belum selesai pada rapat. Jika Owner mensyaratkan hanya hari pasca-D8, 5 Nov menjadi kandidat pertama. Keduanya bukan jaminan; satu hari dengan coverage rendah memutus streak. Jangan menyatakan tanggal akhir pasti.
- **Sistem mengukur** `best_streak` dan `current_streak`; laporan "10 hari" tidak boleh menutupi bahwa keberhasilan siklus agregat, data broker, dan clock adalah gate terpisah.

#### D. Pekerjaan paralel dan batas izin

- **Yura sekarang:** audit ledger read-only, cek broker document public vs bukti MT5, breakdown 49 kode P0, catat hasil/risiko dan validasi antarkode. Tidak mengubah task/observer/DB.
- **Claude sekarang:** lanjutkan 49 tes jalur kegagalan nyata (**bukan hanya menulis literal kode untuk mempercantik indeks**), dibagi: broker 22, demo execution 8, cloud 9, automatic connection 3, dialog model 6, owner surface 1. Setiap batch PR dengan tes negatif, code gate, CI Body/Ubuntu/Windows, tanpa mengubah risk/promotion/historical gate.
- **WP6:** checker langsung mengeluarkan `P0 WP6_NO_AUTOLOGON` dan `NOT_READY AUTOLOGON_INTERACTIVE`. Owner harus menimbang autologon Windows dan risikonya atau menyediakan lingkungan MT5 alternatif yang benar-benar terbukti dapat berjalan tanpa sesi interaktif. Jangan menulis password ke GitHub/ChatGPT/log. Setelah persetujuan window, tes reboot sesungguhnya dan rollback.
- **Bukti sesi broker:** eksekusi probe MT5 read-only hanya dengan persetujuan operasional Owner; tidak ada order, tidak ada terminal MT5 kedua pada VPS produksi.
- **Host riset #255:** perlu Windows PC/VM terpisah dari VPS produksi. Tidak boleh mengaku backtest M5 resmi selesai sebelum provenance UTC broker dan hash diverifikasi.

**Keputusan rapat yang belum dibuat**:
1. Tetap 10 hari bursa penuh + seluruh sembilan gate apa adanya? (rekomendasi: YA)
2. D9: A / B / C? (rekomendasi: C setelah bukti sesi MT5 nyata)
3. Jika D9 disetujui setelah sebagian hari teramati, kapan cutoff resmi *baru* dan bagaimana baseline lama dipertahankan?
4. WP6: Owner memilih autologon terproteksi atau host/arsitektur lain, dan kapan maintenance window reboot?
5. Bukti per simbol FX/XAU/NAS dan akses host riset siapa yang menyiapkan?

**Status tetap: `MEETING_OPEN_OWNER_DECISION_REQUIRED`.** Tidak ada promosi stage, trading, atau deployment karena dokumen ini.

### D9 — Lebar jendela jeda harian: −15/+30 tidak menutup jeda CFD broker
Claude · 4 Nov 2026 · status: Menunggu Owner
Usulan: Peta sesi dari arsip tick broker ([MT5_SESSION_MAP_20261104](maintenance/MT5_SESSION_MAP_20261104.md)) menunjukkan:
- jeda FX hanya 16:54–17:00 New York;
- jeda XAUUSD.vx berlangsung 16:54–18:00 (65 menit) dan NAS100.vx 16:57–18:01 (63 menit).

Jendela D8 (−15/+30, efektif 5 Nov) berakhir 17:30 New York, sehingga 22:30–23:00 UTC tetap gagal karena tidak ada quote CFD dari broker. Tampilan diagnostik: −15/+30 = 97,83 %, −15/+60 = 99,85 % (ambang 98 %).
Pertanyaan:
1. Pertahankan −15/+30, atau ganti ke −15/+60 (jeda CFD penuh) secara prospektif dari tanggal efektif baru?
2. Atau tunggu jadwal sesi resmi per simbol dari MT5 *Specification → Sessions* (GUI, Owner)?
Tanggapan:
- [Claude 4 Nov] Bukti hanya 2 hari dengan jam terverifikasi (2–3 Nov) plus 3 hari pendukung (27–29 Okt). Tidak ada yang diubah; D8 tetap berlaku sampai Owner memutuskan.
Keputusan: —
Tindak lanjut: Owner memutuskan; bila diubah, PR konstanta prospektif seperti #288.

## Checkpoint Manager — 3 November 2026 (catatan koordinasi, BUKAN keputusan Owner baru)

- **Bukti kode:** Draft [integrasi #265](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/265) head `cd3b576d`, setelah perbaikan audit Claude/Manager [#266](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/266), sudah [CI Body/Ubuntu/Windows sukses](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/41480635219). Source PR #257/#259/#263/#264 ditutup sebagai digantikan, tidak di-merge ke main. **Head Jules #259 terbaru `ce7c4074` reintroduksi PASS+NO_DATA -> PASS**; jangan cherry-pick branch tersebut.
- **Syarat release belum berubah:** review manusia/Owner untuk `main` belum APPROVED; tidak ada deploy VPS (`C:\Katarina\code` `64497b5` saat cek), 0 order, Stage0 belum PASS, LIVE OFF.
- **Keputusan terbuka untuk Owner:** apakah menggunakan mesin Windows/VM riset MT5 yang TERPISAH untuk mengambil bar M5 historis ValetaxIntl-Live2 bersufiks `.vx` dan membuktikan UTC/DST + SHA256 sebelum cutoff `2026-10-13T00:00:00Z`. Ini adalah izin operasional TERPISAH dari persetujuan merge/deploy. VPS produksi 2 GB RAM/terminal observer tidak boleh dipakai untuk riset broker tanpa izin baru.
- **Tugas coding nonoperasional** boleh disiapkan tanpa izin MT5: Draft pengaman `--terminal-path`, tes fail-closed, dan rekonsiliasi dokumen. Tidak pernah memulai `MetaTrader5.initialize()` pada observer atau membuka holdout. Sumber tugas dan gate: [#255](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/255), [Manager Board #262](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues/262).

## Keputusan terakhir (maks. 10 baris; yang lebih lama ada di Git)

- 4 Nov — **D8 diputuskan Owner** ("oke saya setujui semua"; pilihan WP15 −15/+30). Rollover DST-aware 17:00 New York
  −15/+30 menit berlaku prospektif mulai 5 Nov 2026 00:00 UTC. Hitungan 10 hari Tahap 0 dimulai ulang dari deploy WP13
  (3 Nov 15:18:14 UTC); data lama tetap tersimpan. Ambang 98 %, denominator dan data historis tidak diubah. Roadmap Tahap 0 diperbarui.
- 29 Okt — Owner mengukuhkan visi Katarina sebagai agentic AI mandiri untuk informasi, penalaran,
  riset, memori, evaluasi, dan usulan perbaikan; keberhasilan diukur dari hasil bersih setelah biaya
  yang terverifikasi. Keputusan dan batasnya ada sekali di `docs/ROADMAP.md` (Arah lanjutan → Agentic AI).


- 29 Okt — Owner: ChatGPT menjadi **manager** dengan akses penuh (roadmap, antrean, merge, VPS); Claude **eksekutor**.
  Aturan tetap Owner (bagian 1–7) tidak berubah. Roadmap "Mulai di sini" diperbarui.
- 29 Okt — D1 selesai: ChatGPT berhasil membuat branch dan PR (#213, branch `chatgpt/wp13-clock-since-20261029`).

- 29 Okt — Usulan agentic AI diterima sebagai arah; WP14 auditor data baca-saja masuk antrean setelah WP13 dan WP8c
  (Owner menjawab "ya", 29 Okt). Rincian: roadmap "Arah lanjutan → Usulan agentic AI".
