from pathlib import Path
import hashlib,importlib.util,json,os,shlex,subprocess,time,traceback
from readonly_physics_readiness import wait_for_ready
R=Path('/home/simjecture/investigations/scientific-attention-20261025');Q=R/'r11-transport-qualification';Q.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=dict(stage='preparing',started_at=time.time(),cases=[],readiness_attempts=[],scope='Two engineering controls; no native worker or decision-model call')
def save():
 p=Q/'STATUS.tmp';p.write_text(json.dumps(s,indent=2));p.replace(Q/'STATUS.json')
save()
try:
 assert json.loads((R/'r10-guard-status.json').read_text())['stage']=='released'
 prior=json.loads((R/'r10-transport-qualification/STATUS.json').read_text())
 assert sha(Path.home()/'.ssh/config')==prior['ssh_config_sha256']
 assert not (R/'plasma-backend-r11.json').exists()
 (R/'plasma-backend-r11.json').write_bytes((R/'plasma-backend-r10.json').read_bytes())
 backend=json.loads((R/'plasma-backend-r11.json').read_text());assert sha(backend['machine_profile'])==prior['machine_profile_sha256']
 profile=json.loads(Path(backend['machine_profile']).read_text())['machine']
 command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+profile['known_hosts'],'-o','IdentitiesOnly=yes','-i',profile['identity_file'],'-p',str(profile['port']),profile['user']+'@'+profile['host'],'test -x '+shlex.quote(backend['binary'])]
 def record(value):s['readiness_attempts'].append(value);save()
 ready=wait_for_ready(command,stop_by=time.time()+180,on_attempt=record);assert ready['ready'],ready['reason']
 s.update(stage='running',backend_sha256=sha(R/'plasma-backend-r11.json'),machine_profile_sha256=sha(backend['machine_profile']),ssh_config_sha256=sha(Path.home()/'.ssh/config'));save()
 work=Q/'research';work.mkdir();old=R/'r8-transport-qualification/research'
 for name in ['inputs','original_analysis.py','environment.json']:(work/name).write_bytes((old/name).read_bytes())
 source=R/'replication-source-04f905c';env=dict(os.environ,PYTHONPATH=str(source/'src')+':'+str(source/'packages/simjecture-monitor/src'),SIMJECTURE_PLASMA_BACKEND=str(R/'plasma-backend-r11.json'),OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
 spec=importlib.util.spec_from_file_location('original_analysis',work/'original_analysis.py');analyzer=importlib.util.module_from_spec(spec);spec.loader.exec_module(analyzer);analyzer.yt.funcs.mylog.setLevel(40)
 for cells,steps in [(64,40),(128,80)]:
  name=f'mesh_{cells}';row=dict(name=name,cells=cells,steps=steps,started_at=time.time());s['cases'].append(row);save()
  with (Q/(name+'.log')).open('w') as log:x=subprocess.run([str(R/'replication-env/bin/python'),'-m','simjecture_monitor.remote_plasma','--name',name,'--cells',str(cells),'--steps',str(steps)],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=195)
  row.update(returncode=x.returncode,receipt=json.loads((work/'runs'/name/'receipt.json').read_text()));save();receipt=row['receipt']
  assert x.returncode==0 and receipt['status']=='succeeded'
  assert receipt['binary_sha256']=='40259ed2687707b4c693e5b0e7fbadef54dca4fab64898d9d42e654fbdf644eb'
  assert receipt['input_sha256']==sha(work/'inputs')
  row['measured']=analyzer.analyze(work/'runs'/name/f'plot{steps:06d}',cells);assert row['measured']['original_checks_passed']
  row['ended_at']=time.time();save()
 s.update(stage='completed',ended_at=time.time(),input_sha256=sha(work/'inputs'),original_analysis_sha256=sha(work/'original_analysis.py'))
except Exception:s.update(stage='failed',ended_at=time.time(),error=traceback.format_exc())
save();print(json.dumps(s),flush=True)
if s['stage']!='completed':raise SystemExit(1)
