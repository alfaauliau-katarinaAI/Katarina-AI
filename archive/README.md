# Arsip

Berkas di sini **tidak dipakai** oleh runtime Katarina, workflow CI, tes, atau dokumen aktif
pada saat diarsipkan (21 Oktober 2026). Isinya disimpan utuh sebagai jejak riset.

| Folder | Isi |
|---|---|
| `scripts/research/` | Skrip riset sekali pakai (audit dan backtest ber-versi) yang tidak dirujuk lagi |
| `docs/research/outputs/` | Output riset 12 Oktober 2026 yang tidak dirujuk dokumen aktif |
| `docs/research/` | Laporan riset bertanggal 10–13 Oktober 2026 yang sudah digantikan riset berikutnya |
| `docs/validation/` | Bukti eksperimen JSON 10 Oktober 2026 (zone/scalp/router lama) yang tidak dirujuk |
| `docs/handoff/`, `docs/maintenance/`, `docs/roadmap/` | Checkpoint, audit cleanup, dan rencana kerja 12–19 Oktober yang sudah lewat |

Struktur folder mengikuti lokasi asal. Untuk memakai lagi sebuah berkas, pindahkan
kembali ke lokasi asalnya (`git mv archive/<path> <path>`) dan tambahkan rujukannya.
Skrip arsip tidak diuji CI dan bisa saja tidak cocok lagi dengan kode terbaru; tautan
relatif di dokumen arsip bisa mengarah ke berkas yang tidak ikut diarsipkan.
