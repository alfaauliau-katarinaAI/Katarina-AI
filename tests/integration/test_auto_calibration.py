from contextlib import closing
from datetime import datetime,timezone
import json,sqlite3,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as S
from katarina.intelligence.broker.auto_calibration import compare_window,calibrate_due,_db,verified_window_offset

class Broker:
    TIMEFRAME_M5=5;COPY_TICKS_INFO=1
    def __init__(self,raw,offset=180,ambiguous=False):self.raw=raw;self.offset=offset;self.ambiguous=ambiguous;self.calls=[]
    def terminal_info(self):return S(trade_allowed=False)
    def symbol_info(self,s):return S(chart_mode=0,point=.01)
    def symbol_select(self,*a):return True
    def bars(self):return [dict(time=self.raw+i*300,open=100.,high=102.,low=99.,close=101.,tick_volume=5) for i in range(2)]
    def copy_rates_from_pos(self,*a):return self.bars()
    def copy_rates_range(self,*a):return self.bars()
    def copy_ticks_range(self,s,start,end,flag):
        self.calls.append((start,end))
        valid=[self.raw-self.offset*60,self.raw+300-self.offset*60]
        if not self.ambiguous and int(start.timestamp()) not in valid:return []
        return [dict(time_msc=int((start.timestamp()+i*30)*1000),bid=v,ask=v+.1) for i,v in enumerate((100.,102.,99.,100.,101.))]

class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE lab_universe(symbol TEXT)');self.db.execute("INSERT INTO lab_universe VALUES('EURUSD')")
        self.db.execute('CREATE TABLE lab_bars(symbol TEXT,stamp INTEGER)')
        self.now=datetime.fromtimestamp(1800000000//300*300,timezone.utc)
        self.raw=int(self.now.timestamp())+180*60-1800
        self.b=Broker(self.raw)
        self.write_reference()
    def write_reference(self):
        (self.root/'latest.json').write_text(json.dumps({'time_reference':dict(observed_at_utc=self.now.isoformat(),broker_server_shift_minutes=180,confirming_symbols=5,canonical_market_clock='MT5_COPY_TICKS_RANGE_TIME_MSC_UTC')}))
    def test_exact_two_window_evidence_is_scoped_and_retains_ticks(self):
        result=calibrate_due(self.db,self.b,self.root,self.now)
        self.assertEqual(result['status'],'MATCHED_WINDOW_ALIGNMENT');self.assertEqual(result['verified_windows'],2)
        self.assertFalse(result['historical_dst_verified'])
        with closing(_db(self.root)) as db:
            self.assertEqual(verified_window_offset(db,'EURUSD',self.raw),180)
            self.assertIsNone(verified_window_offset(db,'EURUSD',self.raw+600))
            self.assertGreater(db.execute('SELECT MAX(length(ticks_zlib)) FROM calibration_runs').fetchone()[0],0)
        self.assertEqual(calibrate_due(self.db,self.b,self.root,self.now)['status'],'WAIT_CALIBRATION_INTERVAL')
    def test_ambiguous_alignment_never_creates_mapping(self):
        self.b.ambiguous=True
        self.assertEqual(calibrate_due(self.db,self.b,self.root,self.now)['status'],'AMBIGUOUS_WINDOW_ALIGNMENT')
        with closing(_db(self.root)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM calibrated_windows').fetchone()[0],0)
    def test_incomplete_volume_and_future_tick_are_rejected(self):
        bar=self.b.bars()[0];start=self.raw-180*60
        ticks=[dict(time_msc=(start+i)*1000,bid=100,ask=101) for i in range(5)]
        bar['tick_volume']=6
        self.assertEqual(compare_window(bar,ticks,180,self.now.timestamp(),.01)['reason'],'TICK_VOLUME_COVERAGE_MISMATCH')
        ticks[-1]['time_msc']=(start+301)*1000
        self.assertFalse(compare_window(bar,ticks,180,self.now.timestamp(),.01)['matched'])
    def test_stale_reference_cannot_trigger_broker_reads(self):
        self.now=datetime.fromtimestamp(self.now.timestamp()+181,timezone.utc)
        result=calibrate_due(self.db,self.b,self.root,self.now)
        self.assertEqual(result['status'],'MORE_BROKER_EVIDENCE_REQUIRED');self.assertFalse(self.b.calls)
    def test_owner_stop_prevents_reads_and_expired_window_not_extrapolated(self):
        (self.root/'continuous.stop').touch()
        self.assertEqual(calibrate_due(self.db,self.b,self.root,self.now)['status'],'OWNER_STOP_REQUEST')
        self.assertFalse(self.b.calls)
    def test_conflicting_new_proof_invalidates_old_mapping_without_erasing_it(self):
        calibrate_due(self.db,self.b,self.root,self.now)
        with closing(_db(self.root)) as db,db:
            db.execute('UPDATE calibrated_windows SET offset_minutes=120')
            db.execute("DELETE FROM calibration_meta WHERE key='last_attempt'")
            db.execute('UPDATE calibration_targets SET visits=0')
        self.now=datetime.fromtimestamp(self.now.timestamp()+1,timezone.utc);self.write_reference()
        result=calibrate_due(self.db,self.b,self.root,self.now)
        self.assertEqual(result['status'],'CONFLICTING_WINDOW_EVIDENCE')
        with closing(_db(self.root)) as db:
            self.assertIsNone(verified_window_offset(db,'EURUSD',self.raw))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM calibrated_windows').fetchone()[0],2)

    def test_volume_mismatch_uses_full_stream_without_weakening_coverage(self):
        self.b.COPY_TICKS_ALL=2
        original=self.b.copy_ticks_range
        # Use five valid partial INFO ticks versus six required full ticks.
        def six(symbol,start,end,flag):
            rows=original(symbol,start,end,flag)
            if rows and flag==self.b.COPY_TICKS_ALL:
                rows.insert(-1,dict(time_msc=rows[-1]['time_msc']-1000,bid=100.,ask=100.1))
            return rows
        self.b.copy_ticks_range=six
        self.b.bars=lambda:[dict(time=self.raw+i*300,open=100.,high=102.,low=99.,close=101.,tick_volume=6) for i in range(2)]
        result=calibrate_due(self.db,self.b,self.root,self.now)
        self.assertEqual(result['status'],'MATCHED_WINDOW_ALIGNMENT')
        with closing(_db(self.root)) as db:
            report=json.loads(db.execute("SELECT report_json FROM calibration_runs WHERE json_extract(report_json,'$.status')='MATCHED_WINDOW_ALIGNMENT'").fetchone()[0])
        matching=[x for x in report['results'] if x['offset_minutes']==180][0]
        self.assertTrue(all(x['tick_source']=='COPY_TICKS_ALL' for x in matching['windows']))
        self.assertTrue(all(x['ticks']==x['expected_tick_volume']==6 for x in matching['windows']))

    def test_partial_history_retries_same_frozen_windows(self):
        original=self.b.copy_ticks_range
        self.b.copy_ticks_range=lambda *args:original(*args)[:-1]
        result=calibrate_due(self.db,self.b,self.root,self.now)
        self.assertEqual(result['status'],'MORE_BROKER_EVIDENCE_REQUIRED')
        self.assertEqual(result['pending_windows'],1)
        self.now=datetime.fromtimestamp(self.now.timestamp()+121,timezone.utc);self.write_reference()
        self.b.copy_ticks_range=original
        self.b.copy_rates_from_pos=lambda *a:(_ for _ in ()).throw(AssertionError('must reuse frozen windows'))
        result=calibrate_due(self.db,self.b,self.root,self.now)
        self.assertEqual(result['status'],'MATCHED_WINDOW_ALIGNMENT')
        self.assertEqual(result['pending_windows'],0)
        with closing(_db(self.root)) as db:
            self.assertEqual(db.execute('SELECT status,attempts FROM calibration_pending').fetchone(),('DONE',2))
