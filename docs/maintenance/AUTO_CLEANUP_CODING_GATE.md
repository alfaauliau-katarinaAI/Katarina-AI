# Katarina AI — Gate coding dan pembersihan otomatis (mandat Owner)
**Dicatat: 4 November 2026 · Berlaku untuk perubahan kode berikutnya di repository Katarina AI**

## Keputusan Owner
Owner meminta **mekanisme permanen di dalam proyek Katarina**, bukan tugas terjadwal/automation pada Claude. Saat Claude, developer, atau agent lain mengerjakan perubahan, **gate lokal sebelum commit dan CI pada push/pull request** harus menghalangi kesalahan kode dan perulangan perbaikan tanpa akar masalah. Proses cleanup aman dijalankan melalui alat repository yang sama. Jangan membuat cron/schedule Claude untuk fungsi ini.

**Status saat dokumen dibuat: SPESIFIKASI DAN PERINTAH IMPLEMENTASI, bukan klaim skrip gate baru telah terpasang/aktif.** Claude wajib mengimplementasikan, menguji, dan mengintegrasikannya dalam PR kode terpisah sebelum menyebut `ACTIVE`. CI lama sudah memiliki sebagian pemeriksaan (hygiene, dependencies, unit/static/integration, promotion gate), jangan menggandakannya secara boros.

## A. Mekanisme coding gate wajib di Katarina

Buat satu entry point CLI **di repository** (usulan `scripts/governance/code_change_gate.py`) yang dapat dijalankan secara lokal dan dipakai kembali oleh workflow `.github/workflows/katarina-body-ci.yml`. Tidak ada ketergantungan dengan sesi Claude atau koneksi VPS. Integrasikan dengan alat existing, jangan membuat implementasi ganda:
- `scripts/governance/audit_repo_hygiene.py` — file accidental/rahasia/artefak terindeks.
- `scripts/governance/audit_dependency_links.py` — import, JSON, link, MQL5 include, website.
- `scripts/governance/promotion_gate.py --check` — konstanta, risiko, kontrak terproteksi.
- `scripts/deployment/release_manifest.py` — inventaris hash `MATCH`, dihitung ulang **hanya oleh developer ketika source berubah**, tanpa auto-patching saat gagal.
- `scripts/governance/runtime_import_map.py`, `reason_code_index.py`, serta tes unit/static/integration dan pengujian Windows/Linux yang ada.

Gate berbentuk tahapan dengan ID stabil:

| Gate | Pemeriksaan wajib | Saat gagal |
|---|---|---|
| `KAT-CG-00` | Identitas HEAD, diff, status branch, file terproteksi, perubahan tak diharapkan | `BLOCKED_BASELINE`; tidak boleh lanjut/overwrite pekerjaan orang |
| `KAT-CG-01` | Sintaks semua Python terlacak (AST), validasi JSON, import, link, MQL5 include, tanpa file kosong/junk atau secret | `FAIL_SYNTAX_OR_DEPENDENCY`; tampilkan file:line |
| `KAT-CG-02` | Unit/static/integration yang relevan + regresi saat memperbaiki bug; bukti RED pada kode lama dan GREEN sesudah | `FAIL_TEST`; tidak men-skip/ubah ekspektasi untuk hijau palsu |
| `KAT-CG-03` | Promotion/Constitution/risk gates, release manifest `MATCH`, larangan perubahan kontrak/fail-open | `FAIL_SAFETY_OR_MANIFEST`; stop tanpa auto-repair risk |
| `KAT-CG-04` | CI Body, Ubuntu, Windows pada SHA final, reviewer sesuai kebijakan | `BLOCKED_CI_OR_REVIEW`; jangan merge |
| `KAT-CG-05` | Untuk rilis saja: kecocokan SHA target, backup dan rollback, smoke read-only, izin Owner, 0 order | `BLOCKED_DEPLOY`; tidak menyentuh VPS |

Jalankan gate yang murah dahulu (**fail-fast**), lalu pengujian yang mahal; reuse hasil CI yang sudah ada daripada menjalankan suite lengkap dua kali di workflow yang sama. Untuk PR, kegagalan satu gate harus membuat **check run FAIL** dan menahan merge melalui kebijakan branch protection yang disahkan Owner; jangan mengklaim branch protection sudah aktif sebelum diverifikasi admin GitHub.

## B. Mencegah siklus salah-perbaiki-salah

Setiap error wajib memiliki **fingerprint stabil** (contoh kombinasi `gate_id + reason_code + file:line + test_name`), prioritas P0/P1/P2, referensi commit/HEAD, serta status:
`DETECTED → REPRODUCED → ROOT_CAUSE_IDENTIFIED → PATCHED → REGRESSION_TESTED → VERIFIED`.

1. Pertama gagal: catat output terstruktur dan buat **tes yang mereproduksi akar masalah**; jangan memperbaiki berdasarkan pesan error yang tidak diverifikasi.
2. Jika fingerprint yang sama gagal lagi sesudah satu percobaan perbaikan: **STOP retry otomatis** dan tandai `REPEATED_FAILURE_NEEDS_ROOT_CAUSE`. Reviewer harus memeriksa akar masalah, lingkungan, perbedaan OS dan asumsi kode. Tidak boleh endless retry atau overwrite berulang.
3. Setelah perbaikan: wajib bukti tes sebelumnya merah lalu hijau (bila dapat direproduksi), suite relevan, manifest, dan review. Tidak boleh auto-skip, menurunkan timeout tanpa analisis, menghapus tes, memalsukan fixture, atau mengubah ledger agar lulus.
4. Kalau temuan membutuhkan data broker/Windows/Owner di luar lingkungan lokal, tandai `BLOCKED_EVIDENCE`; jangan membangun bypass.
5. Error yang sama dan status keputusan berikutnya dilaporkan ke Issue/PR dengan `ID | severity | fingerprint | file:line | akar masalah | tes | SHA | status`; jangan membocorkan token/password/path privat ke log.

**Gate melarang promosi kode yang salah, tetapi tidak menjamin semua bug terdeteksi.** Bukti CI tidak sama dengan Stage 0 PASS atau izin DEMO/LIVE.

## C. Pembersihan otomatis yang aman

Buat alat repository lokal (usulan `scripts/governance/safe_cleanup.py`) dengan dua mode:

- **`--check` / `--dry-run` (default):** identifikasi file cache/build/editor sementara, referensi mati, duplikasi hash, modul tidak terjangkau, dan artifacts. Keluarkan JSON + ringkasan; tidak menyentuh file.
- **`--apply-safe` (opt-in hanya untuk sandbox/worktree development):** hanya boleh menghapus **artefak sementara yang dihasilkan alat**, berada pada allowlist eksplisit (misalnya `__pycache__/`, `*.pyc`, `build/validation/` di checkout development) dan sudah diverifikasi tidak terindeks Git. Cegah traversal/symlink/reparse point, path di luar worktree, file sedang digunakan, dan penghapusan saat HEAD/working tree berubah. Harus idempotent dan memuat jejak tindakan yang bisa diaudit.

**Jangan hapus source tracked otomatis.** Sumber yang diduga tidak berguna hanya diberi `DELETE_CANDIDATE`, wajib cek dynamic import, launcher, konfigurasi stage, workflow, tests, release manifest, dan dependensi secara manual. Baru hapus lewat commit/PR dengan bukti `DELETE_CONFIRMED` dan rollback Git. File `UNVERIFIED_KEEP` tidak boleh dihapus.

**Larangan absolut cleanup:** `C:\Katarina\state`, tick broker, SQLite / WAL / SHM, snapshot, evidence Stage 0, `private`, secrets, `backups`, `logs` aktif, `docs/governance` milik Owner (termasuk untracked), terminal MT5, folder di luar checkout dev, file hidup yang sedang dipakai, `main` langsung, atau Git history/branches/tags. Jangan membuat cleaner VPS otomatis; cleanup worktree dan cabang GitHub tetap butuh bukti/approval khusus.

## D. Trigger repo-native, bukan jadwal Claude

1. **Saat developer akan commit:** perintah lokal `python scripts/governance/code_change_gate.py --quick` untuk syntax/dependency/hygiene + `safe_cleanup.py --check`. Inilah kontrak CLI target **setelah implementasi**.
2. **Saat push/PR:** GitHub Actions existing `katarina-body-ci.yml` mengulang pemeriksaan dan menjalankan suite serta gate keselamatan sesuai batas yang sudah ada. Tidak ada `schedule:` baru; gunakan event `push`, `pull_request`, dan `workflow_dispatch` existing.
3. **Saat source perlu dirampingkan:** cleaner hanya **melaporkan kandidat**, lalu perbaikan/hapus source dilakukan pada PR terpisah; setelah tiap patch gate dijalankan ulang secara terkendali, bukan loop otomatis.
4. **Saat merge/deploy:** CI final dan review sah. Deployment production/manual tetap keputusan Owner, bukan akibat gate GREEN.

Tidak ada auto-commit, auto-merge, force-push, restart, deploy, eksekusi MT5, pembukaan holdout, atau order.

## E. Acceptance test Claude — wajib sebelum gate aktif

- Suntikkan Python rusak dan JSON invalid di fixture izolasi → `KAT-CG-01` merah dengan file:line; pulihkan → hijau.
- Putuskan import/link/MQL5 include di fixture → merah; perbaiki → hijau.
- Tambahkan file `.env`/junk terindeks di fixture → `KAT-CG-01` merah tanpa mencetak isi secret.
- Rusakkan manifest atau file terkunci di fixture → `KAT-CG-03` merah; **tidak** diperbaiki otomatis.
- Ulangi fingerprint failure sesudah satu upaya → `REPEATED_FAILURE_NEEDS_ROOT_CAUSE`, bukan percobaan tak berakhir.
- `safe_cleanup --dry-run` tidak mengubah apapun; `--apply-safe` hanya menghapus allowlisted untracked cache pada repo tes. Symlink/junction, path escape, file tracked, file di luar repo, `state`/`backups`/`private` harus ditolak. Menjalankan dua kali idempotent.
- Seluruh tes unit, static, integration, hygiene, dependency, promotion gate, manifest, CI Body/Ubuntu/Windows lolos pada SHA final tanpa skip safety.
- Laporan mencatat before/after, apa yang **tidak** dihapus, buktinya, dan satu jalur `error → reason → test → fix`.

**Hasil penugasan Claude:** implementasi dalam PR coding terpisah, tes fixture negatif, laporan PR #262 dan `docs/REPAIR_HISTORY.md` hanya setelah benar-benar terverifikasi. Tandai `GATE_SPECIFIED_NOT_ACTIVE` sampai benar-benar wired + CI hijau; setelah itu baru `GATE_ACTIVE_VERIFIED`.

**Jangan mengganti gerbang promosi strategi/Stage 0 dengan coding gate ini.** Keduanya berbeda; LIVE OFF tetap berlaku.
