from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import tempfile
import unittest
from katarina.monitoring.pair_activity import read_pair_activity

class PairActivityTests(unittest.TestCase):
 def test_parallel_pair_routes_privacy_and_process_binding(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);now=datetime.now(timezone.utc);s=now.isoformat()
   e=lambda pair,phase,seq:dict(symbol=pair,phase=phase,state='STARTED',seq=seq,at_utc=s,price=100,login='PRIVATE_SENTINEL')
   events=[e('XAUUSD.vx','TEST_MOMENTUM_H4',1),e('EURUSD.vx','TEST_BREAKOUT_H4',2)]
   (r/'runtime-activity.json').write_text(json.dumps(dict(pid=7,events=events,active=events)))
   (r/'latest.json').write_text(json.dumps(dict(observed_at_utc=s,symbols={'USDJPY.vx':{'bid':10,'account':'PRIVATE_SENTINEL'}})))
   out=read_pair_activity(r,7,allowed=True,now=now)
   self.assertEqual(len(out['active']),2);self.assertEqual(len(out['symbols']),3)
   self.assertNotIn('PRIVATE_SENTINEL',json.dumps(out));self.assertNotIn('price"',json.dumps(out));self.assertNotIn('bid',json.dumps(out))
   self.assertEqual(read_pair_activity(r,8,allowed=True,now=now)['status'],'NOT_ATTESTED')
   self.assertEqual(read_pair_activity(r,7,allowed=False,now=now)['events'],[])
   self.assertEqual(read_pair_activity(r,7,allowed=True,now=now+timedelta(seconds=181))['symbols'],[])
