"""Simple onboarding, genuine lightweight checks, and retained setup provenance."""

import json
import sys
import threading
import time

import pytest

from conjecture_solver.execution_pool import MachineRegistry, Transport, WorkerUnavailable
from conjecture_solver.machine_availability import POLL_SECONDS, check_availability
from conjecture_solver.machine_setup import basic_profile, parse_address
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from conjecture_solver.worker_protocol import load


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("ssh -p 23 root@host.example", {"host": "host.example", "port": 23, "user": "root"}),
        ("root@host.example:23", {"host": "host.example", "port": 23, "user": "root"}),
        (
            "ssh://scientist@host.example:2222",
            {"host": "host.example", "port": 2222, "user": "scientist"},
        ),
        ("ssh -p23 root@127.0.0.1", {"host": "127.0.0.1", "port": 23, "user": "root"}),
        ("ssh -l scientist gpu-box", {"host": "gpu-box", "port": 22, "user": "scientist"}),
        ("gpu-box", {"host": "gpu-box", "port": 22, "user": ""}),
        ("root@[2001:db8::1]:23", {"host": "2001:db8::1", "port": 23, "user": "root"}),
    ],
)
def test_common_ssh_address_formats(address, expected):
    assert parse_address(address) == expected


@pytest.mark.parametrize(
    "address",
    [
        "",
        "ssh -oProxyCommand=evil host",
        "ssh host reboot",
        "user:secret@host",
        "ssh -p 0 root@host",
        "host/path",
        "ssh -p 99999 root@host",
        "-evil",
        "host?command=evil",
    ],
)
def test_addresses_cannot_inject_commands_or_embed_credentials(address):
    with pytest.raises(ValueError):
        parse_address(address)


def test_automatic_profile_defaults_and_explicit_overrides(tmp_path):
    profile = basic_profile("ssh -p 23 root@host")
    assert profile["automatic_setup"]["execution_backend"] == "auto"
    assert profile["automatic_setup"]["gpu_ids"] is None
    overridden = basic_profile(
        "root@host:23", {"memory_mb": 2048, "gpu_ids": [], "execution_backend": "bubblewrap"}
    )
    assert overridden["id"] == profile["id"]
    assert overridden["config"]["memory_mb"] == 2048
    assert overridden["automatic_setup"]["gpu_ids"] == []
    registry = MachineRegistry(tmp_path)
    stored = registry.save(profile)["machine"]
    assert stored["known_hosts"].startswith(str(tmp_path / ".private"))
    assert (tmp_path / ".private/known_hosts").stat().st_mode & 0o777 == 0o600
    command = registry.transport(stored["id"]).command(["true"])
    assert "StrictHostKeyChecking=accept-new" in command


def local_worker(tmp_path):
    registry = MachineRegistry(tmp_path / "machines")
    registry.save(
        {
            "id": "local",
            "kind": "local",
            "root": str(tmp_path / "worker"),
            "python": sys.executable,
            "config": {"cpus": 1, "memory_mb": 2048, "max_jobs": 1},
        }
    )
    from conjecture_solver.execution import probe_execution_backend

    if not probe_execution_backend("bubblewrap")["available"]:
        pytest.skip("Real launcher needs Bubblewrap namespaces")
    registry.prepare("local")
    return registry


def test_heartbeat_does_not_launch_an_experiment_and_records_outage_recovery(tmp_path, monkeypatch):
    registry = local_worker(tmp_path)
    health = tmp_path / "worker/health/worker_probe.json"
    before = health.stat().st_mtime_ns
    real_call = Transport.call
    methods = []

    def call(self, method, **kwargs):
        methods.append(method)
        return real_call(self, method, **kwargs)

    monkeypatch.setattr(Transport, "call", call)
    result = check_availability(registry, "local")
    assert result["online"] and result["status"] == "ready"
    assert methods == ["heartbeat"] and health.stat().st_mtime_ns == before

    def outage(*args, **kwargs):
        raise WorkerUnavailable("Controlled outage")

    monkeypatch.setattr(Transport, "call", outage)
    assert check_availability(registry, "local")["status"] == "offline"
    assert registry.public("local")["availability"]["online"] is False
    monkeypatch.setattr(Transport, "call", real_call)
    assert check_availability(registry, "local")["status"] == "ready"
    assert health.stat().st_mtime_ns == before


def test_server_polls_every_thirty_seconds_without_browser_requests(tmp_path):
    app = SimjectureWebApplication(
        runs_root=tmp_path / "runs", scan_roots=(tmp_path,), allow_mutations=False
    )
    calls = []
    event = threading.Event()

    def poll():
        calls.append(time.monotonic())
        event.set()

    app.workspace.poll_machine_availability = poll
    server = create_server(app, port=0)
    try:
        server.service_actions()
        assert event.wait(2)
        first = server._machine_poll_at
        assert 28 < first - time.monotonic() <= POLL_SECONDS == 30
        server.service_actions()
        assert len(calls) == 1
        event.clear()
        server._machine_poll_thread.join(timeout=2)
        server._machine_poll_at = time.monotonic() - 1
        server.service_actions()
        assert event.wait(2) and len(calls) == 2
        assert not app.workspace.machine_registry.root.exists()
    finally:
        server.server_close()


def test_agent_setup_conversation_contains_no_credentials_and_commands_are_recorded(tmp_path):
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    r = app.workspace.machine_registry
    r.save(
        {
            "id": "local",
            "kind": "local",
            "root": str(tmp_path / "worker"),
            "python": sys.executable,
            "password": "private-fixture-only",
        }
    )
    prepared = app.workspace.prepare_machine_chat(
        {"id": "local", "goal": "Inspect the Python runtime"}
    )
    assert "execution_machine_command" in prepared["prompt"]
    assert "private-fixture-only" not in json.dumps(prepared)
    assert not list(app.workspace.projects_root.glob("*/turns/*"))
    record = app.workspace.machine_command("local", "python3 -c 'print(2+2)'", 5)
    assert record["status"] == "succeeded" and record["stdout"].strip() == "4"
    assert record["scientific_status"] == "not_evidence"
    saved = r.root / "maintenance" / f"{record['id']}.json"
    assert load(saved) == record and saved.stat().st_mode & 0o777 == 0o600
