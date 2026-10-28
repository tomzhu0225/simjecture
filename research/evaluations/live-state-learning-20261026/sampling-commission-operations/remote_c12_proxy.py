from pathlib import Path
import json,sys,time
import websocket
from colab_cli.state import SessionState
from colab_cli.commands.ssh import _build_ws_url,_bridge_proxy_mode
from c12_colab_control import ROOT,PRIVATE,client
for attempt in range(6):
 try:
  path=PRIVATE/'c12-session.json';s=SessionState.model_validate_json(path.read_text())
  if s.token_expires_at.timestamp()-time.time()<300:
   matching=[a for a in client().list_assignments() if a.endpoint==s.endpoint]
   if len(matching)!=1:raise RuntimeError('Owned runtime is no longer assigned')
   info=matching[0].runtime_proxy_info;s.token=info.token;s.url=info.url;s.token_expires_at=info.expires_at()
   path.write_text(s.model_dump_json());path.chmod(0o600)
  pub=(PRIVATE/'colab-c12.pub').read_text().strip()
  ws=websocket.create_connection(_build_ws_url(s),header={'X-Colab-Ssh-Pubkey':pub},timeout=25,http_proxy_host='127.0.0.1',http_proxy_port=9674,suppress_origin=True)
  ws.settimeout(None);break
 except Exception as error:
  print('Colab SSH handshake',attempt+1,type(error).__name__,'http_status',getattr(error,'status_code',None),file=sys.stderr,flush=True)
  if attempt==5:raise SystemExit(1)
  time.sleep(2)
raise SystemExit(_bridge_proxy_mode(ws))
