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

## Keputusan terakhir (maks. 10 baris; yang lebih lama ada di Git)

- 29 Okt — Owner: ChatGPT menjadi **manager** dengan akses penuh (roadmap, antrean, merge, VPS); Claude **eksekutor**.
  Aturan tetap Owner (bagian 1–7) tidak berubah. Roadmap "Mulai di sini" diperbarui.
- 29 Okt — D1 selesai: ChatGPT berhasil membuat branch dan PR (#213, branch `chatgpt/wp13-clock-since-20261029`).

- 29 Okt — Usulan agentic AI diterima sebagai arah; WP14 auditor data baca-saja masuk antrean setelah WP13 dan WP8c
  (Owner menjawab "ya", 29 Okt). Rincian: roadmap "Arah lanjutan → Usulan agentic AI".
