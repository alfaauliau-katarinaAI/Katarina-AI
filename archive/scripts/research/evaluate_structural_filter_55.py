"""Re-score exactly the prior 55-symbol decisions at the original signal time.

Fair paired comparison: preserve the earlier M5 next-open/SL/TP model and
apply a *causal* structural filter to its recorded historical signals only.
Never silently count retuned filters as independent OOS validation.
"""
from __future__ import annotations
import csv,json,math,sys,time
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import MetaTrader5 as mt5
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"/"research"))
from backtest_explainable_55_pairs import (OUT as OLD,get_bars,sensors,
         bisected_indices, TIMEFRAME,stats,split)
from katarina.intelligence.structural_entry_quality import StructuralEntryQuality

OUT=OLD/"structural_quality_v1"
OUT.mkdir(parents=True,exist_ok=True)
def main():
    now=time.perf_counter()
    if not mt5.initialize():raise RuntimeError("MT5 not connected")
    term=mt5.terminal_info()
    if term is None or term.trade_allowed:
        mt5.shutdown();raise RuntimeError("refuse research with live trading enabled")
    quality=StructuralEntryQuality()
    all_before=[];all_after=[];rows=[];failure=[];signals=0
    all_blockers=Counter();all_evidence=Counter()
    for i,path in enumerate(sorted(OLD.glob("*_vx.json"))):
        p=json.loads(path.read_text(encoding="utf-8"))
        sym=p["symbol"];original=p.get("events",[])
        signals+=len(original);all_before.extend(original)
        if not original:
            rows.append(dict(symbol=sym,baseline_n=0,selected_n=0,
                             baseline_avg_R="",selected_avg_R="",baseline_PF="",selected_PF="",
                             baseline_sum_R=0,selected_sum_R=0,rejects=0,errors=0))
            print("PAIR",i+1,sym,"NO_SIGNAL",flush=True)
            continue
        mt5.symbol_select(sym,True)
        info=mt5.symbol_info(sym)
        if info is None:
            failure.append(dict(symbol=sym,error="missing_info"));continue
        market={}
        for key,(tf,period,count) in TIMEFRAME.items():
            arr=get_bars(sym,tf,count)
            if arr is None:
                failure.append(dict(symbol=sym,error="missing_history_"+key));break
            market[key]=(arr,sensors(arr,period),period)
        if len(market)!=3:continue
        times={k:a["time"].astype(np.int64) for k,(a,_,_) in market.items()}
        selected=[];discarded=Counter();errors=0;accepted_reasons=Counter()
        for t in original:
            cut=int(t["entry_time"])
            e=bisected_indices(times["M5"],cut,300)
            if e<55 or e>=len(times["M5"]) or int(times["M5"][e-1])!=cut-300:
                discarded["signal_M5_not_found"]+=1;errors+=1;continue
            slices={}
            for tf,(_,_,period) in market.items():
                end=bisected_indices(times[tf],cut,period)
                if end<55 or end>len(times[tf]):
                    discarded["higher_frame_incomplete_"+tf]+=1
                    errors+=1;break
                if int(times[tf][end-1])+period>cut:
                    raise AssertionError("future higher timeframe leakage")
                slices[tf]=market[tf][1][end-55:end]
            if len(slices)!=3:continue
            spread=float(market["M5"][0]["spread"][e-1])*float(info.point)
            if spread<=0:
                discarded["invalid_signal_spread"]+=1;continue
            try:
                q=quality.assess(side=t["side"],playbook=t["playbook"],
                    m5=slices["M5"],m15=slices["M15"],h1=slices["H1"],
                    spread=spread,as_of_utc=datetime.fromtimestamp(cut,timezone.utc))
            except (ValueError,TypeError,OverflowError) as exc:
                discarded["rejected_sensor_"+type(exc).__name__]+=1;errors+=1;continue
            if q.eligible:
                selected.append(dict(t,entry_score=q.score,
                         evidence=q.evidence,structural_rr=q.geometric_room_R))
                accepted_reasons.update(q.evidence)
            else:
                discarded.update(q.blockers)
        all_after.extend(selected)
        all_blockers.update(discarded)
        all_evidence.update(accepted_reasons)
        origstats=stats(original);selectstats=stats(selected)
        rows.append(dict(symbol=sym,baseline_n=len(original),selected_n=len(selected),
             baseline_avg_R=origstats["avg_R"],selected_avg_R=selectstats["avg_R"],
             baseline_PF=origstats["PF"],selected_PF=selectstats["PF"],
             baseline_sum_R=origstats["sum_R"],selected_sum_R=selectstats["sum_R"],
             rejects=len(original)-len(selected),errors=errors))
        print("PAIR",i+1,sym,"original",len(original),"accepted",len(selected),
              "mean",selectstats["avg_R"],"sensor_err",errors,flush=True)
        if errors:failure.append(dict(symbol=sym,error="signal_matching_errors",count=errors))
    mt5.shutdown()
    # Chronological aggregation avoids artificial file-order drawdown.
    # This remains cumulative *trade R*, NOT a realizable portfolio curve.
    all_before.sort(key=lambda x:(x["exit_time"],x["symbol"]))
    all_after.sort(key=lambda x:(x["exit_time"],x["symbol"]))
    by_split={k:{"baseline":stats([x for x in all_before if split(x["entry_time"])==k]),
                 "structural":stats([x for x in all_after if split(x["entry_time"])==k])}
              for k in ("2025_available","2026_Jan_May","2026_Jun_Oct")}
    by_strategy={k:{"baseline":stats([x for x in all_before if x["playbook"]==k]),
                    "structural":stats([x for x in all_after if x["playbook"]==k])}
              for k in sorted({x["playbook"] for x in all_before})}
    by_side={k:{"baseline":stats([x for x in all_before if x["side"]==k]),
                "structural":stats([x for x in all_after if x["side"]==k])}
             for k in ("BUY","SELL")}
    result=dict(kind="KATARINA_PAIRED_STRUCTURAL_ENTRY_GATE_55",
        symbols_total=55,symbols_rows=len(rows),symbol_failures=failure,
        original_signals=signals,selected_signals=len(all_after),
        sample_stride_M5=36,
        filtering="original signals only; no new entries invented",
        cost_and_exit="identical pre-existing 1.2x M5 ATR stop, 1.8R target, 24 M5 bars; 0.03R extra modeled cost",
        historical_news_verified=False,unseen_holdout=False,
        live_execution_authorized=False,orders_sent=0,
        baseline=stats(all_before),structural=stats(all_after),
        excess_cost_stress={
            str(v):stats([dict(x,R=x["R"]-v) for x in all_after]) for v in (.1,.2)
        },
        periods=by_split,strategies=by_strategy,sides=by_side,
        blocker_counts=dict(all_blockers),accepted_evidence=dict(all_evidence),
        per_pair=rows,duration_sec=round(time.perf_counter()-now,2))
    (OUT/"FINAL_COMPARISON.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    with (OUT/"per_pair_comparison.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    md=["# Audit & uji ulang KATARINA — Entry Quality Structural V1",
        "","**Eksperimen retrospektif; tidak ada strategi yang diizinkan live.**","",
        "## Sebelum vs sesudah filter struktur (exit dipertahankan identik)","",
        "| Metrik | Entry lama | Filter struktur baru |","|---|---:|---:|",
        f"| Jumlah transaksi | {result['baseline']['n']} | {result['structural']['n']} |",
        f"| Rata-rata R | {result['baseline']['avg_R']} | {result['structural']['avg_R']} |",
        f"| PF | {result['baseline']['PF']} | {result['structural']['PF']} |",
        f"| Win rate (%) | {result['baseline']['win_pct']} | {result['structural']['win_pct']} |",
        f"| Total R semua transaksi (bukan return portofolio) | {result['baseline']['sum_R']} | {result['structural']['sum_R']} |","",
        "## Periode historis yang sudah pernah dilihat (BUKAN OOS independen)","",
        "| Segmen | Lama n / mean R | Baru n / mean R |","|---|---:|---:|"]
    for k, v in by_split.items():
        md.append(f"| {k} | {v['baseline']['n']} / {v['baseline']['avg_R']} | {v['structural']['n']} / {v['structural']['avg_R']} |")
    md.extend(["","## Per strategi","",
        "| Strategi | Lama n / mean R | Baru n / mean R |","|---|---:|---:|"])
    for k,v in by_strategy.items():
        md.append(f"| {k} | {v['baseline']['n']} / {v['baseline']['avg_R']} | {v['structural']['n']} / {v['structural']['avg_R']} |")
    md.extend(["","## 55 pair","",
         "| Pair | Lama n | Lama mean R | Baru n | Baru mean R | Error data |",
         "|---|---:|---:|---:|---:|---:|"])
    for p in rows:
        md.append(f"| {p['symbol']} | {p['baseline_n']} | {p['baseline_avg_R']} | {p['selected_n']} | {p['selected_avg_R']} | {p['errors']} |")
    md.extend(["","## Audit dan keterbatasan",
        "- Original backtest memakai **sampling 1 dari 36 candle M5**. Tidak mengukur seluruh peluang; tidak bisa dipakai untuk menghitung pertumbuhan portofolio.",
        "- Dibandingkan subset entry lama pada waktu sinyal yang identik. Model spread, entry di candle berikutnya, stop-first, SL/TP tidak diubah, agar perbedaan disebabkan oleh filter.",
        "- Filter membaca hanya candle M5/M15/H1 **yang sudah tutup pada waktu sinyal**; kualitas struktur: trend location, liquidity sweep, wick, engulf, MTF agreement, biaya, ruang ke target.",
        "- Snapshot broker mengandung timestamp server; *absolute UTC, DST, sesi makro* tidak diverifikasi secara historis. Timing antar-timeframe konsisten secara internal.",
        "- Tidak ada arsip kalender berita valid per timestamp: semua hasil hanyalah **what-if berita aman**; keputusan live tetap WAIT.",
        "- SL/TP masih model sintetis: SL 1,2x ATR M5, TP 1,8R, hold 24 candle, biaya estimasi tambahan 0,03R. Tidak ada tick-level fill, margin, swaps, broker commission reconciliation.",
        "- Entry rules diperiksa pada rentang historis 2025–2026 yang telah digunakan sebelumnya; **hasil membaik sekalipun bukan bukti keunggulan OOS**.",
        "- Nonoverlap hanya dijaga *di dalam satu pair* oleh backtest dasar; tidak ada exposure global atau kurva balance yang akurat.",
        "- Filtering yang memperkecil jumlah transaksi tidak serta merta memaksimalkan growth; laporkan sampel dan expectancy secara terpisah.",
        "- Tidak memodifikasi Risk Governor, tidak ada izin open order.","",
        "## Verdict",
        ("**Belum layak promosi strategi**; lanjutkan demonstrasi paper dan audit tick-level, serta data OOS yang benar-benar baru."
         if result["structural"]["avg_R"] is None or result["structural"]["avg_R"]<=0
         else "**Indikasi awal membaik secara retrospektif, tetapi belum dapat dipromosikan** tanpa OOS independen dan stress test tick."),
        ])
    (OUT/"LAPORAN_FILTER_STRUKTUR.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print("FINAL",json.dumps({k:result[k] for k in ("symbols_total","symbols_rows","symbol_failures","baseline","structural","periods","duration_sec")},ensure_ascii=False),flush=True)
if __name__=="__main__":main()