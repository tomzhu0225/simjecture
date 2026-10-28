from pathlib import Path
import json,os,re,shlex,subprocess,time,hashlib
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request,AuthorizedSession
from colab_cli.client import Client,Prod
from colab_cli.consumption import format_consumption_status
from remote_transport import DIAL
r=Path(__file__).parent;parent=json.loads((r/'c12-resource-plan.json').read_text());assert parent['stop_by']-time.time()>3600
for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:os.environ[k]='http://127.0.0.1:9682'
class Session(AuthorizedSession):
 def request(self,*a,**kw):kw.setdefault('timeout',30);return super().request(*a,**kw)
scopes=['openid','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/userinfo.profile','https://www.googleapis.com/auth/colaboratory']
c=Credentials.from_authorized_user_info(json.loads((Path.home()/'.config/colab-cli/token.json').read_text()),scopes=scopes);c.refresh(Request());api=Client(Prod(),Session(c));assert not api.list_assignments()
m=re.search(r'Current balance:\s*([\d.]+)',format_consumption_status(api.get_consumption_user_info()));assert m
balance=float(m.group(1));assert parent['compute_cap']-(parent['starting_balance']-balance)>3
value=parent|dict(created_at=time.time(),observed_balance=balance,parent_resource_plan='c12-resource-plan.json',parent_sha256=hashlib.sha256((r/'c12-resource-plan.json').read_bytes()).hexdigest(),scope='Deployment replacement only; all six original C12 scientific IDs unstarted; unchanged parent deadline/cumulative compute cap/native ceiling')
body=json.dumps(value,indent=2)+'\n';p=r/'c13-resource-plan.json';assert not p.exists();p.write_text(body)
code="from pathlib import Path;import sys,json,hashlib;r=Path('/home/simjecture/investigations/scientific-attention-20261025');v=json.load(sys.stdin);assert json.loads((r/'c12-guard-status.json').read_text())['stage']=='released';assert not (r/'parked-commission-c12/CAMPAIGN.json').exists();assert hashlib.sha256((r/'c12-resource-plan.json').read_bytes()).hexdigest()==v['parent_sha256'];p=r/'c13-resource-plan.json';assert not p.exists();p.write_text(json.dumps(v,indent=2));print('Saved unchanged C12 parent bounds; no allocation')"
p=subprocess.run(DIAL+['python3 -c '+shlex.quote(code)],input=body,capture_output=True,text=True,timeout=45)
print(p.stdout);print(p.stderr[-1500:]);assert p.returncode==0;print(json.dumps(value))
