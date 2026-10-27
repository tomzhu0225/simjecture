"""Preserve started/unstarted coverage, audit every attempted trial, release owned GPU."""
from pathlib import Path
import json,hashlib,subprocess,shlex,time,traceback
R=Path('/home/simjecture/investigations/scientific-attention-20261025');campaign=R/'base-sft-replication-v3';status=dict(stage='waiting',started_at=time.time())
def read(p):return json.loads(p.read_text())
def save():
 p=R/'r7-finalizer-status.tmp';p.write_text(json.dumps(status,indent=2));p.replace(R/'r7-finalizer-status.json')
save()
try:
 while time.time()<read(R/'r7-lease.json')['stop_by']+90:
  p=campaign/'CAMPAIGN.json';deploy=R/'r7-deploy-status.json'
  if p.exists() and read(p)['stage'] in ['completed','failed']:break
  if deploy.exists() and read(deploy)['stage']=='failed':break
  time.sleep(15)
 original=read(R/'r7-workflow-manifest.json')
 result=read(campaign/'CAMPAIGN.json') if (campaign/'CAMPAIGN.json').exists() else dict(stage='unstarted',blocks=[])
 started={t['id'] for b in result['blocks'] for t in b['trials']};blocks=[]
 for block in original['blocks']:
  selected=[t for t in block['trials'] if t['id'] in started]
  if selected:blocks.append(block|dict(trials=selected))
 coverage=dict(planned_workflows=original['workflows'],started_workflows=len(started),complete_blocks=sum(len(b['trials'])==4 for b in blocks),unstarted=[t for b in original['blocks'] for t in b['trials'] if t['id'] not in started],campaign_stage=result['stage'],stop_reason=result.get('stop_reason'),infrastructure_failures=result.get('infrastructure_failures',[]))
 (R/'r7-coverage.json').write_text(json.dumps(coverage,indent=2));status.update(stage='auditing',coverage=coverage);save()
 if started:
  selected=R/'r7-started-manifest.json';selected.write_text(json.dumps(original|dict(blocks=blocks,workflows=len(started)),indent=2))
  present=[a for a in original['arms'] if any(t['arm']==a for b in blocks for t in b['trials'])]
  source=R/'replication-source-04f905c/packages/simjecture-monitor/scripts'
  args=[str(R/'replication-env/bin/python'),str(source/'audit_scientific_workflows.py'),'--root',str(campaign),'--manifest',str(selected),'--budget',str(R/'native-budget-r7.json'),'--output',str(R/'r7-audit'),'--learned-arm','continued_sft' if 'continued_sft' in present else present[0]]
  for arm in present:args+=['--arm',arm]
  with (R/'r7-audit.log').open('w') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
  with (R/'r7-summary.log').open('w') as log:subprocess.run(['/usr/bin/python3',str(R/'summarize_base_sft_r7.py'),'--manifest',str(R/'r7-workflow-manifest.json'),'--audit',str(R/'r7-audit'),'--output',str(R/'r7-summary.json')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
 if started:
  with (R/'r7-combined-audit.log').open('w') as log:subprocess.run(['/usr/bin/python3',str(R/'combine_base_sft_phases.py'),'--root',str(R),'--new-audit',str(R/'r7-audit'),'--new-campaign',str(campaign),'--output',str(R/'r7-combined-summary.json')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
 status.update(stage='completed',ended_at=time.time())
except Exception:status.update(stage='failed',error=traceback.format_exc(),ended_at=time.time())
finally:
 ssh=['ssh','-S',str(R/'private/r7-a100.sock'),'-o','ControlMaster=no','-o','ProxyCommand=false','-o','BatchMode=yes','root@colab-r7']
 for name in ['r7-prepare-status.json','r7-service-status.json','r7-service-controller.json']:
  try:
   x=subprocess.run(ssh+['cat '+shlex.quote('/content/science-attention/'+name)],capture_output=True,timeout=15)
   if x.returncode==0:(R/('saved-'+name)).write_bytes(x.stdout)
  except subprocess.TimeoutExpired:pass
 save();(R/'STOP_R7_COLAB').write_text('Workflow collection terminal; outcomes retained on coordinator.\n')
print(json.dumps(status),flush=True)
