from pathlib import Path
import hashlib,json,time
R=Path('/home/simjecture/investigations/scientific-attention-20261025')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
assert not (R/'r11-phase-plan.json').exists()
assert read(R/'r10-guard-status.json')['stage']=='released'
auth=read(R/'r11-auth-01/STATUS.json');assert auth['stage']=='completed'
budget=read(R/'r11-native-preflight-budget.json');assert len(budget['starts'])==1 and budget['starts'][0]['ended_at'] is not None and budget['starts'][0]['returncode']==0
q=read(R/'r11-transport-qualification/STATUS.json');assert q['stage']=='completed'
records=read(R/'rep2-audit/records.json')+read(R/'r10-all-continuation-records/audit/records.json')
assert len(records)==55 and len({r['id'] for r in records})==55 and sum(r['whole_workflow_verified'] for r in records)==49
manifest=read(R/'r11-workflow-manifest.json');remaining=[t for b in manifest['blocks'] for t in b['trials']]
assert remaining==read(R/'r10-combined-summary.json')['primary_all_attempts']['unstarted']
assert len(remaining)==manifest['workflows']==9
assert set(manifest['preserved_started'])=={r['id'] for r in records}
assert sha(Path.home()/'.ssh/config')==q['ssh_config_sha256']
parent=read(R/'r9-resource-plan.json');resource=read(R/'r11-resource-plan.json')
assert all(resource[k]==parent[k] for k in ['stop_by','starting_balance','compute_cap'])
(R/'r11-probes.json').write_bytes((R/'r10-probes.json').read_bytes())
old=read(R/'r10-phase-plan.json')
ops=['attach_r11.py','deploy_r11_a100.py','prepare_r11_a100.py','r11_service.py','remote_r11_guard.py','remote_r11_proxy.py','r11_colab_control.py','run_r11_auth.py','run_base_sft_r11.py','finish_r11.py','combine_r11_continuation.py','start_r11_phase.py','r11-native-codex','qualify_r11_physics.py','readonly_physics_readiness.py','p40_presubmission_failure.py','r7_initial_provider_failure.py','summarize_base_sft_r7.py','summarize_base_sft_rep2.py','combine_base_sft_phases.py','combine_r8_continuation.py','attention_transport_r7.py','supervise_attention_link.py','recovery_kernel_check.py']
phase=dict(created_at=time.time(),source_revision=old['source_revision'],source_files_sha256=old['source_files_sha256'],assignment_manifest_sha256=sha(R/'r11-workflow-manifest.json'),controller_sha256=sha(R/'run_base_sft_r11.py'),probes_sha256=sha(R/'r11-probes.json'),backend_profile_sha256=q['backend_sha256'],machine_profile_sha256=q['machine_profile_sha256'],ssh_config_sha256=q['ssh_config_sha256'],require_fresh_model_qualification=True,physics_transport_qualification_sha256=sha(R/'r11-transport-qualification/STATUS.json'),auth_preflight_ended_at=auth['ended_at'],prior_native_starts_including_this_preflight=280,original_native_start_ceiling=640,remaining_native_starts=360,orchestration_sha256={n:sha(R/n) for n in ops},last_retained_workflow_ended_at=max(t['ended_at'] for b in read(R/'base-sft-replication-v6/CAMPAIGN.json')['blocks'] for t in b['trials']),resource_lease='r11-lease.json',resource_plan_sha256=sha(R/'r11-resource-plan.json'),parent_resource_plan_sha256=sha(R/'r9-resource-plan.json'),parent_resource_bounds_unchanged=True,prior_owned_runtime_released=True,retained_started=55,unstarted=9,readiness_policy=dict(maximum_attempts=6,maximum_wall_seconds=180,between_attempt_seconds=5,allowed_remote_command='test -x BINARY',timing='Before assignment; outside episode clock',hard_identity_and_permission_errors='Stop without retry',stderr_retained=True,solver_command_retries=0),scope='Original scientific source, prompts, worker settings, policy decoding, weights and statistical analysis unchanged. Only read-only readiness checks may repeat before assignment. Preserve every prior attempt and reproduce saved model probes before collecting. Unchanged R9 parent deadline and cumulative credit ceiling.')
for name,expected in phase['source_files_sha256'].items():assert sha(R/'replication-source-04f905c'/name)==expected,name
(R/'r11-phase-plan.json').write_text(json.dumps(phase,indent=2)+'\n')
print(json.dumps({k:v for k,v in phase.items() if k not in ('source_files_sha256','orchestration_sha256')}))
