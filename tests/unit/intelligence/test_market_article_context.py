"""Prove full article reading never turns media into broker order clearance."""
import unittest
from datetime import datetime,timezone,timedelta
from katarina.intelligence.news.market_article_context import (
    official_url_is_not_implicit,parse_feed,parse_article,interpret_story,
    market_headline_relevant,
)
NOW=datetime(2026,10,12,13,0,tzinfo=timezone.utc)
STORY={"url":"https://www.cnbc.com/2026/10/12/china-gold-buying-interest-rate-.html",
       "title":"China is importing record amounts of gold, what it means for prices",
       "published_utc":(NOW-timedelta(hours=2)).isoformat()}


class MarketArticleBodyTests(unittest.TestCase):
    def test_source_url_is_verified_and_never_called_official_policy(self):
        for url in ("http://www.cnbc.com/x",
                    "https://www.cnbc.com.attacker.org/x",
                    "https://localhost/x",
                    "https://www.federalreserve.gov/x"):
            self.assertFalse(official_url_is_not_implicit(url))
        self.assertTrue(official_url_is_not_implicit(STORY["url"]))

    def test_offtopic_story_is_rejected(self):
        self.assertFalse(market_headline_relevant(
            "Authorities searched a politician over immigration paperwork"))
        self.assertTrue(market_headline_relevant(
            "China gold demand and central bank imports surge"))

    def test_only_dated_real_rss_items_accepted(self):
        ts=(NOW-timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        xml=("<?xml version='1.0'?><rss><channel><item>"
             "<title>China is importing record amounts of gold, what it means for prices</title>"
             "<link>"+STORY["url"]+"</link><pubDate>"+ts+"</pubDate>"
             "</item></channel></rss>")
        result=parse_feed(xml.encode(),NOW)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["url"],STORY["url"])
        self.assertEqual(parse_feed(xml.encode(),NOW+timedelta(days=3)),[])

    def test_full_html_paragraph_body_not_title_is_used(self):
        paragraph=("This official data from the customs administration describes "
            "changes in gold demand and imported volume. Analysts cautioned "
            "that price effects depend on exchange rates and wider yields. ")
        html=("<html><head><title>Gold rallies guaranteed</title></head><body>"+
              "".join("<p>"+paragraph*2+"</p>" for _ in range(4))+
              "</body></html>")
        sections=parse_article(html.encode())
        result=interpret_story(STORY,sections,NOW)
        self.assertGreater(result["jumlah_kata"],120)
        self.assertTrue(result["isi_artikel_dibaca"])
        self.assertIn("customs administration",result["inti_berdasarkan_isi"])
        self.assertNotIn("guaranteed",result["inti_berdasarkan_isi"])
        self.assertEqual(result["bias_harga_terverifikasi"],"UNCERTAIN")
        self.assertTrue(result["sumber_sekunder_bukan_izin_entry"])
        self.assertEqual(result["arah_kebijakan"],
                         "BELUM_DIVERIFIKASI_DARI_SUMBER_KEBIJAKAN_PRIMER")

    def test_short_body_cannot_forge_market_analysis(self):
        with self.assertRaises(ValueError):
            parse_article(b"<html><body><p>Gold rises.</p></body></html>")
        with self.assertRaises(ValueError):
            interpret_story(STORY,["Only headline as body"],NOW)


if __name__=="__main__": unittest.main()
