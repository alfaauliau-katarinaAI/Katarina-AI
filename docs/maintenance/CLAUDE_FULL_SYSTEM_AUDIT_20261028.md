# KATARINA AI — audit seluruh sistem dan handoff eksekusi untuk Claude

**Snapshot audit: 28 Oktober 2026, sekitar 03:43 WIB (27 Oktober 20:43 UTC).**
**Jenis:** audit faktual kode, dokumen, GitHub dan VPS read-only; bukan izin promosi.
**Prioritas baca:** ringkasan ini → `docs/PROJECT_STATUS.md` → `docs/ROADMAP.md` bagian 1–7 dan R0/R5/R7 → detail PR.
**Status kewenangan:** Level 0 / RESEARCH ONLY, LIVE OFF, tidak ada order DEMO ataupun riil.

## 0. Kesimpulan eksekutif

**Sudah terbukti:** arsitektur satu otak mempunyai boundary order disabled; pengawas MT5 asli dengan branch gabungan mampu membuka koneksi lokal yang diverifikasi dan mengamati 5 instrumen tanpa order; Windows VPS kini NTP-synchronized; CI gabungan Body/Ubuntu/Windows hijau; sistem uji kontinu punya ledger terpisah, kode terkunci per SHA, dan audit harian.

**Belum terbukti:** Tahap 0 lulus 10 hari bursa; cakupan 7 simbol inti; ketahanan reboot tanpa login; 3 uji reconnect dalam *ledger baru*; tick historis per hari serta rekonsiliasi; sertifikasi UTC/DST **historis independen**; 100% WAIT bisa dibuka dengan bukti valid; expectancy positif setelah biaya; holdout; order DEMO/riil; keamanan profil risk untuk uang nyata.

**Jangan samakan:** fitur tersedia ≠ uji sintetis lulus ≠ broker real satu siklus sukses ≠ 10 hari sehat ≠ alpha menguntungkan ≠ otorisasi DEMO/LIVE.

## 1. Sumber kebenaran, branch, dan rilis

| Area | Bukti/status per audit | Keputusan Claude |
|---|---|---|
| Produk di Windows VPS | `C:\Katarina\code` pada main `d8b003a99cbdea4755338da4782f0216ac937f78`. Jangan menyatakan WP12/9b telah merge ke main. | Main tetap tanpa perubahan saat ini. |
| Kode pengujian MT5 | Worktree **frozen** `C:\Katarina\_roadmap_validation\stage0-combined-acceptance-20261028`, HEAD lokal `1a04a8107b046f88401a33258ccfbf7882715d5c`, tree SHA `a48d8c3fad957f6d6236dbbc4f1dbe7168069d24`. | **Jangan edit file tracked pada worktree ini saat 10 hari berlangsung**; perbaikan harus lewat branch baru + keputusan restart periode apabila mengubah observasi. |
| PR gabungan | [PR #208](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/208), draft, HEAD `a13cbc0e490990460bb0bbddd4904428400f5451`, base PR #206; tree GitHub IDENTIK dengan tree lokal di atas. | CI gabungan run **#40574960082 SUCCESS** (Body/Ubuntu/Windows); perlu review Claude atas gabungan sebelum merge. |
| PR lain | [#206](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/206) (WP12/9b/8a, draft, open); [#207](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/207) (clock/NTP, draft, open); [#195](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/195) (WP8a draft open); [#204](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/204) (WP12 draft open); [#205](https://github.com/alfaauliau-katarinaAI/Katarina-AI/pull/205) (WP9b open, bukan draft). | Jangan merge semua PR bertumpuk tanpa analisis duplikasi. PR #208 adalah kandidat INTEGRASI di atas #206, bukan pengganti tinjauan masing-masing. |
| Repo dan CI | Kandidat: 850 tracked files; 246 source files di `src/katarina`; 219 files di tests; 78 scripts; 11 workflow. Manifest **MATCH 306/306**, PASS_PROMOTION_GATE, local suite target **78 tes dijalankan (77 lulus, 1 skip)**; Body/Ubuntu/Windows CI sukses. | Angka file/tes bergantung revision; jangan bandingkan jumlah tes lokal tertarget dengan keseluruhan CI. |
| Pengamatan Stage 0 | Task `Katarina-Stage0-10Day-Observer` Running, terpisah dari task lama yang `Ready`; state baru `C:\Katarina\state\stage0-10day-20261028`. | Ini percobaan operasional read-only pada draft code, **bukan deployment produksi main**. |
| Snapshot produksi lama | Ledger lama pra-WP12/NTP tidak memenuhi sertifikasi time forward. | Dilarang menggabungkan ledger lama untuk mempercepat 10 hari atau mengisi missing ticks sintetis. |

Dokumen review roadmap dibuat di **branch dokumentasi terpisah**, bukan pada tree frozen di atas. Jangan mengubah SHA bukti start uji hanya untuk menyesuaikan dokumen.

## 2. Bukti VPS dan baseline 10 hari (snapshot, BUKAN status real-time selamanya)

- VPS: Windows Server 2012 R2, RAM 2 GB, CPU terbatas, MT5 demo read-only; aplikasi berbasis Python 3.12. Sesi Administrator Task Scheduler memakai `InteractiveToken`, sehingga **reboot/logoff recovery belum dijamin**.
- Sebelum perbaikan waktu, `w32tm` menunjukkan Local CMOS Clock, leap 3, stratum 0; perbandingan NTP terpisah menunjukkan selisih jam VPS sekitar **14,9 detik**. Observer dihentikan tertib, task XML, konfigurasi Windows Time dan SQLite 2 database dibackup privat.
- Setelah perbaikan 28 Oktober: W32Time Automatic, peer `time.windows.com,0x8`, poll ~1024 detik, leap 0, stratum 5, `Last Successful Sync Time` tersedia, perbandingan NTP ~0,08 detik; `scripts/ai/check_host_clock.py` melapor READY. *Itu kondisi teramati, bukan garansi permanen.*
- **Mulai isolasi:** 2026-10-27T20:12:03.244045Z = **28 Oktober 03:12 WIB**, dicatat dalam `stage0-acceptance-start.json`. Hari bursa UTC penuh pertama yang mungkin eligible adalah **28 Oktober**, bukan hari sebelumnya yang hanya parsial.
- **Snapshot terakhir dalam audit ini:** 31/31 siklus OK, 155/155 row quote OK, 5/5 simbol, offset broker terkini **UTC+2**, 0 order, LIVE OFF. Status continuous **WAITING** pada siklus tetapi worker masih aktif; 5 kartu keputusan semuanya WAIT. Ini jumlah menit awal, **0/10 hari penuh disahkan**.
- Kriteria kesehatan awal dari `stage0-health-daily.json` (waktu laporan sebelumnya saat 5 siklus): PASS success-rate, no-duplicates, clock-stable, quote-every-cycle, zero-orders; NOT_MET consecutive-days dan reconnect-recoveries; NO_DATA broker-ticks-per-day dan tick-snapshot-reconciliation. Laporan harian ditulis **07:30 WIB** oleh `Katarina-Stage0-Daily-Health`.
- Saat snapshot laporan, `news_pipeline.retrieval_failed_percent=100%` **tidak boleh dinyatakan kegagalan jaringan berita**: pengujian baru diluncurkan memakai `--no-fetch`. Itu artinya integrasi real news belum diuji pada trial tersebut.
- **Scope kritis:** pada program jangka panjang ada **7 simbol inti**, tetapi soak aktif hanya **5 simbol** sesuai pembatas RAM/konfigurasi saat ini. Claude perlu memutuskan dengan Owner: apakah 5-simbol adalah pilot Tahap 0 atau harus ada 7-simbol dan periode baru sebelum klaim kelulusan keseluruhan. Tidak boleh menandai 7/7 dari data 5/5.
- Task lama `Katarina-Readonly-Observer` tetap Ready/stopped; jangan jalankan bersamaan dengan task baru dan berasumsi tidak akan terjadi konflik terminal.
- Target *bersyarat* paling cepat evaluasi akhir sekitar **11 November 2026 WIB**, bukan tenggat lulus otomatis. Kebutuhan 10 hari bursa berturut-turut dan syarat lain dapat mengundur tanggal.

## 3. Audit subsistem end-to-end

| Subsistem (jalur utama) | Ada/diuji | Kelemahan dan syarat penerimaan |
|---|---|---|
| Arsitektur single brain: `intelligence/cognition/unified_brain.py` | SATU pemilik lifecycle observer → persepsi → keputusan → memori/shadow; synthetic/integration tests dan ci hijau | Jangan membentuk worker/otak kedua. Test nyata hanya jalur observasi, bukan model untung. |
| Koneksi MT5: `adapters/automatic_connection.py` | Satu pass real: route local, identity verified, 5/5 harga, 0 order; synthetic connection suite lulus | Broker fallback cloud / disconnect / restart nyata masih butuh bukti; status `native_mt5_package_available` bukan jaminan quote. |
| Host portability: `intelligence/broker/host_clock_guard.py` | Memeriksa Windows W32Time/Linux timedatectl saat native route; baseline VPS kini READY | Status OS NTP tidak independen sepenuhnya; periksa peer eksternal dan perubahan saat reboot. |
| Tick & server clock: `broker/broker_clock_alignment.py` + `broker/causal_broker_quotes.py` | Quorum >=3, cocokkan historical quotes sesudah konversi shift server; uji WP11 3 fresh+2 stale PASS; offset +2 nyata | Kedua API tetap milik **broker sama**; bukan sertifikasi waktu historis independen. Untuk jam pasar tutup, tahan kandidat; jangan paksa tanda +2/+3 lintas DST. |
| Closed bars/snapshot: `cognition/observer.py` | Time boundary kausal, candle yang sudah tutup, snapshot dan audit ledger; satu pass nyata sukses | Stress latency, gap jam sesi, broker symbol variants, penggunaan data salah arah masih perlu soak dan review. |
| Ledger/stream tick harian: `operations/observation_ledger.py` | Per-siklus (bid/ask/status), WP2 streaming per jam, hash/gap; baseline 155 rows valid | **0 broker_tick_days** dan **0 rekonsiliasi** dalam ledger baru pada snapshot awal. Wajib diuji setelah UTC day tutup, bukan dianggap sukses otomatis. |
| Verifikasi jam kesehatan: `operations/data_health.py` | Memperbaiki false PASS +3→-4→-7→+2; delta DST hanya 1 jam; Stage0 health view | Klaim PASS hanya sesudah 10 hari plus reconnect dan tick-date serta reconcil. |
| Simbol: `broker/observer_universe.py` | 7 simbol program, 5 di trial; mode fixed-universe vs rotation dibedakan | 2 simbol lain belum tercakup. Tidak boleh mengubah `max_symbols` pada run frozen tanpa menilai ulang start dan kapasitas. |
| Berita/makro: `news/news_intelligence.py`, `news/verified_policy_context.py` | WP3 menambahkan diagnosis; artikel official/full-body dan age policy; kriteria blackout aman | Trial `--no-fetch`; artikel verified kosong, blackout dan macro blocker. Butuh diagnosis sumber, data benar, riset counterfactual dengan WP9b sebelum membuka input. |
| Keputusan: `cognition/contextual_decision_intelligence.py` dan `decision_inputs.py` | WP9a blocker ladder, WP9b `legacy_fail_closed` vs shadow `measured_inputs`; 5 WAIT terbaru | Paling banyak 7 alasan utama per simbol: system_unhealthy; no_confirmed_closed_candle_entry; no_verified_relevant_news; high_impact_news_blackout; macro_event_risk_too_high; macro_policy_transmission_not_verified; insufficient_verified_forward_experience. Jangan menghapus alasan hanya demi BUY/SELL. |
| Teknik pasar: `perception/`, `intelligence/lab/` | Regime TREND/SIDEWAYS, adaptasi, candidate tools ada | Tidak ada setup BUY/SELL terpromosi yang lolos Tahap 4; liquidity sweep/pullback/fibo **hipotesis riset**, bukan sinyal terverifikasi. Simbol XAUUSD prioritas, BUY/SELL boleh asimetris. |
| Shadow/outcome: `intelligence/shadow/`, WP9b `decision_shadow` | Shadow study tanpa order dan memori prospective punya guard kausal | 5 WAIT, 0 hipotesis pada one-pass MT5; tidak ada sampel forward berlabel cukup untuk estimator peluang, tidak boleh klaim winrate. |
| Validasi: `research/validation.py` + `validate_strategy.py` | Registry hash, walk-forward, trial count, Bonferroni, holdout opening logged, cost & 3 baseline; tes validasi tersedia | Kinerja aktual setelah biaya BELUM PASS. Bukti validasi historis perlu independen UTC sebelum mengonsumsi bar arsip. |
| Data pengembangan WP8a: `research/dev_dataset.py`, `export_dev_bars.py` | Per-chunk independent UTC proof contract, streaming iterator & eager cap 100k; 15 tests lulus | Adapter MT5 nyata belum menyediakan `verified_historical_bar_shift` berbasis bukti UTC independen. **Ekspor harus tetap fail-closed**, tidak mengarang `verified=True`. |
| Edge/keuntungan | Audit 13 Okt 17 instrumen: kandidat PF ~0,36, ~77% rugi; 7 instrumen 2025–2026 tidak ada playbook stabil positif kedua tahun | **P0 hasil investasi: edge negatif/belum terbukti.** Jangan jadikan 10 hari sensor lulus sebagai bukti profit. Analisis biaya dan metode BUY/SELL baru perlu dilakukan setelah data terpercaya. |
| Biaya dan spread: WP10a/WP10b, `research/market_intelligence.py` | Filter biaya tersedia sebagai alat riset; spread median ~0,24R vs gerak untung median ~0,23R pada audit historis | Tanpa model biaya broker per market/session/swap/komisi/slippage dan threshold terdaftar, hasil optimasi raw return tidak layak promosi. |
| Risk Governor: `engines/risk.py` dan `config/risk_governor_v2.json` | Independent veto; default 1%, hard 5% trade, 8% aggregate risk. Ledger tetap 0 order. | **35% stop DD** pada profil utama sangat permisif untuk uji nyata; parameter adalah keputusan Owner terkunci. Layer DEMO lebih ketat (usulan 0,5%/trade, 3% DD harian) belum disahkan. Jangan ubah config tanpa izin. |
| Capital/Profit Lock/recovery: `cognition/brain_runtime_control.py` dan engines | Reserve logis, preview posisi dimungkinkan, restore ketat terhadap snapshot rusak; no order | Tidak ada feed broker-native atribusi manual-vs-AI yang terverifikasi, EXTREME_RECOVERY mesti pause. Jangan melepaskan reserve atau posisi Owner lewat auto-migration. |
| DEMO execution/outbox: `research/demo_readiness.py`, `intelligence/demo/` | Adapter overlay membatasi, laporan outbox read-only; tes sintetis | **Tidak sedang dijalankan.** Rekonsiliasi 100% dengan real fills belum ada; profil Owner pending, min 3 bulan/200 trade sebelum mempertimbangkan live. |
| Model AI/model confidence | Adaptive sampling dan memory code ada; tidak membolehkan threshold turun tanpa bukti | Confidence calibration belum ada >=300 outcome prospektif label; self-evolution bukan otoritas promosi; AI model/live signal belum terbukti. |
| Infrastruktur/CI/GitHub | Repo di-guard via PR/Body CI; manifest MATCH 306/306; full combined run #40574960082 PASS | 2 GB RAM; restart tanpa interactive login belum tervalidasi; frozen worktree tidak boleh disentuh; 3 PR terkait saling overlap. |
| Website/Cloud Hands/monitor | Struktur website/API/OAuth/monitor tersedia dalam repo; tidak diuji end-to-end dari host untuk audit ini | **Not assessed operationally**. Jangan tulis ONLINE atau production-ready tanpa probe kredensial, TLS, logs, session auth, monitoring, alerting. |

## 4. Gerbang tahap: penilaian berbasis bukti

| Tahap | Status validasi | Bukti yang sudah ada | Apa yang masih diperlukan |
|---|---|---|---|
| **0 Observer/data** | **IN_PROGRESS; 0/10 hari penuh** | Real MT5 5 simbol, NTP baru, 31/31 siklus awal OK; CI gabungan hijau | 10 hari berturut-turut (cakupan >=90% per hari), >=98% siklus, 0 duplicate, 3 reconnect pulih <=10m, hari tick penuh dan reconcil, 0 orders, kejelasan scope 5/7. |
| **1 Scientific validation** | TOOL READY, **GATE BELUM LULUS** | Test registry/split/holdout/cost/baselines | Dataset UTC historis terpercaya, eksperimen nyata deterministik, expectancy net + CI + baseline lengkap, tidak ada leakage. |
| **2 Market Intelligence** | RESEARCH TOOL AVAILABLE, **GATE BELUM LULUS** | Cost-aware filters dan konteks pasar; blocker ladder | Filter pra-daftar, bandingkan spread/volatilitas/session dengan tanpa filter; perbaiki 100% WAIT berbasis bukti. |
| **3 Risk/Execution Intelligence** | SYNTHETIC TOOL AVAILABLE, **GATE BELUM LULUS** | DemoRiskOverlay, report outbox | Owner tentukan batas DEMO, pembuktian 100% outbox fill reconcil, Risk Governor tidak dilemahkan. |
| **4 Adaptive Strategy BUY/SELL** | **PENDING** | Modul candidate/prototype saja | XAUUSD + pembanding, max 5 kandidat/sisi/instrumen; ≥100 holdout trades per strategi, PF net >=1,2, expectancy net >0 dan batas bawah bootstrap 95% >0, beat baselines & drawdown fit. |
| **5 Confidence/self-research** | **PENDING** | Memory/shadow learning research only | ≥300 outcome OOS, Brier lebih baik base rate, kalibrasi bin >=30 di ±10 percentage points; antrean hipotesis tanpa promosi otomatis. |
| **Sebelum LIVE** | **DILARANG** | Trading gate LIVE OFF | DEMO >=3 bulan + >=200 trades, expectancy net >0 dengan bawah CI >0, risk/reconcile 100%, review Owner. |

**Catatan:** roadmap asli bagian 1–7 merupakan kontrak Owner. Audit ini **tidak mengganti** cutoff persentase, persyaratan holdout, atau governance.

## 5. Backlog prioritas yang dapat langsung dikerjakan Claude

### P0 — Keselamatan & kebenaran bukti, harus didahulukan

1. **Cek kesehatan Stage0 setiap hari** tanpa mengganggu worker: hasil `check_stage0_health.py` dan UTC host, status WAITING/BLOCKED, rows FAILED + alasan, no orders, NTP peer drift, tick-gap. Jangan klaim PASS hanya karena task Running.
2. **Selesaikan 3 uji reconnect + day-ticks/reconciliation** dari data sandbox baru. Gunakan prosedur terkontrol yang tidak membahayakan 10 hari dan catat rentang outage. Jika perlu tes invasif, koordinasi Owner/maintenance dan jangan menghapus siklus gagal.
3. **Audit cakupan 5/7.** Apabila kriteria program menuntut 7, siapkan pilot terpisah atau keputusan Owner tentang scope; jangan diam-diam menaikkan worktree frozen atau menyimpulkan Stage0 penuh lulus hanya dari 5.
4. **Perbaiki restart unattended** hanya setelah pengujian sesi GUI MT5: Task Scheduler masih `InteractiveToken`, trigger logon; tidak ada jaminan reboot recovery. Sediakan rollback dan jangan menyimpan password/autologon plaintext.
5. **Audit WP12 seluruh entry points** yang dapat masih memakai timestamp broker mentah, termasuk legacy `perception/screening.py` dan `scripts/ai/run_readonly_decisions.py`, dengan karantina fail-closed. Dapatkan bukti historis DST **independen** sebelum ekspor WP8a; jangan gunakan shift hari ini untuk tahun lalu.
6. **Review PR #206, #207, #208** terhadap satu sama lain dan branch main, cek CI dan potensi duplikasi sebelum merge. Frozen 10-day trial tidak tergantung pada merge dan jangan otomatis diganti kode di tengah soak.

### P1 — Nilai riset (boleh persiapan paralel, tanpa promosi)

7. **Diagnostik 100% WAIT**: tujuh blocker + spread/technical evidence; bedakan `--no-fetch` dari news benar-benar gagal; gunakan WP9b decision shadow dengan *measured_inputs* hanya di eksperimen terisolasi dan data jujur. WP4 jurnal kandidat untuk counterfactual, WP9c tetap owner approval, WP9d setelah WP4+WP8b.
8. **Biaya trading nyata**: WP10a profil spread per simbol/sesi, WP10b swap/slippage/komisi sesudah WP8a; penuhi risk/reward minimal *net* dan uji tanda BUY/SELL berbeda menurut market regime.
9. **Riset strategi terdaftar**, tanpa intip holdout: liquidity sweep, structure, pullback, Fibonacci sebagai kandidat terpisah BUY dan SELL; rumuskan setup/cancel/stop/TP, biaya, baseline, dan kontrol multiple-testing. Ini bukan sakelar entry.
10. **Shadow/learning validity**: kumpulkan markout yang benar-benar eligible (tidak memprediksi hasil kemudian); laporkan sampel nyata vs sintetis, tren per metode/sisi/regime, jangan menaikkan autonomy.

### P2 — Operasi dan keputusan Owner

11. **Profil DEMO** (Owner): validasi rekomendasi pembatas ekstra 0,5% trade/3% harian dan keberadaan 35% hard limit di policy utama; riset dapat menyarankan lebih ketat tetapi kode lock hanya boleh berubah lewat persetujuan.
12. **Deploy/CI procedure**: buat candidate review/promotion terpisah, bukti manifest dan rollback, jangan pindahkan rahasia akun/demo ke repo publik.
13. **Repo status/cross PR**: ringkas setelah setiap review/merge, sinkronkan R5 hanya ketika Claude sudah meninjau; referensi PR dan status tidak boleh menggantikan tes lulus.

## 6. Perintah audit yang aman dan sumber evidence

Dijalankan read-only pada VPS dengan Python environment yang punya paket MT5:
- `python scripts/ai/check_host_clock.py` — host NTP READY/BLOCKED, tanpa order.
- `python scripts/ai/check_stage0_health.py --state-dir C:\Katarina\state\stage0-10day-20261028` — kriteria Stage0 dari ledger **baru**.
- `w32tm /query /status` — sumber dan last sync NTP.
- `schtasks /Query /TN Katarina-Stage0-10Day-Observer /FO LIST /V`; sama untuk `Katarina-Stage0-Daily-Health`.
- `git -C C:\Katarina\_roadmap_validation\stage0-combined-acceptance-20261028 rev-parse HEAD^{tree}` — harus sama `a48d8c3fad957f6d6236dbbc4f1dbe7168069d24`.
- `scripts/governance/promotion_gate.py --check` dan `scripts/deployment/release_manifest.py --manifest ops/deployment/release-manifest.json` pada branch review.

State sensitif pada VPS **tidak** dipublikasikan: `stage0-acceptance-start.json`, `continuous-status.json`, `stage0-health-daily.json`, SQLite/tick broker, task/private connection config. Cukup tulis **agregat tidak mengandung akun/credential** di status proyek.

## 7. Metrik progress, label dan definisi selesai

Gunakan tepat satu label per langkah:
- `CODE_READY`: fungsi + tes ada; tidak membuktikan broker.
- `CI_PASS`: check pada SHA tertentu benar-benar hijau.
- `BROKER_SMOKE_PASS`: satu pass MT5 nyata tanpa order; tidak sama dengan 1 hari penuh.
- `SOAK_RUNNING`: task masih hidup, tetapi health belum lulus.
- `STAGE0_PASS`: sembilan kriteria Tahap 0 semuanya PASS setelah bukti berhari-hari.
- `ALPHA_PASS`: expectancy bersih setelah biaya/holdout dan baseline sesuai syarat stage 4.
- `DEMO_AUTHORIZED` / `LIVE_AUTHORIZED`: hanya setelah catatan promosi Owner; saat ini KEDUANYA FALSE.
- `BLOCKED` / `NO_DATA`: harus jujur, tidak dikonversi ke PASS hanya demi roadmap selesai.

**Check-in Claude:** setelah UTC close setiap hari (laporan auto 07:30 WIB) catat jumlah hari eligible, rates, duplicate, shift, tick-days, reconcil, reconnect, orders, blockers, NTP, dan commit hash. Saat ada `NOT_MET` atau `NO_DATA`, buat tindakan terukur dan jangan mengubah data historis. Tinjau kelemahan tiap sesi; bila perlu pindah perangkat, bukti NTP + shift harus diulang pada host baru.

## 8. Referensi prioritas dan batas klaim

- `docs/ROADMAP.md` bagian 1–7, R0, R4, R5, R7 — kontrak governance dan status paket.
- `docs/PROJECT_STATUS.md` — **satu sumber operasional**, snapshot ini harus disebut jelas dan tidak menggantikan laporan VPS.
- `docs/maintenance/STAGE0_10DAY_ACCEPTANCE_20261028.md` — titik awal dan syarat penerimaan.
- `docs/operations/MT5_CLOCK_PORTABILITY.md`, `docs/maintenance/STAGE0_CLOCK_HEALTH_HANDOFF_20261028.md` — perbaikan clock dan batas bukti.
- `docs/maintenance/INTEGRATION_HANDOFF_20261027.md` — WP12/9b/8a, source-only historical UTC.
- `docs/research/VALIDATION_PROTOCOL.md`, `docs/research/MARKET_INTELLIGENCE.md`, `docs/research/DEMO_READINESS.md`, `docs/architecture/RISK_PROFILE_V2.md`.
- `CLAUDE.md`, `CHANGELOG.md`, `ops/deployment/release-manifest.json`, run [CI #40574960082](https://github.com/alfaauliau-katarinaAI/Katarina-AI/actions/runs/40574960082).

**Kesimpulan Claude:** lanjutkan pengumpulan Stage0 read-only tanpa mengubah snapshot/versi; lakukan audit setiap hari. Siapkan riset terpisah, tetapi tahan semua promosi strategi atau order sampai data, validasi, dan otorisasi terbukti. Tidak ada janji profit atau tanggal kelulusan pasti.
