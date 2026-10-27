from pathlib import Path
import hashlib,json,subprocess,time,traceback
R=Path('/home/simjecture/investigations/scientific-attention-20261025')
for n in ['native-budget-r10.json','r10-launch-status.json','base-sft-replication-v6']:assert not (R/n).exists(),n
lease=json.loads((R/'r10-lease.json').read_text());plan=json.loads((R/'r10-phase-plan.json').read_text())
assert lease['stop_by']==json.loads((R/'r10-resource-plan.json').read_text())['stop_by']
assert json.loads((R/'r10-transport-qualification/STATUS.json').read_text())['stage']=='completed'
auth=json.loads((R/'r10-native-preflight-budget.json').read_text());assert len(auth['starts'])==1 and auth['starts'][0]['returncode']==0 and auth['starts'][0]['ended_at'] is not None
for name,count in [('native-budget-r7.json',125),('native-budget-r8.json',38),('native-budget-r9.json',51)]:
 old=json.loads((R/name).read_text());assert len(old['starts'])==count and all(x.get('ended_at') is not None for x in old['starts'])
assert plan['prior_native_starts_including_this_preflight']==223
for n,h in plan['orchestration_sha256'].items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
assert hashlib.sha256((Path.home()/'.ssh/config').read_bytes()).hexdigest()==plan['ssh_config_sha256']
pids={};status=dict(stage='launching',started_at=time.time(),pids=pids)
def save():
 p=R/'r10-launch-status.tmp';p.write_text(json.dumps(status,indent=2));p.replace(R/'r10-launch-status.json')
save()
try:
 budget=dict(deadline=lease['stop_by']-120,maximum_starts=417,maximum_per_continuation=12,maximum_concurrent=6,executable='/home/simjecture/.local/bin/codex-ggdd',starts=[],parent_prior_starts=223,scope='417 remaining starts after 222 retained prior starts and one R10 preflight; original cohort ceiling 640')
 (R/'native-budget-r10.json').write_text(json.dumps(budget,indent=2))
 for name,python in [('deploy_r10_a100.py','/usr/bin/python3'),('run_base_sft_r10.py',str(R/'replication-env/bin/python')),('finish_r10.py','/usr/bin/python3'),('attach_r10.py',str(R/'colab-control-env/bin/python'))]:
  with (R/(name+'.log')).open('w') as log:p=subprocess.Popen([python,'-u',str(R/name)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  pids[name]=p.pid;save()
 status.update(stage='running',launched_at=time.time(),lease=lease);save()
except Exception as e:
 status.update(stage='failed',error_type=type(e).__name__,error=traceback.format_exc(),ended_at=time.time());save();(R/'STOP_R10_COLAB').write_text('Continuation startup failed; preserve records and release owned runtime.\n')
print(json.dumps(status),flush=True)
