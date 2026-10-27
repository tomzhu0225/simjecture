"""Remote control using renewable short-lived Colab/profile access only."""
from pathlib import Path
import datetime,json,os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import AuthorizedSession
from colab_cli.client import Client,Prod
class BoundedSession(AuthorizedSession):
 def request(self,*args,**kwargs):
  kwargs.setdefault('timeout',25)
  return super().request(*args,**kwargs)
ROOT=Path('/home/simjecture/investigations/scientific-attention-20261025')
PRIVATE=ROOT/'private'
def credentials():
 value=json.loads((PRIVATE/'colab-access.json').read_text())
 expiry=datetime.datetime.fromisoformat(value['expiry']).replace(tzinfo=datetime.timezone.utc).timestamp()
 return value,expiry
def client():
 for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:os.environ[k]='http://127.0.0.1:9674'
 value,_=credentials()
 return Client(Prod(),BoundedSession(Credentials(token=value['token'],expiry=datetime.datetime.fromisoformat(value['expiry']))))
