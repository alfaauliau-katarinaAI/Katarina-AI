"""Invented PC acceptance sensor. Never represents a broker, fill or profit proof."""
from datetime import datetime, timezone
from types import SimpleNamespace


class PCSimulationBroker:
    TIMEFRAME_M5,TIMEFRAME_M15,TIMEFRAME_H1=5,15,60
    COPY_TICKS_INFO=1
    ACCOUNT_TRADE_MODE_DEMO=0

    def __init__(self):
        self.now=int(datetime.now(timezone.utc).timestamp())-1
        self.closed=False

    def initialize(self):
        self.closed=False
        return True

    def shutdown(self): self.closed=True
    def terminal_info(self): return SimpleNamespace(connected=True,trade_allowed=False)
    def account_info(self):
        return SimpleNamespace(balance=10000.,equity=10000.,margin=0.,margin_free=10000.,trade_mode=0,
                               server='SYNTHETIC_PC_ONLY')
    def positions_get(self): return ()
    def orders_get(self): return ()
    def history_deals_get(self,*args): return ()
    def symbols_get(self):
        return [SimpleNamespace(name=s,trade_mode=4) for s in ('EURUSD','GBPUSD','XAUUSD')]
    def symbol_info_tick(self,symbol): return SimpleNamespace(time=self.now,bid=2000.,ask=2000.1)
    def symbol_info(self,symbol): return SimpleNamespace(trade_mode=4)
    def symbol_select(self,symbol,value): return True
    def copy_ticks_range(self,symbol,start,end,flags):
        return [dict(time_msc=self.now*1000,bid=2000.,ask=2000.1)]
    def copy_rates_from_pos(self,symbol,frame,offset,count):
        last=(self.now//(frame*60))*frame*60
        return [dict(time=last-(130-i)*frame*60,open=1990+i*.05,
            high=1991+i*.05,low=1989+i*.05,close=1990.2+i*.05,tick_volume=100)
            for i in range(130)]
