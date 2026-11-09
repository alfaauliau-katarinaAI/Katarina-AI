# D9 — jadwal per simbol: implementasi pratinjau, belum aktif

Baseline sumber: `8942e984b6d6b312ebf95a972f8ac7cb52215e5e`.
Branch pengembangan: `codex/d9-symbol-session-preview-20261109`.
Owner menyetujui implementasi per simbol pada branch terisolasi di chat, lalu
commit, push dan Draft PR untuk CI/review. Aktivasi, tanggal efektif, merge dan
deployment belum diberikan.

## Bukti broker yang berhasil diperoleh

Pada 9 November 2026 15:59:16–15:59:19 UTC, GUI **Symbols → Specification**
MT5 yang sudah berjalan di `WIN-4TTT19K3CL8`, sesi Windows 2, PID 6964 dibaca.
Kolom list-view 0/1/3 memuat nama hari / Quotes / Trade. Identitas ketujuh
simbol cocok. Tidak menjalankan terminal kedua, probe MQL, restart atau order.
Dialog baca-saja ditutup setelah pengambilan. Source tidak diubah di VPS.

| Simbol `.vx` | Quote Senin–Jumat, waktu broker | Trade Senin–Jumat, waktu broker |
|---|---|---|
| XAUUSD, JPN225 | 01:00–23:55 | 01:05–23:55 |
| NAS100, US30 | 01:00–24:00 | 01:05–24:00 |
| EURUSD, GBPUSD, USDJPY | 00:00–23:55 | 00:05–23:55 |

Baris Sabtu/Minggu kosong: **tidak otomatis dianggap bukti sesi tutup**.
Contoh konfigurasi menyimpan hari itu sebagai `null`, bukan daftar kosong.

Artefak privat di `C:\Windows\Temp\` (bukan file repo):

| Artefak | SHA-256 byte file |
|---|---|
| `katarina-d9-broker-sessions-20261109.json` | `92ee7ad9969d4692d8c6f35eb052995d04a679bf881626ffd209197f4193f049` |
| `katarina-d9-broker-session-context-20261109.json` | `e28806082b9a0d3dfd91ceedd46d456d16d67fabd941e41819e53c04a4df039b` |

Artefak tersebut berada di direktori sementara; untuk retensi audit diperlukan
salinan ke penyimpanan bukti privat sebelum pembersihan Windows. Hash saja
tidak menggantikan file sumber. Log akun, heartbeat dan data tick tidak disalin
ke repository. Contoh JSON hanya transkripsi jadwal terpilih dan referensi hash.

Konteks 16:00:21 UTC mencocokkan server pada judul terminal
`ValetaxIntl-Live2` dengan hash server observer:
`dacabd748ea8f1b2394491a79990cde783e49bbcea518832934030cb00ad3c95`.
Snapshot observer 15:59:31.757775 UTC melaporkan offset **+2 jam**,
`LIVE_FEED_CLOCK_VERIFIED`, 3 confirming symbols, `NTP_SYNCHRONIZED`,
`historical_dst_verified=false`, `production_execution=false`, dan 0 order.
Ini bukti titik waktu, bukan sertifikasi offset untuk rentang tanggal.
0 order pada snapshot bukan audit order broker independen.

Dengan offset +2 yang diamati, sesi quote XAU membuka 23:00 UTC hari sebelumnya
dan menutup 21:55 UTC; NAS menutup 22:00 UTC; FX membuka 22:00 UTC hari sebelumnya.
NAS yang tidak berquote sekitar 21:57 UTC dalam peta empiris masih berada dalam
jadwal quote yang sekarang dibaca. **Jangan mengecualikannya sebagai tutup resmi.**
Perbedaan dapat berasal dari kondisi feed atau perubahan jadwal; sebabnya belum
terverifikasi. Jadwal sekarang tidak membuktikan sesi historis 2–6 November.

## Masalah dan perubahan sumber

| Prioritas | Akar masalah / bukti baseline | Koreksi yang disiapkan | Acceptance / blocker |
|---|---|---|---|
| P1 | `observation_ledger.py:366–397` memakai jendela global D8, sementara sesi quote simbol berbeda | `broker_sessions.BrokerSessions` memisahkan simbol, quote/trade, tanggal broker dan `[start,end)` | Uji pembukaan FX saat CFD tutup; belum mengganti assessor resmi |
| P1 | `stage0_breakdown.py:24–50` memberi label DAILY_BREAK dari jendela −15/+60, bukan sesi resmi | Pratinjau membaca quote per simbol, tidak menyamakan label waktu dengan alasan pasar tutup | Quote NAS yang hilang saat resmi open tetap dilaporkan gagal |
| P1 | Bukti offset/sesi hanya titik waktu; DST/hari libur belum diketahui | Tidak menebak offset dari kalender AS/EU; bukti clock berupa rentang UTC eksplisit, tanggal broker harus diverifikasi | Missing/expired/mismatched evidence → UNVERIFIED; tidak memperkecil denominator resmi |
| P1 | PARTIAL/FAILED tidak sama dengan kegagalan quote terjadwal | Quote readiness terpisah dari kegagalan sistem; clock/koneksi tetap terlihat | FAILED, NO_MARKET_DATA, order nonzero dan PARTIAL selain missing-quote tetap SYSTEM_FAILURE_RETAINED |

Kode memakai stdlib dan tidak menghubungi MT5. Tidak ada jalur aktivasi di CLI.
`data_health.assess`, `stage0_session_open`, cutoff, threshold, denominator resmi,
promotion lock dan Risk Governor tidak berubah. Tidak ada persentase PASS baru.
Ini **implementasi evaluator dan pratinjau**, bukan integrasi produksi ke seluruh
sembilan kriteria Stage 0 atau penjadwal observer. Integrasi resmi itu perlu
review kontrak metrik dan izin aktivasi tersendiri.

## Format bukti dan cara memakai pratinjau

Contoh yang sengaja belum dapat mengecualikan satu tanggal pun:

- `config/broker_sessions.d9.example.json`: jadwal quote/trade dalam detik sejak
  tengah malam broker, weekday 0=Senin sampai 6=Minggu. Contoh 01:00=3600,
  23:55=86100, 24:00=86400. `null`/weekday tidak ada = unavailable.
  `[]` hanya boleh menyatakan tutup bila memang ada bukti dan tanggalnya diperiksa.
- `valid_from_utc` dan `valid_until_utc` adalah batas keberlakuan jadwal `[from,until)`
  yang disokong sumber, tidak boleh lebih awal dari capture; saat ini keduanya
  `null`. `verified_broker_dates` kosong: belum ada pemeriksaan exceptions/hari libur.
- `config/broker_session_clock.d9.example.json`: `intervals` masih kosong.
  Tiap interval sah memerlukan `start_utc`, `end_utc`, `offset_seconds`,
  `reason="LIVE_FEED_CLOCK_VERIFIED"`, dan `evidence_sha256`.
  Interval harus tidak tumpang tindih dan hash server harus cocok.
  Di tiap siklus offset ledger juga harus cocok. Rentang tidak boleh diisi
  hanya dengan memperpanjang satu observasi clock. Pergantian DST memerlukan
  rentang bukti baru; tidak ada fallback `is_us_dst`/`is_eu_dst`.
- Untuk sesi melewati tengah malam, `end` dapat lebih dari 86400; misalnya
  `[82800,90000]` = 23:00 sampai 01:00 hari berikutnya. Bukti tanggal awal
  sesi juga wajib tersedia. Interval salah/overlap ditolak.

Pada salinan state lokal untuk audit, setelah bukti privat benar-benar disiapkan:

```bash
python scripts/ai/preview_broker_sessions.py --state-dir PATH_TO_AUDIT_STATE --schedule PATH_TO_SCOPED_SCHEDULE --clock-proof PATH_TO_CLOCK_PROOF --since official --output build/validation/d9-preview.json
```

CLI membuka SQLite `mode=ro`, `PRAGMA query_only=ON`, satu read transaction.
Output tidak boleh menimpa database, sidecar SQLite, bukti input atau hardlink-nya.
`--since official` tetap cutoff `2026-11-03T15:18:14+00:00`.
Contoh repo menghasilkan UNVERIFIED; tidak dibuat valid dengan jam fiktif.
Server provenance input harus berasal dari broker yang sama dengan ledger;
schema ledger lama belum mengikat hash server per siklus. Karena itu pratinjau
tidak boleh dipromosikan menjadi verdict resmi hanya berdasarkan file input ini.

Kategori keluaran: `QUOTE_READY_ONLY`, `MISSING_OPEN_QUOTES`,
`NO_QUOTES_EXPECTED`, `UNVERIFIED`, `SYSTEM_FAILURE_RETAINED`.
Semua simbol wajib dari `config/observer_universe.json` diperiksa, termasuk bila
jadwal atau baris quote hilang. CLI tidak menerima override universe dari argv.
Schedule yang menghapus/menambah simbol menghasilkan `D9_UNIVERSE_MISMATCH`,
readiness UNVERIFIED dan exit 2; keluaran menyimpan hash file universe serta
daftar simbol wajib, deklarasi, yang hilang dan yang tidak dikenal.
API `preview` mewajibkan argumen `required_symbols` terpisah dari schedule.
Output juga tidak boleh menimpa konfigurasi universe atau hardlink-nya.
Quote OK harus unik, finite, bid>0, ask>=bid, tick tidak dari masa depan,
dan umur <=90 detik (horizon default pembaca quote canonical).
`QUOTE_READY_ONLY` tidak membuktikan clock/tick/reconciliation/reconnect/0-order
atau kelulusan Stage 0. Tidak ada fallback ke pengabaian simbol yang hilang.

## Koreksi review berikutnya — belum aktif

- Output `--output` dibatasi ke file **baru** dalam `build/validation/`;
  lokasi di luar root validasi, symlink root, dan target yang sudah ada ditolak.
  Setelah revisi Owner, CLI menulis ke file sementara `.d9-preview-*.tmp`,
  flush+fsync, lalu memublikasikan nama JSON secara eksklusif melalui
  `os.link` (tidak melakukan overwrite). Jika penulisan/publikasi gagal,
  nama JSON final tidak dibuat oleh proses ini dan file sementara dibersihkan.
- Untuk pengujian, direktori validasi diganti dengan direktori sementara.
- Jadwal overnight dari hari sebelumnya yang tervalidasi tetap diklasifikasi
  OPEN meskipun jadwal hari berikutnya belum tersedia. Tanpa bukti tetap
  UNVERIFIED, tidak dianggap CLOSED.
- Aturan resmi D8, cutoff, denominator, sumber data, Risk Governor dan LIVE
  tidak diubah. CI pada commit terbaru harus dijalankan ulang sebelum review.

## Verifikasi dan batas serah-terima

Tes synthetic-only mencakup batas detik/mikrodetik, perbedaan trade lima menit,
24:00, buka mingguan pada tanggal UTC sebelumnya, overnight, simbol/hari hilang,
validitas dan hash server, bukti clock kosong/overlap/mismatch, perubahan offset
pada batas DST AS/EU yang berbeda, hari libur tanpa bukti, quote hilang/duplikat/
future tick, koneksi/clock gagal, dan batas cutoff/as-of.
Tes CLI membandingkan report resmi pada waktu yang sama dan hash file input
sebelum/sesudah pratinjau. Lulus tes ini hanya bukti mekanisme sintetis.

### Perbaikan fixture Windows setelah CI pertama

CI pada `fb4ebd16dcc0a9bee83a41c469df924371ffd644`, run
`42654446484`: Body dan Ubuntu PASS; Windows gagal dengan empat error
`WinError 32` saat membersihkan file database fixture. Ini bukan kegagalan
assertion sesi broker. Akar masalah di `test_broker_session_preview.py:setUp`:
context manager `sqlite3.Connection` menyelesaikan transaksi, tidak menutup
connection. GC koneksi tidak deterministik; Windows melarang unlink file terbuka.

Fixture kini memakai `contextlib.closing(...)` bersama context transaksi.
Tes tambahan menahan referensi kuat pada koneksi dan memastikan `execute`
ditolak setelah setup selesai. Dengan kode fixture sebelum perbaikan, tes itu
gagal deterministik di Linux (`ProgrammingError not raised`); dengan penutupan
eksplisit, tes lulus. Tidak ada skip baru, retry cleanup atau pelonggaran assertion.
CLI produksi sudah menutup koneksi eksplisit pada `finally` dan tidak diubah.

Hasil lokal sebelumnya pada implementasi awal (Python 3.12.14 / NumPy 2.3.5):

| Pemeriksaan | Hasil |
|---|---|
| 20 tes baru + regresi terarah D8/cutoff/breakdown | 35/35 OK |
| Unit lengkap | 1.512 dijalankan, OK, 1 skip |
| Statis lengkap | 98 dijalankan, OK, 4 skip |
| Integrasi lengkap sesudah perbaikan fixture | 229 dijalankan, OK, 0 skip |
| KAT-CG-00/01/02/03 lokal | PASS |
| Constitution Guard / promotion lock | PASS / PASS |
| Manifest kode | MATCH 317; hanya dua entry source baru ditambahkan |

Laporan lokal: `build/code-gate/d9-full.json` (tidak dilacak Git).
CI hosted pada `affb3e4a2f0ab6c0e889219be48d53aa5fdf1dbc` sudah PASS:
run `42656279595`, Body/Ubuntu/Windows/KAT-CG-04. Review independen,
merge, sertifikasi rentang bukti dan aktivasi belum dipenuhi.
Tahap 0 tetap IN_PROGRESS; LIVE OFF. Tidak ada CLOSED_VERIFIED untuk D9 keseluruhan.

### Audit lanjutan 10 November 2026 — scope universe (P1)

Pada SHA `affb3e4a`, `broker_sessions.py:159` membentuk daftar pemeriksaan
dari `sessions.symbols`, sementara CLI tidak membandingkannya dengan universe
canonical. Reproduksi SQLite in-memory dengan ledger yang sama: EURUSD punya
quote, XAU/NAS tidak punya quote ketika ketiganya dijadwalkan open. Schedule
lengkap → `MISSING_OPEN_QUOTES`; schedule yang menyisakan EURUSD →
`QUOTE_READY_ONLY`. Ini hasil diagnostik keliru, bukan perubahan verdict resmi.

Koreksi: caller memasok daftar simbol wajib terpisah; CLI selalu membacanya dari
konfigurasi universe pada checkout yang sama, menyimpan hash byte file dan
menolak scope berbeda. Simbol wajib tidak boleh hilang dari laporan. Tidak ada
perubahan universe canonical, cutoff, assessor D8, risk atau promotion lock.
Acceptance: schedule lengkap tetap berfungsi; schedule kurang/lebih diblokir;
universe kosong/duplikat/tidak sah ditolak; output tidak menimpa konfigurasi;
laporan resmi dan file ledger tetap sama. Empat tes tambahan beserta regresi
D9/D8 menghasilkan **39/39 OK** lokal. CI/review pada SHA revisi wajib diperiksa
lagi; CI hijau pada `affb3e4a` tidak mengesahkan perubahan baru ini.

## Review final tambahan — penguatan keluaran CLI

- PR #294 pada SHA `e902f07` telah melewati Body, Ubuntu, Windows,
  dan KAT-CG-04 CI. Ini **bukan** bukti Stage 0 lulus atau D9 aktif.
- Pemeriksaan lanjutan menemukan kegagalan I/O saat menyimpan hasil
  `--output` terjadi di luar penanganan error CLI. Pembatasan output
  sebelumnya sudah mencegah overwrite, namun kegagalan izin/path dapat
  menghasilkan traceback. Koreksi sekarang mengembalikan status
  `D9_OUTPUT_WRITE_FAILED` (exit 2) tanpa membocorkan detail path privat.
- Tes negatif menggunakan `PermissionError` sintetis dengan direktori
  temporary dan membuktikan tidak ada file keluaran yang dibuat.
- Kode CLI, tes, dan release manifest diperbarui dalam branch yang sama.
  CI **wajib dievaluasi lagi pada SHA final terbaru**; keberhasilan
  pada `e902f07` tidak mengesahkan commit sesudahnya.
- Blocker terpisah yang **tidak ditutup oleh kode**: sertifikasi validitas
  sesi broker/UTC-DST/libur; bukti 7 simbol pada observer VPS produksi
  (snapshot terdahulu 5 simbol); review independen; izin Owner untuk
  merge dan izin lain untuk deploy/aktivasi.


## Revisi permintaan Owner 10 November 2026 — PR tetap Draft

1. **P1 berkas parsial:** output tidak lagi ditulis langsung pada target `.json`.
   Kegagalan I/O setelah sebagian teks sementara sudah ditulis menghasilkan
   `D9_OUTPUT_WRITE_FAILED`, exit 2, tanpa menerbitkan `.json` yang tidak
   lengkap dan tanpa meninggalkan file sementara pada kegagalan yang tertangani.
   Jika proses terhenti paksa, sisa file sementara bukan berkas laporan final
   dan tidak boleh dipakai sebagai bukti. Tes mensimulasikan kegagalan setelah
   menulis prefiks serta race ketika file target dibuat proses lain.
2. **P1 identitas broker ledger:** hasil `preview` selalu memuat
   `ledger_broker_identity_verified: false` dan
   `ledger_broker_identity_reason: D9_LEDGER_CYCLE_BROKER_IDENTITY_UNBOUND`.
   Legacy `observer_cycles` hanya menyimpan `clock_shift_hours`, bukan
   hash identitas broker per siklus. Bukti schedule dan clock yang cocok
   tidak boleh ditafsirkan sebagai verifikasi independen untuk siklus ledger.
   Kategori `QUOTE_READY_ONLY` tetap sebatas diagnostik. Tes regresi
   memeriksa penanda ini bahkan ketika semua quote sintetis tersedia.
3. **Belum dibenarkan untuk diisi:** rentang validitas jadwal broker,
   bukti setiap tanggal/libur, interval UTC/DST, serta ketujuh simbol
   benar-benar diamati di VPS pada scope yang sama. Tidak ada perubahan
   assessor resmi D8, cutoff, denominator, Risk Governor, promotion lock,
   koneksi MT5, atau kewenangan trading.
4. **Syarat penerimaan:** CI Body/Ubuntu/Windows/KAT-CG-04 pada SHA
   terbaru, review ulang Owner, dan tata kelola review independen tetap
   dipenuhi sebelum merge. Tidak ada izin deploy atau aktivasi.
