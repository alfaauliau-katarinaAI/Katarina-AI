from __future__ import annotations
import importlib, json, subprocess, sys

def installed():
    try:
        m=importlib.import_module("MetaTrader5")
        return True,getattr(m,"__version__","unknown"),None
    except Exception as exc:
        return False,None,str(exc)

ok,version,error=installed()
install_stdout=""
install_stderr=""
install_code=None
if not ok:
    p=subprocess.run(
        [sys.executable,"-m","pip","install","--disable-pip-version-check","--no-input","MetaTrader5"],
        capture_output=True,text=True,timeout=240
    )
    install_code=p.returncode
    install_stdout=p.stdout[-4000:]
    install_stderr=p.stderr[-4000:]
    ok,version,error=installed()
out={
    "proof_type":"KATARINA_MT5_PYTHON_BOOTSTRAP",
    "installed":ok,
    "version":version,
    "import_error":error,
    "pip_exit_code":install_code,
    "pip_stdout_tail":install_stdout,
    "pip_stderr_tail":install_stderr,
}
print(json.dumps(out,sort_keys=True))
if not ok:
    raise SystemExit(2)
