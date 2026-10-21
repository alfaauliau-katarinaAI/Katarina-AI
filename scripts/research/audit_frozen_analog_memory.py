"""Reconstruct EVERY historical analog sample from original causal source."""
from __future__ import annotations
import argparse,json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import numpy as np
from evaluate_regime_prediction_ml import select_samples,make_features
from katarina.intelligence.historical_analog_memory import EMBARGO_SECONDS,FEATURE_LAYOUT

def utc(iso):
    dt=datetime.fromisoformat(iso)
    if dt.tzinfo is None:raise ValueError("timezone_required")
    return dt.timestamp()

def audit(doc,source):
    if doc.get("kind")!="frozen_per_symbol_historical_analog_memory_v1" or (
      doc.get("model_promotion_allowed") is not False or
      doc.get("no_live_orders") is not True):
        raise ValueError("unsafe_historical_memory")
    if doc.get("sample_feature_version")!=FEATURE_LAYOUT:
        raise ValueError("outdated_embeddings")
    if doc.get("source_study_was_previously_researched") is not True:
        raise ValueError("false_out_of_sample_claim")
    stop=utc(doc["asof_utc"])
    count=0
    for sym,by_horizon in doc["by_symbol"].items():
        for h,bank in by_horizon.items():
            if bank["status"]!="REFERENCE_ONLY":continue
            h=int(h)
            truth=[x for x in select_samples(source,sym,h)
                   if x["label_end"]+EMBARGO_SECONDS<stop]
            if len(truth)!=bank["n_samples"] or len(truth)!=len(bank["examples"]):
                raise ValueError("missing_or_extra_training_examples")
            for sample,record in zip(truth,bank["examples"]):
                t=utc(record["time_utc"])
                resolved=utc(record["outcome_resolved_utc"])
                if abs(sample["signal_time"]-t)>.1 or abs(sample["label_end"]-resolved)>.1:
                    raise ValueError("sample_time_changed")
                if resolved+EMBARGO_SECONDS>=stop or t>=stop:
                    raise ValueError("unresolved_future_label_in_bank")
                if record["outcome_future_close_up"]!=sample["y"] or record["regime"]!=sample["regime"]:
                    raise ValueError("outcome_or_regime_tampered")
                actual=np.array(record["features"],dtype=float)
                expected=np.array(make_features(sample["source"],"technical_plus_regime"),dtype=float)
                if not np.all(np.isfinite(actual)) or actual.shape!=expected.shape or not np.array_equal(actual,expected):
                    raise ValueError("causal_source_embedding_mismatch")
                count+=1
    return dict(kind="frozen_symbol_analog_memory_audit",
        completed_historical_sample_records_checked=count,
        raw_source_embeddings_verified=True,
        future_resolution_embargo_verified=True,
        symbol_separation_verified=True,
        live_execution_enabled=False,
        model_promotion_allowed=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    raw=Path(a.report).read_bytes()
    src=Path(a.source).read_bytes()
    doc=json.loads(raw)
    if doc["source_sha256"]!=sha256(src).hexdigest():
        raise ValueError("source_sha256_changed")
    result=audit(doc,json.loads(src))
    result["archive_sha256"]=sha256(raw).hexdigest()
    output=Path(a.output)
    if output.exists():raise FileExistsError("immutable")
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
