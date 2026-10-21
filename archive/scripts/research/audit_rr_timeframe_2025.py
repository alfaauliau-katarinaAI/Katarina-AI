"""Read-only validation of frozen 2025–2026 KATARINA optimization artifacts."""
import json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
A=Path(r"C:\KatarinaDev\artifacts\historical-brain")
files={
 "baseline":"katarina_rr_grid_from_2025_2026.json",
 "kfei":"katarina_kfei_tf_rr_2025_2026.json",
 "xau_micro":"katarina_xau_tick_m1_m4_rr_from_2025.json"}
inputs={k:json.loads((A/v).read_text(encoding="utf-8")) for k,v in files.items()}
r=inputs["baseline"];f=inputs["kfei"];m=inputs["xau_micro"]
assert r["live_execution_enabled"] is False
assert f["policy"]["live_orders"] is False
assert m["live_execution_enabled"] is False
assert len(r["symbols"])==len(f["symbols"])==7
assert len(m["results"])==4
tf=set(f["timeframes"])
assert len(tf)==21
assert all(len(x["results"])==21 for x in f["symbols"])
total_base=sum(x["tested_configurations"] for x in r["symbols"])
total_kfei=sum(y.get("configurations",0) for x in f["symbols"] for y in x["results"])
total_micro=sum(x.get("configurations",0) for x in m["results"])
passed_base=sum(x["2025_passing_count"] for x in r["symbols"])
passed_kfei=sum(y.get("2025_passing",0) for x in f["symbols"] for y in x["results"])
passed_micro=sum(x.get("2025_passing",0) for x in m["results"])
survive_base=sum(1 for x in r["symbols"] if x.get("best_2025") and x["best_2025"]["2026"]["mean_R"]>0)
survive_kfei=sum(y.get("2026_positive_among_passed",0) for x in f["symbols"] for y in x["results"])
survive_micro=sum(x.get("2026_positive_among_passed",0) for x in m["results"])
assert (total_base,total_kfei,total_micro)==(1764,5292,336)
assert (passed_base,passed_kfei,passed_micro)==(1,6,0)
assert survive_base+survive_kfei+survive_micro==0
riskdiff=subprocess.run(["git","-C",str(ROOT),"diff","main","--","config","src/katarina/governance"],capture_output=True,text=True)
assert riskdiff.returncode==0 and not riskdiff.stdout.strip(), "Risk settings changed"
audit={"kind":"KATARINA_2025_2026_MULTI_TF_RR_INTEGRITY",
 "outcome":"NO_STRATEGY_PROMOTION",
 "source_sha256":{k:hashlib.sha256((A/v).read_bytes()).hexdigest() for k,v in files.items()},
 "timeframes_native_scanned":len(tf),"symbols":7,
 "tested_parameter_scenarios":{"old_V2_RR":total_base,"KFEI_9_TF":total_kfei,
    "XAU_M1_M4_tick_derived":total_micro,"total":total_base+total_kfei+total_micro},
 "development_2025_gates_passed":passed_base+passed_kfei+passed_micro,
 "subsequent_2026_positive_survivors":0,
 "risk_governor_diff":False,
 "limits":["no untouched future validation","OHLC stop-first proxy; not intratick execution",
   "0.03R assumed commission","2025 starts differ by symbol",
   "H2 research run had 240-minute hold and is NOT scalp",
   "multiple comparisons not corrected","independent scenarios not guaranteed"],
 "checks_passed":True}
out=A/"katarina_rr_timeframe_integrity_20261011.json"
out.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
print(json.dumps(audit,indent=2))
