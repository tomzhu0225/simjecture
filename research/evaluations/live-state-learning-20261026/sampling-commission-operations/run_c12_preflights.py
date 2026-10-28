from pathlib import Path
import subprocess,sys,json,time,traceback
r=Path('/home/simjecture/investigations/scientific-attention-20261025')
s=dict(stage='checking_host_records',started_at=time.time())
def save():(r/'c12-preflight-status.json').write_text(json.dumps(s,indent=2)+'\n')
save()
try:
 for name in ['qualify_c12_host_records.py','qualify_c12_physics.py','run_c12_auth.py']:
  s['current']=name;save()
  subprocess.run([sys.executable,'-u',str(r/name)],check=True,timeout=650)
 assert json.loads((r/'c12-auth-01/STATUS.json').read_text())['stage']=='completed'
 s.update(stage='passed',ended_at=time.time())
except Exception:s.update(stage='failed',error=traceback.format_exc(),ended_at=time.time())
save();print(json.dumps(s),flush=True)
