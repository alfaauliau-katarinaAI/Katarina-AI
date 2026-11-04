# Katarina AI — enam kandidat XAUUSD: spesifikasi pra-registrasi

**Rapat Owner:** 4 November 2026 · **status:** DRAFT FOR FINALIZATION / **NOT REGISTERED** · **branch:** `manager/stage0-proof-meeting-20261104` · [notulen](../ROADMAP_DISCUSSION.md)

Dokumen ini mengonsolidasikan keputusan Owner untuk **B1/S1, B2/S2, B3/S3**. Tanda **APPROVED** menunjukkan keputusan rapat; **TBD/BLOCKED** adalah syarat yang **belum dapat dianggap disetujui**. Jangan menyamakan spesifikasi awal dengan hipotesis resmi; `registry.jsonl` belum ditulis, `code_sha256` belum dibekukan, dataset belum diaudit, dan **belum ada backtest/profitability claim**. Bukan izin trading, deployment, akses holdout atau eksekusi MT5 produksi.

## I. Baseline terpilih dan ruang lingkup

- Instrumen kandidat pertama: **XAUUSD.vx**, dengan konfirmasi nama simbol dan spesifikasi kontrak broker sebelum registrasi. Enam hipotesis **independen per sisi**: B1 BUY sweep, S1 SELL sweep, B2 BUY trend pullback, S2 SELL trend pullback, B3 BUY breakout-retest, S3 SELL breakdown-retest. Kombinasi instrumen baru memerlukan registrasi dan bukti sesi sendiri.
- **APPROVED**: pivot swing high/low **2 candle kiri dan 2 kanan**, baru dikenal setelah dua candle kanan selesai; tidak ada penggunaan retroaktif, equal high/low perlu aturan tie yang deterministik.
- **APPROVED**: TP **struktur valid terdekat yang diketahui pada saat entry**, **tanpa filter minimum RR**. Target harus pada sisi profit dari harga fill; jika tidak ada struktur valid, `WAIT:NO_VALID_STRUCTURAL_TARGET`. Catat gross/net reward dan biaya tanpa menghilangkan trade ber-RR kecil.
- **APPROVED**: SL di luar invalidasi struktur; `buffer = ceil_to_tick(max(tick_size, spread_at_decision, 0.10 × ATR14_Wilder(fully_closed_entry_TF)))`; BUY SL dibulatkan menjauhi entry ke bawah; SELL ke atas. ATR14 Wilder, penggunaan candle telah tutup, **satu posisi aktif per kandidat**, dan fail-closed pada data/quote/spread tak sah disetujui Owner sebagai baseline teknis. Kebijakan posisi *antar-kandidat* bersamaan masih TBD.
- **APPROVED**: entry pada quote yang bisa dieksekusi **setelah** candle konfirmasi selesai (BUY ask; SELL bid). Untuk uji hasil, perhatikan BUY close di bid dan SELL close di ask, spread/komisi/slippage/swap, serta fill gap; tidak boleh fill pada harga close sinyal jika quote berikut tidak tersedia.
- **APPROVED**: ketentuan zona B2/S2 berupa **first visit satu episode**, zona yang pernah breach tidak dapat FRESH lagi, **48 candle H1 sah selesai** sejak konfirmasi, invalidasi hybrid. Intrabar breach distal + buffer → blokir entry langsung. Bila H1 close di luar distal → INVALID; bila H1 close kembali ke dalam sesudah breach → CONSUMED. Pada akhir kunjungan pertama tanpa konfirmasi → CONSUMED. Stop posisi aktif tidak menunggu H1 close.
- **APPROVED**: Hybrid Time Exit dari fill: batas candle lengkap setelah fill **atau** batas menit UTC **atau** batas pra-tutup sesi efektif broker, mana paling awal. Tiga batas memicu **exit intent**, bukan fill tanpa quote; posisi masih terbuka harus dilaporkan bila exit tertunda. SL/TP yang terjadi lebih awal didahulukan.

| ID | Sisi | Struktur/sinyal | Batas candle | Batas UTC | Blokir entry dan upaya exit pra-tutup |
|---|---|---|---:|---:|---:|
| B1 | BUY | Sweep swing low M15 → reclaim M5 | 12 M5 | 90 min | 15 min |
| S1 | SELL | Sweep swing high M15 → reclaim M5 | 12 M5 | 90 min | 15 min |
| B2 | BUY | HH+HL H1 → fresh demand H1 → bullish M15 | 12 M15 | 240 min | 30 min |
| S2 | SELL | LH+LL H1 → fresh supply H1 → bearish M15 | 12 M15 | 240 min | 30 min |
| B3 | BUY | H1 breakout high → M5 retest bullish | 24 M5 | 180 min | 20 min |
| S3 | SELL | H1 breakdown low → M5 retest bearish | 24 M5 | 180 min | 20 min |

Semua waktu pra-tutup dihitung dari **jadwal quote/trade resmi server dan simbol** yang belum diperoleh. Bila tidak tersedia: `BLOCKED_SESSION_EVIDENCE`, bukan menebak dari tick gap.

## II. Aturan entry/SL/TP setiap hipotesis

### B1 — BUY Liquidity Sweep
- **APPROVED**: pilih confirmed swing low M15 sesuai aturan pemilihan level baseline; swing tersebut harus diketahui **sebelum awal candle M5 sinyal**. Pada **satu candle M5 tertutup yang sama**, low menembus swing low, harga ditutup **di atas swing**, serta candle bullish (`close > open`). **Kedalaman minimal satu tick** dipilih sebagai baseline; `low <= swing_low - tick_size` dengan penanganan pembulatan sesuai sumber bid/ask.
- BUY di ask berikutnya; SL di bawah low sweep dikurangi buffer; TP ke swing high/resistance M15 sah terdekat **di atas harga fill**. Tak ada target sah → WAIT. No entry pada quote invalid.

### S1 — SELL Liquidity Sweep
- **APPROVED**: confirmed swing high M15 diketahui sebelum candle M5 sinyal dimulai. Dalam **satu candle M5 tertutup**, high menembus swing high minimal satu tick, close **di bawah swing**, candle bearish (`close < open`).
- SELL di bid berikutnya; SL di atas high sweep ditambah buffer; TP ke swing low/support M15 sah terdekat **di bawah fill**.

### B2 — BUY Trend Pullback
- **APPROVED**: dua confirmed swing high H1 terakhir menunjukkan HH dan dua confirmed swing low H1 terakhir menunjukkan HL, masing-masing pivot H1 2 kiri + 2 kanan. Bila tidak lengkap, WAIT.
- Masuk **fresh demand H1 pada episode first visit**, selama zona masih sah (usia <=48 valid closed H1, belum intrabar breach distal+buffer). M15 candle **menyentuh zona**, `close > open`, dan **close di atas proximal/atas demand**; baru entry BUY pada quote setelah M15 selesai. SL di bawah distal demand/swing pembentuk yang sesuai aturan terdaftar dikurangi buffer; TP level supply/resistance H1 sah terdekat di atas fill.

### S2 — SELL Trend Pullback
- **APPROVED**: dua confirmed swing high terakhir LH dan dua confirmed swing low terakhir LL pada H1; tunggu **fresh supply H1** first visit yang belum breach/expired.
- M15 candle menyentuh zona, `close < open`, dan **close di bawah proximal/bawah supply**; entry SELL pada quote berikut; SL di atas distal supply/swing pembentuk sesuai aturan terdaftar ditambah buffer; TP demand/support H1 sah terdekat di bawah fill.

### B3 — BUY Breakout & Retest
- **APPROVED**: resistance = confirmed swing high H1 2+2 **sebelum bar breakout H1 dimulai**. Bar H1 **telah ditutup** pada `close >= level + 1*tick_size` (breakout body-close, bukan wick-only).
- Hanya **enam candle M5 lengkap pertama** yang dimulai pada/ sesudah close H1 eligible. Satu candle M5 yang sama harus `low <= broken_level`, `close > broken_level`, dan `close > open`. Setelah candle tertutup, entry BUY pada quote berikut. Tiada retest eligible → WAIT:RETEST_TIMEOUT; invalidasi H1 confirmed sebelum entry → WAIT:BREAKOUT_INVALIDATED.
- SL di bawah low retest dikurangi buffer; TP resistance H1 sah terdekat di atas fill.

### S3 — SELL Breakdown & Retest
- **APPROVED**: support = confirmed swing low H1 2+2 **sebelum bar breakdown H1 dimulai**. H1 `close <= level - 1*tick_size`.
- Maksimal enam candle M5 lengkap setelah close H1. Pada satu candle M5 yang sama `high >= broken_level`, `close < broken_level`, dan `close < open`. Entry SELL pada quote berikut; ketidakcocokan/tidak ada retest → WAIT.
- SL di atas high retest ditambah buffer; TP support H1 valid terdekat di bawah fill.

**Catatan:** penulisan tanda `>=` untuk minimal satu tick dan interpretasi wick M5 menggunakan harga bid/ask yang benar harus diuji terhadap kuantisasi tick; transisi pada batas bar yang sama tidak boleh mengambil informasi bar H1 belum tutup.

## III. Parameter yang BELUM lengkap: perlu ditutup sebelum dapat disebut spesifikasi final

| Blocker | Yang harus ditetapkan tanpa melihat hasil P/L | Mengapa masih menghambat |
|---|---|---|
| **G1 Level/swing** | Definisi **latest swing yang masih valid**: TTL/non-zona, hanya level yang belum dibatalkan atau semua confirmed level, pilihan jika beberapa valid, equal pivot, batas lookback maksimum untuk scan | Kalau tak eksplisit, kandidat bisa berbeda pada dua implementasi |
| **G2 Target struktural** | Validitas dan umur target, apakah zona dan swing boleh bercampur; target zona memakai **proximal atau distal boundary**; tie-break newer confirmed; opsi jika target berlapis/overlap | `nearest` tidak unik jika jenis level belum didefinisikan |
| **G3 Demand/supply origin** | Pilihan origin (candle berlawanan terakhir sebelum H1 BOS), seluruh wick vs body, scan/lookback, bila ada beberapa origin atau zona overlap, episode first touch dan harga referensi quote | Definisi zona mentah belum final meskipun first-visit dan umur disetujui |
| **G4 Execution detail** | ATR warm-up, spread invalid/split, tick-size rounding & stops level/freeze, konversi quote ke referensi OHLC, gap, event-order konflik SL/TP/time exit, sesi/trading halt, aturan overlap antar-kandidat | Risiko hasil terlalu optimistis atau ambigu |
| **G5 Breakout/Sweep instance** | Batas umur breakout dan swing setelah konfirmasi, jika dua sinyal dalam satu waktu, satu setup per source ID, penanganan retest/breach intrabar lebih dulu | Potensi duplicate / cherry-pick |
| **G6 Bukti input** | Sumber dev broker dan hash/manifest/tick, clock server→UTC independen, `split.json` dengan gaps, `costs.json` dari broker, identitas server+symbol, `code_sha256` | Tanpa input frozen, registry tak akan membuktikan setup yang diukur |
| **G7 Sesi broker resmi** | `SymbolInfoSessionQuote` **dan** `SymbolInfoSessionTrade` untuk XAUUSD.vx, DST, hari libur, akhir sesi efektif dan timestamp sumber | Tick gap empiris bukan bukti jadwal resmi; preclose masih BLOCKED |
| **G8 Simulator tidak setara** | Port *offline only* seluruh 6 metode, M15, structural TP, no minRR, zona state machine, H1 breakout→M5 retest, ATR adaptif, Hybrid Time Exit dan event-based bid/ask; fixture | Simulator saat ini memakai `target_rr`, `min_rr`, M5+H1 dan fixed `max_hold_bars` — tidak boleh dilabel validasi desain ini |

## III-A. Keputusan D10-K21 — TTL dan validitas swing (APPROVED)

- **M15 confirmed swing berlaku maksimum 96 candle M15 tertutup sejak `confirmed_at`**; **H1 maksimum 72 candle H1 tertutup**. Jika bukti candle kurang/gap, FAIL CLOSED, tidak mengasumsikan swing masih valid. Zona demand/supply **48 candle H1**, dihitung terpisah.
- Support swing low dibatalkan jika **close timeframe asal <= low - 1 tick**; resistance swing high dibatalkan jika **close timeframe asal >= high + 1 tick**. Hanya candle tutup; wick saja tidak membatalkan level. Penilaian selalu pada timestamp sinyal, tidak retroaktif.
- **Khusus B3/S3**, H1 BOS memindahkan sumber level ke status `BROKEN_RETEST_ELIGIBLE` untuk satu upaya dalam maksimal 6 M5, bukan langsung membuang referensi level yang dipatahkan. Level broken tidak lagi menjadi TP resistance/support normal.
- TP terdekat di arah profit setelah fill, tie berdasarkan `confirmed_at` terbaru dan ID deterministik. Untuk B1/S1 target swing lawan M15, B2/S2 target swing H1 lawan atau zona lawan H1 valid, B3/S3 target swing H1 lawan yang belum broken. Harga batas zona proximal dan sumber quote disentuh masih dalam agenda G3 berikut.
- **Status:** D10-K21 approved sebelum preregistration. Perubahan TTL/validasi pasca melihat hasil menjadi hipotesis baru.

## III-B. Keputusan D10-K22 — Pembentukan demand/supply H1 (APPROVED)

**Owner menyetujui paket pembentukan H1 zona untuk B2/S2 (praregistrasi baseline):**

1. **B2 Demand:** close H1 breakout minimal **1 tick** di atas swing high H1 valid yang sudah terkonfirmasi sebelum H1 breakout dimulai. Cari **candle bearish H1 terakhir dalam 12 candle H1 tertutup tepat sebelum breakout**. High sampai low keseluruhan wick candle tersebut adalah fresh demand.
2. **S2 Supply:** close H1 breakdown minimal **1 tick** di bawah swing low H1 valid yang sudah terkonfirmasi sebelum H1 breakdown dimulai. Cari **candle bullish H1 terakhir dalam 12 candle H1 tertutup tepat sebelum breakdown**. High–low wick utuh menjadi fresh supply.
3. Zona hanya berlaku setelah candle BOS H1 ditutup. Origin tidak boleh dipilih dari H1 BOS sendiri atau candle sesudahnya; tanpa origin valid `WAIT:NO_VALID_ZONE_ORIGIN`.
4. Episode **first touch** hanya punya **satu candle M15 yang memuat sentuhan pertama** untuk konfirmasi setelah candle tertutup. B2 candle searah bullish menyentuh zona dan close di atas batas atas demand; S2 bearish menyentuh zona dan close di bawah batas bawah supply. Gagal → CONSUMED, tidak boleh mencobanya lagi. Hybrid distal breach+buffer dan umur 48 valid closed H1 tetap berlaku.
5. TP zona lawan yang valid pada sisi profit: B2 BUY di **batas bawah supply (proximal)**; S2 SELL di **batas atas demand (proximal)**. Bandingkan dengan swing H1 eligible; pilih terdekat dalam arah profit, tie lebih baru terkonfirmasi, tanpa minimum RR.

**Belum dibekukan meskipun inti G3 telah disetujui:** harga BID/ASK untuk memutuskan sentuh/breach, tie-break zona beririsan, aturan quote tepat pada penutupan M15, tick gap dan kesinambungan data, dan implementasi saat sesi berakhir. Hal-hal ini masuk ke **G4**, bukan dianggap persetujuan diam-diam.

**Kontrak eksekusi & rencana memperbaiki simulator:** [SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md](SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md). Keputusan rapat tidak mengizinkan penggunaan simulator saat ini sebagai uji resmi.

## III-C. Keputusan D10-K23 — Simulasi tick kronologis dan enam hipotesis independen (APPROVED)

Owner telah memilih dan mengunci:
- **Replay tick broker sesuai urutan kronologis yang dapat dibuktikan** untuk perubahan status intrabar dan urutan SL/TP/fill; tidak boleh membuat lintasan harga dari OHLC atau memilih hasil yang lebih baik.
- **Referensi sentuhan dan breach zona H1 = BID** sesuai sumber candle broker BID.
- **Entry BUY = ASK, entry SELL = BID; exit BUY = BID, exit SELL = ASK** hanya pada quote yang valid/eksekutabel. Spread aktual dilacak bersama komisi, slippage, swap pada model biaya yang disiapkan sebelum pengujian.
- Bila ketidakpastian tick/urutannya dapat mengubah event transaksi, tandai **`BLOCKED_INTRABAR_ORDER`**; **tidak mengaktifkan fallback OHLC SL-first** ataupun menyimpulkan transaksi ditutup tanpa quote. Blocked harus dilaporkan, bukan disaring diam-diam.
- **Evaluasi keenam kandidat secara terisolasi**, satu posisi aktif per kandidat (D10-K19), tanpa kebijakan netting/hedging portofolio gabungan yang belum disetujui.
- Semua urutan, data dan quote harus dapat diaudit; tidak ada registry/backtest tanpa input sah, code hash serta sesi quote/trade broker terverifikasi. Core G4 disetujui, tetapi detail timestamp boundary, tick-gap/data quality, sumber harga stop/fill, zona overlap, dan stops/freeze broker masih harus ditentukan dan diuji.

**Kontrak rinci dan fixture yang perlu dikembangkan:** [SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md](SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md) (bagian 2A dan 4).

**Remaining blockers:** G3 origin/TTL/first-touch core telah disetujui tetapi overlapping-zone tie belum; G4 edge-case teknis belum; G6 historical development dataset/hash/cost/split belum terverifikasi; G7 sesi resmi MT5 belum tersedia; G8 kode riset belum kompatibel dan belum diimplementasikan. `PREREGISTRATION_BLOCKED`, `NO_BACKTEST`, `HOLDOUT_LOCKED`, `LIVE_OFF`.

## IV. Kriteria siap mendaftar

1. **Spec lengkap:** semua G1–G5 ditetapkan sebagai nilai/aturan yang sama untuk dua sisi hanya jika disengaja; tiap `B1/S1/B2/S2/B3/S3` memiliki `name,symbol,side,regime,playbook,rules,parameters`, `code_sha256`, `spec_version`, alasan WAIT, serta daftar level `discovered_at/confirmed_at`.
2. **Fixture mekanisme lulus** pada synthetic-only: no-lookahead, status zona, minute H1/M15/M5 closed, EMA tidak disisipkan, target tak berubah ketika future bars dimutasi, event-order bid/ask, timeout, DST/sesi/gap, deterministic hash. Tidak membandingkan profit dan tidak membuka holdout.
3. **Dataset valid development-only:** hanya data sebelum **2026-10-13T00:00:00Z** sesuai cutoff riset; verifikasi manifest dan clock, split/gaps serta biaya telah dipraregistrasi; host riset terpisah dari VPS observer; tidak ada forward Stage0 yang digunakan untuk parameter tuning.
4. **Freeze batch bersama:** daftarkan keenam hipotesis pada `registry.jsonl` sebelum P/L kandidat mana pun terlihat; semua variasi selanjutnya adalah ID/hypothesis baru, menghitung Bonferroni `alpha=0.05/N_trials` dan batas maksimal **5/symbol/side**. Jangan memakai registrasi ini sebagai izin order.
5. **Setelah daftar**, jalankan development walk-forward 28 hari, tiga baseline, biaya penuh & sensitivitas 1.5x/2x. Semua hasil termasuk FAIL, NO_TRADE dan data tidak sah tetap dilaporkan. **Holdout tetap terkunci.**

**Keputusan rapat saat dokumen dibuat:** Owner telah menyetujui lima aturan teknis baseline (minimum sweep 1 tick, swing terbaru, TP level terdekat dengan tie terbaru, ATR Wilder 14, satu posisi per kandidat, fail closed). G1–G8 adalah hal yang harus dirinci/ diverifikasi, bukan persetujuan untuk memilih angka berdasarkan backtest.

## V. Status operasional

`DRAFT_SIX_CANDIDATES_PRE_REG_SPEC` · `OWNER_BASELINE_PARAMETERS_APPROVED` · `UNRESOLVED_G1_TO_G8` · `NOT_REGISTERED` · `NO_BACKTEST` · `HOLDOUT_LOCKED` · `LIVE_OFF` · `ZERO_ORDERS`.

Rujukan: `docs/research/VALIDATION_PROTOCOL.md`, `scripts/research/register_setup_hypothesis.py`, `src/katarina/research/setups/{core,simulator,liquidity_sweep,pullback,market_structure}.py`, `docs/maintenance/MT5_SESSION_MAP_20261104.md`, `docs/maintenance/BROKER_SYMBOL_SESSION_EVIDENCE_20261103.md`.
