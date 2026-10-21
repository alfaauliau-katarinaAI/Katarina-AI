# Status perkembangan Katarina AI

Diperbarui: **16 Oktober 2026**. Snapshot sumber setelah penghapusan Management
serta penyatuan satu otak canonical. Lihat commit `main` dan Actions untuk SHA
perubahan yang diuji; status ini tidak mengklaim deployment VPS telah sinkron.

| Bagian | Hasil terverifikasi | Batas |
|---|---|---|
| Branch | Hanya `main`; 42 branch awal selain main sudah terhapus | Branch kerja sementara boleh muncul untuk PR berikutnya |
| Integrasi | 34 branch terverifikasi setara/identik; delapan direview dan diselesaikan | Varian eksekusi eksperimen tetap terpisah dari engine produksi |
| Pengujian | 1.274 unit, 113 static (4 skipped), 132 integration lulus | Tidak membuktikan kesiapan live atau profitabilitas |
| Otak unified | 1 otak dengan 17 modul canonical; persepsi, kognisi dan Neuro-Link berbagi runtime | Memori privat dan proses VPS belum diperiksa |
| Trading | Engine produksi, Risk Governor, konfigurasi risk dan MT5 tidak berubah | Live execution false; 0 order pada verifikasi offline |
| Keamanan | Main wajib PR/body CI, up-to-date dan conversation resolution; admin tunduk aturan | Bukan audit penetrasi menyeluruh |
| Akses | Tidak ada kolaborator tambahan; token Actions read-only secara default | CLI perangkat luar Work belum dipasang/diuji |

## Jalur sesuai diagram patokan — 16 Oktober

Seluruh lifecycle observer dipindah ke `UnifiedKatarinaBrain`: satu lock/koneksi,
satu pemilik context/memori/journal/shadow, urutan settle → learn → propose,
monitoring/foundation dan publikasi. Script observer kini hanya CLI delegasi.
Dua entry point observer legacy ditutup agar perintah lama tidak membuat jalur
paralel. Helper MT5 berada pada adapter eksternal yang diinjeksi.

Modal/Profit Lock dan recovery offline memakai engine lama di bawah control
internal. Checkpoint tidak memigrasi state broker atau mereset reserve. Gerbang
pengiriman menerima penilaian Risk Governor independen tetapi tetap LIVE OFF:
tidak ada callback kirim, antrean retry atau sakelar enable. Uji broker sintetis
menjangkau sensor/persepsi nyata dalam kode, cleanup, restart, sensor gagal,
perubahan izin trading dan checkpoint tampering.

[Diagram patokan dan batas kelulusan](architecture/KATARINA_SINGLE_BRAIN_WORKFLOW_20261016.md).
Perapian jalur source selesai setelah CI, sedangkan sinkronisasi VPS, Cloud auth
serta pembuktian broker/strategi tetap terpisah dan belum dinyatakan selesai.

## Satu otak canonical; Management dihapus

- Tiga workflow Management/team, enam script, workplan dan roadmap spesialis
  dihapus; hook pemanggilnya di Body CI juga dihapus. Sejarah tersedia di Git.
- `UnifiedKatarinaBrain` menjadi satu pintu masuk observer. Persepsi pasar,
  pembelajaran kognitif, recall Neuro-Link dan sintesis riset entry/exit merupakan
  kemampuan di instance yang sama, tanpa worker atau scheduler kedua.
- Fast/Deep menggunakan MemoryStore dan checkpoint yang sama. Pembacaan causal
  mempertahankan waktu pertama informasi tersedia, checksum, provenance dan
  penolakan duplikasi/tampering. Outcome quote hanya OBSERVED, bukan profit broker.
- Rollback Owner dan knowledge window yang terpotong menahan sampling virtual.
  Parameter D1–D6 yang masih membutuhkan validasi tidak diisi sembarangan.
- Cloud Hands, autentikasi Owner, validasi broker dan VPS tetap belum selesai.
  Rekayasa satu otak bukan klaim seluruh grand desain sudah siap produksi.

Diagram dan kontrak ada di [arsitektur unified](architecture/KATARINA_UNIFIED_V1_SYNC.md).

## Integrasi branch sebelumnya

[PR #85](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/85)
menyatukan riwayat 34 branch setelah verifikasi patch-id atau blob file identik.
[PR #86](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/86)
mengintegrasikan Neuro-Link, shadow paper/replay dan penelitian portfolio offline.
Pembacaan memori tetap memeriksa checksum dan menolak payload yang berubah.

Perubahan lama yang sudah ditingkatkan dipertahankan dalam bentuk main terbaru.
Ekstraksi website tidak diterapkan sebagai penghapusan 799 file AI: instruksinya
masuk ke `docs/deployment/STANDALONE_WEBSITE_EXTRACTION.md`.
Varian portfolio historis berada di
`src/katarina/research/experimental_strategy_evidence_portfolio.py`, tanpa
registrasi runtime atau perubahan strategi produksi.

Bukti per branch: [34 branch setara](operations/BRANCH_CONSOLIDATION_20261015.json),
[delapan resolusi unik](operations/BRANCH_UNIQUE_INTEGRATION_20261015.json),
dan [receipt cleanup](operations/BRANCH_CLEANUP_RESULTS_20261015.json).
Seluruh head awal tersimpan sebagai ancestor main; tidak ada force push.

## Bukti CI dan cleanup

- [Body CI PR #85](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38762804497).
- [Body CI PR #86](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38763776156).
- [Body CI main integrasi](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38764010009).

- [Cleanup execute 1](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38763507369): 10 branch dihapus; 33 total branch tersisa.
- [Cleanup execute 2](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38764266063): 10 branch dihapus; 23 total branch tersisa.
- [Cleanup execute 3](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38764494806): 10 branch dihapus; 13 total branch tersisa.
- [Cleanup execute 4](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38764768540): 10 branch dihapus; 3 total branch tersisa.
- [Cleanup execute 5](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38764950294): 2 branch dihapus; 1 total branch tersisa.
- [Dry-run penutup](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38765089798): 0 kandidat, 0 penghapusan.

Setiap eksekusi mengecek ulang SHA branch, strict ancestry, protection dan PR aktif.
Daftar branch dicocokkan setelah setiap batch. Main dipertahankan karena default
branch dilindungi. Seluruh 42 kandidat awal telah diselesaikan; tidak ada branch
unik yang ditinggalkan atau dihapus sebelum integrasi dan CI.

## Prioritas berikutnya

Instruksi Owner 16 Oktober: tunda pembuktian strategi sampai seluruh sistem
terbentuk. Pekerjaan saat ini hanya integrasi teknis. [Permukaan status Owner
tanpa model](operations/OWNER_STATUS_SURFACE.md) memakai observer yang sama;
endpoint model nyata dan TLS HP tetap gerbang konfigurasi eksternal.

Alat persiapan pengujian dialog dan konfigurasi Owner tersedia pada
[daftar gerbang pretrial](operations/PRETRIAL_REMAINING_GATES.md). Mode persiapan
tidak memanggil provider; kualitas model nyata dan TLS HP tetap belum terverifikasi.

Pembaruan bukti host 16 Oktober sekitar 18.19 WIB: checkout aplikasi cocok dengan
`6392646`; observer/MT5 aktif, snapshot 399/399 siklus dan 3 instrumen, live OFF.
Tiga ACK WAIT terlihat pada pembacaan berikutnya. Ini belum mengaudit memori atau
fingerprint modul yang sudah dimuat. Lihat [batas bukti dan pemeriksa runtime
baca-saja](operations/READONLY_RUNTIME_EVIDENCE.md); bagian snapshot awal di atas
dipertahankan sebagai riwayat, bukan klaim bahwa host belum pernah diperiksa.

1. Verifikasi checkout, fingerprint modul, lokasi memori dan proses VPS secara
   read-only sebelum menyatakan otak yang berjalan di VPS sinkron.
2. Autentikasi CLI pada perangkat kerja tujuan bila dibutuhkan, sesuai
   [panduan akses](operations/GITHUB_ACCESS.md).
3. Evaluasi bukti broker prospektif secara terpisah; repository rapi dan CI hijau
   tidak mengaktifkan live trading.

Gunakan [CHANGELOG](../CHANGELOG.md) dan commit SHA untuk menelusuri perubahan.

## Portabilitas host — 16 Oktober 2026

Otak dapat menjalankan satu siklus riset lokal tanpa VPS/MT5 melalui
`run_contextual_market_observer.py --offline-research`. `--doctor` memeriksa host;
lokasi state mengikuti konfigurasi/OS, anggaran observasi mengikuti kapasitas.
Lihat [panduan host portabel](architecture/KATARINA_PORTABLE_HOST.md). Tidak ada migrasi state legacy otomatis,
Cloud Hands lintas host belum terverifikasi, live tetap OFF.

## Koneksi otomatis baca-saja — 16 Oktober 2026

Launcher memilih local/cloud/offline menurut konfigurasi akun yang diizinkan.
Retry terbatas mengulang seluruh pass; tanpa koneksi valid tetap riset lokal.
Sensor HTTPS baru memerlukan pemasangan dan kredensial sekali; belum diuji pada
MT5/cloud nyata. Lihat [kontrak koneksi otomatis](architecture/KATARINA_AUTOMATIC_CONNECTION.md). Risk Governor independen, live OFF.

## Paket uji PC — 16 Oktober 2026

Peluncur utama START_KATARINA sekarang menjalankan acceptance sintetis sekali,
bukan supervisor VPS background. SETUP_KATARINA membuat environment privat.
Laporan HTML/JSON lokal memisahkan hasil demo dari observasi broker dan tidak
menganggap fallback offline sebagai kelulusan broker. Lihat [panduan PC](QUICKSTART_PC.md).
Paket source-only bermanifest commit disediakan artifact CI; live OFF.

## Pemulihan environment privat — 16 Oktober 2026

Startup memeriksa dependensi dan menguji kandidat pengganti sebelum memilihnya.
Environment lama, strategi, Risk Governor dan memori tetap dipertahankan; tidak
ada perubahan source atau izin trading. Panduan: [pemulihan environment](architecture/KATARINA_ENVIRONMENT_RECOVERY.md). Live OFF.

## AI trading pretrial extension — 16 October

Dialog, heuristic Fast/Deep model routing and bounded read tools now run through
UnifiedKatarinaBrain with the existing memory and single host lock. The explicit
Owner console/browser surface supports a configured model; no model or API token
is bundled. Owner browser access uses bearer authentication and requires TLS for
non-loopback binding. This is not a native Android application.

MT5 local/cloud sensor adapters accept nonexecuting WAIT feedback and return
identity-bound acknowledgements. The observer records receipts. This is a
bidirectional adapter path, not a live order gateway or verified broker execution.
Risk Governor, trading strategy and MT5 source remain unchanged; delivery is OFF.

The portable `pretrial` command distinguishes synthetic checks from missing real
model, destination host, MT5 and demo broker evidence. See
[pretrial contract and instructions](architecture/KATARINA_AI_TRADING_PRETRIAL.md).

### GitHub CI evidence for pretrial

[PR #94](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/94) and
[Actions run 38811219852](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38811219852)
verify the published implementation: Body CI plus Linux, Windows and macOS
installation, extracted-package acceptance, pretrial and environment recovery all
passed. These are synthetic/protocol checks, not real-model quality or broker
execution clearance. The validation JSON records the exact tested commit.

The main-only workflow-catalog maintenance job checks that its source SHA still
matches remote main before disabling an orphaned YAML registration. It preserves
source-backed and GitHub dynamic workflows, Actions runs and artifacts. Four
additional unit tests verify scope, dry-run and revision-race behavior.
