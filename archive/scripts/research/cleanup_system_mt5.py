from __future__ import annotations
import json, subprocess

ps=r'''
$rows=@()
foreach($p in @(Get-WmiObject Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue)){
  $owner=$p.GetOwner()
  $user=[string]$owner.User
  $domain=[string]$owner.Domain
  $killed=$false
  $rc=$null
  if($user -ieq 'SYSTEM'){
    try { $rc=[int]$p.Terminate(); $killed=($rc -eq 0) } catch { $rc=-1 }
    if(-not $killed){
      try {
        & taskkill.exe /PID ([string]$p.ProcessId) /F | Out-Null
        Start-Sleep -Milliseconds 250
        $alive = Get-WmiObject Win32_Process -Filter ("ProcessId="+[string]$p.ProcessId) -ErrorAction SilentlyContinue
        $killed = ($null -eq $alive)
        if($killed){ $rc=0 }
      } catch {}
    }
  }
  $rows += [pscustomobject]@{
    pid=[int]$p.ProcessId
    owner=($domain+'\\'+$user)
    executable=[string]$p.ExecutablePath
    creation=[string]$p.CreationDate
    killed=$killed
    terminate_rc=$rc
  }
}
$rows | ConvertTo-Json -Compress
'''
p=subprocess.run(["powershell.exe","-NoProfile","-Command",ps],capture_output=True,text=True,timeout=45)
raw=p.stdout.strip()
try:
    rows=json.loads(raw) if raw else []
except Exception:
    rows={"raw":raw}
print(json.dumps({"proof_type":"KATARINA_MT5_SYSTEM_PROCESS_CLEANUP","exit_code":p.returncode,"rows":rows,"stderr":p.stderr[-1000:]},sort_keys=True))
raise SystemExit(0 if p.returncode==0 else 2)
