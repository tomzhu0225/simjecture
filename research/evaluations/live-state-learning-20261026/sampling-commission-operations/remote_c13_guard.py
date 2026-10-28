from pathlib import Path
import json,time
from c13_colab_control import ROOT,PRIVATE,client,credentials
lease=json.loads((ROOT/'c13-lease.json').read_text());status=ROOT/'c13-guard-status.json'
while True:
 reason=None
 try:
  value,expiry=credentials();api=client()
  if time.time()>=lease['stop_by']:reason='hard_resource_deadline'
  elif time.time()>=expiry-300:reason='short_lived_control_credential_not_renewed'
  elif (ROOT/'STOP_C13_COLAB').exists():reason='operator_stop'
  # A new, separately registered workflow phase has its own spending ceiling.
  usage=None
  try:usage=api.get_consumption_user_info()
  except Exception:pass
  from colab_cli.consumption import format_consumption_status
  import re
  match=re.search(r'Current balance:\s*([\d.]+)',format_consumption_status(usage)) if usage is not None else None
  balance=float(match.group(1)) if match else None
  if balance is not None and lease['starting_balance']-balance>=lease['compute_cap']:reason='phase_compute_cap'
  status.write_text(json.dumps(dict(stage='watching',at=time.time(),balance=balance,credential_expires=expiry,stop_reason=reason)))
  if reason:
   session=json.loads((PRIVATE/'c13-session.json').read_text())
   api.unassign(session['endpoint'])
   remaining=api.list_assignments()
   if any(a.endpoint==session['endpoint'] for a in remaining):raise RuntimeError('Owned runtime still assigned after release request')
   status.write_text(json.dumps(dict(stage='released',at=time.time(),reason=reason,balance=balance)))
   break
 except Exception as error:
  status.write_text(json.dumps(dict(stage='retrying_control',at=time.time(),error_type=type(error).__name__,stop_reason=reason)))
 time.sleep(20 if reason else 40)
