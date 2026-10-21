import json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from katarina.intelligence.news.public_context import ContextStore,parse_news,parse_calendar
from katarina.intelligence.perception.screening import features,screen,correlation,save_observation
from katarina.intelligence.news.economic_feed import EconomicFeedGate,EconomicCalendarSnapshot
from katarina.intelligence.perception.economics import EconomicEvent

UTC=timezone.utc
NOW=datetime(2026,10,6,12,tzinfo=UTC)
RSS=b"<rss><channel><item><title>Policy statement</title><pubDate>Tue, 06 Oct 2026 10:00:00 GMT</pubDate><link>https://example.org</link></item></channel></rss>"

def calendar(events=None):
    return json.dumps(events or [dict(title="CPI",country="USD",date="2026-10-07T08:30:00-04:00",impact="High",forecast="2%",previous="3%")]).encode()

def bars(n=120,seconds=60):
    end=int(NOW.timestamp())-seconds
    return [dict(time=end-(n-1-i)*seconds,open=100+i*.1,high=101+i*.1,low=99+i*.1,close=100.5+i*.1,tick_volume=100+i%7) for i in range(n)]

class ClearContext:
    def assess(self,currencies,now):
        return dict(ready=True,reasons=[])

def market(symbol="A",mode=4):
    return dict(symbol=symbol,base="EUR",profit="USD",trade_mode=mode,
                connected=True,tick_time=NOW.timestamp(),bid=112.4,ask=112.5,
                m1=features(bars(),60,NOW),m5=features(bars(seconds=300),300,NOW),errors=[])

class PublicContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=ContextStore(Path(self.temp.name)/"test.sqlite")
    def tearDown(self):
        self.store.db.close();self.temp.cleanup()
    def seed(self):
        self.store.record("calendar",NOW,calendar())
        self.store.record("fed",NOW,RSS)
    def test_future_publication_excluded(self):
        self.assertEqual(parse_news(RSS,"fed",NOW-timedelta(hours=3))["items"],[])
    def test_first_seen_prevents_backdating(self):
        self.store.record("fed",NOW,RSS)
        self.assertFalse(self.store.latest("fed",NOW-timedelta(seconds=1))["ready"])
    def test_feed_no_headline_is_not_feed_failure(self):
        self.seed()
        self.assertTrue(self.store.assess(("USD",),NOW)["ready"])
    def test_feed_outage_overrides_prior_success(self):
        self.seed();self.store.record("fed",NOW+timedelta(seconds=1),error="Timeout")
        self.assertIn("news_currency_uncovered",self.store.assess(("USD",),NOW+timedelta(seconds=1))["reasons"])
    def test_stale_calendar(self):
        self.seed()
        self.assertIn("calendar_unavailable",self.store.assess(("USD",),NOW+timedelta(hours=2))["reasons"])
    def test_unknown_currency_not_silently_clear(self):
        self.seed()
        self.assertIn("calendar_currency_uncovered",self.store.assess(("ZAR",),NOW)["reasons"])
    def test_future_calendar_event_known_now_can_block(self):
        event=dict(title="NFP",country="USD",date=(NOW+timedelta(minutes=20)).isoformat(),impact="High")
        self.store.record("calendar",NOW,calendar([event]))
        self.assertIn("economic_blackout",self.store.assess(("USD",),NOW)["reasons"])
    def test_missing_actual_not_fabricated(self):
        parsed=parse_calendar(calendar(),NOW)
        self.assertFalse(parsed["actual_available"])
        self.assertIsNone(parsed["events"][0]["actual"])
        self.assertEqual(parsed["events"][0]["forecast"],"2%")
    def test_calendar_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            parse_calendar(calendar([dict(title="X",country="USD",date="2026-10-06T12:00:00",impact="High")]),NOW)
    def test_revision_preserves_old_vintage(self):
        self.seed()
        newer=RSS.replace(b"Policy statement",b"Revised statement")
        self.store.record("fed",NOW+timedelta(seconds=10),newer)
        self.assertEqual(self.store.latest("fed",NOW)["payload"]["items"][0]["title"],"Policy statement")
    def test_duplicate_headline(self):
        raw=RSS.replace(b"</channel>",RSS.split(b"<channel>")[1].split(b"</channel>")[0]+b"</channel>")
        self.assertEqual(len(parse_news(raw,"fed",NOW)["items"]),1)
    def test_failed_parse_stored_as_error(self):
        self.assertEqual(self.store.record("calendar",NOW,b"oops"),"ERROR")
        self.assertFalse(self.store.latest("calendar",NOW)["ready"])
    def test_asymmetric_blackout_checks_all_events(self):
        events=tuple(EconomicEvent(str(m),NOW+timedelta(minutes=m),3,("USD",)) for m in (-16,20))
        snap=EconomicCalendarSnapshot("test",NOW,NOW+timedelta(hours=1),events)
        decision=EconomicFeedGate().assess(snap,now_utc=NOW)
        self.assertTrue(decision.blackout)
        self.assertEqual(decision.event_name,"20")

class MarketBrainTests(unittest.TestCase):
    def test_closed_bars_only(self):
        data=bars();data[-1]["time"]=int(NOW.timestamp())
        with self.assertRaises(ValueError):features(data,60,NOW)
    def test_duplicate_bars_rejected(self):
        data=bars();data[-1]["time"]=data[-2]["time"]
        with self.assertRaises(ValueError):features(data,60,NOW)
    def test_nonfinite_prices_rejected(self):
        data=bars();data[-1]["close"]=float("nan")
        with self.assertRaises(ValueError):features(data,60,NOW)
    def test_scale_invariant_atr(self):
        data=bars()
        scaled=[{k:(v*100 if k in ("open","high","low","close") else v) for k,v in b.items()} for b in data]
        self.assertAlmostEqual(features(data,60,NOW)["atr_bps"],features(scaled,60,NOW)["atr_bps"])
    def test_cost_filter(self):
        row=market();row["ask"]=115
        self.assertEqual(screen([row],ClearContext(),NOW)["research_watchlist"],[])
    def test_close_only_not_candidate(self):
        result=screen([market(mode=3)],ClearContext(),NOW)
        self.assertEqual(result["research_watchlist"],[])
        self.assertEqual(result["symbols"][0]["allowed_sides"],[])
    def test_direction_restriction(self):
        self.assertEqual(screen([market(mode=2)],ClearContext(),NOW)["symbols"][0]["allowed_sides"],["SELL"])
    def test_stale_and_future_ticks(self):
        for offset in (-31,1):
            row=market();row["tick_time"]+=offset
            self.assertFalse(screen([row],ClearContext(),NOW)["symbols"][0]["research_candidate"])
    def test_rank_never_authorizes_trade(self):
        result=screen([market()],ClearContext(),NOW)
        self.assertEqual(result["research_watchlist"],["A"])
        self.assertEqual(result["symbols"][0]["action"],"NO_TRADE")
        self.assertFalse(result["live_execution_enabled"])
    def test_correlated_candidates_not_both_selected(self):
        result=screen([market("A"),market("B")],ClearContext(),NOW)
        self.assertEqual(result["research_watchlist"],["A"])
    def test_correlation_requires_overlap(self):
        self.assertIsNone(correlation({"1":1},{"2":1}))
    def test_context_outage_excludes_watchlist(self):
        class Missing:
            def assess(self,currencies,now):
                return dict(ready=False,reasons=["calendar_unavailable"])
        result=screen([market()],Missing(),NOW)
        self.assertEqual(result["research_watchlist"],[])
    def test_bar_evidence_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            store=ContextStore(Path(directory)/"db")
            for _ in range(2):
                row=market();row["m1_bars"]=bars()
                result=screen([row],ClearContext(),NOW)
                save_observation(store,result)
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM market_evidence").fetchone()[0],1)
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM brain_observations").fetchone()[0],2)
            self.assertNotIn("m1_bars",result["symbols"][0])
            store.db.close()
    def test_disconnected_broker(self):
        row=market();row["connected"]=False
        self.assertEqual(screen([row],ClearContext(),NOW)["research_watchlist"],[])

if __name__=="__main__":unittest.main()
