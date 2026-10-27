from pathlib import Path
import json,os,re,shlex,subprocess,time,hashlib
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request,AuthorizedSession
from colab_cli.client import Client,Prod
from colab_cli.consumption import format_consumption_status
from remote_transport import DIAL
R=Path(__file__).parent
assert not (R/'r11-resource-plan.json').exists()
parent=json.loads((R/'r9-resource-plan.json').read_text())
assert parent['stop_by']-time.time()>4500
for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:os.environ[k]='http://127.0.0.1:9682'
class Session(AuthorizedSession):
 def request(self,*a,**k):k.setdefault('timeout',30);return super().request(*a,**k)
scopes=['openid','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/userinfo.profile','https://www.googleapis.com/auth/colaboratory']
c=Credentials.from_authorized_user_info(json.loads((Path.home()/'.config/colab-cli/token.json').read_text()),scopes=scopes);c.refresh(Request());api=Client(Prod(),Session(c));assert not api.list_assignments(),'Inspect any account allocation before provisioning'
match=re.search(r'Current balance:\s*([\d.]+)',format_consumption_status(api.get_consumption_user_info()));assert match
balance=float(match.group(1));remaining=parent['compute_cap']-(parent['starting_balance']-balance);assert remaining>3
plan=dict(created_at=time.time(),stop_by=parent['stop_by'],starting_balance=parent['starting_balance'],compute_cap=parent['compute_cap'],observed_balance=balance,remaining_parent_compute_units=remaining,parent_resource_plan='r9-resource-plan.json',parent_semantic_sha256=hashlib.sha256(json.dumps(parent,sort_keys=True,separators=(',',':')).encode()).hexdigest(),remaining_workflows=9,prior_native_starts=279,required_native_preflight_starts=1,maximum_additional_native_starts=361,maximum_per_workflow=12,maximum_concurrent_native=6,maximum_parallel_workflows=1,minimum_gap_between_workflows_seconds=90,owned_assignment_count_before_allocation=0,scope='Replacement runtime for the nine original unstarted IDs; unchanged R9 parent hard deadline and aggregate 55-CU ceiling. Preserve all 55 earlier attempts. No training or checkpoint change.')
body=json.dumps(plan,indent=2)+'\n';(R/'r11-resource-plan.json').write_text(body)
code="""from pathlib import Path
import sys,json,hashlib
r=Path('/home/simjecture/investigations/scientific-attention-20261025');body=sys.stdin.read();v=json.loads(body);parent=json.loads((r/'r9-resource-plan.json').read_text())
assert hashlib.sha256(json.dumps(parent,sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['parent_semantic_sha256']
assert all(v[k]==parent[k] for k in ['stop_by','starting_balance','compute_cap'])
assert json.loads((r/'r10-guard-status.json').read_text())['stage']=='released'
p=r/'r11-resource-plan.json';assert not p.exists();p.write_text(body);print('Replacement plan saved; no GPU allocated and parent bounds unchanged')
"""
x=subprocess.run(DIAL+['python3 -c '+shlex.quote(code)],input=body,capture_output=True,text=True,timeout=45);x.check_returncode();print(json.dumps(plan));print(x.stdout)
