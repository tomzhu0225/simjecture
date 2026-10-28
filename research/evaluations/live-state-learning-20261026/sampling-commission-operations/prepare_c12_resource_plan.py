"""Read the live Colab account and register a new bounded commissioning lease."""
from pathlib import Path
import json,os,re,shlex,subprocess,time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request,AuthorizedSession
from colab_cli.client import Client,Prod
from colab_cli.consumption import format_consumption_status
from remote_transport import DIAL
r=Path(__file__).parent
assert not (r/'c12-resource-plan.json').exists()
for key in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:os.environ[key]='http://127.0.0.1:9682'
class Session(AuthorizedSession):
 def request(self,*args,**kwargs):kwargs.setdefault('timeout',30);return super().request(*args,**kwargs)
scopes=['openid','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/userinfo.profile','https://www.googleapis.com/auth/colaboratory']
c=Credentials.from_authorized_user_info(json.loads((Path.home()/'.config/colab-cli/token.json').read_text()),scopes=scopes);c.refresh(Request())
api=Client(Prod(),Session(c));assignments=api.list_assignments()
assert not assignments,'Existing allocation requires inspection before provisioning'
match=re.search(r'Current balance:\s*([\d.]+)',format_consumption_status(api.get_consumption_user_info()));assert match
balance=float(match.group(1));assert balance>20
plan=dict(created_at=time.time(),stop_by=time.time()+7200,starting_balance=balance,compute_cap=20,maximum_native_starts=73,authentication_preflight_starts=1,maximum_per_workflow=12,maximum_concurrent_native=6,maximum_parallel_workflows=1,minimum_gap_seconds=90,maximum_workflows=6,optimizer_updates=0,owned_assignment_count_before_allocation=0,scope='New native sampling commissioning only; frozen Conjecture 1 continued-SFT weights, constrained route/question decoder at temperature 1, qualified task_protocol host with 12 parent turns. No efficacy claim or training export.')
body=json.dumps(plan,indent=2)+'\n';(r/'c12-resource-plan.json').write_text(body)
code="from pathlib import Path;import sys;p=Path('/home/simjecture/investigations/scientific-attention-20261025/c12-resource-plan.json');assert not p.exists();p.write_text(sys.stdin.read());print('Registered new resource ceiling; no GPU allocation')"
p=subprocess.run(DIAL+['python3 -c '+shlex.quote(code)],input=body,capture_output=True,text=True,timeout=45)
print(p.stdout);print(p.stderr[-1000:]);assert p.returncode==0
print(json.dumps(plan),flush=True)
