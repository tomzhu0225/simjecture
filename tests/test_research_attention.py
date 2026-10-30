import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from conjecture_solver import attention_cli, research_attention
from conjecture_solver.research_service import ResearchService
from conjecture_solver.study import configure_parser


def test_unconfigured_study_never_imports_model_package(monkeypatch):
    import builtins

    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("simjecture_monitor") or name in {"torch", "transformers"}:
            raise AssertionError("Normal study tried to load optional tooling")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert (
        research_attention.configure(
            SimpleNamespace(args=SimpleNamespace(), service=SimpleNamespace(manifest={}))
        )
        is None
    )


def test_catalogue_exposes_an_optional_attention_tool_without_a_solver(monkeypatch):
    monkeypatch.setattr(attention_cli.importlib.util, "find_spec", lambda name: None)
    card = attention_cli.catalogue_card()
    assert card["kind"] == "attention" and not card["installed"]
    assert card["action"] == "attention" and "variants" not in card
    assert "shadow" in card["description"]


def test_study_cli_has_explicit_config_and_no_automatic_activation():
    import argparse

    parser = argparse.ArgumentParser()
    configure_parser(parser)
    assert parser.parse_args(["--campaign", "/study"]).attention_config is None
    assert parser.parse_args(
        ["--campaign", "/study", "--attention-config", "/observer.json"]
    ).attention_config == Path("/observer.json")


def configured(tmp_path, mode="shadow", director=True):
    pytest.importorskip("simjecture_monitor")
    service = ResearchService.create(tmp_path / "study", "Check measured fields.")
    manifest = service.manifest | {"director_policy": {"enabled": director}}
    from conjecture_solver.research_service import put

    put(service.root / "research.json", manifest)
    service.manifest = manifest
    path = tmp_path / "attention.json"
    path.write_text(
        json.dumps(dict(mode=mode, socket="/private/model.sock", auth_token_file="/private/token"))
    )
    sup = SimpleNamespace(
        root=service.root,
        args=SimpleNamespace(attention_config=path),
        service=service,
        state={"deadline": service.manifest["deadline"], "status": "running"},
    )
    return sup, path


def test_real_study_observation_has_no_private_reasoning_and_uses_unknown_timing(tmp_path):
    sup, _ = configured(tmp_path)
    observer = research_attention.configure(sup)
    directory = tmp_path / "native"
    directory.mkdir()
    (directory / "response.json").write_text(
        "\n".join(
            json.dumps(e)
            for e in [
                dict(type="item.completed", item=dict(type="reasoning", text="PRIVATE_REASONING")),
                dict(
                    type="item.completed",
                    item=dict(type="agent_message", text="Submitted calculation"),
                ),
            ]
        )
        + "\n"
    )
    observer.directory = directory
    packet = observer.observe()
    assert "PRIVATE_REASONING" not in packet.model_dump_json()
    assert "Submitted calculation" in packet.model_dump_json()
    assert packet.timing.progress_age_ms is None
    assert packet.timing.quiet_state == "unknown"
    assert packet.worker_state == "active"
    sup.service.waiting_status = lambda: {"status": "waiting", "reason": "Requested wait"}
    assert observer.observe().worker_state == "active"
    observer.directory = None
    assert observer.observe().worker_state == "parked"
    assert "Submitted calculation" in observer.observe().model_dump_json()
    observer.close()


def test_alerts_require_director_and_resume_cannot_silently_change_policy(tmp_path):
    sup, path = configured(tmp_path, "alerts", director=False)
    with pytest.raises(ValueError, match="enabled research director"):
        research_attention.configure(sup)
    path.write_text(
        json.dumps(
            dict(mode="shadow", socket="/private/model.sock", auth_token_file="/private/token")
        )
    )
    instance = research_attention.configure(sup)
    instance.close()
    path.write_text(
        json.dumps(
            dict(mode="alerts", socket="/private/model.sock", auth_token_file="/private/token")
        )
    )
    with pytest.raises(ValueError, match="immutable"):
        research_attention.configure(sup)


def test_attention_dispatch_uses_existing_director_and_respects_host_boundaries(tmp_path):
    sup, _ = configured(tmp_path, "alerts")
    observer = research_attention.configure(sup)
    launched = []
    sup.boundary = lambda: False
    sup.save = lambda: None

    def director(**kwargs):
        launched.append(kwargs)
        sup.state["director_count"] = sup.state.get("director_count", 0) + 1
        return False  # Existing asynchronous director API reports launch this way.

    sup.run_director = director
    decision = {"action": "wake_director", "authority": "attention_only"}
    assert observer.dispatch(decision, observer.observe().model_dump())
    assert launched == [dict(force=True, background=True)]
    assert sup.state["attention_notice"]["authority"] == "Unreviewed attention request only"
    sup.boundary = lambda: True
    assert not observer.dispatch(decision, {})
    assert len(launched) == 1
    observer.close()


def test_experiment_evidence_compacts_artifacts_and_ignores_heartbeat_churn(tmp_path):
    from conjecture_solver.research_service import put

    sup, _ = configured(tmp_path)
    observer = research_attention.configure(sup)
    exp_a = sup.root / "experiments" / "exp_0001.json"
    exp_b = sup.root / "experiments" / "exp_0002.json"
    record_a = dict(
        id="exp_0001",
        created_at=100.0,
        status="running",
        artifacts={f"cache/file_{i}.dat": "a" * 64 for i in range(40)},
        binding=dict(capability="python-3", inputs={"in.dat": "b" * 64}, runtime_sha256="c" * 64),
        execution_heartbeat=dict(elapsed_wall_seconds=10.0, observed_at=110.0),
        telemetry=dict(
            status="ok",
            value=2.5,
            target=10.0,
            observed_at=110.0,
            elapsed_seconds=10.0,
            estimated_additional_seconds=30.0,
        ),
        execution=dict(
            returncode=0,
            timed_out=False,
            stdout="x" * 40000,
            stderr="y" * 40000,
        ),
    )
    record_b = dict(id="exp_0002", created_at=101.0, status="running")
    put(exp_a, record_a)
    put(exp_b, record_b)
    first = observer.observe()
    receipts = {
        e.id: json.loads(e.content) for e in first.evidence if e.id.startswith("experiments_")
    }
    assert receipts["experiments_0"]["id"] == "exp_0001"
    assert receipts["experiments_0"]["status"] == "running"
    assert receipts["experiments_0"]["telemetry"]["value"] == 2.5
    assert "artifacts" not in receipts["experiments_0"]
    assert receipts["experiments_1"]["id"] == "exp_0002"
    # Heartbeat-only update that also flips mtime order between exp_0001 and exp_0002
    record_a["execution_heartbeat"] = dict(elapsed_wall_seconds=15.0, observed_at=115.0)
    record_a["telemetry"]["observed_at"] = 115.0
    record_a["telemetry"]["elapsed_seconds"] = 15.0
    put(exp_a, record_a)
    second = observer.observe()
    assert second.state_revision == first.state_revision
    observer.close()


def test_multi_alert_campaign_advances_incident_id_only_after_state_changes(tmp_path):
    from conjecture_solver.research_service import put

    sup, _ = configured(tmp_path, "alerts")
    observer = research_attention.configure(sup)
    exp = sup.root / "experiments" / "exp_0001.json"
    put(exp, dict(id="exp_0001", created_at=100.0, status="running"))
    assert observer.observe().incident_id == "study-attention"
    observer.observer.state["attempts"].append(
        dict(scope=["main-worker", "study", "study-attention"], at=100.0, status="dispatched")
    )
    observer.observer.save()
    # Unchanged state keeps the same incident_id even across restart
    assert observer.observe().incident_id == "study-attention"
    observer.close()
    restored = research_attention.configure(sup)
    assert restored.observe().incident_id == "study-attention"
    # While background director is pending, incident_id still does not advance
    sup._director_pending = {"future": SimpleNamespace(done=lambda: False)}
    put(exp, dict(id="exp_0001", created_at=100.0, status="completed"))
    assert restored.observe().incident_id == "study-attention"
    # Once director finishes and state has changed, incident_id advances for the next alert
    sup._director_pending = None
    assert restored.observe().incident_id == "study-attention-2"
    restored.close()


def test_dispatch_clears_unlaunched_notice_and_active_worker_tick_preserves_wake_flag(tmp_path):
    sup, _ = configured(tmp_path, "alerts")
    observer = research_attention.configure(sup)
    sup.boundary = lambda: False
    sup.save = lambda: None
    sup.run_director = lambda **kwargs: False  # Declines without incrementing director_count
    assert not observer.dispatch({"action": "wake_director"}, {})
    assert "attention_notice" not in sup.state
    # During an active worker turn (directory is not None), tick() must not harvest
    # _director_pending or consume director_wake_worker prematurely.
    harvested = []
    sup.run_director = lambda **kwargs: harvested.append(kwargs)
    sup._director_pending = {"future": SimpleNamespace(done=lambda: True)}
    sup.state["director_wake_worker"] = True
    observer.observer.tick = lambda observe, dispatch: None
    observer.tick(directory=tmp_path)
    assert harvested == []
    assert sup.state.get("director_wake_worker") is True
    observer.tick(directory=None)
    assert harvested == [dict(background=True)]
    assert "director_wake_worker" not in sup.state
    observer.close()
