"""Causal cross-asset opportunity arbitration, research-only.

Ranks only candidates visible at the SAME decision timestamp.
Never sees realized trade outcome. Rejects non-validated or stale signals.
No broker imports, no volume or order creation.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
from math import isfinite
from typing import Sequence

@dataclass(frozen=True)
class Opportunity:
    symbol: str
    cut_utc: datetime
    side: str
    playbook: str
    score: float
    structural_rr: float
    spread_atr: float
    semantic_confirmed: bool
    quality_eligible: bool
    fresh: bool
    news_verified: bool
    research_only: bool = True
    live_execution_authorized: bool = False

@dataclass(frozen=True)
class Arbitration:
    selected: Opportunity | None
    valid: tuple[Opportunity,...]
    reasons: tuple[str,...]
    mode: str = "RESEARCH_ONLY"
    live_execution_authorized: bool = False

def candidate_rank(x:Opportunity) -> tuple[float,float,float,str]:
    """Pre-frozen score; more structure, then better room and lower costs."""
    return (-round(x.score,6),-min(x.structural_rr,3.5),
            round(x.spread_atr,6),x.symbol)

def select_at_checkpoint(candidates:Sequence[Opportunity], *,
                         cut_utc:datetime, hypothesis_news_clear:bool=False,
                         min_score:float=.64) -> Arbitration:
    if cut_utc.tzinfo is None or not .2<=min_score<=.95:
        raise ValueError("invalid_selection_checkpoint")
    good=[]; reasons=[]
    for x in candidates:
        if x.cut_utc.tzinfo is None or x.cut_utc!=cut_utc:
            reasons.append("stale_or_future_candidate");continue
        if not x.symbol or x.side not in ("BUY","SELL"):
            reasons.append("invalid_side_or_symbol");continue
        if not all(isfinite(v) for v in (x.score,x.structural_rr,x.spread_atr)):
            reasons.append("nonfinite_signal_score");continue
        if x.live_execution_authorized or not x.research_only:
            reasons.append("execution_permission_not_accepted");continue
        if (not x.fresh or not x.quality_eligible or not x.semantic_confirmed or
                x.score<min_score or x.structural_rr<1.25 or x.spread_atr>.28):
            reasons.append("setup_quality_rejected");continue
        if not x.news_verified and not hypothesis_news_clear:
            reasons.append("news_context_unverified");continue
        good.append(x)
    good.sort(key=candidate_rank)
    if not good:reasons.append("NO_TRADE")
    return Arbitration(good[0] if good else None,tuple(good),
                      tuple(sorted(set(reasons))))

@dataclass(frozen=True)
class RiskLimits:
    risk_fraction: float=.0025
    max_trades_per_day: int=1
    max_portfolio_exposure: int=1
    daily_loss_limit_fraction: float=.005
    def __post_init__(self):
        if not (0<self.risk_fraction<=.01 and
                1<=self.max_trades_per_day<=4 and
                self.max_portfolio_exposure==1 and
                self.daily_loss_limit_fraction>=self.risk_fraction):
            raise ValueError("invalid_risk_limits")

def portfolio_replay(groups:Sequence[tuple[datetime,Sequence[Opportunity]]],
                     outcomes:dict[tuple[str,int],dict],
                     risk:RiskLimits=RiskLimits(),
                     *,hypothesis_news_clear:bool=False):
    """At each fixed checkpoint pick top CURRENT candidate then enter if flat.

    outcomes dictionary is consulted only AFTER the choice; it can never
    influence which candidate is selected. Unrealized capital is not
    marked-to-market; this is a sequential fixed-fraction R approximation.
    """
    equity=1.0;peak=1.0;max_dd=0.
    last_exit=None;day=None;entries_today=0;day_pnl=0.;trades=[]
    considered=0;valid_windows=0;rejected=0;days_seen=set()
    for cut,pool in sorted(groups,key=lambda a:a[0]):
        dt=cut.astimezone(timezone.utc)
        d=dt.date()
        days_seen.add(d.isoformat())
        if day!=d:
            day=d;entries_today=0;day_pnl=0.
        choice=select_at_checkpoint(pool,cut_utc=cut,
                                   hypothesis_news_clear=hypothesis_news_clear)
        considered+=len(pool)
        if choice.selected is None:continue
        valid_windows+=1
        if entries_today>=risk.max_trades_per_day or (
            last_exit is not None and dt<last_exit
        ) or day_pnl<=-risk.daily_loss_limit_fraction:
            rejected+=1;continue
        selected=choice.selected
        key=(selected.symbol,int(dt.timestamp()))
        if key not in outcomes:
            rejected+=1;continue
        outcome=outcomes[key]
        if outcome is None:
            rejected+=1;continue
        exit_time=datetime.fromtimestamp(outcome["exit_time"],timezone.utc)
        if exit_time<=dt:raise ValueError("future_outcome_bad_exit")
        pnl=equity*risk.risk_fraction*float(outcome["R"])
        if equity+pnl<=0:raise ValueError("equity_bankruptcy")
        equity+=pnl;peak=max(peak,equity);max_dd=max(max_dd,1-equity/peak)
        day_pnl+=pnl;entries_today+=1;last_exit=exit_time
        trades.append(dict(symbol=selected.symbol,
            checkpoint_utc=dt.isoformat(),exit_utc=exit_time.isoformat(),
            R=round(float(outcome["R"]),7),score=selected.score,
            structural_rr=selected.structural_rr,
            pnl_fraction=round(pnl,10),equity=round(equity,10),
            day=d.isoformat()))
    return dict(trades=trades,days_observed=len(days_seen),
                all_candidates=considered,valid_windows=valid_windows,
                capacity_rejections=rejected,equity_multiple=round(equity,6),
                max_drawdown_pct=round(max_dd*100,4),
                risk_per_entry_pct=risk.risk_fraction*100)