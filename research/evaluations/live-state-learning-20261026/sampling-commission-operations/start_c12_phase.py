"""Launch only a registered, fresh bounded model/native commissioning phase."""
from pathlib import Path
import hashlib,json,subprocess,time,os,traceback
R=Path('/home/simjecture/investigations/scientific-attention-20261025')
S=R/'workflow-return-source-171ac44'
read=lambda p:json.loads(p.read_text())
for n in ['native-budget-c12.json','c12-launch-status.json']:assert not (R/n).exists(),n
lease=read(R/'c12-lease.json');phase=read(R/'c12-phase-plan.json')
assert lease['stop_by']==read(R/'c12-resource-plan.json')['stop_by']
assert read(R/'c12-auth-01/STATUS.json')['stage']=='completed'
assert read(R/'c12-physics/STATUS.json')['stage']=='completed'
assert all(s.get('ended_at') is not None for s in read(R/'control-commission-02/native-budget.json')['starts'])
for n,h in phase['orchestration_sha256'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
assert not (R/'parked-commission-c12/CAMPAIGN.json').exists()
budget=dict(deadline=lease['stop_by']-120,maximum_starts=72,maximum_per_continuation=12,maximum_concurrent=6,executable='/home/simjecture/.local/bin/codex-ggdd',starts=[],scope='Six new commissioning episodes; one authentication start was used separately; total ceiling 73')
(R/'native-budget-c12.json').write_text(json.dumps(budget,indent=2)+'\n')
state=dict(stage='launching',started_at=time.time(),pids={})
def save():
 p=R/'c12-launch-status.tmp';p.write_text(json.dumps(state,indent=2));p.replace(R/'c12-launch-status.json')
env=dict(os.environ,PYTHONPATH=str(S/'src')+':'+str(S/'packages/simjecture-monitor/src'),OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
try:
 for name,python in [('deploy_c12_a100.py','/usr/bin/python3'),('run_c12_sampling.py',str(R/'control-commission-env/bin/python')),('attach_c12.py',str(R/'colab-control-env/bin/python'))]:
  with (R/(name+'.log')).open('x') as log:p=subprocess.Popen([python,'-u',str(R/name)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  state['pids'][name]=p.pid;save()
 state.update(stage='running',launched_at=time.time(),lease=lease)
except Exception:
 state.update(stage='failed',error=traceback.format_exc(),ended_at=time.time());(R/'STOP_C12_COLAB').write_text('Startup failed; release owned runtime.\n')
save();print(json.dumps(state),flush=True)
