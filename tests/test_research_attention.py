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


def test_long_poll_confirmations_reach_the_background_director(tmp_path, monkeypatch):
    import time
    from concurrent.futures import Future

    from simjecture_monitor import attention_support as protocol

    from conjecture_solver.agent_supervisor import AgentSupervisor
    from tests.test_research_director import supervisor

    clock = [1000.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    sup = supervisor(tmp_path)
    sup.args.attention_config = tmp_path / "attention.json"
    sup.args.attention_config.write_text(json.dumps(dict(
        mode="alerts", socket="/private/model.sock", auth_token_file="/private/token",
        poll_seconds=60.0,
    )))
    attention = research_attention.configure(sup)

    class Immediate:
        def submit(self, function, *args):
            future = Future()
            future.set_result(function(*args))
            return future

        def shutdown(self, **kwargs):
            pass

    class Client:
        def score(self, observation):
            view = protocol.pack(
                observation, len, token_counter_id="fixture", budget_tokens=1000000
            )
            choice = protocol.Choice(
                action="wake_director", support_kind="none", question_ref=None,
                basis="measurement", evidence=[next(iter(view.aliases))],
            )
            return dict(
                view=view.model_dump(),
                decision=protocol.bind_choice(
                    observation, view, choice, policy_id="fixture"
                ).model_dump(),
            )

    launched = []

    def launch(runner, directory, prompt, **kwargs):
        launched.append((directory, kwargs))
        return 0

    monkeypatch.setattr(AgentSupervisor, "launch", launch)
    attention.observer.executor.shutdown()
    attention.observer.executor = Immediate()
    attention.observer.client = Client()
    try:
        for at in (1000, 1001, 1060, 1061):
            clock[0] = at
            attention.observer.tick(attention.observe, attention.dispatch)
        pending = sup._director_pending
        assert pending is not None
        assert pending["future"].result(timeout=5) == 0
        assert len(launched) == 1
        assert launched[0][1] == {"judge": True, "director": True}
        assert sup.state["director_count"] == 1
        assert pending["packet"]["attention_request"] == sup.state["attention_notice"]
        assert attention.observer.state["attempts"][0]["status"] == "dispatched"
        assert attention.observer.state["requests"] == 2
        assert sup.service._all("reviews") == []
    finally:
        attention.close()
        if hasattr(sup, "_director_executor"):
            sup._director_executor.shutdown(wait=True)


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


def test_selection_uses_creation_order_before_limit_and_heartbeat_does_not_reopen(tmp_path):
    from conjecture_solver.research_service import put

    sup, _ = configured(tmp_path, "alerts")
    observer = research_attention.configure(sup)
    paths = []
    for index in range(6):
        path = sup.root / "experiments" / f"exp_{index}.json"
        put(path, dict(id=f"exp_{index}", created_at=index + 1, status="running"))
        paths.append(path)
    first = observer.observe()
    ids = [json.loads(e.content)["id"] for e in first.evidence if e.id.startswith("experiments_")]
    assert ids == ["exp_2", "exp_3", "exp_4", "exp_5"]
    observer.observer.state["attempts"].append(
        dict(scope=list(first.scope()), status="reserved", at=100)
    )
    observer.observer.save()
    put(paths[0], dict(id="exp_0", created_at=1, status="running",
                       execution_heartbeat={"observed_at": 100}))
    second = observer.observe()
    assert second.state_revision == first.state_revision
    assert second.incident_id == first.incident_id
    assert [json.loads(e.content)["id"] for e in second.evidence
            if e.id.startswith("experiments_")] == ids
    observer.close()


def test_restart_losing_worker_excerpt_does_not_bypass_reserved_attempt(tmp_path):
    sup, _ = configured(tmp_path, "alerts")
    instance = research_attention.configure(sup)
    directory = tmp_path / "turn"
    directory.mkdir()
    (directory / "response.json").write_text(json.dumps(dict(
        type="item.completed", item=dict(type="agent_message", text="public result")
    )) + "\n")
    instance.directory = directory
    before = instance.observe()
    assert any(e.id.startswith("worker_event_") for e in before.evidence)
    instance.observer.state["attempts"].append(
        dict(scope=list(before.scope()), status="reserved", at=100)
    )
    instance.observer.save()
    instance.close()
    restored = research_attention.configure(sup)
    after = restored.observe()
    assert not any(e.id.startswith("worker_event_") for e in after.evidence)
    assert after.scope() == before.scope()
    assert restored.observer.state["attempts"][0]["status"] == "reserved"
    restored.close()


def test_operational_timing_distinguishes_heartbeat_from_measured_progress(tmp_path, monkeypatch):
    from conjecture_solver.research_service import put

    sup, _ = configured(tmp_path)
    observer = research_attention.configure(sup)
    path = sup.root / "experiments" / "exp_1.json"
    clock = [1000.0]
    monkeypatch.setattr(research_attention.time, "time", lambda: clock[0])
    record = dict(id="exp_1", created_at=900, started_at=900, status="running",
                  execution_heartbeat=dict(observed_at=999),
                  telemetry=dict(available=True, value=2.0, observed_at=999, elapsed_seconds=99))
    put(path, record)
    first = observer.observe()
    assert first.timing.phase_elapsed_ms == 100000
    assert first.timing.heartbeat_age_ms == 1000
    assert first.timing.progress_age_ms == 0
    clock[0] += 3600
    record["execution_heartbeat"]["observed_at"] = clock[0] - 1
    record["telemetry"].update(observed_at=clock[0] - 1, elapsed_seconds=3699)
    put(path, record)
    later = observer.observe()
    assert later.state_revision == first.state_revision
    assert later.timing.heartbeat_age_ms == 1000
    assert later.timing.progress_age_ms == 3600000
    observer.close()
    restored = research_attention.configure(sup)
    assert restored.observe().timing.progress_age_ms == 3600000
    record["telemetry"]["value"] = 3.0
    put(path, record)
    assert restored.observe().timing.progress_age_ms == 0
    restored.close()


@pytest.mark.parametrize("launched", [False, True])
def test_dispatch_exception_restores_notice_only_when_launch_not_indicated(tmp_path, launched):
    sup, _ = configured(tmp_path, "alerts")
    observer = research_attention.configure(sup)
    sup.boundary = lambda: False
    sup.save = lambda: None
    original = {"previous": "notice"}
    sup.state["attention_notice"] = original

    def director(**kwargs):
        # run_director reserves a count even if creating its directory fails.
        sup.state["director_count"] = 1
        if launched:
            sup._director_pending = {"future": object()}
        raise OSError("indeterminate launch")

    sup.run_director = director
    with pytest.raises(OSError, match="indeterminate"):
        observer.dispatch({"action": "wake_director"}, {})
    if launched:
        assert sup.state["attention_notice"]["authority"] == "Unreviewed attention request only"
    else:
        assert sup.state["attention_notice"] == original
    observer.close()


def test_failed_director_dispatch_keeps_reserved_scope_after_real_observer_restart(tmp_path):
    from concurrent.futures import Future

    from simjecture_monitor import attention_support as protocol

    sup, _ = configured(tmp_path, "alerts")
    attention = research_attention.configure(sup)
    directory = tmp_path / "turn"
    directory.mkdir()
    (directory / "response.json").write_text(json.dumps(dict(
        type="item.completed", item=dict(type="agent_message", text="Public event")
    )) + "\n")
    attention.directory = directory
    submitted = attention.observe()
    view = protocol.pack(submitted, len, token_counter_id="test", budget_tokens=1000000)
    choice = protocol.Choice(action="wake_director", support_kind="none", question_ref=None,
                             basis="measurement", evidence=[next(iter(view.aliases))])
    future = Future()
    future.set_result(dict(view=view.model_dump(), decision=protocol.bind_choice(
        submitted, view, choice, policy_id="test").model_dump()))
    attention.observer.pending = (future, submitted)
    attention.observer.gate.evaluate = lambda *args, **kwargs: {"disposition": "admitted"}
    attention.observer.next_poll = float("inf")
    sup.boundary = lambda: False
    sup.save = lambda: None
    sup.run_director = lambda **kwargs: (_ for _ in ()).throw(OSError("launch failed"))
    attention.observer.tick(attention.observe, attention.dispatch)
    attempts = attention.observer.state["attempts"]
    assert len(attempts) == 1 and attempts[0]["status"] == "reserved"
    assert "attention_notice" not in sup.state
    attention.close()
    restored = research_attention.configure(sup)
    assert list(restored.observe().scope()) == attempts[0]["scope"]
    assert restored.observer.state["attempts"] == attempts
    restored.close()


@pytest.mark.parametrize("status", ["reserved", "dispatched"])
def test_legacy_incident_migration_preserves_attempt_and_advances_after_change(tmp_path, status):
    from conjecture_solver.research_service import put

    sup, _ = configured(tmp_path, "alerts")
    observer = research_attention.configure(sup)
    path = sup.root / "experiments" / "exp_1.json"
    put(path, dict(id="exp_1", created_at=1, status="running"))
    initial = observer.observe()
    observer.observer.state["attempts"].append(
        dict(scope=list(initial.scope()), status=status, at=100)
    )
    observer.observer.state.pop("incident_semantic_version")
    observer.observer.save()
    observer.close()
    restored = research_attention.configure(sup)
    assert restored.observe().scope() == initial.scope()
    put(path, dict(id="exp_1", created_at=1, status="failed"))
    assert restored.observe().incident_id == "study-attention-2"
    assert restored.observer.state["attempts"][0]["status"] == status
    restored.close()


@pytest.mark.parametrize("newer_notice", [False, True])
def test_real_background_launch_failure_clears_only_matching_notice(
    tmp_path, monkeypatch, newer_notice
):
    import time

    from conjecture_solver.agent_supervisor import AgentSupervisor
    from tests.test_research_director import supervisor

    sup = supervisor(tmp_path)
    sup.args.attention_config = tmp_path / "attention.json"
    sup.args.attention_config.write_text(json.dumps(dict(
        mode="alerts", socket="/private/model.sock", auth_token_file="/private/token"
    )))
    attention = research_attention.configure(sup)
    monkeypatch.setattr(
        AgentSupervisor, "launch",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("missing executable")),
    )
    assert attention.dispatch({"action": "wake_director"}, {})
    pending = sup._director_pending
    assert pending is not None
    saved_notice = pending["packet"]["attention_request"]
    assert saved_notice == sup.state["attention_notice"]
    with pytest.raises(FileNotFoundError):
        pending["future"].result(timeout=5)
    replacement = {"created_at": time.time(), "decision": "newer"}
    if newer_notice:
        sup.state["attention_notice"] = replacement
    assert not sup.run_director(background=True)
    assert sup._director_pending is None
    assert "missing executable" in sup.state["last_director_error"]
    if newer_notice:
        assert sup.state["attention_notice"] == replacement
    else:
        assert "attention_notice" not in sup.state
    attention.close()
    sup._director_executor.shutdown(wait=True)
