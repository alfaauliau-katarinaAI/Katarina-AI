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
Keputusan:
Tindak lanjut: ChatGPT (keputusan; spesifikasi WP13 disesuaikan), Claude (eksekusi di PR #233).

## Keputusan terakhir (maks. 10 baris; yang lebih lama ada di Git)

- 29 Okt — Owner mengukuhkan visi Katarina sebagai agentic AI mandiri untuk informasi, penalaran,
  riset, memori, evaluasi, dan usulan perbaikan; keberhasilan diukur dari hasil bersih setelah biaya
  yang terverifikasi. Keputusan dan batasnya ada sekali di `docs/ROADMAP.md` (Arah lanjutan → Agentic AI).


- 29 Okt — Owner: ChatGPT menjadi **manager** dengan akses penuh (roadmap, antrean, merge, VPS); Claude **eksekutor**.
  Aturan tetap Owner (bagian 1–7) tidak berubah. Roadmap "Mulai di sini" diperbarui.
- 29 Okt — D1 selesai: ChatGPT berhasil membuat branch dan PR (#213, branch `chatgpt/wp13-clock-since-20261029`).

- 29 Okt — Usulan agentic AI diterima sebagai arah; WP14 auditor data baca-saja masuk antrean setelah WP13 dan WP8c
  (Owner menjawab "ya", 29 Okt). Rincian: roadmap "Arah lanjutan → Usulan agentic AI".
