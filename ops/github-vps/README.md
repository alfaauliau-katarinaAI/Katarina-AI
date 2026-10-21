# GitHub ↔ VPS: jalur pemeriksaan baca-saja

Jalur ini menggunakan repositori canonical **alfaauliau-katarinaAI/Katarina-AI**, bukan URL pemilik lama. Tidak menginstal servis, mengubah Git remote, melakukan `git pull`, membuka port, atau memulai trading.

## Komponen yang sudah ada

- Source GitHub: https://github.com/alfaauliau-katarinaAI/Katarina-AI
- Panduan konteks Claude: [CLAUDE.md](../../CLAUDE.md).
- Jalur eskalasi VPS yang ada: [katarina-vps-lab.yml](../../.github/workflows/katarina-vps-lab.yml) (manual `workflow_dispatch`, hanya `main`, memerlukan runner berlabel `self-hosted, windows, x64, katarina-vps`).
- Request yang diizinkan workflow: `ops/vps/requests/actions/<nama>.json`, dengan verifikasi berkas dan allowlist tugas oleh `Invoke-KatarinaRemoteTask.ps1`.
- Prosedur resmi kerja: [GITHUB_FIRST_DEVELOPMENT.md](../../docs/operations/GITHUB_FIRST_DEVELOPMENT.md); verifikasi sumber dilakukan dahulu melalui Body CI.

**Penting:** keberadaan workflow tidak membuktikan runner VPS online. Status runner, kredensial Git pada host, path checkout aktual, dan jaringan host harus diuji di VPS. Windows Server 2012 R2 bukan OS yang tercantum dalam dukungan runner GitHub saat ini. Jangan memaksakan instalasi runner baru, mengubah keamanan VPS, atau menjalankan workflow otomatis pada push.

## Pemeriksaan dari VPS (tanpa perubahan berkas)

Di PowerShell pada VPS, dari checkout Katarina AI yang benar, jalankan dengan **path yang sudah diverifikasi** (jangan menebak folder atau menjalankan pada repositori lain):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\ops\github-vps\Test-KatarinaGitHubRoute.ps1" -RepoRoot "PATH_CHECKOUT_KATARINA_YANG_SUDAH_DIVERIFIKASI"
```

Hasil adalah JSON pada terminal, tanpa disimpan ke disk. `CONNECTED_READONLY` artinya host ini dapat membaca `main` di GitHub lewat HTTPS dan checkout lokal memiliki `origin` ke repo canonical. `BLOCKED` berarti periksa field yang gagal. Pemeriksaan ini **tidak** membuktikan ada agent yang aktif, status Actions self-hosted, sinkronisasi data runtime, atau komunikasi Claude langsung ke VPS.

Cara menilai sinkronisasi source: bandingkan `local_head_sha` dengan `github_main_sha`; ketidaksamaan bukan alasan untuk mereset/menimpa checkout. Tinjau perubahan lokal dan release manifest sebelum melakukan update menggunakan prosedur deployment yang berlaku.

## Akses Claude / cloud

- Claude dapat membaca dokumen melalui URL GitHub publik ini, atau melalui konektor GitHub bila diaktifkan dalam akun Claude. Berkas ini **bukan** kredensial atau jembatan eksekusi Claude.
- Untuk melakukan pemeriksaan VPS dari GitHub, gunakan workflow manual **Katarina VPS Lab** hanya setelah runner yang benar terbukti online, permintaan read-only telah ditinjau, dan commit sumber lolos CI.
- Akses langsung melalui Cloudflare/SSH membutuhkan tunnel dan aturan identitas terpisah, tidak otomatis diberikan oleh koneksi GitHub. Jangan mengekspos RDP, MT5, endpoint eksekusi, atau token.
- Tidak boleh mengubah file lain, mengaktifkan live trading, membuat heartbeat commit, mencatat rahasia, atau mengirim order.

Referensi:
- GitHub deploy keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys
- GitHub self-hosted runners: https://docs.github.com/en/actions/reference/runners/self-hosted-runners
- GitHub Actions runner security: https://docs.github.com/en/actions/reference/security/secure-use
- Cloudflare SSH: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/use-cases/ssh/
