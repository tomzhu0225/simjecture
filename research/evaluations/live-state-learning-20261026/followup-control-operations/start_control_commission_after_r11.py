"""Run the authorized six-workflow commission after the frozen comparison ends."""
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
TOOLS = ROOT / 'control-commission-tools-e0ae6fa'
SCIENCE = ROOT / 'control-commission-science-45f0204'
PYTHON = ROOT / 'control-commission-env/bin/python'
OUT = ROOT / 'control-commission-sequence-01.json'
CAMPAIGN = ROOT / 'control-commission-01'
STOP = ROOT / 'STOP_CONTROL_COMMISSION'
assert not OUT.exists() and not CAMPAIGN.exists()


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


status = dict(stage='waiting_for_original_comparison', started_at=time.time(),
              pid=os.getpid(), decision_model_calls=0, optimizer_updates=0,
              original_comparison_modified=False,
              scope='User-authorized follow-up integration commission, six assignments, two hours, at most 73 native starts; no GPU allocation or model calls')


def save():
    p = OUT.with_suffix('.tmp')
    p.write_text(json.dumps(status, indent=2) + '\n')
    p.replace(OUT)


def cancelled():
    if STOP.exists():
        raise RuntimeError('Operator stopped the queued follow-up before launch')


env = dict(os.environ, PYTHONNOUSERSITE='1', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2',
           PYTHONPATH=str(TOOLS / 'src') + ':' + str(TOOLS / 'packages/simjecture-monitor/src'))
save()
try:
    limit = read(ROOT / 'r11-lease.json')['stop_by'] + 300
    while time.time() < limit:
        cancelled()
        try:
            finalizer = read(ROOT / 'r11-finalizer-status.json')
            guard = read(ROOT / 'r11-guard-status.json')
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(10)
            continue
        if finalizer['stage'] == 'failed':
            raise RuntimeError('Original comparison finalization failed; no follow-up authorized by this runner')
        if finalizer['stage'] == 'completed':
            summary = read(ROOT / 'r11-combined-summary.json')
            primary = summary['primary_all_attempts']
            if not primary.get('complete_design') or primary.get('audit_violations'):
                raise RuntimeError('Original comparison terminal but incomplete or inconsistent; preserve remaining assignments')
            if guard['stage'] == 'released':
                check_predecessor(summary, guard, read(ROOT / 'native-budget-r11.json'))
                break
        time.sleep(10)
    else:
        raise TimeoutError('Original comparison did not satisfy prerequisites within its existing lease')

    plan = read(ROOT / 'control-commission-plan.json')
    assert plan['workflows'] == 6 and plan['resource_bounds']['native_starts'] == 73
    assert plan['resource_bounds']['wall_seconds'] == 7200
    check_tool_hashes(TOOLS / 'packages/simjecture-monitor', plan['commissioning_tools_sha256'])
    for name, expected in plan['source_files_sha256'].items():
        assert sha(SCIENCE / name) == expected, name
    environment = read(ROOT / 'control-commission-environment.json')
    assert environment['stage'] == 'prepared'
    assert environment['python'] == str(PYTHON)
    assert sha(PYTHON.parent.parent / 'lib/python3.12/site-packages/commission-dependencies.pth') == environment['dependency_path_file_sha256']
    status.update(stage='qualifying_physics', predecessor_audited_at=time.time(),
                  predecessor_summary_sha256=sha(ROOT / 'r11-combined-summary.json'),
                  predecessor_guard_sha256=sha(ROOT / 'r11-guard-status.json'),
                  plan_sha256=sha(ROOT / 'control-commission-plan.json'))
    save()
    cancelled()
    with (ROOT / 'control-commission-physics-01.log').open('w') as log:
        result = subprocess.run([str(PYTHON), str(ROOT / 'qualify_control_commission_physics.py')],
                                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=660)
    if result.returncode:
        raise RuntimeError('Fresh control physics qualification failed; no native workflow started')
    cancelled()
    qualification = ROOT / 'control-commission-physics-01/STATUS.json'
    assert read(qualification)['stage'] == 'completed'
    command = [str(PYTHON), str(TOOLS / 'packages/simjecture-monitor/scripts/run_control_commission.py')]
    arguments = {
        'plan': ROOT / 'control-commission-plan.json', 'root': CAMPAIGN,
        'source': SCIENCE, 'python': PYTHON,
        'codex': Path('/home/simjecture/.local/bin/codex-ggdd'),
        'backend': ROOT / 'control-commission-backend.json',
        'plasma-assets': ROOT / 'plasma', 'physics-qualification': qualification,
        'predecessor-summary': ROOT / 'r11-combined-summary.json',
        'predecessor-guard': ROOT / 'r11-guard-status.json',
        'predecessor-budget': ROOT / 'native-budget-r11.json',
    }
    for key, value in arguments.items():
        command += ['--' + key, str(value)]
    status.update(stage='launching_commission', command=command)
    save()
    with (ROOT / 'control-commission-01.log').open('w') as log:
        child = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        owner = process_stat(child.pid)
        status.update(stage='commissioning', runner_pid=child.pid, launched_at=time.time())
        save()
        try:
            code = child.wait(timeout=7500)
        except subprocess.TimeoutExpired:
            stop_session(owner)
            child.wait(timeout=15)
            raise
    finalization = read(CAMPAIGN / 'FINALIZATION.json')
    commission_path = CAMPAIGN / 'COMMISSION.json'
    commission = read(commission_path) if commission_path.exists() else None
    status.update(stage='completed' if code == 0 and commission and commission.get('commissioned') else 'incomplete',
                  runner_returncode=code, finalization=finalization,
                  commission={k: v for k, v in (commission or {}).items() if k != 'inputs_sha256'},
                  ended_at=time.time())
except Exception:
    status.update(stage='failed', error=traceback.format_exc(), ended_at=time.time())
finally:
    save()
print(json.dumps(status), flush=True)
