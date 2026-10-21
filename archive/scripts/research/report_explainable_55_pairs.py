"""Aggregate all-pair read-only decision backtest, preserving all WAIT counts."""
import csv,json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
OUT=Path(r"C:\KatarinaDev\decision-backtest-20261012")
LABELS=("2025_available","2026_Jan_May","2026_Jun_Oct")
def split(t):return LABELS[0] if t<1767225600 else LABELS[1] if t<1780272000 else LABELS[2]
def month(t):return datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m")
def stats(records):
    if not records:return dict(n=0,mean_R=None,sum_R=0.,PF=None,win_pct=None,DD_R=0.)
    values=[x["R"] for x in records];n=len(values);pos=sum(max(x,0) for x in values)
    neg=-sum(min(x,0) for x in values)
    total=0.;maxeq=0.;dd=0.
    for x in values:
        total+=x;maxeq=max(maxeq,total);dd=max(dd,maxeq-total)
    return dict(n=n,mean_R=round(total/n,5),sum_R=round(total,4),
        PF=round(pos/neg,4) if neg else None,
        win_pct=round(100*sum(x>0 for x in values)/n,2),
        DD_R=round(dd,4))
def fmt(x):
    return "—" if x is None else ("+" if x>=0 else "")+f"{x:.4f}"
def main():
    files=sorted(OUT.glob("*_vx.json"))
    if len(files)!=55:
        print("RESULTS_INCOMPLETE",len(files),flush=True);return 3
    data=[json.loads(f.read_text(encoding="utf-8")) for f in files]
    trades=sorted((t for p in data for t in p.get("events",[])),
                  key=lambda x:(x["exit_time"],x["symbol"]))
    bymonth=defaultdict(list);byperiod=defaultdict(list)
    by_regime=defaultdict(list);by_strategy=defaultdict(list);by_side=defaultdict(list)
    for t in trades:
        bymonth[month(t["exit_time"])].append(t)
        byperiod[split(t["entry_time"])].append(t)
        by_regime[t["regime"]].append(t)
        by_strategy[t["playbook"]].append(t)
        by_side[t["side"]].append(t)
    actions=Counter();regimes=Counter();blockers=Counter();skips=Counter();symbols=[]
    for p in data:
        actions.update(p.get("decisions",{}));regimes.update(p.get("states",{}))
        blockers.update(p.get("wait_blockers",{}));skips.update(p.get("quality_skips",{}))
        row=dict(symbol=p["symbol"],status=p["status"],
           first_M5=p.get("history",{}).get("first_M5",""),
           last_M5=p.get("history",{}).get("last_M5",""),
           observations=p.get("observations",0),
           BUY=p.get("decisions",{}).get("BUY",0),
           SELL=p.get("decisions",{}).get("SELL",0),
           WAIT=p.get("decisions",{}).get("WAIT",0),
           modeled_trades=p.get("overall",{}).get("n",0),
           overall_avg_R=p.get("overall",{}).get("avg_R"),
           overall_sum_R=p.get("overall",{}).get("sum_R"),
           overall_PF=p.get("overall",{}).get("PF"),
           overall_win_pct=p.get("overall",{}).get("win_pct"))
        for label in LABELS:
            x=p.get("splits",{}).get(label,{})
            row[label+"_n"]=x.get("n",0)
            row[label+"_avg_R"]=x.get("avg_R")
        symbols.append(row)
    monthly=[dict(month=k,**stats(v),distinct_symbols=len({t["symbol"] for t in v}))
             for k,v in sorted(bymonth.items())]
    report=dict(kind="KATARINA_EXPLAINABLE_DECISION_ALL_55_RESEARCH_REPLAY",
        symbol_count=len(data),completed_symbols=sum(p["status"]=="OK" for p in data),
        errors=[dict(symbol=p["symbol"],status=p["status"],
                     detail=p.get("error")) for p in data if p["status"]!="OK"],
        candle_source="read-only broker MT5 closed M5/M15/H1",
        sample_every_M5_bars=36,
        historical_news_verified=False,
        technical_counterfactual_assumes_news_verified=True,
        live_authorized=False,broker_orders_sent=0,
        simulated_stop="1.2 times recent M5 ATR (minimum 4 x spread and 4 points)",
        modeled_target_R=1.8,modeled_hold_M5_bars=24,extra_cost_R=.03,
        position_portfolio_realism="NOT modeled: independent trade R only",
        total_observations=sum(p.get("observations",0) for p in data),
        total_signals=actions["BUY"]+actions["SELL"],
        decisions=dict(actions),states=dict(regimes),blockers=dict(blockers),
        data_skips=dict(skips),modeled_events=len(trades),
        overall=stats(trades),
        cost_stress_overall={str(extra):stats([dict(x,R=x["R"]-extra) for x in trades])
            for extra in (.10,.20)},
        splits={k:stats(byperiod[k]) for k in LABELS},
        monthly=monthly,by_symbol=symbols,
        by_regime={k:stats(v) for k,v in sorted(by_regime.items())},
        by_strategy={k:stats(v) for k,v in sorted(by_strategy.items())},
        by_side={k:stats(v) for k,v in sorted(by_side.items())},
        limitations=[
           "ONLY sampled one in every 36 M5 bars, not a bar-by-bar full scan.",
           "Historical news/blackouts are NOT verified. Signals are hypothetical assuming verified-clear news; actual safe decision is WAIT without archive.",
           "Retrospectively viewed 2025/2026 data are NOT a fresh independent out-of-sample validation.",
           "Broker MT5 timestamps are server time encoded in epoch fields; seasonal UTC/DST shifts not independently reconstructed.",
           "Entries use next M5 open and bar-recorded spread; hypothetical SL 1.2x M5 ATR, TP 1.8R, max 24 bars, extra .03R estimated cost.",
           "Same-bar stop+target is assumed stop-first; no true tick, swap, margin, commission reconciliation or severe slippage modeled.",
           "Independent trade sums are not account return; no portfolio correlation, exposure, overlapping positions or floating risk modeled.",
           "All outcomes are research-only, with no actual broker order or live-risk authorization."
        ])
    (OUT/"FINAL_SUMMARY.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    with (OUT/"per_pair.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(symbols[0]));w.writeheader();w.writerows(symbols)
    with (OUT/"monthly.csv").open("w",newline="",encoding="utf-8") as f:
        fields=list(monthly[0]) if monthly else ["month","n","mean_R","sum_R","PF","win_pct","DD_R","distinct_symbols"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(monthly)
    lines=[
     "# Backtest Decision Brain KATARINA — 55 Pair (12 Oktober 2026)","",
     "**Riset historis selesai. Ini bukan bukti strategi live menguntungkan.**","",
     "## Ringkasan faktual","",
     f"- Broker simbol: {len(data)}, berhasil: {report['completed_symbols']}, error/kurang data: {len(report['errors'])}.",
     f"- Snapshot historis yang dianalisis: {report['total_observations']:,}, sampling 1 dari 36 M5 bar (~3 jam) per pair.",
     f"- Keputusan: BUY {actions['BUY']:,}, SELL {actions['SELL']:,}, WAIT {actions['WAIT']:,}.",
     f"- Trade hipotetis dengan exit terdefinisi: {report['modeled_events']:,}; mean {fmt(report['overall']['mean_R'])}R, PF {fmt(report['overall']['PF'])}, win rate {fmt(report['overall']['win_pct'])}%.",
     "- Entry pada open M5 berikutnya, spread dari candle broker; SL 1,2 ATR M5, TP 1,8R, hold maksimum 24 M5 bar, biaya tambahan asumsi 0,03R.",
     "- News historis TIDAK divalidasi. Sinyal dihitung hanya untuk diagnosis teknis dengan berita DIASUMSIKAN aman; tidak boleh menjadi izin entry.",
     "- Backtest pasar menggunakan data lampau yang sudah pernah diteliti. Tidak boleh disebut independent forward/OOS.",
     "- Tambahan stress test biaya +0,10R/trade dan +0,20R/trade masing-masing menghasilkan rata-rata "
       +fmt(report["cost_stress_overall"]["0.1"]["mean_R"])+"R dan "
       +fmt(report["cost_stress_overall"]["0.2"]["mean_R"])+"R.",
     "",
     "## Total hasil retrospektif per periode","",
     "| Periode | Trade | Avg R | Jumlah R | PF | Win% |",
     "|---|---:|---:|---:|---:|---:|"
    ]
    for k in LABELS:
        s=report["splits"][k]
        lines.append(f"| {k} | {s['n']} | {fmt(s['mean_R'])} | {fmt(s['sum_R'])} | {fmt(s['PF'])} | {fmt(s['win_pct'])}% |")
    lines+=["","## Performa menurut kondisi pasar dan strategi","",
        "Sinyal ini hanya kandidat teknis dengan asumsi berita valid, tidak termasuk Risk Governor live.","",
        "| Kondisi | Trade | Mean R | PF | Win% |","|---|---:|---:|---:|---:|"]
    for k,v in report["by_regime"].items():
        lines.append(f"| {k} | {v['n']} | {fmt(v['mean_R'])} | {fmt(v['PF'])} | {fmt(v['win_pct'])}% |")
    lines+=["","| Strategi | Trade | Mean R | PF | Win% |","|---|---:|---:|---:|---:|"]
    for k,v in report["by_strategy"].items():
        lines.append(f"| {k} | {v['n']} | {fmt(v['mean_R'])} | {fmt(v['PF'])} | {fmt(v['win_pct'])}% |")
    lines+=["","## Data lengkap semua pair","",
            "| Pair | Status | Snapshot | BUY | SELL | WAIT | Trade | Avg R | PF | 2025 n/R | Jan–Mei 2026 n/R | Jun–Okt 2026 n/R |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|"]
    for p in symbols:
        col=lambda q:str(p[q+"_n"])+"/"+fmt(p[q+"_avg_R"])
        lines.append(f"| {p['symbol']} | {p['status']} | {p['observations']} | {p['BUY']} | {p['SELL']} | {p['WAIT']} | {p['modeled_trades']} | {fmt(p['overall_avg_R'])} | {fmt(p['overall_PF'])} | {col('2025_available')} | {col('2026_Jan_May')} | {col('2026_Jun_Oct')} |")
    lines+=["","## Rekap seluruh entry multipair per bulan","",
        "Penjumlahan R **bukan** return akun, karena modal, ukuran kontrak dan exposure bersamaan tidak dimodelkan.","",
        "| Bulan | Trade | Avg R | Total R | Pair dengan entry |",
        "|---|---:|---:|---:|---:|"]
    for q in monthly:
        lines.append(f"| {q['month']} | {q['n']} | {fmt(q['mean_R'])} | {fmt(q['sum_R'])} | {q['distinct_symbols']} |")
    lines+=["","## Mengapa KATARINA tidak entry?","",
        "Alasan WAIT paling banyak: "+", ".join(f"{k}: {v:,}" for k,v in blockers.most_common(10))+".",
        "",
        "## Batasan wajib disebutkan",""]
    lines.extend("- "+x for x in report["limitations"])
    lines+=["","## Keputusan","",
        "**Tidak ada promosi live.** Ini diagnostik menyeluruh untuk kualitas keputusan per pair; performa buruk/tidak cukup sampel harus dinyatakan gagal/belum terbukti.",
        "File audit: per_pair.csv, monthly.csv, FINAL_SUMMARY.json. Bar mentah dan event individu tetap privat di VPS.",
        ""]
    (OUT/"LAPORAN_LENGKAP.md").write_text("\n".join(lines),encoding="utf-8")
    print("FINAL_REPORT",json.dumps(dict(symbols=report["completed_symbols"],errors=report["errors"],
         observations=report["total_observations"],actions=report["decisions"],overall=report["overall"],
         splits=report["splits"],months=len(monthly)),ensure_ascii=False),flush=True)
    return 0
if __name__=="__main__":raise SystemExit(main())