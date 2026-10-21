import unittest
from datetime import datetime, timedelta, timezone

from katarina.intelligence.perception.adaptive_regime import (
    AdaptiveRegimeEngine, ClosedFrame, MarketState, Playbook, StructuralEvidence)
from katarina.intelligence.perception.causal_seasonality import (
    CausalSeasonality, HistoricalOutcome)
from katarina.engines.adaptive_scalper import (
    AdaptiveScalpRouter, ClosedPriceContext, ScalpSide)

T = datetime(2026,10,9,15,tzinfo=timezone.utc)

def frames(h=1, m15=1, m5=1, adx=25, er=.40):
    return {k: ClosedFrame(di, adx, er, float(1.), T-timedelta(minutes=5))
            for k,di in (("H1",h),("M15",m15),("M5",m5))}

def candle(**overrides):
    d=dict(open=100,high=101,low=99.7,close=100.5,previous_close=100.2,
           previous_channel_high=102,previous_channel_low=98,atr=1.5,
           spread_to_atr=.08,data_fresh=True,broker_session_open=True)
    d.update(overrides)
    return ClosedPriceContext(**d)

class RegimeV2Tests(unittest.TestCase):
    def setUp(self): self.e = AdaptiveRegimeEngine()
    def test_trend_and_pullback(self):
        up=self.e.assess(frames=frames(),as_of_utc=T)
        self.assertEqual(up.state,MarketState.TREND_UP)
        self.assertEqual(up.playbook,Playbook.TREND_PULLBACK)
        self.assertFalse(up.execution_authorized)
        down=self.e.assess(frames=frames(-1,-1,-1),as_of_utc=T)
        self.assertEqual(down.state,MarketState.TREND_DOWN)
        pullback=self.e.assess(frames=frames(1,1,-1),as_of_utc=T)
        self.assertEqual(pullback.state,MarketState.PULLBACK_UP)
    def test_range_and_unconfirmed_transition(self):
        r=self.e.assess(frames=frames(0,0,0,adx=12,er=.1),as_of_utc=T)
        self.assertEqual(r.state,MarketState.SIDEWAYS)
        x=self.e.assess(frames=frames(1,-1,1,adx=35,er=.9),as_of_utc=T)
        self.assertEqual(x.state,MarketState.TRANSITION)
    def test_structural_states(self):
        r=self.e.assess(frames=frames(-1,1,1),as_of_utc=T,
                        structure=StructuralEvidence(swing_reclaim=1,rejection_direction=1))
        self.assertEqual(r.state,MarketState.REVERSAL_UP)
        b=self.e.assess(frames=frames(),as_of_utc=T,
                        structure=StructuralEvidence(swing_break=1,atr_ratio=1.3))
        self.assertEqual(b.state,MarketState.BREAKOUT_UP)
        shock=self.e.assess(frames=frames(),as_of_utc=T,
                            structure=StructuralEvidence(atr_ratio=3))
        self.assertEqual(shock.state,MarketState.VOLATILITY_SHOCK)
    def test_future_leakage_and_invalid_values(self):
        bad=frames()
        bad["M5"]=ClosedFrame(1,25,.3,1,T+timedelta(seconds=1))
        self.assertEqual(self.e.assess(frames=bad,as_of_utc=T).state,MarketState.UNKNOWN)
        self.assertEqual(self.e.assess(frames=frames(),as_of_utc=T,
            structure=StructuralEvidence(atr_ratio=-1)).state,MarketState.UNKNOWN)

class RouterTests(unittest.TestCase):
    def setUp(self): self.e=AdaptiveRegimeEngine(); self.router=AdaptiveScalpRouter()
    def test_trend_lightweight_signal(self):
        r=self.e.assess(frames=frames(),as_of_utc=T)
        plan=self.router.plan("XAUUSD.vx",r,candle())
        self.assertEqual(plan.side,ScalpSide.BUY)
        self.assertTrue(plan.ready_for_research)
        self.assertFalse(plan.live_risk_authorized)
    def test_range_edge_no_rsi_required(self):
        r=self.e.assess(frames=frames(0,0,0,adx=12,er=.10),as_of_utc=T)
        plan=self.router.plan("EURUSD.vx",r,candle(open=98.2,high=98.8,low=97.9,
                     close=98.6,previous_close=98.3))
        self.assertEqual(plan.side,ScalpSide.BUY)
        self.assertEqual(plan.strategy,Playbook.RANGE_FADE)
    def test_cost_blackout_and_stale_still_block(self):
        r=self.e.assess(frames=frames(),as_of_utc=T)
        for override in (dict(spread_to_atr=.5),dict(news_blackout=True),
                         dict(data_fresh=False),dict(broker_session_open=False)):
            self.assertFalse(self.router.plan("XAUUSD.vx",r,
                candle(**override)).ready_for_research)

class CausalSeasonalityTests(unittest.TestCase):
    def test_no_future_leak_and_symbol_isolation(self):
        s=CausalSeasonality(min_bin_samples=5,prior_weight=5)
        old=[HistoricalOutcome("XAUUSD.vx",T-timedelta(days=n+10),
              T-timedelta(days=n+9),n%2==0) for n in range(20)]
        future=[HistoricalOutcome("XAUUSD.vx",T-timedelta(minutes=3),
                T+timedelta(hours=2),True) for _ in range(30)]
        self.assertEqual(s.train(old+future,cutoff_utc=T),20)
        a=s.estimate("XAUUSD.vx",as_of_utc=T)
        self.assertEqual(a.baseline_up_rate,.5)
        b=s.estimate("NAS100.vx",as_of_utc=T)
        self.assertEqual(b.directional_tilt,0)
        self.assertEqual(b.hour_samples,0)
        self.assertRaises(ValueError,s.estimate,"XAUUSD.vx",
                          as_of_utc=T-timedelta(seconds=1))

from katarina.intelligence.perception.closed_swing_structure import ClosedBar, ClosedSwingStructure

class ClosedStructureTests(unittest.TestCase):
    def setUp(self):
        self.engine=ClosedSwingStructure()
        self.history=[ClosedBar(T-timedelta(minutes=5*(44-i)),
                        100,101,99,100.2) for i in range(44)]
    def test_prior_only_reclaim_and_breakout(self):
        spring=ClosedBar(T,99.5,100.5,97,100.2)
        x=self.engine.extract(self.history+[spring],as_of_utc=T,spread=.1)
        self.assertEqual(x.swing_reclaim,1)
        self.assertEqual(x.swing_break,0)
        blast=ClosedBar(T,100,108,99,107)
        y=self.engine.extract(self.history+[blast],as_of_utc=T,spread=.1)
        self.assertEqual(y.swing_break,1)
        self.assertGreater(y.atr_ratio,1.1)
    def test_future_bar_fails_closed(self):
        future=ClosedBar(T+timedelta(minutes=5),100,101,99,100.2)
        with self.assertRaises(ValueError):
            self.engine.extract(self.history+[future],as_of_utc=T,spread=.1)


from katarina.intelligence.cognition.adaptive_observation import KatarinaAdaptiveBrainV2

class BrainV2IntegrationTests(unittest.TestCase):
    def test_closed_breakout_routes_without_orders(self):
        bars=[ClosedBar(T-timedelta(minutes=5*(44-i)),100,101,99,100.2)
              for i in range(44)]
        bars.append(ClosedBar(T,100,108,99,107))
        f=frames()
        f["M5"]=ClosedFrame(1,27,.6,2.5,T)
        output=KatarinaAdaptiveBrainV2().observe(symbol="NAS100.vx",frames=f,
             closed_bars=bars,as_of_utc=T,actual_spread=.10,
             broker_session_open=True,data_fresh=True,news_blackout=False)
        self.assertEqual(output.regime.state,MarketState.BREAKOUT_UP)
        self.assertTrue(output.proposal.ready_for_research)
        self.assertEqual(output.proposal.side,ScalpSide.BUY)
        self.assertFalse(output.live_risk_authorized)
        self.assertFalse(output.proposal.live_risk_authorized)

if __name__=="__main__":
    unittest.main()
