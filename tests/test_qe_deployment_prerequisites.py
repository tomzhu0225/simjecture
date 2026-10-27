"""Isolated deployment entry tests: all install/doctor calls are mocks."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from conjecture_solver.deployment import DeploymentManager, DeploymentProfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/quantum-espresso/scripts"
pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux shell entry points")


def executable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\nset -eu\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def isolated(tmp_path):
    project = tmp_path / "project with spaces"
    scripts = project / "skills/quantum-espresso/scripts"
    scripts.mkdir(parents=True)
    for name in ("bootstrap.sh", "deploy.sh", "prerequisites.sh"):
        shutil.copyfile(SCRIPTS / name, scripts / name)
    tools = tmp_path / "tools with spaces"
    tools.mkdir()
    for name in ("uname", "findmnt", "readlink", "mkdir", "ln", "basename"):
        (tools / name).symlink_to(shutil.which(name))
    executable(tools / "bwrap", "exit 0")
    log = tmp_path / "calls.log"
    python = executable(
        project / ".venv/bin/python",
        '''printf 'python' >> "$CALLS"
printf ' <%s>' "$@" >> "$CALLS"
printf '\\n' >> "$CALLS"
case "$*" in
  *'import sys;'*) exit "${VERSION_RC:-0}" ;;
  *'import conjecture_solver.cli'*) exit "${IMPORT_RC:-0}" ;;
  *'--profile core'*) exit "${CORE_RC:-0}" ;;
  *'--check-disk'*) exit "${DISK_RC:-0}" ;;
esac''',
    )
    uv = executable(
        tools / "uv",
        '''if [[ "$1" = --version ]]; then exit "${UV_RC:-0}"; fi
printf '%s\\n' "$UV_PROJECT_ENVIRONMENT" >> "$CALLS.uv-environments"
printf 'uv' >> "$CALLS"
printf ' <%s>' "$@" >> "$CALLS"
printf '\\n' >> "$CALLS"
exit "${INSTALL_RC:-0}"''',
    )
    env = {k: v for k, v in os.environ.items() if k not in {
        "SIMJECTURE_BOOTSTRAP_PYTHON", "UV_PROJECT_ENVIRONMENT"}}
    env.update(PATH=str(tools), CALLS=str(log), HOME=str(tmp_path / "home"))
    return SimpleNamespace(project=project, scripts=scripts, tools=tools,
                           python=python, uv=uv, env=env, log=log,
                           runtime=tmp_path / "runtime with spaces")


def deploy(f, *args):
    return subprocess.run(
        ["/bin/bash", str(f.scripts / "deploy.sh"), "--project-root", str(f.project),
         "--runtime-base", str(f.runtime), *args],
        env=f.env, text=True, capture_output=True, timeout=20,
    )


def no_install(f):
    assert not (f.project / ".runtime").exists()
    assert not f.runtime.exists()
    assert not f.log.exists() or "uv <run>" not in f.log.read_text()


@pytest.mark.parametrize("tool,hint", [("uv", "--uv"), ("bwrap", "bubblewrap"),
                                       ("findmnt", "util-linux"), ("uname", "coreutils")])
def test_missing_tools_fail_before_mutation(isolated, tool, hint):
    f = isolated
    (f.tools / tool).unlink()
    result = deploy(f)
    assert result.returncode == 2
    assert hint in result.stderr
    no_install(f)


@pytest.mark.parametrize("system,machine", [("Darwin", "x86_64"), ("Linux", "aarch64")])
def test_unsupported_platform_stops_before_uv(isolated, system, machine):
    f = isolated
    (f.tools / "uname").unlink()
    executable(
        f.tools / "uname",
        f'if [[ "$1" = -s ]]; then echo {system}; else echo {machine}; fi',
    )
    result = deploy(f)
    assert result.returncode == 2
    assert "Linux x86_64" in result.stderr
    no_install(f)
    assert not f.log.exists()


@pytest.mark.parametrize("setting,hint", [("VERSION_RC", ">=3.11"),
                                           ("IMPORT_RC", "uv sync --frozen"),
                                           ("CORE_RC", "doctor remedies"),
                                           ("DISK_RC", ""), ("UV_RC", "uv cannot run")])
def test_failed_prerequisites_do_not_install(isolated, setting, hint):
    f = isolated
    f.env[setting] = "1"
    result = deploy(f)
    assert result.returncode != 0
    assert hint in result.stderr
    no_install(f)


def test_missing_python_has_actionable_remedy(isolated):
    f = isolated
    f.python.unlink()
    result = deploy(f)
    assert result.returncode == 2
    assert "SIMJECTURE_BOOTSTRAP_PYTHON" in result.stderr
    assert "installation.md" in result.stderr
    no_install(f)


def test_explicit_bad_python_never_silently_falls_back(isolated):
    f = isolated
    f.env["SIMJECTURE_BOOTSTRAP_PYTHON"] = "/no/such/python"
    result = deploy(f)
    assert result.returncode == 2
    assert "/no/such/python" in result.stderr
    no_install(f)


def test_deploy_space_paths_and_existing_application_without_path_python3(isolated):
    f = isolated
    assert shutil.which("python3", path=f.env["PATH"]) is None
    result = deploy(f, "--uv", str(f.uv), "--bubblewrap-dir", str(f.tools))
    assert result.returncode == 0, result.stderr
    assert (f.project / ".runtime/quantum-espresso-7.4").is_symlink()
    text = f.log.read_text()
    assert text.index("--profile> <core>") < text.index("uv <run>")
    assert text.count("uv <run>") == 2
    assert "<--check-disk>" in text


def test_existing_environment_reused_without_relink(isolated):
    f = isolated
    target = f.runtime / "quantum-espresso-7.4"
    target.mkdir(parents=True)
    sentinel = target / "existing-record"
    sentinel.write_text("unchanged")
    local = f.project / ".runtime/quantum-espresso-7.4"
    local.parent.mkdir()
    local.symlink_to(target)
    original = local.lstat().st_ino
    assert deploy(f).returncode == 0
    assert deploy(f).returncode == 0
    assert local.lstat().st_ino == original
    assert sentinel.read_text() == "unchanged"


def test_existing_conflicting_prefix_preserved(isolated):
    f = isolated
    local = f.project / ".runtime/quantum-espresso-7.4"
    local.mkdir(parents=True)
    result = deploy(f)
    assert result.returncode == 2
    assert "left unchanged" in result.stderr
    assert not f.runtime.exists()
    assert "uv <run>" not in f.log.read_text()


def test_failed_install_does_not_run_qe_doctor(isolated):
    f = isolated
    f.env["INSTALL_RC"] = "4"
    assert deploy(f).returncode == 4
    assert f.log.read_text().count("uv <run>") == 1


@pytest.mark.parametrize("relative", [False, True, "dot-relative"])
def test_application_environment_selection(isolated, relative):
    f = isolated
    app = f.project / "separate app"
    app.mkdir()
    (app / "bin").mkdir()
    (app / "bin/python").symlink_to(f.python)
    value = "separate app" if relative else str(app)
    if relative == "dot-relative":
        value = "./separate app"
    f.env["UV_PROJECT_ENVIRONMENT"] = value
    assert deploy(f).returncode == 0
    assert Path(str(f.log) + ".uv-environments").read_text().splitlines() == [str(app)] * 2


def test_bootstrap_uses_real_application_interpreter_without_path_python3(isolated):
    f = isolated
    # Actual Python version check and file execution; runtime provisioning mocked.
    f.python.unlink()
    f.python.symlink_to(sys.executable)
    (f.scripts / "finalize_runtime.py").write_text(
        "import os,sys\nfrom pathlib import Path\n"
        "with Path(os.environ['CALLS']).open('a') as f:\n"
        "    f.write(sys.executable+' '+str(sys.argv)+'\\n')\n"
    )
    (f.project / "scripts").mkdir()
    (f.project / "scripts/runtime_environment.sh").write_text('python="$bootstrap_python"\n')
    result = subprocess.run(
        ["/bin/bash", str(f.scripts / "bootstrap.sh"), "--prefix", str(f.runtime),
         "--project-root", str(f.project)],
        env=f.env, text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert f.log.read_text().count(str(f.python)) == 2
    assert not f.runtime.exists()


@pytest.mark.parametrize("override", [None, "", "/explicit application/python"])
def test_operator_passes_application_python_to_qe_bootstrap(tmp_path, monkeypatch, override):
    import conjecture_solver.deployment as dep

    root = tmp_path / "project"
    bootstrap = executable(root / "skills/quantum-espresso/scripts/bootstrap.sh", "exit 0")
    (root / "pyproject.toml").write_text("[project]\nname='mock'\n")
    (root / "capabilities").mkdir()
    (root / "environments").mkdir()
    manager = DeploymentManager(root)
    monkeypatch.setattr(manager, "_already_ready", lambda *a: None)
    monkeypatch.setattr(manager, "_core_checks", lambda **kw: [])
    monkeypatch.setattr(manager, "_configured_runtime_root", lambda *a: tmp_path / "runtime")
    expected = override or sys.executable
    if override is not None:
        monkeypatch.setenv("SIMJECTURE_BOOTSTRAP_PYTHON", override)
    else:
        monkeypatch.delenv("SIMJECTURE_BOOTSTRAP_PYTHON", raising=False)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 2, "", "mock stops before install")

    monkeypatch.setattr(dep, "_run_install_command", run)
    report = manager._install_bootstrap(
        DeploymentProfile.QUANTUM_ESPRESSO, dry_run=False, repair=False,
        source=None, jobs=1, capture_output=True,
    )
    assert not report.ready
    assert calls[0][0][0] == str(bootstrap)
    assert calls[0][1]["environment"]["SIMJECTURE_BOOTSTRAP_PYTHON"] == expected


@pytest.mark.parametrize("capture", [False, True])
def test_install_command_supplied_environment(tmp_path, capture):
    from conjecture_solver.deployment import _run_install_command

    destination = tmp_path / "environment.json"
    result = _run_install_command(
        [sys.executable, "-c",
         "import os,pathlib,sys;pathlib.Path(sys.argv[1]).write_text(os.environ['QE_TEST'])",
         str(destination)],
        capture_output=capture, environment=os.environ | {"QE_TEST": "explicit application"},
    )
    assert result.returncode == 0
    assert destination.read_text() == "explicit application"


def test_real_disk_preflight_rejects_non_native_filesystem(isolated):
    f = isolated
    (f.tools / "findmnt").unlink()
    executable(f.tools / "findmnt", "echo drvfs")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "finalize_runtime.py"), "--check-disk", str(f.runtime)],
        env=f.env, text=True, capture_output=True, timeout=20,
    )
    assert result.returncode != 0
    assert "Linux-native runtime filesystem" in result.stderr
    no_install(f)


@pytest.mark.parametrize("existing,required_gib", [(False, 3), (True, 1)])
def test_real_disk_preflight_rejects_low_reserve(tmp_path, monkeypatch, existing, required_gib):
    import runpy

    prefix = tmp_path / "runtime"
    if existing:
        (prefix / "conda-meta").mkdir(parents=True)
        (prefix / "conda-meta/history").touch()
    monkeypatch.setattr(sys, "argv", ["finalize_runtime.py", "--check-disk", str(prefix)])
    monkeypatch.setattr(shutil, "which", lambda *a: None)
    monkeypatch.setattr(shutil, "disk_usage", lambda *a: SimpleNamespace(free=0))
    with pytest.raises(SystemExit, match=f"need {required_gib * 1024**3}"):
        runpy.run_path(str(SCRIPTS / "finalize_runtime.py"))
    assert not (prefix / "share").exists()
    assert not prefix.exists() if not existing else (prefix / "conda-meta/history").exists()


@pytest.mark.parametrize("value", ["/absent app", "absent relative app"])
@pytest.mark.parametrize("override", [False, True])
def test_invalid_explicit_app_never_falls_back(isolated, value, override):
    f = isolated
    f.env["UV_PROJECT_ENVIRONMENT"] = value
    (f.tools / "python3").symlink_to(f.python)
    if override:
        f.env["SIMJECTURE_BOOTSTRAP_PYTHON"] = str(f.python)
    result = deploy(f)
    assert result.returncode == 2
    assert "Invalid UV_PROJECT_ENVIRONMENT" in result.stderr
    assert "uv sync --frozen" in result.stderr
    no_install(f)
    assert not f.log.exists()


def test_explicit_app_preflight_uses_uv_target_not_other_bootstrap(isolated):
    f = isolated
    app = f.project / "target app"
    target = executable(app / "bin/python", "exit 41")
    f.env["UV_PROJECT_ENVIRONMENT"] = "target app"
    f.env["SIMJECTURE_BOOTSTRAP_PYTHON"] = str(f.python)
    result = deploy(f)
    assert result.returncode == 2
    assert "Application packages are unavailable" in result.stderr
    no_install(f)
    assert "import conjecture_solver.cli" not in f.log.read_text()
    assert target.exists()


def test_explicit_bootstrap_also_binds_uv_environment(isolated):
    f = isolated
    alternate = executable(f.project / "alternate app/bin/python", 'exit 0')
    f.env["SIMJECTURE_BOOTSTRAP_PYTHON"] = str(alternate)
    assert deploy(f).returncode == 0
    assert Path(str(f.log) + ".uv-environments").read_text().splitlines() == [
        str(alternate.parent.parent)
    ] * 2


def test_path_only_python_does_not_validate_uncreated_uv_environment(isolated):
    f = isolated
    executable(f.tools / "python3", "exit 0")
    f.python.unlink()
    result = deploy(f)
    assert result.returncode == 2
    assert "No existing application environment" in result.stderr
    assert "UV_PROJECT_ENVIRONMENT" in result.stderr
    no_install(f)


def test_relative_bootstrap_uv_and_bubblewrap_from_external_cwd(isolated, tmp_path):
    f = isolated
    external = tmp_path / "caller dir"
    external.mkdir()
    rel_app = external / "rel app/bin"
    rel_app.mkdir(parents=True)
    (rel_app / "python").symlink_to(f.python)
    rel_tools = external / "rel tools"
    rel_tools.mkdir()
    (rel_tools / "uv").symlink_to(f.uv)
    (f.tools / "bwrap").rename(rel_tools / "bwrap")
    f.env["SIMJECTURE_BOOTSTRAP_PYTHON"] = "./rel app/bin/python"
    result = subprocess.run(
        [
            "/bin/bash",
            str(f.scripts / "deploy.sh"),
            "--project-root",
            str(f.project),
            "--runtime-base",
            str(f.runtime),
            "--uv",
            "./rel tools/uv",
            "--bubblewrap-dir",
            "./rel tools",
        ],
        cwd=external,
        env=f.env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert Path(str(f.log) + ".uv-environments").read_text().splitlines() == [
        str(external / "rel app")
    ] * 2
