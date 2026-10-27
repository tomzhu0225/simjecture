"""Install a temporary, expiring control check for the exact owned R10 lease."""
from pathlib import Path
import datetime, json, subprocess, time
R=Path(__file__).parent
lease=json.loads((R/'r10-lease.json').read_text())
assert lease['stop_by']>time.time()
end=datetime.datetime.fromtimestamp(lease['stop_by']+660,datetime.timezone.utc).isoformat()
args='-d Ubuntu-CPP -u tomzhu0225 -- /usr/bin/flock -n '+str(R/'r10-control.lock')+' /home/tomzhu0225/.local/share/uv/tools/google-colab-cli/bin/python '+str(R/'r10_control_once.py')
def quote(value):return "'"+value.replace("'","''")+"'"
script="""$ErrorActionPreference='Stop'
$name='Simjecture-R10-20261027'
if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) { throw 'Existing R10 task; inspect before modifying' }
$end=[DateTimeOffset]::Parse(END)
$start=(Get-Date).AddSeconds(10)
$action=New-ScheduledTaskAction -Execute 'wsl.exe' -Argument ARGUMENTS
$trigger=New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration ($end.LocalDateTime-$start)
$trigger.EndBoundary=$end.UtcDateTime.ToString('yyyy-MM-ddTHH:mm:ssZ')
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -DeleteExpiredTaskAfter (New-TimeSpan -Minutes 1)
$principal=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
Start-ScheduledTask -TaskName $name
Get-ScheduledTask -TaskName $name | Select-Object TaskName,State | ConvertTo-Json -Compress
""".replace('END',quote(end)).replace('ARGUMENTS',quote(args))
x=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,timeout=45)
record=dict(at=time.time(),task='Simjecture-R10-20261027',endpoint=lease['endpoint'],stop_by=lease['stop_by'],task_expires_at=lease['stop_by']+660,returncode=x.returncode,result=x.stdout.strip(),error=x.stderr.strip())
(R/'r10-scheduled-control.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record));x.check_returncode()
