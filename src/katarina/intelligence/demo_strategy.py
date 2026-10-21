"""Immutable protected demo variants; historical checks are not forward proof."""
from hashlib import sha256
import json
from math import isfinite
from katarina.intelligence.session_gaps import GAP_POLICY, spans_long_gap

VERSION = 'demo-protected-h1-v2'
DEMO_POLICY = 'DEMO_BASE_COST_GOVERNOR_V2'


def demo_policy(report):
    """Stress scenarios inform the experiment; only baseline screens demo entry.

    Keep variant identity unchanged so changing eligibility cannot erase its
    prospective outcomes or cooldown. This policy never grants live authority.
    """
    checks=report.get('checks')
    if not isinstance(checks,list) or len(checks)!=3 or [c.get('multiplier') for c in checks]!=[1,2,3]:
        raise ValueError('INVALID_DEMO_COST_CHECKS')
    return dict(report,qualified=checks[0].get('passed') is True,
                qualification_policy=DEMO_POLICY,stress_checks_advisory=True,
                stress_resilient=all(c.get('passed') is True for c in checks),
                live_authorized=False)


def validate_config(c):
    if (c.get('method') not in ('MOMENTUM', 'MEAN_REVERSION', 'BREAKOUT')
            or c.get('side') not in ('BUY', 'SELL')
            or type(c.get('lookback')) is not int or c['lookback'] not in (12,24,48)
            or type(c.get('horizon')) is not int or c['horizon'] not in (4,12,24)
            or type(c.get('threshold')) not in (float,int) or c['threshold'] not in (.5,1,1.5)):
        raise ValueError('INVALID_DEMO_STRATEGY')


def signal(rows, index, config):
    validate_config(config)
    lookback = config['lookback']
    if index < max(lookback,14):
        return None
    prior = rows[index-lookback:index]
    scale = sum(r[2]-r[3] for r in rows[index-14:index])/14
    if not isfinite(scale) or scale <= 0:
        return None
    side = 1 if config['side']=='BUY' else -1
    close, threshold, family = rows[index][4], config['threshold'], config['method']
    trigger = ((close-prior[0][4])*side > threshold*scale if family=='MOMENTUM' else
               (sum(r[4] for r in prior)/lookback-close)*side > threshold*scale if family=='MEAN_REVERSION' else
               close > max(r[2] for r in prior)+(threshold-.5)*scale if side==1 else
               close < min(r[3] for r in prior)-(threshold-.5)*scale)
    return scale if trigger else None


def validate_rows(rows):
    if not isinstance(rows,list) or not 55<=len(rows)<=8192:
        raise ValueError('INVALID_DEMO_BARS')
    previous = None
    for row in rows:
        if (not isinstance(row,(list,tuple)) or len(row)<5
                or any(type(x) not in (int,float) or not isfinite(x) for x in row[:5])
                or min(row[:5])<=0 or row[2]<max(row[1],row[4])
                or row[3]>min(row[1],row[4]) or row[2]<row[3]
                or (previous is not None and row[0]<=previous)):
            raise ValueError('INVALID_DEMO_BARS')
        previous=row[0]


def qualify_variant(rows, config, *, spread, original_id):
    validate_config(config);validate_rows(rows)
    if type(spread) not in (int,float) or not isfinite(spread) or spread<0:
        raise ValueError('INVALID_DEMO_SPREAD')
    split=len(rows)*2//3;side=1 if config['side']=='BUY' else -1
    horizon=config['horizon'];samples=[[],[]]
    for i in range(max(config['lookback'],14),len(rows)-horizon,horizon+1):
        scale=signal(rows,i,config)
        if scale is None or spans_long_gap(rows,i,horizon):
            continue
        bucket=0 if i+horizon<split else 1 if i>=split else None
        if bucket is None:continue
        entry=rows[i+1][1];stop=entry-side*2*scale;target=entry+side*4*scale
        if min(stop,target)<=0:continue
        exit_price=rows[i+horizon][4]
        for bar in rows[i+1:i+horizon+1]:
            # Adverse-first when OHLC cannot distinguish intrabar order.
            if (bar[3]<=stop if side==1 else bar[2]>=stop):
                exit_price=min(stop,bar[1]) if side==1 else max(stop,bar[1]);break
            if (bar[2]>=target if side==1 else bar[3]<=target):
                exit_price=target;break
        samples[bucket].append(((exit_price-entry)*side/scale,scale))
    checks=[]
    for multiplier in (1,2,3):
        groups=[]
        for data in samples:
            values=[gross-multiplier*(spread/scale+.2) for gross,scale in data]
            groups.append(dict(n=len(values),mean=sum(values)/len(values) if values else None))
        checks.append(dict(multiplier=multiplier,development=groups[0],review=groups[1],
                           passed=all(g['n']>=30 and g['mean']>0 for g in groups)))
    identity=dict(version=VERSION,original_id=original_id,method=config['method'],side=config['side'],
                  lookback=config['lookback'],horizon=horizon,threshold=config['threshold'],
                  stop_range=2,target_range=4,bar_ambiguity='ADVERSE_FIRST',gap_policy=GAP_POLICY)
    ident=sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    return demo_policy(dict(id=ident,parameters=identity,checks=checks,
                independent_holdout=False,prospective_validation=False,live_authorized=False))
