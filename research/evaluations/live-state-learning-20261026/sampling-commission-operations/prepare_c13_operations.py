"""Reduce the failed deployment payload; retain C12 scientific assignments/bounds."""
from pathlib import Path
import ast,json,hashlib
r=Path('.')
names=['attach_c12.py','deploy_c12_a100.py','prepare_c12_a100.py','c12_service.py','remote_c12_guard.py','remote_c12_proxy.py','c12_colab_control.py','local_c12_failsafe.py','install_c12_controls.py','c12_control_once.py','run_c12_sampling.py','start_c12_phase.py','allocate_c12_http2.py','poll_c12.py']
for old in names:
 name=old.replace('c12','c13')
 s=(r/old).read_text().replace('c12','c13').replace('C12','C13')
 s=s.replace('parked-commission-c13','parked-commission-c12').replace('c13-auth-01','c12-auth-01').replace('c13-preflight-status.json','c12-preflight-status.json').replace('c13-physics/','c12-physics/').replace('c13-backend.json','c12-backend.json')
 if old in ['deploy_c12_a100.py','prepare_c12_a100.py']:
  s=s.replace('validation-model-assets.tar.gz','validation-model-assets-c13.tar.gz')
  s=s.replace('4b7a12dfa53e2bfc18ad0073c5fa5b820b6da08fa04c36ac8de722fcaee47bd0','ce4494689a92d5da131f9e45115bbd6baac296b160fc2df41cd9ac8a2d5fc62e')
  s=s.replace('timeout=240','timeout=600')
 if old=='allocate_c12_http2.py':
  s=s.replace('simjecture-science-20261028a','simjecture-science-20261028b')
  s=s.replace("assert not (r/'c13-launch-status.json').exists();", "assert json.loads((r/'c12-guard-status.json').read_text())['stage']=='released';assert not (r/'c13-launch-status.json').exists();")
  s=s.replace('New six-workflow native sampling commission; no optimizer; fresh two-hour and 20-CU ceiling','Deployment replacement for six untouched C12 assignments; unchanged C12 deadline and cumulative 20-CU ceiling')
  s=s.replace('http_version=http_version,error_markers=',"http_version=http_version,error_summary=response.stderr.replace(c.token,'[REDACTED]').replace(challenge.token,'[REDACTED]')[-512:],error_markers=")
 ast.parse(s,filename=name);p=r/name;assert not p.exists();p.write_text(s)
print('Prepared replacement deployment; scientific source, IDs, weights, deadline unchanged')
