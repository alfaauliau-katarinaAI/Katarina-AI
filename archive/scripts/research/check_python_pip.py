from __future__ import annotations
import json, subprocess, sys

out={"python":sys.executable,"version":sys.version,"pip":False,"pip_version":None}
try:
    p=subprocess.run([sys.executable,"-m","pip","--version"],capture_output=True,text=True,timeout=30)
    out["pip"]=p.returncode==0
    out["pip_version"]=(p.stdout or p.stderr).strip()
except Exception as exc:
    out["pip_error"]=str(exc)
print(json.dumps(out,sort_keys=True))
