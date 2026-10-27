from pathlib import Path
import json,os,re,shlex,subprocess,time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request,AuthorizedSession
from colab_cli.client import Client,Prod
from colab_cli.consumption import format_consumption_status
from remote_transport import DIAL
R=Path(__file__).parent
assert not (R/'r9-resource-plan.json').exists()
for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:os.environ[k]='http://127.0.0.1:9682'
class Session(AuthorizedSession):
 def request(self,*a,**k):k.setdefault('timeout',30);return super().request(*a,**k)
scopes=['openid','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/userinfo.profile','https://www.googleapis.com/auth/colaboratory']
c=Credentials.from_authorized_user_info(json.loads((Path.home()/'.config/colab-cli/token.json').read_text()),scopes=scopes);c.refresh(Request());api=Client(Prod(),Session(c))
assignments=api.list_assignments();assert not assignments,'Inspect existing account allocations before any new lease'
match=re.search(r'Current balance:\s*([\d.]+)',format_consumption_status(api.get_consumption_user_info()));assert match
balance=float(match.group(1));assert balance>55
start=time.time();plan=dict(created_at=start,stop_by=start+28800,starting_balance=balance,compute_cap=55,remaining_workflows=26,prior_native_starts=170,required_native_preflight_starts=1,maximum_additional_native_starts=470,maximum_per_workflow=12,maximum_concurrent_native=6,maximum_parallel_workflows=1,minimum_gap_between_workflows_seconds=90,owned_assignment_count_before_allocation=0,scope='New bounded continuation after the prior owned runtime was released; preserve all 38 attempted outcomes and execute only the 26 unstarted original IDs. No training or checkpoint change.')
(R/'r9-resource-plan.json').write_text(json.dumps(plan,indent=2))
code="from pathlib import Path;import sys,json;r=Path('/home/simjecture/investigations/scientific-attention-20261025');assert json.loads((r/'r7-guard-status.json').read_text())['stage']=='released';p=r/'r9-resource-plan.json';assert not p.exists();p.write_bytes(sys.stdin.buffer.read());print('Fresh bounded resource plan saved; no runtime allocated')"
x=subprocess.run(DIAL+['python3 -c '+shlex.quote(code)],input=json.dumps(plan),capture_output=True,text=True,timeout=45);x.check_returncode();print(json.dumps(plan));print(x.stdout)
