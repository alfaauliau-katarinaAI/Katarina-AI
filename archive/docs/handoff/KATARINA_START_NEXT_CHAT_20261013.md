# KATARINA AI — START NEXT CHAT

**Checkpoint: 12 Oktober 2026 | Version: V6 | Status: riset-only / WAIT.**

Dokumen ini adalah sumber utama untuk memulai chat baru. Jangan menganggap strategi sudah profitable. Jangan gunakan data 2025–Oktober 2026 sebagai holdout independen karena sudah diteliti berulang kali. **Hanya lakukan pekerjaan baru jika diminta pengguna.**

## Tujuan yang telah ditetapkan

- Pemilihan opportunity terbaik secara simultan dari **maksimum 17 instrumen pilihan yang tersedia di broker** (7 major, 5 cross, XAUUSD, BTCUSD, OIL, US30, US100), tidak mengandalkan satu market; tidak memaksakan transaksi setiap hari. **Riset historis lama** tetap pada 55 pair.
- **Intraday first** sebagai strategi utama. **Scalping hanya opsi ekstrem** yang harus diuji mandiri, dan **default DISABLED** karena hasilnya masih negatif.
- Risk-aware, tidak ada otorisasi pengiriman trading live; ketika data, news, risiko, eksekusi atau evidence tidak cukup: **WAIT**.
- Preferensi komunikasi: bahasa Indonesia, langsung hasil dan status, tanpa penjabaran proses panjang.

## Hasil historis kumulatif (semua model, bukan realized broker P/L)

| Tahap | Sampel / strategi | Avg net R | Profit factor | Keputusan |
|---|---|---:|---:|---|
| Baseline 55 pair | 8.310 event, sampling 1/36 M5 | -0,20509 | 0,7008 | Rugi |
| Structural Entry V1 | 1.241 event | -0,15169 | 0,7741 | Selektif, masih rugi |
| Exit V2 3-pair | 203 event | -0,07575 | 0,8815 | Tolak penerapan universal |
| Semantic Setup V3 | 731 event | -0,14473 | 0,7847 | Definisi setup benar, tetapi masih rugi |
| Daily Multi-Pair V4 | 187 transaksi, 67 hari positif | -0,073 | 0,885 | Return model -3,47% |
| Full M5 Intraday V5 | 658 transaksi, prefilter scanner saja | +0,00556 | 1,009 | Return +0,58% model saja; +0,10R biaya => -14,68% |
| Extreme Scalp V5 | 155 transaksi | negatif | 0,702 | Return -2,58% model; DISABLED |
| **Full M5 + Brain V6** | **565 transaksi** | **-0,03744** | **0,9416** | **Return model -5,4351%; maks DD model 19,6548%** |
| V6 +0,10 R extra cost | 565 transaksi | -0,13744 | 0,8049 | **Return model -17,8946%** |
| V6 control alfabetis | 564 transaksi | -0,03025 | 0,9526 | Return -4,4637%; ranking Brain belum lebih baik |

**V6** telah menguji **55 pair**, memindai **4.841.516 candle M5 tertutup**, menghasilkan **39.691 kandidat scanner**, **1.590 lolos semantic, structural-quality dan keputusan Brain**, dan **565 trade portofolio**. Pada **329 hari pasar** historis: **165 hari profit**, **145 hari rugi**, **19 tanpa transaksi**. Hanya **6/16 bulan** yang positif.

Angka ini diperoleh dengan model risk 0,25%/entry dan asumsi spread/slippage/bar-fill; bukan pertumbuhan modal yang bisa direplikasi di akun real tanpa validasi broker.

## Masalah yang telah ditemukan

1. Label playbook lama mengakui fake pullbacks dan breakout tanpa retest. SemanticSetup memperbaiki definisi closed-candle tetapi *tidak menghasilkan edge secara otomatis*.
2. Banyak kandidat V6 ditolak: no_pullback_location **24.386**, insufficient_structural_room **8.422**, Brain disagreement on direction **2.138**.
3. V5 scanner dan full Brain sebelumnya tidak sepakat. V6 telah menyatukan scanner + pemeriksaan semantik + entry quality + keputusan Brain **sebelum** cross-pair ranking. Hasil gabungannya **lebih buruk** dari V5.
4. Perbandingan ranking V6 melawan pemilihan alfabetis pada jam yang sama **belum menunjukkan keunggulan**.
5. Biaya komisi broker historis **belum terkalibrasi**. Audit akun 120 hari hanya **1 deal** tanpa data komisi per pair. Audit tick spot-check: hanya **13 dari 16** permintaan historis tersedia dekat target waktu pada 4 instrumen.
6. Minimum lot, historical tick fill, margin, swap, conversion P/L dan news blackout historis belum dipastikan. Skenario modal $1k/$5k hanyalah diagnosis, tidak membuktikan implementasi nyata.
7. MT5 broker raw timestamp sekitar UTC+3 pada 12 Okt 2026; histori zona waktu dan DST **belum** divalidasi. Jangan klaim slot laporan sudah UTC/WIB benar.
8. Data historis yang pernah dipakai memutus independensi evaluasi; **0 closed trade baru** dari snapshot awal pengumpulan forward setelah freeze.

## Status kode, pengujian, dan keamanan

- Branch utama GitHub: **main**, repo **alfaauliau-katarinaAI/Katarina-AI**.
- Sebelum checkpoint, HEAD teruji: **5b5d8b4b80ea2a4874e4939019a809856da2b6e3**.
- Lokal VPS **753 unit tests, 96 static tests, 22 integration tests PASS**.
- Di GitHub seluruh 3 workflow: **Operational Hardening, Stage 10-40 Baseline, Body CI PASS**.
- MT5 telah dikonfirmasi **trade_allowed=False**; **0 live orders**. Jangan mengubah Risk Governor atau mengaktifkan live tanpa dasar.
- **Intraday RESEARCH-ONLY**, **Scalp DISABLED**, tindakan saat tanpa data/news/risk terverifikasi: **WAIT**.
- **Brain masih rules-based/explainable**, bukan trained model dengan probabilitas kemenangan terkalibrasi.

## Lokasi penting dalam repository

- docs/research/KATARINA_BRAIN_UNIFIED_INTRADAY_V6_20261012.md
- docs/research/KATARINA_FULL_M5_INTRADAY_SCALP_V5_20261012.md
- docs/research/KATARINA_MULTI_PAIR_DAILY_RANK_V4_20261012.md
- docs/research/KATARINA_ROOT_CAUSE_AND_SEMANTICS_V3_20261012.md
- docs/research/KATARINA_ENTRY_EXIT_V2_AUDIT_20261012.md
- docs/research/KATARINA_ENTRY_BRAIN_STRUCTURAL_55_PAIR_20261012.md
- docs/research/outputs/20261012/brain_unified_intraday_v6_full.json
- docs/research/outputs/20261012/brain_unified_intraday_v6_trades.csv
- docs/research/outputs/20261012/brain_unified_intraday_v6_forward_contract.json
- src/katarina/intelligence/unified_intraday_gate.py
- src/katarina/intelligence/intraday_scalp_research.py
- src/katarina/intelligence/market_decision_pipeline.py
- src/katarina/intelligence/semantic_setup_truth.py
- src/katarina/intelligence/structural_entry_quality.py
- src/katarina/intelligence/research_readiness_gate.py
- scripts/research/backtest_unified_intraday_brain_v6.py
- scripts/research/collect_forward_intraday_v6.py

VPS: **C:\KatarinaDev\ci-research-fresh-20261012** (checkout BERSIH dan tersinkron dengan GitHub main; gunakan ini untuk pekerjaan berikutnya). **C:\KatarinaDev\ci-research** adalah checkout LAMA yang tidak sepenuhnya dapat di-reset akibat akses beberapa file ditolak; jangan gunakan sebagai sumber kerja atau menghapusnya tanpa menyelesaikan masalah izin., **C:\KatarinaDev\brain-runtime\Scripts\python.exe** (runtime dengan MT5), **C:\KatarinaDev\decision-backtest-20261012** (keluaran test), **C:\KatarinaDev\handoff-backups** (snapshot cadangan privat). Jangan upload kredensial, trade account ID, history broker pribadi, cache browser atau file privat ke GitHub.

## Kondisi cleanup

- Main GitHub sebelum checkpoint punya **1.054 item tree**, tidak ada tracked file >1 MB maupun folder cache Python/node_modules/venv/pyc yang ditemukan.
- Branch penelitian dan web masih punya commit *diverged/unmerged* dan harus dipertahankan: **research/brain-intelligence-admission-20261011**, **research/portfolio-regime-audit-20261011**, **web/standalone-extraction**. Jangan menghapus pekerjaan yang belum merged.
- Workspace VPS lama sempat tidak sinkron dengan main. Snapshot recovery privat telah diverifikasi di **C:\KatarinaDev\handoff-backups\ci-research-pre-github-sync-20261012.zip** (3,483 MB, 963 berkas, SHA256 b2dfcfcc78476c4d4c89c3a58026d7980b8c3ee1083b06eb3fe190cdf6f58bb6). Ini bukan artefak publik.
- VPS hanya ~2 GB RAM. Layanan MT5, Chrome dan website jangan dihentikan atau datanya dihapus tanpa perintah khusus. Cache unit/integration/temp regenerable aman dibersihkan.

## Pekerjaan berikutnya bila pengguna memerintahkan

1. Bekukan konfigurasi Brain V6 yang konsisten sebagai **research baseline**. Jangan membiarkan pipeline skrip dan production gate berbeda.
2. Kumpulkan observasi **forward yang benar-benar baru** setelah freeze, lengkap dengan biaya, eksekusi, batas margin/lot dan validitas berita. Jangan menyatakan riset atas tape 2025–Oktober 2026 sebagai OOS.
3. Uji robustitas lintas pair berdasarkan expectancy R net-of-cost, PF, DD akun, korelasi exposure, win days vs no-trade days, dan kestabilan regime/bulan.
4. Uji scalp secara independen dan tetap disabled hingga menghasilkan bukti berulang yang sah.
5. Jalur LIVE hanya bisa dipertimbangkan setelah bukti independen yang kuat, tanpa mengubah risk governor sembarangan.

**Kalimat chat baru:** "Lanjutkan KATARINA dari KATARINA_START_NEXT_CHAT.md di main GitHub. Cek status saja dahulu; jangan mengerjakan apa pun selain yang saya perintahkan."

**Tidak ada profit harian yang dijamin. Keputusan NO_TRADE dapat menjadi keputusan yang optimal.**

## 8. HASIL CLEANUP TERAKHIR (VERIFIKASI 12 Oktober 2026)

- **GitHub:** checkpoint V1–V6 di main; tidak ada tracked file >1 MB dan tidak ada cache build/test tracked. Ketiga branch lama dipertahankan karena commit unik belum merged. Tidak ada data riset atau commit dibuang.
- **VPS kode:** bersih pada checkout baru **C:\KatarinaDev\ci-research-fresh-20261012**; main GitHub SHA **0e643838b3fe546ba68e0c9789ada814dd1b157a** saat clone. Git status clean dan handoff tersedia. Test pada fresh checkout: **752 unit, 96 static, 22 integration PASS**.
- **VPS lama:** akses ditolak pada beberapa file checkout **C:\KatarinaDev\ci-research** sehingga reset/rename terhenti. Checkout lama sengaja tetap disimpan, bukan diam-diam dihapus atau dinyatakan bersih. Snapshot ZIP sebelum percobaan reset telah diuji integritas dan disimpan privat.
- **Safe cleanup:** **66 cache Python/test regenerable, sekitar 4,465 MB**, dihapus dari enam direktori code workspace, tanpa error. Skrip helper sementara untuk perpindahan yang tidak lagi dibutuhkan dibersihkan. Data tick/historical broker, hasil penelitian dan website tetap utuh.
- **VPS status:** RAM tersedia **220 MB dari 2.047 MB**, ruang disk tersedia **9,32 GB**; **tidak ada backtest aktif**, MT5 tetap berjalan. RAM tetap rendah terutama karena aplikasi MT5 dan Chrome yang sengaja tidak dimatikan.
- **GitHub Body CI** pada commit checkpoint **0e643838** sukses. Lihat laporan cleanup privat **C:\KatarinaDev\state\handoff_cleanup_20261012.json** untuk daftar cache.
- Ini **bukan** janji semua VPS menjadi ringan sepenuhnya: RAM tidak akan meningkat signifikan tanpa menutup aplikasi atau menambah RAM. Aplikasi aktif tidak disentuh untuk menghindari gangguan.

## 9. BATAS SCANNER BARU (12 Oktober 2026)

- Scanner operasional dan default replay V6 berikutnya memakai **maksimum 17 instrumen**: 7 major FX, 5 cross FX, XAUUSD, BTCUSD, oil, US30, US100. Semua simbol tetap diperiksa terhadap katalog broker aktif; yang tidak ada/disabled otomatis dilewati, tanpa membuat simbol palsu.
- Pada audit read-only VPS, **17/17 tersedia dari katalog 74**; oil = `XTIUSD.vx`, US100 = `NAS100.vx`. Tidak ada order dikirim.
- Resolver dan tes ada di `src/katarina/intelligence/broker_scan_universe.py` dan `tests/unit/intelligence/test_broker_scan_universe.py`; rincian di `docs/operations/BROKER_ADAPTIVE_SCAN_SCOPE_20261012.md`.
- Data hasil V1–V6 tetap arsip 55 pair dan **tidak boleh dipresentasikan sebagai performa 17 instrumen**. Risk Governor, permission live, dan hasil forward independen tidak berubah.


## 10. ADAPTIVE RESEARCH DI GITHUB ACTIONS (12 Oktober 2026)

- Jalur adaptif baru: src/katarina/intelligence/adaptive_walkforward.py dan adaptive_strategy_library.py, plus tes dan workflow .github/workflows/adaptive-brain-research.yml. Detail di docs/research/KATARINA_ADAPTIVE_RESEARCH_V7_20261012.md.
- Komputasi dan test di runner GitHub, bukan VPS. Dataset GitHub dari paper trade V6 digunakan untuk diagnosis retrospektif subset simbol, bukan backtest profit metode baru.
- Memori performa belajar hanya setelah exit paper dan memisahkan BUY/SELL, instrumen/keluarga dan kondisi biaya. Risiko hanya simulasi; Risk Governor produksi tetap.
- TREND_PULLBACK, BREAKOUT_RETEST, LIQUIDITY_SWEEP_RECLAIM dan RANGE_MEAN_REVERSION adalah prototipe *hipotesis*, tidak boleh diberi P/L milik trade V6.
- Data 2025–2026 telah diteliti sebelumnya; walk-forward kronologis ini bukan bukti holdout independen. Privat data broker tetap di luar GitHub.
- Output produksi tetap WAIT. Tidak ada pengaktifan LIVE atau penulisan file pada VPS.


### Verifikasi hasil V7 oleh runner GitHub

- Commit kode: f1aa89aefe7f5c1b54d8e777156d10a8faa3f997. **Keempat workflow GitHub PASS**, termasuk Adaptive Research (#38200671468).
- Subset arsip V6: 334 paper trade historis pada 14 instrumen yang pernah tereksekusi dalam model V6; bukan keseluruhan histori kandidat 17 instrumen.
- Adaptive model pada biaya dasar: 70 trade, return **-2,7752%** (pembanding V6 subset kondisional: **-0,3066%**). Biaya tambahan +0,10R: 44 trade, return **-4,1422%**. Belum profitable.
- Prototipe metode alternatif belum punya evaluasi P/L dari candlestick historisnya masing-masing. Jangan menyatakan strategi V7 lolos atau mengaktifkan live.
- Artifact riset tersimpan dalam run Actions (retensi 7 hari). VPS tidak diubah atau ditulis.


## 11. STRATEGY TOURNAMENT CANDLE ASLI — GITHUB RUNNER (12 Oktober 2026)

- Runner baru .github/workflows/public-strategy-tournament.yml, kode scripts/research/public_market_tournament.py, tes tests/unit/intelligence/test_public_market_tournament.py, dokumentasi docs/research/KATARINA_STRATEGY_TOURNAMENT_V8_20261012.md.
- Pengujian diarahkan untuk keluarga Trend Pullback, Breakout Retest, Liquidity Sweep, Range Mean Reversion; BUY dan SELL dipisah. Pilot pertama EURUSD + XAUUSD menggunakan M1 BID/ASK **publik** dari Dukascopy, bukan file privat broker VPS, dengan agregasi M5/H1 tertutup dan entry candle berikutnya.
- Broker live, Risk Governor, penulisan dan restart VPS semuanya tidak disentuh. GitHub runner menggunakan permission contents:read. Arsip M1 mentah tidak ditulis ke GitHub, hanya diagnostic summary dan modeled paper events sementara.
- Status edge/profit harus mengikuti hasil runner, bukan klaim sebelum tes. Semua historical paper tetap RESEARCH-ONLY / WAIT.


### Uji pertama Strategy Tournament V8 — diverifikasi GitHub (12 Oktober 2026)

- GitHub Actions PASS: https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38202938538
- Data publik M5 referensi (bukan BID/ASK nyata broker), rentang 2026-08-17 s.d. 2026-09-08: EURUSD 4894 M5, XAUUSD 4683 M5.
- Empat metode, BUY/SELL terpisah: 674 transaksi simulasi yang **boleh overlap**, semua 8 kelompok method/side mean R negatif. Pool -0,163411 R, PF 0,73002 — **bukan return portofolio investable**.
- Dukascopy BID/ASK asli tidak berhasil diambil via runner karena TLS timeout. Sumber alternatif M5 berhasil, dengan asumsi spread model yang harus dipisah dari evidence broker. VPS tidak ditulis.
- Belum ada strategi profitable yang tervalidasi; 15 instrumen lain belum diuji pada pipeline baru. Tetap RESEARCH-ONLY/WAIT, live trading disabled.


### Ekspansi uji V8-B (GitHub-only)

- 11 sumber M5 publik terverifikasi: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP, EURJPY, XAUUSD, USOIL, US30, NAS100. Enam belum ada sampel M5 cocok: USDCHF, NZDUSD, GBPJPY, AUDJPY, EURAUD, BTCUSD (bukan berarti broker tidak punya).
- Runner GitHub Actions dipecah 4 kelompok, peristiwa Juni–Agustus 2026, dengan ringkasan per strategi/BUY-SELL per bulan dan +0,10/+0,20 R biaya asumsi.
- Model tetap menggunakan OHLC referensi publik, **ASK/spread hanya asumsi**; belum broker-tick-validated maupun independent unseen holdout.
- Ada agregator hasil sementara; research-triage gate mensyaratkan minimal 20 trade/bulan dan PF >=1,20 serta rata-rata R >=+0,10 pada ketiga bulan setelah +0,10R biaya tambahan. Lulus triase BUKAN izin live.
- VPS tidak diubah. Angka baru harus diisi setelah runner benar-benar PASS.


### VERIFIKASI AKHIR V8-B — 11 pasar / Juni–Agustus 2026

- RUNNER PASS 5/5: https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/38204091035 . Body CI + Operational Hardening + Stage 10-40 Baseline commit sama juga PASS.
- 11 sumber M5 publik = 3995 paper event **overlap**; 88 grup strategi/instrumen/BUY-SELL di-screen, **0 lulus** kriteria konsistensi 3 bulan setelah biaya tambahan +0,10R.
- Positif tetapi **tidak signifikan**: AUDUSD 4 trade +0,386R, USDCAD 3 trade +0,087R, EURJPY 19 trade +0,126R. XAUUSD 1331 trade -0,1729R, Oil 390 -0,2204R, US30 934 -0,2428R, NAS100 1267 -0,2298R.
- Detail angka dan batas interpretasi di docs/research/KATARINA_STRATEGY_TOURNAMENT_V8_20261012.md. Data tersebut **bukan** BID/ASK broker, spread simulasi dan tidak lolos holdout baru. Enam simbol lain belum punya sampel M5 publik setara.
- Status resmi: RESEARCH-ONLY / WAIT. Tidak ada promosi strategi, order live, write VPS, atau perubahan Risk Governor.


### V9 — broker-read actual M5 + spread, TWO new entry methods (12 October 2026)

- Read-only broker diagnostic on **17 broker symbols**, period June–August 2026; run script `scripts/research/broker_entry_diagnostics_v9.py` (sha `0b300ca`), loaded directly in VPS Python memory, **no VPS files written**.
- 6,557 overlapping modeled events: V8 4329, new V9 2228; mean baseline **-0.150738R**, extra cost +0.10R **-0.250738R**. 0 groups meet robust all-3-month screen, NOT profitable and NOT independent OOS.
- FX M5 spread/ATR median often >0.50; EURGBP 1.57396, oil XTIUSD 0.81395. This calls for cost-aware higher timeframe research, not raising risk.
- Two XAUUSD SELL methods positive only very weak after cost stress, fail monthly consistency, not production eligible.
- Sanitized full aggregate: `docs/research/outputs/20261012/broker_entry_v9_aggregate_sanitized.json`. Report: `docs/research/BROKER_ENTRY_DIAGNOSTICS_V9_20261012.md`.
- GitHub Actions V9 safety and Body CI PASS. No real orders, VPS file edits, private datasets, Risk Governor changes or live authorization. Continue RESEARCH-ONLY/WAIT.


### V10 — Multi-timeframe M15/H1, RR SL risk, broker M15-H4 (12 Oktober 2026)

- Kode riset terisolasi: `scripts/research/broker_multitf_risk_v10.py` at commit `8778c7d`. Menjalankan broker read-only via source in-memory VPS; VPS files/services tidak disentuh. Periode TRAIN Juni-Juli, DIAGNOSTIC Agustus-September 2026 (sudah pernah diteliti: BUKAN unseen holdout).
- 1264 kombinasi asset/timeframe/entry/SL/TP, 9 lolos TRAIN, **0 lolos diagnostic**. Semua belum profitable robust. 13604 kandidat sinyal mentah.
- Simulasi risiko +0,10R biaya tambahan: 0,10% risk 1 posisi -4.0915%, 0,25% risk 1 posisi -7.1036%, 0,50% risk 1 posisi -8.1869%. Risk Governor produksi TIDAK DIUBAH.
- Laporan: `docs/research/BROKER_MULTITF_RISK_V10_20261012.md`. Agregasi mesin tanpa raw broker bars `docs/research/outputs/20261012/broker_multitf_risk_v10_aggregate_sanitized.json`.
- Tetap WAIT/RESEARCH-ONLY, no live orders, no broker data privat upload, no VPS write, tidak mengubah struktur utama KATARINA.


### Final single-study tick verdict, 12 Oktober 2026

- Repo audit: `scripts/research/frozen_xau_sell_tick_verdict.py`; records immutable pinned V9 entry logic.
- XAUUSD SELL Sep15–Oct09 broker BID/ASK ticks:
  TREND_EXPANSION_V9 = 19/21 tick-complete, after-cost +0,310727R,
  PF 1,63904, **PAPER-OBSERVE ONLY** (small, historical, no unseen OOS).
  SWEEP_2C_CONFIRM_V9 = 28/31 complete, -0,403243R,
  PF 0,49123, **REJECT from live-candidate consideration**.
- June–August MT5 historical tick returns empty on sampled dates;
  they were not falsely declared tick-validated.
- Document: `docs/research/FROZEN_XAU_SELL_TICK_VERDICT_20261012.md`.
  Machine result: `docs/research/outputs/20261012/frozen_xau_sell_tick_verdict_aggregate.json`.
- Final project action: **STOP parameter churn, NO LIVE, freeze candidate.
  Collect truly prospective independent paper results before any
  further deployment discussion**. No change to core, VPS files,
  production Risk Governor, orders, MT5 settings.


### Context-based decision intelligence, 12 October 2026 (actual implementation)

- Native module `src/katarina/intelligence/contextual_decision_intelligence.py`
  with resolved prospective outcome memory, news-policy provenance,
  market regime and friction, causal clock, risk veto and reasons for WAIT.
- Existing `MarketDecisionBrain.evaluate_contextually` is an
  **opt-in native research method**. Old `evaluate`, production
  Brain, scanner, risk governor, MT5 trade gateway, dashboard
  **unchanged**. No live auto activation.
- 17 deterministic unit tests passed with safety workflow, full
  Body CI and operational baseline PASS on code SHA `cb9a1f2`.
- Actual broker-read 3-symbol contextual snapshot at 05:50 UTC
  (2026-10-12) returned XAUUSD=TRANSITION/WAIT,
  EURUSD=SIDEWAYS/WAIT, NAS100=SIDEWAYS/WAIT.
  News connector NOT CONNECTED and prospective outcome ledger EMPTY.
  Broker raw epochs appear UTC+3 **now** (confirmed across 3
  symbol ticks), historical DST alignment not verified. Probe aligned
  current read-only snapshot only; never use offset for live/historical
  backfill without separate verification.
- Probe: `scripts/research/probe_contextual_decision_broker.py`.
  Report: `docs/research/CONTEXTUAL_DECISION_INTELLIGENCE_20261012.md`.
- No VPS writes and no live orders. No claim of profitable model or
  LLM-only forecast. More historic parameter churn is not authorized.


### 12 Oktober 2026 — single autonomy research pipeline
- Current routine source checkpoint `c1c608ba1641b82f0e46567d04437cafab45bfcd`.
- One active VPS task `Katarina-MarketBrain-Observer`,
  invoking `scripts/ai/run_contextual_market_observer.py` every 5 min;
  legacy Decision/Analog observer tasks remain disabled.
  Retry 2 times after failure, IgnoreNew/worker.lock.
- 17 broker instruments scanned; current output 17 WAIT,
  open virtual shadow 1, resolved sampled virtual 1,
  no actual MT5 orders. This is **research only**.
- Fed/ECB/BoE full-article policy provenance and CNBC full-body
  financially relevant media context share one private SQLite DB.
  Unverified secondary stories can never authorize execution.
- New virtual shadow positions: symbol/method/side/regime, spread,
  structural stop/target, after-cost **modeled 0.15R penalty**;
  one virtual exposure at a time, 8-minute observation-gap invalidation,
  5-loss 24h reversible virtual pause, and descriptive memory.
  **Cannot promote virtual to broker-verified ResolvedExperience.**
- Broker read-only native lot/margin/profit calculators usable
  on 17/17 symbols; real commission/slippage/cent risk not proven.
- GitHub Body CI successful, run 38258819050 (includes
  autonomy synthetic-safety artifact). No new automatic CI fanout.
- Report: `docs/operations/AUTONOMY_READINESS_20261012.md`.
- Still NOT full autonomous live trader; missing independent forward
  evidence, verified costs and explicit governed live authorization.

### 12 October 2026 — native Market Brain replay and VPS cleanup
- Reused existing MarketDecisionBrain V3 and adaptive_walkforward with point-in-time M5/M15/H1 broker replay. No duplicate brain, cron, execution gateway or live order.
- Five broker markets Oct 5–12 historical: 2,926 reviewed signal instants, 194 hypothetical price-path candidates; 109/40/39 train/validation/test, 6 purged/embargoed; adaptive selected 1 (-0.371R modeled), WAIT 193.
- Actual historical BID/ASK, fees, fills, historical DST and contemporaneous news not verified; all research only, not independent OOS or real PnL.
- Cost stress of 0.05/0.15/0.30R on all candidates, grouped per method / symbol / regime. See private VPS JSON native-market-brain-replay-private.json.
- CI Body PASS run 38265389941. Report: docs/research/NATIVE_MARKET_BRAIN_REPLAY_20261012.md.
- Closed orphan dedicated headless Chrome QA only, removed 69.17MB temp profile + 33 Python cache dirs 2.2MB; free RAM ~441MB -> ~505MB sampled. Interactive browsers, MT5, DC, services untouched.
- Single existing observer temporarily paused only for replay and re-enabled afterward; other observer jobs disabled.
- Profitability not established; no live activation.

### 2026-10-12 — native-brain BID/ASK tick validation
- Current implementation: `src/katarina/intelligence/causal_tick_reconciliation.py` and `scripts/research/run_native_brain_tick_reconciliation.py`; no second brain or observer.
- SOURCE BIAS FIX: `causal_market_replay.py` freezes `all_technical_proposals` BEFORE any later OHLC outcome, so samples are not preselected by future label completion. Dedicated unit test checks unlabeled candidates retained.
- Source code SHA `c75dd8e23ab7a2ab8c5156348124fc27f8c64ba5`: GitHub Body CI PASS run 38274053823.
- 5 live-available broker symbol archives: 228 pre-outcome native technical proposals, 193 historical OHLC proxy labels, 50 time-balanced pre-outcome tick-audited proposals, 31 BID/ASK complete, 16 excessive entry spread, 2 quote gaps, 1 incomplete exit.
- 31 valid quote-simulated outcomes after EXTRA ASSUMED 0.15R stress: mean -0.166634R, PF 0.63424, 13 positive 18 negative; 10 SL/19 TIME/2 TP. Only October 2026; no independent OOS or broker fill evidence.
- Regime/method root causes and per-month scorecards private file `C:\KatarinaDev\artifacts\contextual-observer\native-brain-tick-reconciliation-private.json`. Main docs `docs/research/NATIVE_BRAIN_TICK_RECONCILIATION_20261012.md`.
- RANGE_FADE especially negative and often spread-blocked. TREND_PULLBACK SELL/ BREAKOUT_RETEST SELL superficially positive but only 8/4 quote-completed samples: no promotion.
- Actual broker deal history 2026 found 1 account record with no symbol, insufficient to calibrate realized commissions. No live trading, no production Risk Governor changes.
- 5-minute canonical observer restored after temporary pause; two redundant observers remain disabled.

### 12 October 2026 — UTC quote clock and 15min journal repaired
- Latest MT5 server tick had +3h and 10–15s extra lead; 15min quote journal previously marked 53 missing. New causal_broker_quotes uses real broker historical UTC prices up to decision time and due-window [due,due+120s] first BID/ASK to reconcile.
- All 53 old missing samples recovered from actual broker quote history with distinct BROKER_TICK_RECOVERED status and private SQLite backup; never label these as forward broker trades or profits.
- GitHub Body CI success run 38278103654, code SHA cea5b2925ada1aae4844fa6e666bea7951b15138; 35 VPS unit tests pass; XAUUSD actual historical tick in-memory journal test passed.
- Original one observer running and legacy two observer tasks disabled. 17-sym snapshot healthy, past-only quote ages 0.01–11.85s, order count 0. Full doc docs/operations/SINGLE_CONTEXTUAL_OBSERVER_20261012.md.

### 12 Okt 2026 — canonical MT5 UTC event time implemented
- Code source SHA `b70d9a09d5a2d419f333c84115dbba01124df745`, Body CI PASS run `38279655126`, 58 local unit tests pass.
- MT5 historical tick `time_msc` UTC is canonical per-symbol decision clock; VPS UTC only audit, scheduling and causal freshness ceiling.
- Closed M5/M15/H1 bars filtered strictly by the verified MT5 tick time, not Windows wall clock; policy/news/Brain as_of uses event time.
- 15-minute markout deadline and virtual 2-hour quote holding horizon anchored to original broker tick timestamp (no invented fills).
- VPS smoke 17 symbols, 0 sensor failures, 17 WAIT, zero broker orders; example XAU tick 16:46:51.800Z vs VPS wall 16:46:52.111Z, M5 closed 16:45Z.
- Single observer enabled, prior Decision and Analog observers disabled; no production Risk Governor or order authorization changed.
- Full operational note in docs/operations/SINGLE_CONTEXTUAL_OBSERVER_20261012.md.

### 13 Oct 2026 — 17-instrument two-window native Brain research
- Codes: `directional_consensus.py` added side-specific closed M5/M15/H1 support vs counterevidence; existing Brain V3 suppresses strongly contradictory trend/pullback technical signals as WAIT only, never permits a new broker order. ContextualDecision exports fields to existing `latest.json`.
- Broker `copy_rates_from_pos` historical M5 signal bar spread points multiplied by symbol point, replaces default 0.04 ATR assumed spread in causal backtest (still NOT real next-open BID/ASK fill).
- 4 sequential Oct broker batches + 4 Sep historical window batches, each 3–5 symbols bounded to protect VPS memory, all 17 distinct symbols per window.
- **Sept 17,669 conditions, 908 modeled labels, zero adaptive selections. Oct 18,970 conditions, 1,065 labels, 3 adaptive selections total -1.284R (modeled). Combined 36,639 evaluations and 1,973 labels. All 8 method+BUY/SELL groups negative in BOTH retrospectively inspected windows after 0.15R extra cost assumption.** Do not fit a winner on these dates; no valid profitable strategy identified.
- 17-symbol one-pass contextual observer smoke after code changes: 0 errors, 17 WAIT, 0 orders; directional_alignment populated in same JSON context. Existing one observer restored, two legacy observers disabled.
- Latest code SHA d621ea685512a7a4072426776a5aacd9c17a8773, GitHub Body CI PASS run 38290257969. Audit `docs/research/17_MARKET_DIRECTION_EVIDENCE_SEP_OCT_20261013.md`.
- VPS free RAM sampled ~138MB after historic tests; keep historical tests sequential, do not kill active Chrome/MT5/DC. No live permission, no new cron.

### 2026-10-13 — Historical root-cause forensic audit completed (17 pairs)
- Source code e21e0e96d60549e7656b28f46cc93e5445564fda, GitHub Body CI PASS 38293407912. Single MT5 observer smoke 17/17 instruments, 17 WAIT, 0 real orders, canonical MT5 timestamp.
- Fixed first M5 bar SL/TP omission and premature 2-hour time-exit censoring in causal_market_replay. These change baseline counts; old and new figures are not comparable as an improvement claim.
- 8 bounded sequential brokers M5 retrospective Sep/Oct: 36,736 as-of closed candle decisions, 2,567 pre-outcome technical candidates, 1,964 resolved OHLC-proxy labels, 603 censored (no fabricated outcome).
- Among 1,964: 1,098 SL (520 first 15m), 813 TIME, only 53 TP, 1,513 losing post assumed +0.15R cost, mean -0.46436R PF 0.36227 for all hypothetical candidates not portfolio. Both inspected windows negative for every of 8 playbook+BUY/SELL groups.
- 1,083/1,964 have signal-bar-spread >=20% simulated next-open stop-risk; median 23.584%; 815 >=30%. RANGE_FADE SELL: 703 n, mean -0.620R, 527 STOP and median spread/risk 40%. EURGBP worst by aggregate proxy, XAUUSD negative even with median spread/risk 3.6%. Fullbar unsequenced median favorable 0.23R vs adverse 1.026R; do not interpret as chronologically observed fills.
- Added DEFAULT conservative spread/risk budget 20% in MarketDecisionBrain V3 as WAIT veto ONLY, exposed in contextual card. Not tuned to optimal alpha; no live promotion.
- Reproducible code closed_bar_failure_forensics.py + aggregate_closed_bar_forensics.py; private reports C:\KatarinaDev\artifacts\contextual-observer\katarina-verified-forensic-17-market-sep-oct.json plus batch1..4 sept/oct. Public audit docs/research/KATARINA_ENTRY_FAILURE_AUDIT_20261013.md.
- Next: predeclare substantive alternate entry/exit hypotheses (range sweep+reclaim, shorter breakout invalidation, pullback confirmation, time-horizon alternatives) and validate ONLY on new untouched periods and actual broker tick/fees. Historical policy/news cannot be hallucinated. Risk Governor stays locked; no second brain, no new cron.

### 2026-10-13 — Native semantic setup gate enforced; 17-symbol inspection
- GitHub source SHA 51e7725ab5e2a0da00a6b6b83802da302afbb103, Body CI PASS run 38294648480; VPS 54 targeted unit tests PASS.
- Previously MarketDecisionPipeline semantic_setup computed but MarketDecisionBrain V3 did NOT enforce it. It now reuses native `CausalSetupValidator` as a HARD VETO on technical BUY/SELL if named playbook pattern unconfirmed; invalid semantic evidence fails closed. Existing ContextDecision exports `pattern_semantically_confirmed`, `pattern_semantic_blockers`.
- Read-only October 17 markets, 4 bounded sequential MT5 spread/closed-bar batches after gate: 31,139 evaluation instants, 158 OHLC-labeled candidate setups (+10 censored), adaptive selected 0, weighted modeled mean -0.2775R under 0.15R extra assumed cost. Individual tiny positive subgroups NOT robust, do not promote or claim edge.
- One MT5 observer smoke 17 symbols, 17 WAIT, 0 live orders, 1 semantic pattern confirmed in snapshot; canonical observer restored, legacy observers stay disabled.
- Private files `C:\KatarinaDev\artifacts\contextual-observer\semantic-replay-oct-batch1..4.json`, `semantic-oct17-research-private.json`. Public full audit `docs/research/NATIVE_SEMANTIC_VETO_AUDIT_20261013.md`.
- Next research is precommitted novel range sweep/reclaim target midpoint, tighter structural breakout retest and confirmed pullback logic, tested on untouched tick BID/ASK dates and actual costs; do NOT optimize existing inspected Sept/Oct, NO LIVE.

### 13 Okt 2026 — 3 precommitted alternative entry/exit rules + exhaustive Aug 2026 quote audit
- Code frozen `5bc2502d6c28c2b45a17cd3517b5823318beaf4c` BEFORE requesting Aug 2026 data. Rule-only research `precommitted_setup_research.py`: real prior-range sweep+reclaim target midpoint, H1/M15-aligned corrective pullback resume to H1 structural target, actual previous breakout/current retest to measured range projection. No production AI Brain modifications, no order actions.
- Run `run_precommitted_aug_setup_research.py` Aug10..Aug21 intended UTC, all 17 MT5 .vx instruments in 4 bounded sequential groups, 47,225 evaluated, 161 prelabel hypotheses, 157 OHLC closed outcomes, 4 censored, OHLC mean -0.308641R PF .594147 at +0.15R assumed cost.
- Re-ran with `--audit-all` **161/161** using REAL historical broker BID/ASK quote paths; 157 tick simulations fully valid, 1 reference raw M5 missing, 3 exits incomplete; mean -0.315584R PF .593206, 98 stop/31 TP/28 TIME. These are NOT real broker fills/commissions.
- Tick method/side n and mean (extra hypothetical +0.15R): range sweep BUY 15/-0.515, range sweep SELL 18/+0.410 PF1.712 (statistically uncertain; 9 win/9 lose; naive bootstrap bounds include zero), pullback BUY 25/-0.461, pullback SELL 16/-0.004, breakout retest BUY 41/-0.735, SELL 42/-0.178. 131/157 cases from XAU/NAS100/US30, so not broad diversified edge.
- Brokerage trade commission, realized slippage, actual fill, historical DST, untouched forward OOS NOT verified. Do not promote winner from August data. Code for audit aggregate `aggregate_precommitted_aug_research.py`, VPS private result `C:\KatarinaDev\artifacts\contextual-observer\precommitted-Aug2026-17market-exhaustive-ticks.json`.
- Repo detailed report `docs/research/PRECOMMITTED_AUG_2026_ALTERNATIVE_ENTRY_EXIT_BIDASK_AUDIT.md`, CI PASS run 38297032416 on code SHA fe64934d081429e6a760af79a5ca7f3f47e5c5e3; 23 VPS tests PASS. Main observer restored, original 2 old observers disabled; no live orders.
