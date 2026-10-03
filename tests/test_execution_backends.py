import os
import shutil
from contextlib import suppress

import pytest

from conjecture_solver.execution import probe_execution_backend
from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig
from conjecture_solver.research_service import ResearchService


def test_backend_is_explicit_and_immutable(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMJECTURE_SANDBOX", "proot-cooperative")
    assert MVPAgentConfig().execution_backend == "bubblewrap"
    service = ResearchService.create(
        tmp_path / "study", "Bounded claim", execution_backend="proot-cooperative"
    )
    assert ResearchService(service.root).manifest["execution_backend"] == "proot-cooperative"
    with pytest.raises(ValueError, match="immutable"):
        ResearchService.create(service.root, "Bounded claim", execution_backend="bubblewrap")


def test_missing_bubblewrap_does_not_fallback(monkeypatch):
    monkeypatch.setattr(
        shutil, "which", lambda binary: None if binary == "bwrap" else "/usr/bin/proot"
    )
    report = probe_execution_backend("bubblewrap")
    assert not report["available"]
    assert report["backend"] == "bubblewrap"


@pytest.mark.parametrize("backend", ["proot-cooperative", "process-cooperative"])
def test_cooperative_execution_seals_inputs_clears_environment_and_times_out(
    tmp_path, monkeypatch, backend
):
    if os.geteuid() == 0 or (backend == "proot-cooperative" and not shutil.which("proot")):
        pytest.skip("Needs an unprivileged account and selected backend")
    pytest.importorskip("psutil")
    monkeypatch.setenv("PROVIDER_TEST_SECRET", "must-not-inherit")
    sandbox = BubblewrapSandbox(
        tmp_path, MVPAgentConfig(execution_backend=backend, max_command_seconds=10)
    )
    source = tmp_path / "probe.py"
    source.write_text(
        "import os\nfrom pathlib import Path\n"
        'assert "PROVIDER_TEST_SECRET" not in os.environ\n'
        'Path("result.txt").write_text("42")\n'
    )

    def run(timeout=10):
        return sandbox.run_python(
            ("probe.py",),
            input_artifacts=(),
            program_path="probe.py",
            program_sha256=sandbox._file_sha256(source),
            timeout_seconds=timeout,
        )

    result = run()
    assert result.returncode == 0, result.stderr
    assert result.isolation_backend == backend
    assert (tmp_path / "result.txt").read_text() == "42"
    source.write_text(
        'from pathlib import Path\np=Path("probe.py")\np.chmod(0o600)\np.write_text("tampered")\n'
    )
    before = source.read_bytes()
    assert run().returncode == 125
    assert source.read_bytes() == before
    source.write_text("import time\ntime.sleep(30)\n")
    assert run(0.4).timed_out


@pytest.mark.parametrize("backend", ["proot-cooperative", "process-cooperative"])
def test_parent_death_cleans_up_experiment_descendants(tmp_path, backend):
    if os.geteuid() == 0 or (backend == "proot-cooperative" and not shutil.which("proot")):
        pytest.skip("Needs an unprivileged account and selected backend")
    import subprocess
    import sys
    import time

    psutil = pytest.importorskip("psutil")
    (tmp_path / "slow.py").write_text(
        "import os, time\nfrom pathlib import Path\n"
        "Path('experiment.pid').write_text(str(os.getpid()))\ntime.sleep(60)\n"
    )
    parent = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from conjecture_solver.mvp_agent import BubblewrapSandbox,MVPAgentConfig; "
            "import sys; s=BubblewrapSandbox(sys.argv[1], "
            f"MVPAgentConfig(execution_backend={backend!r},max_command_seconds=60)); "
            "s.run_python(('slow.py',))",
            str(tmp_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid = None
    try:
        end = time.monotonic() + 10
        while not (tmp_path / "experiment.pid").exists() and time.monotonic() < end:
            time.sleep(0.05)
        pid = int((tmp_path / "experiment.pid").read_text())
        parent.kill()
        parent.wait(timeout=5)
        end = time.monotonic() + 5
        while psutil.pid_exists(pid) and time.monotonic() < end:
            if psutil.Process(pid).status() == psutil.STATUS_ZOMBIE:
                break
            time.sleep(0.05)
        assert not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=5)
        if pid and psutil.pid_exists(pid):
            with suppress(psutil.NoSuchProcess):
                psutil.Process(pid).kill()


def test_workspace_fallback_is_checked_and_warned(monkeypatch):
    from conjecture_solver import execution

    def probe(backend):
        return dict(
            backend=backend, available=backend == "proot-cooperative", reason="probe result"
        )

    monkeypatch.setattr(execution, "probe_execution_backend", probe)
    selected = execution.select_execution_backend()
    assert selected["backend"] == "proot-cooperative"
    assert selected["fallback_reason"] == "probe result"
    assert "not a security sandbox" in selected["warning"]
    assert execution.select_execution_backend("bubblewrap")["backend"] == "bubblewrap"
    monkeypatch.setattr(
        execution,
        "probe_execution_backend",
        lambda backend: dict(
            backend=backend, available=False, reason="root or missing prerequisite"
        ),
    )
    assert execution.select_execution_backend()["backend"] == "bubblewrap"
    assert not execution.select_execution_backend()["available"]
