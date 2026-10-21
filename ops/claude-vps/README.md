# Claude Pro ↔ GitHub ↔ Katarina VPS — jalur kerja aman

Status: **STAGING ONLY / BELUM MEMBERI CLAUDE AKSES VPS**.
Pemilik: Owner Katarina. Tidak membuat API berbayar, GitHub Actions runner, webhook, SSH publik, token, atau akses trading.

## Target

- Source kebenaran: `https://github.com/alfaauliau-katarinaAI/Katarina-AI`.
- Checkout runtime yang sudah ada di VPS: `C:\KatarinaDev\github-main` (**jangan sentuh**).
- Checkout terpisah khusus review/PR Claude: `C:\KatarinaDev\claude-workspace\Katarina-AI`.
- Jalur perubahan: Claude Pro/Claude Code → branch `claude/*` → Pull Request → Body CI → persetujuan Owner → merge; deployment ke runtime adalah tindakan terpisah.
- File `CLAUDE.md` di root repository tetap menjadi sumber arahan dan batas keamanan utama.

## Fakta sebelum aktivasi (21 Oktober 2026)

- VPS Windows Server 2012 R2 (build 6.3.9600) dengan Git dan Node v18.18.0.
- Pemeriksaan awal menemukan `claude` tidak ada pada PATH; dukungan Claude Code pada OS lama ini **belum diverifikasi**.
- Checkout VPS existing tertinggal ratusan commit dan terdapat perubahan/hapus lokal; **tidak boleh melakukan pull/reset/clean terhadap checkout ini**.
- Repository saat ini publik. **Jangan commit kredensial, data akun, tick/data harga privat, memory, log pribadi, atau alamat VPS**.

## Jalur A: Claude Code di VPS (berpotensi menggunakan langganan Pro, tanpa API key)

1. Jalankan `ops/claude-vps/prepare-workspace.ps1` secara manual oleh Owner/operator setelah review. Script hanya melakukan shallow clone ke workspace baru; tidak mengubah checkout runtime.
2. Pastikan versi Windows mendukung rilis Claude Code yang akan dipasang. Jika tidak, **jangan memaksa instalasi atau upgrade OS/Node pada runtime trading**; gunakan komputer pendamping yang kompatibel atau jalur B.
3. Instal Claude Code sesuai dokumentasi resmi di lingkungan yang kompatibel; login interaktif menggunakan akun Claude Pro. **Jangan tempel token atau kode login di Issue/PR/chat**. Pastikan `ANTHROPIC_API_KEY` tidak disetel agar tidak tanpa sengaja ditagih melalui API.
4. Dari checkout terpisah, jalankan `claude`, terima trust workspace secara sadar, lalu gunakan `claude remote-control` jika fitur dan OS mendukung. Remote Control memerlukan proses lokal tetap hidup, dan dapat dikendalikan melalui aplikasi/web Claude yang sudah login.
5. Izinkan hanya baca/review/test di workspace baru. Gunakan branch dan PR untuk perubahan. Jangan berikan izin sistem administrator atau akses otomatis ke `C:\KatarinaDev\runtime`, `state`, `private-market-data`, kredensial, atau MT5; **folder terpisah saja tidak merupakan sandbox keamanan OS**. Untuk pembatasan nyata, gunakan user Windows non-admin dan ACL khusus setelah audit.

## Jalur B: Claude Code Cloud/Routines (Pro, hanya GitHub — bukan akses VPS)

1. Di `https://claude.ai/code/routines` (jika akun eligible), hubungkan repositori Katarina dan buat routine terbatas untuk review PR / coding.
2. Routine hanya boleh membaca source publik dan menghasilkan commit pada branch/PR. Jangan pasang konektor VPS, secret produksi, runner self-hosted, atau perintah deploy.
3. Owner/ChatGPT melihat diff, komentar dan status CI di GitHub. Ini **bukan percakapan ChatGPT-Claude real-time** dan **bukan akses terminal VPS**.
4. Untuk menyalurkan patch ke VPS, Owner harus terlebih dahulu meninjau dan menyetujui PR, memeriksa checksum/release dan menggunakan prosedur deploy yang ada. Tidak ada eksekusi otomatis kode PR di VPS.

## Uji penerimaan tanpa menyentuh trading

- [ ] Checkout Claude di lokasi baru, `git status` bersih, remote tepat.
- [ ] `C:\KatarinaDev\github-main` dan seluruh proses produksi tidak diubah.
- [ ] Metode autentikasi Claude Pro terverifikasi tanpa API key, jika memilih jalur A.
- [ ] Claude membaca `CLAUDE.md` dan berhasil membuat PR **dokumentasi saja**.
- [ ] Body CI sukses; tidak ada secret di commit, environment variable ataupun log.
- [ ] Tidak ada pengaturan port/firewall, akses administrator, scheduled task, webhook, runner, order MT5 atau perubahan Risk Governor.
- [ ] Owner menguji akses dari HP secara manual; statusnya didokumentasikan jujur.

**Catatan:** Akses dari GitHub ke VPS tidak timbul dari keberadaan berkas ini saja. Akses terminal Claude baru aktif setelah pemasangan yang kompatibel, login Pro yang sah, dan izin OS yang sesuai. Pekerjaan pada repository harus tetap melewati PR/branch protection.
