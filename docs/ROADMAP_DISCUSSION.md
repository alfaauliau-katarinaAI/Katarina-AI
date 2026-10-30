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

## Keputusan terakhir (maks. 10 baris; yang lebih lama ada di Git)

- 29 Okt — Owner mengukuhkan visi Katarina sebagai agentic AI mandiri untuk informasi, penalaran,
  riset, memori, evaluasi, dan usulan perbaikan; keberhasilan diukur dari hasil bersih setelah biaya
  yang terverifikasi. Keputusan dan batasnya ada sekali di `docs/ROADMAP.md` (Arah lanjutan → Agentic AI).


- 29 Okt — Owner: ChatGPT menjadi **manager** dengan akses penuh (roadmap, antrean, merge, VPS); Claude **eksekutor**.
  Aturan tetap Owner (bagian 1–7) tidak berubah. Roadmap "Mulai di sini" diperbarui.
- 29 Okt — D1 selesai: ChatGPT berhasil membuat branch dan PR (#213, branch `chatgpt/wp13-clock-since-20261029`).

- 29 Okt — Usulan agentic AI diterima sebagai arah; WP14 auditor data baca-saja masuk antrean setelah WP13 dan WP8c
  (Owner menjawab "ya", 29 Okt). Rincian: roadmap "Arah lanjutan → Usulan agentic AI".
