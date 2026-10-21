"""Observer routes research-only shadow proposals to the correct broker symbol."""
import unittest
from unittest.mock import patch
from tests.unit.intelligence.test_multi_market_brain import market,ClearContext,bars,NOW
from katarina.intelligence.multi_market_brain import screen
from katarina.intelligence.symbol_playbooks import SYMBOLS

def record(symbol="NAS100.vx",mode=4):
    row=market(symbol,mode)
    row["m1_bars"]=bars()
    row["m5_bars"]=bars(seconds=300)
    row["point"]=.1
    row["tick_size"]=.1
    row["stop_level_points"]=3
    return row

def fake_proposal(symbol,one,five,day,now):
    return [dict(family=SYMBOLS[symbol],side="BUY",signal_atr=1.,
                hypothetical_stop=109.,hypothetical_target=116.5,
                max_holding_minutes=45)]

class MarketSpecificObserverTests(unittest.TestCase):
    def test_unknown_symbol_never_receives_generic_strategy(self):
        result=screen([record("UNKNOWN.vx")],ClearContext(),NOW)
        self.assertEqual(result["shadow_candidate_count"],0)
        self.assertFalse(result["live_execution_enabled"])

    def test_registered_symbol_uses_named_playbook_only(self):
        with patch("katarina.intelligence.symbol_playbooks.propose",
                   side_effect=fake_proposal) as mocked:
            result=screen([record("NAS100.vx")],ClearContext(),NOW)
        self.assertEqual(mocked.call_count,1)
        self.assertEqual(result["shadow_candidate_count"],1)
        offer=result["symbols"][0]["shadow_hypotheses"][0]
        self.assertEqual(offer["family"],SYMBOLS["NAS100.vx"])
        self.assertFalse(offer["live_risk_authorized"])
        self.assertTrue(offer["playbook_is_symbol_specific"])
        self.assertFalse(result["live_execution_enabled"])

    def test_session_symbol_needs_intraday_history(self):
        with patch("katarina.intelligence.symbol_playbooks.propose") as mocked:
            result=screen([record("US30.vx")],ClearContext(),NOW)
        mocked.assert_not_called()
        self.assertEqual(result["shadow_candidate_count"],0)

    def test_broker_sell_only_rejects_buy_research_hypothesis(self):
        with patch("katarina.intelligence.symbol_playbooks.propose",
                   side_effect=fake_proposal):
            result=screen([record("NAS100.vx",mode=2)],ClearContext(),NOW)
        self.assertEqual(result["shadow_candidate_count"],0)

    def test_invalid_stop_geometry_never_published(self):
        def wrong_stop(symbol,one,five,day,now):
            return [dict(family=SYMBOLS[symbol],side="BUY",signal_atr=1.,
                hypothetical_stop=112.45,hypothetical_target=114.,
                max_holding_minutes=45)]
        with patch("katarina.intelligence.symbol_playbooks.propose",
                   side_effect=wrong_stop):
            result=screen([record("NAS100.vx")],ClearContext(),NOW)
        self.assertEqual(result["shadow_candidate_count"],0)

if __name__=="__main__":
    unittest.main()
