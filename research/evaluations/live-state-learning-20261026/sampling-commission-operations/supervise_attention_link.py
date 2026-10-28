"""Reconnect only an already-owned Colab SSH link; never allocate a runtime."""
from pathlib import Path
import argparse,json,os,subprocess,time,traceback
from simjecture_monitor.native_guard import process_stat,stop_session
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);args=p.parse_args()
plan=json.loads(args.plan.read_text());status_path=Path(plan['status']);control=Path(plan['control_socket']);forward=Path(plan['forward_socket']);lease_path=Path(plan['lease']);stop=Path(plan['stop_file'])
assert not status_path.exists() and not control.exists() and not forward.exists()
state=dict(stage='starting',started_at=time.time(),connections=[]);process=None;owner=None

def save():
 t=status_path.with_suffix('.tmp');t.write_text(json.dumps(state,indent=2));t.replace(status_path)
def deadline():return json.loads(lease_path.read_text())['stop_by']
save();consecutive_failures=0
try:
 while time.time()<deadline() and not stop.exists():
  if process is not None:
   assert process.poll() is not None
   stop_session(owner)
  for socket in [control,forward]:socket.unlink(missing_ok=True)
  with Path(plan['log']).open('a') as log:process=subprocess.Popen(plan['command'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  owner=process_stat(process.pid);record=dict(pid=process.pid,identity=owner,started_at=time.time());state['connections'].append(record);state.update(stage='connecting',current_pid=process.pid);save()
  ready=False;bound=min(time.time()+45,deadline())
  while time.time()<bound and process.poll() is None and not stop.exists():
   if control.exists():
    check=subprocess.run(['ssh','-S',str(control),'-O','check',plan['destination']],capture_output=True,timeout=3)
    if check.returncode==0:
     ready=True;record['ready_at']=time.time();state['stage']='ready';save();break
   time.sleep(.2)
  if not ready:
   stop_session(owner)
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:stop_session(owner);process.wait(timeout=5)
   consecutive_failures+=1;record.update(ended_at=time.time(),returncode=process.returncode,ready=False);save()
   if consecutive_failures>=3:raise RuntimeError('Three consecutive owned-link connection attempts failed')
  else:
   while process.poll() is None and time.time()<deadline() and not stop.exists():time.sleep(.2)
   if process.poll() is None:
    stop_session(owner);process.wait(timeout=5)
   record.update(ended_at=time.time(),returncode=process.returncode,ready=True)
   if record['ended_at']-record['ready_at']>=60:consecutive_failures=0
   else:consecutive_failures+=1
   state['stage']='disconnected';save()
   if consecutive_failures>=3:raise RuntimeError('Owned-link connection repeatedly stopped before stabilizing')
  time.sleep(.3)
 state.update(stage='stopped',ended_at=time.time())
except Exception as error:
 state.update(stage='failed',error_type=type(error).__name__,error=traceback.format_exc(),ended_at=time.time());stop.write_text('Owned inference link could not be maintained; release owned runtime.\n')
finally:
 if process is not None:
  stop_session(owner)
  try:process.wait(timeout=5)
  except subprocess.TimeoutExpired:pass
 for socket in [control,forward]:socket.unlink(missing_ok=True)
 save()
