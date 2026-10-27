from pathlib import Path
import json,subprocess,sys,shlex
from remote_transport import DIAL
R=Path(__file__).parent
code='''from pathlib import Path
import json,subprocess,time,shlex
r=Path('/home/simjecture/investigations/scientific-attention-20261025');out={'at':time.time()};pids={}
for n in ['r11-guard-status.json','r11-allocation-status.json','r11-deploy-status.json','r11-link-status.json','base-sft-replication-v7/CAMPAIGN.json']:
 p=r/n
 if p.exists():
  v=json.loads(p.read_text());out[n]={k:v[k] for k in ('stage','started_at','ended_at','at','balance','credential_expires','master_supervisor_pid','runtime_processes','current_pid','stop_reason','error','blocks','next_trial','adapter_qualification') if k in v}
  for key in ['master_supervisor_pid','current_pid','bridge_pid']:
   if v.get(key):pids[n+':'+key]=v[key]
for name,pid in json.loads((r/'r11-launch-status.json').read_text())['pids'].items():pids[name]=pid
pids['guard']=json.loads((r/'r11-handoff.json').read_text())['guard_pid']
out['processes']={name:{'pid':pid,'exists':Path('/proc',str(pid)).exists()} for name,pid in pids.items()}
v=json.loads((r/'native-budget-r11.json').read_text());out['native']={'starts':len(v['starts']),'active':sum(x.get('ended_at') is None for x in v['starts'])}
records=[]
for p in sorted((r/'base-sft-replication-v7').glob('*/OUTCOME.json')):
 v=json.loads(p.read_text());records.append({'id':p.parent.name,**{k:v[k] for k in ('whole_workflow_verified','verified_complete','elapsed_seconds','stage','family','arm') if k in v}})
out['outcomes']=records
s=r/'private/r11-a100.sock'
if s.exists():
 program="from pathlib import Path;import json,subprocess;r=Path('/content/science-attention');v={n:json.loads((r/n).read_text()) for n in ['r11-prepare-status.json','r11-service-controller.json','r11-service-status.json'] if (r/n).exists()};v['gpu']=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used','--format=csv,noheader'],capture_output=True,text=True,timeout=5).stdout.strip();print(json.dumps(v))"
 try:
  x=subprocess.run(['ssh','-S',str(s),'-o','ControlMaster=no','-o','ProxyCommand=false','-o','BatchMode=yes','root@colab-r11','python3 -c '+shlex.quote(program)],capture_output=True,text=True,timeout=15)
  if x.returncode==0:
   v=json.loads(x.stdout);out['runtime']={n:({k:value[k] for k in ('stage','started_at','ended_at','pid','error') if k in value} if isinstance(value,dict) else value) for n,value in v.items()}
  else:out['runtime_query_returncode']=x.returncode
 except subprocess.TimeoutExpired:out['runtime_observation']='SSH read timeout; not a terminal state'
print(json.dumps(out))
'''
x=subprocess.run(DIAL+['python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=45);x.check_returncode();v=json.loads(x.stdout);(R/'r11-live-status.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v,indent=2))
