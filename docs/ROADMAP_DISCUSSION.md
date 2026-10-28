# Rapat roadmap Katarina AI

Tempat rapat tertulis Owner, Yura (PM), Claude dan pelaksana AI (ChatGPT/Codex). **Berkas ini bukan aturan**: yang
berlaku hanya `docs/ROADMAP.md`. Hasil rapat masuk roadmap setelah diputuskan.

## Peserta dan kewenangan

| Peserta | Peran di rapat | Memutuskan |
|---|---|---|
| Owner | Pemilik proyek | Semua hal; satu-satunya untuk bagian 1–7 roadmap, gerbang promosi, kewenangan trading |
| ChatGPT | Manager | Roadmap, antrean, spesifikasi paket, pembagian tugas, review/merge, operasi VPS |
| Claude | Eksekutor | Menjalankan keputusan ChatGPT; menyampaikan bukti dan risiko teknis |
| Yura | Reviewer PM | Memberi pendapat; keputusan lewat Owner |

## Cara rapat

1. **Membuka topik.** Siapa pun menambah topik di "Agenda" dengan format di bawah. ChatGPT lewat PR yang hanya
   mengubah berkas ini (judul `docs(rapat): ...`) atau langsung bersama perubahan roadmap. Owner/Yura boleh menulis
   langsung di GitHub atau mengirimkannya ke ChatGPT/Claude untuk dituliskan.
2. **Menanggapi.** Tambah satu baris di bagian "Tanggapan" topik itu, diawali `[Owner]`, `[Yura]`, `[Claude]` atau
   `[ChatGPT]` dan tanggal. Singkat, dengan bukti (berkas, PR, angka). Tidak mengubah tanggapan orang lain.
3. **Memutuskan.** Peserta yang berwenang (tabel di atas) mengisi baris "Keputusan". ChatGPT atau Claude lalu
   memindahkan hasilnya ke `docs/ROADMAP.md`, mencatat satu baris di "Keputusan terakhir", dan menghapus topik dari
   agenda (riwayat lengkap ada di Git).
4. **Bentuk.** ±40 baris per topik; tanpa log kerja. Aturan tetap Owner (LIVE OFF, Risk Governor, batas 35%,
   gerbang promosi, holdout) hanya berubah dengan keputusan Owner.

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
Keputusan: Menunggu pembahasan Claude dan keputusan pihak berwenang.
Tindak lanjut: Claude audit existing dan berikan opsi paket serta tes; Owner memutuskan perubahan gerbang/kewenangan.

### D5 — Perapian branch lama dan disiplin PR tanpa tumpukan
Owner/Yura (usulan untuk review Claude) · 29 Okt 2026 · status: Terbuka
Usulan: Pertahankan satu basis \`main\` untuk PR baru, hindari PR bergantung pada branch PR lain, dan hapus branch
yang terbukti tidak digunakan setelah audit commit/PR. Jangan merge gabungan perubahan lama untuk sekadar bersih-bersih.
Audit 29 Okt: PR terbuka 0 saat diperiksa; kandidat sisa branch PR ditutup tanpa merge adalah
\`chatgpt/docs-pr-review-blockers-20261023\`, \`chatgpt/dc2-repair-review-20261027\`,
\`chatgpt/stage0-clock-audit-20261028\`, \`chatgpt/mt5-stage0-10day-readonly-20261028\`,
\`chatgpt/claude-full-system-audit-20261028\`; branch uji izin \`chatgpt/write-permission-check-20261029\`
identik dengan \`main\`. Kelima branch lama masih mengandung commit unik, bukan otomatis aman dihapus.
Pertanyaan: 1. Apakah seluruh commit unik sudah diganti/ditolak dengan alasan atau perlu dipecah menjadi paket baru?
2. Apakah WP13, bridge MCP/VPS, dan broker discovery masih digunakan dan siapa pemiliknya?
Tanggapan:
- [ChatGPT/Yura 29 Okt] Jangan hapus branch aktif/bernilai tanpa verifikasi; tidak mengubah runtime VPS.
Keputusan: Menunggu verifikasi dan keputusan pembersihan.
Tindak lanjut: Claude audit dependensi dan commit unik; manager menyetujui penghapusan kandidat terverifikasi lewat mekanisme GitHub.

## Keputusan terakhir (maks. 10 baris; yang lebih lama ada di Git)

- 29 Okt — Owner: ChatGPT menjadi **manager** dengan akses penuh (roadmap, antrean, merge, VPS); Claude **eksekutor**.
  Aturan tetap Owner (bagian 1–7) tidak berubah. Roadmap "Mulai di sini" diperbarui.
- 29 Okt — D1 selesai: ChatGPT berhasil membuat branch dan PR (#213, branch `chatgpt/wp13-clock-since-20261029`).

- 29 Okt — Usulan agentic AI diterima sebagai arah; WP14 auditor data baca-saja masuk antrean setelah WP13 dan WP8c
  (Owner menjawab "ya", 29 Okt). Rincian: roadmap "Arah lanjutan → Usulan agentic AI".
