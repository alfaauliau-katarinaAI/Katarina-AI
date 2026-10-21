"""Brief, non-misleading developer-only selection and coverage diagnostics."""
import json,sys
from collections import Counter
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows=r["all_combinations"]
print("count",len(rows),"adequate",sum(x["selection_sample_sufficient"] for x in rows),
      "validated",sum(x["development_pass"] for x in rows))
print("Adequate sample cohort shortlist, selected by older price history ONLY")
for x in [x for x in rows if x["selection_sample_sufficient"]][:18]:
    a=x["development_aug"]; b=x["development_sep"]; o=x["chronological_october_diagnostic"]
    print(x["symbol"],x["family"],x["side"],"TP",x["tp_atr"],"SL",x["sl_atr"],
          "aug",a["n"],round(a["mean_r"],3),
          "sep",b["n"],round(b["mean_r"],3),
          "oct",o["n"],None if o["mean_r"] is None else round(o["mean_r"],3),
          "pf_aug",None if a["profit_factor"] is None else round(a["profit_factor"],2),
          "pf_sep",None if b["profit_factor"] is None else round(b["profit_factor"],2))
print("Top inadequate-n-but-positive-OCT, NOT valid strategy")
for x in sorted((a for a in rows if a["chronological_october_diagnostic"]["n"]>=10),
                key=lambda a:-(a["chronological_october_diagnostic"]["mean_r"] or -999))[:6]:
    print(x["symbol"],x["family"],x["side"],x["tp_atr"],x["sl_atr"],
          "OCT",x["chronological_october_diagnostic"]["n"],
          round(x["chronological_october_diagnostic"]["mean_r"],3),
          "DEV_PASS",x["development_pass"])
