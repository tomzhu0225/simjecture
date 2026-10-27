"""Commission additional resumptions using only the first pilot's unused budget."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
import traceback

from simjecture_monitor.control_commission import check_predecessor, check_tool_hashes
from simjecture_monitor.native_guard import process_stat, stop_session

ROOT = Path('/home/simjecture/investigations/scientific-attention-20261025')
SOURCE = ROOT / 'control-commission-v2-source-8626a77'
PYTHON = ROOT / 'control-commission-env/bin/python'
CAMPAIGN = ROOT / 'control-commission-02'
STATUS = ROOT / 'control-commission-v2-status.json'
assert not STATUS.exists() and not CAMPAIGN.exists()


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


state = dict(stage='checking_parent', started_at=time.time(), pid=os.getpid(),
             decision_model_calls=0, optimizer_updates=0, gpu_allocations=0)


def save():
    p = STATUS.with_suffix('.tmp')
    p.write_text(json.dumps(state, indent=2) + '\n')
    p.replace(STATUS)


env = dict(os.environ, PYTHONNOUSERSITE='1', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2',
           PYTHONPATH=str(SOURCE / 'src') + ':' + str(SOURCE / 'packages/simjecture-monitor/src'))
save()
try:
    check_predecessor(read(ROOT / 'r11-combined-summary.json'), read(ROOT / 'r11-guard-status.json'),
                      read(ROOT / 'native-budget-r11.json'))
    parent_path = ROOT / 'control-commission-01/native-budget.json'
    parent = read(parent_path)
    assert parent['maximum_starts'] == 73 and len(parent['starts']) == 14
    assert all(v.get('ended_at') is not None for v in parent['starts'])
    assert read(ROOT / 'control-commission-01/CAMPAIGN.json')['stage'] == 'failed'
    assert read(ROOT / 'control-commission-sequence-01.json')['stage'] == 'incomplete'
    parent_hash = sha(parent_path)
    plan = read(ROOT / 'control-commission-v2-plan-prepared.json')
    assert plan['parent_turn_limit'] == 12 and plan['workflows'] == 6
    old_plan = read(ROOT / 'control-commission-plan.json')
    old_ids = {t['id'] for b in old_plan['blocks'] for t in b['trials']}
    assert not old_ids & {t['id'] for b in plan['blocks'] for t in b['trials']}
    check_tool_hashes(SOURCE / 'packages/simjecture-monitor', plan['commissioning_tools_sha256'])
    for name, expected in plan['source_files_sha256'].items():
        assert sha(SOURCE / name) == expected, name
    assert parent['deadline'] - time.time() > 3300
    state.update(stage='qualifying_physics', parent_deadline=parent['deadline'],
                 parent_native_starts=14, remaining_native_starts=59, parent_budget_sha256=parent_hash)
    save()
    with (ROOT / 'control-commission-physics-02.log').open('w') as log:
        result = subprocess.run([str(PYTHON), str(ROOT / 'qualify_control_commission_v2_physics.py')],
                                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=660)
    if result.returncode:
        raise RuntimeError('Second-round physics qualification failed; no new workflow started')
    assert sha(parent_path) == parent_hash
    if (ROOT / 'STOP_CONTROL_COMMISSION').exists():
        raise RuntimeError('Operator stopped the follow-up before launch')
    remaining = int(parent['deadline'] - time.time() - 30)
    assert remaining > 2700
    plan['resource_bounds'] = plan['resource_bounds'] | dict(wall_seconds=remaining, native_starts=59)
    plan['resource_parent'] = dict(
        budget_path=str(parent_path), sha256=parent_hash, original_native_starts=73,
        retained_native_starts=14, remaining_native_starts=59, absolute_deadline=parent['deadline'],
        scope='Retain the first two pilot outcomes and four unstarted IDs; this is a new qualification round with disjoint IDs, not a replacement',
    )
    plan_path = ROOT / 'control-commission-v2-plan.json'
    assert not plan_path.exists()
    plan_path.write_text(json.dumps(plan, indent=2) + '\n')
    command = [str(PYTHON), str(SOURCE / 'packages/simjecture-monitor/scripts/run_control_commission.py')]
    arguments = {
        'plan': plan_path, 'root': CAMPAIGN, 'source': SOURCE, 'python': PYTHON,
        'codex': Path('/home/simjecture/.local/bin/codex-ggdd'),
        'backend': ROOT / 'control-commission-v2-backend.json',
        'plasma-assets': ROOT / 'plasma',
        'physics-qualification': ROOT / 'control-commission-physics-02/STATUS.json',
        'predecessor-summary': ROOT / 'r11-combined-summary.json',
        'predecessor-guard': ROOT / 'r11-guard-status.json',
        'predecessor-budget': ROOT / 'native-budget-r11.json',
    }
    for key, value in arguments.items():
        command += ['--' + key, str(value)]
    assert time.time() + remaining <= parent['deadline']
    state.update(stage='launching', plan_sha256=sha(plan_path), wall_seconds=remaining, command=command)
    save()
    with (ROOT / 'control-commission-02.log').open('w') as log:
        child = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        owner = process_stat(child.pid)
        state.update(stage='commissioning', runner_pid=child.pid, launched_at=time.time())
        save()
        try:
            code = child.wait(timeout=remaining + 240)
        except subprocess.TimeoutExpired:
            stop_session(owner)
            child.wait(timeout=15)
            raise
    finalization = read(CAMPAIGN / 'FINALIZATION.json')
    p = CAMPAIGN / 'COMMISSION.json'
    commission = read(p) if p.exists() else {}
    state.update(stage='completed' if code == 0 and commission.get('commissioned') else 'incomplete',
                 runner_returncode=code, finalization=finalization,
                 commission={k: v for k, v in commission.items() if k != 'inputs_sha256'},
                 ended_at=time.time())
except Exception:
    state.update(stage='failed', error=traceback.format_exc(), ended_at=time.time())
finally:
    save()
print(json.dumps(state), flush=True)
