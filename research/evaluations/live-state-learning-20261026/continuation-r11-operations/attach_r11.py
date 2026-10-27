from pathlib import Path
import json,os,subprocess,time,uuid
from colab_cli.client import Accelerator,Variant,Shape
from colab_cli.state import SessionState
from r11_colab_control import ROOT,PRIVATE,client,credentials,BoundedSession
from colab_cli.client import Client,Prod
from google.oauth2.credentials import Credentials
class AllocationSession(BoundedSession):
 def request(self,*args,**kwargs):
  kwargs.setdefault('timeout',120)
  return super().request(*args,**kwargs)
os.umask(0o077)
status_path=ROOT/'r11-allocation-status.json'
if status_path.exists():raise RuntimeError('Existing allocation record; inspect rather than allocate twice')
lease=json.loads((ROOT/'r11-lease.json').read_text())
status=dict(stage='preflight',at=time.time(),name=lease['session'])
def save():status_path.write_text(json.dumps(status,indent=2))
save()
try:
 session=SessionState.model_validate_json((PRIVATE/'r11-session.json').read_text())
 assert session.name==lease['session'] and session.endpoint==lease['endpoint']
 handoff=json.loads((ROOT/'r11-handoff.json').read_text())
 status.update(stage='assigned_guarded',endpoint=session.endpoint,guard_pid=handoff['guard_pid']);save()
 python=ROOT/'colab-control-env/bin/python'
 key=PRIVATE/'colab-r11'
 if not key.exists():subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
 sock=PRIVATE/'r11-a100.sock'
 if sock.exists():raise RuntimeError('Existing recovery master socket; inspect before replacing')
 command=['timeout',str(max(1,int(lease['stop_by']-time.time()))),'ssh','-M','-S',str(sock),'-N','-o','BatchMode=yes','-o','ConnectTimeout=160','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(PRIVATE/'r11-known-hosts'),'-o','HostKeyAlias='+lease['session'],'-o','IdentitiesOnly=yes','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','-o','ExitOnForwardFailure=yes','-o','StreamLocalBindMask=0177','-i',str(key),'-o','ProxyCommand='+str(python)+' '+str(ROOT/'remote_r11_proxy.py'),'-L',str(ROOT/'private/r11-link.sock')+':/content/science-attention/attention.sock','root@colab-r11']
 link_plan=dict(status=str(ROOT/'r11-link-status.json'),control_socket=str(sock),forward_socket=str(ROOT/'private/r11-link.sock'),lease=str(ROOT/'r11-lease.json'),stop_file=str(ROOT/'STOP_R11_COLAB'),log=str(ROOT/'r11-master.log'),destination='root@colab-r11',command=command)
 (ROOT/'r11-link-plan.json').write_text(json.dumps(link_plan,indent=2))
 with (ROOT/'r11-link-supervisor.log').open('w') as log:supervisor=subprocess.Popen([str(ROOT/'replication-env/bin/python'),'-u',str(ROOT/'supervise_attention_link.py'),'--plan',str(ROOT/'r11-link-plan.json')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 status.update(stage='connecting',master_supervisor_pid=supervisor.pid,master_socket=str(sock));save()
 for _ in range(60):
  if supervisor.poll() is not None:raise RuntimeError('Owned-link supervisor stopped before readiness')
  link=ROOT/'r11-link-status.json'
  if link.exists():
   value=json.loads(link.read_text())
   if value['stage']=='failed':raise RuntimeError('Owned-link supervisor failed')
   if value['stage']=='ready':break
  time.sleep(2)
 else:raise TimeoutError('Owned runtime link not ready within bound')
 status.update(stage='ready',ready_at=time.time());save()
except Exception as error:
 status.update(stage='failed',error_type=type(error).__name__,at=time.time());save()
 (ROOT/'STOP_R11_COLAB').write_text('Owned runtime attachment failed.\n')
print(json.dumps(status),flush=True)
