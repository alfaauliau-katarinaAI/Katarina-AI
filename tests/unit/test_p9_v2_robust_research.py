import json
import tempfile
import unittest
from pathlib import Path
from katarina.research.p9_v2_robust import ENGINES,load_candidate,quote_research_only

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"research"/"p9_v2_robust"/"P9_V2_ROBUST_RESEARCH_CANDIDATES.json"
class TestP9V2RobustResearch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=load_candidate(MANIFEST)
 def test_five_engines_only(self):
  self.assertEqual(len(ENGINES),5)
  self.assertFalse(self.d["risk_allocation"]["live_authorized"])
 def test_balanced_adr_low_normal_high(self):
  vals=[quote_research_only(self.d,engine="NAS_H4_SELL",adr_ratio=k,balance_usd=10000)
    for k in (.5,1.,1.4)]
  self.assertEqual([x.paper_risk_pct for x in vals],[2.25,3.,3.75])
  self.assertEqual([x.hypothetical_loss_usd for x in vals],[225.,300.,375.])
  self.assertTrue(all(not x.can_send_orders and x.authorized_live_risk_pct==0 for x in vals))
 def test_dd_brakes(self):
  h=quote_research_only(self.d,engine="XAU_H1_BUY",adr_ratio=1.,balance_usd=10000,closed_dd_pct=4.)
  v=quote_research_only(self.d,engine="XAU_H1_BUY",adr_ratio=1.,balance_usd=10000,closed_dd_pct=8.)
  self.assertEqual(h.paper_risk_pct,.375)
  self.assertEqual(v.paper_risk_pct,0.)
 def test_fail_closed_modes_and_input(self):
  for mode in ("LIVE","DEMO"):
   with self.assertRaises(PermissionError):
    quote_research_only(self.d,engine="NAS_H4_SELL",adr_ratio=1.,balance_usd=10000,mode=mode)
  for ratio in (0.,-1.,float("nan"),float("inf")):
   with self.assertRaises(ValueError):
    quote_research_only(self.d,engine="NAS_H4_SELL",adr_ratio=ratio,balance_usd=10000)
  with self.assertRaises(ValueError):
   quote_research_only(self.d,engine="XAU_H1_SELL",adr_ratio=1.,balance_usd=10000)
 def test_manifest_production_tamper_denied(self):
  d=json.loads(json.dumps(self.d))
  d["risk_allocation"]["live_authorized"]=True
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"candidate.json";f.write_text(json.dumps(d))
   with self.assertRaises(PermissionError):load_candidate(f)
 def test_max_stress_remains_paper(self):
  q=quote_research_only(self.d,engine="NAS_H4_SELL",adr_ratio=1.5,
    balance_usd=10000,profile="MAX_STRESS")
  self.assertEqual(q.paper_risk_pct,4.5)
  self.assertFalse(q.can_send_orders)
