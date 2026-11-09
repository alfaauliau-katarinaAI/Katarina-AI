# Katarina AI — Kontrak eksekusi & spesifikasi simulator keenam kandidat

**Status:** **KONTRAK DASAR D10-K23 + BATAS EVENT D10-K24 DISETUJUI**; rincian model broker/data dan seluruh gerbang preregistration **BELUM LULUS**. D10-K22 menetapkan zona; D10-K23 (5 November 2026 WIB) menetapkan replay tick kronologis, touch BID, BUY ASK/SELL BID, block bila urutan tak terbukti, dan 6 hipotesis terisolasi. **Bukan perubahan kode eksekusi, bukan approval backtest/holdout atau izin order.**
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

## 2B. Keputusan D10-K24 — boundary candle, zona beririsan, urutan tick (APPROVED)

Owner secara eksplisit menyetujui semua aturan ini pada 5 Nov 2026 WIB, **sebelum** melihat P/L keenam kandidat:

1. **Candle M15 memakai interval setengah terbuka `[open_utc,close_utc)`.** Tick dengan timestamp tepat sama dengan `close_utc` termasuk candle M15 **berikutnya**, bukan candle yang baru tutup. Satu candle M15 tempat BID tick first touch terjadi digunakan **satu kali** untuk konfirmasi B2/S2 **setelah candle itu selesai**, sepanjang status fresh/invalidasi masih memenuhi aturan. Urutan close-bar signal vs tick pada boundary harus kausal: sinyal dari candle yang baru tutup baru boleh dievaluasi setelah close diketahui, dan fill pada tick eligible setelah keputusan, bukan memakai tick boundary berulang untuk mengisi sinyal yang baru dihitung. Fixture harus menguji hal ini.
2. **Zona demand/supply H1 beririsan:** pada BID tick first touch, buat himpunan zona eligible dan benar-benar disentuh pada tick tersebut; pilih nilai absolut `abs(bid_tick - proximal_edge)` **paling kecil**. Tie: `zone_confirmed_at` lebih baru, lalu `zone_id` stabil untuk hasil deterministik. Pilihan terjadi pada event first touch **tanpa melihat price path masa depan**. Jangan membuka beberapa entry dengan menggandakan satu event; status zona tak terpilih saat sentuhan simultan **masih perlu aturan lifecycle** agar tidak mengubah jumlah kesempatan diam-diam.
3. **Tick timestamp sama:** pakai urutan asli dari bukti feed yang dapat diverifikasi bila ada. Bila beberapa urutan masih sama-sama mungkin dan dapat mengubah signal/SL/TP/fill/first touch, status **`BLOCKED_INTRABAR_ORDER`**. Tidak memaksakan urutan berdasarkan harga atau ID buatan dan **tidak** memakai OHLC SL-first/TP-first. Bila semua urutan yang masih mungkin memiliki konsekuensi identik, catat bahwa urutan tidak memengaruhi outcome dan lanjut hanya jika bukti/algoritme kesetaraan tersebut benar-benar teruji (tidak melakukan guess atas urutan).
4. Aturan **D10-K23 tetap**: struktur & touch BID, BUY entry ASK/SELL entry BID, BUY exit BID/SELL exit ASK, enam hipotesis independen, fail-closed ketika bukti event tidak lengkap.

### 2B.1 Remaining technical details — BELUM disetujui / belum terverifikasi

| Item | Yang harus ditetapkan sebelum code/spec freeze | Owner status |
|---|---|---|
| Zona beririsan yang tidak terpilih | Semua zona lain yang sama-sama first-touched → `CONSUMED_OVERLAP_NOT_SELECTED`, hanya terpilih menjalani satu konfirmasi M15 | **APPROVED D10-K25** |
| Prioritas event tepat boundary H1/M15/M5 | Secara eksplisit tetapkan ordering causal close-bar update, FIRST_TOUCH, SIGNAL_KNOWN, ENTRY_INTENT, dan tick execution sehingga tidak double-fill | **PENDING fixture** |
| Tick data quality | Cara memvalidasi quote duplicate, hole/gap, late/out-of-order, ketepatan timestamp dan sumber broker terhadap hasil; tidak memilih threshold dengan melihat profit | **PENDING dataset evidence** |
| Model order broker | Laporan stop-level/freeze, mekanisme trigger SL/TP vs harga fill dan slippage waktu gap, swap, trade halt; tidak mengarang fill | **PENDING contract evidence** |
| Sesi resmi | Quote session dan trade session XAUUSD.vx serta DST/holiday per hari, `effective_at_utc` | **BLOCKED real evidence** |
| Input frozen | `code_sha256`, tick bar hash, UTC clock evidence, manifest, `costs.json`, `split.json` | **PENDING** |

### 2B.2 Pemeriksaan kesiapan implementasi offline (read-only GitHub audit)

| Komponen | Bukti repo di `main` | Penilaian |
|---|---|---|
| Protokol registrasi dan validator | `docs/research/VALIDATION_PROTOCOL.md`, `src/katarina/research/validation.py`; registry hash, split/gap, biaya, Bonferroni dan holdout firewall | **Tersedia**, tidak berarti kandidat siap didaftarkan |
| Dataset bar historis | `src/katarina/research/dev_dataset.py` punya `M5/M15/H1` dan cutoff `2026-10-13T00:00:00Z`, hash manifest | **Tersedia untuk bars saja**, bukan replay tick yang diperlukan keputusan D10-K23 |
| Loader/CLI riset | `scripts/research/simulate_setups.py` hanya membaca verified dev bars; `scripts/research/export_dev_bars.py` melarang pemakaian VPS observer produksi, butuh mesin riset terisolasi | **Belum memiliki jalur tick replay auditable** |
| Detektor & engine setup | `src/katarina/research/setups/{liquidity_sweep,pullback,market_structure,core,simulator}.py` masih sinyal lama dengan `target_rr`, `min_rr`, M5/H1, `max_hold_bars` dan OHLC exit | **Mismatch; implementasi offline belum dimulai** |
| Suite fixture | Rencana pengujian T01–T12 tersedia di bagian 4 dokumen ini | **Hanya spesifikasi tes**; belum dieksekusi/lulus |
| Data asli dan sesi broker | Bukti sesi resmi `SymbolInfoSessionQuote`/`SymbolInfoSessionTrade` belum tersedia; tick stream historis development yang dapat diaudit dan costs hash belum ditunjukkan | **Blocked for verified full research** |

**Gate implementation readiness:** `CONTRACT_CORE_DEFINED` dan `ACCEPTANCE_CRITERIA_DRAFTED`, tetapi `IMPLEMENTATION_NOT_STARTED`, `REAL_DATA_NOT_VERIFIED`, `SESSION_EVIDENCE_MISSING`. Tahap yang mungkin selanjutnya adalah membuat **branch riset terisolasi dan fixture synthetic-only** setelah rencana kerja/otorisasi yang jelas; ini tidak sama dengan pengujian profitabilitas. **Tidak ada izin untuk menyentuh source produksi, VPS observer, MT5 trading, registry, atau holdout**.

## 2C. Keputusan D10-K25 — first visit zona beririsan (OWNER APPROVED, 5 Nov 2026 WIB)

**Keputusan Owner:** bila satu tick BID pertama secara bersamaan menyentuh beberapa zona H1 yang masih eligible dan FRESH, **semua zona yang tersentuh menghabiskan kesempatan first visit**. Zona prioritas dipilih menurut D10-K24: jarak BID ke proximal edge paling dekat; tie `zone_confirmed_at` terbaru, lalu stable `zone_id`.

**Transisi deterministik yang wajib diwujudkan di simulator offline:**
1. Tick first-touch terverifikasi menghasilkan satu `touch_event_id`, satu `selected_zone_id` dan daftar `all_touched_zone_ids` dari kumpulan zona eligible **pada tick itu**, tanpa informasi masa depan.
2. Zona terpilih → `FIRST_VISIT_PENDING_M15`. **Semua zona lain yang sama-sama baru tersentuh → `CONSUMED` seketika**, reason `CONSUMED_OVERLAP_NOT_SELECTED`. Zona yang tidak tersentuh tetap `FRESH` jika valid.
3. **Hanya zona prioritas** yang boleh menghasilkan `ENTRY_INTENT`, setelah satu candle M15 yang memuat first touch (interval `[open_utc,close_utc)`) ditutup dan memenuhi konfirmasi. Pada akhir episode, zona terpilih juga → `CONSUMED`, baik terjadi entry maupun sinyal gagal. Tidak boleh mencoba zona overlap lain sebagai fallback.
4. Bila terjadi intrabar breach distal+buffer sebelum konfirmasi, blokir entry langsung, catat breach; setelah H1 close tentukan status `INVALID` atau `CONSUMED` sesuai D10-K9/K10; tidak kembali `FRESH`.
5. Jika tick/urutannya tidak dapat membuktikan event bersama, `BLOCKED_INTRABAR_ORDER` atau `BLOCKED_DATA_EVIDENCE`; **jangan** menciptakan first touch atau memutasi lifecycle atas event yang belum pasti. Catat `source_tick_id,touch_event_id,all_touched_zone_ids,selected_zone_id,consumed_zone_ids,bid,event_at_utc,reason_code`.
6. Zona yang disentuh pada **tick berbeda** dievaluasi mengikuti episode masing-masing; satu posisi aktif per kandidat tetap berlaku dan keenam kandidat dinilai terpisah.

### 2C.1 Status kontrak dan implementasi

| Lingkup | Status |
|---|---|
| D10-K1–D10-K25: aturan inti sinyal, swing TTL, SL/TP, zona, time-exit, BID/ASK dan event ordering | **DESAIN INTI DISETUJUI** |
| Perilaku zona overlap yang tak dipilih | **DITETAPKAN D10-K25**; tambah fixture overlap ke T03 dan T10 |
| Algoritme/prasyarat order broker, stop/freeze, slippage gap, replay tick out-of-order, timestamp dan DST | **PENDING VERIFIKASI INPUT & UNIT TEST**; tidak boleh mengarang fill |
| Dev dataset pre-13 Okt 2026, manifest/hashes/clock, `costs.json`, `split.json`, official MT5 sessions | **BELUM TERBUKTI** |
| Source simulator tick replay sesuai semua enam hipotesis | **BELUM DIIMPLEMENTASIKAN**; kode `main` masih OHLC+target RR |
| Preregistration, backtest development, akses holdout, demo/live | **BELUM DIOTORISASI** |

**Kesimpulan:** `SPEC_CORE_FINALIZED` / `OFFLINE_SYNTHETIC_ENGINE_REQUIREMENTS_READY` / `G6_DATA_UNVERIFIED` / `G7_SESSION_BLOCKED` / `G8_ENGINE_NOT_IMPLEMENTED` / `REGISTRY_NOT_WRITTEN` / `NO_BACKTEST` / `LIVE_OFF`.

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

`D10-K22_ZONE_BASELINE_APPROVED` · `D10-K23_TICK_REPLAY_APPROVED` · `D10-K24_EVENT_BOUNDARIES_APPROVED` · `D10-K25_OVERLAP_CONSUMED_APPROVED` · `G3_CORE_APPROVED` · `G4_CORE_APPROVED_TECHNICAL_DETAILS_PENDING` · `G6_DATA_COST_UNVERIFIED` · `G7_OFFICIAL_BROKER_SESSIONS_MISSING` · `G8_SIMULATOR_NOT_IMPLEMENTED` · `NO_BACKTEST` · `REGISTRY_NOT_WRITTEN` · `HOLDOUT_LOCKED` · `LIVE_OFF`.
