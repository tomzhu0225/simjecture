"""US allocation only; ephemeral handoff then all model traffic remains off-host."""
from pathlib import Path
import datetime,hashlib,json,os,re,shlex,subprocess,time,uuid
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request,AuthorizedSession
from colab_cli.client import Client,Prod,Variant,Accelerator,Shape,Assignment,PostAssignmentResponse
from colab_cli.state import SessionState
from colab_cli.consumption import format_consumption_status
from remote_transport import DIAL
R=Path(__file__).parent;REMOTE='/home/simjecture/investigations/scientific-attention-20261025'
status_file=R/'r11-local-allocation-http2-retry01-status.json';assert not status_file.exists()
status=dict(stage='preflight',started_at=time.time());api=None;owned=None;handed=False
os.umask(0o077)
for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:os.environ[k]='http://127.0.0.1:9682'
def save():
 p=status_file.with_suffix('.tmp');p.write_text(json.dumps(status,indent=2));p.replace(status_file)
class Session(AuthorizedSession):
 def request(self,*a,**k):k.setdefault('timeout',120);return super().request(*a,**k)
save()
try:
 # Prove registration and source readiness before obtaining a paid runtime.
 check="from pathlib import Path;import json,hashlib;r=Path('/home/simjecture/investigations/scientific-attention-20261025');p=json.loads((r/'r11-phase-plan.json').read_text());assert p['retained_started']==55 and p['unstarted']==9;assert json.loads((r/'r10-guard-status.json').read_text())['stage']=='released';assert not (r/'r11-launch-status.json').exists();assert all(hashlib.sha256((r/n).read_bytes()).hexdigest()==h for n,h in p['orchestration_sha256'].items());print('registered-ready')"
 verified=subprocess.run(DIAL+['python3 -c '+shlex.quote(check)],capture_output=True,text=True,timeout=45)
 assert verified.returncode==0 and verified.stdout.strip()=='registered-ready','Registration must be verified before allocation'
 scopes=['openid','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/userinfo.profile','https://www.googleapis.com/auth/colaboratory']
 c=Credentials.from_authorized_user_info(json.loads((Path.home()/'.config/colab-cli/token.json').read_text()),scopes=scopes);c.refresh(Request())
 assert c.granted_scopes is None or not set(c.granted_scopes)-set(scopes)
 api=Client(Prod(),Session(c));assert not api.list_assignments(),'Inspect an existing account allocation before provisioning'
 match=re.search(r'Current balance:\s*([\d.]+)',format_consumption_status(api.get_consumption_user_info()));assert match
 balance=float(match.group(1));parent=json.loads((R/'r11-resource-plan.json').read_text());assert parent['compute_cap']-(parent['starting_balance']-balance)>3
 notebook=uuid.uuid4();status.update(stage='allocating',notebook=str(notebook),balance=balance);save()
 challenge=api._get_assignment(notebook,Variant.GPU,Accelerator.A100,Shape.HIGH_RAM)
 if isinstance(challenge,Assignment):result=challenge
 else:
  url=api._build_assign_url(notebook,Variant.GPU,Accelerator.A100,Shape.HIGH_RAM)+'&authuser=0'
  entries=[('url',url),('proxy','http://127.0.0.1:9682'),('request','POST'),('header','Accept: application/json'),('header','Content-Length: 0'),('header','X-Colab-Client-Agent: colab-cli'),('header','X-Goog-Colab-Token: '+challenge.token),('header','Authorization: Bearer '+c.token)]
  config='\n'.join(k+' = '+json.dumps(v) for k,v in entries)+'\n'
  started=time.time()
  response=subprocess.run(['curl','--config','-','--http2','--silent','--show-error','--max-time','120','--write-out','\n%{http_code}\n%{http_version}'],input=config,capture_output=True,text=True,timeout=125)
  body,http_code,http_version=response.stdout.rsplit('\n',2)
  status['assignment_http']=dict(method='POST',host='colab.research.google.com',path='/tun/m/assign',started_at=started,ended_at=time.time(),curl_returncode=response.returncode,http_status=http_code,http_version=http_version,error_summary=response.stderr.replace(c.token,'[REDACTED]').replace(challenge.token,'[REDACTED]')[-512:],error_markers=[m for m in ['timed out','Connection reset','HTTP/2 stream','Empty reply','SSL_ERROR','CONNECT tunnel failed'] if m in response.stderr]);save()
  if response.returncode or http_code!='200':raise RuntimeError('Assignment HTTP transport failed; inspect sanitized status')
  decoded=json.loads(api._strip_xssi_prefix(body));owned=decoded.get('endpoint')
  result=PostAssignmentResponse.model_validate(decoded)
 owned=result.endpoint;info=result.runtime_proxy_info
 session=SessionState(name='simjecture-science-20261027e',token=info.token,url=info.url,endpoint=owned,token_expires_at=info.expires_at(),variant='GPU',accelerator='A100',machine_shape='HIGH_RAM')
 lease=dict(created_at=time.time(),stop_by=parent['stop_by'],session=session.name,endpoint=owned,starting_balance=parent['starting_balance'],observed_balance=balance,compute_cap=parent['compute_cap'],parent_lease='r11-resource-plan.json',scope='Continuation of nine unstarted original scientific workflows; 55 earlier attempts preserved; unchanged R9 parent deadline and aggregate spending ceiling')
 assert lease['stop_by']-time.time()>900
 (R/'r11-lease.json').write_text(json.dumps(lease,indent=2))
 with (R/'r11-local-guard.log').open('w') as log:guard=subprocess.Popen([__import__('sys').executable,'-u',str(R/'local_r11_failsafe.py')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 status.update(stage='handing_off',endpoint=owned,local_guard_pid=guard.pid);save()
 access=dict(token=c.token,expiry=c.expiry.isoformat(),minted_at=time.time(),scopes=c.granted_scopes or scopes)
 payload=dict(session=json.loads(session.model_dump_json()),lease=lease,access=access)
 program="""from pathlib import Path
import json,sys,os,subprocess,time
r=Path('/home/simjecture/investigations/scientific-attention-20261025');private=r/'private';os.umask(0o077);v=json.load(sys.stdin)
for name in ['r11-lease.json','r11-handoff.json','r11-allocation-status.json','r11-transport-commission','STOP_R11_COLAB']:assert not (r/name).exists(),name
for path,value in [(r/'r11-lease.json',v['lease']),(private/'r11-session.json',v['session']),(private/'colab-access.json',v['access'])]:
 t=path.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2));t.chmod(0o600);t.replace(path)
with (r/'r11-guard.log').open('w') as log:g=subprocess.Popen([str(r/'colab-control-env/bin/python'),'-u',str(r/'remote_r11_guard.py')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
time.sleep(.2);assert g.poll() is None
receipt=dict(at=time.time(),endpoint=v['session']['endpoint'],guard_pid=g.pid,session=v['session']['name']);(r/'r11-handoff.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
"""
 x=subprocess.run(DIAL+['python3 -c '+shlex.quote(program)],input=json.dumps(payload),capture_output=True,text=True,timeout=55)
 assert x.returncode==0,'Ephemeral handoff failed'
 receipt=json.loads(x.stdout);assert receipt['endpoint']==owned;handed=True
 status.update(stage='guarded',remote_guard_pid=receipt['guard_pid']);save()
 controls=subprocess.run([__import__('sys').executable,str(R/'install_r11_controls.py')],capture_output=True,text=True,timeout=55)
 assert controls.returncode==0,'Bounded local control task installation failed; inspect guarded runtime'
 status['scheduled_control_installed']=True;save()
 launch="import runpy;runpy.run_path('/home/simjecture/investigations/scientific-attention-20261025/start_r11_phase.py',run_name='__main__')"
 x=subprocess.run(DIAL+['python3 -c '+shlex.quote(launch)],capture_output=True,text=True,timeout=55)
 assert x.returncode==0,'Guarded runtime exists; inspect remote launch state before further action'
 launched=json.loads(x.stdout);assert launched['stage']=='running';(R/'r11-launch.json').write_text(json.dumps(launched,indent=2));status.update(stage='running',pids=launched['pids'],stop_by=lease['stop_by']);save()
except Exception as e:
 status.update(stage='failed',error_type=type(e).__name__,handoff_confirmed=handed,endpoint=owned,ended_at=time.time());save()
 if owned and not handed:
  try:
   api.unassign(owned);assert not any(a.endpoint==owned for a in api.list_assignments());status['owned_released']=True
  except Exception as cleanup:status['release_error_type']=type(cleanup).__name__
  save()
print(json.dumps(status),flush=True)
