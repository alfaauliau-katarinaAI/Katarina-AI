"""Generate V6 audit and machine-readable decision, research only."""
from pathlib import Path
import json
B=Path(r"C:\KatarinaDev\decision-backtest-20261012\intraday_brain_integrated_v6")
OLD=B.parent/"intraday_scalp_full_m5_v5"
res=json.loads((B/"ALL_55_RESULT.json").read_text(encoding="utf-8"))
commission=json.loads((B/"COMMISSION_HISTORY_COVERAGE.json").read_text(encoding="utf-8"))
forward=json.loads((B/"prospective"/"LATEST_FORWARD_STATUS.json").read_text(encoding="utf-8"))
tick=json.loads((OLD/"TICK_SPREAD_SAMPLES.json").read_text(encoding="utf-8"))
v5=json.loads((OLD/"FULL_M5_55_FINAL.json").read_text(encoding="utf-8"))
v6=res["results"]
rank=v6["BRAIN_INTRADAY_0_EXTRA_COST"]
months=rank["by_month"]
pf=lambda x:("-" if x is None else f"{x:.4f}")
lines=[
"# KATARINA V6 — Brain terpadu, full M5, 55 pair",
"",
"**Hasil: strategi BELUM PROFIT. Status READ-ONLY, WAIT. Tidak ada live order.**",
"",
f"Scanner memindai {res['M5_closed_bars_scanned']:,} closed M5 bar, menghasilkan {res['raw_intraday_candidate_count']:,} setup intraday, dan {res['passes']:,} lolos full Brain + aturan struktur + kualitas entry.",
"",
"## Performa portofolio multi-pair",
"",
"| Strategi | Trade | Avg R | PF | Hasil modal model | Maks DD model |",
"|---|---:|---:|---:|---:|---:|",
]
cases=[
    ("V5 scanner tanpa full Brain",v5["policies"]["INTRADAY_ONLY"]),
    ("V6 Brain intraday",rank),
    ("V6 + 0,10R biaya ekstra",v6["BRAIN_INTRADAY_PLUS_0_10R"]),
    ("V6 + 0,20R biaya ekstra",v6["BRAIN_INTRADAY_PLUS_0_20R"]),
    ("Kontrol pilih pair alfabetis",v6["BRAIN_ALPHABETICAL_CONTROL"]),
    ("Simulasi modal $1.000, minimum lot",v6["BROKER_MIN_LOT_SCENARIO_1000USD"]),
    ("Simulasi modal $5.000, minimum lot",v6["BROKER_MIN_LOT_SCENARIO_5000USD"]),
]
for label,x in cases:
    lines.append(f"| {label} | {x['n']} | {pf(x['trade_stats']['avg_R'])} | {pf(x['trade_stats']['PF'])} | {x['return_model_pct']:.2f}% | {x['max_drawdown_pct']:.2f}% |")
positive=sum(x["avg_R"]>0 for x in months.values())
negative=sum(x["avg_R"]<0 for x in months.values())
lines.extend(["",
"## Hari dan konsistensi",
"",
f"Periode pasar berkode jam broker: {res['market_coverage_days']} hari. V6 entry pada {rank['days_traded']} hari: {rank['positive_trade_days']} hari positif, {rank['negative_trade_days']} negatif, {rank['no_trade_market_days']} tidak ada entry. Bulan positif {positive}/{len(months)}, negatif {negative}.",
"",
"| Bulan server broker | Trade | Avg R | PF |",
"|---|---:|---:|---:|"])
for mon,data in sorted(months.items()):
    lines.append(f"| {mon} | {data['n']} | {pf(data['avg_R'])} | {pf(data['PF'])} |")
lines.extend(["",
"## Masalah yang dibuktikan",
"",
f"- Penolakan terbesar: no_pullback_location {res['rejections'].get('quality_false_no_pullback_location',0):,}, insufficient_structural_room {res['rejections'].get('quality_false_insufficient_structural_room',0):,}, Brain arah tidak cocok {res['rejections'].get('brain_no_matching_direction',0):,}.",
"- Scanner, SemanticSetup, StructuralEntryQuality dan full Brain sekarang dikonfirmasi PADA SAAT sinyal tersedia; baru kemudian ranking multi-pair. Pengembalian trade masa depan tidak dipakai memilih posisi.",
"- Ketika Brain sungguhan dipakai, performa lebih buruk daripada V5. Kontrol alfabetis V6 sedikit lebih baik. Berarti ranking skor belum menghasilkan edge yang konsisten.",
"- Intraday tetap jalur RISET utama. Scalp ekstrem tetap DISABLED; eksperimen V5 scalping merugikan.",
"",
"## Biaya real dan audit broker",
"",
f"- {tick['usable_samples']}/16 sampel tick historis tersedia di sekitar waktu target; tidak mewakili seluruh 55 instrumen dan seluruh momen order.",
f"- Riwayat komisi broker 120 hari memberi {commission['deals_returned']} deal dan {len(commission['summary_by_symbol'])} simbol dengan statistik komisi, sehingga biaya komisi per lot belum bisa dikalibrasi secara kredibel.",
"- Simulasi memakai spread M5, one-point adverse fill tiap sisi, serta estimasi biaya +0,03 R. Stress tambahan 0,10/0,20R menunjukkan strategi tidak tahan biaya.",
"- Skenario modal $1k/$5k memakai spesifikasi lot minimum broker saat ini dan risiko stop setelah fill simulasi: ini DIAGNOSTIK retrospektif, bukan hasil strategi kausal dengan risk sizing dan margin historis terverifikasi.",
"- Margin, swap, tick intrabar, impact slippage, berita historis, dan offset UTC/DST historis belum tersertifikasi.",
"",
"## Data baru / forward",
"",
f"- Freeze kontrak paper: {forward['freeze_utc']}.",
f"- Snapshot pertama sesudah freeze: {forward['scanned'].get('fresh_market_evaluated',0)} pair segar; setup intraday terbaru {len(forward['technical_candidates_at_latest_m5'])}; hasil transaksi baru {forward['new_closed_trade_outcomes']}.",
"- Belum ada untouched independent out-of-sample profit/loss sejak freeze. Seluruh data 2025–Oktober 2026 telah dipakai berulang kali; JANGAN menyebut performa di atas sebagai validasi forward.",
"- Produk read-only mencatat data dan WAIT; tidak mengizinkan broker orders. Evaluasi hanya boleh berubah setelah bukti baru cukup.",
"",
"## Keputusan",
"",
"**INTRADAY RESEARCH ONLY; SCALPING OFF; LIVE WAIT.** Tidak ada strategi yang telah lolos profitable + cost-robust + independent OOS.",
"",
"Source: src/katarina/intelligence/intraday_scalp_research.py; scripts/research/backtest_unified_intraday_brain_v6.py; scripts/research/collect_forward_intraday_v6.py. Semua file log dan hasil detail disimpan di VPS.",
""])
(B/"LAPORAN_BRAIN_TERPADU_V6.md").write_text("\n".join(lines),encoding="utf-8")
decision=dict(version="V6",symbols=res["scan_symbols"],
    scanned_M5=res["M5_closed_bars_scanned"],raw_candidates=res["raw_intraday_candidate_count"],
    full_brain_pass=res["passes"],trades=rank["n"],
    expectancy_R=rank["trade_stats"]["avg_R"],PF=rank["trade_stats"]["PF"],
    model_return_pct=rank["return_model_pct"],model_max_dd_pct=rank["max_drawdown_pct"],
    positive_days=rank["positive_trade_days"],negative_days=rank["negative_trade_days"],
    no_trade_days=rank["no_trade_market_days"],
    months_positive=positive,months_negative=negative,
    extra_fee_0_10R_return_pct=v6["BRAIN_INTRADAY_PLUS_0_10R"]["return_model_pct"],
    untouched_oos=False,forward_closed_trades=forward["new_closed_trade_outcomes"],
    broker_commission_verified=False,news_historical_verified=False,
    mode="INTRADAY_RESEARCH_ONLY",scalp_extreme_enabled=False,
    live_execution_authorized=False,orders_sent=0)
(B/"KESIMPULAN_V6.json").write_text(json.dumps(decision,indent=2),encoding="utf-8")
print("V6_REPORT",json.dumps(decision,ensure_ascii=False),flush=True)