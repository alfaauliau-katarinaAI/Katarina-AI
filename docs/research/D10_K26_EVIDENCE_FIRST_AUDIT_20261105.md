# Katarina AI — D10-K26, audit bukti broker & host riset sebelum simulator offline
**Tanggal keputusan:** 5 Nov 2026 WIB · **Status:** `EVIDENCE_FIRST_APPROVED` / `NOT_VERIFIED_FOR_SIMULATION` · **Ruang lingkup:** audit artefak GitHub *read-only* serta daftar bukti yang perlu dikumpulkan. **Bukan** izin untuk menjalankan probe di terminal produksi, menggunakan VPS observer, coding simulator, mengakses holdout, preregistration atau backtest.

## 1. Keputusan Owner

Owner memilih **verifikasi tick historis, biaya/spesifikasi broker, sesi MT5, dan lingkungan riset sebelum mengizinkan coding simulator offline** (bukan jalur synthetic-only coding dulu). Tidak ada keputusan baru yang boleh ditafsirkan sebagai izin menyentuh MT5, EA/trading, VPS produksi, atau mengubah aturan Stage0. D10-K1–K25 tetap berlaku.

## 2. Bukti yang diperiksa dari repositori (bukan verifikasi langsung lingkungan)

| Evidence ID | Fakta yang dapat diverifikasi dari repo saat audit | Klasifikasi | Yang masih kurang |
|---|---|---|---|
| **EV26-TICK-01** | `docs/maintenance/MT5_SESSION_MAP_20261104.md` merinci lokasi archive observer `C:\Katarina\state\readonly-observer\broker-ticks\<SIMBOL>\<YYYY-MM-DD>.csv.gz`, dengan ringkasan 22–29 Okt dan 2–3 Nov 2026 serta ketidakpastian konversi waktu lama | **DOCUMENTED_HISTORICAL_OBSERVER_ARCHIVE, BUKAN DATA DEVELOPMENT VERIFIED** | Daftar dan SHA-256 berkas asli, isi tick bid/ask, tanggal rentang, integritas time_msc+sequence, gap, identitas server, bukti konversi UTC, data tick broker **sebelum cutoff 13 Okt 2026** dari host riset terpisah |
| **EV26-BARS-02** | `src/katarina/research/dev_dataset.py` mendukung M5/M15/H1/H4 bar, manifest+hash dan cutoff `2026-10-13T00:00:00Z`; `scripts/research/export_dev_bars.py` mensyaratkan MT5 riset terisolasi & clock evidence | **TOOLING_VERIFIED; NO VERIFIED HISTORICAL TICK LOADER** | Tick archive research + decoder/validator actual broker, korelasi tick→bar dan hash provenance. **Bar OHLC bukan pengganti tick intrabar D10-K23** |
| **EV26-COST-03** | `docs/research/VALIDATION_PROTOCOL.md` menetapkan biaya spread entry/exit, komisi pulang-pergi, slippage, swap long/short, triple swap weekday dan stress 1.5x/2x; `costs.json` wajib dibekukan sebelum riset | **COST_FORMULA_VERIFIED, COST_VALUES_NOT_VERIFIED** | Nilai faktual untuk **server+akun+simbol+tanggal efektif**: spread/tick bid-ask, komisi per lot/kontrak, swap long/short/triple day, slippage pembuktian, currency conversion, minimum volume dan contract spec, serta `costs.json` hash |
| **EV26-SYMBOL-04** | `dev_dataset.py::_metadata` membaca `point`, `trade_tick_size`, `trade_contract_size`, tetapi tidak membuktikan snapshot historis kontrak XAUUSD.vx atau semua aturan stop/freeze | **READER_EXISTS; CONTRACT_EVIDENCE_MISSING** | `symbol_info(XAUUSD.vx)` dari broker relevan, `digits, point, trade_tick_size, trade_contract_size, trade_stops_level, trade_freeze_level, volume_min, volume_step, currency_profit, trade_mode`, server/account type, TTL dan captured_at_utc; tangkapan spesifikasi (redacted) |
| **EV26-SESS-05** | `docs/maintenance/BROKER_SYMBOL_SESSION_EVIDENCE_20261103.md`: script `KatarinaBrokerSessionProbe.mq5` dikompilasi di staging, **belum dijalankan** pada MT5 produksi; `MT5_SESSION_MAP_20261104.md` hanya peta gap tick empiris | **PROBE_CODE_VERIFIED; OFFICIAL_SESSION_NOT_OBSERVED** | Output `SymbolInfoSessionQuote` DAN `SymbolInfoSessionTrade` untuk simbol/server dan semua weekday; timezone/UTC offset independen, DST AS dan broker, akhir pekan/libur/exception; source date dan reviewer |
| **EV26-HOST-06** | `scripts/research/export_dev_bars.py` dan `scripts/research/build_bar_clock_evidence.py` memerlukan **research terminal64.exe portable yang ditunjuk eksplisit**, marker `.katarina-research-terminal=ISOLATED_RESEARCH_ONLY`, AutoTrading OFF, no EA/observer, dan melarang VPS production observer | **ISOLATION_REQUIREMENTS_VERIFIED; HOST_ACTUAL_NOT_VERIFIED** | Aset host/path yang benar-benar terpisah, hardware/disk/RAM, software & Python environment, terminal locked, trading disabled, clock/NTP evidence, permission read-only, direktori input development terpisah dari observer/holdout dan daftar kontrol akses |
| **EV26-SPLIT-07** | `VALIDATION_PROTOCOL.md` menetapkan `split.json` berisi dev/holdout/gaps; registry hash-chained, holdout once-only; data sejak 13 Okt 2026 adalah holdout program, tidak boleh dijadikan development/test tuning | **PROTOCOL_VERIFIED; CONCRETE_SPLIT/COST/HASH UNVERIFIED** | `split.json`, `costs.json`, manifest tiap berkas dan hash; validasi kalender gap, tanggal efektif, pemisahan file; cutoff konservatif **before 2026-10-13T00:00Z** |
| **EV26-ENGINE-08** | `src/katarina/research/setups/simulator.py` masih OHLC M5/H1, fixed max_hold_bars; `core.py` masih target_rr/min_rr; belum ada replay tick D10-K23, six-candidate first touch D10-K25 dan Hybrid Time Exit | **CODE_MISMATCH_CONFIRMED; CODING NOT AUTHORIZED** | Implementasi dan fixture synthetic-only di branch terpisah **nanti** setelah bukti di atas lolos dan Owner mengizinkan |

### Kesimpulan data yang tidak boleh disalahartikan
- Arsip tick observer yang terdokumentasi untuk **akhir Oktober–awal November 2026** berada **sesudah cutoff pengembangan 13 Okt 2026 UTC**. Arsip tersebut **tidak bisa dipromosikan sebagai development dataset untuk mengoptimalkan enam kandidat**, dan data backfill dari masa tersebut bukan forward trade.
- **Keberadaan script atau manifest reader bukan bukti** data historis valid, biaya aktual, jadwal broker, atau host terisolasi sudah siap.
- Jam kosong XAUUSD.vx yang dihitung dari tick 21:54–23:00 UTC pada rentang tertentu adalah **observasi**, bukan sesi `SymbolInfoSession*` resmi; angka tidak boleh dikonversi menjadi kebijakan preclose tanpa bukti broker.
- Broker server, jenis akun, konfigurasi kontrak, tanggal efektif dan offset DST **belum diverifikasi langsung** dalam rapat ini. Jangan mengisi placeholder biaya/jam/tingkat spread sebagai 'aktual'.

## 3. Paket bukti yang harus masuk sebelum izin simulator offline

| Prioritas | Paket bukti | Minimal kriteria `VERIFIED` | Pengambil bukti yang diperkenankan |
|---|---|---|---|
| **P0-E1** | Tick historis development | Tick **BID & ASK**, timestamp sumber dan sequence teruji, symbol exact XAUUSD.vx, server/account type, identitas feed, rentang **sebelum 2026-10-13**, SHA-256, laporan gap & anomaly, UTC independent clock | Host riset terisolasi yang telah mendapat izin; jangan menyalin observer/holdout menjadi dev |
| **P0-E2** | Spesifikasi kontrak dan biaya | Snapshot symbol contract & account fee berlaku untuk periode yang diklaim; stop/freeze, precision/tick_size, spread samples, komisi, swap long/short/triple, rollover, slippage evidence; `costs.json` provenance/hash | Read-only MT5/specs resmi dari broker; sensor tidak membuka order |
| **P0-E3** | Sesi MT5 | Log quote **dan** trade session resmi per weekday, evidence server identity/time zone, DST/holiday exception, timestamp source, reviewer; missing means UNVERIFIED | Probe read-only **hanya setelah izin terpisah** untuk terminal/host yang ditunjuk |
| **P0-E4** | Lingkungan riset | Identitas host non-produksi, bukti terminal portable terisolasi/marker, AutoTrading OFF, no EA/observer, izin data folder, disk quota, clock & dependencies | Inventory read-only pada host riset **setelah identitas dan izin jelas** |
| **P0-E5** | Split & integritas | Cutoff development vs holdout, `split.json` gaps, manifest tick/bar dan costs SHA, penyimpanan redacted di private evidence storage, report validator | Reviewer independen, tidak memanggil CLI holdout |

**Klasifikasi audit:** `NOT_PRESENT` (berkas/bukti belum diberikan), `PRESENT_UNVERIFIED` (ada namun belum diaudit), `VERIFIED` (sumber+hash+reproducibility sah), `BLOCKED` (memerlukan izin/privat/data). Semua raw logs broker/account dan identitas privat **jangan commit ke GitHub**; hanya ringkasan bukti tanpa PII dan hash yang tepat dapat ditautkan ke PR.

## 4. Urutan kerja dan batas izin

1. Owner menyetujui *evidence first* → dokumentasikan daftar bukti dan audit repo **sekarang**.
2. **Berikutnya**: tetapkan host penelitian terpisah dan pengumpulan data dari sumber aman, serta **izin eksplisit** jika perlu menjalankan probe broker read-only pada MT5 produksi; jangan menyamakan keputusan D10-K26 dengan izin menjalankan script pada VPS.
3. Ambil bukti dan lakukan verifikasi read-only; redaksi data akun, harga dan kontrak dicatat dari sumber, hash/clock/sesi ditandatangani reviewer.
4. Jika semua P0-E1–E5 `VERIFIED`, ajukan keputusan Owner yang **terpisah** untuk implementasi simulator synthetic-only. Ini tetap **bukan** izin evaluasi P/L atau registrasi final.
5. Sesudah simulator sesuai spesifikasi lulus fixture T01–T12 dan seluruh input difreeze, barulah tinjau `registry.jsonl`, development walk-forward dan biaya. Holdout tetap LOCKED.

**Batas tegas rapat:** tidak menyentuh VPS, tidak memasang/menjalankan MQL5 probe, tidak mengambil broker tick live, tidak menjalankan MT5, tidak membuat `costs.json` estimasi, tidak mengubah source, tidak memulai fixture/backtest, tidak mengakses holdout, tidak mengubah trading.

`D10-K26_EVIDENCE_FIRST_APPROVED` · `REPO_TOOLING_AUDITED` · `REAL_TICK_DEV_UNVERIFIED` · `BROKER_FEES_UNVERIFIED` · `OFFICIAL_SESSION_MISSING` · `ISOLATED_RESEARCH_HOST_UNVERIFIED` · `NO_CODING` · `NO_BACKTEST` · `NOT_REGISTERED` · `HOLDOUT_LOCKED` · `LIVE_OFF`.
