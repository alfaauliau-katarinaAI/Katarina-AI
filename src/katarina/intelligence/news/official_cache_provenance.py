"""Verify official/cache acquisition freshness independent of CACHED label.

CACHED only means a fetch was skipped. It does not mean the last fetch was
successful, fresh, complete or correct. This never invents macro direction.
"""
from __future__ import annotations

from datetime import datetime,timezone
from hashlib import sha256
import json

from katarina.intelligence.news.public_context import TTL, utc


def inspect_cached_official_sources(db, *, as_of_utc: datetime) -> dict:
    if not isinstance(as_of_utc,datetime) or as_of_utc.tzinfo is None:
        raise ValueError("timezone_aware_cache_clock_required")
    now=as_of_utc.astimezone(timezone.utc)
    rows={}
    for source in ("fed","ecb","boe","calendar"):
        item={"status":"SOURCE_UNAVAILABLE","fetched_age_seconds":None,
              "digest_ok":False,"coverage_ok":False,"fresh_and_valid":False}
        try:
            record=db.execute(
                """SELECT fetched,status,digest,raw,payload FROM snapshots
                   WHERE source=? ORDER BY id DESC LIMIT 1""",
                (source,)).fetchone()
            if record is None:
                rows[source]=item
                continue
            fetched, status, digest, raw, payload=record
            fetched_utc=utc(fetched)
            age=(now-fetched_utc).total_seconds()
            item["fetched_age_seconds"]=round(age,1)
            if age < 0:
                item["status"]="FUTURE_CACHE_RECEIPT"
            elif age > TTL[source]:
                item["status"]="STALE_CACHE_RECEIPT"
            elif status!="OK":
                item["status"]="LATEST_FETCH_NOT_OK"
            elif not isinstance(raw,bytes) or not raw or sha256(raw).hexdigest()!=digest:
                item["status"]="TAMPERED_OR_MISSING_RAW_DIGEST"
            else:
                item["digest_ok"]=True
                data=json.loads(payload)
                if not isinstance(data,dict):
                    item["status"]="MALFORMED_CACHE_PAYLOAD"
                elif source=="calendar":
                    lo=utc(data["coverage_from"]);hi=utc(data["coverage_to"])
                    item["coverage_ok"]=(
                        lo<=now<hi and lo < hi and
                        isinstance(data.get("events"),list) and
                        bool(data.get("coverage"))
                    )
                    item["status"]=("FRESH_VERIFIED_CACHE" if item["coverage_ok"]
                                    else "CALENDAR_OUTSIDE_COVERAGE")
                else:
                    item["coverage_ok"]=(
                        isinstance(data.get("items"),list)
                        and bool(data.get("items"))
                        and isinstance(data.get("coverage"),list)
                        and bool(data["coverage"])
                    )
                    item["status"]=("FRESH_VERIFIED_CACHE" if item["coverage_ok"]
                                    else "RSS_CACHE_PAYLOAD_INCOMPLETE")
        except (KeyError,ValueError,TypeError,OverflowError):
            item["status"]="UNVERIFIABLE_SOURCE_RECEIPT"
        item["fresh_and_valid"]=item["status"]=="FRESH_VERIFIED_CACHE"
        rows[source]=item
    return {
        "kind":"KATARINA_OFFICIAL_SOURCE_CACHE_INTEGRITY",
        "status":("ALL_FOUR_SOURCE_CACHES_VERIFIED"
                  if all(x["fresh_and_valid"] for x in rows.values())
                  else "SOURCE_CACHE_DEGRADED"),
        "sources":rows,
        "all_four_cache_digests_fresh":all(
            x["fresh_and_valid"] for x in rows.values()),
        "point_in_time_article_relevance_verified":False,
        "policy_inference_from_headlines_authorized":False,
        "live_execution_authorized":False,
    }
