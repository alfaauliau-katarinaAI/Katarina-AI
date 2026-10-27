# Handoff perbaikan terisolasi Katarina AI — 27 Oktober 2026

**Untuk Claude / reviewer.** Audit ini dilaksanakan lewat **Desktop Commander akun kedua** pada perangkat `WIN-4TTT19K3CL8`. File yang diperiksa/diperbaiki berada di worktree terpisah:
`C:\Katarina\_roadmap_validation\repair-integration-20261027`, branch `chatgpt/repair-integration-20261027`.

## Batas perubahan dan keamanan

- Checkout produksi `C:\Katarina\code` **tidak disentuh oleh edit, merge, atau redeploy**; HEAD produksi saat pemeriksaan `d8b003a`. Hanya fetch metadata remote pada repositori Git yang sama.
- Task `Katarina-Readonly-Observer` terbaca `Running` pada Task Scheduler, mode `Interactive only`. Ini bukan konfirmasi kesehatan data terbaru.
- **LIVE OFF**, tidak mengaktifkan akun DEMO, worker, `order_send`, atau mengubah `promotion_lock.json`.
- Tidak melakukan pembacaan/optimasi holdout. Data sebelum penerapan perbaikan jam WP12 bukan bukti harga forward.
- Merge kerja ini **bukan merge ke `main`**. Semua pemasangan/runtime tetap menunggu audit Claude dan otorisasi yang sudah ditetapkan.

## Apa yang diperbaiki dan bagaimana

1. **WP12 / PR #204 — jam tick MT5 server -> UTC.** Ambil perubahan PR sebagai merge terisolasi dari `origin/main`, tidak menimpa runtime produksi. Tes `test_server_utc_wp12.py` memeriksa shift +2, +3, peralihan DST, quote kausal dan fail-closed; `test_legacy_clock_wp12.py` memeriksa dua jalur lama tetap WAIT/karantina. Pada integrasi, kedua paket tersebut lulus **5 + 2 tes**. Jalur legacy `screening.collect` dan `run_readonly_decisions` tetap dikarantina; konversi seluruh arsip historis belum tersertifikasi.
2. **WP9b / PR #205 — measured inputs + shadow decisions.** Merge ke worktree WP12; conflict teks pada `CHANGELOG.md`, `RUNTIME_MODULE_MAP.md`, dan `release-manifest.json` tidak diselesaikan dengan menerima data stale WP9b. File generator dipertahankan dan harus dibuat ulang dari kode gabungan. Integrasi otomatis `observer.py` dan `observation_ledger.py` diuji lagi. Tes `test_decision_inputs.py` **5 lulus**, `test_decision_shadow.py` **2 lulus**; shadow tetap 0 order.
3. **WP8a / PR #195 — eksport dataset pengembangan.** PR #195 dibangun atas basis `main` lama, sehingga merge seluruh branch akan **menghapus** kode WP2/WP3/WP9a/WP11 yang sudah ada. Hanya 3 berkas WP8a (`dev_dataset.py`, `export_dev_bars.py`, `test_dev_dataset_wp8a.py`) dipindahkan secara selektif ke integrasi, tanpa membawa penghapusan berkas yang sudah merge.
4. **Perbaikan keselamatan bar historis WP8a.** Sebelumnya `rate["time"]` langsung diberi label UTC. Sekarang setiap chunk memanggil `broker.verified_historical_bar_shift(symbol, timeframe, start_utc, end_utc)`. Bukti harus eksplisit `verified=True`, `time_basis="INDEPENDENT_UTC"`, `shift_hours` integer -12..+14, dan `source_sha256` 64 heksadesimal. Offset diterapkan pada koordinat query server dan dikurangkan dari epoch bar **sebelum** cutoff holdout/cek penutupan. Setiap chunk menyimpan `clock_evidence` di manifest; loader menolak manifest tanpa bukti valid. Nilai verified=True dan SHA pada API adalah klaim adapter operator; kode hanya memvalidasi struktur dan mencatat jejak, **bukan memverifikasi kebenaran sumber independen secara kriptografis**. Broker MT5 asli **tidak memiliki adapter bukti independen ini**, maka CLI ekspor dengan broker mentah akan **fail-closed**, bukan menerbitkan dataset dengan UTC yang mungkin keliru.
5. Tambah empat kasus regresi WP8a (tanpa bukti -> tolak, offset server +3 -> UTC, bukti bertanda tidak verified -> tolak). Total **12 tes WP8a lulus**, mencakup tes asli hash/cutoff/gap/determinisme.

## Verifikasi dan batas bukti

- Tes tertarget yang dijalankan di worktree DC kedua: 5 WP12 UTC, 2 WP12 legacy, 5 WP9b unit, 2 WP9b integrasi, 12 WP8a = **26 tes lulus**. Lima suite tambahan (peta modul 2, manifest 2, jam broker 14, quote kausal 9, ledger 13) memberikan **40 tes PASS**, total **66 tes tertarget PASS**.
- Tes dilakukan dengan Python 3.12.10 milik VPS; menggunakan stub/sintetis dan file temporer. **Tidak** dinyatakan sebagai hasil broker nyata atau profitabilitas.
- Suite static lokal: **69 PASS, 2 FAIL dari 71** karena Python VPS tidak mempunyai paket numpy, diimpor historical_analog_memory. Gagal pada test_every_katarina_module_imports dan test_script_imports_resolve, bukan bukti regresi perubahan WP12/WP9b/WP8a. Belum memasang dependensi di host RAM 2GB. Periksa kembali di CI terisolasi yang punya dependensi lengkap.
- Regresi lengkap >1000 tes **tidak dijalankan pada host produksi RAM 2GB** karena bisa mengganggu observer. Gunakan GitHub Actions Linux + Windows pada HEAD integrasi, lalu cek artefak.
- Sudah dijalankan pada worktree: peta modul **245** (A=187, B=40, C=15, D=3), manifest resmi **MATCH 304/304**, dan **PASS_PROMOTION_GATE**. Reviewer harus menjalankan ulang generator pasca perubahan/rebase: `python scripts/governance/runtime_import_map.py --output docs/maintenance/RUNTIME_MODULE_MAP.md`, `python scripts/deployment/release_manifest.py --manifest ops/deployment/release-manifest.json --generate`, verifikasi ulang manifest `MATCH`; `python scripts/governance/promotion_gate.py --check`.
- Hasil audit sumber `main` per 27 Oktober tetap: edge belum terbukti (profit factor kandidat 0,36 pada audit 13 Oktober), pengamatan forward Tahap 0 belum mencapai kriteria kelulusan, dan DEMO/LIVE tidak boleh dinyalakan.

## Sisa blocker dan urutan review Claude

1. **Paling penting:** verifikasi per simbol + timeframe + chunk periode historis untuk offset/DST menggunakan **referensi UTC independen** dan bukti harga yang memadai. Broker ticks dan bars dengan basis jam server yang sama **tidak** membuktikan UTC hanya dengan saling dicocokkan. Berikan adapter `verified_historical_bar_shift` yang berlandaskan bukti terarsip, atau biarkan WP8a menolak ekspor.
2. Tinjau apakah karantina `screening.collect` menghentikan konsumen aktif yang diperlukan; validasi semua entry point waktu historis WP12. Jangan hilangkan penolakan tanpa verifikasi waktu.
3. Lakukan rerun semua tes/CI lintas Linux/Windows dan manifest/peta modul pada HEAD gabungan; periksa regressi ledger, observer, risk, import, dan risiko memori loader WP8a untuk dataset multi-tahun.
4. WP9b tetap default `legacy_fail_closed`, `measured_inputs` hanya untuk shadow/riset, jangan diaktifkan di VPS tanpa review serta otorisasi Owner.
5. Setelah sukses, Claude mereview/merge sesuai aturan roadmap dan **baru kemudian** merencanakan deployment WP12 ke VPS dengan rollback, memulai ulang hitungan Tahap 0. Jangan backfill CELAH menjadi data forward.
6. `docs/ROADMAP.md` baris R5 yang masih menyebut WP9b/WP12 "Siap dikerjakan" adalah status **usang** relatif terhadap PR #204/#205 yang terbuka; reviewer Claude perlu menyelaraskan R5 setelah review, tidak menganggap PR lulus hanya karena tes tertarget berhasil.

## Rujukan

- WP12: https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/204
- WP9b: https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/205
- WP8a: https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/195
- Roadmap status dan governance: `docs/ROADMAP.md`, `docs/PROJECT_STATUS.md`, `CLAUDE.md`.
