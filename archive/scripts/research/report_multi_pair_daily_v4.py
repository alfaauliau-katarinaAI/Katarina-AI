"""Make compact, auditable report for simultaneous multi-pair strategy replay."""
from __future__ import annotations
import csv,json,math
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
ROOT=Path(r"C:\KatarinaDev\decision-backtest-20261012\synchronous_multi_pair_daily_v4")
def n(x):return "-" if x is None else f"{x:,.4f}"
def stress(trades,extra):
    equity=1.;peak=1.;dd=0.;profit=0.;loss=0.
    rs=[]
    for t in trades:
        r=t["R"]-extra
        rs.append(r)
        profit+=max(r,0.);loss+=max(-r,0.)
        equity*=1+.0025*r
        peak=max(peak,equity)
        dd=max(dd,1-equity/peak)
    return {"n":len(rs),"mean_R":round(mean(rs),5) if rs else None,
            "PF":round(profit/loss,4) if loss else None,
            "equity_multiple":round(equity,6),"drawdown_pct":round(dd*100,3),
            "positive_days":sum(r>0 for r in rs)}
def main():
    r=json.loads((ROOT/"FINAL_DAILY_RANK_55.json").read_text(encoding="utf-8"))
    ranked=r["ranked_policy"];control=r["alphabetical_control"]
    ts=ranked["trades"];picks=Counter(t["symbol"] for t in ts)
    w=r["historical_time_series_coverage"];days=ranked["days_observed"]
    strs={name:stress(ts,x) for name,x in
          (("modeled",0),("extra_0_10R",.1),("extra_0_20R",.2))}
    pct=lambda a,b:f"{100*a/max(b,1):.2f}%"
    lines=["# KATARINA — Sinkronisasi Pencarian Multi-Pair (55 Instrumen)",
      "",
      "**Eksperimen read-only; ini bukan bukti sistem profit setiap hari atau izin trading live.**",
      "",
      "## Metode yang dibekukan sebelum pengujian",
      "",
      "- 55 simbol broker, dievaluasi serentak pada **06:00, 12:00, 18:00 kode waktu broker**. Ini bukan jam UTC yang telah diverifikasi; pengamatan langsung 12 Oktober 2026 menemukan raw tick sekitar 3 jam lebih maju daripada UTC VPS.",
      "- Baca hanya M5/M15/H1 selesai pada waktu penilaian; pilih satu sinyal kualitas terbaik di timestamp itu, tanpa menunggu/melihat hasil sinyal beberapa jam ke depan.",
      "- Kandidat harus disetujui Brain teknis, StructuralEntryQuality dan pemeriksaan definisi playbook (real structure/retest/sweep).",
      "- Ranking memakai skor bukti struktur, ruang menuju target dan spread relatif ATR. Skor bukan probabilitas profit yang terkalibrasi.",
      "- Maksimal **satu entry per tanggal pada kode waktu broker**, satu posisi hipotetis aktif sekaligus, risk **0,25% dari ekuitas** per entry. Tidak ada layering.",
      "- Exit: baseline model M5 next-open, SL 1,2 ATR M5, TP 1,8R, maksimum 24 candle M5 dan estimasi biaya 0,03R.",
      "- Semua simulasi berasumsi berita historis aman (padahal tidak terverifikasi). Keputusan real-time tetap WAIT sampai news dan governor valid.",
      "",
      "## Berapa hari ada peluang?",
      "",
      f"- Pair diuji: **{r['number_of_symbols']}**.",
      f"- Checkpoint dengan setidaknya satu simbol punya data: **{w['unique_checkpoints']:,}**.",
      f"- Rata-rata simbol terscan per checkpoint: **{w['avg_symbols_scanned_per_checkpoint']}**.",
      f"- Hari dengan setidaknya satu snapshot: **{days:,}**.",
      f"- Hari dengan setidaknya satu peluang memenuhi kriteria: **{ranked['day_with_at_least_one_valid_signal']:,}** ({pct(ranked['day_with_at_least_one_valid_signal'],days)} dari hari teramati).",
      f"- Hari yang benar-benar mendapat satu trade simulasi: **{ranked['trade_days']:,}** ({pct(ranked['trade_days'],days)}).",
      f"- Hari NO TRADE: **{ranked['days_no_trade']:,}** ({pct(ranked['days_no_trade'],days)}).",
      f"- Hari simulasi profit: **{ranked['positive_trade_days']:,}** ({pct(ranked['positive_trade_days'],days)} dari seluruh hari teramati).",
      f"- Hari simulasi rugi: **{ranked['negative_trade_days']:,}**.",
      f"- Checkpoint dengan lebih dari satu kandidat serentak: **{w['simultaneous_multi_candidate_sessions']}**. Ini mengukur seberapa sering ranking antar-pair bisa dibandingkan secara adil.",
      "",
      "## Performa gabungan — bukan proyeksi live",
      "",
      "| Metode | Trade | Avg R | PF | Win% | Growth model | Max DD model |",
      "|---|---:|---:|---:|---:|---:|---:|",
      f"| Ranking skor KATARINA | {ranked['trade_stats']['n']} | {n(ranked['trade_stats']['avg_R'])} | {n(ranked['trade_stats']['PF'])} | {n(ranked['trade_stats']['win_pct'])} | {n((ranked['equity_multiple']-1)*100)}% | {n(ranked['max_drawdown_pct'])}% |",
      f"| Kontrol alfabetis, kandidat dan timestamp sama | {control['trade_stats']['n']} | {n(control['trade_stats']['avg_R'])} | {n(control['trade_stats']['PF'])} | {n(control['trade_stats']['win_pct'])} | {n((control['equity_multiple']-1)*100)}% | {n(control['max_drawdown_pct'])}% |",
      "",
      "Kontrol bukan strategi matang; fungsinya memeriksa apakah skor relatif benar-benar bernilai ketika banyak kandidat hadir bersamaan.",
      "",
      "## Stress test biaya tambahan",
      "",
      "| Biaya tambahan di atas model 0,03R | Rata-rata R | PF | Return modal model | Drawdown model |",
      "|---|---:|---:|---:|---:|"]
    for k,x in (("0R",strs["modeled"]),("0,10R",strs["extra_0_10R"]),("0,20R",strs["extra_0_20R"])):
        lines.append(f"| {k} | {n(x['mean_R'])} | {n(x['PF'])} | {n((x['equity_multiple']-1)*100)}% | {n(x['drawdown_pct'])}% |")
    lines+=["","## Hasil menurut periode yang sudah pernah diteliti","",
          "| Periode | Trade | Mean R | PF |","|---|---:|---:|---:|"]
    for k,x in ranked["by_period"].items():
        lines.append(f"| {k} | {x['n']} | {n(x['avg_R'])} | {n(x['PF'])} |")
    lines+=["","## Rekap entry multipair tiap bulan","",
           "| Bulan kode waktu broker | Trade | Avg R | Total R | PF |","|---|---:|---:|---:|---:|"]
    for k,x in ranked["monthly"].items():
        lines.append(f"| {k} | {x['n']} | {n(x['avg_R'])} | {n(x['sum_R'])} | {n(x['PF'])} |")
    lines+=["","## Pair terpilih paling sering","",
        "| Pair | Kali terpilih |","|---|---:|"]
    for sym,num in picks.most_common(20):
        lines.append(f"| {sym} | {num} |")
    lines+=["","## Batasan dan keputusan",""]
    lines.extend("- "+s for s in r["limitations"])
    lines+=["",
      "- Data 2025–2026 telah dipakai untuk riset sebelumnya. **Bukan validasi holdout independen**.",
      "- Hari dikelompokkan berdasarkan tanggal **timestamp historis berkode broker**, bukan kalender Asia/Jakarta maupun UTC tersertifikasi. DST historis broker belum dikalibrasi; jangan mengonversi jam slot ke WIB menggunakan satu offset untuk semua periode.",
      "- Tidak mengukur semua peluang seharian; hanya tiga pengambilan keputusan per hari. Angka profit harian tidak dapat digeneralisasikan.",
      "- Ranking berbasis skor aturan, bukan probabilitas profit terlatih; jangan optimasi atau pilih pair setelah melihat hasil tanpa membekukan model lagi.",
      "- Profit, drawdown dan equity adalah model fixed-fraction 0,25%, bukan P/L broker, belum memvalidasi minimum lot, leverage, margin atau volatilitas gap.",
      "- **Kesimpulan: sistem dapat membandingkan seluruh pair, tetapi tidak boleh memaksa entry setiap hari.**",
      "",
      "File lengkap: FINAL_DAILY_RANK_55.json dan ranked_trades.csv (detail pada VPS); compact CSV tersedia di repository.",
      ""]
    (ROOT/"LAPORAN_MULTI_PAIR_HARIAN.md").write_text("\n".join(lines),encoding="utf-8")
    (ROOT/"STRESS_SUMMARY.json").write_text(json.dumps(strs,indent=2),encoding="utf-8")
    with (ROOT/"per_symbol_watch_stats.csv").open("w",newline="",encoding="utf-8") as f:
        fields=["symbol","valid_checkpoints","raw_technical_candidates","strict_candidates",
                "quality_reject","semantics_reject","brain_WAIT","chosen"]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for s in r["per_symbol"]:
            c=s["counts"]
            writer.writerow(dict(symbol=s["symbol"],valid_checkpoints=s["valid_checkpoints"],
                raw_technical_candidates=c.get("raw_technical_candidates",0),
                strict_candidates=c.get("strict_candidates",0),
                quality_reject=c.get("quality_reject",0),
                semantics_reject=c.get("semantics_reject",0),
                brain_WAIT=c.get("brain_WAIT",0),
                chosen=picks.get(s["symbol"],0)))
    print("REPORT_READY",json.dumps({"days":days,"trade_days":ranked["trade_days"],
        "positive_days":ranked["positive_trade_days"],"no_trade_days":ranked["days_no_trade"],
        "ranked":ranked["trade_stats"],"control":control["trade_stats"],
        "stress":strs},ensure_ascii=False),flush=True)
if __name__=="__main__":main()