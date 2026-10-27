"""Prepare only the nine original unstarted assignments after the user review."""
from pathlib import Path
import ast
import hashlib
import json
import time

ROOT = Path(__file__).parent
prior = json.loads((ROOT / 'r11-prior-state.json').read_text())
terminal = json.loads((ROOT / 'r10-review-terminal-evidence.json').read_text())
summary = terminal['r10-combined-summary.json']['primary_all_attempts']
assert summary['started'] == 55 and len(summary['unstarted']) == 9
assert not summary['audit_violations']
assert prior['r10-guard-status.json']['stage'] == 'released'
assert prior['native'] == {'starts': 56, 'active': 0}
assert not any(p['exists'] for p in prior['r10-controller_processes'].values())
assert not prior['r11_existing']

manifest = json.loads((ROOT / 'r10-workflow-manifest.json').read_text())
ids = {row['id'] for row in summary['unstarted']}
blocks = []
for block in manifest['blocks']:
    selected = [row for row in block['trials'] if row['id'] in ids]
    if selected:
        blocks.append(block | {'trials': selected})
assert [row for block in blocks for row in block['trials']] == summary['unstarted']
preserved = list(manifest['preserved_started']) + [row['id'] for row in prior['r10-audit/records.json']]
assert len(preserved) == len(set(preserved)) == 55
assert not set(preserved) & ids
manifest.update(
    blocks=blocks, workflows=9, preserved_started=preserved, created_at=time.time(),
    continuation_reason='User resumed after review; preserve all 55 attempts and run only the nine original unstarted assignments',
    preparation=dict(state='Prepared; fresh physics/auth/model qualification required', retained_attempts=55,
                     retained_verified=49, native_starts_used_including_preflights=279,
                     remaining_original_native_start_ceiling=361, previous_runtime_released=True,
                     rerun_attempted_ids=False),
)
path = ROOT / 'r11-workflow-manifest.json'
assert not path.exists()
path.write_text(json.dumps(manifest, indent=2) + '\n')

names = [
    'attach_r10.py', 'deploy_r10_a100.py', 'prepare_r10_a100.py', 'r10_service.py',
    'remote_r10_guard.py', 'remote_r10_proxy.py', 'r10_colab_control.py',
    'run_r10_auth.py', 'run_base_sft_r10.py', 'finish_r10.py',
    'combine_r10_continuation.py', 'start_r10_phase.py', 'qualify_r10_physics.py',
    'allocate_r10_http2.py', 'local_r10_failsafe.py', 'install_r10_controls.py',
    'r10_control_once.py', 'prepare_r10_resource_plan.py', 'register_r10_phase.py',
    'poll_r10.py',
]
written = []
for old_name in names:
    name = old_name.replace('r10', 'r11')
    original = (ROOT / old_name).read_text()
    text = original.replace('r10', 'r11').replace('R10', 'R11').replace('base-sft-replication-v6', 'base-sft-replication-v7')
    if old_name == 'run_r10_auth.py':
        text = text.replace('222 retained starts', '279 retained starts').replace('remaining 418', 'remaining 361')
    elif old_name == 'qualify_r10_physics.py':
        text = text.replace("r9-guard-status.json", "r10-guard-status.json")
        text = text.replace("r9b-transport-qualification/STATUS.json", "r10-transport-qualification/STATUS.json")
        text = text.replace("plasma-backend-r9.json", "plasma-backend-r10.json")
    elif old_name == 'prepare_r10_resource_plan.py':
        text = text.replace('remaining_workflows=17', 'remaining_workflows=9')
        text = text.replace('prior_native_starts=222', 'prior_native_starts=279')
        text = text.replace('maximum_additional_native_starts=418', 'maximum_additional_native_starts=361')
        text = text.replace('17 original unstarted IDs', 'nine original unstarted IDs').replace('47 earlier attempts', '55 earlier attempts')
        text = text.replace("r9-guard-status.json", "r10-guard-status.json")
    elif old_name == 'register_r10_phase.py':
        text = text.replace("r9-guard-status.json", "r10-guard-status.json")
        text = text.replace("r9-all-continuation-records/audit/records.json", "r10-all-continuation-records/audit/records.json")
        text = text.replace('len(records)==47', 'len(records)==55').replace('records})==47', 'records})==55').replace('records)==43', 'records)==49')
        text = text.replace("r9-combined-summary.json", "r10-combined-summary.json")
        text = text.replace("manifest['workflows']==17", "manifest['workflows']==9")
        text = text.replace("r9-probes.json", "r10-probes.json").replace("r9-phase-plan.json", "r10-phase-plan.json")
        text = text.replace('including_this_preflight=223', 'including_this_preflight=280').replace('remaining_native_starts=417', 'remaining_native_starts=360')
        text = text.replace('base-sft-replication-v5/CAMPAIGN.json', 'base-sft-replication-v6/CAMPAIGN.json')
        text = text.replace('retained_started=47,unstarted=17', 'retained_started=55,unstarted=9')
    elif old_name == 'start_r10_phase.py':
        text = text.replace("('native-budget-r9.json',51)", "('native-budget-r9.json',51),('native-budget-r10.json',56)")
        text = text.replace("including_this_preflight']==223", "including_this_preflight']==280")
        text = text.replace('maximum_starts=417', 'maximum_starts=360').replace('parent_prior_starts=223', 'parent_prior_starts=280')
        text = text.replace('417 remaining starts after 222 retained prior starts and one R11 preflight', '360 remaining starts after 279 retained prior starts and one R11 preflight')
    elif old_name == 'combine_r10_continuation.py':
        marker = "(ROOT/'r11-audit',ROOT/'base-sft-replication-v7')"
        assert marker in text
        text = text.replace(marker, "(ROOT/'r10-audit',ROOT/'base-sft-replication-v6')," + marker)
    elif old_name == 'allocate_r10_http2.py':
        text = text.replace('simjecture-science-20261027d', 'simjecture-science-20261027e')
        text = text.replace('17 unstarted original scientific workflows; 47 earlier attempts', 'nine unstarted original scientific workflows; 55 earlier attempts')
        marker = "try:\n scopes="
        assert marker in text
        check = '''try:
 # Prove registration and source readiness before obtaining a paid runtime.
 check="from pathlib import Path;import json,hashlib;r=Path('/home/simjecture/investigations/scientific-attention-20261025');p=json.loads((r/'r11-phase-plan.json').read_text());assert p['retained_started']==55 and p['unstarted']==9;assert json.loads((r/'r10-guard-status.json').read_text())['stage']=='released';assert not (r/'r11-launch-status.json').exists();assert all(hashlib.sha256((r/n).read_bytes()).hexdigest()==h for n,h in p['orchestration_sha256'].items());print('registered-ready')"
 verified=subprocess.run(DIAL+['python3 -c '+shlex.quote(check)],capture_output=True,text=True,timeout=45)
 assert verified.returncode==0 and verified.stdout.strip()=='registered-ready','Registration must be verified before allocation'
 scopes='''
        text = text.replace(marker, check)
    ast.parse(text, filename=name)
    dest = ROOT / name
    assert not dest.exists(), name
    dest.write_text(text)
    written.append(dict(path=name, sha256=hashlib.sha256(text.encode()).hexdigest(), derived_from=old_name))

record = dict(created_at=time.time(), manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              assignments=9, preserved_attempts=55, operations=written,
              scope='Resource/controller phase replacement only; original scientific source, model, decoder, task and analysis stay frozen')
(ROOT / 'r11-operations-preparation.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
