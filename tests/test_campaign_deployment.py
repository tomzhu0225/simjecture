import argparse
import copy
import errno
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from conjecture_solver import campaign_deployment as deployment
from conjecture_solver import deployment_probe
from conjecture_solver.worker_protocol import Machine


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(tmp_path, **changes):
    hypothesis = tmp_path / "hypothesis.txt"
    hypothesis.write_text("Test the supplied physical hypothesis.\n")
    value = {
        "schema_version": "simjecture-deployment/1",
        "name": "Private research setup",
        "machine_registry": "machines",
        "software": {"simjecture_version": "0.7.0"},
        "workers": [{"id": "node-a"}],
        "files": [
            {
                "id": "hypothesis",
                "path": hypothesis.name,
                "sha256": digest(hypothesis),
                "purpose": "hypothesis",
            }
        ],
        "study": {
            "worker": {"backend": "codex", "model": "worker-model", "reasoning_effort": "high"},
            "director": {"backend": "codex", "model": "director-model", "reasoning_effort": "high"},
            "reviewer": {"backend": "codex", "model": "reviewer-model", "reasoning_effort": "high"},
            "wall_seconds": 172800,
            "report_reserve_seconds": 1800,
            "initial_max_experiment_bytes": 64 * 1024**3,
            "initial_max_total_bytes": 256 * 1024**3,
            "director_storage_increases": True,
        },
    } | changes
    return save(tmp_path, value)


def save(tmp_path, value):
    path = tmp_path / "deployment.json"
    path.write_text(json.dumps(value, indent=2) + "\n")
    return path, value


def items(report):
    return {entry.id: entry for entry in report.checks}


@pytest.fixture
def hosts(tmp_path, monkeypatch):
    """Probe-boundary fakes; file hashing is real, and no services are started."""
    calls = []
    records = {}
    overrides = {}

    def inspect(files, storage_path):
        result = {
            "simjecture_version": "0.7.0",
            "python_source_sha256": "a" * 64,
            "python_version": "3.12",
            "storage": {"free_bytes": 200 * 1024**3},
            "files": {},
        }
        for f in files:
            try:
                result["files"][f["id"]] = deployment_probe.file_identity(f["path"])
            except OSError as error:
                result["files"][f["id"]] = {"error": "file_unavailable", "errno": error.errno}
            except ValueError as error:
                result["files"][f["id"]] = {"error": str(error)}
        return result

    class Transport:
        def __init__(self, identifier):
            self.identifier = identifier
            self.machine = Machine(id=identifier, kind="local", root=str(tmp_path / identifier))

        def run(self, argv, payload, *, timeout):
            calls.append(("inspect", self.identifier, argv, payload, timeout))
            actual = inspect(**payload)
            actual.update(overrides.get(self.identifier, {}))
            return actual

    class Registry:
        def __init__(self, root):
            calls.append(("registry", str(root)))

        def machine(self, identifier):
            return Machine(id=identifier, kind="local", root=str(tmp_path / identifier))

        def check(self, identifier):
            calls.append(("check", identifier))
            result = records.get(
                identifier,
                {
                    "probe": {
                        "worker_id": "1" * 32,
                        "config_sha256": "b" * 64,
                        "capacity": {"cpus": 32},
                        "python": "3.12",
                        "protocol": "simjecture-worker/1",
                        "capabilities": {},
                    }
                },
            )
            if isinstance(result, Exception):
                raise result
            return result | {"machine": self.machine(identifier).model_dump()}

        def transport(self, identifier):
            return Transport(identifier)

        def prepare(self, *args):
            pytest.fail("Deployment check must not prepare workers")

        def freeze(self, *args):
            pytest.fail("Deployment check must not freeze an execution pool")

    monkeypatch.setattr(deployment_probe, "inspect_host", inspect)
    monkeypatch.setattr("conjecture_solver.execution_pool.MachineRegistry", Registry)
    return calls, records, overrides


def test_offline_plan_never_reads_artifacts_connects_or_starts_clock(tmp_path, monkeypatch):
    path, value = manifest(tmp_path)
    (tmp_path / "hypothesis.txt").unlink()

    def forbidden(*args, **kwargs):
        pytest.fail("Offline plan attempted a live operation")

    monkeypatch.setattr(deployment_probe, "inspect_host", forbidden)
    monkeypatch.setattr("conjecture_solver.execution_pool.MachineRegistry", forbidden)
    report = deployment.deployment_report(path)
    assert report.status == "planned"
    assert all(c.status == "planned" for c in report.checks)
    assert report.manifest_sha256 == digest(path)
    assert report.declared_study.model_dump() == value["study"]
    assert not report.study_created and report.scientific_qualification == "not_assessed"
    assert not (tmp_path / "machines").exists()
    assert not list(tmp_path.rglob("research.json"))


def test_ready_report_is_rechecked_and_relative_paths_follow_manifest(tmp_path, monkeypatch, hosts):
    path, _ = manifest(tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    report = deployment.deployment_report(path, check=True)
    assert report.status == "ready"
    assert all(c.status == "passed" for c in report.checks)
    assert items(report)["worker:node-a"].observed["capacity"] == {"cpus": 32}
    (tmp_path / "hypothesis.txt").write_text("Changed after preparation")
    again = deployment.deployment_report(path, check=True)
    assert again.status == "blocked"
    assert items(again)["file:hypothesis"].status == "failed"
    assert hosts[0].count(("check", "node-a")) == 2
    assert not list(tmp_path.rglob("research.json"))


def test_missing_optional_file_allowed_but_present_corruption_blocks(tmp_path, hosts):
    path, value = manifest(tmp_path)
    value["files"].append(
        {
            "id": "archive",
            "path": "large-archive",
            "sha256": "0" * 64,
            "required": False,
            "purpose": "prior_evidence",
        }
    )
    save(tmp_path, value)
    report = deployment.deployment_report(path, check=True)
    assert report.status == "ready" and items(report)["file:archive"].status == "skipped"
    (tmp_path / "large-archive").write_text("Unexpected bytes")
    report = deployment.deployment_report(path, check=True)
    assert report.status == "blocked" and items(report)["file:archive"].required


def test_optional_unreadable_file_is_not_treated_as_absent(tmp_path, monkeypatch, hosts):
    path, value = manifest(tmp_path)
    value["files"][0]["required"] = False
    save(tmp_path, value)

    def denied(*args):
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(deployment_probe, "file_identity", denied)
    assert deployment.deployment_report(path, check=True).status == "blocked"


def test_remote_file_hashes_use_saved_transport_and_literal_paths(tmp_path, hosts):
    unusual = tmp_path / 'table $(touch SHOULD_NOT_EXIST) "name".dat'
    unusual.write_bytes(b"private material bytes")
    path, value = manifest(tmp_path)
    value["files"].append(
        {
            "id": "material",
            "machine": "node-a",
            "path": str(unusual),
            "sha256": digest(unusual),
            "purpose": "material",
        }
    )
    save(tmp_path, value)
    report = deployment.deployment_report(path, check=True, timeout_seconds=240)
    assert report.status == "ready"
    call = next(c for c in hosts[0] if c[0] == "inspect")
    assert call[-1] == 240 and call[3]["files"][0]["path"] == str(unusual)
    assert str(unusual) not in call[2][2]  # File name is JSON stdin, never executable code.
    assert "private material bytes" not in report.model_dump_json()
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()


def test_unavailable_worker_does_not_hide_other_workers_or_claim_files_checked(tmp_path, hosts):
    from conjecture_solver.execution_pool import WorkerUnavailable

    path, value = manifest(tmp_path, workers=[{"id": "node-a"}, {"id": "node-b"}])
    value["files"].append(
        {"id": "restart", "machine": "node-a", "path": "/private/checkpoint", "sha256": "0" * 64}
    )
    save(tmp_path, value)
    hosts[1]["node-a"] = WorkerUnavailable("private-fixture-secret")
    report = deployment.deployment_report(path, check=True)
    assert report.status == "blocked"
    assert items(report)["file:restart"].status == "skipped"
    assert items(report)["worker:node-b"].status == "passed"
    assert "private-fixture-secret" not in report.model_dump_json()


@pytest.mark.parametrize(
    "difference",
    [
        {"python_source_sha256": "c" * 64},
        {"simjecture_version": "0.6.2"},
    ],
)
def test_worker_must_match_coordinator_even_without_explicit_source_pin(
    tmp_path, hosts, difference
):
    path, _ = manifest(tmp_path)
    hosts[2]["node-a"] = difference
    report = deployment.deployment_report(path, check=True)
    assert report.status == "blocked" and items(report)["code:node-a"].status == "failed"


def test_coordinator_version_and_source_pin_checked(tmp_path, hosts):
    path, _ = manifest(
        tmp_path, software={"simjecture_version": "0.6.2", "python_source_sha256": "0" * 64}
    )
    report = deployment.deployment_report(path, check=True)
    assert report.status == "blocked" and items(report)["coordinator"].status == "failed"


def test_config_storage_and_instrument_identity_all_reported(tmp_path, hosts):
    path, _ = manifest(
        tmp_path,
        workers=[
            {
                "id": "node-a",
                "config_sha256": "c" * 64,
                "minimum_free_bytes": 300 * 1024**3,
                "capabilities": [
                    {"name": "flash"},
                    {"name": "analysis", "contract_sha256": "c" * 64},
                ],
            }
        ],
    )
    hosts[1]["node-a"] = {
        "probe": {
            "worker_id": "1" * 32,
            "config_sha256": "b" * 64,
            "capacity": {"cpus": 32},
            "python": "3.12",
            "protocol": "simjecture-worker/1",
            "capabilities": {"analysis": {"contract_sha256": "d" * 64}},
        }
    }
    report = deployment.deployment_report(path, check=True)
    for key in [
        "worker:node-a",
        "storage:node-a",
        "capability:node-a:flash",
        "capability:node-a:analysis",
    ]:
        assert items(report)[key].status == "failed"
    assert report.scientific_qualification == "not_assessed"


@pytest.mark.parametrize("identity", [None, "invalid", "d" * 64])
def test_registered_instrument_requires_an_actual_identity(tmp_path, hosts, identity):
    from conjecture_solver.execution_pool import MachineRegistry

    path, _ = manifest(tmp_path, workers=[{"id": "node-a", "capabilities": [{"name": "flash"}]}])
    record = MachineRegistry(tmp_path / "machines").check("node-a")
    record["probe"]["capabilities"]["flash"] = {
        "contract_sha256": identity,
        "description": "Scientifically unqualified runtime",
    }
    hosts[1]["node-a"] = record
    report = deployment.deployment_report(path, check=True)
    assert report.status == ("ready" if identity == "d" * 64 else "blocked")
    assert report.scientific_qualification == "not_assessed"


@pytest.mark.parametrize(
    "alter",
    [
        lambda v: v.update(schema_version="unknown/2"),
        lambda v: v["workers"].append(v["workers"][0]),
        lambda v: v["files"].append(v["files"][0]),
        lambda v: v["files"][0].update(machine="missing-worker"),
        lambda v: v["files"][0].update(machine="node-a", path="relative-file"),
        lambda v: v["files"][0].update(machine="node-a", path="/root/../file"),
        lambda v: v["files"][0].update(sha256="not-a-hash"),
        lambda v: v["study"].update(initial_max_total_bytes=1),
        lambda v: v["study"].update(report_reserve_seconds=172800),
        lambda v: v["study"].update(wall_seconds=float("nan")),
        lambda v: v["study"].update(wall_seconds=True),
        lambda v: v["study"]["director"].update(backend="grok"),
        lambda v: v["study"].update(initial_max_total_bytes=True),
        lambda v: v.update(attention={"config_file": "missing"}),
    ],
)
def test_invalid_plans_rejected_without_network(tmp_path, hosts, alter):
    path, value = manifest(tmp_path)
    alter(value)
    save(tmp_path, value)
    with pytest.raises(ValueError, match="Invalid deployment manifest"):
        deployment.deployment_report(path, check=True)
    assert hosts[0] == []


def test_validation_error_does_not_echo_rejected_credentials(tmp_path):
    path, _ = manifest(tmp_path, password="do-not-log-this-secret")
    with pytest.raises(ValueError) as error:
        deployment.read_manifest(path)
    assert "do-not-log-this-secret" not in str(error.value)


def add_attention(tmp_path, value, *, required=True):
    config = tmp_path / "attention.json"
    config.write_text(
        json.dumps(
            {
                "mode": "alerts",
                "socket": "/private/model.sock",
                "auth_token_file": "/private/model.token",
            }
        )
    )
    value["files"].append(
        {
            "id": "attention",
            "path": config.name,
            "sha256": digest(config),
            "purpose": "attention_config",
        }
    )
    value["attention"] = {"config_file": "attention", "required": required}
    return save(tmp_path, value)[0], config


def test_attention_checks_identity_without_scoring_or_leaking_token(tmp_path, monkeypatch, hosts):
    from simjecture_monitor.tool import AttentionClient

    _, value = manifest(tmp_path)
    path, _ = add_attention(tmp_path, value)
    calls = []

    def health(self):
        calls.append("health")
        return {"ready": True, "policy": "conjecture1", "private-extra": "secret-fixture"}

    monkeypatch.setattr(AttentionClient, "health", health)
    monkeypatch.setattr(AttentionClient, "score", lambda *a: pytest.fail("No model inference"))
    report = deployment.deployment_report(path, check=True)
    assert report.status == "ready" and calls == ["health"]
    assert "secret-fixture" not in report.model_dump_json()
    assert any("warm-up" in limitation for limitation in report.unchecked)


@pytest.mark.parametrize("required", [True, False])
def test_attention_outage_respects_declared_requirement(tmp_path, monkeypatch, hosts, required):
    from simjecture_monitor.tool import AttentionClient

    _, value = manifest(tmp_path)
    path, _ = add_attention(tmp_path, value, required=required)

    def unavailable(self):
        raise ValueError("private-service-token")

    monkeypatch.setattr(AttentionClient, "health", unavailable)
    report = deployment.deployment_report(path, check=True)
    assert report.status == ("blocked" if required else "ready")
    assert "private-service-token" not in report.model_dump_json()


def test_modified_attention_config_prevents_contact(tmp_path, monkeypatch, hosts):
    from simjecture_monitor.tool import AttentionClient

    _, value = manifest(tmp_path)
    path, config = add_attention(tmp_path, value)
    config.write_text("Changed socket/token routing")
    monkeypatch.setattr(
        AttentionClient, "health", lambda *a: pytest.fail("Unverified configuration")
    )
    report = deployment.deployment_report(path, check=True)
    assert report.status == "blocked" and items(report)["attention"].status == "skipped"


def test_attention_reread_cannot_change_verified_service_routing(tmp_path, monkeypatch, hosts):
    from simjecture_monitor.tool import AttentionClient

    from conjecture_solver.execution_pool import MachineRegistry

    _, value = manifest(tmp_path)
    path, config = add_attention(tmp_path, value)
    original_check = MachineRegistry.check

    def intervening_change(self, identifier):
        config.write_text("Unverified new service routing")
        return original_check(self, identifier)

    monkeypatch.setattr(MachineRegistry, "check", intervening_change)
    monkeypatch.setattr(AttentionClient, "health", lambda *a: pytest.fail("Unverified service"))
    report = deployment.deployment_report(path, check=True)
    assert items(report)["file:attention"].status == "passed"
    assert items(report)["attention"].status == "failed" and report.status == "blocked"


def test_worker_profile_change_does_not_redirect_file_inspection(tmp_path, monkeypatch, hosts):
    from conjecture_solver.execution_pool import MachineRegistry

    path, _ = manifest(tmp_path)
    original_transport = MachineRegistry.transport

    def changed(self, identifier):
        transport = original_transport(self, identifier)
        transport.machine.root = "/changed-worker-root"
        return transport

    monkeypatch.setattr(MachineRegistry, "transport", changed)
    report = deployment.deployment_report(path, check=True)
    assert report.status == "blocked"
    assert not any(call[0] == "inspect" for call in hosts[0])


def test_bad_source_inspection_is_blocked_with_unchecked_items(tmp_path, hosts):
    path, _ = manifest(tmp_path)
    hosts[2]["node-a"] = {"files": None}
    report = deployment.deployment_report(path, check=True)
    assert report.status == "blocked"
    assert items(report)["code:node-a"].status == "skipped"


def test_coordinator_inspection_failure_does_not_claim_files_missing(tmp_path, monkeypatch, hosts):
    path, _ = manifest(tmp_path)

    def unavailable(*args):
        raise PermissionError("Private source cannot be read")

    monkeypatch.setattr(deployment_probe, "inspect_host", unavailable)
    report = deployment.deployment_report(path, check=True)
    assert report.status == "blocked"
    assert items(report)["file:hypothesis"].status == "skipped"
    assert items(report)["worker:node-a"].status == "passed"


def test_source_identity_covers_supporting_python_modules(tmp_path, monkeypatch):
    from types import SimpleNamespace

    source = tmp_path / "package"
    source.mkdir()
    (source / "__init__.py").write_text("")
    helper = source / "helper.py"
    helper.write_text("value=1\n")
    skill = source / "builtin_skills" / "example.py"
    skill.parent.mkdir()
    skill.write_text("skill_version=1\n")
    monkeypatch.setattr(
        deployment_probe.importlib.util,
        "find_spec",
        lambda _: SimpleNamespace(origin=str(source / "__init__.py")),
    )
    monkeypatch.setattr(deployment_probe.importlib.metadata, "version", lambda _: "0.7.0")
    first = deployment_probe.inspect_host([], str(tmp_path))["python_source_sha256"]
    helper.write_text("value=2\n")
    second = deployment_probe.inspect_host([], str(tmp_path))["python_source_sha256"]
    assert first != second
    skill.write_text("skill_version=2\n")
    assert deployment_probe.inspect_host([], str(tmp_path))["python_source_sha256"] == second


@pytest.mark.parametrize("seconds", [True, 0, -1, float("inf"), float("nan")])
def test_invalid_inspection_timeout_rejected_before_io(tmp_path, seconds):
    with pytest.raises(ValueError, match="timeout"):
        deployment.deployment_report(tmp_path / "absent", timeout_seconds=seconds)


def test_file_probe_refuses_fifo_and_detects_changes(tmp_path, monkeypatch):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="not_regular"):
        deployment_probe.file_identity(fifo)
    regular = tmp_path / "mutable"
    regular.write_text("before")
    real = os.fstat
    calls = 0

    def changing(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            regular.write_text("after changed")
        return real(fd)

    monkeypatch.setattr(os, "fstat", changing)
    with pytest.raises(ValueError, match="changed_during_check"):
        deployment_probe.file_identity(regular)


def test_cli_writes_new_report_and_refuses_overwrite_before_checks(tmp_path, hosts, capsys):
    path, _ = manifest(tmp_path)
    parser = argparse.ArgumentParser()
    deployment.configure_parser(parser)
    output = tmp_path / "readiness.json"
    args = parser.parse_args(["check", "--manifest", str(path), "--output", str(output)])
    assert args.handler(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert json.loads(output.read_text()) == report
    calls = copy.deepcopy(hosts[0])
    with pytest.raises(ValueError, match="new report"):
        args.handler(args)
    assert hosts[0] == calls
    (tmp_path / "hypothesis.txt").unlink()
    args.output = None
    assert args.handler(args) == 1


def test_actual_managed_local_worker_check_does_not_launch_research(tmp_path, monkeypatch):
    from conjecture_solver.execution_pool import MachineRegistry

    source = str(Path(deployment_probe.__file__).resolve().parents[1])
    monkeypatch.setenv("PYTHONPATH", source)
    registry = MachineRegistry(tmp_path / "machines")
    registry.save(
        {
            "id": "node-a",
            "kind": "local",
            "python": sys.executable,
            "root": str(tmp_path / "worker"),
            "config": {
                "execution_backend": "process-cooperative",
                "cpus": 2,
                "memory_mb": 2048,
                "max_jobs": 2,
            },
        }
    )
    registry.prepare("node-a")
    version = deployment_probe.importlib.metadata.version("simjecture")
    path, value = manifest(tmp_path, software={"simjecture_version": version})
    checkpoint = tmp_path / "worker/checkpoint"
    checkpoint.write_bytes(b"synthetic restart fixture")
    value["files"].append(
        {
            "id": "checkpoint",
            "machine": "node-a",
            "path": str(checkpoint),
            "sha256": digest(checkpoint),
            "purpose": "restart",
        }
    )
    save(tmp_path, value)
    before = list((tmp_path / "worker/jobs").iterdir())
    report = deployment.deployment_report(path, check=True)
    assert report.status == "ready", report.model_dump_json(indent=2)
    assert list((tmp_path / "worker/jobs").iterdir()) == before == []
    assert not list(tmp_path.rglob("research.json"))
    assert items(report)["file:checkpoint"].status == "passed"
