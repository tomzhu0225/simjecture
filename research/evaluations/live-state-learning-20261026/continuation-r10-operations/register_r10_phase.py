from pathlib import Path
import hashlib,json,time
R=Path('/home/simjecture/investigations/scientific-attention-20261025')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
assert not (R/'r10-phase-plan.json').exists()
assert read(R/'r9-guard-status.json')['stage']=='released'
auth=read(R/'r10-auth-01/STATUS.json');assert auth['stage']=='completed'
budget=read(R/'r10-native-preflight-budget.json');assert len(budget['starts'])==1 and budget['starts'][0]['ended_at'] is not None and budget['starts'][0]['returncode']==0
q=read(R/'r10-transport-qualification/STATUS.json');assert q['stage']=='completed'
records=read(R/'rep2-audit/records.json')+read(R/'r9-all-continuation-records/audit/records.json')
assert len(records)==47 and len({r['id'] for r in records})==47 and sum(r['whole_workflow_verified'] for r in records)==43
manifest=read(R/'r10-workflow-manifest.json');remaining=[t for b in manifest['blocks'] for t in b['trials']]
assert remaining==read(R/'r9-combined-summary.json')['primary_all_attempts']['unstarted']
assert len(remaining)==manifest['workflows']==17
assert set(manifest['preserved_started'])=={r['id'] for r in records}
assert sha(Path.home()/'.ssh/config')==q['ssh_config_sha256']
parent=read(R/'r9-resource-plan.json');resource=read(R/'r10-resource-plan.json')
assert all(resource[k]==parent[k] for k in ['stop_by','starting_balance','compute_cap'])
(R/'r10-probes.json').write_bytes((R/'r9-probes.json').read_bytes())
old=read(R/'r9-phase-plan.json')
ops=['attach_r10.py','deploy_r10_a100.py','prepare_r10_a100.py','r10_service.py','remote_r10_guard.py','remote_r10_proxy.py','r10_colab_control.py','run_r10_auth.py','run_base_sft_r10.py','finish_r10.py','combine_r10_continuation.py','start_r10_phase.py','r10-native-codex','qualify_r10_physics.py','readonly_physics_readiness.py','p40_presubmission_failure.py','r7_initial_provider_failure.py','summarize_base_sft_r7.py','summarize_base_sft_rep2.py','combine_base_sft_phases.py','combine_r8_continuation.py','attention_transport_r7.py','supervise_attention_link.py','recovery_kernel_check.py']
phase=dict(created_at=time.time(),source_revision=old['source_revision'],source_files_sha256=old['source_files_sha256'],assignment_manifest_sha256=sha(R/'r10-workflow-manifest.json'),controller_sha256=sha(R/'run_base_sft_r10.py'),probes_sha256=sha(R/'r10-probes.json'),backend_profile_sha256=q['backend_sha256'],machine_profile_sha256=q['machine_profile_sha256'],ssh_config_sha256=q['ssh_config_sha256'],require_fresh_model_qualification=True,physics_transport_qualification_sha256=sha(R/'r10-transport-qualification/STATUS.json'),auth_preflight_ended_at=auth['ended_at'],prior_native_starts_including_this_preflight=223,original_native_start_ceiling=640,remaining_native_starts=417,orchestration_sha256={n:sha(R/n) for n in ops},last_retained_workflow_ended_at=max(t['ended_at'] for b in read(R/'base-sft-replication-v5/CAMPAIGN.json')['blocks'] for t in b['trials']),resource_lease='r10-lease.json',resource_plan_sha256=sha(R/'r10-resource-plan.json'),parent_resource_plan_sha256=sha(R/'r9-resource-plan.json'),parent_resource_bounds_unchanged=True,prior_owned_runtime_released=True,retained_started=47,unstarted=17,readiness_policy=dict(maximum_attempts=6,maximum_wall_seconds=180,between_attempt_seconds=5,allowed_remote_command='test -x BINARY',timing='Before assignment; outside episode clock',hard_identity_and_permission_errors='Stop without retry',stderr_retained=True,solver_command_retries=0),scope='Original scientific source, prompts, worker settings, policy decoding, weights and statistical analysis unchanged. Only read-only readiness checks may repeat before assignment. Preserve every prior attempt and reproduce saved model probes before collecting. Unchanged R9 parent deadline and cumulative credit ceiling.')
for name,expected in phase['source_files_sha256'].items():assert sha(R/'replication-source-04f905c'/name)==expected,name
(R/'r10-phase-plan.json').write_text(json.dumps(phase,indent=2)+'\n')
print(json.dumps({k:v for k,v in phase.items() if k not in ('source_files_sha256','orchestration_sha256')}))
