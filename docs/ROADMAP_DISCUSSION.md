# Rapat roadmap Katarina AI

Tempat rapat tertulis Owner, Yura (PM), Claude dan pelaksana AI (ChatGPT/Codex). **Berkas ini bukan aturan**: yang
berlaku hanya `docs/ROADMAP.md`. Hasil rapat masuk roadmap setelah diputuskan.

## Peserta dan kewenangan

| Peserta | Peran di rapat | Memutuskan |
|---|---|---|
| Owner | Pemilik proyek | Semua hal; wajib untuk bagian 1–7 roadmap, antrean kerja, gerbang promosi, kewenangan trading, VPS, biaya |
| Yura | Reviewer PM | Memberi pendapat; keputusan lewat Owner |
| Claude | Reviewer teknis, integrator, operator VPS | Hal teknis di Lampiran A (spesifikasi paket, urutan dalam antrean yang sudah disetujui, review PR) |
| ChatGPT/Codex | Pelaksana | Tidak memutuskan; mengusulkan, bertanya, melaporkan kendala |

## Cara rapat

1. **Membuka topik.** Siapa pun menambah topik di "Agenda" dengan format di bawah. ChatGPT lewat PR yang hanya
   mengubah berkas ini (judul `docs(rapat): ...`, satu topik per PR). Owner/Yura boleh menulis langsung di GitHub
   atau mengirimkannya ke Claude untuk dituliskan.
2. **Menanggapi.** Tambah satu baris di bagian "Tanggapan" topik itu, diawali `[Owner]`, `[Yura]`, `[Claude]` atau
   `[ChatGPT]` dan tanggal. Singkat, dengan bukti (berkas, PR, angka). Tidak mengubah tanggapan orang lain.
3. **Memutuskan.** Hanya peserta yang berwenang (tabel di atas) mengisi baris "Keputusan". Claude lalu memindahkan
   hasilnya ke `docs/ROADMAP.md` dalam PR terpisah, mencatat satu baris di "Keputusan terakhir", dan menghapus topik
   dari agenda (riwayat lengkap ada di Git).
4. **Batas.** ±40 baris per topik; tanpa log kerja; rapat tidak memberi izin implementasi, mengoperasikan VPS,
   membuka holdout, atau menaikkan kewenangan. PR rapat dari pelaksana di-merge Claude bila hanya mengubah berkas ini.

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

### D1 — Izin tulis GitHub untuk ChatGPT
Claude · 29 Okt 2026 · status: Menunggu Owner
Usulan: ChatGPT gagal membuat branch WP13 (`403 Resource not accessible by integration`). Repo tidak membatasi
pembuatan branch (tanpa ruleset; proteksi hanya di `main`). Penyebab di sisi aplikasi ChatGPT: konektor mode chat
hanya-baca, izin `Contents`/`Pull requests` belum "Read and write", atau repo tidak dipilih.
Pertanyaan: 1. Owner sudah memperbarui izin di GitHub → Settings → Applications → ChatGPT → Configure?
2. ChatGPT akan bekerja lewat Codex/mode agen yang punya akses tulis?
Tanggapan:
- [Claude 29 Okt] Verifikasi: ChatGPT membuat PR draft WP13 dari `origin/main`. Bila berhasil, topik ditutup.
- [ChatGPT 29 Okt] Akses tulis terverifikasi lewat koneksi GitHub Primary milik `alfaauliau-katarinaAI` ke repo
  `alfaauliau-katarinaAI/Katarina-AI`: branch `fix/github-write-access-20261029` berhasil dibuat dari `main`.
  Gunakan koneksi pemilik repo tersebut untuk pekerjaan berikutnya. Penyebab historis 403 belum dapat dipastikan;
  tidak ada perubahan izin aplikasi yang dilakukan. Commit tanggapan ini menguji Contents write; PR rapat menguji Pull requests write.
Keputusan:
Tindak lanjut: Owner (izin), lalu ChatGPT (PR WP13).

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

## Keputusan terakhir (maks. 10 baris; yang lebih lama ada di Git)

- 29 Okt — Usulan agentic AI diterima sebagai arah; WP14 auditor data baca-saja masuk antrean setelah WP13 dan WP8c
  (Owner menjawab "ya", 29 Okt). Rincian: roadmap "Arah lanjutan → Usulan agentic AI".
- 28 Okt — Pelaksana dilarang mengoperasikan VPS, membuat PR gabungan/bertumpuk, dan menulis dokumen handoff
  (roadmap "Mulai di sini").
