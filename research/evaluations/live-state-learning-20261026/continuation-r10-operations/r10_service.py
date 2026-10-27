from pathlib import Path
import json,os,subprocess,sys,time,traceback
r=Path('/content/science-attention');p=r/'r10-service-controller.json'
if p.exists():raise RuntimeError('Existing service controller; inspect before restarting')
s=dict(stage='waiting_for_preparation',started_at=time.time());child=None
source=r/'replication-source-04f905c'
def save():p.write_text(json.dumps(s,indent=2))
def deadline():return json.loads((r/'r10-lease.json').read_text())['stop_by']
save()
try:
 while time.time()<deadline()-120:
  f=r/'r10-prepare-status.json'
  if f.exists():
   prep=json.loads(f.read_text())
   if prep['stage']=='failed':raise RuntimeError('Runtime restoration failed')
   if prep['stage']=='ready':break
  time.sleep(3)
 else:raise TimeoutError('Insufficient remaining validation lease')
 args=[sys.executable,'-u','-m','simjecture_monitor.multiadapter_server','--checkpoint',prep['base'],'--socket',str(r/'attention.sock'),'--status',str(r/'r10-service-status.json'),'--auth-token-file',str(r/'attention.token'),'--maximum-tokens','8192','--wall-seconds',str(int(deadline()-time.time())),'--idle-seconds','3600','--temperature','1','--decision-distribution','independent/v1']
 for policy in ['continued_sft']:args+=['--adapter',policy+'='+str(r/'validation-assets'/policy/'adapter')]
 env=dict(os.environ,PYTHONPATH=str(source/'packages/simjecture-monitor/src'),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
 with (r/'r10-service.log').open('w') as log:
  child=subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT)
  s.update(stage='serving',pid=child.pid);save()
  while child.poll() is None and time.time()<deadline():time.sleep(5)
  if child.poll() is None:raise TimeoutError('Lease ended')
  if child.returncode:raise RuntimeError('Model server returned '+str(child.returncode))
 s.update(stage='completed',ended_at=time.time())
except Exception:s.update(stage='failed',error=traceback.format_exc(),ended_at=time.time())
finally:
 if child is not None and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:child.kill();child.wait()
 save()
