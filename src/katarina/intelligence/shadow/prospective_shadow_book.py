"""KATARINA prospective read-only *virtual* research. No broker or LLM API.

Samples ONE ranked contextual hypothesis per 5-minute closed bar across
all markets. Quotes simulate a 2-hour SL/TP path at observed intervals:
gaps cannot be interpreted as real fills, and ALL outcomes remain
UNVERIFIED MODELLED QUOTES, never cost-reconciled trades or live alpha.

The sole canonical observer owns this SQLite book; no worker/cron added.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
import json
import sqlite3

from katarina.intelligence.cognition.self_evolution_lab import ShadowResearchPolicy

UTC=timezone.utc
MAX_HORIZON_SEC=2*3600
MAX_GAP_SEC=8*60
QUOTE_SKEW_SEC=20
MAX_PORTFOLIO_OPEN=1
COST_STRESS_R=0.15
MAX_SPREAD_RISK_FRACTION=0.30
MIN_RR=1.25


def epoch(t):
    if not isinstance(t,datetime) or t.tzinfo is None:
        raise ValueError("utc_aware_datetime_required")
    return t.astimezone(UTC).timestamp()


@dataclass(frozen=True)
class ResearchHypothesis:
    symbol:str
    method:str
    regime:str
    side:str
    closed_bar_at:datetime
    observed_at:datetime
    bid:float
    ask:float
    tick_at:float
    stop:float
    target:float
    evidence_score:float
    blockers:tuple[str,...]
    official_news_verified:bool
    spread_atr:float

    def geometry(self):
        if self.side not in ("BUY","SELL"):
            return None
        if not all(isinstance(v,(int,float)) and isfinite(v) for v in
                   (self.bid,self.ask,self.tick_at,self.stop,self.target,
                    self.evidence_score,self.spread_atr)):
            return None
        if self.bid<=0 or self.ask<self.bid or self.spread_atr<0:
            return None
        entry=self.ask if self.side=="BUY" else self.bid
        risk=(entry-self.stop if self.side=="BUY" else self.stop-entry)
        reward=(self.target-entry if self.side=="BUY" else entry-self.target)
        spread=self.ask-self.bid
        if (risk<=0 or reward/risk<MIN_RR or
                spread/risk>MAX_SPREAD_RISK_FRACTION or
                self.evidence_score<.62 or self.method in ("","OBSERVE")):
            return None
        return risk,reward/risk


class ProspectiveShadowBook:
    """Immutable signal ledger, state replay, and bounded virtual position.

    All writes transaction-bound and idempotent. Outcomes after a gap become
    UNCERTAIN_GAP, not a fabricated win/loss. Pending signals require a
    new actual broker quote observed after their entry.
    """
    def __init__(self,db:sqlite3.Connection):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS prospective_shadow(
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,bar_close TEXT NOT NULL,
            observed_at REAL NOT NULL,tick_at REAL NOT NULL,
            method TEXT NOT NULL,regime TEXT NOT NULL,side TEXT NOT NULL,
            bid REAL NOT NULL,ask REAL NOT NULL,
            entry REAL NOT NULL,stop REAL NOT NULL,target REAL NOT NULL,
            risk REAL NOT NULL,rr REAL NOT NULL,evidence_score REAL NOT NULL,
            official_news_verified INTEGER NOT NULL,
            blockers TEXT NOT NULL,
            state TEXT NOT NULL,last_quote_epoch REAL NOT NULL,
            exit_at REAL,exit_price REAL,reason TEXT,virtual_net_r REAL,
            UNIQUE(symbol,bar_close,method,side)
        )""")
        db.execute("""CREATE INDEX IF NOT EXISTS prospective_open
            ON prospective_shadow(state,observed_at)""")
        db.commit()

    def settle(self, *,now:datetime, quotes:dict[str,tuple[float,float,float]]):
        """Quote timestamp MUST not lead true UTC by >20 seconds."""
        t=epoch(now)
        actions=[]
        with self.db:
            for (oid,symbol,observed,tick_at,side,entry,stop,target,risk,last) in (
                self.db.execute("""SELECT id,symbol,observed_at,tick_at,side,
                    entry,stop,target,risk,last_quote_epoch
                    FROM prospective_shadow WHERE state='OPEN'
                    ORDER BY observed_at,id""").fetchall()
            ):
                q=quotes.get(symbol)
                if not q:
                    if t-last>MAX_GAP_SEC:
                        self._close(oid,"UNCERTAIN_GAP",t,None,"quote_missing",None)
                        actions.append((symbol,"UNCERTAIN_GAP"))
                    continue
                bid,ask,quote_at=q
                if not all(isfinite(x) for x in (bid,ask,quote_at)) or bid<=0 or ask<bid:
                    if t-last>MAX_GAP_SEC:
                        self._close(oid,"UNCERTAIN_GAP",t,None,"quote_invalid",None)
                        actions.append((symbol,"UNCERTAIN_GAP"))
                    continue
                if quote_at>t+QUOTE_SKEW_SEC or quote_at<t-MAX_GAP_SEC:
                    if t-last>MAX_GAP_SEC:
                        self._close(oid,"UNCERTAIN_GAP",t,None,"stale_or_future_quote",None)
                        actions.append((symbol,"UNCERTAIN_GAP"))
                    continue
                if quote_at<=last:
                    if t-last>MAX_GAP_SEC:
                        self._close(oid,"UNCERTAIN_GAP",t,None,"quote_not_advancing",None)
                        actions.append((symbol,"UNCERTAIN_GAP"))
                    continue
                if quote_at-last>MAX_GAP_SEC:
                    self._close(oid,"UNCERTAIN_GAP",t,None,"unobserved_intratrade_path",None)
                    actions.append((symbol,"UNCERTAIN_GAP"))
                    continue
                price=bid if side=="BUY" else ask
                if side=="BUY":
                    stop_hit=price<=stop;target_hit=price>=target
                else:
                    stop_hit=price>=stop;target_hit=price<=target
                if stop_hit:
                    reason="SIMULATED_STOP_QUOTE"
                    # pessimistic gap: cannot fill at better than stop.
                    filled=min(price,stop) if side=="BUY" else max(price,stop)
                elif target_hit:
                    reason="SIMULATED_TARGET_QUOTE"
                    # capped favourable take profit; cannot claim a better fill.
                    filled=min(price,target) if side=="BUY" else max(price,target)
                elif quote_at>=tick_at+MAX_HORIZON_SEC:
                    reason="SIMULATED_TIMED_EXIT_QUOTE"
                    filled=price
                else:
                    self.db.execute("""UPDATE prospective_shadow
                        SET last_quote_epoch=? WHERE id=?""",(quote_at,oid))
                    continue
                gross=(filled-entry)/risk if side=="BUY" else (entry-filled)/risk
                net=gross-COST_STRESS_R
                self._close(oid,"VIRTUAL_QUOTED",quote_at,filled,reason,net)
                actions.append((symbol,"VIRTUAL_QUOTED"))
        return actions

    def _close(self,oid,state,t,price,reason,net):
        self.db.execute("""UPDATE prospective_shadow SET
            state=?,exit_at=?,exit_price=?,reason=?,virtual_net_r=?
            WHERE id=? AND state='OPEN'""",(state,t,price,reason,net,oid))

    def propose(self,hypotheses:list[ResearchHypothesis],now:datetime,
                *,research_policy:ShadowResearchPolicy|None=None,
                research_priorities:dict[tuple[str,str,str,str],int]|None=None):
        """Deterministic, ranked one-entry across all correlated instruments.

        Signal is a virtual simulation even if official news is unavailable;
        such uncleared cases are labeled, never counted as validated alpha.
        """
        t=epoch(now)
        if research_priorities is None:
            research_priorities={}
        if (not isinstance(research_priorities,dict)
                or len(research_priorities)>20):
            raise ValueError("invalid_curiosity_priority_map")
        for key,priority in research_priorities.items():
            if (not isinstance(key,tuple) or len(key)!=4
                    or any(not isinstance(k,str) or not k for k in key)
                    or key[2] not in ("BUY","SELL")
                    or type(priority) is not int or not 0<=priority<=3):
                raise ValueError("invalid_curiosity_priority")
        if research_policy is not None:
            if not isinstance(research_policy,ShadowResearchPolicy):
                raise ValueError("invalid_shadow_research_policy")
            try:
                learned_at=datetime.fromisoformat(research_policy.as_of_utc)
                if learned_at.tzinfo is None or epoch(learned_at)>t+1e-6:
                    raise ValueError("future_shadow_learning_not_allowed")
            except (TypeError,ValueError) as exc:
                raise ValueError("invalid_or_future_shadow_learning") from exc
            if not research_policy.integrity_ok:
                return {"accepted":False,"reason":"SHADOW_LEARNING_INVALID_FAIL_CLOSED",
                        "candidates":0,"mode":"NO_REAL_ORDERS"}
        for h in hypotheses:
            if abs(epoch(h.observed_at)-t)>3:
                raise ValueError("hypothesis_timestamp_mismatch")
        from katarina.intelligence.shadow.prospective_shadow_review import pause_due_to_losses
        eligible=[]
        drift_paused=0
        for h in hypotheses:
            if pause_due_to_losses(self.db,symbol=h.symbol,method=h.method,
                                   side=h.side,regime=h.regime,at_utc=now):
                drift_paused+=1
                continue
            dims=h.geometry()
            if dims is None:continue
            if research_policy is not None and h.evidence_score < (
                    research_policy.score_floor(
                        h.symbol,h.method,h.side,h.regime)):
                continue
            bt=epoch(h.closed_bar_at)
            if bt>t or t-bt>900 or abs(t-h.tick_at)>QUOTE_SKEW_SEC:
                continue
            if h.regime in ("UNKNOWN","VOLATILITY_SHOCK","TRANSITION"):
                continue
            risk,rr=dims
            if not (h.ask>0 and h.bid>0):continue
            # Curiosity guides ONLY virtual samples; geometry, spread,
            # news, one-position and learning-integrity gates still prevail.
            curiosity=research_priorities.get(
                (h.symbol,h.method,h.side,h.regime),0)
            rank=(curiosity,min(rr,3.0)/(1+max(h.spread_atr,0)),
                  h.evidence_score, -((h.ask-h.bid)/risk))
            eligible.append((rank,h.symbol,h,risk,rr))
        if not eligible:
            return {"accepted":False,"reason":"NO_CLOSED_BAR_VALID_HYPOTHESIS",
                    "candidates":0,"drift_paused":drift_paused}
        # Stable priority + quality; never dependent on input order.
        ranked=sorted(eligible,key=lambda x:(
            -x[0][0],-x[0][1],-x[0][2],-x[0][3],x[1]))
        with self.db:
            open_count=self.db.execute(
                "SELECT COUNT(*) FROM prospective_shadow WHERE state='OPEN'").fetchone()[0]
            if open_count>=MAX_PORTFOLIO_OPEN:
                return {"accepted":False,"reason":"ONE_VIRTUAL_PORTFOLIO_POSITION_AT_A_TIME",
                        "candidates":len(eligible)}
            # If a duplicate top-ranked proposal already exists, keep trying
            # a genuinely new candle; never open a second active position.
            for _,_,h,risk,rr in ranked:
                exists=self.db.execute(
                    "SELECT 1 FROM prospective_shadow WHERE symbol=? AND bar_close=? AND method=? AND side=?",
                    (h.symbol,h.closed_bar_at.isoformat(),h.method,h.side)).fetchone()
                if exists:continue
                entry=h.ask if h.side=="BUY" else h.bid
                self.db.execute("""INSERT INTO prospective_shadow(
                    symbol,bar_close,observed_at,tick_at,method,regime,side,
                    bid,ask,entry,stop,target,risk,rr,evidence_score,
                    official_news_verified,blockers,state,last_quote_epoch
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (h.symbol,h.closed_bar_at.isoformat(),t,h.tick_at,h.method,
                     h.regime,h.side,h.bid,h.ask,entry,h.stop,h.target,risk,rr,
                     h.evidence_score,1 if h.official_news_verified else 0,
                     json.dumps(h.blockers),"OPEN",h.tick_at))
                return {"accepted":True,"reason":"VIRTUAL_UNCLEARED_RESEARCH_ONLY",
                        "symbol":h.symbol,"side":h.side,"method":h.method,
                        "official_news_verified":h.official_news_verified,
                        "candidates":len(eligible),"mode":"NO_REAL_ORDERS"}
        return {"accepted":False,"reason":"ALL_PROPOSALS_DUPLICATE",
                "candidates":len(eligible)}

    def summary(self):
        counts=dict(self.db.execute(
            "SELECT state,COUNT(*) FROM prospective_shadow GROUP BY state"))
        # No dollar / performance guarantee. Conditional on actually
        # sampled discrete bid/ask quotes and an assumed 0.15R cost.
        groups=self.db.execute("""SELECT method,side,regime,COUNT(*),
            AVG(virtual_net_r),SUM(CASE WHEN virtual_net_r>0 THEN 1 ELSE 0 END)
            FROM prospective_shadow WHERE state='VIRTUAL_QUOTED'
            GROUP BY method,side,regime ORDER BY method,side,regime""").fetchall()
        return {
            "mode":"PAPER_ONLY_QUOTE_SAMPLING_NOT_VERIFIED_BROKER_FILLS",
            "counts":counts,
            "outcomes":[{"method":m,"side":s,"regime":r,"n":n,
                         "mean_modeled_r":round(avg,6),
                         "positive":pos} for m,s,r,n,avg,pos in groups],
            "portfolio_virtual_max_concurrent":MAX_PORTFOLIO_OPEN,
            "assumed_extra_cost_r":COST_STRESS_R,
            "commission_verified":False,"full_tick_path_verified":False,
            "usable_for_live_model_promotion":False,
            "orders_submitted":0,"live_execution_authorized":False,
        }
