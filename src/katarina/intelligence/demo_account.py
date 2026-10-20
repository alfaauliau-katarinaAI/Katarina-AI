"""Persistent risk evidence from demo enrolment, never lifetime risk claims."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite

from katarina.engines.risk import RiskRequest


def number(v):
    return type(v) in (int,float) and isfinite(v)


class DemoAccountLedger:
    def __init__(self, db, *, login, server, clock):
        self.db,self.clock=db,clock
        self.binding=sha256(f'{login}|{server}'.encode()).hexdigest()
        db.execute('CREATE TABLE IF NOT EXISTS demo_account_state(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL)')
        db.commit()

    def capture(self, broker):
        now=self.clock();day=datetime.fromtimestamp(now,timezone.utc).date().isoformat()
        account=broker.account_info();positions=broker.positions_get();orders=broker.orders_get()
        if account is None or positions is None or orders is None:
            raise ValueError('DEMO_ACCOUNT_BOOK_UNAVAILABLE')
        for key in ('balance','equity','margin_free'):
            if not number(getattr(account,key,None)) or getattr(account,key)<0:
                raise ValueError('DEMO_CAPITAL_UNVERIFIED')
        if min(account.balance,account.equity)<=0:
            raise ValueError('DEMO_CAPITAL_EXHAUSTED')
        if account.currency not in ('USD','USC'):
            raise ValueError('DEMO_CURRENCY_UNVERIFIED')
        stored=self.db.execute('SELECT payload FROM demo_account_state WHERE id=1').fetchone()
        state=json.loads(stored[0]) if stored else None
        if state and state['binding']!=self.binding:
            raise ValueError('DEMO_ACCOUNT_EPOCH_BINDING_CHANGED')
        start=state['start'] if state else now
        # A wide book-reconciliation query accommodates broker display offsets.
        # No deal timestamp from this query is used as a market decision clock.
        deals=broker.history_deals_get(datetime.fromtimestamp(start,timezone.utc)-timedelta(days=1),
                                       datetime.fromtimestamp(now,timezone.utc)+timedelta(days=1))
        if deals is None or len(deals)>10000:
            raise ValueError('DEMO_ACCOUNT_HISTORY_UNAVAILABLE_OR_LIMIT')
        if any(type(getattr(d,'ticket',None)) is not int for d in deals):
            raise ValueError('DEMO_ACCOUNT_HISTORY_INVALID')
        if state is None:
            if positions or orders:
                raise ValueError('DEMO_ENROLMENT_REQUIRES_EMPTY_ACCOUNT_BOOK')
            state=dict(binding=self.binding,start=now,initial_balance=account.balance,
                       seen=[d.ticket for d in deals],net_book_change=0.,peak=account.equity,
                       day=day,day_base=account.equity,max_daily_dd=0.,max_total_dd=0.)
        seen=set(state['seen']);new=[d for d in deals if d.ticket not in seen]
        if len({d.ticket for d in new})!=len(new):
            raise ValueError('DEMO_DUPLICATE_DEAL_RECORDS')
        change=cashflow=0.
        for deal in new:
            values=[getattr(deal,k,None) for k in ('profit','commission','swap','fee')]
            if not all(number(v) for v in values):
                raise ValueError('DEMO_DEAL_COST_FIELDS_UNAVAILABLE')
            if deal.type not in (broker.DEAL_TYPE_BUY,broker.DEAL_TYPE_SELL,broker.DEAL_TYPE_BALANCE):
                raise ValueError('DEMO_UNCLASSIFIED_ACCOUNT_OPERATION')
            change+=sum(values)
            if deal.type==broker.DEAL_TYPE_BALANCE:cashflow+=sum(values)
        expected=state['initial_balance']+state['net_book_change']+change
        if abs(account.balance-expected)>max(.02,abs(account.balance)*1e-8):
            raise ValueError('DEMO_ACCOUNT_BALANCE_NOT_RECONCILED')
        state['net_book_change']+=change
        state['seen']=sorted(seen|{d.ticket for d in new})
        state['peak']=max(state['peak']+cashflow,account.equity,account.balance)
        if state['day']!=day:
            state.update(day=day,day_base=account.equity,max_daily_dd=0.)
        else:state['day_base']+=cashflow
        if state['day_base']<=0 or state['peak']<=0:
            raise ValueError('DEMO_ACCOUNT_BASELINE_INVALID')
        state['max_daily_dd']=max(state['max_daily_dd'],max(0.,1-account.equity/state['day_base']))
        state['max_total_dd']=max(state['max_total_dd'],max(0.,1-account.equity/state['peak']))
        capital=min(account.balance,account.equity)
        open_cash=0.;unbounded=False
        for p in positions:
            values=[getattr(p,k,None) for k in ('volume','price_current','sl')]
            if not all(number(v) and v>0 for v in values) or p.type not in (0,1):
                unbounded=True;continue
            loss=broker.order_calc_profit(p.type,p.symbol,p.volume,p.price_current,p.sl)
            if not number(loss):unbounded=True
            else:open_cash+=max(0.,-loss)
        # Pending orders are not guessed to have zero risk. This bounded trial
        # never creates them; any pending book blocks additional submissions.
        unbounded=unbounded or bool(orders)
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO demo_account_state VALUES(1,?)',
                            (json.dumps(state,allow_nan=False),))
        risk=RiskRequest(.001,min(1.,open_cash/capital),state['max_total_dd'],.5,2.,True,True,
                         min(1.,state['max_daily_dd']),unbounded,capital,
                         max(capital,state['peak']),account.currency)
        return dict(risk=risk,observed_at=now,account=account,positions=positions,orders=orders,
                    scope='DEMO_ENROLMENT_EPOCH_NOT_LIFETIME',epoch=state['start'])
