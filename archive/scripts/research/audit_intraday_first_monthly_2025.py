"""Audit KATARINA 2025-26 intraday-first monthly projected cash accounting."""
import json,math,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
A=Path(r"C:\KatarinaDev\artifacts\historical-brain")
src=A/"katarina_intraday_first_monthly_projection_2025_2026.json"
r=json.loads(src.read_text(encoding="utf-8"))
assert r["research_only"] and not r["live_execution"]
assert r["risk_profile_unchanged"] and not r["scalping_enabled_in_projection"]
for entry in r["month_scenarios"]:
  months=entry["monthly"]
  assert len(months)==22
  totals=sum(x.get("net_usd",0.) for x in months.values())
  assert abs(totals-entry["gain_usd"])<.18,(entry["rr"],entry["scenario"],entry["starting_balance_usd"],totals,entry["gain_usd"])
  assert entry["trades_filled"]+entry["skipped_min_lot"]==129
  assert entry["reserve_usd"]==0.
  assert entry["max_observed_closed_balance_dd_fraction"]<.20
selected=[e for e in r["month_scenarios"] if e["starting_balance_usd"]==10000 and e["rr"]==2. and e["scenario"]=="base"][0]
months=selected["monthly"]
pos25=sum(x.get("net_usd",0)>0 for k,x in months.items() if k.startswith("2025"))
pos26=sum(x.get("net_usd",0)>0 for k,x in months.items() if k.startswith("2026"))
worst=sorted((x.get("net_usd",0.),k) for k,x in months.items())[:4]
best=sorted(((x.get("net_usd",0.),k) for k,x in months.items()),reverse=True)[:4]
audit={"kind":"KATARINA_INTRADAY_FIRST_MONTHLY_PROJECTION_AUDIT",
  "source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
  "cash_scenarios_verified":len(r["month_scenarios"]),
  "all_scenarios_month_cash_and_trade_counts_verified":True,
  "monthly_profit_positive_2025":pos25,"months_2025":12,
  "monthly_profit_positive_2026":pos26,"months_2026_partial":10,
  "biggest_wins":best,"worst_months":worst,
  "reserve_triggered":False,
  "total_gains_due_to_two_best_months_fraction":round(sum(x[0] for x in best[:2])/selected["gain_usd"],4),
  "positive_weeks_all_93_calendar_weeks":selected["positive_active_weeks"],
  "calendar_week_count":93,
  "proportion_all_weeks_positive":round(selected["positive_active_weeks"]/93,4),
  "live_authorized":False}
dest=A/"katarina_intraday_first_monthly_integrity_20261011.json"
dest.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
print(json.dumps(audit,indent=2))
