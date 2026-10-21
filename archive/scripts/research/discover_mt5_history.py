from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> None:
    roots=[]
    appdata=os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata)/"MetaQuotes"/"Terminal")
    roots.extend([
        Path(r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal"),
    ])
    seen=set()
    matches=[]
    extensions={".tkc",".hcc",".hc",".csv"}
    for root in roots:
        try:
            root=root.resolve()
        except Exception:
            continue
        if str(root).lower() in seen or not root.exists():
            continue
        seen.add(str(root).lower())
        for base,dirs,files in os.walk(root):
            rel=Path(base).relative_to(root)
            if len(rel.parts)>7:
                dirs[:]=[]
                continue
            for name in files:
                p=Path(base)/name
                low_path=str(p).lower()
                if "xau" not in low_path and "gold" not in low_path:
                    continue
                if p.suffix.lower() not in extensions:
                    continue
                try:
                    size=p.stat().st_size
                except OSError:
                    size=-1
                matches.append({"path":str(p),"size":size,"suffix":p.suffix.lower()})
                if len(matches)>=200:
                    break
            if len(matches)>=200:
                break
        if len(matches)>=200:
            break

    mt5_python=False
    mt5_error=None
    try:
        import MetaTrader5 as mt5  # type: ignore
        mt5_python=True
        version=getattr(mt5,"__version__","unknown")
    except Exception as exc:
        version=None
        mt5_error=str(exc)

    out={
        "proof_type":"KATARINA_MT5_HISTORY_DISCOVERY",
        "roots_checked":[str(x) for x in roots],
        "xau_history_files":matches,
        "file_count":len(matches),
        "metatrader5_python_available":mt5_python,
        "metatrader5_python_version":version,
        "metatrader5_python_error":mt5_error,
    }
    print(json.dumps(out,sort_keys=True))


if __name__=="__main__":
    main()
