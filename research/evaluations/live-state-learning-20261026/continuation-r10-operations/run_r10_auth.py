from pathlib import Path
import json,os,subprocess,time,traceback
R=Path('/home/simjecture/investigations/scientific-attention-20261025');d=R/'r10-auth-01';d.mkdir(exist_ok=False);(d/'work').mkdir()
budget=R/'r10-native-preflight-budget.json'
assert not budget.exists()
budget.write_text(json.dumps(dict(deadline=time.time()+360,maximum_starts=1,maximum_per_continuation=1,maximum_concurrent=1,executable='/home/simjecture/.local/bin/codex-ggdd',starts=[],scope='One continuation preflight, after 222 retained starts; deducted from remaining 418'),indent=2))
wrapper=R/'r10-native-codex';wrapper.write_text('#!'+str(R/'replication-env/bin/python')+'\nfrom simjecture_monitor.native_guard import main\nmain()\n');wrapper.chmod(0o700)
command=[str(wrapper),'exec','--ephemeral','--json','--sandbox','read-only','--skip-git-repo-check','--model','gpt-6-astra','-c','model_reasoning_effort="high"','-c','features.shell_tool=false','-c','features.unified_exec=false','-c','web_search="disabled"','--output-last-message',str(d/'last.txt'),'-']
env=dict(os.environ,PYTHONPATH=str(R/'replication-source-04f905c/src')+':'+str(R/'replication-source-04f905c/packages/simjecture-monitor/src'),SIMJECTURE_NATIVE_BUDGET=str(budget),SIMJECTURE_CONTINUATION='r10-auth-01',SIMJECTURE_CONTINUATION_DEADLINE=str(time.time()+300),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
status=dict(stage='running',started_at=time.time())
(d/'STATUS.json').write_text(json.dumps(status))
try:
 with (d/'events.jsonl').open('w') as out,(d/'stderr.log').open('w') as err:
  p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=out,stderr=err,cwd=d/'work',env=env,start_new_session=True)
  status['wrapper_pid']=p.pid;(d/'STATUS.json').write_text(json.dumps(status));p.communicate('Return exactly READY. Do not use tools. This is an authentication preflight, not a scientific task.'.encode(),timeout=330)
 status.update(returncode=p.returncode,stage='completed' if p.returncode==0 and (d/'last.txt').exists() and (d/'last.txt').read_text().strip()=='READY' else 'failed')
except Exception as e:status.update(stage='failed',error_type=type(e).__name__)
status['ended_at']=time.time();(d/'STATUS.json').write_text(json.dumps(status,indent=2));print(json.dumps(status))
