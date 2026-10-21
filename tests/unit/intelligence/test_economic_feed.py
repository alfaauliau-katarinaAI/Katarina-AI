import unittest
from datetime import datetime,timezone
import json

from katarina.intelligence.economic_feed import EconomicFeedGate, JsonEconomicCalendarAdapter


class EconomicFeedTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,6,12,0,tzinfo=timezone.utc)

    def test_missing_calendar_fails_closed(self):
        d=EconomicFeedGate().assess(None,now_utc=self.now)
        self.assertTrue(d.blackout)
        self.assertFalse(d.ready)

    def test_stale_calendar_fails_closed(self):
        raw=json.dumps({
            "provider":"test",
            "fetched_at_utc":"2026-10-06T10:00:00+00:00",
            "valid_until_utc":"2026-10-06T11:00:00+00:00",
            "events":[],
        })
        snap=JsonEconomicCalendarAdapter().parse(raw)
        self.assertTrue(EconomicFeedGate().assess(snap,now_utc=self.now).blackout)

    def test_high_impact_usd_event_blocks(self):
        raw=json.dumps({
            "provider":"test",
            "fetched_at_utc":"2026-10-06T11:55:00+00:00",
            "valid_until_utc":"2026-10-06T13:00:00+00:00",
            "events":[{"name":"NFP","timestamp_utc":"2026-10-06T12:10:00+00:00","impact":3,"currencies":["USD"]}],
        })
        snap=JsonEconomicCalendarAdapter().parse(raw)
        d=EconomicFeedGate().assess(snap,now_utc=self.now)
        self.assertTrue(d.blackout)
        self.assertEqual(d.event_name,"NFP")

    def test_fresh_clear_calendar_allows(self):
        raw=json.dumps({
            "provider":"test",
            "fetched_at_utc":"2026-10-06T11:55:00+00:00",
            "valid_until_utc":"2026-10-06T13:00:00+00:00",
            "events":[],
        })
        d=EconomicFeedGate().assess(JsonEconomicCalendarAdapter().parse(raw),now_utc=self.now)
        self.assertTrue(d.ready)
        self.assertFalse(d.blackout)


if __name__=="__main__": unittest.main()
