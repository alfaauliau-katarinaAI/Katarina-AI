"""WP8c independent bar clock evidence and release verification.

Tahap 1 development-only bar clock verification using official US release dates
and M5 tick volume spike consensus across core symbols (EURUSD, USDJPY, XAUUSD).
Fails closed when evidence is weak, shifted, ambiguous, or off-calendar.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from katarina.intelligence.operations.data_health import _last_sunday, _nth_sunday
from katarina.research.validation import ValidationError, canonical, sha256_text

CORE_SYMBOLS = ("EURUSD", "USDJPY", "XAUUSD")
CANDIDATE_SHIFTS = range(-12, 15)
DEFAULT_CALENDAR_PATH = Path("config/research/us_release_calendar.csv")


def _utc_dt(val: str | datetime | int | float) -> datetime:
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, timezone.utc)
    if isinstance(val, str):
        text = val.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    raise ValidationError("INVALID_DATETIME_FORMAT")


def is_eu_dst(dt: datetime) -> bool:
    """True if dt falls during EU Summer Time (EEST, last Sun Mar 01:00 UTC to last Sun Oct 01:00 UTC)."""
    utc = _utc_dt(dt)
    year = utc.year
    start_date = _last_sunday(year, 3)
    end_date = _last_sunday(year, 10)
    start_dt = datetime(year, start_date.month, start_date.day, 1, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(year, end_date.month, end_date.day, 1, 0, 0, tzinfo=timezone.utc)
    return start_dt <= utc < end_dt


def is_us_dst(dt: datetime) -> bool:
    """True if dt falls during US Daylight Saving Time (EDT, 2nd Sun Mar 07:00 UTC to 1st Sun Nov 06:00 UTC)."""
    utc = _utc_dt(dt)
    year = utc.year
    start_date = _nth_sunday(year, 3, 2)
    end_date = _nth_sunday(year, 11, 1)
    start_dt = datetime(year, start_date.month, start_date.day, 7, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(year, end_date.month, end_date.day, 6, 0, 0, tzinfo=timezone.utc)
    return start_dt <= utc < end_dt


def _bar_time(bar: dict | object) -> datetime:
    if isinstance(bar, dict):
        t = bar.get("time_utc") if "time_utc" in bar else bar.get("time")
    else:
        t = getattr(bar, "time_utc", getattr(bar, "time", None))
    if t is None:
        raise ValidationError("BAR_TIME_MISSING")
    return _utc_dt(t)


def _bar_volume(bar: dict | object) -> int:
    if isinstance(bar, dict):
        vol = bar.get("tick_volume", bar.get("real_volume", bar.get("volume", 0)))
    else:
        vol = getattr(bar, "tick_volume", getattr(bar, "real_volume", getattr(bar, "volume", 0)))
    try:
        val = int(vol)
        if val < 0:
            raise ValueError
        return val
    except (TypeError, ValueError) as error:
        raise ValidationError("BAR_VOLUME_INVALID") from error


def release_shift(bars_by_symbol: dict, release_utc: str | datetime) -> int | None:
    """Test integer shifts -12..+14 against M5 volume spikes on known release minute.

    Requires:
      1. Peak tick volume in a +/- 4-hour window falls EXACTLY on the release minute.
      2. Peak volume is >= 3x the median of exactly 24 surrounding bars (12 before, 12 after);
         a release near the edge of the data, with fewer neighbours, is rejected.
      3. Consensus across >= 2 of EURUSD, USDJPY, XAUUSD with zero conflicts.

    Returns shift integer (-12..+14) if valid consensus is established, else None.
    """
    release_dt = _utc_dt(release_utc)
    if not isinstance(bars_by_symbol, dict):
        return None

    symbol_shifts = {}
    for symbol in CORE_SYMBOLS:
        bars = bars_by_symbol.get(symbol)
        if not bars or not isinstance(bars, (list, tuple)):
            continue

        try:
            parsed_bars = [(_bar_time(b), _bar_volume(b), b) for b in bars]
        except ValidationError:
            continue

        parsed_bars.sort(key=lambda x: x[0])
        valid_shifts_for_symbol = []

        for candidate_shift in CANDIDATE_SHIFTS:
            target_server_time = release_dt + timedelta(hours=candidate_shift)
            window_start = target_server_time - timedelta(hours=4)
            window_end = target_server_time + timedelta(hours=4)

            window_bars = [b for b in parsed_bars if window_start <= b[0] <= window_end]
            target_bar = next((b for b in window_bars if b[0] == target_server_time), None)
            if target_bar is None:
                continue

            target_vol = target_bar[1]
            if target_vol <= 0:
                continue

            # Check 1: Target bar must be the STRICT UNIQUE maximum volume in the +/- 4 hour window.
            if any(b[1] >= target_vol for b in window_bars if b[0] != target_server_time):
                continue

            # Check 2: Volume must be >= 3x median of 24 surrounding bars (12 before, 12 after).
            target_idx = parsed_bars.index(target_bar)
            bars_before = parsed_bars[max(0, target_idx - 12):target_idx]
            bars_after = parsed_bars[target_idx + 1:min(len(parsed_bars), target_idx + 13)]
            surrounding = bars_before + bars_after

            if len(bars_before) != 12 or len(bars_after) != 12:  # full 24-bar context or reject
                continue

            median_vol = statistics.median([b[1] for b in surrounding])
            if target_vol < 3 * max(median_vol, 1):
                continue

            valid_shifts_for_symbol.append(candidate_shift)

        if len(valid_shifts_for_symbol) == 1:
            symbol_shifts[symbol] = valid_shifts_for_symbol[0]
        else:
            symbol_shifts[symbol] = None

    valid_shifts = [s for s in symbol_shifts.values() if s is not None]
    if len(valid_shifts) >= 2 and len(set(valid_shifts)) == 1:
        return valid_shifts[0]

    return None


def _dst_transition_dates(start_year: int, end_year: int) -> list[datetime]:
    dates = []
    for y in range(start_year, end_year + 1):
        for d in (_last_sunday(y, 3), _last_sunday(y, 10), _nth_sunday(y, 3, 2), _nth_sunday(y, 11, 1)):
            dates.append(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))
    return sorted(set(dates))


def shift_timeline(samples: list[dict]) -> list[dict]:
    """Build timeline segments from verified release shift samples.

    Shift changes must align with official EU/US DST transition boundaries.
    Ranges where rules conflict, evidence is missing, or unverified by bounding samples
    return NO_EVIDENCE (fail closed).
    """
    if not isinstance(samples, (list, tuple)) or not samples:
        return [dict(start_utc="2020-01-01T00:00:00+00:00",
                     end_utc="2026-10-13T00:00:00+00:00",
                     shift_hours=None, status="NO_EVIDENCE")]

    clean_samples = []
    for s in samples:
        if isinstance(s, dict) and "release_utc" in s and "shift_hours" in s:
            sh = s["shift_hours"]
            if type(sh) is int and -12 <= sh <= 14:
                clean_samples.append((_utc_dt(s["release_utc"]), sh))

    clean_samples.sort(key=lambda x: x[0])
    if not clean_samples:
        return [dict(start_utc="2020-01-01T00:00:00+00:00",
                     end_utc="2026-10-13T00:00:00+00:00",
                     shift_hours=None, status="NO_EVIDENCE")]

    # Check for off-calendar shift changes between consecutive samples
    all_transitions = _dst_transition_dates(2020, 2027)
    for i in range(len(clean_samples) - 1):
        t1, s1 = clean_samples[i]
        t2, s2 = clean_samples[i + 1]
        if s1 != s2:
            trans_between = [tr for tr in all_transitions if t1 <= tr <= t2]
            if not trans_between:
                # Shift change occurred off-calendar without DST boundary! Fail closed.
                return [dict(start_utc="2020-01-01T00:00:00+00:00",
                             end_utc="2026-10-13T00:00:00+00:00",
                             shift_hours=None, status="NO_EVIDENCE")]

    # Find candidate rules matching ALL samples
    matching_rules = []
    for base in CANDIDATE_SHIFTS:
        # Candidate Rule 1: EU DST schema
        def eu_rule(dt, b=base):
            return b + 1 if is_eu_dst(dt) else b

        # Candidate Rule 2: US DST schema
        def us_rule(dt, b=base):
            return b + 1 if is_us_dst(dt) else b

        # Candidate Rule 3: Fixed schema
        def fixed_rule(dt, b=base):
            return b

        for name, fn in (("EU_DST", eu_rule), ("US_DST", us_rule), ("FIXED", fixed_rule)):
            if all(fn(t) == s for t, s in clean_samples):
                matching_rules.append((name, fn))

    if not matching_rules:
        return [dict(start_utc="2020-01-01T00:00:00+00:00",
                     end_utc="2026-10-13T00:00:00+00:00",
                     shift_hours=None, status="NO_EVIDENCE")]

    # Build timeline segments along DST boundaries
    bounds = [datetime(2020, 1, 1, tzinfo=timezone.utc)] + all_transitions + [datetime(2026, 10, 13, tzinfo=timezone.utc)]
    bounds = sorted(set(bounds))

    raw_segments = []
    for i in range(len(bounds) - 1):
        b_start = bounds[i]
        b_end = bounds[i + 1]
        mid = b_start + (b_end - b_start) / 2

        # Fail closed: a DST segment is verified only by a sample measured inside it.
        # No extrapolation into neighbouring segments (no +/-N day tolerance).
        segment_bounded = any(b_start <= t < b_end for t, _ in clean_samples)

        shifts_at_mid = {fn(mid) for _, fn in matching_rules}
        if len(shifts_at_mid) == 1 and segment_bounded:
            val = next(iter(shifts_at_mid))
            raw_segments.append(dict(start_utc=b_start.isoformat(),
                                     end_utc=b_end.isoformat(),
                                     shift_hours=val,
                                     status="VERIFIED"))
        else:
            raw_segments.append(dict(start_utc=b_start.isoformat(),
                                     end_utc=b_end.isoformat(),
                                     shift_hours=None,
                                     status="NO_EVIDENCE"))

    # Merge contiguous segments with identical status and shift_hours
    merged = []
    for seg in raw_segments:
        if not merged:
            merged.append(seg)
        else:
            prev = merged[-1]
            if prev["status"] == seg["status"] and prev["shift_hours"] == seg["shift_hours"]:
                prev["end_utc"] = seg["end_utc"]
            else:
                merged.append(seg)

    return merged


class BarClockEvidenceAdapter:
    """Broker wrapper introducing verified_historical_bar_shift."""

    def __init__(self, broker: object, report: dict):
        # Only a report whose timeline is recomputed from its own samples and whose
        # hash matches is accepted; an arbitrary hand-written timeline is rejected.
        verified = verify_report_body(report)
        self._broker = broker
        self._timeline = verified["timeline"]
        self._source_sha256 = verified["source_sha256"]

    def verified_historical_bar_shift(self, symbol: str, timeframe: str, start: datetime | str, end: datetime | str) -> dict:
        start_dt = _utc_dt(start)
        end_dt = _utc_dt(end)

        matched_shift = None
        for seg in self._timeline:
            s_start = _utc_dt(seg["start_utc"])
            s_end = _utc_dt(seg["end_utc"])
            if s_start <= start_dt and end_dt <= s_end:
                if seg.get("status") == "VERIFIED" and seg.get("shift_hours") is not None:
                    matched_shift = seg["shift_hours"]
                    break

        if matched_shift is not None:
            return dict(verified=True,
                        shift_hours=matched_shift,
                        time_basis="INDEPENDENT_UTC",
                        source_sha256=self._source_sha256)

        return dict(verified=False,
                    shift_hours=None,
                    time_basis="UNVERIFIED",
                    source_sha256=self._source_sha256,
                    reason="BATCH_CROSSES_SEGMENTS_OR_UNVERIFIED")

    def __getattr__(self, item: str):
        return getattr(self._broker, item)


HEX64 = re.compile(r"[a-f0-9]{64}")


def _calendar_releases(calendar_csv_content: str) -> set[datetime]:
    if not calendar_csv_content or not calendar_csv_content.strip():
        raise ValidationError("CALENDAR_EVIDENCE_MISSING")
    rows = list(csv.DictReader(calendar_csv_content.strip().splitlines()))
    if not rows:
        raise ValidationError("CALENDAR_EVIDENCE_EMPTY")
    releases = set()
    for row in rows:
        try:
            releases.add(_utc_dt(row["release_utc"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError("CALENDAR_ROW_INVALID") from error
        if not str(row.get("source_url", "")).startswith("https://"):
            raise ValidationError("CALENDAR_SOURCE_MISSING")
    return releases


def _check_samples(samples, releases: set[datetime]) -> None:
    if not isinstance(samples, list) or not samples:
        raise ValidationError("EVIDENCE_SAMPLES_INSUFFICIENT")
    seen = set()
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != {"release_utc", "shift_hours", "bars_sha256"}:
            raise ValidationError("EVIDENCE_SAMPLE_INVALID")
        sh = sample["shift_hours"]
        if type(sh) is not int or not -12 <= sh <= 14:
            raise ValidationError("EVIDENCE_SAMPLE_INVALID")
        if not isinstance(sample["bars_sha256"], str) or HEX64.fullmatch(sample["bars_sha256"]) is None:
            raise ValidationError("EVIDENCE_SAMPLE_LINEAGE_MISSING")
        when = _utc_dt(sample["release_utc"])
        if when not in releases:
            raise ValidationError("EVIDENCE_SAMPLE_OFF_CALENDAR")
        if when in seen:
            raise ValidationError("EVIDENCE_SAMPLE_DUPLICATE")
        seen.add(when)


def verify_report_body(report: dict) -> dict:
    """Recompute hash and timeline from samples; reject anything that differs."""
    if not isinstance(report, dict):
        raise ValidationError("EVIDENCE_REPORT_INVALID")
    sha = report.get("source_sha256")
    if not isinstance(sha, str) or HEX64.fullmatch(sha) is None:
        raise ValidationError("EVIDENCE_REPORT_INVALID_HASH")
    body = {k: v for k, v in report.items() if k != "source_sha256"}
    if sha256_text(canonical(body)) != sha:
        raise ValidationError("EVIDENCE_REPORT_HASH_MISMATCH")
    if body.get("schema_version") != 1 or body.get("sample_count") != len(body.get("samples") or []):
        raise ValidationError("EVIDENCE_REPORT_INVALID")
    if body.get("timeline") != shift_timeline(body.get("samples")):
        raise ValidationError("EVIDENCE_REPORT_TIMELINE_NOT_REPRODUCIBLE")
    if not any(seg.get("status") == "VERIFIED" for seg in body["timeline"]):
        raise ValidationError("EVIDENCE_SAMPLES_INSUFFICIENT")
    return report


def build_evidence_report(
    calendar_csv_content: str,
    samples: list[dict],
    *,
    rejected: list[dict] | None = None,
    provenance: dict | None = None,
) -> dict:
    """Generate canonical evidence report dict and lineage SHA256."""
    _check_samples(samples, _calendar_releases(calendar_csv_content))
    cal_hash = sha256_text(calendar_csv_content)
    timeline = shift_timeline(samples)

    if not any(seg.get("status") == "VERIFIED" for seg in timeline):
        raise ValidationError("EVIDENCE_SAMPLES_INSUFFICIENT")

    report_body = dict(calendar_sha256=cal_hash,
                       sample_count=len(samples),
                       samples=samples,
                       schema_version=1,
                       timeline=timeline)
    if rejected is not None:
        report_body["rejected"] = rejected
    if provenance is not None:
        report_body["provenance"] = provenance

    source_sha256 = sha256_text(canonical(report_body))
    return dict(source_sha256=source_sha256,
                **report_body)


def _normalize_raw_bar(bar: dict | object) -> dict:
    if isinstance(bar, dict):
        t = bar.get("time_utc") if "time_utc" in bar else bar.get("time")
        if any(k not in bar for k in ("open", "high", "low", "close")):
            raise ValidationError("BAR_OHLC_MISSING")
        op = bar["open"]
        hi = bar["high"]
        lo = bar["low"]
        cl = bar["close"]
        vol = bar.get("tick_volume", bar.get("real_volume", bar.get("volume")))
        sp = bar.get("spread", 0)
        rvol = bar.get("real_volume", 0)
    else:
        t = getattr(bar, "time_utc", getattr(bar, "time", None))
        if not all(hasattr(bar, k) for k in ("open", "high", "low", "close")):
            raise ValidationError("BAR_OHLC_MISSING")
        op = getattr(bar, "open")
        hi = getattr(bar, "high")
        lo = getattr(bar, "low")
        cl = getattr(bar, "close")
        vol = getattr(bar, "tick_volume", getattr(bar, "real_volume", getattr(bar, "volume", None)))
        sp = getattr(bar, "spread", 0)
        rvol = getattr(bar, "real_volume", 0)

    if t is None:
        raise ValidationError("BAR_TIME_MISSING")
    if vol is None:
        raise ValidationError("BAR_VOLUME_MISSING")

    try:
        op = float(op)
        hi = float(hi)
        lo = float(lo)
        cl = float(cl)
        vol = int(vol)
        sp = int(sp)
        rvol = int(rvol)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValidationError("BAR_VALUES_INVALID") from error

    prices = (op, hi, lo, cl)
    if not all(math.isfinite(x) and x > 0 for x in prices):
        raise ValidationError("BAR_PRICES_NON_FINITE_OR_NON_POSITIVE")
    if lo > min(op, cl) or hi < max(op, cl) or hi < lo:
        raise ValidationError("BAR_OHLC_GEOMETRY_INVALID")
    if vol < 0 or sp < 0 or rvol < 0:
        raise ValidationError("BAR_METRICS_NEGATIVE")

    if isinstance(t, datetime):
        t_val = _utc_dt(t).isoformat()
    elif isinstance(t, (int, float)):
        t_val = int(t)
    else:
        t_val = str(t)

    return {
        "close": cl,
        "high": hi,
        "low": lo,
        "open": op,
        "real_volume": rvol,
        "spread": sp,
        "tick_volume": vol,
        "time": t_val,
    }


def collect_release_samples(
    broker: object,
    calendar_rows: list[dict] | str | iter,
    *,
    symbols: tuple[str, ...] = CORE_SYMBOLS,
    timeframe: str = "M5",
) -> tuple[list[dict], list[dict]]:
    """Collect release shift samples and rejected releases across calendar releases.

    Queries M5 bars around each release utc (-17h..+19h to cover -12..+14 candidate shifts
    ±4 hours + 12 context bars) for given symbols.
    Computes deterministic bars_sha256 hash across canonical raw bar representations.
    Fails closed: releases without consensus are recorded in rejected with a reason code.
    """
    if isinstance(calendar_rows, str):
        if not calendar_rows.strip():
            rows = []
        else:
            rows = list(csv.DictReader(calendar_rows.strip().splitlines()))
    elif isinstance(calendar_rows, (list, tuple)):
        rows = calendar_rows
    else:
        rows = list(calendar_rows)

    frame = getattr(broker, "TIMEFRAME_" + timeframe, timeframe)
    sorted_symbols = tuple(sorted(symbols))

    samples = []
    rejected = []

    for row in rows:
        if isinstance(row, dict):
            release_val = row.get("release_utc")
        else:
            release_val = row

        if not release_val:
            rejected.append({"release_utc": None, "reason": "MISSING_RELEASE_UTC", "bars_sha256": None})
            continue

        try:
            release_dt = _utc_dt(release_val)
        except ValidationError:
            rejected.append({"release_utc": str(release_val), "reason": "INVALID_RELEASE_DATETIME", "bars_sha256": None})
            continue

        release_utc_iso = release_dt.isoformat()

        # Window covers candidate shift -12 (-12-4-1 = -17h) to +14 (+14+4+1 = +19h)
        query_start = release_dt - timedelta(hours=17)
        query_end = release_dt + timedelta(hours=19)

        bars_by_symbol = {}
        canonical_raw_by_symbol = {}
        all_empty = True
        malformed_found = False

        for symbol in sorted_symbols:
            try:
                raw_rates = broker.copy_rates_range(symbol, frame, query_start, query_end)
            except Exception:
                raw_rates = None

            if raw_rates is None or len(raw_rates) == 0:
                bars_by_symbol[symbol] = []
                canonical_raw_by_symbol[symbol] = []
            else:
                all_empty = False
                try:
                    norm_bars = [_normalize_raw_bar(b) for b in raw_rates]
                    norm_bars.sort(key=lambda x: str(x["time"]))
                    canonical_raw_by_symbol[symbol] = norm_bars
                    bars_by_symbol[symbol] = norm_bars
                except ValidationError:
                    malformed_found = True
                    bars_by_symbol[symbol] = []
                    canonical_raw_by_symbol[symbol] = []

        bars_sha256 = sha256_text(canonical(canonical_raw_by_symbol))

        if all_empty:
            rejected.append({"release_utc": release_utc_iso, "reason": "BROKER_BARS_UNAVAILABLE", "bars_sha256": bars_sha256})
            continue

        shift = release_shift(bars_by_symbol, release_dt)

        if shift is not None and type(shift) is int and -12 <= shift <= 14:
            samples.append({
                "release_utc": release_utc_iso,
                "shift_hours": shift,
                "bars_sha256": bars_sha256,
            })
        else:
            reason = "MALFORMED_BAR_DATA" if malformed_found else "NO_CONSENSUS_OR_WEAK_EVIDENCE"
            rejected.append({
                "release_utc": release_utc_iso,
                "reason": reason,
                "bars_sha256": bars_sha256,
            })

    return samples, rejected


def load_evidence_report(path: str | Path, calendar_path: str | Path = DEFAULT_CALENDAR_PATH) -> dict:
    """Load and validate evidence report JSON file against calendar CSV content."""
    p = Path(path)
    if not p.is_file():
        raise ValidationError("EVIDENCE_REPORT_NOT_FOUND")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as error:
        raise ValidationError("EVIDENCE_REPORT_INVALID_JSON") from error

    if not isinstance(data, dict):
        raise ValidationError("EVIDENCE_REPORT_INVALID")

    cal_p = Path(calendar_path)
    if not cal_p.is_file():
        raise ValidationError("CALENDAR_FILE_NOT_FOUND")
    cal_content = cal_p.read_text(encoding="utf-8")
    releases = _calendar_releases(cal_content)
    verify_report_body(data)
    if sha256_text(cal_content) != data.get("calendar_sha256"):
        raise ValidationError("CALENDAR_HASH_MISMATCH")
    _check_samples(data["samples"], releases)
    return data
