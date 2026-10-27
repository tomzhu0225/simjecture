"""Isolate the new controls from the original cohort's forced-source environment."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

ROOT = Path('/home/simjecture/investigations/scientific-attention-20261025')
ENV = ROOT / 'control-commission-env'
TOOLS = ROOT / 'control-commission-tools-e0ae6fa'
SCIENCE = ROOT / 'control-commission-science-45f0204'
PLAN = json.loads((ROOT / 'control-commission-plan.json').read_text())
assert not ENV.exists(), 'Inspect an existing commissioning environment instead of replacing it'
base = subprocess.run(
    [str(ROOT / 'replication-env/bin/python'), '-c', 'import sys;print(sys._base_executable)'],
    capture_output=True, text=True, check=True, timeout=20,
).stdout.strip()
subprocess.run([base, '-m', 'venv', '--without-pip', str(ENV)], check=True, timeout=30)
python = ENV / 'bin/python'
site = ENV / 'lib/python3.12/site-packages'
assert site.is_dir()
dependencies = [
    ROOT / 'env/lib/python3.12/site-packages',
    Path('/home/simjecture/agent-runtimes/simjecture-0.6.2-replan-recovery-20261018/lib/python3.12/site-packages'),
]
assert all(p.is_dir() and not (p / 'sitecustomize.py').exists() for p in dependencies)
# Plain path entries do not execute the dependency directories' .pth hooks.
# In particular, they cannot insert the old frozen research sources ahead of PYTHONPATH.
pth = site / 'commission-dependencies.pth'
pth.write_text(''.join(str(p) + '\n' for p in dependencies))

result = dict(at=time.time(), python=str(python), base_python=base,
              dependency_path_file_sha256=hashlib.sha256(pth.read_bytes()).hexdigest(),
              shared_dependency_directories=[str(p) for p in dependencies], probes={})
for mode, source in [('operator', TOOLS), ('science', SCIENCE)]:
    env = dict(os.environ, PYTHONNOUSERSITE='1',
               PYTHONPATH=str(source / 'src') + ':' + str(source / 'packages/simjecture-monitor/src'))
    module = 'simjecture_monitor.control_commission' if mode == 'operator' else 'simjecture_monitor.workflow_prompt'
    code = (
        'import importlib,json,sys;from pathlib import Path;'
        f'm=importlib.import_module({module!r});p=Path(m.__file__).resolve();'
        f'assert p.is_relative_to(Path({str(source)!r}));'
        'import pydantic,yt;'
        "print(json.dumps({'module':m.__name__,'file':str(p),'python':sys.executable,"
        "'pydantic':pydantic.__version__,'yt':yt.__version__}))"
    )
    probe = subprocess.run([str(python), '-c', code], env=env, capture_output=True,
                           text=True, timeout=30)
    if probe.returncode:
        raise RuntimeError(probe.stderr[-3000:])
    result['probes'][mode] = json.loads(probe.stdout)
    script = source / 'packages/simjecture-monitor/scripts' / (
        'run_control_commission.py' if mode == 'operator' else 'scientific_workflow_trials.py')
    help_result = subprocess.run([str(python), str(script), '--help'], env=env,
                                 capture_output=True, text=True, timeout=30)
    if help_result.returncode:
        raise RuntimeError(help_result.stderr[-3000:])
    if mode == 'science':
        assert '--worker-prompt' in help_result.stdout and 'routine_help' in help_result.stdout
    result['probes'][mode]['help_passed'] = True

env = dict(os.environ, PYTHONNOUSERSITE='1',
           PYTHONPATH=str(TOOLS / 'src') + ':' + str(TOOLS / 'packages/simjecture-monitor/src'))
check = """from pathlib import Path
import json
from simjecture_monitor.control_commission import check_predecessor
r=Path('/home/simjecture/investigations/scientific-attention-20261025')
check_predecessor(json.loads((r/'r10-combined-summary.json').read_text()),
                  json.loads((r/'r10-guard-status.json').read_text()),
                  json.loads((r/'native-budget-r10.json').read_text()))
"""
probe = subprocess.run([str(python), '-c', check], env=env, capture_output=True,
                       text=True, timeout=30)
assert probe.returncode != 0 and 'Original comparison is incomplete' in probe.stderr
result.update(stage='prepared', actual_partial_predecessor_rejected=True,
              source_files_verified=len(PLAN['source_files_sha256']),
              operator_tools_verified=len(PLAN['commissioning_tools_sha256']),
              native_workers_started=0, physics_jobs_started=0, gpu_allocated=False)
(ROOT / 'control-commission-environment.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
