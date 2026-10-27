"""Bounded local CPU qualification; independent of the remote scientific cohort."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import platform
import resource
import shutil
import subprocess
import time
import traceback

ROOT = Path(__file__).parent
BINARY = Path('/home/tomzhu0225/src/warpx-pr6766-rz-terminal/build-port-1d-make/bin/warpx.1d.NOMPI.OMP.DP.PDP')
EXPECTED_BINARY = '17f3fa0e6dda982b699cfb613f45abff6ccc5976ad461081fd885f59f9ccd85e'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**3, 1024**3))


reference = json.loads((ROOT / 'reference.json').read_text())
assert sha(BINARY) == EXPECTED_BINARY
assert sha(ROOT / 'inputs') == reference['research/inputs']['sha256']
assert sha(ROOT / 'original_analysis.py') == reference['research/original_analysis.py']['sha256']
plan = dict(
    created_at=time.time(), binary=str(BINARY), binary_sha256=EXPECTED_BINARY,
    input_sha256=sha(ROOT / 'inputs'), original_analysis_sha256=sha(ROOT / 'original_analysis.py'),
    cases=[dict(name='mesh_64', cells=64, steps=40), dict(name='mesh_128', cells=128, steps=80)],
    limits=dict(omp_threads=2, virtual_memory_bytes=8 * 1024**3, cpu_seconds=60, wall_seconds=90),
    criteria=dict(original_field_error_below=0.05, original_charge_residual_below=1e-11,
                  field_error_absolute_difference_at_most=1e-8,
                  peak_relative_difference_at_most=1e-8, time_relative_tolerance=1e-12,
                  time_absolute_tolerance=1e-26),
    scope='Two matched-time CPU controls only; no model training or change to the running P40 cohort',
)
with (ROOT / 'PLAN.json').open('x') as stream:
    json.dump(plan, stream, indent=2)
status = dict(stage='running', started_at=time.time(), pid=os.getpid(), cases=[])


def save():
    p = ROOT / 'STATUS.tmp'
    p.write_text(json.dumps(status, indent=2))
    p.replace(ROOT / 'STATUS.json')


save()
try:
    import scipy
    import numpy as np
    import yt
    from scipy.constants import c, e, epsilon_0, m_e
    yt.funcs.mylog.setLevel(40)
    status['analysis_environment'] = dict(
        python=platform.python_version(), scipy=scipy.__version__, numpy=np.__version__,
        yt=yt.__version__, constants=dict(c=c, e=e, epsilon_0=epsilon_0, m_e=m_e))
    spec = importlib.util.spec_from_file_location('frozen_original_analysis', ROOT / 'original_analysis.py')
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)  # Import only; its historical main() is not used.
    env = dict(os.environ, OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OMP_DYNAMIC='FALSE', CUDA_VISIBLE_DEVICES='', MPLBACKEND='Agg')
    for case in plan['cases']:
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                             if line.startswith('MemAvailable:'))) * 1024
        if available < 8 * 1024**3:
            raise RuntimeError('Local memory headroom fell below the qualification allowance')
        folder = ROOT / case['name']
        folder.mkdir()
        shutil.copyfile(ROOT / 'inputs', folder / 'inputs')
        command = [str(BINARY), 'inputs', f"amr.n_cell={case['cells']}",
                   f"max_step={case['steps']}", 'amr.max_level=0',
                   'diagnostics.diags_names=diag1', 'diag1.file_prefix=plot',
                   f"diag1.intervals={case['steps']}", 'amrex.the_arena_init_size=67108864',
                   'warpx.verbose=0']
        started = time.time()
        with (folder / 'solver.log').open('w') as log:
            result = subprocess.run(['/usr/bin/time', '-v', '-o', str(folder / 'resource.log'),
                                     'timeout', '--kill-after=5s', '90s']
                                    + command, cwd=folder, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, preexec_fn=limits,
                                    start_new_session=True, timeout=100)
        row = dict(**case, command=command, returncode=result.returncode,
                   started_at=started, ended_at=time.time(), process_seconds=time.time() - started)
        if result.returncode:
            status['cases'].append(row)
            raise RuntimeError('Local solver failed; retained log identifies the failure')
        plot = folder / f"plot{case['steps']:06d}"
        measured = analyzer.analyze(plot, case['cells'])
        dataset = yt.load(str(plot))
        fields = dataset.covering_grid(level=0, left_edge=dataset.domain_left_edge,
                                       dims=dataset.domain_dimensions)
        peak = float(np.max(np.abs(fields[('mesh', 'Ez')].to_ndarray())))
        entries = [json.loads(line) for line in reference[case['name'] + '-analysis.log']['text'].splitlines()
                   if line.startswith('{')]
        golden = next(v for v in entries if 'relative_field_error' in v)
        differences = dict(field_error_absolute=abs(measured['relative_field_error'] - golden['relative_field_error']),
                           peak_relative=abs(peak / golden['peak_electric_field_V_per_m'] - 1),
                           physical_time_absolute=abs(measured['physical_time_s'] - golden['physical_time_s']))
        passed = (measured['original_checks_passed']
                  and differences['field_error_absolute'] <= 1e-8
                  and differences['peak_relative'] <= 1e-8
                  and math.isclose(measured['physical_time_s'], golden['physical_time_s'],
                                   rel_tol=1e-12, abs_tol=1e-26))
        row.update(measured=measured, peak_electric_field_V_per_m=peak, p40_reference=golden,
                   differences=differences, bounded_control_qualified=bool(passed),
                   solver_log_sha256=sha(folder / 'solver.log'),
                   resource_log=(folder / 'resource.log').read_text())
        (folder / 'RESULT.json').write_text(json.dumps(row, indent=2))
        status['cases'].append(row)
        save()
    status.update(stage='completed', ended_at=time.time(),
                  bounded_controls_qualified=all(v['bounded_control_qualified'] for v in status['cases']),
                  analysis_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
except Exception:
    status.update(stage='failed', ended_at=time.time(), error=traceback.format_exc())
    raise
finally:
    save()
print(json.dumps(dict(stage=status['stage'], qualified=status.get('bounded_controls_qualified'),
                     cases=[dict(name=v['name'], seconds=v['process_seconds'],
                                 qualified=v.get('bounded_control_qualified'),
                                 measured=v.get('measured'), differences=v.get('differences'))
                            for v in status['cases']])), flush=True)
