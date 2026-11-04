# Coding gate KAT-CG dan safe cleanup — panduan operasional

Implementasi dari spesifikasi Owner `docs/maintenance/AUTO_CLEANUP_CODING_GATE.md` (PR #278) dan
`CLAUDE_BLOCKER_CLOSURE_20261103.md` bagian 6. Mekanisme ini milik repository dan berjalan saat developer
memanggilnya atau saat push/PR. **Bukan** jadwal/automation Claude, tidak menyentuh VPS, broker, atau MT5.
Coding gate **bukan** gerbang promosi strategi dan bukan bukti Tahap 0. LIVE tetap OFF.

**Status 4 Nov 2026: `GATE_ACTIVE_VERIFIED` dan `AUTO_CLEANUP_SAFE_VERIFIED`** (bukti di RH-013 `docs/REPAIR_HISTORY.md`):
- Gate aktif di Body CI sejak PR #283 (`main` `59cb42d5`).
- Commit negatif sengaja `ab548622` membuat CI merah di `KAT-CG-01` (`KAT-ERR-90d3601c JSON_INVALID config/ci_negative_proof.json:4`), suite tidak dijalankan, dan job `KAT-CG-04` ikut merah. Setelah revert, CI hijau di Body/Ubuntu/Windows.
- PR #284, #285, #286 juga melewati gate ini.
- Branch protection tidak mewajibkan approval review (0). Gate tidak mengklaim review manusia.

## Gate

| Gate | Isi (alat existing yang dipakai) | Status gagal |
|---|---|---|
| `KAT-CG-00` | HEAD, branch, diff terhadap `origin/main`, path unmerged, penanda konflik, daftar file kontrak yang berubah | `BLOCKED_BASELINE` |
| `KAT-CG-01` | AST semua Python terlacak, JSON valid (file:line), `audit_dependency_links.py` (import, JSON, link, include MQL5, website), `audit_repo_hygiene.py` (junk/`.env`/artefak terindeks/sumber kosong; isi rahasia tidak pernah dibaca) | `FAIL_SYNTAX_OR_DEPENDENCY` |
| `KAT-CG-02` | `unittest discover` unit/static/integration (di CI: langkah regression yang sudah ada, tidak dijalankan dua kali) | `FAIL_TEST` |
| `KAT-CG-03` | `promotion_gate.py --check`, `audit_constitution_guard.py`, `release_manifest.py` harus `MATCH`. Gate tidak pernah meregenerasi manifest atau lock | `FAIL_SAFETY_OR_MANIFEST` |
| `KAT-CG-04` | Check run `body`, `Portable brain (ubuntu-latest)`, `Portable brain (windows-latest)` = success pada SHA. Di CI: job agregat `KAT-CG-04 CI gate` (`needs: [body, portable-host]`) | `BLOCKED_CI_OR_REVIEW` |
| `KAT-CG-05` | Rilis saja: receipt operator (`target_sha` = SHA, backup `integrity ok`, rollback, referensi izin Owner, smoke 0 order dan LIVE off) + ulang CG-03/04. Tidak menghubungi VPS | `BLOCKED_DEPLOY` |

Fail-fast: gate berikutnya tidak berjalan bila gate sebelumnya gagal (`not_run` di laporan).
Exit code: `0` PASS, `1` FAIL, `2` BLOCKED, `3` `REPEATED_FAILURE_NEEDS_ROOT_CAUSE`.
Review manusia tetap diatur branch protection GitHub; gate tidak bisa dan tidak boleh menggantikan atau mengklaimnya.

## Cara menjalankan

```bash
python scripts/governance/code_change_gate.py --quick              # sebelum commit: CG-00 + CG-01 + cleanup --check
python scripts/governance/code_change_gate.py --full               # CG-00..03 lokal
python scripts/governance/code_change_gate.py --gate KAT-CG-04 --sha <SHA>   # sebelum merge (gh atau GITHUB_TOKEN)
python scripts/governance/code_change_gate.py --gate KAT-CG-05 --sha <SHA> --deploy-receipt receipt.json
git config core.hooksPath ops/git-hooks                           # opsional: pre-commit menjalankan --quick
```

Laporan: `build/code-gate/code-change-gate.json` (tidak dilacak Git). Di CI laporan diunggah sebagai artefak `katarina-body-gate-*`.

## Error → reason → tes → perbaikan (anti-loop)

Setiap temuan punya fingerprint stabil `sha256(gate|reason|file|line|test)`, `error_id` `KAT-ERR-xxxxxxxx`, severity P0/P1/P2
(aturan area yang sama dengan `REASON_CODE_INDEX.md`) dan entri di `build/code-gate/failure-ledger.json`:

1. Gagal pertama → `DETECTED` (HEAD dicatat).
2. Fingerprint yang sama gagal lagi pada **HEAD lain** (sudah ada satu upaya perbaikan) → `REPEATED_FAILURE_NEEDS_ROOT_CAUSE`. Gate berhenti (exit 3) dan menolak berjalan lagi sampai akar masalah dicatat:
   `python scripts/governance/code_change_gate.py --record-root-cause <FP> --cause "<akar masalah>" --test <tes reproduksi>` → `ROOT_CAUSE_IDENTIFIED`.
3. Fingerprint hilang pada gate yang dijalankan → `VERIFIED` dengan `fix_commit` = HEAD. Jika muncul lagi sesudahnya → langsung `REPEATED_FAILURE_NEEDS_ROOT_CAUSE`.

Tidak diizinkan: menghapus/men-skip tes, mengubah ekspektasi, menaikkan timeout tanpa analisis, meregenerasi manifest atau lock untuk membuat hijau.
Bukti broker/Windows/Owner yang tidak ada → `BLOCKED_EVIDENCE` (`CI_STATUS_UNAVAILABLE`, `DEPLOY_RECEIPT_MISSING`), bukan bypass.
Ledger CI bersifat per-run. Deteksi perulangan bekerja pada ledger lokal developer/agent, tempat loop perbaikan terjadi.

## Safe cleanup

```bash
python scripts/governance/safe_cleanup.py --check       # default, sama dengan --dry-run: tidak mengubah apa pun
python scripts/governance/safe_cleanup.py --apply-safe  # hanya di worktree development, bukan main/produksi
```

- **Boleh dihapus** (`--apply-safe`): `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.hypothesis`, `*.pyc`/`*.pyo`, file editor (`*~`, `*.swp`), dan folder laporan regenerable `build/validation|body|stage10|governance|discovery`. Syaratnya: tidak dilacak Git, berada di dalam worktree, dan tanpa symlink/junction/reparse point di jalurnya.
- **Selalu ditolak**:
  - lokasi `state`, `backups`, `private`, `logs`, `broker-ticks`, `.git`, `.katarina-envs`, `docs/governance`;
  - file SQLite/WAL/SHM/DB/`.csv.gz`/`.jsonl`, termasuk yang berada di dalam folder allowlist;
  - `build/code-gate`, karena berisi ledger;
  - checkout produksi (`C:\Katarina\code` atau marker `.katarina-production`), branch `main`, dan worktree yang berubah selama proses;
  - folder yang bukan root worktree.
- **Source terlacak tidak pernah dihapus.** Duplikat isi dan modul tak terjangkau hanya dilabeli `DELETE_CANDIDATE`. Item kontrak/identitas (`entrypoints`, `ports`, tombstone `run_market_brain.py`/`run_decision_brain_v3.py`) dilabeli `PROTECTED_KEEP`. Penghapusan source tetap lewat PR dengan bukti `DELETE_CONFIRMED`.
- Idempotent. Setiap apply menambah satu baris ke `build/code-gate/cleanup-audit.jsonl`.

## Bukti acceptance (tes otomatis)

`tests/static/test_code_change_gate.py` membangun repo fixture terisolasi dari berkas terlacak dan memeriksa skenario berikut:
- Python rusak dan JSON invalid → CG-01 merah dengan file:line; setelah dipulihkan → hijau.
- Import putus dan include MQL5 putus → merah.
- `.env` terindeks → merah tanpa isi rahasia di laporan.
- Manifest drift dan perubahan `risk.py` → CG-03 merah, sedangkan manifest/berkas tidak diperbaiki otomatis.
- Penanda konflik → `BLOCKED_BASELINE`.
- Satu upaya perbaikan yang gagal → `REPEATED_FAILURE_NEEDS_ROOT_CAUSE` dan STOP, lalu root cause wajib dicatat, lalu `VERIFIED` dengan commit perbaikan.
- CG-04 tanpa bukti atau dengan check gagal → BLOCKED.
- CG-05 tanpa receipt atau dengan receipt cacat → BLOCKED.
- Wiring workflow tanpa `schedule:`.

`tests/static/test_safe_cleanup.py` memeriksa skenario berikut:
- `--check`/`--dry-run` tidak mengubah apa pun.
- `--apply-safe` hanya menghapus allowlist; item terlacak, `state`/`backups`/`private`/`logs`/`docs/governance`, SQLite/WAL, dan arsip tick ditolak.
- Symlink keluar worktree ditolak dan target luar tetap utuh.
- Path escape ditolak.
- `main`, produksi, dan worktree yang berubah ditolak.
- Folder non-root ditolak.
- Duplikat hanya dilaporkan.
- Proses idempotent.
