"""Reproducible executive audit with intraday priority and scalp veto."""
from __future__ import annotations
import json,csv
from collections import Counter
from pathlib import Path
from datetime import datetime
B=Path(r"C:\KatarinaDev\decision-backtest-20261012\intraday_scalp_full_m5_v5")
def pretty(x):
    if x is None:return "n/a"
    return f"{x:,.3f}"
def main():
    r=json.loads((B/"FULL_M5_55_FINAL.json").read_text(encoding="utf-8"))
    a=json.loads((B/"BRAIN_AGREEMENT_AUDIT.json").read_text(encoding="utf-8"))
    b=json.loads((B/"BROKER_CONTRACT_AUDIT.json").read_text(encoding="utf-8"))
    ticks=json.loads((B/"TICK_SPREAD_SAMPLES.json").read_text(encoding="utf-8"))
    perf=r["policies"]
    intr=perf["INTRADAY_ONLY"]
    mix=perf["INTRADAY_FIRST_SCALP_EXTREME"]
    scal=perf["SCALP_EXTREME_ONLY"]
    blind=perf["ALPHABETICAL_MATCHED"]
    months=intr["by_month"]
    npos=sum(x["avg_R"]>0 for x in months.values())
    nneg=sum(x["avg_R"]<0 for x in months.values())
    counts=Counter()
    with (B/"COMBINED_POLICY_TRADES.csv").open(encoding="utf-8") as f:
        for x in csv.DictReader(f):counts[x["symbol"]]+=1
    doc=[
      "# KATARINA Brain V5 — Full M5 Intraday First / Extreme Scalping",
      "",
      "**Status: READ-ONLY RESEARCH. No live orders, no trade authorization, no proven profitable strategy.**",
      "",
      "Tanggal pembekuan eksperimen: 12 Oktober 2026. Dataset 2025–Oktober 2026 sudah dilihat pada riset sebelumnya; ini *in-sample, not independent out-of-sample*. Jangan memperkirakan return ke depan dari kurva model ini.",
      "",
      "## Rancangan yang diperiksa",
      "",
      "- Memindai setiap M5 CLOSED bar yang valid untuk **55 pair**, bukan 3 snapshot harian seperti V4.",
      "- Tahap pertama memakai prefilter cepat, berbasis closed H1/M15 trend + actual M5 pullback/displacement. Ini modul hipotesis baru, **bukan** setiap-candle full MarketDecisionPipeline atau model neural terlatih.",
      "- **Intraday (prioritas)**: konfirmasi arah H1/M15, setidaknya dua candle koreksi M5 sebelumnya, displacement >=0,42 ATR, spread <=0,22 ATR. Struktur SL dari extreme lokal + buffer; TP 1,8R; batas waktu 48 M5 (4 jam).",
      "- **Scalp ekstrem (opsi riset)**: sweep+reclaim level 20 candle, rejection wick >=0,45 ATR, tick-volume proxy >=1,25 rerata, spread <=0,12 ATR, H1 mendukung. SL invalidasi candle + buffer, TP 1,3R; maksimal 8 M5 (40 menit).",
      "- Ranking antar-pair dilakukan pada timestamp M5 yang sama tanpa mengetahui return masa depan; jika bersamaan, intraday didahulukan. Pembanding menggunakan pemilihan alfabetis pada kesempatan setara.",
      "- Simulasi satu posisi sekaligus, maksimal dua entry per hari kode waktu broker. Risiko model 0,25% intraday, 0,10% scalp ekstrem, nominal kapasitas harian 0,50%.",
      "- Entry M5 next open, bid/ask diturunkan dari OHLC Bid+spread per bar, stop-first bila SL/TP terjadi di bar sama, slippage dua sisi masing-masing satu point, biaya tambahan intraday 0,03R, scalp 0,06R. Broker round-trip commission tidak tersedia secara historis.",
      "",
      "## Data dan hasil portofolio",
      "",
      f"- Simbol: **{r['number_symbols_fetched']} / {r['number_symbols_requested']}**; candle M5 yang dipindai: **{r['full_M5_bars_evaluated']:,}**.",
      f"- Hari pengamatan dengan >=20 pair memiliki >=60 bar: **{r['comparable_days']:,}**.",
      f"- Kandidat setup: **{r['total_candidates']:,}** dari **{r['candidate_windows']:,}** timestamp berbeda. Kandidat != transaksi.",
      "",
      "| Kebijakan | Trades | Days positive / traded | Avg R | Profit factor | Return model | Max DD model |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for label,x in (
        ("Intraday only",intr),
        ("Intraday first + extreme scalp",mix),
        ("Extreme scalp only",scal),
        ("Alphabetical control",blind)):
        doc.append(f"| {label} | {x['n']} | {x['positive_trade_days']} / {x['days_traded']} | {pretty(x['trade_stats']['avg_R'])} | {pretty(x['trade_stats']['PF'])} | {pretty(x['return_model_pct'])}% | {pretty(x['max_drawdown_pct'])}% |")
    doc.extend(["",
      "**No verified sustainable edge:** intraday-only 658 trades, 187 profitable days and 142 loss days, +0,58% *modeled* return, but PF 1,009 and avg only +0,00556R. That is effectively break-even and fragile.",
      "Adding scalp changes selection of earlier daily opportunities (11 scalp entries selected in combined policy) and makes combined performance negative. Pure scalping is decisively negative under tested rules.",
      "",
      "## Broker cost stress (intraday only)",
      "",
      "| Added cost beyond original model | PF | Avg R | Return model | Max DD |",
      "|---|---:|---:|---:|---:|"])
    for name,x in (
        ("none",{"PF":intr["trade_stats"]["PF"],"mean_R":intr["trade_stats"]["avg_R"],
                 "return_pct":intr["return_model_pct"],"max_dd_pct":intr["max_drawdown_pct"]}),
        ("+0.10R",r["cost_stress"]["0.1"]["INTRADAY_ONLY"]),
        ("+0.20R",r["cost_stress"]["0.2"]["INTRADAY_ONLY"])):
        doc.append(f"| {name} | {pretty(x['PF'])} | {pretty(x['mean_R'])} | {pretty(x['return_pct'])}% | {pretty(x['max_dd_pct'])}% |")
    doc.extend(["",
      "This stress uses illustrative per-trade R cost increments and is not the precise USD broker bill.",
      "",
      "## Historical consistency — intraday",
      "",
      f"Profitable months: **{npos} / {len(months)}**; negative months **{nneg}**.",
      "",
      "| Broker-coded month | n | Average R | PF |",
      "|---|---:|---:|---:|"])
    for mon,m in sorted(months.items()):
        doc.append(f"| {mon} | {m['n']} | {pretty(m['avg_R'])} | {pretty(m['PF'])} |")
    doc.extend(["",
      "## Brain agreement — essential integration blocker",
      "",
      f"- V5 independently preselected **{a['original_selected']}** trades.",
      f"- Previous Explainable Market Brain agreed with direction in **{a['counters']['brain_side_agree']}** of them.",
      f"- Only **{a['counters']['strict_full_agree']}** also passed Brain's structural quality and matching true semantic setup.",
      "- This is a post-selection audit, not a revised policy simulation: it does not select the second-best asset when Brain vetoes the top candidate. The numerical V5 return must not be presented as old Brain's return.",
      "- **Action:** keep V5 isolated in research; require consistent Brain/entry quality decisions before any production promotion.",
      "",
      "## Broker contract and execution limitations",
      "",
      f"- Account report currency (not account ID): **{b['account_currency']}**.",
      f"- Current broker symbol specifications indicate minimum-lot hypothetical affordability in the **same 658 combined-policy entries**: equity 1,000 USD: **{b['counts']['feasible_1000']}**; 5,000 USD: **{b['counts']['feasible_5000']}**; 10,000 USD: **{b['counts']['feasible_10000']}**.",
      "- These are hypothetical capital scenarios, not the actual account capital. Current symbol tick values, minimum lots and stop levels cannot certify historical tradability or margin requirements.",
      f"- Spot-check 16 historical tick requests (EURUSD/XAUUSD/US30/JPN225 over four calendar dates): **{ticks['usable_samples']}/16** returned quote-change ticks near requested time.",
      "- Historical XAUUSD tick data were not available around several 2025–2026 reference dates, despite existing M5 OHLC; this prevents full tick-level execution validation.",
      "- MetaTrader bar spread and per-symbol tick value are broker observations, but the paper fill uses next-bar OHLC, not actual tick sequencing. Commissions, swaps, partial fills, time zones and historical exchange conversion remain unresolved.",
      "",
      "## Trading-mode policy",
      "",
      "**Primary: INTRADAY RESEARCH ONLY.** Only a preliminary, negligible theoretical edge before full costs; no live permission.",
      "",
      "**SCALP_EXTREME: PAPER RESEARCH ONLY, DEFAULT DISABLED.** The tested version worsens expectancy. Use separately only to gather new causal event evidence, not automatically for trading.",
      "",
      "**When no verified candidate exists: WAIT.** Intraday profits cannot be guaranteed each day and avoiding a bad trade is an explicit design requirement.",
      "",
      "### Work needed before any maturity claim",
      "",
      "1. Reconcile the fast full-M5 prefilter and ExplainableMarketDecisionPipeline using identical causal decision inputs. Verify multi-pair portfolio replay with the Brain gate actually in force.",
      "2. Reconstruct historical tick bid/ask fills, spread variation, commission and swap at sufficient sample coverage, plus margin, volume steps, risk sizing and session/time-zone alignment.",
      "3. Freeze one set of rules and perform a truly new forward or independent chronological holdout after freeze; evaluate expected R, PF, max equity drawdown and monthly consistency with costs.",
      "4. Do not deploy live until the external evidence and risk governor explicitly support it. No order_send was called.",
      "",
      "Output paths on VPS: C:\\KatarinaDev\\decision-backtest-20261012\\intraday_scalp_full_m5_v5\\",
      "",
      "Primary research code: src/katarina/intelligence/intraday_scalp_research.py; scripts/research/backtest_full_m5_intraday_scalp_v5.py.",
      "",
      "Docs basis: MQL5 Python copy_rates_from_pos, copy_ticks_from, symbol_info. Broker-specific commission, time-zone and instrument behavior require separate verification.",
      ""])
    (B/"LAPORAN_INTRADAY_SCALP_V5.md").write_text("\n".join(doc),encoding="utf-8")
    snap=dict(
        decision="INTRADAY_RESEARCH_ONLY__SCALP_EXTREME_DISABLED",
        reason="Full M5 intraday theoretical PF only 1.0093; +0.10R fee turns expectancy negative; 31 of 658 selected entries pass prior Brain semantic/quality corroboration",
        model_not_live=True,live_trading_allowed=False,orders_sent=0,
        symbols=r["number_symbols_fetched"],M5_checked=r["full_M5_bars_evaluated"],
        trade_days=intr["days_traded"],
        profitable_trade_days=intr["positive_trade_days"],
        intraday=dict(trades=intr["n"],PF=intr["trade_stats"]["PF"],
            meanR=intr["trade_stats"]["avg_R"],model_return_pct=intr["return_model_pct"],
            cost_0_10R_return_pct=r["cost_stress"]["0.1"]["INTRADAY_ONLY"]["return_pct"]),
        scalp=dict(trades=scal["n"],PF=scal["trade_stats"]["PF"],
            meanR=scal["trade_stats"]["avg_R"]),
        brain_agreement=a["counters"]["strict_full_agree"],
        scenario_1000_USD_minlot_feasible=b["counts"]["feasible_1000"],
        tick_sample_valid=ticks["usable_samples"],
        out_of_sample=False,
        historical_news_verified=False,
        tick_fills_fully_validated=False,
        commission_reconciled=False)
    (B/"V5_POLICY_DECISION.json").write_text(json.dumps(snap,indent=2),encoding="utf-8")
    print("REPORT_V5_DONE",json.dumps(snap,ensure_ascii=False),flush=True)
if __name__=="__main__":main()