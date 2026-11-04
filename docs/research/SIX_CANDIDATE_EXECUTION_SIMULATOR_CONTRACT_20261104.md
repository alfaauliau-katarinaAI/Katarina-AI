# Katarina AI — Kontrak eksekusi & spesifikasi simulator keenam kandidat

**Status:** **KONTRAK DESAIN EKSEKUSI D10-K23 DISETUJUI**; rincian implementasi dan seluruh gerbang preregistration **BELUM LULUS**. D10-K22 menetapkan zona; D10-K23 (5 November 2026 WIB) menetapkan replay tick kronologis, touch BID, BUY ASK/SELL BID, block bila urutan tak terbukti, dan 6 hipotesis terisolasi. **Bukan perubahan kode eksekusi, bukan approval backtest/holdout atau izin order.**
Rujukan [spesifikasi enam kandidat](SIX_CANDIDATE_PREREGISTRATION_SPEC_20261104.md) dan [protokol validasi](VALIDATION_PROTOCOL.md).

## 1. G3 — Zona H1 yang disetujui Owner (D10-K22)

| Kunci | BUY B2 demand | SELL S2 supply | Status |
|---|---|---|---|
| Pemicu | H1 BOS **close >= confirmed swing high + tick_size** | H1 BOS **close <= confirmed swing low - tick_size** | APPROVED |
| Persyaratan BOS | Level swing sudah terkonfirmasi sebelum candle H1 BOS dimulai; min 1 tick | Sama | APPROVED |
| Origin | **Candle bearish H1 terakhir** dalam **12 candle H1 selesai sebelum BOS** | **Candle bullish H1 terakhir** dalam 12 H1 sebelum BOS | APPROVED |
| Batas zona | High dan low candle origin utuh **full wick**, bukan body | Sama | APPROVED |
| Lahir zona | Setelah candle BOS H1 selesai, bukan intrabar | Sama | Interpretasi causal wajib |
| Entry reaksi | Satu **M15 candle yang memuat first touch**, perlu menyentuh zona lalu bullish dan **close di atas high zona** | Sama, bearish dan **close di bawah low zona** | APPROVED |
| Target zona lawan | **Proximal edge supply = low zona supply** | **Proximal edge demand = high zona demand** | APPROVED |
| Usia & invalidasi | Maksimum **48 valid closed H1** sejak confirm; first visit only; breach hybrid tidak pernah fresh lagi | Sama | APPROVED dari D10-K9/K10 |

Tidak ada candle origin dalam 12 H1 sah → `WAIT:NO_VALID_ZONE_ORIGIN`. Jangan memilih candle lain setelah melihat P/L. Jika first-touch M15 close gagal, zona `CONSUMED`; bila breach distal+buffer sebelum entry, tak boleh membuka entry dan status breach diselesaikan oleh H1 close. Waktu `zone_confirmed_at = BOS_close_utc` harus memiliki rekam sumber. **D10-K23 menetapkan BID** sebagai referensi touch/breach zona serta BUY ASK/SELL BID sebagai harga eksekusi; deteksi overlap zona dan penanganan tick tepat batas M15 **belum diputuskan secara rinci**.

## 2. Eksekusi riset: pemisahan aturan dan bukti broker

### Kontrak keputusan yang telah didukung Owner

1. Semua keputusan struktur memakai **bar tertutup** dan timestamp `known_at <= decision_at`. Swing H1/M15: 2 kiri + 2 kanan, dengan `confirmed_at` setelah 2 bar kanan selesai. TTL swing M15 96 bar dan H1 72 bar; zona H1 48 bar. Candle hilang/gap bukan candle sah.
2. Entry: sinyal menjadi eligible hanya **sesudah close bar konfirmasi**, fill BUY di ASK dan SELL di BID pada quote eksekutabel berikut, dengan biaya aktual dan batas sesi sah. Tidak ada filled order di waktu sinyal jika quote tidak ada; tidak ada entry kembali dari setup yang sudah dikonsumsi.
3. SL BUY di bawah ekstrem struktur minus buffer; SL SELL di atas ekstrem plus buffer; buffer `ceil_to_tick(max(tick_size, spread_at_decision, .10*ATR14_Wilder(closed entry TF)))`. TP dipilih dari tingkat struktur sah terdekat yang menguntungkan relatif terhadap harga fill, **tanpa min RR**, tie newer `confirmed_at`, lalu stable id. Jika stop/TP invalid atau melanggar batas spesifikasi broker → `WAIT` dengan reason; **bukan** melonggarkan stop atau mendekatkan target setelah hasil diketahui.
4. B1/S1 time exit 12 fully completed M5 bar/90 menit UTC/15 min sebelum official close, B2/S2 12 M15/240 min/30 min, B3/S3 24 M5/180 min/20 min. Yang terjadi pertama membuat **exit intent**; fill hanya di quote yang benar-benar dapat dieksekusi. Jika tidak ada quote: `EXIT_PENDING_NO_QUOTE`, laporkan posisi belum tertutup. SL/TP yang sudah terjadi lebih awal menang.
5. Satu posisi aktif **per kandidat**, dengan reason saat sinyal duplikat. Sejauh ini belum ada izin melakukan netting/hedging portofolio antarkandidat dalam riset. Keputusan terhadap **interaksi antar-kandidat** diperlukan sebelum suatu simulasi gabungan, tetapi bisa tetap menilai setiap hipotesis terpisah sesuai protokol.

## 2A. Keputusan D10-K23 — kontrak eksekusi yang DISETUJUI

| Aspek | Kebijakan wajib dari Owner | Efek terhadap simulasi |
|---|---|---|
| Data urutan peristiwa | **Replay tick broker kronologis dengan bukti timestamp dan urutan** | Tidak boleh membuat lintasan harga dari OHLC; tidak boleh menyimpulkan urutan intrabar dari high/low |
| First touch / distal breach | **BID tick** sebagai referensi sentuh/breach H1 zone; semua bar OHLC struktur memakai BID broker konsisten | BUY ASK tidak digunakan untuk memutuskan apakah struktur zona tersentuh |
| Entry | **BUY ASK; SELL BID** pada quote eksekutabel berikutnya **setelah** bar sinyal ditutup | Jangan mengisi fill pada harga close sinyal atau quote masa lalu |
| Exit | Harga likuidasi nyata **BUY ditutup BID, SELL ditutup ASK**; SL/TP/time exit dinilai pada tick berurutan | Tidak mengarang TP/SL/cutoff atau mendahulukan hasil lebih baik |
| Intrabar uncertainty | Jika urutan timestamp/tick atau sumber harga tidak dapat membuktikan SL vs TP / trigger vs fill, **`BLOCKED_INTRABAR_ORDER`** | **TIDAK ADA fallback OHLC SL-first maupun TP-first**; baris/episode yang terhalang wajib ada pada report |
| Evaluasi | **Enam hipotesis XAUUSD terpisah** B1,S1,B2,S2,B3,S3 | Satu posisi aktif per kandidat. Jangan menyisipkan aturan exposure/netting/hedging antarkandidat sebagai pengaruh tersembunyi |
| Sesi | Hanya sesi **quote dan trade resmi** broker XAUUSD.vx yang terverifikasi dapat membuka hak eksekusi | Tanpa bukti sesi, `BLOCKED_SESSION_EVIDENCE`; data tick-gap empiris bukan jam resmi |

Keputusan ini mengunci **kebijakan logika**, bukan mengesahkan bahwa data tick, session, dataset, spec kontrak, atau simulator yang ada sudah memenuhi persyaratan.

### 2A.1 Kontrak pipeline *offline research* (target implementasi, bukan kode aktif)

**Input yang harus terikat hash/version:** `candidate_spec` (BUY/SELL tunggal; param/timeframes/SL/TP/TTL/zone), `symbol_contract` (point, digits, tick size, stop/freeze levels, order semantics), `development_dataset_manifest` (file dan SHA-256), `historical_clock_evidence` (server→UTC), `tick_stream` (BID/ASK + UTC timestamp resolusi cukup + bukti order), `closed_bars` (M5,M15,H1 yang dibangun/ diverifikasi dari sumber tanpa lookahead), `session_evidence` (quote & trade per simbol+hari/DST), `costs.json`, `split.json`. Kontrak ini **tidak** boleh mengambil data dari VPS/MT5 produksi secara otomatis.

**Event pipeline yang harus dibuat murni/deterministik:**
1. Validasi input, identitas simbol/server, manifest/hash, urutan tick, koneksi waktu broker→UTC, bar tertutup, gap, sesi dan spesifikasi harga sebelum menghitung sinyal. Bukti tidak ada → **BLOCKED** (record reason dan hash sumber).
2. Saat close candle, perbarui confirmed swing 2+2 (TTL M15 96/H1 72), BOS, zona (origin 12 H1, first visit, expiry 48 H1), status breakout retest 6 M5. Gunakan hanya `known_at <= event_at`.
3. Baca aliran tick satu per satu untuk first-touch & breach dengan BID. Tanpa quote BID/ASK valid atau urutan terverifikasi → jangan membuat setup/fill hipotetis. Bila syarat sinyal candle tertutup terpenuhi, bentuk `ENTRY_INTENT`.
4. Pada tick **sesudah keputusan sinyal**, selama trade session terbukti membuka eksekusi dan spesifikasi order mengizinkan, catat `ENTRY_FILLED` pada harga ASK untuk BUY / BID untuk SELL. **Satu kandidat, maksimal satu posisi aktif**. Quote hilang atau sesi tidak terbukti → `BLOCKED`, bukan fill.
5. Set SL struktural + buffer 0.10 ATR14 Wilder TF entry, TP struktur valid terdekat arah profit tanpa min RR. Jika broker stops-level atau geometri invalid, rekam `WAIT`, bukan mengubah target berdasarkan hasil.
6. Proses quote kronologis untuk SL/TP dan Hybrid Time Exit (bar count lengkap sejak fill, clock UTC, pra-tutup sesi resmi). Pemicu time exit menghasilkan `EXIT_INTENT`; hanya tick dan trade session yang memungkinkan eksekusi dapat menghasilkan `EXIT_FILLED`. Tanpa quote atau broker menutup trade → `EXIT_PENDING_NO_QUOTE`, posisi tetap terbuka dengan risiko gap.
7. Penentuan status akhir: `CLOSED`, `WAIT`, `BLOCKED_*`, `EXIT_PENDING_NO_QUOTE`, `DATA_GAP_UNVERIFIED`. Jangan menghapus trade gagal/dibatalkan tanpa reason. Posisi belum exit pada batas data **tidak** boleh diam-diam diperlakukan sebagai trade closed dengan harga bar terakhir.
8. Simulasikan setiap kandidat secara independen sebelum perbandingan side dan baseline; tidak ada perintah broker. Data berisiko bocor dari holdout, timestamp palsu, atau tick tidak lengkap harus ditolak sebelum kalkulasi P/L.

**Audit trail event minimum:** `candidate_id`, `hypothesis_spec_hash`, `source_file_sha256`, `source_tick_id`/`timestamp_utc`, `source_bar_tf`, `bar_closed_at_utc`, `signal_known_at_utc`, `session_evidence_hash`, `bid`, `ask`, `event_type`, `event_status`, `reason_code`, `position_id`, `intended_exit_reason`, `fill_price` (hanya jika benar-benar filled) dan `cost_snapshot_hash`. Audit trail tidak boleh memalsukan identitas tick.

### 2A.2 Bagian implementasi yang MASIH PENDING sebelum final code/spec freeze

| Detail | Proposal desain untuk keputusan berikutnya | Status |
|---|---|---|
| Quote duplicate timestamp | Wajib ada urutan event terpercaya dari sumber; jika tidak bisa dibuktikan dan memengaruhi fill/outcome, **BLOCKED** | Konsisten kebijakan Owner, namun tie-break teknis pending |
| First touch tepat batas M15 | Definisikan candle interval `[open_utc, close_utc)`; tick tepat `close_utc` termasuk candle berikutnya; confirmation candle harus memuat first touch, bukan bar sebelumnya | PROPOSED |
| Zona beririsan dan urutan beberapa sumber level | Prioritas zona eligible **proximal distance terdekat** dari BID first touch, tie confirmed_at terbaru, lalu zone_id stabil; bila tak lengkap → WAIT | PROPOSED |
| Timestamp tick gap, late/out-of-order quote | Tetapkan ambang/laporan kualitas dari bukti broker **sebelum** pengujian; no synthetic interpolation dan no silent resampling | PENDING threshold |
| SL/TP trigger versus broker fill/stop constraints | Gunakan tick actual BID/ASK, nilai order semantics kontrak broker; jika harga trigger pasti tapi fill belum terverifikasi, jangan buat fill harga target palsu | PENDING modelling |
| Candidate overlap | Setiap hipotesis terisolasi tanpa netting atau hedging bersama. Simulasi portofolio gabungan adalah pekerjaan/otorisasi terpisah | APPROVED independence; portfolio policy not approved |

**Jangan menyamakan `BLOCKED_INTRABAR_ORDER` dengan transaksi rugi, untung, ataupun 0R**. Hitung juga cakupan data blocked, distribusi waktu/data gaps, dan alasannya; bila event penting tidak dapat dipastikan, penelitian tersebut tidak boleh mengklaim PASS.

## 3. G8 — Gap kode simulator nyata di `main` (audit read-only)

| Lokasi | Kondisi sekarang | Perubahan offline yang diperlukan |
|---|---|---|
| `src/katarina/research/setups/core.py::signal` | `target_rr` tetap dan `min_rr >= 0.01` | Target struktur causal; tidak menghapus peluang hanya karena RR kecil |
| `src/katarina/research/setups/simulator.py::simulate` | Memuat M5 dan H1 saja; setiap setup berada pada loop M5 | Gunakan M15,H1,M5 secara timestamp-as-of, tidak ada lookahead |
| `simulator.py::_exit` | `max_hold_bars` M5 dan OHLC stop-first | Hybrid bar/UTC/verified preclose, tick-order, status pending/no quote dan gap |
| `src/katarina/research/setups/liquidity_sweep.py` | Range M5, tanpa confirmed M15 swing reference | Sweep+reclaim satu M5 terhadap M15 pivot + TTL 96 + min 1 tick |
| `src/katarina/research/setups/pullback.py` | Mean pullback M5, bukan fresh H1 zone | Pembentukan zona 12 H1 / BOS+1 tick / full wick, finite-state first-visit dan M15 |
| `src/katarina/research/setups/market_structure.py` | M5 close-break immediate entry | Breakout H1 >=1 tick + one M5 retest within six |
| `src/katarina/research/validation.py` + CLI | Memiliki registry dan validator, tidak menyelamatkan aturan sinyal yang berbeda | Pertahankan hash ledger; pastikan input simulator adalah versi yang dipraregistrasi |

**Batas edit:** tidak ada perubahan terhadap `src/`, `scripts/`, MT5, VPS, `main`, ledger Stage0, `holdout`, atau strategi demo/live dalam rapat ini. Implementasi baru pada branch riset terpisah dan perlu audit/CI serta persetujuan sesuai roadmap.

## 4. Tes penerimaan dan gerbang implementasi (tidak dijalankan pada rapat ini)

**Fixture deterministik yang wajib ada sebelum review source code riset:**

- `T01` pivot M15/H1 2+2: pivot tidak dapat dipakai sebelum dua right bars closed; TTL 96/72 boundaries dan equal-high tie.
- `T02` B1/S1 sweep+reclaim **satu M5** + penetrasi satu tick; tidak fill pada close candle.
- `T03` B2/S2 BOS H1 min 1 tick, origin candle berlawanan terakhir dalam 12 H1, zona full wick, confirm first-touch candle M15 satu episode, breach intrabar, expiry 48 H1, target proximal lawan.
- `T04` B3/S3 H1 close-break min tick, M5 same-bar retest within six full bars, cancel/reason jika timeout, swing broken eligible satu kali.
- `T05` ATR14 Wilder dari bar tertutup, dynamic SL buffer, rounding tick size, stops level, structural TP tanpa minRR.
- `T06` BID touch & breach; entry BUY ASK/SELL BID, exit BUY BID/SELL ASK, valid session trade vs quote mismatch.
- `T07` Same-OHLC-but-opposite tick ordering → dua outcome berbeda **hanya bila urutan tick terbukti**; missing/out-of-order tick → `BLOCKED_INTRABAR_ORDER`; jangan SL-first fallback.
- `T08` Time Exit B1/S1 12 M5/90 min/15 min; B2/S2 12 M15/240 min/30 min; B3/S3 24 M5/180 min/20 min, termasuk partial bar dan no quote at expiry.
- `T09` DST broker, sesi overnight, penutupan Jumat, holiday, bars/ticks missing, unavailable session evidence → fail closed/no fabricated fill.
- `T10` Independensi enam `symbol×side×strategy`, satu posisi per kandidat, sinyal duplikat di-block tanpa mengganggu evaluasi kandidat lain.
- `T11` Non-mutation/cost/manifest hash: future-bar poisoning tidak mengubah signal lama; inputs sama → event/log hash sama; `code_sha256` dan split hash cocok; tidak membaca holdout.
- `T12` Broker spread/slippage/commission/swap dari sumber terdaftar + stress 1.5x/2x pada validator; tidak menghilangkan blocked/fail trades untuk menaikkan metrik.

**Tahapan pekerjaan yang diizinkan saat ini hanya spesifikasi & audit read-only**, bukan menjalankan tes di VPS:
1. D10-K23 telah memilih tick replay/BID/ASK/fail-closed/isolasi enam kandidat.
2. Bekukan detail event boundary & zona overlap yang masih **PROPOSED** pada D10-K24, dan lengkapi sumber symbol/session.
3. Implementasi simulator **offline research branch terpisah** setelah scope dan akses disetujui, dengan unit test synthetic-only. Jangan sentuh kode `main` atau VPS observer/trading otomatis.
4. Lulus peer review, fixture, verifikasi data development/cost/session, freeze code/data/split/hashes.
5. Baru daftar seluruh 6 definisi unik di registry sebelum evaluasi profit; setiap parameter berubah = percobaan baru; maksimum 5/simbol/sisi dan `alpha=0.05/N`.

## 5. Status

`D10-K22_ZONE_BASELINE_APPROVED` · `D10-K23_TICK_REPLAY_APPROVED` · `G3_CORE_APPROVED` · `G4_CORE_APPROVED_TECHNICAL_DETAILS_PENDING` · `G6_DATA_COST_UNVERIFIED` · `G7_OFFICIAL_BROKER_SESSIONS_MISSING` · `G8_SIMULATOR_NOT_IMPLEMENTED` · `NO_BACKTEST` · `REGISTRY_NOT_WRITTEN` · `HOLDOUT_LOCKED` · `LIVE_OFF`.
