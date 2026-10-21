"""Public-data pilot: 4 strategy families on genuine BID/ASK M1 candles.

Downloads Dukascopy's publicly served LZMA daily minute candles directly
inside GitHub Actions. NOT broker VPS data; not a live execution system.
Historical research only; no account, MT5, trade API, GitHub write token.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import lzma
from math import isfinite
from pathlib import Path
import struct
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from katarina.intelligence.lab.adaptive_strategy_library import (
    ClosedBar, StrategyHypothesis, propose_closed_candle_strategies)

BASE = "https://datafeed.dukascopy.com/datafeed"
RECORD = struct.Struct(">IIIIIf")  # seconds, open, close, low, high, volume
SCALE = {
    "EURUSD": 100000, "GBPUSD": 100000, "AUDUSD": 100000,
    "NZDUSD": 100000, "USDCAD": 100000, "USDCHF": 100000,
    "EURGBP": 100000, "EURAUD": 100000,
    "USDJPY": 1000, "EURJPY": 1000, "GBPJPY": 1000, "AUDJPY": 1000,
    "XAUUSD": 1000,
}
METHODS = ("TREND_PULLBACK", "BREAKOUT_RETEST", "LIQUIDITY_SWEEP_RECLAIM",
           "RANGE_MEAN_REVERSION")
MAX_PUBLIC_DAYS = 25  # keep downloads bounded
MAX_SYMBOLS_PER_RUN = 4  # use a separate bounded runner matrix for wider scope


@dataclass(frozen=True)
class QuoteCandle:
    time: int  # minute or resampled bar CLOSE in UTC
    bid_open: float
    bid_high: float
    bid_low: float
    bid_close: float
    ask_open: float
    ask_high: float
    ask_low: float
    ask_close: float

    def bid(self):
        return ClosedBar(self.time, self.bid_open, self.bid_high,
                         self.bid_low, self.bid_close)

    def spread_open(self):
        return self.ask_open - self.bid_open

    def spread_close(self):
        return self.ask_close - self.bid_close


def parse_minute_file(payload: bytes, day: date, scale: int, *, side: str):
    """Decode fixed 24-byte public candles; reject corrupt/ambiguous files."""
    if side not in ("BID", "ASK") or scale <= 0:
        raise ValueError("invalid_market_decoder_config")
    if not payload:
        return {}
    raw = lzma.decompress(payload)
    if len(raw) % RECORD.size:
        raise ValueError("invalid_candle_record_length")
    first = int(datetime(day.year, day.month, day.day,
                         tzinfo=timezone.utc).timestamp())
    out = {}
    for i in range(0, len(raw), RECORD.size):
        offset, o, c, lo, hi, volume = RECORD.unpack_from(raw, i)
        if offset >= 86400 or offset % 60 != 0 or offset in out:
            raise ValueError("invalid_or_duplicate_minute_offset")
        if min(o, c, lo, hi) <= 0 or hi < max(o, c, lo) or lo > min(o, c, hi):
            raise ValueError("invalid_public_minute_ohlc")
        if not isfinite(volume) or volume < 0:
            raise ValueError("invalid_public_minute_volume")
        out[offset] = (first + offset + 60,
                       o/scale, hi/scale, lo/scale, c/scale)
    return out


def fetch_daily(symbol: str, day: date, side: str, *, opener=urlopen):
    """404 and zero-length response mean no market data, never synthetic data."""
    if symbol not in SCALE or side not in ("BID", "ASK"):
        raise ValueError("unsupported_public_data_symbol")
    name = f"{side}_candles_min_1.bi5"
    uri = f"{BASE}/{symbol}/{day.year}/{day.month-1:02d}/{day.day:02d}/{name}"
    try:
        with opener(Request(uri, headers={"User-Agent": "Katarina-Research/1.0"}),
                    timeout=25) as response:
            data = response.read(12_000_001)
    except HTTPError as e:
        if e.code == 404:
            return None
        raise RuntimeError(f"public_data_http_{e.code}") from e
    except (URLError, TimeoutError) as e:
        raise RuntimeError("public_data_unavailable") from e
    if len(data) > 12_000_000:
        raise RuntimeError("unexpected_public_data_size")
    return data or None


def load_public_minutes(symbol: str, begin: date, end: date, *, fetch=fetch_daily):
    days = (end-begin).days
    if symbol not in SCALE or not 0 < days <= MAX_PUBLIC_DAYS:
        raise ValueError("invalid_public_scope")
    collected = []
    coverage = {"calendar_days": days, "complete_days": 0,
                "empty_days": 0, "minutes": 0}
    for n in range(days):
        day = begin + timedelta(days=n)
        bid_data = fetch(symbol, day, "BID")
        ask_data = fetch(symbol, day, "ASK")
        if bid_data is None and ask_data is None:
            coverage["empty_days"] += 1
            continue
        if bid_data is None or ask_data is None:
            raise RuntimeError(f"partial_bid_ask_data_{symbol}_{day}")
        bid = parse_minute_file(bid_data, day, SCALE[symbol], side="BID")
        ask = parse_minute_file(ask_data, day, SCALE[symbol], side="ASK")
        # The feed sometimes has side-specific missing minutes. Skip those
        # minutes, never fill the gaps with interpolated prices.
        if not bid or not ask:
            coverage["empty_days"] += 1
            continue
        for key in sorted(set(bid) & set(ask)):
            b = bid[key]; a = ask[key]
            if b[0] != a[0] or a[4] < b[4] or a[1] < b[1]:
                raise ValueError("crossed_public_bid_ask")
            collected.append(QuoteCandle(b[0],b[1],b[2],b[3],b[4],
                                         a[1],a[2],a[3],a[4]))
        coverage["complete_days"] += 1
    collected.sort(key=lambda b:b.time)
    if len({b.time for b in collected}) != len(collected):
        raise ValueError("duplicate_public_timestamps")
    coverage["minutes"] = len(collected)
    return collected, coverage


def aggregate(bars: list[QuoteCandle], minutes: int):
    size = minutes*60
    groups = defaultdict(list)
    for b in bars:
        group_end = ((b.time-1)//size + 1)*size
        groups[group_end].append(b)
    result=[]
    for end, group in sorted(groups.items()):
        if (len(group) != minutes or group[0].time != end-size+60
                or group[-1].time != end or
                any(b.time-a.time != 60 for a,b in zip(group,group[1:]))):
            continue  # never create partial/incomplete lookahead bars
        result.append(QuoteCandle(
            end, group[0].bid_open, max(x.bid_high for x in group),
            min(x.bid_low for x in group), group[-1].bid_close,
            group[0].ask_open, max(x.ask_high for x in group),
            min(x.ask_low for x in group), group[-1].ask_close))
    return result


def calculate_fill(hypothesis: StrategyHypothesis, entry: QuoteCandle,
                   future: list[QuoteCandle], *, max_hold=24,
                   assumed_fee_r=.03, slippage_point=.0):
    """Model trade with real recorded bid/ask candles, adverse stop-first.

    Not a tick/queue/margin replay. Signals at candle CLOSE, entries next bar.
    """
    side = hypothesis.side
    if side not in ("BUY", "SELL") or not future or not (
            0 <= assumed_fee_r <= .5 and slippage_point >= 0):
        raise ValueError("invalid_model_trade_inputs")
    if side == "BUY":
        entry_price = entry.ask_open + slippage_point
        stop = hypothesis.stop
        target = hypothesis.target
        risk = entry_price-stop
    else:
        entry_price = entry.bid_open-slippage_point
        # Hypotheses derive levels from BID OHLC. Short positions close on ASK.
        # Shift both levels by observed entry spread; use future ASK path.
        stop = hypothesis.stop+entry.spread_open()
        target = hypothesis.target+entry.spread_open()
        risk = stop-entry_price
    if risk <= 0 or target <= 0 or stop <= 0:
        return None
    # Bad opening gaps invalidate the intended geometry, rather than
    # silently turning a profitable stop/target into a new proposal.
    reward = target-entry_price if side == "BUY" else entry_price-target
    if reward <= 0 or reward/risk < .6 or risk <= 2*slippage_point:
        return None
    final = 0.0
    reason="TIME"
    exit_at = entry.time
    for candle in future[:max_hold]:
        if side == "BUY":
            sl = candle.bid_low <= stop
            tp = candle.bid_high >= target
            if sl:
                final=stop-slippage_point
                reason="SL_STOP_FIRST" if tp else "SL"
            elif tp:
                final=target-slippage_point
                reason="TP"
            else:
                final=candle.bid_close-slippage_point
        else:
            sl=candle.ask_high >= stop
            tp=candle.ask_low <= target
            if sl:
                final=stop+slippage_point
                reason="SL_STOP_FIRST" if tp else "SL"
            elif tp:
                final=target+slippage_point
                reason="TP"
            else:
                final=candle.ask_close+slippage_point
        exit_at=candle.time
        if sl or tp:
            break
    gross = (final-entry_price if side == "BUY" else entry_price-final)/risk
    return {"symbol":hypothesis.symbol, "strategy":hypothesis.strategy_id,
            "side":side, "regime":hypothesis.regime,
            "signal_at":hypothesis.signal_at, "entry_at":entry.time-300,
            "exit_at":exit_at, "R":round(gross-assumed_fee_r,6),
            "outcome":reason, "risk_price":round(risk,8)}


def simulate_symbol(symbol: str, minutes: list[QuoteCandle], *,
                    max_hold=24, assumed_fee_r=.03):
    m5=aggregate(minutes,5)
    h1=aggregate(minutes,60)
    if len(m5)<80 or len(h1)<16:
        return [],{"status":"INSUFFICIENT_CLOSED_HISTORY",
                    "m5":len(m5),"h1":len(h1)}
    clock=[x.time for x in h1]
    positions_until={}
    trades=[]
    count=Counter()
    for i in range(30,len(m5)-max_hold-1):
        now=m5[i].time
        previous=m5[i-29:i+1]
        if any(b.time-a.time!=300 for a,b in zip(previous,previous[1:])):
            count["m5_gap"]+=1
            continue
        j=bisect_right(clock,now)
        if j<16 or m5[i+1].time != now+300:
            count["h1_warmup_or_entry_gap"]+=1
            continue
        recent_h1=h1[max(0,j-16):j]
        if len(recent_h1)!=16:
            continue
        # All H1 rows have candle CLOSE <= now. Same for M5. No future bars
        # are passed to the strategy generator.
        candidates=propose_closed_candle_strategies(
            symbol,tuple(b.bid() for b in previous),
            tuple(b.bid() for b in recent_h1),now=now,
            spread=max(0,m5[i].spread_close()),point=1/SCALE[symbol])
        count["signals"]+=len(candidates)
        for candidate in candidates:
            key=(candidate.strategy_id,candidate.side)
            if positions_until.get(key,0)>now:
                continue
            future=m5[i+1:i+1+max_hold]
            if any(b.time-a.time!=300 for a,b in zip(future,future[1:])):
                count["future_gap_skipped"]+=1
                continue
            trade=calculate_fill(candidate,m5[i+1],future,
                                 max_hold=max_hold,assumed_fee_r=assumed_fee_r,
                                 slippage_point=1/SCALE[symbol])
            if trade is not None:
                positions_until[key]=trade["exit_at"]
                trades.append(trade)
    return trades,{"status":"OK","m5":len(m5),"h1":len(h1),
                   "signals":count["signals"],"skips":dict(count)}


def metrics(trades, extra_cost_r=0.):
    values=[t["R"]-extra_cost_r for t in trades]
    if not values:
        return {"n":0,"avg_r":None,"profit_factor":None,
                "win_pct":None,"model_return_pct":None,"max_drawdown_pct":None}
    gain=sum(x for x in values if x>0)
    loss=-sum(x for x in values if x<0)
    equity=peak=1.
    dd=0.
    for value in values:
        equity*=max(.01,1.+.0025*value)
        peak=max(equity,peak)
        dd=max(dd,(peak-equity)/peak)
    return {"n":len(values),"avg_r":round(sum(values)/len(values),6),
            "profit_factor":round(gain/loss,5) if loss else None,
            "win_pct":round(100*sum(x>0 for x in values)/len(values),2),
            "model_return_pct":round(100*(equity-1),4),
            "max_drawdown_pct":round(100*dd,4)}


def run(symbols, begin, end, output: Path, *, fetch=fetch_daily):
    if not symbols or len(symbols)>MAX_SYMBOLS_PER_RUN:
        raise ValueError("too_many_symbols_for_one_public_runner")
    if any(x not in SCALE for x in symbols):
        raise ValueError("symbol_not_verified_for_provider")
    output.mkdir(parents=True,exist_ok=True)
    report={"source":"Dukascopy public BID/ASK M1 historical candles",
            "research_only":True,"real_broker_account_costs_verified":False,
            "point_in_time_news_verified":False,"independent_holdout":False,
            "trade_allowed":False,"orders_sent":0,
            "requested_symbols":symbols,"start_inclusive":begin.isoformat(),
            "end_exclusive":end.isoformat(),"symbols":{},
            "data_status":"PUBLIC_HISTORICAL_PILOT"}
    all_trades=[]
    for symbol in symbols:
        minutes,coverage=load_public_minutes(symbol,begin,end,fetch=fetch)
        trades,stats=simulate_symbol(symbol,minutes)
        all_trades+=trades
        buckets=defaultdict(list)
        for t in trades:
            buckets[(t["strategy"],t["side"],t["regime"])].append(t)
        ranked=[]
        for key,items in buckets.items():
            ranked.append({"strategy":key[0],"side":key[1],"regime":key[2],
                           "base":metrics(items),"extra_0_10R":metrics(items,.1),
                           "extra_0_20R":metrics(items,.2),
                           "promotion_eligible":False,
                           "status":"EXPLORATORY_NOT_INDEPENDENT"})
        ranked.sort(key=lambda x:(x["strategy"],x["side"],x["regime"]))
        report["symbols"][symbol]={"coverage":coverage,"bars":stats,
                                   "candidate_groups":ranked,
                                   "all_trades":metrics(trades)}
        print("PUBLIC_PILOT",symbol,coverage,stats,metrics(trades),flush=True)
    report["combined_diagnostic"]=metrics(all_trades)
    report["limitations"]=[
        "Data are public Dukascopy candles, NOT actual VPS broker quotes",
        "Commissions and slippage assumptions are unverified",
        "M1 OHLC still cannot resolve intraminute tick order; stops take precedence",
        "Previously researched price periods do not represent independent holdout",
        "More months and minimum sample counts are required before ranking any strategy",
        "No publication of provider raw candles or broker-private files",
    ]
    (output/"summary.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,
                                                  allow_nan=False)+"\n",encoding="utf-8")
    # Study-level event records only, never republish provider M1 OHLC files.
    import csv
    if all_trades:
        with (output/"paper_trades.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(all_trades[0]))
            w.writeheader();w.writerows(all_trades)
    print("PUBLIC_PILOT_RESULT",json.dumps({
        "source":report["source"],"symbols":list(report["symbols"]),
        "total_trades":len(all_trades),"results":report["combined_diagnostic"],
        "orders_sent":0,"live_authorized":False},ensure_ascii=False),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--symbols",default="EURUSD,XAUUSD")
    parser.add_argument("--start",default="2026-09-01")
    parser.add_argument("--end",default="2026-09-12")
    parser.add_argument("--output",type=Path,default=Path("artifacts/public_tournament"))
    a=parser.parse_args()
    begin=date.fromisoformat(a.start);end=date.fromisoformat(a.end)
    run([x.strip().upper() for x in a.symbols.split(",") if x.strip()],
        begin,end,a.output)


if __name__=="__main__":
    main()
