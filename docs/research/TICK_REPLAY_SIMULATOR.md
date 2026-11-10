# Simulator tick replay enam kandidat XAUUSD.vx (K1)

Status: **CODE_COMPLETE (offline, research-only)**. Belum ada izin backtest, belum ada data broker
terverifikasi, tidak ada jalur order. Dasar aturan: D10-K1..K27 di
[`SIX_CANDIDATE_PREREGISTRATION_SPEC_20261104.md`](SIX_CANDIDATE_PREREGISTRATION_SPEC_20261104.md) dan
[`SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md`](SIX_CANDIDATE_EXECUTION_SIMULATOR_CONTRACT_20261104.md).
Modul lama `research/setups/*` (OHLC + `target_rr`) **bukan** validasi desain ini dan tidak dipakai.

## Lokasi

| Berkas | Isi |
|---|---|
| `src/katarina/research/tick_replay/contract.py` | Kontrak input (simbol, sesi, biaya, dataset), tabel enam kandidat dengan `spec_sha256`, validasi tick |
| `.../bars.py` | Candle BID `[open, close)`, gap, ambiguitas milidetik sama |
| `.../structure.py` | Pivot 2+2, TTL swing, ATR14 Wilder, BOS H1, zona, breakout, pemilihan target |
| `.../engine.py` | `TickReplay`: loop kronologis, aturan enam kandidat, fill, exit, ledger deterministik |
| `.../dataset.py` | Loader CSV `time_msc,bid,ask[,flags]` + manifest JSON, cek SHA-256 |
| `scripts/research/replay_six_candidates.py` | CLI; tanpa `--owner-approval-ref` hanya memvalidasi input |
| `tests/unit/research/test_tick_replay_{structure,engine}.py`, `tests/integration/test_tick_replay_cli.py` | T01–T12 dengan fixture sintetis (teknis saja) |

## Urutan event per tick

1. Cek gap quote terhadap waktu quote-session resmi. Gap > `max_quote_gap_ms` membuat candle yang tersentuh tidak sah.
2. Candle dengan `end_ms <= waktu tick` ditutup (H1, M15, lalu M5). Struktur diperbarui dulu, lalu aturan kandidat dievaluasi. Sinyal dan exit hitungan bar menjadi *intent* yang hanya boleh fill pada tick **sesudah** tick yang mengungkap penutupan candle.
3. Pada tick itu sendiri, urutannya: posisi terbuka diperiksa SL/TP, lalu deadline UTC dan pre-close (fill pada tick pertama ≥ deadline), lalu intent entry, lalu first touch/breach zona berbasis BID.
4. Tick dimasukkan ke candle yang memuatnya.

## Pilihan implementasi untuk item yang belum ditetapkan Owner (2B.1)

Semua pilihan di bawah ini fail-closed dan tidak dipilih berdasarkan profit. Owner dapat mengubahnya, dan setiap
perubahan menghasilkan `ENGINE_VERSION`/`spec_sha256` baru.

| Item | Pilihan |
|---|---|
| Prioritas boundary | H1 → M15 → M5 pada instan yang sama; fill tidak pernah terjadi pada tick pengungkap. |
| Out-of-order/duplikat urutan | Data mundur (`TICK_OUT_OF_ORDER`), `seq` tidak naik, atau quote silang/nol membuat **seluruh** input ditolak. |
| Milidetik sama tanpa bukti urutan | Jika quote dalam grup berbeda dan grup itu memicu entry, exit atau zona, hasilnya `BLOCKED_INTRABAR_ORDER`. Posisi dikeluarkan dari ledger sebagai `POSITION_BLOCKED` tanpa harga exit. Jika `sequence_evidence = VERIFIED_SOURCE_ORDER`, grup diproses berurutan. |
| Trigger SL/TP | BUY: `BID <= SL` atau `BID >= TP`. SELL: `ASK >= SL` atau `ASK <= TP`. Fill pada quote tick pemicu. Gap melewati SL dicatat `fill_beyond_stop`. |
| Stops level | Diperiksa saat fill terhadap BID (BUY) atau ASK (SELL): jarak SL dan TP harus ≥ `stops_level` (minimal 1 tick). Jika tidak, `WAIT:INVALID_BROKER_STOP_GEOMETRY`. Freeze level dicatat di kontrak; simulator tidak memodifikasi order, jadi tidak dipakai. |
| Target | Dipilih saat fill dari struktur yang valid saat itu (sisi profit, terdekat, tie terbaru). Jika tidak ada, `WAIT:NO_VALID_STRUCTURAL_TARGET`. |
| Sesi | Tanpa bukti sesi, entry `BLOCKED_SESSION_EVIDENCE`. Exit di luar trade session menjadi `EXIT_PENDING_NO_QUOTE` sampai tick trade-session berikutnya. Tanpa bukti sesi, seluruh waktu dihitung sebagai waktu quote untuk deteksi gap. |
| Gap antara sinyal dan fill | `BLOCKED_DATA_GAP`. Swing pada timeframe yang terkena gap menjadi `EXPIRED_GAP`, ATR di-reset, dan zona FRESH berakhir. |
| Biaya | Komisi, swap per malam (rollover UTC, hari triple swap) dan spread masuk/keluar dicatat per trade dari snapshot ber-hash. **Tidak ada agregasi atau metrik profit**. Stress 1,5x/2x (T12) adalah tugas validator Tahap 1, bukan simulator. |
| Akhir data | `OPEN_AT_DATA_END` / `UNFILLED_AT_DATA_END`; tidak ditutup paksa. |

## Pemetaan tes

| Tes | Cakupan |
|---|---|
| T01 | Pivot hanya setelah dua candle kanan tutup, tie high sama, TTL M15 96, invalidasi 1 tick |
| T02 | B1/S1 sweep + reclaim, tidak fill pada tick penutupan |
| T03 | B2/S2 BOS, zona, konfirmasi M15, first visit consumed, overlap K24/K25, breach hybrid, TTL 48 H1 |
| T04 | B3/S3 retest, timeout enam M5, tanpa target |
| T05 | ATR Wilder, buffer `ceil`, stops level, TP struktural |
| T06 | Entry ASK/BID, exit BID/ASK, mismatch trade vs quote session |
| T07 | Milidetik sama terverifikasi vs tidak; SL dan TP dalam satu grup diblokir |
| T08 | Exit bar, UTC, pre-close, tidak ada quote saat expiry |
| T09 | Tanpa sesi, gap quote, candle tidak sah |
| T10 | Kandidat independen, satu posisi, sinyal duplikat diblokir |
| T11 | Hash ledger deterministik, future poisoning, cutoff 13 Okt, input ditolak |
| T12 | Snapshot biaya per trade, tanpa metrik profit |

## Blocker data (belum dapat dijalankan pada data asli)

1. Tick historis XAUUSD.vx sebelum 13 Okt 2026 beserta manifest belum diarsipkan. Pengambilan batch besar butuh izin terpisah karena VPS 2 GB menjalankan observer Stage 0.
2. Bukti sesi resmi (`SymbolInfoSessionQuote/Trade`) dan konversi UTC belum tersedia. Tanpa itu semua entry `BLOCKED_SESSION_EVIDENCE`.
3. Snapshot biaya (komisi/swap) ber-hash belum ada.
4. Bukti urutan sumber untuk milidetik sama belum ada, sehingga dataset harus `UNVERIFIED`.
5. Menjalankan replay pada data asli adalah backtest dan membutuhkan persetujuan Owner tersendiri (`--owner-approval-ref`).
