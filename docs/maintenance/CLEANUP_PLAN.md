# Catatan perapian Katarina AI

Untuk dikerjakan di Claude Code, tahap demi tahap. Basis: `main` setelah PR #143 (21 Oktober 2026).

## Aturan untuk semua tahap

Tempel blok ini di awal setiap sesi Claude Code:

```
Baca CLAUDE.md dulu. Aturan perapian:
- Tanpa perubahan perilaku. Jangan mengubah logika trading, Risk Governor
  (src/katarina/engines/risk.py), config risk, EA MT5, atau flag live_execution.
- Satu tahap = satu branch = satu PR kecil. Body CI wajib hijau sebelum merge.
- Pindahkan ke archive/ (lokasi asal dipertahankan), jangan langsung dihapus.
- Config di config/ dan config/stages/ dimuat lewat nama dinamis, jadi jangan
  dihapus hanya karena tidak ditemukan lewat grep.
- Sebelum memindah file, cek rujukannya di src/, scripts/, tests/,
  .github/workflows/, docs/, config/, dan ops/deployment/release-manifest.json.
- Perbarui CLAUDE.md dan CHANGELOG.md di setiap PR.
```

Kerjakan sesuai urutan di bawah. Tahap 1 menjadi dasar untuk tahap lainnya.

## Tahap 1 — Peta modul yang benar-benar dipakai (read-only, tanpa ubah kode)

```
Buat scripts/governance/runtime_import_map.py yang menelusuri import secara
statis mulai dari entry point runtime: scripts/ai/run_contextual_market_observer.py,
katarina_pc.py, worker demo, publisher monitor, dan script yang dipanggil oleh
.github/workflows/*.yml. Hasilkan docs/maintenance/RUNTIME_MODULE_MAP.md yang
mengelompokkan setiap modul di src/katarina/ menjadi:
(A) dipakai runtime, (B) hanya dipakai tests, (C) hanya dipakai script riset,
(D) tidak dirujuk sama sekali. Jangan memindah file apa pun di tahap ini.
```

Hasil cek awal saya: otak versi lama ternyata masih di-import. Contohnya,
`multi_market_brain` dirujuk 4 modul src dan `adaptive_brain_v2` dirujuk 3 modul src.
Jadi otak lama tidak bisa langsung diarsipkan. Peta dari tahap ini akan menunjukkan
mana yang aman.

## Tahap 2 — Pensiunkan otak lama di `intelligence/`

```
Berdasarkan RUNTIME_MODULE_MAP.md, untuk brain.py, adaptive_brain_v2.py,
market_decision_brain_v3.py, multi_market_brain.py, dan brain_observer.py:
jika masih dipakai runtime, pindahkan bagian yang dipakai ke modul canonical
(unified_brain.py atau modul kemampuannya) dengan perilaku identik, lalu
arahkan import ke sana. Modul yang hanya dipakai tests ikut diarsipkan bersama
tests-nya. Kerjakan satu modul per PR.
```

Target hasil: hanya `unified_brain.py` yang tersisa sebagai pintu masuk otak.

## Tahap 3 — Kelompokkan `intelligence/` (106 file) ke subfolder

```
Kelompokkan file di src/katarina/intelligence/ ke subpaket menurut fungsi,
misalnya market/, research/, demo/, news/, broker/, memory/. Sediakan shim
import sementara di lokasi lama (re-export plus DeprecationWarning) supaya
tidak ada yang rusak. Hapus shim di PR terpisah setelah semua import diganti.
```

## Tahap 4 — Ganti nama `body/stageNN` dan workflow `stageNN`

```
Buat tabel stageNN -> nama fungsi (contoh: stage07 -> transport,
stage08 -> validation, stage09 -> health_safety) dari docs/reviews dan
config/stages. Ganti nama modul body/stageNN.py sesuai fungsinya, dengan alias
lama tetap ada selama satu rilis. config/stages/stageNN.json jangan diganti
nama dulu karena dimuat berdasarkan nomor; cukup catat pemetaannya.
```

## Tahap 5 — Sederhanakan 39 workflow CI

```
Gabungkan 12 workflow stage07-* menjadi satu workflow dengan matrix job, serta
stage06-* dan stage08/09/35 ke dalam katarina-body-ci.yml jika pemicunya sama.
Pertahankan nama check yang diwajibkan branch protection (cek dulu daftarnya di
Settings > Branches) agar main tidak terkunci. Workflow riset lama (v9, v10,
tournament, replay) yang tidak dipicu 30 hari terakhir dipindah ke
archive/workflows/ (tanpa nama .yml aktif).
```

Hati-hati: mengganti nama check yang diwajibkan branch protection bisa membuat PR tidak bisa di-merge.

## Tahap 6 — Pindahkan logika dari `scripts/` ke `src/`

```
Untuk script di scripts/ai/ dan scripts/research/ yang berisi logika lebih dari
sekitar 150 baris, pindahkan logikanya ke src/katarina/... dan jadikan script itu
CLI tipis yang hanya membaca argumen lalu memanggil fungsi di src. Script riset
yang hasilnya sudah tercatat jangan diubah logikanya, cukup diarsipkan jika
sudah tidak dipakai.
```

## Tahap 7 — Pisahkan website ke repo sendiri

Panduannya sudah ada di `docs/deployment/STANDALONE_WEBSITE_EXTRACTION.md`. Tahap ini dikerjakan paling akhir karena menyentuh Cloudflare Pages dan workflow yang menulis JSON ke `website/`.

```
Ikuti docs/deployment/STANDALONE_WEBSITE_EXTRACTION.md. Buat repo baru untuk
website/, sites/, functions/, dan oauth_gateway/. Workflow publisher di repo
ini hanya mengirim JSON ke repo website (atau ke storage), tidak lagi commit ke
website/ di sini. Domain Cloudflare dipindah setelah repo baru terbukti deploy.
```

## Tahap 8 — Satu sumber status

```
Gabungkan README (bagian status), docs/PROJECT_STATUS.md, dan
docs/CURRENT_PROJECT_HANDOFF.md: README cukup ringkas dan menautkan ke satu file
status. Arsipkan dokumen bertanggal yang sudah digantikan.
```

## Setelah perapian

Arahkan tenaga ke hal yang menentukan apakah bot bisa trading otomatis: bukti edge.
Artinya hasil riset ulang setelah perbaikan spread, uji out-of-sample, dan hasil demo
forward yang cukup lama dan konsisten. Hasil demo itu sekarang sudah tampil di website.
