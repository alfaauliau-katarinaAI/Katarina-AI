# KATARINA AI

**Analisis lebih terarah. Keputusan lebih disiplin.**

KATARINA AI adalah proyek yang dikembangkan untuk membantu pengamatan pasar, evaluasi strategi, dan pengambilan keputusan yang lebih sistematis.

## Uji langsung di komputer

Windows: ekstrak source, jalankan **SETUP_KATARINA.bat**, lalu **START_KATARINA.bat**.
Uji awal memakai data buatan tanpa MT5/VPS dan menghasilkan laporan HTML lokal.
[Petunjuk uji PC dan MT5 baca-saja](docs/QUICKSTART_PC.md). Live tetap OFF.

## Tentang proyek

Fokus KATARINA AI adalah menghadirkan pengalaman analisis yang praktis, terukur, dan memperhatikan risiko. Pengembangan dan pengujian masih berlangsung.

## Status

**Development Preview / research-only. Live trading belum diaktifkan.** Edge strategi belum terbukti;
observer read-only di VPS uji sedang disiapkan ulang (menunggu login akun demo), DEMO forward belum berjalan.

[**Status lengkap**](docs/PROJECT_STATUS.md) ·
[**Roadmap**](docs/ROADMAP.md) ·
[**Perubahan**](CHANGELOG.md) ·
[**Diagram satu otak**](docs/architecture/KATARINA_SINGLE_BRAIN_WORKFLOW_20261016.md) ·
[**Akses GitHub lintas perangkat**](docs/operations/GITHUB_ACCESS.md)

Lulus pengujian sumber tidak membuktikan profitabilitas atau kesiapan trading live. Hasil CI terbaru ada di
[GitHub Actions](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions).

## Informasi

- [Perkembangan proyek](https://github.com/alfaauliau-katarinaAI/Katarina-AI/commits/main)
- [Status pengujian](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions)
- [Laporkan kendala](https://github.com/alfaauliau-katarinaAI/Katarina-AI/issues)

> **Perhatian:** Pasar keuangan memiliki risiko kerugian. Tidak ada jaminan hasil atau keuntungan. Gunakan lingkungan pengujian terlebih dahulu dan jangan membagikan kredensial akun.

## Pendanaan riset & kerja sama teknis

- [**KATARINA AI Research & Sponsorship — situs publik**](https://katarina-research.vercel.app/) (bisa dibaca tanpa login).
- Terbuka untuk pembahasan sponsor infrastruktur (VPS/data), riset yang dibiayai dengan ruang lingkup tertulis, serta jasa evaluasi sistem Python/MT5 dan laporan pengujian yang disepakati.
- **GitHub Sponsors masih dalam peninjauan** per 11 Oktober 2026. Belum ada tautan pembayaran sponsor aktif, paket berbayar yang sudah dijual, atau dana yang diterima melalui halaman ini.
- KATARINA AI masih **development preview**. Belum terbukti menghasilkan profit stabil, belum siap ditawarkan sebagai robot trading live, dan bukan produk investasi atau janji imbal hasil. Semua angka kinerja harus berasal dari pengujian yang dapat direproduksi.
- Hubungi: [email kerja sama](mailto:alfaaulia8@gmail.com?subject=KATARINA%20AI%20Research%20Collaboration).


## Layanan dan paket yang direncanakan

- [**KATALOG KATARINA — early access, belum menerima pembayaran**](website/plans.html): rencana akses gratis, paket riset premium, dan lisensi EA ketika selesai divalidasi. Harga bersifat indikatif, bukan penawaran transaksi aktif.
- [**Konsultasi dan jasa teknis**](mailto:alfaaulia8@gmail.com?subject=KATARINA%20AI%20Technical%20Services%20Quote): pengujian Python/MT5, QA data, integrasi non-trading, dan dokumentasi dengan penawaran tertulis.
- [**Kemitraan riset/infrastruktur**](website/sponsors.html): kontak awal, bukan checkout GitHub Sponsors.
- TIDAK menerima pembayaran paket langganan atau lisensi EA sampai produk, ketentuan penggunaan, verifikasi pembayaran, dan dukungan pelanggan siap. Tidak ada jaminan hasil trading.


## Catatan teknis

- [Audit struktur dan dependensi otomatis](scripts/governance/audit_dependency_links.py) diperiksa di GitHub Actions. Ini pemeriksaan sumber, **bukan** bukti kesiapan live.
- [Aturan pengembangan dan validasi](docs/operations/GITHUB_FIRST_DEVELOPMENT.md) · [panduan hosting Cloudflare Pages](docs/deployment/CLOUDFLARE_PAGES_SETUP.md).
- Dialog dan pretrial AI trading (LIVE OFF): `python katarina_pc.py pretrial` menjalankan acceptance sintetis;
  `chat --model-config PATH` dan `ui` membuka dialog model yang dikonfigurasi. Umpan balik MT5 hanya WAIT/ACK.
  [Kontrak dan gerbang bukti nyata](docs/architecture/KATARINA_AI_TRADING_PRETRIAL.md).
