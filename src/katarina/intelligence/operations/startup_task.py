"""WP6 preflight: will the canonical observer come back by itself after a VPS reboot? Read-only.

Inputs are evidence the operator exports (no change is made here):
- the Task Scheduler XML of ``Katarina-Readonly-Observer`` (``schtasks /query /tn NAME /xml``),
- the launcher text (``C:\\Katarina\\run-observer.ps1``),
- the Windows autologon state (``AutoAdminLogon`` and the user; the password is never read).

Two start modes are recognised:
- ``AUTOLOGON_INTERACTIVE``: LogonTrigger + InteractiveToken and Windows autologon for that user, so
  MT5 keeps its interactive desktop (current production design, session 2).
- ``BOOT_NON_INTERACTIVE``: BootTrigger with a stored-password/S4U principal (session 0). MT5 in
  session 0 is unproven for this terminal, so it stays ``BLOCKED_EVIDENCE`` until tested on an
  isolated host.

Verdicts: ``READY_FOR_REBOOT_TEST`` | ``NOT_READY`` | ``BLOCKED_EVIDENCE``. This checks configuration only;
``READY_AFTER_REBOOT`` needs evidence from a real reboot (``post_reboot.assess``). Never authorizes trading.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
CANONICAL_LAUNCHER = "run-observer.ps1"
MUTEX_NAME = "Global\\KatarinaReadonlyObserver"
NON_INTERACTIVE_LOGON = {"Password", "S4U", "ServiceAccount"}
_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


def _seconds(text: str | None) -> int | None:
    match = _DURATION.match((text or "").strip())
    if not match or not any(match.groups()):
        return None
    d, h, m, s = (int(x or 0) for x in match.groups())
    return ((d * 24 + h) * 60 + m) * 60 + s


def _text(node, path: str, default: str | None = None) -> str | None:
    found = node.find(path, NS)
    return found.text.strip() if found is not None and found.text else default


def _finding(reason: str, severity: str, detail: str = "") -> dict:
    return {"reason": reason, "severity": severity, "detail": detail}


def analyze(task_xml: str, launcher_text: str, *, autologon_enabled: bool | None, autologon_user: str | None,
            session0_mt5_verified: bool = False) -> dict:
    findings: list[dict] = []
    try:
        # schtasks writes UTF-16 with an encoding declaration; parse the decoded text without it.
        root = ET.fromstring(re.sub(r"^\ufeff?\s*<\?xml[^>]*\?>", "", task_xml))
    except ET.ParseError as error:
        return {"verdict": "NOT_READY", "mode": None, "findings": [_finding("WP6_TASK_XML_INVALID", "P0", str(error))],
                "live_execution_authorized": False}
    principal = root.find("t:Principals/t:Principal", NS)
    logon_type = _text(principal, "t:LogonType", "InteractiveToken") if principal is not None else None
    principal_user = _text(principal, "t:UserId") if principal is not None else None
    boot = root.findall("t:Triggers/t:BootTrigger", NS)
    logon = root.findall("t:Triggers/t:LogonTrigger", NS)
    enabled = [t for t in boot + logon if (_text(t, "t:Enabled", "true") or "true").lower() == "true"]
    settings = root.find("t:Settings", NS)
    if settings is None:
        settings = ET.Element("Settings")
    if (_text(settings, "t:Enabled", "true") or "true").lower() != "true":
        findings.append(_finding("WP6_TASK_DISABLED", "P0"))
    commands = " ".join(filter(None, [_text(a, "t:Command", "") + " " + _text(a, "t:Arguments", "")
                                      for a in root.findall("t:Actions/t:Exec", NS)]))
    if CANONICAL_LAUNCHER not in commands or "-File" not in commands:
        findings.append(_finding("WP6_ACTION_NOT_CANONICAL_LAUNCHER", "P0", commands[:160]))
    if _text(settings, "t:MultipleInstancesPolicy", "IgnoreNew") != "IgnoreNew":
        findings.append(_finding("WP6_MULTIPLE_INSTANCES_ALLOWED", "P0",
                                 _text(settings, "t:MultipleInstancesPolicy", "")))
    limit = _seconds(_text(settings, "t:ExecutionTimeLimit", "PT72H"))
    if limit not in (0, None) or _text(settings, "t:ExecutionTimeLimit", "PT72H") != "PT0S":
        findings.append(_finding("WP6_EXECUTION_TIME_LIMIT", "P0", _text(settings, "t:ExecutionTimeLimit", "PT72H")))
    restart = settings.find("t:RestartOnFailure", NS)
    interval = _seconds(_text(restart, "t:Interval")) if restart is not None else None
    count = int(_text(restart, "t:Count", "0")) if restart is not None else 0
    if restart is None or interval is None or interval > 600 or count < 3:
        findings.append(_finding("WP6_NO_RESTART_ON_FAILURE", "P1", f"interval={interval} count={count}"))
    for key in ("DisallowStartIfOnBatteries", "StopIfGoingOnBatteries"):
        if (_text(settings, f"t:{key}", "true") or "true").lower() == "true":
            findings.append(_finding("WP6_BATTERY_POLICY_CAN_STOP", "P2", key))
    if "STOP_OBSERVER" not in launcher_text:
        findings.append(_finding("WP6_LAUNCHER_NO_STOP_MARKER", "P0"))
    if MUTEX_NAME not in launcher_text or "WaitOne(" not in launcher_text:
        findings.append(_finding("WP6_LAUNCHER_NO_SINGLE_INSTANCE_MUTEX", "P0"))
    elif "AbandonedMutexException" not in launcher_text:
        # A killed launcher leaves the named mutex abandoned: WaitOne throws and, with
        # ErrorActionPreference=Stop, the next start fails until RestartOnFailure retries.
        findings.append(_finding("WP6_LAUNCHER_ABANDONED_MUTEX_NOT_HANDLED", "P1"))
    mode = None
    boot_ok = [t for t in enabled if t in boot]
    if boot_ok and logon_type in NON_INTERACTIVE_LOGON:
        mode = "BOOT_NON_INTERACTIVE"
        if not session0_mt5_verified:
            findings.append(_finding("WP6_SESSION0_MT5_UNVERIFIED", "P0",
                                     "MT5 terminal in session 0 must be proven on an isolated host first"))
    elif [t for t in enabled if t in logon] and logon_type == "InteractiveToken":
        mode = "AUTOLOGON_INTERACTIVE"
        trigger_user = _text(logon[0], "t:UserId") or principal_user
        if autologon_enabled is None:
            findings.append(_finding("WP6_AUTOLOGON_STATE_UNKNOWN", "P0"))
        elif not autologon_enabled:
            findings.append(_finding("WP6_NO_AUTOLOGON", "P0", "LogonTrigger never fires after a reboot without login"))
        elif (autologon_user or "").split("\\")[-1].lower() != (trigger_user or "").split("\\")[-1].lower():
            findings.append(_finding("WP6_AUTOLOGON_USER_MISMATCH", "P0", f"{autologon_user} != {trigger_user}"))
    else:
        findings.append(_finding("WP6_NO_REBOOT_TRIGGER", "P0", f"logon_type={logon_type}"))
    blocking = [f for f in findings if f["severity"] in ("P0", "P1")]
    if any(f["reason"] == "WP6_SESSION0_MT5_UNVERIFIED" for f in blocking) and len(blocking) == 1:
        verdict = "BLOCKED_EVIDENCE"
    else:
        verdict = "NOT_READY" if blocking else "READY_FOR_REBOOT_TEST"
    return {"verdict": verdict, "mode": mode, "logon_type": logon_type, "findings": findings,
            "orders_submitted": 0, "live_execution_authorized": False}
