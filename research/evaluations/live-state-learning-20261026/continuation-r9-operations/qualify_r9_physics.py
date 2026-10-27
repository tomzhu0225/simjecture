"""Qualify a study-only SSH alias with bounded pre-connection retries."""
from pathlib import Path
import hashlib, importlib.util, json, os, shlex, subprocess, time, traceback
R = Path('/home/simjecture/investigations/scientific-attention-20261025')
Q = R / 'r9-transport-qualification'
Q.mkdir(exist_ok=False)
status = dict(stage='preparing', started_at=time.time(), scope='Two engineering controls; no native actors or model updates', cases=[])
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save():
    p = Q / 'STATUS.tmp'; p.write_text(json.dumps(status, indent=2)); p.replace(Q / 'STATUS.json')
save()
try:
    config = Path.home() / '.ssh/config'
    assert not config.exists(), 'Inspect existing SSH configuration rather than overwrite it'
    baseline = subprocess.run(['ssh', '-G', '117.50.245.224'], capture_output=True, check=True).stdout
    profile = json.loads(Path('/home/simjecture/investigations/current-injection-smr-20261015/machines/profiles/p40-smr.json').read_text())
    machine = profile['machine']; alias = 'simjecture-attention-r9-p40'
    assert machine['host'] == '117.50.245.224' and machine['port'] == 23
    text = f'Host {alias}\n    HostName {machine["host"]}\n    HostKeyAlias {machine["host"]}\n    ConnectionAttempts 3\n    ControlMaster no\n    ControlPath none\n    StrictHostKeyChecking yes\n'
    (Q / 'SSH_CONFIG_PLAN.json').write_text(json.dumps(dict(created_at=time.time(), config=str(config), original_exists=False, text=text, semantics='OpenSSH retries TCP establishment only. No replay after SSH command submission. The original 180-second wrapper limit remains.'), indent=2))
    fd = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f: f.write(text)
    after = subprocess.run(['ssh', '-G', '117.50.245.224'], capture_output=True, check=True).stdout
    assert baseline == after, 'Unrelated original host configuration changed'
    machine['host'] = alias
    (R / 'private/p40-r9-profile.json').write_text(json.dumps(profile, indent=2)); (R / 'private/p40-r9-profile.json').chmod(0o600)
    backend = json.loads((R / 'plasma-backend-r8.json').read_text())
    backend['machine_profile'] = str(R / 'private/p40-r9-profile.json')
    (R / 'plasma-backend-r9.json').write_text(json.dumps(backend, indent=2))
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + machine['known_hosts'], '-o', 'IdentitiesOnly=yes', '-i', machine['identity_file'], '-p', str(machine['port']), machine['user'] + '@' + machine['host']]
    effective = subprocess.run(ssh[:-1] + ['-G', ssh[-1]], capture_output=True, text=True, check=True).stdout
    selected = dict(line.split(' ', 1) for line in effective.splitlines() if line.split()[0] in {'hostname', 'connectionattempts', 'controlmaster', 'controlpath', 'hostkeyalias', 'stricthostkeychecking', 'connecttimeout'})
    assert selected['connectionattempts'] == '3' and selected['hostname'] == '117.50.245.224'
    check = subprocess.run(ssh + ['sha256sum ' + shlex.quote(backend['binary'])], capture_output=True, text=True, timeout=55)
    assert check.returncode == 0 and check.stdout.split()[0] == '40259ed2687707b4c693e5b0e7fbadef54dca4fab64898d9d42e654fbdf644eb', check.stderr[-500:]
    status.update(stage='running', effective_ssh=selected, unrelated_host_settings_identical=True, ssh_config_sha256=sha(config), machine_profile_sha256=sha(R / 'private/p40-r9-profile.json'), backend_sha256=sha(R / 'plasma-backend-r9.json')); save()
    work = Q / 'research'; work.mkdir()
    old = R / 'r8-transport-qualification/research'
    for name in ['inputs', 'original_analysis.py', 'environment.json']:
        (work / name).write_bytes((old / name).read_bytes())
    source = R / 'replication-source-04f905c'
    env = dict(os.environ, PYTHONPATH=str(source / 'src') + ':' + str(source / 'packages/simjecture-monitor/src'), SIMJECTURE_PLASMA_BACKEND=str(R / 'plasma-backend-r9.json'), OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
    spec = importlib.util.spec_from_file_location('original_analysis', work / 'original_analysis.py'); analyzer = importlib.util.module_from_spec(spec); spec.loader.exec_module(analyzer); analyzer.yt.funcs.mylog.setLevel(40)
    for cells, steps in [(64, 40), (128, 80)]:
        name = f'mesh_{cells}'
        row = dict(name=name, cells=cells, steps=steps, started_at=time.time()); status['cases'].append(row); save()
        with (Q / (name + '.log')).open('w') as log:
            result = subprocess.run([str(R / 'replication-env/bin/python'), '-m', 'simjecture_monitor.remote_plasma', '--name', name, '--cells', str(cells), '--steps', str(steps)], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=195)
        row['returncode'] = result.returncode
        receipt = json.loads((work / 'runs' / name / 'receipt.json').read_text()); row['receipt'] = receipt; save()
        assert result.returncode == 0 and receipt['status'] == 'succeeded'
        assert receipt['binary_sha256'] == '40259ed2687707b4c693e5b0e7fbadef54dca4fab64898d9d42e654fbdf644eb'
        assert receipt['input_sha256'] == sha(work / 'inputs')
        row['measured'] = analyzer.analyze(work / 'runs' / name / f'plot{steps:06d}', cells)
        assert row['measured']['original_checks_passed']
        row['ended_at'] = time.time(); save()
    status.update(stage='completed', ended_at=time.time(), original_analysis_sha256=sha(work / 'original_analysis.py'), input_sha256=sha(work / 'inputs'))
except Exception:
    status.update(stage='failed', ended_at=time.time(), error=traceback.format_exc())
save(); print(json.dumps(status), flush=True)
if status['stage'] != 'completed': raise SystemExit(1)
