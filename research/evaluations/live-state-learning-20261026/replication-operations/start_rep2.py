from pathlib import Path
import hashlib,json,os,re,subprocess,time,traceback
from rep2_colab_control import ROOT,client,credentials
from colab_cli.consumption import format_consumption_status
R=ROOT
for name in ['rep2-lease.json','native-budget-rep2.json','rep2-allocation-status.json','base-sft-replication-v2','STOP_REP2_COLAB']:
 assert not (R/name).exists(),'An execution resource already exists: '+name
assert json.loads((R/'replication-auth-01/STATUS.json').read_text())['stage']=='completed'
auth=json.loads((R/'replication-native-preflight-budget.json').read_text());assert len(auth['starts'])==1 and auth['starts'][0]['returncode']==0 and auth['starts'][0]['ended_at'] is not None
plan=json.loads((R/'rep2-phase-plan.json').read_text())
for name,expected in plan['orchestration_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==expected,name
assert not plan['model_qualification_pending']
assert credentials()[1]-time.time()>1800
api=client();assert not api.list_assignments(),'Account already has an allocation; inspect ownership'
m=re.search(r'Current balance:\s*([\d.]+)',format_consumption_status(api.get_consumption_user_info()));assert m
balance=float(m.group(1));assert balance>=100,'Insufficient current balance for registered phase ceiling'
prior=json.loads((R/'replication-lease.json').read_text());assert time.time()+6000<prior['stop_by']
assert json.loads((R/'replication-guard-status.json').read_text())['stage']=='released'
assert not json.loads((R/'native-budget-replication.json').read_text())['starts']
lease=dict(created_at=time.time(),stop_by=prior['stop_by'],recovery_of='replication-lease.json',session='simjecture-science-20261026n',starting_balance=prior['starting_balance'],observed_balance=balance,compute_cap=prior['compute_cap'],scope='Registered repeated base/SFT scientific workflows; separate phase from the closed original cycle',phase_plan_sha256=hashlib.sha256((R/'rep2-phase-plan.json').read_bytes()).hexdigest())
(R/'rep2-lease.json').write_text(json.dumps(lease,indent=2))
pids={};status=dict(stage='connecting_physics',started_at=time.time(),pids=pids)
def save():
 p=R/'rep2-launch-status.tmp';p.write_text(json.dumps(status,indent=2));p.replace(R/'rep2-launch-status.json')
save()
try:
 profile=json.loads(Path('/home/simjecture/investigations/current-injection-smr-20261015/machines/profiles/p40-smr.json').read_text())['machine']
 assert hashlib.sha256(Path('/home/simjecture/investigations/current-injection-smr-20261015/machines/profiles/p40-smr.json').read_bytes()).hexdigest()==json.loads((R/'rep2-resource-preflight.json').read_text())['remote_profile_sha256']
 sock=R/'private/p40-rep2.sock';assert not sock.exists()
 command=['timeout',str(int(lease['stop_by']-time.time())),'ssh','-M','-S',str(sock),'-N','-o','BatchMode=yes','-o','ConnectTimeout=20','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+profile['known_hosts'],'-o','IdentitiesOnly=yes','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','-o','StreamLocalBindMask=0177','-i',profile['identity_file'],'-p',str(profile['port']),profile['user']+'@'+profile['host']]
 with (R/'rep2-p40-master.log').open('w') as log:master=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 pids['p40_master']=master.pid;save()
 for _ in range(30):
  if master.poll() is not None:raise RuntimeError('P40 master stopped before readiness')
  if sock.exists():
   x=subprocess.run(['ssh','-S',str(sock),'-O','check',profile['user']+'@'+profile['host']],capture_output=True,timeout=5)
   if x.returncode==0:break
  time.sleep(1)
 else:raise TimeoutError('P40 master not ready')
 budget=dict(deadline=lease['stop_by']-120,maximum_starts=639,maximum_per_continuation=12,maximum_concurrent=6,executable='/home/simjecture/.local/bin/codex-ggdd',starts=[],parent_prior_starts=1,preflight_budget_sha256=hashlib.sha256((R/'replication-native-preflight-budget.json').read_bytes()).hexdigest(),scope='639 workflow starts plus one recorded preflight within the 640-start phase')
 (R/'native-budget-rep2.json').write_text(json.dumps(budget,indent=2))
 status['stage']='launching';save()
 for filename,python in [('deploy_rep2_a100.py','/usr/bin/python3'),('run_base_sft_rep2.py',str(R/'replication-env/bin/python')),('finish_rep2.py','/usr/bin/python3'),('allocate_rep2.py',str(R/'colab-control-env/bin/python'))]:
  with (R/(filename+'.log')).open('w') as log:p=subprocess.Popen([python,'-u',str(R/filename)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  pids[filename]=p.pid;save()
 status.update(stage='running',launched_at=time.time(),lease=lease);save()
except Exception as error:
 status.update(stage='failed',error_type=type(error).__name__,error=traceback.format_exc(),ended_at=time.time());save()
 (R/'STOP_REP2_COLAB').write_text('Workflow launch failed; preserve records and release owned allocation.\n')
print(json.dumps(status),flush=True)
