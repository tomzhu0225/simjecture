from pathlib import Path
import hashlib,json,time,subprocess,os
r=Path('/home/simjecture/investigations/scientific-attention-20261025');s=r/'workflow-return-source-171ac44';c=r/'parked-commission-c12'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert read(r/'c12-preflight-status.json')['stage']=='passed'
assert read(r/'c12-host-record-qualification.json')['stage']=='passed'
assert read(r/'control-commission-02/COMMISSION.json')['commissioned']
auth=read(r/'c12-native-preflight-budget.json')['starts'];assert len(auth)==1 and auth[0]['ended_at'] and auth[0]['returncode']==0
assert not c.exists()
env=dict(os.environ,PYTHONPATH=str(s/'src')+':'+str(s/'packages/simjecture-monitor/src'))
command=[str(r/'control-commission-env/bin/python'),str(s/'packages/simjecture-monitor/scripts/collect_workflow_returns.py'),'plan','--root',str(c),'--purpose','commissioning','--replicates','1','--configuration-seed','202610280100','--order-seed','2026102801','--native-cap','12','--model-policy','continued_sft','--adapter-sha256','76bf1bdf4c6d6a261211057d3cab4c8609131788827569f9c33f802d3491dab5','--temperature','1','--decision-distribution','scientific-route-question/v1','--backend',str(r/'c12-backend.json'),'--worker-prompt','task_protocol','--parent-turn-limit','12','--maximum-parallel-workflows','1','--minimum-gap-seconds','90']
for family in ['progressing_work','unit_conversion','source_binding']:command+=['--family',family]
with (r/'c12-planning.log').open('x') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
(r/'c12-probes.json').write_bytes((r/'r11-probes.json').read_bytes())
names=['attach_c12.py','deploy_c12_a100.py','prepare_c12_a100.py','c12_service.py','remote_c12_guard.py','remote_c12_proxy.py','c12_colab_control.py','run_c12_sampling.py','start_c12_phase.py','c12-native-codex','attention_transport_r7.py','supervise_attention_link.py','recovery_kernel_check.py']
plan=read(c/'PLAN.json');assert sum(len(b['trials']) for b in plan['blocks'])==6
value=dict(created_at=time.time(),source_revision='171ac44dab39904e6934609de8ba41be325790c7',workflows=6,optimizer_updates=0,scope='Native-sampling integration only; new commissioning IDs, no training or efficacy estimate',assignment_plan_sha256=sha(c/'PLAN.json'),orchestration_sha256={n:sha(r/n) for n in names},adapter_sha256=plan['adapter_sha256'],probes_sha256=sha(r/'c12-probes.json'),resource_plan_sha256=sha(r/'c12-resource-plan.json'),physics_sha256=sha(r/'c12-physics/STATUS.json'),host_record_qualification_sha256=sha(r/'c12-host-record-qualification.json'),collection_settings=plan['collection_settings'],decision_distribution=plan['decision_distribution'],temperature=plan['temperature'])
(r/'c12-phase-plan.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value),flush=True)
