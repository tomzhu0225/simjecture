"""Bounded native sampling commission; no optimizer and no overwritten attempts."""
from pathlib import Path
import hashlib,json,os,subprocess,time,traceback,shlex
from simjecture_monitor.attention_server import request
from simjecture_monitor.native_guard import process_stat,stop_session
R=Path('/home/simjecture/investigations/scientific-attention-20261025')
S=R/'workflow-return-source-171ac44';C=R/'parked-commission-c12'
state=dict(stage='waiting_for_model',started_at=time.time());bridge=None;child=None
lease=json.loads((R/'c13-lease.json').read_text());deadline=lease['stop_by']-120
socket=R/'private/c13-link.sock'

def read(p):return json.loads(p.read_text())
def save():
 p=R/'c13-controller-status.tmp';p.write_text(json.dumps(state,indent=2));p.replace(R/'c13-controller-status.json')
def health():return request(socket,dict(operation='health',auth_token=(R/'private/attention.token').read_text().strip()),timeout=30)['status']
def predict(observation,policy):return request(socket,dict(observation=observation,policy=policy,auth_token=(R/'private/attention.token').read_text().strip()),timeout=360)
def probes(name):
 rows=[]
 for probe in read(R/'c13-probes.json'):
  value=predict(probe['observation'],probe['policy']);reference=probe['reference']
  errors=[]
  for field,values in reference['probabilities'].items():
   converted={k:v**reference['temperature'] for k,v in values.items()};total=sum(converted.values())
   errors.extend(abs(v/total-value['prediction']['probabilities'][field][k]) for k,v in converted.items())
  rows.append(dict(policy=probe['policy'],maximum_probability_error=max(errors),reference=reference,result=value))
  (R/name).write_text(json.dumps(rows,indent=2)+'\n')
  assert value['policy']==probe['policy'] and value['input_prompt_sha256']==reference['prompt_sha256']
  assert max(errors)<=1e-4
 return [dict(policy=v['policy'],maximum_probability_error=v['maximum_probability_error']) for v in rows]
save()
try:
 phase=read(R/'c13-phase-plan.json')
 for n,h in phase['orchestration_sha256'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
 for n,h in read(C/'PLAN.json')['source_files_sha256'].items():
  p=S/'src'/n[5:] if n.startswith('core/') else S/'packages/simjecture-monitor'/n
  assert hashlib.sha256(p.read_bytes()).hexdigest()==h,n
 assert hashlib.sha256((C/'PLAN.json').read_bytes()).hexdigest()==phase['assignment_plan_sha256']
 while time.time()<min(state['started_at']+1500,deadline-1750):
  if (R/'STOP_C13_COLAB').exists():raise RuntimeError('Owned runtime stopped before model readiness')
  try:
   ready=health()
   if ready['stage']=='ready':break
  except (OSError,RuntimeError,ValueError):pass
  time.sleep(10)
 else:raise TimeoutError('Model not ready within setup allowance')
 assert ready['temperature']==1.0 and ready['decision_distribution']=='scientific-route-question/v1'
 assert ready['model_identities']['continued_sft']['adapter_files_sha256']['adapter_model.safetensors']==phase['adapter_sha256']
 state.update(stage='qualifying_model',model_identities=ready['model_identities']);save()
 state['initial_qualification']=probes('c13-initial-probes.json');save()
 with (R/'c13-bridge.log').open('x') as log:
  bridge=subprocess.Popen(['/usr/bin/python3','-u',str(R/'attention_transport_r7.py'),'--socket',str(R/'attention-c13.sock'),'--upstream',str(R/'private/c13-link.sock'),'--log',str(R/'c13-transport.jsonl'),'--stop-by',str(deadline+100),'--request-seconds','24'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 owner=process_stat(bridge.pid)
 for _ in range(100):
  if bridge.poll() is not None:raise RuntimeError('Inference relay failed')
  if (R/'attention-c13.sock').exists():break
  time.sleep(.1)
 else:raise TimeoutError('Inference relay did not appear')
 socket=R/'attention-c13.sock'
 assert health()['model_identities']==state['model_identities']
 state.update(stage='collecting',bridge_pid=bridge.pid);save()
 env=dict(os.environ,PYTHONPATH=str(S/'src')+':'+str(S/'packages/simjecture-monitor/src'),PATH='/home/simjecture/.local/bin:'+os.environ.get('PATH',''),OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
 command=[str(R/'control-commission-env/bin/python'),str(S/'packages/simjecture-monitor/scripts/collect_workflow_returns.py'),'run','--root',str(C),'--budget',str(R/'native-budget-c13.json'),'--backend',str(R/'c12-backend.json'),'--socket',str(socket),'--auth-token-file',str(R/'private/attention.token'),'--wrapper',str(R/'c13-native-codex'),'--python',str(R/'control-commission-env/bin/python'),'--plasma-assets',str(R/'plasma')]
 with (R/'c13-collection.log').open('x') as log:
  child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  child_owner=process_stat(child.pid);state['collector_pid']=child.pid;save()
  child.wait(timeout=max(1,deadline-time.time()))
 state['collector_returncode']=child.returncode
 state['final_qualification']=probes('c13-final-probes.json')
 campaign=read(C/'CAMPAIGN.json');state['collection_export']=campaign.get('export');state['campaign_stage']=campaign['stage']
 state['unstarted_episodes']=campaign.get('unstarted_episodes')
 state.update(stage='completed' if campaign['stage']=='completed' and campaign.get('export',{}).get('collection_verified') else 'incomplete',ended_at=time.time())
except Exception:
 state.update(stage='failed',error=traceback.format_exc(),ended_at=time.time())
finally:
 if child is not None and child.poll() is None:
  stop_session(child_owner)
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:pass
 if bridge is not None:
  stop_session(owner)
  try:bridge.wait(timeout=10)
  except subprocess.TimeoutExpired:pass
 for _ in range(20):
  active=[s for s in read(R/'native-budget-c13.json')['starts'] if s.get('ended_at') is None]
  if not active:break
  time.sleep(1)
 state['native_starts']=len(read(R/'native-budget-c13.json')['starts']);state['native_active_at_finalization']=len(active)
 ssh=['ssh','-S',str(R/'private/c13-a100.sock'),'-o','ControlMaster=no','-o','ProxyCommand=false','-o','BatchMode=yes','root@colab-c13']
 for name in ['c13-prepare-status.json','c13-service-status.json','c13-service-controller.json']:
  try:
   p=subprocess.run(ssh+['cat '+shlex.quote('/content/science-attention/'+name)],capture_output=True,timeout=15)
   if p.returncode==0:(R/('c13-saved-'+name)).write_bytes(p.stdout)
  except subprocess.TimeoutExpired:pass
 save();(R/'STOP_C13_COLAB').write_text('Native sampling commission terminal; preserve records and release only its owned runtime.\n')
print(json.dumps(state),flush=True)
