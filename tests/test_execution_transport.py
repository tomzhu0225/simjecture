"""Synthetic subprocess replies; tests never invoke local/SSH workers."""

import json
from types import SimpleNamespace

import pytest

from conjecture_solver.execution_pool import Transport, WorkerUnavailable


def transport(tmp_path):
    return Transport({"id": "node", "kind": "local", "root": str(tmp_path)})


@pytest.mark.parametrize(
    "envelope,code",
    [
        ({}, 0),
        ({"ok": 1, "result": {}}, 0),
        ({"ok": True}, 0),
        ({"ok": True, "result": None}, 0),
        ({"ok": True, "result": []}, 0),
        ({"ok": True, "result": {"status": "running"}}, 1),
    ],
)
def test_malformed_success_is_transport_uncertainty(tmp_path, monkeypatch, envelope, code):
    monkeypatch.setattr(
        "conjecture_solver.execution_pool.subprocess.run",
        lambda *a, **kw: SimpleNamespace(stdout=json.dumps(envelope), stderr="", returncode=code),
    )
    with pytest.raises(WorkerUnavailable):
        transport(tmp_path).call("status")


def test_valid_worker_rejection_remains_a_semantic_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "conjecture_solver.execution_pool.subprocess.run",
        lambda *a, **kw: SimpleNamespace(
            stdout=json.dumps({"ok": False, "error": "Frozen input hash changed"}),
            stderr="",
            returncode=1,
        ),
    )
    with pytest.raises(ValueError, match="Frozen input hash changed"):
        transport(tmp_path).call("stage")


def test_valid_worker_result_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "conjecture_solver.execution_pool.subprocess.run",
        lambda *a, **kw: SimpleNamespace(
            stdout=json.dumps({"ok": True, "result": {"status": "running"}}),
            stderr="",
            returncode=0,
        ),
    )
    assert transport(tmp_path).call("status") == {"status": "running"}


def test_dispatch_recovers_malformed_reply_without_false_terminal_failure(tmp_path, monkeypatch):
    import time
    from contextlib import nullcontext

    from conjecture_solver.execution_pool import dispatch, job_identifier
    from conjecture_solver.worker_protocol import load, put

    record = {
        "id": "exp_fixture",
        "status": "running",
        "machine": "node",
        "binding": {
            "source": "calc.py",
            "args": [],
            "inputs": {"calc.py": "a" * 64},
            "capability": None,
            "runtime_sha256": None,
        },
        "outputs": ["result.json"],
        "timeout": 30,
        "workspace_limit_bytes": 1024**2,
        "resources": {"cpus": 1, "memory_mb": 1024, "gpus": 0},
    }
    directory = tmp_path / "experiments"
    directory.mkdir()
    path = directory / "exp_fixture.json"
    put(path, record)
    service = SimpleNamespace(
        root=tmp_path,
        manifest={
            "deadline": time.time() + 60,
            "execution_pool": {
                "registry": str(tmp_path / "registry"),
                "workers": {
                    "node": {
                        "probe": {
                            "config_sha256": "b" * 64,
                            "worker_code_sha256": None,
                            "worker_id": None,
                        }
                    }
                },
            },
        },
        _read=lambda *args: load(path),
        lock=nullcontext,
    )
    remote = {"id": job_identifier(service, record), "status": "succeeded", "artifacts": {}}
    replies = iter([{"ok": True}, {"ok": True, "result": remote}])
    methods = []

    def run(*args, **kwargs):
        methods.append(json.loads(kwargs["input"])["method"])
        return SimpleNamespace(stdout=json.dumps(next(replies)), stderr="", returncode=0)

    monkeypatch.setattr("conjecture_solver.execution_pool.subprocess.run", run)
    monkeypatch.setattr(
        "conjecture_solver.execution_pool.MachineRegistry.transport",
        lambda *args, **kwargs: transport(tmp_path),
    )
    waiting = []

    def sleep(seconds):
        current = load(path)
        waiting.append(seconds)
        assert current["status"] == "running"
        assert current["transport_status"] == "unreachable"

    monkeypatch.setattr("conjecture_solver.execution_pool.time.sleep", sleep)
    dispatch(service, record)
    assert methods == ["status", "status"]
    assert waiting == [1]
    assert load(path)["status"] == "succeeded"
    assert load(path)["transport_status"] == "connected"


@pytest.mark.parametrize("result", [True, "installed", ["ready"]])
def test_generic_bootstrap_accepts_scalar_or_list_results_from_real_fixture_process(
    tmp_path, result
):
    import sys

    # INSTALL_BACKEND currently emits {"ok": True, "result": True}. This real,
    # harmless fixture prints the envelope only; it never runs setup/install code.
    script = "import json; print(json.dumps(" + repr({"ok": True, "result": result}) + "))"
    assert transport(tmp_path).run([sys.executable, "-c", script], {}) == result
