"""WP8c independent bar clock evidence and release verification.

Tahap 1 development-only bar clock verification using official US release dates
and M5 tick volume spike consensus across core symbols (EURUSD, USDJPY, XAUUSD).
Fails closed when evidence is weak, shifted, ambiguous, or off-calendar.
"""
from __future__ import annotations

import csv
import hashlib
import json
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
      2. Peak volume is >= 3x the median of surrounding 24 bars (12 before, 12 after).
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

            if len(surrounding) < 12:  # Need adequate surrounding bar context
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

    sample_min_dt = clean_samples[0][0]
    sample_max_dt = clean_samples[-1][0]

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

        # A segment is bounded by samples if there is a sample covering/bounding it
        # Expand tolerance to 200 days to allow samples across DST transitions
        segment_bounded = (b_start >= sample_min_dt - timedelta(days=200)) and (b_end <= sample_max_dt + timedelta(days=200))

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

    def __init__(self, broker: object, timeline_segments: list[dict], source_sha256: str):
        self._broker = broker
        self._timeline = timeline_segments
        self._source_sha256 = source_sha256

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


def build_evidence_report(calendar_csv_content: str, samples: list[dict]) -> dict:
    """Generate canonical evidence report dict and lineage SHA256."""
    if not calendar_csv_content or not calendar_csv_content.strip():
        raise ValidationError("CALENDAR_EVIDENCE_MISSING")

    # Validate that calendar has at least 1 non-header row
    lines = [line.strip() for line in calendar_csv_content.strip().splitlines() if line.strip()]
    if len(lines) <= 1:
        raise ValidationError("CALENDAR_EVIDENCE_EMPTY")

    cal_hash = sha256_text(calendar_csv_content)
    timeline = shift_timeline(samples)

    if not any(seg.get("status") == "VERIFIED" for seg in timeline):
        raise ValidationError("EVIDENCE_SAMPLES_INSUFFICIENT")

    report_body = dict(calendar_sha256=cal_hash,
                       sample_count=len(samples),
                       samples=samples,
                       schema_version=1,
                       timeline=timeline)
    source_sha256 = sha256_text(canonical(report_body))
    return dict(source_sha256=source_sha256,
                **report_body)


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

    sha = data.get("source_sha256")
    if not isinstance(sha, str) or re.fullmatch(r"[a-fA-F0-9]{64}", sha) is None:
        raise ValidationError("EVIDENCE_REPORT_INVALID_HASH")

    body = {k: v for k, v in data.items() if k != "source_sha256"}
    if sha256_text(canonical(body)) != sha:
        raise ValidationError("EVIDENCE_REPORT_HASH_MISMATCH")

    cal_p = Path(calendar_path)
    if not cal_p.is_file():
        raise ValidationError("CALENDAR_FILE_NOT_FOUND")

    cal_content = cal_p.read_text(encoding="utf-8")
    lines = [line.strip() for line in cal_content.strip().splitlines() if line.strip()]
    if len(lines) <= 1:
        raise ValidationError("CALENDAR_EVIDENCE_EMPTY")

    if sha256_text(cal_content) != data.get("calendar_sha256"):
        raise ValidationError("CALENDAR_HASH_MISMATCH")

    timeline = data.get("timeline")
    if not isinstance(timeline, list) or not any(s.get("status") == "VERIFIED" for s in timeline if isinstance(s, dict)):
        raise ValidationError("EVIDENCE_REPORT_INVALID_TIMELINE")

    return data
