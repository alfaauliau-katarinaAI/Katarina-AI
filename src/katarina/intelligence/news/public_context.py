"""Point-in-time public context. Text is evidence, never executable instructions."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
import sqlite3
import ssl
import urllib.request
import xml.etree.ElementTree as ET

UTC = timezone.utc
SOURCES = {
    "fed": ("https://www.federalreserve.gov/feeds/press_all.xml", ("USD",)),
    "ecb": ("https://www.ecb.europa.eu/rss/press.html", ("EUR",)),
    "boe": ("https://www.bankofengland.co.uk/rss/news", ("GBP",)),
    "calendar": ("https://nfs.faireconomy.media/ff_calendar_thisweek.json", ()),
}
CALENDAR_CURRENCIES = ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY")
TTL = {"calendar": 3600, "fed": 1800, "ecb": 1800, "boe": 1800}


def utc(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result.astimezone(UTC)


def parse_news(raw, source, fetched):
    root = ET.fromstring(raw)
    items, seen = [], set()
    for item in root.findall("./channel/item"):
        title = " ".join((item.findtext("title") or "").split())
        date = item.findtext("pubDate")
        if not title or not date:
            continue
        published = parsedate_to_datetime(date)
        if published.tzinfo is None:
            raise ValueError("RSS publication timezone missing")
        published = published.astimezone(UTC)
        # Future headlines must not become known evidence.
        if published > fetched:
            continue
        key = sha256((title.casefold() + published.isoformat()).encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        items.append(dict(id=key, title=title, url=item.findtext("link") or "",
                          published_utc=published.isoformat(),
                          known_at_utc=fetched.isoformat(), currencies=SOURCES[source][1]))
    if not root.findall("./channel/item"):
        raise ValueError("unrecognized or empty RSS feed")
    return dict(items=items, coverage=SOURCES[source][1])


def parse_calendar(raw, fetched):
    data = json.loads(raw)
    if not isinstance(data, list) or not data:
        raise ValueError("calendar empty or malformed")
    events, weeks = [], set()
    impacts = {"Low": 1, "Medium": 2, "High": 3, "Holiday": 0}
    for row in data:
        original = datetime.fromisoformat(row["date"])
        if original.tzinfo is None or row["impact"] not in impacts:
            raise ValueError("unknown calendar time/impact")
        # Weekly export is Sunday through Saturday, in its supplied timezone.
        sunday = original.date() - timedelta(days=(original.weekday() + 1) % 7)
        weeks.add((sunday.isoformat(), original.utcoffset().total_seconds()))
        events.append(dict(name=row["title"], currency=row["country"].upper(),
                           event_utc=original.astimezone(UTC).isoformat(),
                           impact=impacts[row["impact"]],
                           forecast=row.get("forecast") or None,
                           previous=row.get("previous") or None,
                           actual=row.get("actual") or None,
                           known_at_utc=fetched.isoformat()))
    if len(weeks) != 1:
        raise ValueError("inconsistent calendar coverage")
    week, offset = next(iter(weeks))
    start = datetime.fromisoformat(week).replace(tzinfo=timezone(timedelta(seconds=offset)))
    return dict(events=events, coverage=CALENDAR_CURRENCIES,
                coverage_from=start.astimezone(UTC).isoformat(),
                coverage_to=(start + timedelta(days=7)).astimezone(UTC).isoformat(),
                actual_available=any(e["actual"] is not None for e in events))


class ContextStore:
    """Append-only retrieval versions preserve first availability, including revisions."""
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("""CREATE TABLE IF NOT EXISTS snapshots(
            id INTEGER PRIMARY KEY, source TEXT, fetched TEXT, status TEXT,
            digest TEXT, raw BLOB, payload TEXT, error TEXT)""")
        self.db.commit()

    def record(self, source, fetched, raw=b"", error=""):
        payload = {}
        status = "ERROR" if error else "OK"
        if not error:
            try:
                payload = (parse_calendar(raw, fetched) if source == "calendar"
                           else parse_news(raw, source, fetched))
            except (ValueError, KeyError, TypeError, ET.ParseError) as exc:
                status, error = "ERROR", type(exc).__name__
        self.db.execute("INSERT INTO snapshots VALUES(NULL,?,?,?,?,?,?,?)",
                        (source, fetched.isoformat(), status, sha256(raw).hexdigest(),
                         raw, json.dumps(payload), error))
        self.db.commit()
        return status

    def latest(self, source, now):
        row = self.db.execute(
            "SELECT fetched,status,digest,payload,error FROM snapshots WHERE source=? AND fetched<=? ORDER BY fetched DESC,id DESC LIMIT 1",
            (source, now.astimezone(UTC).isoformat())).fetchone()
        if not row:
            return dict(source=source, ready=False, reason="missing")
        fetched, status, digest, payload, error = row
        age = (now - utc(fetched)).total_seconds()
        return dict(source=source, fetched_utc=fetched, sha256=digest,
                    ready=status == "OK" and 0 <= age <= TTL[source],
                    reason=error or ("fresh" if age <= TTL[source] else "stale"),
                    payload=json.loads(payload))

    def refresh(self, now, force=False):
        outcomes = {}
        for name, (url, _) in SOURCES.items():
            # Errors also back off; failed fetches must never mark cached data fresh.
            recent = self.db.execute("SELECT fetched FROM snapshots WHERE source=? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
            if not force and recent and 0 <= (now - utc(recent[0])).total_seconds() < 900:
                outcomes[name] = "CACHED"
                continue
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "KatarinaResearch/1.0"})
                try:
                    import certifi
                    tls = ssl.create_default_context(cafile=certifi.where())
                except ImportError:
                    tls = ssl.create_default_context()
                with urllib.request.urlopen(request, timeout=15, context=tls) as response:
                    raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ValueError("feed too large")
                outcomes[name] = self.record(name, datetime.now(UTC), raw)
            except Exception as exc:
                # Avoid logging credentials or arbitrary server response text.
                outcomes[name] = self.record(name, datetime.now(UTC), error=type(exc).__name__)
        return outcomes

    def assess(self, currencies, now):
        required = set(currencies)
        reasons, matched, headlines = [], [], []
        calendar = self.latest("calendar", now)
        body = calendar.get("payload", {})
        if not calendar["ready"]:
            reasons.append("calendar_unavailable")
        elif not (utc(body["coverage_from"]) <= now and now + timedelta(minutes=30) < utc(body["coverage_to"])):
            reasons.append("calendar_outside_coverage")
        elif not required.issubset(set(body["coverage"])):
            reasons.append("calendar_currency_uncovered")
        else:
            for event in body["events"]:
                minutes = (utc(event["event_utc"]) - now).total_seconds() / 60
                if event["impact"] >= 2 and (event["currency"] in required or event["currency"] == "ALL") and -15 <= minutes <= 30:
                    matched.append(event["name"])
            if matched:
                reasons.append("economic_blackout")
        news_covered = set()
        for source in ("fed", "ecb", "boe"):
            snapshot = self.latest(source, now)
            if not snapshot["ready"]:
                continue
            news_covered.update(snapshot["payload"]["coverage"])
            for item in snapshot["payload"]["items"]:
                if set(item["currencies"]) & required and 0 <= (now - utc(item["published_utc"])).total_seconds() <= 86400:
                    headlines.append(dict(source=source, **item))
                    if (now - utc(item["published_utc"])).total_seconds() <= 900:
                        reasons.append("recent_official_release")
        if not required.issubset(news_covered):
            reasons.append("news_currency_uncovered")
        return dict(ready=not reasons, reasons=sorted(set(reasons)),
                    blackout_events=matched, headlines=headlines,
                    actual_available=body.get("actual_available", False),
                    sentiment=None, directional_inference="not_calibrated")
