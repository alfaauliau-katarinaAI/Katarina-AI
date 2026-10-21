"""Point-in-time M5 full-candle scan: intraday first, extreme scalps second.

Research hypotheses, not trained win probabilities. Every closed M5 candle is
considered, including WAIT/reject. HTF indices only use fully closed bars.
Instrument point/spread are passed by broker adapter, never fabricated.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
import numpy as np

@dataclass(frozen=True)
class Candidate:
    symbol: str
    cut: int
    idx: int
    side: str
    mode: str
    score: float
    atr: float
    spread_atr: float
    prior_extreme: float
    reasons: tuple[str,...]
    research_only: bool = True
    live_execution_authorized: bool = False

def trailing_mean(v,n):
    v=np.asarray(v,dtype=float)
    s=np.r_[0.,np.cumsum(v)]
    r=np.full(len(v),np.nan)
    r[n-1:] = (s[n:]-s[:-n])/n
    return r

def previous_extremes(a,n=20):
    hi=np.full(len(a),-np.inf);lo=np.full(len(a),np.inf)
    for k in range(1,n+1):
        hi[k:]=np.maximum(hi[k:],a["high"][:-k])
        lo[k:]=np.minimum(lo[k:],a["low"][:-k])
    return hi,lo

def vector_prefilter(symbol,m5,m15,h1,point,
                     *,min_bars=90,max_candidates=None,
                     allow_unresolved_latest=False):
    """Return ALL prequalified events; no stride, no future-label access."""
    if not point>0 or not isfinite(point):
        raise ValueError("invalid_broker_point")
    n=len(m5)
    if n<min_bars+50:return [],{"bars":n,"candidates":0}
    times=m5["time"].astype(np.int64)
    o=m5["open"];c=m5["close"];h=m5["high"];l=m5["low"]
    spread=m5["spread"].astype(float)*point
    previous_close=np.r_[c[0],c[:-1]]
    tr=np.maximum.reduce((h-l,abs(h-previous_close),abs(l-previous_close)))
    atr=trailing_mean(tr,14)
    hi20,lo20=previous_extremes(m5,20)
    hi8,lo8=previous_extremes(m5,8)
    meanvol=trailing_mean(m5["tick_volume"].astype(float),20)
    body=c-o
    buy_ctr=(body<0).astype(int);sell_ctr=(body>0).astype(int)
    bsum=np.r_[0,np.cumsum(buy_ctr)];ssum=np.r_[0,np.cumsum(sell_ctr)]
    buy_opposite=np.zeros(n,int);sell_opposite=np.zeros(n,int)
    buy_opposite[7:]=bsum[7:n]-bsum[:n-7]
    sell_opposite[7:]=ssum[7:n]-ssum[:n-7]
    # Above includes *current* bar; adjust to prior 7 bars strictly.
    buy_opposite[7:]=bsum[7:n]-bsum[:n-7]  # count bars [i-7, i-1]
    sell_opposite[7:]=ssum[7:n]-ssum[:n-7]
    # NOTE prefix indexed 'i': prefix[i] holds up to i-1; correct.
    cut=times+300
    m15t=m15["time"].astype(np.int64)
    h1t=h1["time"].astype(np.int64)
    i15=np.searchsorted(m15t,cut-900,side="right")-1
    ih1=np.searchsorted(h1t,cut-3600,side="right")-1
    # Offline historical fills require subsequent bars; prospective observation
    # must be able to inspect the latest FULLY CLOSED bar without any future bars.
    horizon_end=n if allow_unresolved_latest else n-49
    valid=(np.arange(n)>=min_bars)&(np.arange(n)<horizon_end)
    valid&=(i15>=10)&(ih1>=10)&np.isfinite(atr)&(atr>0)
    ix15=np.clip(i15,10,len(m15)-1);ixh1=np.clip(ih1,10,len(h1)-1)
    valid&=((cut-(m15t[ix15]+900))<=1800)
    valid&=((cut-(h1t[ixh1]+3600))<=7200)
    valid[1:] &= (times[1:]-times[:-1]==300) | (np.arange(1,n)==0)
    valid[:-1]&=(times[1:]-times[:-1]==300)
    # Market regimes derived from multiple *closed* HTF candles.
    ht15=m15["close"][ix15]-m15["close"][ix15-6]
    ht1=h1["close"][ixh1]-h1["close"][ixh1-4]
    buytrend=(ht15>.15*atr)&(ht1>.25*atr)
    selltrend=(ht15<-.15*atr)&(ht1<-.25*atr)
    srat=spread/np.maximum(atr,1e-12)
    bull=(body>.42*atr)&(c>previous_close)
    bear=(-body>.42*atr)&(c<previous_close)
    # Look for actual prior opposite candles and nearby local invalidation.
    pullbuy=(buy_opposite>=2)&(c-lo8<=2.6*atr)&(c>lo8+.2*atr)
    pullsell=(sell_opposite>=2)&(hi8-c<=2.6*atr)&(c<hi8-.2*atr)
    intrabuy=(valid & buytrend & bull & pullbuy & (srat<=.22))
    intrasell=(valid & selltrend & bear & pullsell & (srat<=.22))
    # Extreme scalp: reclaim prior 20-candle liquidity + rejection wick
    # and elevated broker tick-volume proxy. Never a default trade mode.
    lowwick=np.minimum(c,o)-l
    highwick=h-np.maximum(c,o)
    vol_ratio=m5["tick_volume"]/np.maximum(meanvol,1)
    scalp_buy=(valid &(l<lo20-.08*atr)&(c>lo20+.09*atr)&
               (body>.25*atr)&(lowwick>.45*atr)&
               (vol_ratio>=1.25)&(srat<=.12)&(ht1>0))
    scalp_sell=(valid &(h>hi20+.08*atr)&(c<hi20-.09*atr)&
                (-body>.25*atr)&(highwick>.45*atr)&
                (vol_ratio>=1.25)&(srat<=.12)&(ht1<0))
    picks=[]
    for mode,side,mask,extreme in (
        ("INTRADAY","BUY",intrabuy,lo8),
        ("INTRADAY","SELL",intrasell,hi8),
        ("SCALP_EXTREME","BUY",scalp_buy,lo20),
        ("SCALP_EXTREME","SELL",scalp_sell,hi20),
    ):
        indices=np.flatnonzero(mask)
        for i in indices:
            if mode=="INTRADAY":
                strength=min(2.,abs(body[i])/atr[i])
                score=min(.99,.54+.12*strength+.05*min(buy_opposite[i] if side=="BUY" else sell_opposite[i],4)-.3*srat[i])
                reason=("mtf_trend_aligned","closed_pullback","displacement","spread_normalized")
            else:
                sweep=((lo20[i]-l[i]) if side=="BUY" else (h[i]-hi20[i]))/atr[i]
                score=min(.99,.68+.11*min(sweep,1.5)+.07*min(vol_ratio[i]/2,1.5)-.3*srat[i])
                reason=("prior_liquidity_sweep_reclaim","rejection_wick","volume_spike","cheap_spread")
            picks.append(Candidate(symbol,int(cut[i]),int(i),side,mode,
                round(float(score),5),float(atr[i]),float(srat[i]),
                float(extreme[i]),reason))
    picks.sort(key=lambda x:(x.cut,x.mode,x.symbol,x.side))
    if max_candidates is not None:
        picks=picks[:max_candidates]
    return picks,dict(bars=n,closed_bars_considered=int(valid.sum()),
        intraday=int(intrabuy.sum()+intrasell.sum()),
        scalp_extreme=int(scalp_buy.sum()+scalp_sell.sum()),
        candidates=len(picks),has_future_inputs=False)

def fill_next_open(m5,event,point,*,additional_cost_R=0.):
    """Conservative next open modeled Bid/Ask & spread, stop-first M5.

    Not tick-level fill. Slippage 1 tick on entry & exit (if tick known).
    Historical commission is not available from OHLC and stressed separately.
    """
    i=event.idx;side=1 if event.side=="BUY" else -1
    n=len(m5);hold=48 if event.mode=="INTRADAY" else 8
    rr=1.8 if event.mode=="INTRADAY" else 1.3
    if i+1>=n or int(m5["time"][i+1])-int(m5["time"][i])!=300:
        return None
    atr=event.atr
    sr=float(m5["spread"][i+1])*point
    if sr<=0:return None
    mid=float(m5["open"][i+1])
    entry=mid+(sr if side==1 else 0)+side*point
    buffer=.13*atr+sr
    if event.mode=="INTRADAY":
        stop=(min(event.prior_extreme,float(m5["low"][i]))-buffer if side==1
              else max(event.prior_extreme,float(m5["high"][i]))+buffer)
        maxrisk=3.0*atr
    else:
        stop=(float(m5["low"][i])-.1*atr-sr if side==1
              else float(m5["high"][i])+.1*atr+sr)
        maxrisk=1.7*atr
    risk=side*(entry-stop)
    if risk<max(4*sr,4*point,.45*atr) or risk>maxrisk:
        return None
    tp=entry+side*rr*risk
    last=i;price=entry;kind="TIME";gap=False
    for k in range(i+1,min(i+hold+1,n)):
        if k>i+1 and int(m5["time"][k])-int(m5["time"][k-1])!=300:
            gap=True;break
        bar=m5[k];sp=float(bar["spread"])*point
        if sp<0:gap=True;break
        high=float(bar["high"])+(sp if side==-1 else 0)
        low=float(bar["low"])+(sp if side==-1 else 0)
        open_=float(bar["open"])+(sp if side==-1 else 0)
        hit_sl=low<=stop if side==1 else high>=stop
        hit_tp=high>=tp if side==1 else low<=tp
        if hit_sl:
            price=(min(stop,open_) if side==1 else max(stop,open_))-side*point
            kind="SL"
        elif hit_tp:
            price=tp-side*point
            kind="TP"
        else:
            price=float(bar["close"])+(sp if side==-1 else 0)-side*point
            kind="TIME"
        last=k
        if hit_sl or hit_tp:break
    if last==i:return None
    pnl_R=side*(price-entry)/risk-(.03 if event.mode=="INTRADAY" else .06)-additional_cost_R
    if not isfinite(pnl_R):return None
    return dict(symbol=event.symbol,mode=event.mode,side=event.side,
        cut=event.cut,entry_time=int(m5["time"][i+1]),
        exit_time=int(m5["time"][last])+300,
        R=round(pnl_R,7),raw_outcome=kind,hold_bars=last-i,
        score=event.score,spread_atr=event.spread_atr,
        spread_price=round(sr,9),risk_price=round(risk,9),
        stop_price=round(stop,9),take_price=round(tp,9),
        model_rr=rr,gap_interrupted=gap)