from pathlib import Path
import json,subprocess,shlex,time,traceback
R=Path('/home/simjecture/investigations/scientific-attention-20261025');status=dict(stage='waiting_for_allocation',started_at=time.time());path=R/'c12-deploy-status.json'
def save():
 p=path.with_suffix('.tmp');p.write_text(json.dumps(status,indent=2));p.replace(path)
ssh=['ssh','-S',str(R/'private/c12-a100.sock'),'-o','ControlMaster=no','-o','ProxyCommand=false','-o','BatchMode=yes','root@colab-c12']
def remote(cmd,timeout=30):return subprocess.run(ssh+[cmd],capture_output=True,timeout=timeout)
save()
try:
 deadline=json.loads((R/'c12-lease.json').read_text())['stop_by']
 while time.time()<min(status['started_at']+600,deadline-120):
  p=R/'c12-allocation-status.json'
  if p.exists():
   allocation=json.loads(p.read_text())
   if allocation['stage']=='failed':raise RuntimeError('Allocation failed; inspect before retry')
   if allocation['stage']=='ready':break
  time.sleep(3)
 else:raise TimeoutError('Allocation not ready within setup bound')
 status['stage']='deploying';save()
 assert remote('mkdir -p /content/science-attention/workflow-return-source-171ac44').returncode==0
 # Only the serving package is needed on A100; the coordinator retains the full source.
 p=subprocess.Popen(['tar','-cf','-','-C',str(R/'workflow-return-source-171ac44'),'packages/simjecture-monitor/src'],stdout=subprocess.PIPE)
 x=subprocess.run(ssh+['tar -xf - -C /content/science-attention/workflow-return-source-171ac44'],stdin=p.stdout,capture_output=True,timeout=90);p.stdout.close();assert p.wait()==0 and x.returncode==0
 for source,name in [('validation-model-assets.tar.gz','validation-model-assets.tar.gz'),('prepare_c12_a100.py','prepare_c12_a100.py'),('c12_service.py','c12_service.py'),('recovery_kernel_check.py','recovery_kernel_check.py'),('c12-lease.json','c12-lease.json'),('private/attention.token','attention.token')]:
  program="from pathlib import Path;import sys,shutil,os;os.umask(0o077);p=Path("+repr('/content/science-attention/'+name)+");f=p.open('wb');shutil.copyfileobj(sys.stdin.buffer,f);f.close();p.chmod(0o600)"
  with (R/source).open('rb') as data:x=subprocess.run(ssh+['python3 -c '+shlex.quote(program)],stdin=data,capture_output=True,timeout=240)
  assert x.returncode==0,'Asset upload failed'
 program="from pathlib import Path;import subprocess,json;r=Path('/content/science-attention');out={};\nfor name in ['prepare_c12_a100.py','c12_service.py']:\n log=(r/(name+'.log')).open('w');p=subprocess.Popen(['/usr/bin/python3','-u',str(r/name)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True);out[name]=p.pid\nprint(json.dumps(out))"
 x=remote('python3 -c '+shlex.quote(program));assert x.returncode==0
 status.update(stage='deployed',runtime_processes=json.loads(x.stdout),ended_at=time.time())
except Exception as e:
 status.update(stage='failed',error_type=type(e).__name__,error=traceback.format_exc(),ended_at=time.time())
 (R/'STOP_C12_COLAB').write_text('Deployment failed; preserve all records and release owned allocation.\n')
finally:save()
print(json.dumps(status),flush=True)
