"""WP6 preflight: can the observer restart by itself after a reboot? Read-only, never changes the VPS.

Offline (any OS), from exported evidence:
  python scripts/ai/wp6_startup_preflight.py --task-xml task.xml --launcher run-observer.ps1 --autologon 0
On the Windows host, read the live task and autologon flag (read-only; the password is never read):
  python scripts/ai/wp6_startup_preflight.py --live
Exit code 0 only for READY_FOR_REBOOT_TEST.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from katarina.intelligence.operations.startup_task import analyze  # noqa: E402

TASK = "Katarina-Readonly-Observer"


def _live():
    xml = subprocess.run(["schtasks", "/query", "/tn", TASK, "/xml"], stdout=subprocess.PIPE, check=True,
                         timeout=30).stdout
    text = xml.decode("utf-16") if xml[:2] in (b"\xff\xfe", b"\xfe\xff") else xml.decode("mbcs", "replace")
    launcher = Path(r"C:\Katarina\run-observer.ps1").read_text(encoding="utf-8-sig")
    import winreg  # Windows only
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon") as key:
        def value(name):
            try:
                return winreg.QueryValueEx(key, name)[0]
            except FileNotFoundError:
                return None
        enabled, user = str(value("AutoAdminLogon") or "0") == "1", value("DefaultUserName")
    return text, launcher, enabled, user


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--task-xml", type=Path)
    parser.add_argument("--launcher", type=Path)
    parser.add_argument("--autologon", choices=("0", "1"))
    parser.add_argument("--autologon-user")
    parser.add_argument("--session0-mt5-verified", action="store_true",
                        help="Only with recorded evidence from an isolated host")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.live:
        xml, launcher, enabled, user = _live()
    else:
        if not (args.task_xml and args.launcher):
            parser.error("--task-xml and --launcher are required without --live")
        raw = args.task_xml.read_bytes()
        xml = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
        launcher = args.launcher.read_text(encoding="utf-8-sig")
        enabled = None if args.autologon is None else args.autologon == "1"
        user = args.autologon_user
    report = analyze(xml, launcher, autologon_enabled=enabled, autologon_user=user,
                     session0_mt5_verified=args.session0_mt5_verified)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in report["findings"]:
        print(f"{item['severity']} {item['reason']} {item['detail']}".rstrip())
    print("WP6_PREFLIGHT", report["verdict"], report["mode"])
    return 0 if report["verdict"] == "READY_FOR_REBOOT_TEST" else 1


if __name__ == "__main__":
    raise SystemExit(main())
