"""One durable research-only decision/quote-observation ledger.

Store all WAIT choices once per symbol/closed M5 bar. Only later
observed bid/ask markouts are resolved; NEVER count them as fills,
commission-reconciled net R, profitable trades or trained alpha.
"""
from __future__ import annotations
from datetime import datetime
from math import isfinite
import json
import sqlite3

HORIZON=900
MAX_EXIT_DELAY=120


def ts(value):
    x=datetime.fromisoformat(value.replace("Z","+00:00"))
    if x.tzinfo is None:raise ValueError("aware_clock_required")
    return x.timestamp()


class ContextDecisionJournal:
    def __init__(self,db:sqlite3.Connection):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS contextual_decisions(
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL, closed_m5_utc TEXT NOT NULL,
            observed_utc TEXT NOT NULL, side TEXT NOT NULL,
            method TEXT NOT NULL, decision TEXT NOT NULL,
            blockers_json TEXT NOT NULL,
            entry_bid REAL, entry_ask REAL, entry_tick_epoch REAL,
            due_epoch REAL, status TEXT NOT NULL,
            exit_tick_epoch REAL, markout_bps REAL,
            UNIQUE(symbol,closed_m5_utc)
        )""")
        db.execute("""CREATE INDEX IF NOT EXISTS contextual_pending_due
            ON contextual_decisions(status,due_epoch)""")
        db.commit()

    def record(self,*,symbol,closed_m5_utc,observed_utc,
               side,method,decision,blockers,bid,ask,tick_epoch):
        if not symbol or side not in ("BUY","SELL","WAIT"):
            raise ValueError("invalid_symbol_or_side")
        now=ts(observed_utc); close=ts(closed_m5_utc)
        if close>now or now-close>1200:
            raise ValueError("stale_or_future_signal_bar")
        if side in ("BUY","SELL"):
            if (not all(isinstance(v,(int,float)) and isfinite(v) for v in (bid,ask,tick_epoch))
                    or bid<=0 or ask<bid or not close<=tick_epoch<=now
                    or now-tick_epoch>180):
                raise ValueError("invalid_bid_ask_or_tick_clock")
            # Measurement begins at MT5 quote's own tick timestamp,
            # never at the Windows scheduled-task wall time.
            status="PENDING"; due=tick_epoch+HORIZON
        else:
            status="NO_SIGNAL";due=None;bid=ask=tick_epoch=None
        with self.db:
            self.db.execute("""INSERT OR IGNORE INTO contextual_decisions(
                symbol,closed_m5_utc,observed_utc,side,method,decision,
                blockers_json,entry_bid,entry_ask,entry_tick_epoch,due_epoch,status
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (symbol,closed_m5_utc,observed_utc,side,method,decision,
                 json.dumps(tuple(blockers)),bid,ask,tick_epoch,due,status))
        return self.db.execute(
            "SELECT changes()").fetchone()[0]==1

    @staticmethod
    def _markout(side,entry_bid,entry_ask,quote,due,now):
        if quote is None:return None
        try:
            bid,ask,q=quote
            if (not all(isfinite(float(v)) for v in
                        (bid,ask,q,entry_bid,entry_ask,due,now)) or
                not 0<float(bid)<=float(ask) or
                not 0<float(entry_bid)<=float(entry_ask) or
                not float(due)<=float(q)<=min(float(due)+MAX_EXIT_DELAY,float(now))):
                return None
            mid=(float(entry_bid)+float(entry_ask))/2
            delta=(float(bid)-float(entry_ask) if side=="BUY"
                   else float(entry_bid)-float(ask))
            return float(q),delta/mid*10000
        except (ValueError,TypeError,OverflowError):
            return None

    def resolve(self,quotes,now,*,quote_lookup=None):
        """Resolve causal 15-minute quote markouts.

        If quote_lookup is supplied, fetch the *actual* broker BID/ASK
        tick at/after each due_epoch, even if fetched on the NEXT 5-min
        observer cycle. Store a distinct BROKER_TICK_RECONCILED status:
        this retrospective price observation is NEVER an executed fill,
        a forward simulated order, or validated broker net profit.

        Without a callback retain the in-memory quote path for old
        offline tests. An invalid, stale or future tick cannot resolve.
        """
        if now.tzinfo is None:raise ValueError("now_requires_timezone")
        when=now.timestamp()
        n=0
        with self.db:
            rows=self.db.execute("""SELECT id,symbol,side,entry_bid,entry_ask,
              due_epoch FROM contextual_decisions
              WHERE status='PENDING' AND due_epoch<=?
              ORDER BY due_epoch,id""",(when,)).fetchall()
            for iid,symbol,side,bid,ask,due in rows:
                quote=None
                status="QUOTED"
                if quote_lookup is None:
                    quote=quotes.get(symbol)
                else:
                    try:
                        quote=quote_lookup(symbol,due,when)
                    except Exception:
                        quote=None  # fail-closed, not a guessed price
                    status="BROKER_TICK_RECONCILED"
                marked=self._markout(side,bid,ask,quote,due,when)
                if marked is not None:
                    q,markout=marked
                    self.db.execute("""UPDATE contextual_decisions
                        SET status=?,exit_tick_epoch=?,markout_bps=?
                        WHERE id=? AND status='PENDING'""",
                        (status,q,markout,iid))
                    n+=1
                elif when>due+MAX_EXIT_DELAY:
                    self.db.execute("""UPDATE contextual_decisions
                        SET status='MISSING_EXIT' WHERE id=? AND status='PENDING'""",
                        (iid,))
        return n

    def reconcile_missing(self,quote_lookup,now,*,max_records=80):
        """Recover old MISSING_EXIT cases from broker history only.

        Recovered records keep the distinct BROKER_TICK_RECOVERED status.
        These are EX-POST data repairs, not newly observed forward alpha.
        No unbounded replay and no outside of +/-120s tick interpolation.
        """
        if now.tzinfo is None:raise ValueError("now_requires_timezone")
        if not 1<=max_records<=100:raise ValueError("bounded_recovery_required")
        when=now.timestamp()
        recovered=0
        with self.db:
            rows=self.db.execute("""SELECT id,symbol,side,entry_bid,entry_ask,
              due_epoch FROM contextual_decisions
              WHERE status='MISSING_EXIT' AND due_epoch<=?
              ORDER BY id LIMIT ?""",
              (when-MAX_EXIT_DELAY,max_records)).fetchall()
            for iid,symbol,side,bid,ask,due in rows:
                try:
                    quote=quote_lookup(symbol,due,when)
                except Exception:
                    quote=None
                marked=self._markout(side,bid,ask,quote,due,when)
                if marked is not None:
                    q,markout=marked
                    self.db.execute("""UPDATE contextual_decisions
                        SET status='BROKER_TICK_RECOVERED',
                        exit_tick_epoch=?,markout_bps=?
                        WHERE id=? AND status='MISSING_EXIT'""",
                        (q,markout,iid))
                    recovered+=1
        return recovered

    def summary(self):
        counts=dict(self.db.execute(
            "SELECT status,COUNT(*) FROM contextual_decisions GROUP BY status"))
        latest=self.db.execute(
            "SELECT MAX(observed_utc) FROM contextual_decisions").fetchone()[0]
        return {"counts":counts,"last_observation_utc":latest,
                "outcome_type":"15min_BID_ASK_QUOTE_MARKOUT_NOT_EXECUTED_TRADING_PNL",
                "sample_overlap_possible":True,
                "historically_reconciled_quotes_never_promoted":True,
                "broker_commission_verified":False,
                "usable_as_ResolvedExperience":False,
                "live_execution_authorized":False}
