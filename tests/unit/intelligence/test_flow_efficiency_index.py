import unittest
from katarina.intelligence.perception.flow_efficiency_index import KatarinaFlowEfficiencyIndex

class KFEIUnitTests(unittest.TestCase):
    def setUp(self):self.k=KatarinaFlowEfficiencyIndex()
    def test_monotonic_up_and_down_are_opposites(self):
        base=[100+.2*j for j in range(13)]
        a=self.k.calculate(base,[1.]*51,broker_spread=.03)
        b=self.k.calculate(list(reversed(base)),[1.]*51,broker_spread=.03)
        self.assertEqual(a.regime_hint,"DIRECTIONAL_DRIVE")
        self.assertAlmostEqual(a.directional_strength,-b.directional_strength)
        self.assertAlmostEqual(a.efficiency_ratio,1.)
        self.assertFalse(a.live_execution_authorized)
    def test_chop_low_efficiency(self):
        closes=[100 if i%2==0 else 100.2 for i in range(13)]
        x=self.k.calculate(closes,[1.]*51,broker_spread=.08)
        self.assertEqual(x.regime_hint,"SIDEWAYS_OR_NOISE")
        self.assertAlmostEqual(x.directional_strength,0.)
    def test_spread_recorded_not_conflated_with_direction(self):
        closes=[100+.3*j for j in range(13)]
        a=self.k.calculate(closes,[1.]*51,broker_spread=.02)
        b=self.k.calculate(closes,[1.]*51,broker_spread=.20)
        self.assertEqual(a.directional_strength,b.directional_strength)
        self.assertGreater(b.spread_to_atr,a.spread_to_atr)
    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            self.k.calculate([100]*12,[1]*51,broker_spread=.1)
        with self.assertRaises(ValueError):
            self.k.calculate([100]*13,[1]*51,broker_spread=float('nan'))
        with self.assertRaises(ValueError):
            self.k.calculate([100]*13,[0]*51,broker_spread=.1)
if __name__=="__main__":unittest.main()
