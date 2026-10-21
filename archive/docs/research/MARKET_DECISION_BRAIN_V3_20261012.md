# KATARINA Market Decision Brain V3 — 12 Oktober 2026

**Fungsi:** satu kartu penjelasan untuk **enam pertanyaan penting** setiap pair: (1) apa yang terjadi; (2) tren bullish/bearish/sideways/tidak pasti; (3) ke mana harga berpeluang bergerak secara **bersyarat**; (4) playbook paling sesuai; (5) apa dilakukan jika tak ada setup; (6) apakah entry sekarang diizinkan.

## Perubahan dibandingkan kode sebelumnya

- `MarketDecisionPipeline` sekarang memiliki **potential_action** dan **setup_ready** yang terpisah dari `action`. Saat konteks berita belum diverifikasi, action **WAIT** meskipun setup secara teknikal terbentuk.
- `MarketDecisionBrain` di `src/katarina/intelligence/market_decision_brain_v3.py` merangkum regime, bias, fase, skenario utama/alternatif, target support/resistance H1 (atau *proyeksi ATR* yang ditandai jelas), level invalidasi struktur M15, estimasi RR setelah spread, alasan, blocker dan kondisi pemicu evaluasi berikutnya.
- Bukti teknikal memakai skor **berbobot**, tidak mewajibkan semua indikator sependapat sekaligus. Skor **bukan probabilitas menang**. Beberapa syarat tetap wajib: candle data valid, spread yang layak, kondisi trading broker, berita, rasio risk/reward, bukti edge independen tiap pair–playbook–arah, dan persetujuan risiko.
- `technical_signal` ialah gagasan **riset**, bukan instruksi order. `decision` tetap WAIT jika ada blocker. `live_execution_authorized` selalu **false** pada modul ini; tidak ada path untuk mengirim order.
- Jika UNKNOWN / TRANSITION atau sisi range tidak jelas, KATARINA menyatakan **WAIT** dan memberi kondisi yang harus terkonfirmasi. Tidak dipaksa BUY/SELL.
- Scanner VPS `scripts/ai/run_decision_brain_v3.py` membaca 55 simbol broker read-only dan menyimpan semua kartu JSON **lokal**; tidak mengirim histori/akun ke repository.

## Audit masalah clock MT5

Saat audit ditemukan timestamp candle/tick broker disimpan sebagai wall-clock **UTC+3** dalam `time`, sehingga sebelum perbaikan candle terbaca **masa depan** oleh UTC VPS. Scanner baru memverifikasi offset bersama dengan sedikitnya dua quote likuid yang saat itu fresh dan konsisten; **tanpa verifikasi, batalkan scan**. Setelah diverifikasi, candle ditransformasikan ke UTC dan quote yang stale/future-timestamp tetap **tidak diperbolehkan** menjadi izin transaksi. Offset tidak diasumsikan permanen karena server broker dapat mengubah DST.

## Smoke test lengkap 55 pair (snapshot 2026-10-11 23:13:47 UTC)

| Item | Hasil |
|---|---:|
| Instrumen diuji | 55 |
| TREND_UP | 10 |
| PULLBACK_UP | 1 |
| TREND_DOWN | 1 |
| SIDEWAYS | 30 |
| TRANSITION | 13 |
| Idea teknikal SELL | 6 |
| Idea teknikal BUY | 0 |
| Idea WAIT | 49 |
| Keputusan eksekusi WAIT | **55** |
| Broker order terkirim | **0** |

Semua keputusan **WAIT** bukan kegagalan scanning: `news_context_verified=false`, belum ada edge pair-playbook tervalidasi secara independen (penelitian multipair sebelumnya gagal validasi), dan paper-risk belum disetujui. Sebagian quote juga stale/sedikit ahead saat audit sehingga tidak memenuhi hard gate. Keputusan tidak boleh berubah hanya karena menerapkan scoring yang lebih longgar.

## Validasi

- `tests/unit/intelligence/test_market_decision_brain_v3.py` mencakup enam jawaban, sinyal BUY sintetis dan gate riset, time/future-bar, news, spread, edge salah pair, stale, dan independensi izin live.
- `tests/unit/intelligence/test_market_decision_pipeline.py` menguji kompatibilitas adapter lama.
- `GitHub Actions: KATARINA Body CI` menjalankan kedua unit test via discover. Scanner MT5 hanya dijalankan eksplisit di VPS, **tidak** pada GitHub-hosted runner.

## Batasan dan pekerjaan yang masih diperlukan

V3 adalah **decision observer riset**, bukan sistem trading mandiri yang layak live. Skenario harga adalah hipotesis kondisional berdasarkan level harga, bukan kepastian arah. Edge dari uji 2025/2026 sudah gagal di evaluasi lanjutan; jangan menaikkan statusnya secara otomatis. Tahap lanjutan harus membuktikan kalibrasi klasifikasi regime, kualitas skenario, dan manfaat pilihan strategi melalui **walk-forward baru** serta forward-demo dengan biaya/slippage/margin broker aktual.

**Tidak ada perubahan Risk Governor produksi, saldo, akun, atau eksekusi live.**
