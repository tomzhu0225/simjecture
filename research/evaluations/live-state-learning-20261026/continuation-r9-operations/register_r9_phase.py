"""Freeze the continuation from existing audited records before allocating compute."""
from pathlib import Path
import hashlib,json,time
R=Path('/home/simjecture/investigations/scientific-attention-20261025')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
assert not (R/'r9-phase-plan.json').exists()
auth=read(R/'r9-auth-01/STATUS.json');assert auth['stage']=='completed'
budget=read(R/'r9-native-preflight-budget.json');assert len(budget['starts'])==1 and budget['starts'][0]['ended_at'] is not None and budget['starts'][0]['returncode']==0
q=read(R/'r9b-transport-qualification/STATUS.json');assert q['stage']=='completed'
records=read(R/'rep2-audit/records.json')+read(R/'r8-all-continuation-records/audit/records.json')
assert len(records)==38 and len({r['id'] for r in records})==38 and sum(r['whole_workflow_verified'] for r in records)==34
manifest=read(R/'r9-workflow-manifest.json');left=[t for b in manifest['blocks'] for t in b['trials']]
expected=read(R/'r8-combined-summary.json')['primary_all_attempts']['unstarted']
assert left==expected and len(left)==manifest['workflows']==26
assert set(manifest['preserved_started'])=={r['id'] for r in records}
assert sha(Path.home()/'.ssh/config')==q['ssh_config_sha256']
(R/'r9-probes.json').write_bytes((R/'r8-probes.json').read_bytes())
old=read(R/'r8-phase-plan.json')
ops=['attach_r9.py','deploy_r9_a100.py','prepare_r9_a100.py','r9_service.py','remote_r9_guard.py','remote_r9_proxy.py','r9_colab_control.py','run_r9_auth.py','run_base_sft_r9.py','finish_r9.py','combine_r9_continuation.py','start_r9_phase.py','r9-native-codex','qualify_r9_physics.py','qualify_r9b_physics.py','p40_presubmission_failure.py','r7_initial_provider_failure.py','summarize_base_sft_r7.py','summarize_base_sft_rep2.py','combine_base_sft_phases.py','combine_r8_continuation.py','attention_transport_r7.py','supervise_attention_link.py','recovery_kernel_check.py']
phase=dict(created_at=time.time(),source_revision=old['source_revision'],source_files_sha256=old['source_files_sha256'],assignment_manifest_sha256=sha(R/'r9-workflow-manifest.json'),controller_sha256=sha(R/'run_base_sft_r9.py'),probes_sha256=sha(R/'r9-probes.json'),backend_profile_sha256=q['backend_sha256'],machine_profile_sha256=q['machine_profile_sha256'],ssh_config_sha256=q['ssh_config_sha256'],require_fresh_model_qualification=True,physics_transport_qualification_sha256=sha(R/'r9b-transport-qualification/STATUS.json'),failed_readonly_setup_qualification_sha256=sha(R/'r9-transport-qualification/STATUS.json'),auth_preflight_ended_at=auth['ended_at'],prior_native_starts_including_this_preflight=171,original_native_start_ceiling=640,remaining_native_starts=469,orchestration_sha256={n:sha(R/n) for n in ops},last_retained_workflow_ended_at=max(t['ended_at'] for b in read(R/'base-sft-replication-v4/CAMPAIGN.json')['blocks'] for t in b['trials']),resource_lease='r9-lease.json',resource_plan_sha256=sha(R/'r9-resource-plan.json'),prior_owned_runtime_released=True,retained_started=38,unstarted=26,scope='Same original scientific source, prompts, worker configuration, policy decoding and weights. Only connection establishment permits three OpenSSH attempts; never retry an ambiguous submitted simulation or an attempted workflow. Fresh model probes must pass before any scientific assignment.')
for name,expected_hash in phase['source_files_sha256'].items():assert sha(R/'replication-source-04f905c'/name)==expected_hash,name
(R/'r9-phase-plan.json').write_text(json.dumps(phase,indent=2))
print(json.dumps({k:v for k,v in phase.items() if k not in ('source_files_sha256','orchestration_sha256')}))
