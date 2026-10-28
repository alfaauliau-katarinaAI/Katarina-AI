"""Invented PC acceptance sensor. Never represents a broker, fill or profit proof."""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from pathlib import Path
import json
from types import SimpleNamespace
from contextlib import contextmanager


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
        return SimpleNamespace(balance=10000.,equity=10000.,margin=0.,margin_free=10000.,trade_mode=0,server='PC-SIMULATION')
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

    def write_clock_fixture(self, root):
        """Known zero-offset invented clock for PC acceptance only, never broker proof."""
        root=Path(root);root.mkdir(parents=True,exist_ok=True)
        now=datetime.fromtimestamp(self.now,timezone.utc)
        (root/'broker-clock-evidence.json').write_text(json.dumps(dict(schema_version=1,
            shift_hours=0,valid_from=(now-timedelta(minutes=5)).isoformat(),
            valid_until=(now+timedelta(minutes=5)).isoformat(),source='INDEPENDENT_CLOCK_OBSERVATION',
            source_sha256=sha256(b'PC invented zero-offset clock').hexdigest(),
            broker_server_sha256=sha256(self.account_info().server.encode()).hexdigest())),encoding='utf-8')


@contextmanager
def synthetic_observation_clock():
    """Freeze only synthetic acceptance clocks to a known open FX session.

    Explicitly entered by test runners, never selected by a broker field or config.
    Authentication/permission expiry still uses the real system clock.
    """
    from unittest.mock import patch

    from datetime import datetime as real_datetime

    class FixtureMeta(type):
        def __instancecheck__(cls, value):
            return isinstance(value, real_datetime)

    class FixtureDateTime(real_datetime, metaclass=FixtureMeta):
        calls = 0
        @classmethod
        def now(cls, tz=None):
            cls.calls += 1
            value = cls(2026, 10, 29, 12, tzinfo=timezone.utc) + timedelta(milliseconds=cls.calls)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    with patch('katarina.intelligence.cognition.observer.datetime', FixtureDateTime), \
         patch('katarina.adapters.pc_simulation.datetime', FixtureDateTime), \
         patch('katarina.intelligence.cognition.unified_brain.datetime', FixtureDateTime), \
         patch('katarina.intelligence.cognition.continuous_observation.datetime', FixtureDateTime):
        yield FixtureDateTime
