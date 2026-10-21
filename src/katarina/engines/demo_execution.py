"""Demo-only submission boundary connecting RiskGovernor to a durable outbox.

No terminal initialization, login, strategy selection or background activation.
The owner supplies an already connected broker and reconciled risk evidence.
Uncertain submissions are retained and block further risk until reconciled.
"""
from dataclasses import asdict, dataclass
from contextlib import closing
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import sqlite3
import threading
import time

from katarina.engines.risk import RiskAction, RiskRequest

# Broker retcodes that state the request was not executed. Such a send is
# terminal (REJECTED) instead of UNKNOWN, so it no longer blocks later intents.
NOT_EXECUTED_RETCODES = ('TRADE_RETCODE_REQUOTE', 'TRADE_RETCODE_REJECT', 'TRADE_RETCODE_CANCEL',
                         'TRADE_RETCODE_INVALID', 'TRADE_RETCODE_INVALID_VOLUME', 'TRADE_RETCODE_INVALID_PRICE',
                         'TRADE_RETCODE_INVALID_STOPS', 'TRADE_RETCODE_TRADE_DISABLED',
                         'TRADE_RETCODE_MARKET_CLOSED', 'TRADE_RETCODE_NO_MONEY',
                         'TRADE_RETCODE_PRICE_CHANGED', 'TRADE_RETCODE_PRICE_OFF', 'TRADE_RETCODE_INVALID_FILL')
# An UNKNOWN send with no matching deal or pending order after this long is NOT_FILLED.
UNFILLED_AFTER_SECONDS = 900


@dataclass(frozen=True)
class DemoIntent:
    intent_id: str
    experiment_id: str
    symbol: str
    side: str
    volume: float
    price: float
    stop_loss: float
    take_profit: float
    created_at: float
    loss_reserve_cash: float = 0.


class DemoExecutionBoundary:
    """Single-writer submission; safe for multiple producers, not live accounts.

    All processes sharing a demo account must use this SAME outbox. Transactional
    reservation allows only one unfinished submission across distinct intents.
    A successful send is not considered a reconciled position or a learning gain.
    """
    def __init__(self, broker, governor, outbox, *, expected_login,
                 expected_server, stop_requested, clock=time.time, magic=20261020):
        if (type(expected_login) is not int or expected_login <= 0
                or not isinstance(expected_server, str) or not expected_server
                or not callable(stop_requested) or type(magic) is not int or magic <= 0):
            raise ValueError('DEMO_BINDING_REQUIRED')
        self.broker, self.governor = broker, governor
        self.login, self.server = expected_login, expected_server
        self.stop_requested, self.clock, self.magic = stop_requested, clock, magic
        self.lock = threading.Lock()
        self.path = Path(outbox)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._db()) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS demo_outbox('
                       'intent_id TEXT PRIMARY KEY,digest TEXT NOT NULL,'
                       'state TEXT NOT NULL,updated_at REAL NOT NULL,'
                       'retcode INTEGER,broker_order INTEGER,broker_deal INTEGER)')
            fields={r[1] for r in db.execute('PRAGMA table_info(demo_outbox)')}
            for name,kind in [('intent_json','TEXT'),('position_id','INTEGER'),('outcome_json','TEXT')]:
                if name not in fields:db.execute(f'ALTER TABLE demo_outbox ADD COLUMN {name} {kind}')

    def _db(self):
        return sqlite3.connect(self.path, timeout=5)

    def _guard(self):
        if self.stop_requested():
            return 'OWNER_STOP_REQUEST'
        terminal,account=self.broker.terminal_info(),self.broker.account_info()
        reason=self._identity_error((terminal,account))
        if reason:return reason
        if (getattr(terminal, 'trade_allowed', None) is not True
                or getattr(terminal, 'tradeapi_disabled', None) is not False
                or getattr(account, 'trade_allowed', None) is not True
                or getattr(account, 'trade_expert', None) is not True):
            return 'DEMO_TRADING_PERMISSION_OFF'
        return None

    def _identity_error(self, pair=None):
        b = self.broker
        terminal, account = pair if pair is not None else (b.terminal_info(), b.account_info())
        if terminal is None or getattr(terminal, 'connected', None) is not True:
            return 'TERMINAL_DISCONNECTED'
        # Require the installed SDK constant. No fallback from a name/server label.
        demo = getattr(b, 'ACCOUNT_TRADE_MODE_DEMO', None)
        if (type(demo) is not int or account is None
                or type(getattr(account, 'trade_mode', None)) is not int
                or account.trade_mode != demo):
            return 'DEMO_ACCOUNT_REQUIRED'
        if (type(getattr(account, 'login', None)) is not int
                or account.login != self.login or account.server != self.server):
            return 'DEMO_ACCOUNT_BINDING_CHANGED'
        return None

    def _valid(self, i, risk):
        if not isinstance(i, DemoIntent) or not isinstance(risk, RiskRequest):
            return 'INVALID_DEMO_INTENT'
        if (not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', i.intent_id)
                or not re.fullmatch(r'[a-f0-9]{64}', i.experiment_id)
                or not re.fullmatch(r'[A-Za-z0-9_.#-]{1,40}', i.symbol)
                or i.side not in ('BUY', 'SELL')):
            return 'INVALID_DEMO_INTENT'
        values = (i.volume, i.price, i.stop_loss, i.take_profit, i.created_at)
        if any(type(v) not in (int, float) or not isfinite(v) or v <= 0 for v in values):
            return 'INVALID_DEMO_INTENT'
        if type(i.loss_reserve_cash) not in (int,float) or not isfinite(i.loss_reserve_cash) or i.loss_reserve_cash<0:
            return 'INVALID_DEMO_COST_RESERVE'
        if not 0 <= self.clock()-i.created_at <= 5:
            return 'DEMO_INTENT_STALE'
        if not (i.stop_loss < i.price < i.take_profit if i.side == 'BUY'
                else i.take_profit < i.price < i.stop_loss):
            return 'INVALID_DEMO_PROTECTION'
        return None

    def _mark(self, ident, state, result=None):
        # Tickets and account-native details remain in the PRIVATE outbox only.
        with closing(self._db()) as db, db:
            db.execute('UPDATE demo_outbox SET state=?,updated_at=?,retcode=?,'
                       'broker_order=?,broker_deal=? WHERE intent_id=?',
                       (state, self.clock(), getattr(result, 'retcode', None),
                        getattr(result, 'order', None), getattr(result, 'deal', None), ident))

    def submit(self, intent, risk, *, risk_observed_at, filling_mode):
        """Caller must provide freshly reconciled FULL account risk and lineage.

        Filling mode must be selected from broker specifications by the caller.
        No default filling mode, guessed capital, risk-free empty book, automatic
        retry or automatic promotion from historical profits is provided here.
        """
        with self.lock:
            try:
                return self._submit(intent, risk, risk_observed_at, filling_mode)
            except Exception:
                # Never leak broker/account/server details through exceptions.
                return {'status': 'BOUNDARY_ERROR', 'orders_submitted': None,
                        'submission_outcome': 'CHECK_PRIVATE_OUTBOX', 'live_authorized': False}

    def _submit(self, i, risk, stamp, filling):
        def receipt(state, sent=0):
            return dict(status=state, orders_submitted=sent, live_authorized=False)
        reason = self._valid(i, risk)
        if reason:
            return receipt(reason)
        if (type(stamp) not in (int, float) or not isfinite(stamp)
                or not 0 <= self.clock()-stamp <= 2):
            return receipt('DEMO_RISK_EVIDENCE_STALE')
        reason = self._guard()
        if reason:
            return receipt(reason)
        b = self.broker
        if type(filling) is not int or filling not in {
                getattr(b, name, None) for name in ('ORDER_FILLING_FOK', 'ORDER_FILLING_IOC', 'ORDER_FILLING_RETURN')}:
            return receipt('UNVERIFIED_FILLING_MODE')
        # Use the existing governor; an APPROVE or REDUCE is required, then
        # independently verify that the requested lot fits its approved budget.
        decision = self.governor.evaluate(risk)
        if decision.action not in (RiskAction.APPROVE, RiskAction.REDUCE):
            return receipt('RISK_GOVERNOR_'+decision.action.value)
        capital = risk.risk_capital
        if type(capital) not in (int, float) or not isfinite(capital) or capital <= 0:
            return receipt('DEMO_CAPITAL_UNVERIFIED')
        side = b.ORDER_TYPE_BUY if i.side == 'BUY' else b.ORDER_TYPE_SELL
        loss = b.order_calc_profit(side, i.symbol, i.volume, i.price, i.stop_loss)
        if (type(loss) not in (int, float) or not isfinite(loss) or loss >= 0
                or -loss+i.loss_reserve_cash > capital*decision.approved_fraction):
            return receipt('DEMO_VOLUME_EXCEEDS_APPROVED_RISK')
        payload = asdict(i)
        payload.update(risk=asdict(risk), risk_observed_at=stamp, filling_mode=filling,
                       expected_account_hash=sha256(f'{self.login}|{self.server}'.encode()).hexdigest())
        digest = sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
        db = self._db()
        try:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT digest,state FROM demo_outbox WHERE intent_id=?', (i.intent_id,)).fetchone()
            if old:
                return receipt('DUPLICATE_'+old[1] if old[0] == digest else 'INTENT_ID_CONFLICT')
            if db.execute("SELECT 1 FROM demo_outbox WHERE state IN ('RESERVED','SUBMITTING','UNKNOWN','ACCEPTED','PARTIAL','OPEN','OWNERSHIP_REVIEW','PROTECTION_REVIEW') LIMIT 1").fetchone():
                return receipt('DEMO_RECONCILIATION_REQUIRED')
            db.execute('INSERT INTO demo_outbox(intent_id,digest,state,updated_at,intent_json) VALUES(?,?,?,?,?)',
                       (i.intent_id, digest, 'RESERVED', self.clock(),json.dumps(asdict(i),allow_nan=False)))
            db.commit()
        finally:
            db.close()
        request = dict(action=b.TRADE_ACTION_DEAL, symbol=i.symbol, volume=i.volume,
                       type=side, price=i.price, sl=i.stop_loss, tp=i.take_profit,
                       deviation=0, magic=self.magic, comment='KD:'+sha256(i.intent_id.encode()).hexdigest()[:20],
                       type_time=b.ORDER_TIME_GTC, type_filling=filling)
        attempted = False
        try:
            checked = b.order_check(request)
            if checked is None or type(checked.retcode) is not int or checked.retcode != 0:
                self._mark(i.intent_id, 'CHECK_REJECTED')
                return receipt('DEMO_ORDER_CHECK_REJECTED')
            reason = self._guard()
            if reason or self.clock()-stamp > 2 or self.clock()-i.created_at > 5:
                self._mark(i.intent_id, 'CANCELLED')
                return receipt(reason or 'DEMO_EVIDENCE_EXPIRED_BEFORE_SEND')
            # Durable reservation precedes the only possible native send.
            self._mark(i.intent_id, 'SUBMITTING')
            attempted = True
            result = b.order_send(request)
            code = getattr(result, 'retcode', None)
            rejected = {getattr(b, name, None) for name in NOT_EXECUTED_RETCODES} - {None}
            state = ('ACCEPTED' if code == b.TRADE_RETCODE_DONE else
                     'PARTIAL' if code == b.TRADE_RETCODE_DONE_PARTIAL else
                     'REJECTED' if type(code) is int and code in rejected else 'UNKNOWN')
            self._mark(i.intent_id, state, result)
            return receipt('DEMO_'+state, 1)
        except Exception:
            self._mark(i.intent_id, 'UNKNOWN')
            return receipt('DEMO_UNKNOWN_RECONCILIATION_REQUIRED', int(attempted))

    def reconcile(self):
        """Prove fills/closed outcomes from broker books; no order is sent here."""
        with self.lock:
            reason=self._identity_error()
            if reason:return {'status':reason,'opened':0,'closed':0}
            b=self.broker;opened=closed=0
            with closing(self._db()) as db:
                rows=db.execute("SELECT intent_id,state,updated_at,broker_deal,intent_json,position_id FROM demo_outbox WHERE state IN ('RESERVED','SUBMITTING','UNKNOWN','ACCEPTED','PARTIAL','OPEN','PROTECTION_REVIEW') ORDER BY updated_at LIMIT 64").fetchall()
                for ident,state,at,deal_id,raw,position_id in rows:
                    if not raw:continue
                    intent=json.loads(raw)
                    if not position_id:
                        if deal_id:
                            candidates=b.history_deals_get(ticket=deal_id)
                        else:
                            candidates=b.history_deals_get(datetime.fromtimestamp(at,timezone.utc)-timedelta(days=1),
                                                          datetime.fromtimestamp(self.clock(),timezone.utc)+timedelta(days=1))
                            comment='KD:'+sha256(ident.encode()).hexdigest()[:20]
                            candidates=None if candidates is None or len(candidates)>10000 else [d for d in candidates if getattr(d,'comment',None)==comment]
                            if (candidates==[] and state in ('SUBMITTING','UNKNOWN')
                                    and self.clock()-at>UNFILLED_AFTER_SECONDS and self._no_pending(comment)):
                                # Old enough, no deal and no pending order: the send never executed.
                                with db:db.execute("UPDATE demo_outbox SET state='NOT_FILLED',updated_at=? WHERE intent_id=?",(self.clock(),ident))
                                continue
                        if candidates is None or len(candidates)!=1:continue
                        entry=candidates[0]
                        if (getattr(entry,'magic',None)!=self.magic or getattr(entry,'symbol',None)!=intent['symbol']
                                or getattr(entry,'entry',None)!=getattr(b,'DEAL_ENTRY_IN',None)
                                or getattr(entry,'type',None)!=(b.ORDER_TYPE_BUY if intent['side']=='BUY' else b.ORDER_TYPE_SELL)
                                or type(getattr(entry,'position_id',None)) is not int or entry.position_id<=0
                                or not 0<getattr(entry,'volume',0)<=intent['volume']+1e-8):continue
                        position_id=entry.position_id
                    positions=b.positions_get(ticket=position_id)
                    deals=b.history_deals_get(position=position_id)
                    if positions is None or deals is None or not deals or len(deals)>256:continue
                    if any(getattr(d,'magic',None)!=self.magic or getattr(d,'symbol',None)!=intent['symbol'] for d in deals):
                        with db:db.execute("UPDATE demo_outbox SET state='OWNERSHIP_REVIEW' WHERE intent_id=?",(ident,))
                        continue
                    if positions:
                        if len(positions)!=1:continue
                        p=positions[0]
                        if p.magic!=self.magic or p.symbol!=intent['symbol']:
                            with db:db.execute("UPDATE demo_outbox SET state='OWNERSHIP_REVIEW' WHERE intent_id=?",(ident,))
                            continue
                        if not getattr(p,'sl',0)>0 or not getattr(p,'tp',0)>0:
                            with db:db.execute("UPDATE demo_outbox SET state='PROTECTION_REVIEW' WHERE intent_id=?",(ident,))
                            continue
                        with db:
                            db.execute("UPDATE demo_outbox SET state='OPEN',position_id=? WHERE intent_id=?",(position_id,ident))
                        opened+=int(state!='OPEN')
                        continue
                    entries=[d for d in deals if d.entry==b.DEAL_ENTRY_IN]
                    exits=[d for d in deals if d.entry in (b.DEAL_ENTRY_OUT,getattr(b,'DEAL_ENTRY_OUT_BY',3))]
                    if (not entries or not exits or any(d.entry not in (b.DEAL_ENTRY_IN,b.DEAL_ENTRY_OUT,getattr(b,'DEAL_ENTRY_OUT_BY',3)) for d in deals)
                            or abs(sum(d.volume for d in entries)-sum(d.volume for d in exits))>1e-8):continue
                    values=[getattr(d,k,None) for d in deals for k in ('profit','commission','swap','fee')]
                    if any(type(v) not in (int,float) or not isfinite(v) for v in values):continue
                    sign=1 if intent['side']=='BUY' else -1
                    filled=sum(d.volume for d in entries)
                    prices=[getattr(d,'price',None) for d in entries]
                    entry_price=(sum(p*d.volume for p,d in zip(prices,entries))/filled
                                 if filled>0 and all(type(p) in (int,float) and isfinite(p) and p>0 for p in prices) else None)
                    costs={k:sum(getattr(d,k) for d in deals) for k in ('commission','swap','fee')}
                    outcome=dict(net_profit_native=sum(values),closed_observed_at=self.clock(),
                                 # Positive slippage is adverse: paid above (BUY) or sold below (SELL) the intent price.
                                 entry_slippage_price=(entry_price-intent['price'])*sign if entry_price is not None else None,
                                 commission_native=costs['commission'],swap_native=costs['swap'],fee_native=costs['fee'],
                                 entry_volume=sum(d.volume for d in entries),deal_count=len(deals),
                                 prospective_broker_outcome=True,live_authorized=False)
                    with db:
                        db.execute("UPDATE demo_outbox SET state='CLOSED',position_id=?,outcome_json=? WHERE intent_id=?",
                                   (position_id,json.dumps(outcome,allow_nan=False),ident))
                    closed+=1
            return dict(status='DEMO_BOOK_RECONCILED',opened=opened,closed=closed)

    def _no_pending(self, comment):
        orders = getattr(self.broker, 'orders_get', lambda: None)()
        return orders is not None and not any(getattr(o, 'comment', None) == comment for o in orders)

    def close_owned(self, position_id, *, price, observed_at, filling_mode):
        """One durable risk-reducing close attempt, bound to a proven owned fill."""
        with self.lock:
            reason=self._guard()
            if reason:return {'status':reason,'orders_submitted':0}
            if (type(position_id) is not int or position_id<=0 or type(price) not in (int,float)
                    or not isfinite(price) or price<=0 or type(observed_at) not in (int,float)
                    or not isfinite(observed_at) or not 0<=self.clock()-observed_at<=2
                    or type(filling_mode) is not int or filling_mode not in {
                        getattr(self.broker,k,None) for k in ('ORDER_FILLING_FOK','ORDER_FILLING_IOC','ORDER_FILLING_RETURN')}):
                return {'status':'DEMO_CLOSE_EVIDENCE_INVALID','orders_submitted':0}
            b=self.broker
            with closing(self._db()) as db:
                owned=db.execute("SELECT intent_json FROM demo_outbox WHERE position_id=? AND state='OPEN'",(position_id,)).fetchall()
                if len(owned)!=1:return {'status':'DEMO_OWNERSHIP_UNVERIFIED','orders_submitted':0}
                intent=json.loads(owned[0][0])
                book=b.positions_get(ticket=position_id)
                if book is None or len(book)!=1:return {'status':'DEMO_CLOSE_BOOK_UNAVAILABLE','orders_submitted':0}
                p=book[0]
                if p.magic!=self.magic or p.symbol!=intent['symbol'] or p.type not in (b.ORDER_TYPE_BUY,b.ORDER_TYPE_SELL):
                    return {'status':'DEMO_OWNERSHIP_UNVERIFIED','orders_submitted':0}
                with db:
                    db.execute('CREATE TABLE IF NOT EXISTS demo_closes(position_id INTEGER PRIMARY KEY,state TEXT NOT NULL,created_at REAL NOT NULL)')
                    db.execute('INSERT OR IGNORE INTO demo_closes VALUES(?,?,?)',(position_id,'RESERVED',self.clock()))
                    inserted=db.execute('SELECT changes()').fetchone()[0]
                if not inserted:return {'status':'DEMO_CLOSE_ALREADY_RESERVED','orders_submitted':0}
                request=dict(action=b.TRADE_ACTION_DEAL,position=position_id,symbol=p.symbol,volume=p.volume,
                             type=b.ORDER_TYPE_SELL if p.type==b.ORDER_TYPE_BUY else b.ORDER_TYPE_BUY,
                             price=price,deviation=0,magic=self.magic,comment='KD:CLOSE',
                             type_time=b.ORDER_TIME_GTC,type_filling=filling_mode)
                attempted=False
                try:
                    check=b.order_check(request)
                    if check is None or type(check.retcode) is not int or check.retcode!=0:
                        state='CHECK_REJECTED'
                    else:
                        reason=self._guard();latest=b.positions_get(ticket=position_id)
                        if (reason or self.clock()-observed_at>2 or latest is None or len(latest)!=1
                                or latest[0].magic!=self.magic or latest[0].symbol!=p.symbol
                                or latest[0].type!=p.type or abs(latest[0].volume-p.volume)>1e-8):
                            state=reason or 'BOOK_CHANGED'
                        else:
                            with db:db.execute("UPDATE demo_closes SET state='SUBMITTING' WHERE position_id=?",(position_id,))
                            attempted=True;result=b.order_send(request)
                            state='ACCEPTED' if getattr(result,'retcode',None)==b.TRADE_RETCODE_DONE else 'UNKNOWN'
                except Exception:state='UNKNOWN'
                with db:db.execute('UPDATE demo_closes SET state=? WHERE position_id=?',(state,position_id))
                return {'status':'DEMO_CLOSE_'+state,'orders_submitted':int(attempted)}
