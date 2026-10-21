# Arsip branch 22 Oktober 2026

Branch di bawah sudah tidak membawa perubahan yang belum ada di `main` (diperiksa per berkas: identik, sudah pindah ke subpaket baru, atau sengaja dihapus). Dicatat di sini sebelum dihapus supaya bisa dipulihkan kapan saja.

| Branch | Commit terakhir | Alasan |
|---|---|---|
| `ccr-1758c3cd-9g5dcd` | `a9e4f6d3b5695f5126a9fa520d2eeca8c4d0c666` | Sudah tergabung penuh (leluhur main, PR #152). |
| `chore/tidy-repository` | `42d0353e15f3fa3ba8c4dc880b3e080981510773` | Isinya masuk lewat PR #139 (commit pertama "Tidy repository"). |
| `claude/vps-access-handoff-20261021` | `7078ac94ee83cb535f439aac63290402aac0e848` | Panduan akses VPS lewat SSH; digantikan Desktop Commander OAuth (lihat branch `claude-vps-bridge`). |
| `feat/continuous-all-market-research-20261020` | `be51cabbc967172ef0c7faa3a6b3273a58ed3e16` | Semua fitur (WAL storage, network doctor, multi-symbol demo routing, dashboard MT5) sudah ada di main di lokasi subpaket baru; sisanya hanya `memory/*.jsonl` runtime state yang tidak boleh di-commit. |
| `policy/owner-ms-sd-elliott-risk-20261021` | `d53caddacdf41059e4c5ee83c47d84e56b08e9a8` | Berkas `docs/governance/OWNER_STRATEGY_AND_RISK_SELECTION_20261021.json` identik di main (PR #139). |
| `research/ms-sd-elliott-evidence-v1-20261021` | `e685154df55ef16a2a2827efcdbf09f447b8622c` | Masuk lewat PR #139; `owner_structure_candidate.py` lalu sengaja dihapus di commit 8f982c6 (modul hanya dipakai test). |
| `research/v26-corrected-selection-guard-20261019` | `6c50ed5f7b9a1d46f0026a30605148233db592a5` | Ketiga berkas identik di main. |

Branch yang dipertahankan: `main`, dan `claude-vps-bridge` (kanal pesan GitHub↔VPS yang di-poll tugas `ClaudeGitHubBridgePoll`; isinya pesan ping, bukan kode untuk `main`).

## Memulihkan branch

```bash
git fetch origin <commit>
git push origin <commit>:refs/heads/<nama-branch>
```

GitHub tidak menjamin commit tanpa branch atau tag disimpan selamanya; untuk arsip permanen buat tag `archive/branch/<nama>` dari commit di atas.
