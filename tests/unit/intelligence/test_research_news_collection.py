from datetime import datetime,timezone,timedelta
from hashlib import sha256
import sqlite3
import unittest
from katarina.intelligence.news.research_news_collection import collect,parse_feed,event_study,allowed,describe_body,SOURCES
from katarina.intelligence.perception.observational_associations import observe_associations


class ResearchNewsTests(unittest.TestCase):
    def test_existing_body_cache_preserves_actual_first_known_time(self):
        self.db.execute('CREATE TABLE contextual_market_articles(url,published,body,fetched,sha256)')
        published=(self.now-timedelta(hours=2)).isoformat()
        known=(self.now-timedelta(hours=1)).isoformat()
        body='actual cached article body'
        self.db.execute('INSERT INTO contextual_market_articles VALUES(?,?,?,?,?)',
            ('https://www.cnbc.com/a',published,body,known,sha256(body.encode()).hexdigest()))
        result=collect(self.db,self.now,exchange=lambda *a:b'<rss/>')
        self.assertEqual(result['new_documents'][0]['known_utc'],known)
        self.assertEqual(result['new_documents'][0]['source'],'cnbc')
        result=collect(self.db,self.now,exchange=lambda *a:b'<rss/>')
        self.assertEqual(result['new_documents'],[])

    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.now=datetime.now(timezone.utc)
    def tearDown(self):self.db.close()

    def test_rss_and_rdf_feed_dates_and_hosts(self):
        date=(self.now-timedelta(hours=1)).isoformat()
        xml=f'<rss><channel><item><title>Policy</title><link>https://www.rba.gov.au/media.html</link><pubDate>{date}</pubDate></item></channel></rss>'.encode()
        self.assertEqual(len(parse_feed(xml,'www.rba.gov.au',self.now)),1)
        self.assertEqual(parse_feed(xml,'other.example',self.now),[])
        rdf=f'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/"><item><title>Policy</title><link>https://www.rba.gov.au/media.html</link><dc:date>{date}</dc:date></item></rdf:RDF>'.encode()
        self.assertEqual(len(parse_feed(rdf,'www.rba.gov.au',self.now)),1)
        self.assertFalse(allowed('https://www.rba.gov.au@127.0.0.1/file','www.rba.gov.au'))

    def test_real_body_required_cached_and_first_seen_not_backdated(self):
        date=(self.now-timedelta(days=1)).isoformat()
        calls=[]
        def exchange(url,host):
            calls.append(url)
            if '/feed/' in url or '/rss/' in url or '/feeds/' in url:
                return f'<rss><channel><item><title>Policy</title><link>https://{host}/statement</link><pubDate>{date}</pubDate></item></channel></rss>'.encode()
            return ('<html>'+''.join('<p>'+'policy economy inflation '*40+'</p>' for _ in range(3))+'</html>').encode()
        result=collect(self.db,self.now,exchange=exchange)
        self.assertEqual(result['status'],'FULL_BODY_STORED')
        row=result['new_documents'][0]
        self.assertGreater(datetime.fromisoformat(row['known_utc']),datetime.fromisoformat(date))
        self.assertFalse(row['semantic_interpretation_verified'])
        for _ in range(len(SOURCES)-1):collect(self.db,self.now,exchange=exchange)
        before=len(calls)
        result=collect(self.db,self.now,exchange=exchange)
        self.assertEqual(result['status'],'CACHED')
        self.assertEqual(len(calls),before)

    def test_event_study_waits_for_future_and_reports_observed_reaction(self):
        collect(self.db,self.now,exchange=lambda *a:b'<rss/>')
        known=self.now-timedelta(hours=2)
        body='body'
        self.db.execute('INSERT INTO research_news_documents VALUES(?,?,?,?,?,?,?,?)',
            ('id','boc','https://www.bankofcanada.ca/a',known.isoformat(),known.isoformat(),body,sha256(body.encode()).hexdigest(),'summary'))
        for seconds,mid in [(0,100),(900,101),(3600,99)]:
            clock=known+timedelta(seconds=seconds)
            observe_associations(self.db,{'A':(mid,mid,clock.timestamp())},clock)
        result=event_study(self.db,self.now)
        self.assertEqual(len(result['groups']),2)
        self.assertAlmostEqual(result['groups'][0]['mean_mid_return_bps'],100)
        self.assertEqual(result['groups'][0]['status'],'INSUFFICIENT_EVENTS')
        self.assertEqual(result['stored_reactions'],2)
        self.assertEqual(event_study(self.db,self.now)['stored_reactions'],2)
        self.assertFalse(result['causality_proven'])
        self.assertFalse(result['strategy_validated'])

    def test_missing_quotes_are_not_invented(self):
        collect(self.db,self.now,exchange=lambda *a:b'<rss/>')
        result=event_study(self.db,self.now)
        self.assertEqual(result['status'],'WAITING_FOR_DATA')

    def test_topics_extract_actual_context_without_claiming_sentiment(self):
        text='We use cookies and subscribe to our newsletter to receive updates daily.\nInflation and interest rates remain elevated as the dollar rises while oil supply falls across global markets.'
        result=describe_body(text)
        self.assertIn('RATES_INFLATION',result['topics'])
        self.assertIn('ENERGY_SUPPLY',result['topics'])
        self.assertNotIn('cookies',result['extractive_summary'])
        self.assertEqual(result['sentiment'],'NOT_INFERRED')

    def test_http_failure_remains_visible_and_other_sources_continue(self):
        from urllib.error import HTTPError
        def exchange(url,host):raise HTTPError(url,403,'Forbidden',None,None)
        result=collect(self.db,self.now,exchange=exchange)
        source=result['source_checked']
        self.assertEqual(result['source_statuses'][source],'HTTP_403')
        again=collect(self.db,self.now,exchange=lambda *a:b'<rss/>')
        self.assertNotEqual(again['source_checked'],source)
        self.assertEqual(again['source_statuses'][source],'HTTP_403')

    def test_quote_observed_after_window_cannot_repair_missing_history(self):
        collect(self.db,self.now,exchange=lambda *a:b'<rss/>')
        known=self.now-timedelta(hours=2);body='Inflation and monetary policy.'
        self.db.execute('INSERT INTO research_news_documents VALUES(?,?,?,?,?,?,?,?)',
            ('id','fed','https://www.federalreserve.gov/a',known.isoformat(),known.isoformat(),body,sha256(body.encode()).hexdigest(),'summary'))
        observe_associations(self.db,{},self.now)
        self.db.execute('INSERT INTO research_market_samples VALUES(?,?,?,?)',('A',known.timestamp(),self.now.timestamp(),100))
        self.db.execute('INSERT INTO research_market_samples VALUES(?,?,?,?)',('A',known.timestamp()+900,self.now.timestamp(),101))
        result=event_study(self.db,self.now)
        self.assertEqual(result['stored_reactions'],0)
        self.assertEqual(result['groups'],[])

    def test_five_minute_reaction_persists_with_topic_and_no_duplicate(self):
        collect(self.db,self.now,exchange=lambda *a:b'<rss/>')
        known=self.now-timedelta(minutes=6)
        body='Inflation and interest rates influence the dollar and global oil supply.'
        self.db.execute('INSERT INTO research_news_documents VALUES(?,?,?,?,?,?,?,?)',
            ('id','fed','https://www.federalreserve.gov/a',known.isoformat(),known.isoformat(),body,sha256(body.encode()).hexdigest(),'summary'))
        for seconds,mid in [(1,100),(301,101)]:
            clock=known+timedelta(seconds=seconds)
            observe_associations(self.db,{'A':(mid,mid,clock.timestamp())},clock)
        result=event_study(self.db,self.now)
        self.assertEqual(result['stored_reactions'],1)
        self.assertEqual(result['pending_windows'],2)
        self.assertEqual(result['groups'][0]['horizon_seconds'],300)
        self.assertIn('RATES_INFLATION',[r['topic'] for r in result['topic_groups']])
        self.assertAlmostEqual(result['groups'][0]['mean_mid_return_bps'],100)
        self.assertEqual(event_study(self.db,self.now)['stored_reactions'],1)

    def test_failed_sources_retry_after_five_minutes_not_every_cycle(self):
        from urllib.error import HTTPError
        def failure(url,host):raise HTTPError(url,403,'Forbidden',None,None)
        for _ in SOURCES:collect(self.db,self.now,exchange=failure)
        self.assertEqual(collect(self.db,self.now+timedelta(seconds=299),exchange=failure)['status'],'CACHED')
        result=collect(self.db,self.now+timedelta(seconds=301),exchange=lambda *a:b'<rss/>')
        self.assertEqual(result['status'],'NO_NEW_ARTICLE')

    def test_public_http_request_declares_supported_feed_and_article_formats(self):
        from unittest.mock import patch,MagicMock
        from katarina.intelligence.news.research_news_collection import fetch
        response=MagicMock();response.__enter__.return_value.read.return_value=b'<rss/>'
        opener=MagicMock();opener.open.return_value=response
        with patch('katarina.intelligence.news.research_news_collection.build_opener',return_value=opener):
            self.assertEqual(fetch('https://www.rba.gov.au/rss/a.xml','www.rba.gov.au'),b'<rss/>')
        request=opener.open.call_args.args[0]
        self.assertIn('application/rss+xml',request.get_header('Accept'))
        self.assertIn('text/html',request.get_header('Accept'))
