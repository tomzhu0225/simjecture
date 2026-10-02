"""Command/limit construction tests only; no OS limits or numerical runtime changed."""

import resource
from types import SimpleNamespace

import pytest

from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig


def sandbox(tmp_path, cpus):
    result = object.__new__(BubblewrapSandbox)
    result.root = tmp_path
    result.config = MVPAgentConfig(max_command_seconds=2.5)
    result.isolation_backend = "bubblewrap"
    result.executable = "unused-bwrap-fixture"
    result.assigned_cpus = cpus
    return result


@pytest.mark.parametrize("cpus,cpu_seconds", [(None, 4), (1, 4), (2, 6), (8, 21)])
def test_cpu_time_budget_accounts_for_reserved_threads(tmp_path, monkeypatch, cpus, cpu_seconds):
    limits = {}
    monkeypatch.setattr(resource, "setrlimit", lambda key, value: limits.update({key: value}))
    runner = sandbox(tmp_path, cpus)
    runner._limits()
    assert limits[resource.RLIMIT_CPU] == (cpu_seconds, cpu_seconds)
    assert limits[resource.RLIMIT_AS] == (runner.config.max_memory_bytes,) * 2
    assert limits[resource.RLIMIT_FSIZE] == (runner.config.max_file_bytes,) * 2
    assert limits[resource.RLIMIT_CORE] == (0, 0)


def test_cpu_allocation_preserves_explicit_capability_thread_settings(tmp_path, monkeypatch):
    runner = sandbox(tmp_path, 8)
    installed = SimpleNamespace(
        assert_runtime_identity=lambda: None,
        runtime_root=tmp_path / "runtime",
        container_root="/opt/capability",
        container_executable="/opt/capability/bin/python",
        read_only_mounts=[],
        device_paths=[],
        environment={"OMP_NUM_THREADS": "8", "OPENBLAS_NUM_THREADS": "1"},
    )
    runner.capabilities = SimpleNamespace(get=lambda name: installed)
    monkeypatch.setattr(runner, "_run_command", lambda command, **kwargs: command)
    command = runner.run_capability("fixture", ("input.py",))
    environment = {
        command[i + 1]: command[i + 2]
        for i, value in enumerate(command)
        if value == "--setenv"
    }
    assert environment["OMP_NUM_THREADS"] == "8"
    assert environment["OPENBLAS_NUM_THREADS"] == "1"
    assert "--unshare-all" in command and "--clearenv" in command


@pytest.mark.parametrize("cpus", [0, -1, True, 1.5, float("inf"), 65537])
def test_invalid_cpu_allocation_cannot_change_limits(tmp_path, monkeypatch, cpus):
    limits = []
    monkeypatch.setattr(resource, "setrlimit", lambda *args: limits.append(args))
    with pytest.raises(ValueError, match="Assigned CPUs"):
        sandbox(tmp_path, cpus)._limits()
    assert not limits


def test_nonfinite_cpu_budget_cannot_change_limits(tmp_path, monkeypatch):
    limits = []
    monkeypatch.setattr(resource, "setrlimit", lambda *args: limits.append(args))
    runner = sandbox(tmp_path, 8)
    runner.config = MVPAgentConfig(max_command_seconds=1e308)
    with pytest.raises(ValueError, match="finite"):
        runner._limits()
    assert not limits
