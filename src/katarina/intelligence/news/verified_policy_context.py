"""Read the official article BODY before describing economic policy.

Only source URLs from the existing Fed/ECB/BoE RSS registry are accepted.
This does not scrape a headline into a directional trading command.
No article/body => no verified policy claim; no LLM-generated facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit
import re
import ssl
import urllib.request

from katarina.intelligence.cognition.contextual_decision_intelligence import MacroEvidence
from katarina.intelligence.news.news_intelligence import NewsItem

HOSTS={
    "fed":("www.federalreserve.gov","federalreserve.gov"),
    "ecb":("www.ecb.europa.eu","ecb.europa.eu"),
    "boe":("www.bankofengland.co.uk","bankofengland.co.uk"),
}
SOURCE_EXPOSURE={"fed":"USD","ecb":"EUR","boe":"GBP"}
POLICY={
    "fed":"federal funds rate",
    "ecb":"key ecb interest rates",
    "boe":"bank rate",
}
MAX_BYTES=600_000
MIN_WORDS=95
FRESH_SECONDS=6*3600


class _Paragraphs(HTMLParser):
    """Parse published paragraph text, never embedded JS/JSON-LD."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth=0
        self.skip_depth=0
        self.capture=[]
        self.paragraphs=[]

    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript","header","footer","nav","aside","form"):
            self.skip_depth+=1
        if tag=="p":
            self.depth+=1
            self.capture.append([])

    def handle_data(self,data):
        if self.depth and not self.skip_depth and self.capture:
            self.capture[-1].append(data)

    def handle_endtag(self,tag):
        if tag=="p" and self.depth:
            words=" ".join(" ".join(self.capture.pop()).split())
            if len(words)>=25:
                self.paragraphs.append(words)
            self.depth-=1
        if tag in ("script","style","noscript","header","footer","nav","aside","form"):
            self.skip_depth=max(0,self.skip_depth-1)


def _host_ok(url,source):
    try:
        parsed=urlsplit(url)
        return (parsed.scheme=="https" and parsed.username is None
                and parsed.password is None and parsed.port in (None,443)
                and parsed.hostname in HOSTS[source])
    except (ValueError,KeyError):
        return False


def parse_full_article(raw,source):
    if source not in HOSTS or len(raw)>MAX_BYTES:
        raise ValueError("article_source_or_size_invalid")
    parser=_Paragraphs()
    parser.feed(raw.decode("utf-8","replace"))
    body="\n".join(parser.paragraphs)
    if len(body.split())<MIN_WORDS:
        raise ValueError("full_article_body_unavailable")
    return body


def fetch_official_article(url,source,timeout=10):
    if not _host_ok(url,source):
        raise ValueError("article_url_not_official")
    request=urllib.request.Request(url,headers={
        "User-Agent":"KatarinaReadOnlyResearch/1.0",
        "Accept":"text/html,application/xhtml+xml;q=0.8",
    })
    try:
        import certifi
        tls=ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        tls=ssl.create_default_context()
    with urllib.request.urlopen(request,timeout=timeout,context=tls) as res:
        final_url=res.geturl()
        if not _host_ok(final_url,source):
            raise ValueError("article_redirected_off_official_host")
        if res.status!=200 or "text/html" not in res.headers.get("Content-Type","").lower():
            raise ValueError("not_official_html_article")
        raw=res.read(MAX_BYTES+1)
    return parse_full_article(raw,source)


def _policy_signal(body,source):
    """A claim only when the same full-text sentence says a rate action.

    No rate mention / contradictory signals -> UNCERTAIN.
    There is no NLP confidence or prediction of broker P&L.
    """
    sentences=re.split(r"(?<=[.!?])\s+(?=[A-Z])",body)
    found=set()
    for sentence in sentences:
        s=" ".join(sentence.lower().split())
        if POLICY[source] not in s and not (
            source=="fed" and "target range" in s and "federal" in s
        ):
            continue
        if re.search(r"\b(decided|announced|voted|agreed|will)\b",s) is None:
            continue
        if re.search(r"\b(?:lower\w*|cut\w*|reduc\w*|decreas\w*)\b",s):
            found.add("EASING")
        if re.search(r"\b(?:rais\w*|increas\w*|hike\w*|lift\w*)\b",s):
            found.add("TIGHTENING")
        if re.search(r"\b(maintain|unchanged|hold|keep)\b",s):
            found.add("HOLD")
    if len(found)!=1:
        return "UNCERTAIN"
    return next(iter(found))


def instrument_currencies(symbol):
    base=symbol.upper().split(".")[0]
    for prefix in ("XAUUSD","XAGUSD","BTCUSD","ETHUSD","NAS100","US100","US30","XTIUSD","USOIL"):
        if base.startswith(prefix):
            return ("USD",)
    if len(base)>=6 and base[:6].isalpha():
        return (base[:3],base[3:6])
    return ()


def market_mechanism(symbol,source,policy):
    curr=SOURCE_EXPOSURE[source]
    base=symbol.upper().split(".")[0]
    currencies=instrument_currencies(symbol)
    if curr not in currencies or policy not in ("TIGHTENING","EASING"):
        return "UNCERTAIN","Kaitan kebijakan ke arah harga belum terbukti."
    # Hypothesized immediate rate differential channel, not a forecast.
    relative="BUY" if policy=="TIGHTENING" else "SELL"
    if base.startswith(("XAUUSD","XAGUSD")) and source=="fed":
        side="SELL" if policy=="TIGHTENING" else "BUY"
        mechanism=("Hipotesis: suku bunga/imbal hasil USD lebih tinggi dapat menekan emas; "
                   "sentimen risiko, inflasi dan real yield bisa membalik arah.")
    elif base.startswith(("NAS100","US100","US30","USOIL","XTIUSD","BTCUSD")):
        return "UNCERTAIN","Arah indeks/komoditas juga bergantung laba, risiko dan suplai; tidak ada inferensi harga tunggal."
    elif len(base)>=6 and base[:3]==curr:
        side=relative
        mechanism="Hipotesis diferensial suku bunga mendukung mata uang dasar; harga dapat bereaksi sebaliknya."
    elif len(base)>=6 and base[3:6]==curr:
        side="SELL" if relative=="BUY" else "BUY"
        mechanism="Hipotesis diferensial suku bunga mendukung mata uang kuotasi; reaksi pasar tidak terjamin."
    else:
        return "UNCERTAIN","Dampak tidak langsung belum bisa disimpulkan."
    return side,mechanism


@dataclass(frozen=True)
class ReadArticle:
    source_id:str
    url:str
    title:str
    published_at_utc:datetime
    observed_at_utc:datetime
    body:str
    sha256:str


def evidence_from_article(article,symbol,now):
    from hashlib import sha256
    source=article.source_id
    if not _host_ok(article.url,source):
        raise ValueError("unverified_official_origin")
    p=article.published_at_utc
    o=article.observed_at_utc
    if p.tzinfo is None or o.tzinfo is None or now.tzinfo is None:
        raise ValueError("article_missing_timezone")
    if not (p<=o<=now and 0<=(now-p).total_seconds()<=FRESH_SECONDS):
        raise ValueError("article_not_known_by_decision_time")
    if len(article.body.split())<MIN_WORDS or sha256(article.body.encode()).hexdigest()!=article.sha256:
        raise ValueError("article_body_digest_or_length_invalid")
    if SOURCE_EXPOSURE[source] not in instrument_currencies(symbol):
        return None
    policy=_policy_signal(article.body,source)
    side,mechanism=market_mechanism(symbol,source,policy)
    # Only one explicit, single-direction full-article policy decision
    # is significant. Ambiguous news stays visible in the explanation.
    validated=policy in ("TIGHTENING","EASING","HOLD")
    return MacroEvidence(
        source_id=source,published_at_utc=p,observed_at_utc=o,
        affected_symbol=symbol,
        favored_side=side if validated else "UNCERTAIN",
        policy_direction=("Kebijakan suku bunga: "+policy+
                          " (klasifikasi kalimat isi resmi, bukan judul)"),
        transmission_mechanism=mechanism,
        source_verified=True,significant=validated and side in ("BUY","SELL"),
    )


def item_from_article(article,symbol,now):
    """Only a genuinely fetched body may be counted as NewsContext evidence."""
    evidence=evidence_from_article(article,symbol,now)
    if evidence is None:return None
    return NewsItem(
        source_id=article.source_id,published_utc=article.published_at_utc,
        title=article.title,tags=(SOURCE_EXPOSURE[article.source_id],),
        impact=2 if evidence.significant else 1,sentiment=0.0,
        url=article.url,
    )
