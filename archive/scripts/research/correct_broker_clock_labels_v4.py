"""Correct report labels after observing server-time displacement.

This changes METADATA ONLY: no entry timing, P/L, signals, model or trade
selection is modified. Historical DST cannot be certified from one live read.
"""
import json
from pathlib import Path
p=Path(r"C:\KatarinaDev\decision-backtest-20261012\synchronous_multi_pair_daily_v4\FINAL_DAILY_RANK_55.json")
d=json.loads(p.read_text(encoding="utf-8"))
rules=d["rules_frozen_before_run"]
raw=rules.pop("checkpoints_utc_hours",None)
if raw is None:
    raw=rules.get("checkpoints_broker_encoded_hours")
assert raw==[6,12,18]
rules["checkpoints_broker_encoded_hours"]=raw
rules["day_reset"]="encoded broker clock date, not certified UTC or Indonesia civil date"
d["clock_diagnostic_2026_10_12"]={
    "source":"read-only paired live tick timestamp vs VPS UTC observation",
    "current_detected_broker_encoded_clock_offset_hours":3,
    "independent_recent_quotes":52,
    "historical_dst_or_offset_series_verified":False,
    "interpretation":"This corrects labels; P/L/backtest math is unchanged"}
notes=d["limitations"]
explanation=("06/12/18 sessions and day/month grouping are encoded broker-clock fields, NOT "
             "independently certified UTC. Current +3-hour difference cannot be applied to historical DST without verification.")
if explanation not in notes:notes.append(explanation)
p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
print("CLOCK_LABELS_CORRECTED",raw,"trades_unchanged",len(d["ranked_policy"]["trades"]))