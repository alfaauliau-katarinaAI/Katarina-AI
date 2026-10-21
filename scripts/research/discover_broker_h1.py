"""One-shot price-rule search on real broker bars; no historical news is assumed."""
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from katarina.intelligence.perception.calendar_history import load_calendar_history
from katarina.intelligence.lab.autonomous_strategy_discovery import Candle,discover


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',required=True)
    a=p.parse_args();root=Path(a.output_dir)
    root.mkdir(parents=True,exist_ok=False)
    import MetaTrader5 as mt5
    if not mt5.initialize():raise RuntimeError('terminal_unavailable')
    try:
        terminal=mt5.terminal_info()
        if terminal is None or terminal.trade_allowed:raise RuntimeError('trading_must_be_off')
        start=datetime(2025,1,1,tzinfo=timezone.utc);end=datetime.now(timezone.utc)
        summary=[]
        for symbol in ('XAUUSD.vx','EURUSD.vx','USDJPY.vx'):
            data,coverage=load_calendar_history(mt5.copy_rates_range,symbol,mt5.TIMEFRAME_H1,3600,start,end,now=end)
            if data is None:raise RuntimeError('history_missing')
            bars=tuple(Candle(int(r['time'])+3600,float(r['open']),float(r['high']),float(r['low']),float(r['close'])) for r in data)
            result=discover(bars,seed=42,population=24,generations=8)
            result.update(symbol=symbol,coverage=coverage,origin='BROKER_H1_BID_OHLC_PROXY',
                broker_historical_clock_verified=False,news_features_used=False,
                history_already_inspected_not_pristine_holdout=True)
            (root/(symbol+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
            row=dict(symbol=symbol,bars=len(bars),trials=result['candidate_trials'],
                     candidates=result['candidate_rules'],live_authorized=False)
            summary.append(row);print(json.dumps(row),flush=True)
        (root/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    finally:mt5.shutdown()


if __name__=='__main__':main()
