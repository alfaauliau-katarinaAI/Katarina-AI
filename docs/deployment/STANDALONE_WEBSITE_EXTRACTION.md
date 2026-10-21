# Pemisahan website ke repo sendiri (perapian Tahap 7)

Situs publik saat ini masih di repo ini, karena project Cloudflare Pages men-deploy folder `website/`
dari `main`. Folder situs **jangan dihapus** sebelum Pages terbukti men-deploy dari repo baru.

## Yang sudah disiapkan di repo ini

`scripts/deployment/export_website_repo.py` menyalin hanya berkas publik yang di-track ke folder kosong:
`website/`, `functions/`, `sites/`, `oauth_gateway/`, `scripts/update_hot_news.py`, workflow
`katarina-hotnews.yml`, dan panduan Pages/monitor. Ditambah `README.md`, `.gitignore`, dan
`EXPORT_MANIFEST.json` (commit asal + SHA-256 tiap berkas). Kode otak, MT5, VPS, dan config tidak ikut.

Tidak ada penerbit yang meng-commit JSON ke `website/` dari repo ini: workflow hot-news hanya mengunggah
artifact, dan monitor runtime diisi publisher VPS lewat worker Cloudflare. Jadi pemisahan tidak butuh
token lintas-repo.

## Langkah Owner (tidak bisa dilakukan integrasi GitHub sesi Claude: pembuatan repo ditolak 403)

1. Buat repo baru, mis. `alfaauliau-katarinaAI/Katarina-Website` (boleh privat; Pages mendukung repo privat).
2. Di checkout repo ini:
   ```bash
   python scripts/deployment/export_website_repo.py --dest ../Katarina-Website
   cd ../Katarina-Website && git init -b main && git add -A && git commit -m "Initial website export"
   git remote add origin https://github.com/alfaauliau-katarinaAI/Katarina-Website.git && git push -u origin main
   ```
3. Cloudflare → Workers & Pages → project situs → Settings → Builds: hubungkan ke repo baru dengan setelan
   yang sama seperti sekarang (preset None, build kosong/`exit 0`, output `website`). Lihat
   [setup Pages](CLOUDFLARE_PAGES_SETUP.md). Worker `sites/runtime-monitor` dipindah dengan cara serupa.
4. Bandingkan halaman dan JSON di deployment baru dengan yang lama (checklist QA di setup Pages).
5. Setelah terbukti, minta PR lanjutan untuk menghapus `website/`, `functions/`, `sites/`, `oauth_gateway/`,
   `scripts/update_hot_news.py`, dan workflow hot-news dari repo ini (`audit_dependency_links` ikut berhenti
   memeriksa link website). Domain dipindah paling akhir.
