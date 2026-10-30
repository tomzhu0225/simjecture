"""Append a remote instrument without invalidating an active worker pool."""

import json
import os
import sys

import pytest

from conjecture_solver.execution_pool import MachineRegistry, Transport
from conjecture_solver.research_service import ResearchService
from tests.test_execution_pool import finish


def instrument(capabilities, tmp_path, name):
    runtime = tmp_path / name
    runtime.mkdir()
    executable = runtime / "python-tool"
    executable.write_text(
        f"#!{sys.executable}\nimport runpy,sys\nrunpy.run_path(sys.argv[1],run_name='__main__')\n"
    )
    executable.chmod(0o555)
    (capabilities / (name + ".json")).write_text(
        json.dumps(
            dict(
                manifest=dict(
                    name=name,
                    version="1",
                    description="Readiness test Python instrument",
                    skill="python",
                    executable_kind="python",
                ),
                runtime_root=str(runtime),
                executable=executable.name,
            )
        )
    )


@pytest.fixture
def remote_study(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("Needs an unprivileged native process worker")
    capabilities = tmp_path / "capabilities"
    capabilities.mkdir()
    instrument(capabilities, tmp_path, "original")
    registry = MachineRegistry(tmp_path / "registry")
    registry.save(
        dict(
            id="native",
            kind="local",
            root=str(tmp_path / "worker"),
            python=sys.executable,
            config=dict(
                cpus=2,
                memory_mb=2048,
                execution_backend="process-cooperative",
                capabilities=[str(capabilities)],
            ),
        )
    )
    registry.prepare("native")
    service = ResearchService.create(
        tmp_path / "study", "Original bounded claim", execution_pool=registry.freeze(["native"])
    )
    (service.work / "calc.py").write_text(
        "from pathlib import Path\nPath('result.json').write_text('{\"ready\":true}')\n"
    )
    return service, capabilities


def test_remote_append_runs_and_remains_source_bound(remote_study, tmp_path):
    service, capabilities = remote_study
    manifest = (service.root / "research.json").read_bytes()
    old_hashes = service.capability_hashes()
    instrument(capabilities, tmp_path, "new-runtime")
    added = service.register_capability(
        "new-runtime",
        machine="native",
        development=dict(
            parent_capability="original--at-native",
            change_type="numerical",
            rationale="Register a separately versioned experimental implementation.",
            preserved_assumptions="Preserve the readiness calculation and original instrument.",
            validation_plan="Execute through the exact worker and inspect the new source.",
        ),
    )
    alias = "new-runtime--at-native"
    assert added["name"] == alias
    assert (
        service.solver_development_status()["builds"][0]["development"]["parent_capability"]
        == "original--at-native"
    )
    assert service.register_capability("new-runtime")["runtime_sha256"] == added["runtime_sha256"]
    assert service.capability_hashes().items() >= old_hashes.items()
    assert alias in ResearchService(service.root).machines()["native"]["capabilities"]
    assert (service.root / "research.json").read_bytes() == manifest
    assert "runpy.run_path" in json.dumps(
        service.read_instrument(alias, root="runtime", path="python-tool")
    )
    receipt = service.run("calc.py", capability=alias, outputs=["result.json"], stage="exploration")
    result = finish(service, [receipt["id"]])[0]
    assert result["status"] == "succeeded", result
    assert result["binding"]["worker_capability"] == "new-runtime"
    assert result["binding"]["runtime_sha256"] == added["runtime_sha256"]
    service.fetch_remote(experiment=result["id"], path="result.json")
    method = service.method(
        source="calc.py",
        capability=alias,
        scope="instrument",
        model="Finite readiness calculation",
        geometry="No spatial domain",
        observable="Exact readiness flag",
        validation="Actual worker receipt",
        rationale="Exercise source-bound registration and execution",
        validation_experiments=[result["id"]],
    )
    assert method["binding"]["runtime_sha256"] == added["runtime_sha256"]


def test_remote_registration_rejects_original_replacement(remote_study, tmp_path):
    service, capabilities = remote_study
    instrument(capabilities, tmp_path, "new-runtime")
    executable = tmp_path / "original/python-tool"
    executable.chmod(0o755)
    executable.write_text(executable.read_text() + "# Changed original instrument\n")
    with pytest.raises(ValueError, match="immutable"):
        service.register_capability("new-runtime", machine="native")
    assert service._all("capability_additions") == []


def test_remote_registration_rejects_worker_identity_change(remote_study, tmp_path, monkeypatch):
    service, capabilities = remote_study
    instrument(capabilities, tmp_path, "new-runtime")
    original = Transport.call

    def changed(self, operation, **kwargs):
        result = original(self, operation, **kwargs)
        if operation == "probe":
            result["worker_code_sha256"] = "0" * 64
        return result

    monkeypatch.setattr(Transport, "call", changed)
    with pytest.raises(ValueError, match="identity or configuration"):
        service.register_capability("new-runtime", machine="native")
    with pytest.raises(ValueError, match="Choose a frozen"):
        service.register_capability("new-runtime", machine="absent")
