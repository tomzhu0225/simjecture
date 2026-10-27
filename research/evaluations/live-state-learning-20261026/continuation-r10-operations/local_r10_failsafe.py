"""Release only the recorded owned endpoint at its independent hard deadline."""
from pathlib import Path
import json,os,time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request,AuthorizedSession
from colab_cli.client import Client,Prod
R=Path(__file__).parent;lease=json.loads((R/'r10-lease.json').read_text());out=R/'r10-local-guard-status.json'
for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:os.environ[k]='http://127.0.0.1:9682'
def put(v):
 p=out.with_suffix('.tmp');p.write_text(json.dumps(v,indent=2));p.replace(out)
put(dict(stage='waiting_for_deadline',at=time.time(),endpoint=lease['endpoint'],stop_by=lease['stop_by']))
while time.time()<lease['stop_by']:
 if (R/'r10-verified-released.json').exists():
  v=json.loads((R/'r10-verified-released.json').read_text())
  if v.get('endpoint')==lease['endpoint'] and v.get('released'):put(dict(stage='completed',at=time.time(),reason='verified_external_release'));raise SystemExit(0)
 time.sleep(min(20,max(.1,lease['stop_by']-time.time())))
class Session(AuthorizedSession):
 def request(self,*a,**k):k.setdefault('timeout',30);return super().request(*a,**k)
for attempt in range(20):
 try:
  scopes=['openid','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/userinfo.profile','https://www.googleapis.com/auth/colaboratory']
  c=Credentials.from_authorized_user_info(json.loads((Path.home()/'.config/colab-cli/token.json').read_text()),scopes=scopes);c.refresh(Request());api=Client(Prod(),Session(c))
  before=api.list_assignments()
  if any(a.endpoint==lease['endpoint'] for a in before):api.unassign(lease['endpoint'])
  after=api.list_assignments();assert not any(a.endpoint==lease['endpoint'] for a in after)
  put(dict(stage='released',at=time.time(),endpoint=lease['endpoint'],was_assigned=any(a.endpoint==lease['endpoint'] for a in before)));break
 except Exception as e:put(dict(stage='release_retry',at=time.time(),endpoint=lease['endpoint'],attempt=attempt+1,error_type=type(e).__name__));time.sleep(30)
else:put(dict(stage='release_unconfirmed',at=time.time(),endpoint=lease['endpoint']))
