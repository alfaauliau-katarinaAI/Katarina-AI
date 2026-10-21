"""Full-article market news context, auxiliary to official monetary evidence.

Read ONE existing CNBC world RSS publisher feed, then retrieve actual
article paragraphs. Bounded RSS and article requests, persistent cache,
no GitHub API polling. Media reports inform conditional narrative ONLY:
they do NOT become verified official MacroEvidence or trade clearance.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from urllib.parse import urlsplit
from html import unescape
import json
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET

from katarina.intelligence.news.verified_policy_context import _Paragraphs

FEED="https://www.cnbc.com/id/100727362/device/rss/rss.html"
HOST="www.cnbc.com"
MAX_FEED=600_000
MAX_ARTICLE=1_500_000
AGE_SECONDS=24*3600
TTL_SECONDS=1800
USER_AGENT="KatarinaMarketObserver/1.0"
MARKET_TITLE_KEYWORDS=re.compile(
    r"\b(gold|silver|oil|crude|energy|fed|fomc|interest\s+rates?|"
    r"inflation|cpi|ppi|payroll|employment|recession|central\s+bank|"
    r"tariffs?|forex|currency|currencies|dollar|euro|yen|yuan|"
    r"bond|yield|treasury|nasdaq|dow\s+jones|stocks?|equities|"
    r"bitcoin|crypto|opec|financial\s+markets?|economy|economic)\b",
    re.IGNORECASE,
)

def market_headline_relevant(title):
    return bool(MARKET_TITLE_KEYWORDS.search(title))


def official_url_is_not_implicit(url):
    """CNBC webpage is an attributed media article, NOT policy release."""
    try:
        u=urlsplit(url)
        return (u.scheme=="https" and u.hostname==HOST and
                u.username is None and u.password is None and
                u.port in (None,443))
    except ValueError:
        return False


def _fetch(url,limit,timeout=10):
    if not official_url_is_not_implicit(url):
        raise ValueError("non_whitelisted_media_host")
    req=urllib.request.Request(url,headers={
        "User-Agent":USER_AGENT,
        "Accept":"application/rss+xml,text/html;q=0.9,*/*;q=0.5",
    })
    try:
        import certifi
        tls=ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        tls=ssl.create_default_context()
    with urllib.request.urlopen(req,timeout=timeout,context=tls) as response:
        if response.status!=200 or not official_url_is_not_implicit(response.geturl()):
            raise ValueError("redirect_or_http_error")
        raw=response.read(limit+1)
    if len(raw)>limit:
        raise ValueError("article_or_feed_too_large")
    return raw


def parse_feed(raw,now):
    if len(raw)>MAX_FEED:raise ValueError("oversize_rss")
    tree=ET.fromstring(raw)
    if tree.find("./channel") is None:
        raise ValueError("malformed_cnbc_rss")
    stories=[]
    seen=set()
    for item in tree.findall("./channel/item"):
        url=(item.findtext("link") or "").split("?")[0].split("#")[0].strip()
        title=" ".join(unescape(item.findtext("title") or "").split())
        date=item.findtext("pubDate") or ""
        if (not official_url_is_not_implicit(url) or len(title)<24
                or not market_headline_relevant(title) or url in seen):
            continue
        try:
            published=parsedate_to_datetime(date)
            if published.tzinfo is None:continue
            published=published.astimezone(timezone.utc)
        except (TypeError,ValueError,OverflowError):
            continue
        if not 0<=(now-published).total_seconds()<=AGE_SECONDS:continue
        seen.add(url)
        stories.append({"url":url,"title":title,
                        "published_utc":published.isoformat()})
    stories.sort(key=lambda x:x["published_utc"],reverse=True)
    return stories[:12]


def parse_article(raw):
    if len(raw)>MAX_ARTICLE:raise ValueError("article_too_large")
    reader=_Paragraphs()
    reader.feed(raw.decode("utf-8","replace"))
    paragraphs=[s for s in reader.paragraphs if len(s.split())>=12]
    body="\n".join(paragraphs)
    if len(body.split())<120 or len(paragraphs)<3:
        raise ValueError("insufficient_real_article_body")
    return paragraphs


def _topic(text):
    words=text.lower()
    if re.search(r"\b(gold|silver|bullion|central bank gold)\b",words):
        return "GOLD"
    if re.search(r"\b(oil|crude|opec|brent|diesel|energy)\b",words):
        return "OIL"
    if re.search(r"\b(fed|fomc|interest rates?|inflation|monetary|yield|bond)\b",words):
        return "RATES"
    if re.search(r"\b(bitcoin|crypto)\b",words):
        return "CRYPTO"
    return "MACRO_MARKET"


def interpret_story(story,paragraphs,fetched):
    """Ground text in article paragraphs. No invented observed price target."""
    if not paragraphs or sum(len(p.split()) for p in paragraphs)<120:
        raise ValueError("missing_full_article")
    body="\n".join(paragraphs)
    topic=_topic(story["title"]+" "+body[:2000])
    # Intro from ACTUAL body, never the RSS title as a substituted summary.
    informative=[p for p in paragraphs if len(p.split())>=17]
    if len(informative)<2:
        raise ValueError("insufficient_article_explanation")
    facts=" ".join(informative[:2])
    digest=sha256(body.encode()).hexdigest()
    mechanisms={
        "GOLD":"Permintaan emas atau perubahan suku bunga riil bisa menggeser bias XAUUSD; kenaikan dolar/yield dapat melawan dampaknya.",
        "OIL":"Perubahan pasokan dan risiko geopolitik memengaruhi premium harga minyak; permintaan dan realisasi kebijakan harus diperiksa.",
        "RATES":"Perubahan prospek suku bunga bisa mengubah yield dan selisih kurs; reaksinya perlu dikonfirmasi oleh data dan harga.",
        "CRYPTO":"Likuiditas dan selera risiko dapat memengaruhi aset kripto; korelasi dengan USD/ekuitas tidak stabil.",
        "MACRO_MARKET":"Dampak terhadap instrumen tertentu belum dapat ditentukan tanpa mekanisme kausal dan konfirmasi data lain.",
    }
    return {
        "source":"CNBC",
        "url":story["url"],
        "published_utc":story["published_utc"],
        "fetched_utc":fetched.isoformat(),
        "topic":topic,
        "inti_berdasarkan_isi":facts[:490],
        "arah_kebijakan":"BELUM_DIVERIFIKASI_DARI_SUMBER_KEBIJAKAN_PRIMER",
        "mekanisme_dampak_bersyarat":mechanisms[topic],
        "bias_harga_terverifikasi":"UNCERTAIN",
        "isi_artikel_dibaca":True,
        "jumlah_kata":len(body.split()),
        "sha256_isi":digest,
        "sumber_sekunder_bukan_izin_entry":True,
    }


def _schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS contextual_market_rss(
        id INTEGER PRIMARY KEY, fetched TEXT NOT NULL, rows_json TEXT NOT NULL,
        status TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS contextual_market_articles(
        url TEXT PRIMARY KEY,published TEXT NOT NULL,body TEXT NOT NULL,
        fetched TEXT NOT NULL,sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS contextual_market_article_failures(
        url TEXT PRIMARY KEY,attempted TEXT NOT NULL,reason TEXT NOT NULL)""")
    db.commit()


def collect_market_articles(db,now):
    """One RSS every 30m, <=1 previously-unread article per 5m cycle."""
    _schema(db)
    status=[]
    row=db.execute("""SELECT fetched,rows_json,status
        FROM contextual_market_rss ORDER BY id DESC LIMIT 1""").fetchone()
    if row and (now-datetime.fromisoformat(row[0])).total_seconds()<TTL_SECONDS:
        stories=json.loads(row[1]); status.append("rss_cached")
    else:
        try:
            stories=parse_feed(_fetch(FEED,MAX_FEED),now)
            fetched_status="OK"
        except Exception as error:
            stories=[]
            fetched_status=type(error).__name__
            status.append("rss_unavailable:"+fetched_status)
        with db:
            db.execute("INSERT INTO contextual_market_rss(fetched,rows_json,status) VALUES(?,?,?)",
                       (now.isoformat(),json.dumps(stories),fetched_status))
        # Prune repetitive feed fetch rows, preserving latest 48 snapshots.
        with db:
            db.execute("""DELETE FROM contextual_market_rss WHERE id NOT IN(
                SELECT id FROM contextual_market_rss ORDER BY id DESC LIMIT 48)""")
    # Old cached RSS snapshots may predate the relevance filter.
    # Never download a cached off-topic world headline either.
    stories=[s for s in stories if market_headline_relevant(s.get("title",""))]
    for story in stories[:8]:
        row=db.execute("SELECT 1 FROM contextual_market_articles WHERE url=?",
                       (story["url"],)).fetchone()
        if row:continue
        failure=db.execute(
            "SELECT attempted FROM contextual_market_article_failures WHERE url=?",
            (story["url"],)).fetchone()
        if failure and (now-datetime.fromisoformat(failure[0])).total_seconds()<3600:
            continue
        try:
            paragraphs=parse_article(_fetch(story["url"],MAX_ARTICLE))
            body="\n".join(paragraphs)
            with db:
                db.execute("INSERT OR IGNORE INTO contextual_market_articles VALUES(?,?,?,?,?)",
                    (story["url"],story["published_utc"],body,now.isoformat(),
                     sha256(body.encode()).hexdigest()))
            status.append("full_media_article_read")
        except Exception as e:
            with db:
                db.execute("INSERT OR REPLACE INTO contextual_market_article_failures VALUES(?,?,?)",
                           (story["url"],now.isoformat(),type(e).__name__))
            status.append("full_media_article_failed:"+type(e).__name__)
        break
    output=[]
    for url,published,body,fetched,digest in db.execute(
        """SELECT url,published,body,fetched,sha256 FROM contextual_market_articles
        ORDER BY published DESC LIMIT 12"""):
        if sha256(body.encode()).hexdigest()!=digest:continue
        try:
            p=datetime.fromisoformat(published)
            f=datetime.fromisoformat(fetched)
            if not (p<=f<=now and 0<=(now-p).total_seconds()<=AGE_SECONDS):
                continue
            story=next((x for x in stories if x["url"]==url),None)
            if story is None or not market_headline_relevant(story["title"]):
                continue
            # A revised RSS timestamp must not relabel an older cached body.
            output.append(interpret_story({**story, 'published_utc':published},body.split("\n"),f))
        except (ValueError,TypeError,KeyError):
            continue
    return output,tuple(status)
