from pathlib import Path
import hashlib,json,os,subprocess,time,traceback
from simjecture_monitor.attention_server import request
from r7_initial_provider_failure import initial_429
from p40_presubmission_failure import presubmission_failure
from simjecture_monitor.native_guard import process_stat,stop_session

root=Path('/home/simjecture/investigations/scientific-attention-20261025')
manifest_path=root/'r9-workflow-manifest.json';manifest=json.loads(manifest_path.read_text())
campaign=root/'base-sft-replication-v5';campaign.mkdir(exist_ok=False)
status=dict(stage='waiting_for_model',started_at=time.time(),manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),blocks=[],host_revision=manifest['host_revision'])
def save():
 p=campaign/'CAMPAIGN.tmp';p.write_text(json.dumps(status,indent=2));p.replace(campaign/'CAMPAIGN.json')
def budget():return json.loads((root/'native-budget-r9.json').read_text())
health_path=root/'private/r9-link.sock'
bridge=None;bridge_owner=None
def health():return request(health_path,dict(operation='health',auth_token=(root/'private/attention.token').read_text().strip()),timeout=30)['status']
save()
try:
 phase=json.loads((root/'r9-phase-plan.json').read_text())
 assert phase['assignment_manifest_sha256']==status['manifest_sha256']
 assert phase['require_fresh_model_qualification']
 assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==phase['controller_sha256']
 assert hashlib.sha256((root/'r9-probes.json').read_bytes()).hexdigest()==phase['probes_sha256']
 assert hashlib.sha256((root/'plasma-backend-r9.json').read_bytes()).hexdigest()==phase['backend_profile_sha256']
 for relative,expected in phase['source_files_sha256'].items():
  assert hashlib.sha256((root/'replication-source-04f905c'/relative).read_bytes()).hexdigest()==expected
 while time.time()<min(status['started_at']+1500,budget()['deadline']-manifest['minimum_seconds_for_new_block']):
  if (root/'STOP_R9_COLAB').exists():raise RuntimeError('Deployment or allocation stopped before model readiness')
  try:
   ready=health()
   if ready['stage']=='ready':break
  except (OSError,RuntimeError,ValueError):pass
  time.sleep(15)
 else:raise RuntimeError('Model not ready within the collection allocation')
 identity=ready['model_identities']
 status.update(stage='warming',model_identities=identity);save()
 # Warm using commissioning inputs only, before any held-out execution.
 warm=campaign/'warmup';warm.mkdir()
 for label,folder in [('healthy','commission-02-observe'),('unit-reporting','commission-03-rules')]:
  paths=sorted((root/folder/'monitor').glob('attention-*.json'))
  if not paths:raise RuntimeError('Commissioning input is missing')
  packet=json.loads(paths[-1].read_text())['submitted']
  for policy in ['base','continued_sft']:
   result=request(root/'private/r9-link.sock',dict(observation=packet,policy=policy,auth_token=(root/'private/attention.token').read_text().strip()),timeout=360)
   (warm/(label+'-'+policy+'.json')).write_text(json.dumps(result,indent=2))
   if result['decision']['status']=='insufficient_input':raise RuntimeError('Commissioning input exceeds the declared model budget')

 # Start the bounded public relay only after the resident model is warm.
 with (root/'r9-bridge.log').open('w') as log:
  bridge=subprocess.Popen(['/usr/bin/python3','-u',str(root/'attention_transport_r7.py'),'--socket',str(root/'attention-r9.sock'),'--upstream',str(root/'private/r9-link.sock'),'--log',str(campaign/'transport.jsonl'),'--stop-by',str(budget()['deadline']+120),'--request-seconds','24'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 bridge_owner=process_stat(bridge.pid);status['bridge_pid']=bridge.pid;save()
 for _ in range(100):
  if bridge.poll() is not None:raise RuntimeError('Public inference relay failed before readiness')
  if (root/'attention-r9.sock').exists():break
  time.sleep(.1)
 else:raise TimeoutError('Public inference relay did not appear')
 health_path=root/'attention-r9.sock'
 import math,shlex,itertools
 ssh=['ssh','-S',str(root/'private/r9-a100.sock'),'-o','ControlMaster=no','-o','ProxyCommand=false','-o','BatchMode=yes','root@colab-r9']
 probes=json.loads((root/'r9-probes.json').read_text());qualification=[]
 for probe in probes:
  policy=probe['policy']
  if policy != 'base' and identity[policy]['adapter_files_sha256']!=probe['adapter_hashes']:raise RuntimeError('Served adapter differs from saved update')
  result=request(root/'attention-r9.sock',dict(observation=probe['observation'],policy=policy,auth_token=(root/'private/attention.token').read_text().strip()),timeout=360)
  reference=probe['reference']
  if result['policy']!=policy or result['input_prompt_sha256']!=reference['prompt_sha256']:raise RuntimeError('Named-adapter qualification input mismatch')
  maximum=0.0
  for field,values in reference['probabilities'].items():
   converted={key:value**reference['temperature'] for key,value in values.items()};total=sum(converted.values())
   for key,value in converted.items():maximum=max(maximum,abs(value/total-result['prediction']['probabilities'][field][key]))
  qualification.append(dict(policy=policy,prompt_sha256=reference['prompt_sha256'],saved_temperature=reference['temperature'],serving_temperature=1.0,maximum_probability_error=maximum))
  (campaign/('qualification-'+policy+'-'+reference['prompt_sha256'][:16]+'.json')).write_text(json.dumps(dict(reference=reference,result=result,maximum_probability_error=maximum),indent=2))
  if maximum>1e-4:raise RuntimeError('Named adapter does not reproduce the saved reload probe')
 (campaign/'ADAPTER_QUALIFICATION.json').write_text(json.dumps(qualification,indent=2))
 status.update(stage='collecting',warmed_at=time.time(),adapter_qualification=qualification);save()

 def physics_preflight(trial):
  backend_path=root/'plasma-backend-r9.json';assert hashlib.sha256(backend_path.read_bytes()).hexdigest()==phase['backend_profile_sha256']
  backend=json.loads(backend_path.read_text());assert 'control_path' not in backend
  assert hashlib.sha256(Path(backend['machine_profile']).read_bytes()).hexdigest()==phase['machine_profile_sha256']
  profile=json.loads(Path(backend['machine_profile']).read_text())['machine']
  command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+profile['known_hosts'],'-o','IdentitiesOnly=yes','-i',profile['identity_file'],'-p',str(profile['port']),profile['user']+'@'+profile['host'],'test -x '+shlex.quote(backend['binary'])]
  started=time.time()
  assert hashlib.sha256((Path.home()/'.ssh/config').read_bytes()).hexdigest()==phase['ssh_config_sha256']
  result=subprocess.run(command,capture_output=True,timeout=55)
  check=dict(planned_trial=trial['id'],before_assignment=True,started_at=started,ended_at=time.time(),returncode=result.returncode)
  status.setdefault('physics_preflights',[]).append(check);save()
  if result.returncode:raise RuntimeError('P40 transport unavailable before assignment; no native trial started')
  if time.time()+750>=budget()['deadline']:raise TimeoutError('Insufficient remaining native lease after transport preflight; assignment remains unstarted')

 def run_trial(trial):
  directory=campaign/trial['id'];deadline=min(time.time()+750,budget()['deadline'])
  env=dict(os.environ,PYTHONPATH=str(root/'replication-source-04f905c/src')+':'+str(root/'replication-source-04f905c/packages/simjecture-monitor/src'),PATH='/home/simjecture/.local/bin:'+os.environ.get('PATH',''),OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',SIMJECTURE_PLASMA_BACKEND=str(root/'plasma-backend-r9.json'),SIMJECTURE_NATIVE_BUDGET=str(root/'native-budget-r9.json'),SIMJECTURE_CONTINUATION=trial['id'],SIMJECTURE_CONTINUATION_DEADLINE=str(deadline),SIMJECTURE_ATTENTION_TOKEN_FILE=str(root/'private/attention.token'))
  cmd=[str(root/'replication-env/bin/python'),str(root/'replication-source-04f905c/packages/simjecture-monitor/scripts/scientific_workflow_trials.py'),'--root',str(directory),'--family',trial['family'],'--arm',('adapted' if trial['arm'] in {'base','continued_sft'} else trial['arm']),'--seed',str(trial['seed']),'--socket',str(root/'attention-r9.sock'),'--wrapper',str(root/'r9-native-codex'),'--python',str(root/'replication-env/bin/python'),'--plasma-assets',str(root/'plasma')]
  if trial['arm'] in {'base','continued_sft'}:cmd+=['--model-policy',trial['arm']]
  if trial['arm']=='base':cmd[cmd.index('--arm')+1]='base'
  receipt=dict(**trial,started_at=time.time())
  with (campaign/(trial['id']+'.log')).open('w') as log:
   p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   owner=process_stat(p.pid)
   try:receipt['controller_exit']=p.wait(timeout=max(1,deadline-time.time()))
   except subprocess.TimeoutExpired:
    stop_session(owner);p.wait(timeout=10);receipt.update(controller_exit=p.returncode,resource_timeout=True)
  receipt['ended_at']=time.time();outcome=directory/'OUTCOME.json'
  if outcome.exists():receipt['outcome']=json.loads(outcome.read_text())
  else:receipt['missing_outcome']=True
  (campaign/(trial['id']+'-receipt.json')).write_text(json.dumps(receipt,indent=2))
  return receipt
 def infrastructure_failures(trial,receipt):
  failures=[];directory=campaign/trial['id']
  if receipt.get('missing_outcome') or receipt['controller_exit']!=0:
   failures.append(dict(id=trial['id'],kind='collector_failure'))
  errors=directory/'monitor/attention-errors.jsonl'
  if errors.exists() and errors.read_text().strip():failures.append(dict(id=trial['id'],kind='attention_error'))
  if presubmission_failure(directory):failures.append(dict(id=trial['id'],kind='solver_presubmission_transport_unavailable'))
  for path in (directory/'research/runs').glob('*/receipt.json'):
   value=json.loads(path.read_text())
   if value.get('status')=='unknown' or value.get('transport_status') in {'failed','timeout'}:
    failures.append(dict(id=trial['id'],kind='unconfirmed_solver_transport'))
  for entry in budget()['starts']:
   if entry['continuation']!=trial['id']:continue
   if entry.get('ended_at') is None:
    failures.append(dict(id=trial['id'],kind='native_role_still_active'))
   elif not entry.get('native'):
    failures.append(dict(id=trial['id'],kind='native_invocation_failed'))
   elif entry.get('returncode')!=0 and not entry.get('cancelled') and entry['ended_at']<entry['deadline']-2:
    failures.append(dict(id=trial['id'],kind='native_provider_or_process_failure',returncode=entry.get('returncode')))
  return failures

 last_workflow_ended=float(phase['last_retained_workflow_ended_at']);consecutive_initial_429=0;next_cooldown=manifest['minimum_gap_between_workflows_seconds']
 for block in manifest['blocks']:
  lease=budget()
  remaining_bound=len(block['trials'])*(750+180)
  if time.time()+remaining_bound>=lease['deadline'] or lease['maximum_starts']-len(lease['starts'])<12*len(block['trials']):
   status['stop_reason']='No complete new block fits the remaining lease';break
  if health()['model_identities']!=identity:raise RuntimeError('Model identity changed during the frozen comparison')
  record=dict(id=block['id'],started_at=time.time(),trials=[]);status['blocks'].append(record);save()
  for trial in block['trials']:
   earliest=last_workflow_ended+next_cooldown
   status.update(stage='between_workflows',next_trial=trial['id'],not_before=earliest);save()
   while time.time()<earliest:
    if (root/'STOP_R9_COLAB').exists():raise RuntimeError('Owned model resource stopped between workflows')
    time.sleep(min(3,earliest-time.time()))
   if health()['model_identities']!=identity:raise RuntimeError('Model identity changed before a timed trial')
   physics_preflight(trial)
   status['stage']='collecting';save()
   receipt=run_trial(trial);last_workflow_ended=receipt['ended_at']
   record['trials'].append(dict(id=receipt['id'],arm=receipt['arm'],controller_exit=receipt['controller_exit'],ended_at=receipt['ended_at']));save()
   failures=infrastructure_failures(trial,receipt)
   if failures:
    starts=[v for v in budget()['starts'] if v['continuation']==trial['id']]
    recognized=all(f['kind']=='native_provider_or_process_failure' for f in failures) and initial_429(campaign/trial['id'],starts)
    if recognized:
     consecutive_initial_429+=1;next_cooldown=180
     status.setdefault('preserved_initial_provider_failures',[]).append(dict(id=trial['id'],block=block['id'],failures=failures,consecutive=consecutive_initial_429))
     if consecutive_initial_429<3:save();continue
    status.update(stop_reason='Infrastructure failure or three consecutive pre-action provider rejections; preserve every attempt',infrastructure_failures=failures);save();break
   consecutive_initial_429=0;next_cooldown=manifest['minimum_gap_between_workflows_seconds']
  record['ended_at']=time.time();save()
  if status.get('infrastructure_failures'):break
 final_qualification=[]
 for index,probe in enumerate(probes):
  result=request(root/'attention-r9.sock',dict(observation=probe['observation'],policy=probe['policy'],auth_token=(root/'private/attention.token').read_text().strip()),timeout=360)
  reference=probe['reference'];errors=[]
  for field,values in reference['probabilities'].items():
   converted={key:value**reference['temperature'] for key,value in values.items()};total=sum(converted.values())
   errors.extend(abs(value/total-result['prediction']['probabilities'][field][key]) for key,value in converted.items())
  record=dict(policy=probe['policy'],maximum_probability_error=max(errors),reference=reference,result=result)
  final_qualification.append(record)
  (campaign/'FINAL_QUALIFICATION.json').write_text(json.dumps(final_qualification,indent=2))
  if result['input_prompt_sha256']!=reference['prompt_sha256'] or max(errors)>1e-4:raise RuntimeError('Final adapter qualification failed')
 status.update(stage='completed',ended_at=time.time())
except Exception:status.update(stage='failed',error=traceback.format_exc(),ended_at=time.time())
if bridge is not None:
 stop_session(bridge_owner)
 try:bridge.wait(timeout=5)
 except subprocess.TimeoutExpired:pass
 (root/'attention-r9.sock').unlink(missing_ok=True)
save();print(json.dumps(status),flush=True)
