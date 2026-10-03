import argparse
import json
import time

import pytest

from conjecture_solver.research_control import ExperimentMonitor, read_monitor
from conjecture_solver.research_director import DirectorVerdict
from conjecture_solver.research_service import ResearchService
from conjecture_solver.research_supervisor import ResearchSupervisor


def supervisor(tmp_path):
    s = ResearchService.create(tmp_path / "study", "A full physical trajectory", wall_seconds=900)
    instructions = tmp_path / "instructions.txt"
    instructions.write_text(
        "Complete an affordable trajectory then refine; no fixed phase schedule."
    )
    args = argparse.Namespace(
        campaign=s.root,
        state_dir=s.root / "supervisor",
        wall_seconds=900,
        instructions_file=instructions,
        backend="codex",
        model="worker",
        judge_model="director",
        director_enabled=True,
    )
    sup = ResearchSupervisor(args)
    (s.work / "calc.py").write_text("print(1)\n")
    return sup


def active(sup, monkeypatch):
    monkeypatch.setattr(sup.service, "_spawn_experiment", lambda record: None)
    r = sup.service.run("calc.py", outputs=["result.json"], stage="exploration", timeout=700)
    return r


def answer(sup, monkeypatch, stops, decision="replan"):
    verdict = dict(
        decision=decision,
        rationale="The measured configuration cannot cover the target in budget.",
        scientific_feasibility="limited",
        budget_feasibility="infeasible",
        stop_experiments=stops,
        next_action=(
            "Commission a cheaper complete trajectory with adaptive stepping and accuracy checks."
        ),
    )

    def launch(directory, prompt, **kwargs):
        assert kwargs["judge"]
        assert sup.args.turn_seconds <= 120
        assert "MVP research strategy" in prompt
        (directory / "response.json").write_text(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": json.dumps(verdict)},
                }
            )
            + "\n"
            + json.dumps({"type": "turn.completed", "usage": {}})
            + "\n"
        )
        return 0

    monkeypatch.setattr(sup, "launch", launch)


def test_director_stops_named_experiment_and_requires_artifact_plan(tmp_path, monkeypatch):
    sup = supervisor(tmp_path)
    sup.args.turn_seconds = 1200
    r = active(sup, monkeypatch)
    answer(sup, monkeypatch, [r["id"]])
    assert sup.run_director(force=True)
    assert sup.args.turn_seconds == 1200
    assert sup.service._read("experiments", r["id"])["cancel_requested"]
    d = sup.service.director_status()[0]
    assert d["control_actions"][0]["experiment"] == r["id"]
    with pytest.raises(ValueError, match="Director requested"):
        sup.service.run("calc.py", outputs=["result.json"], stage="exploration", key="new")
    with pytest.raises(ValueError, match="Record lab.note"):
        sup.service.director_ack(d["id"], response="plan", reason="Use a cheaper timing pilot.")
    plan = sup.service.note(
        "Adaptive trajectory with a bounded accuracy comparison.",
        kind="next_test",
        estimated_seconds=60,
    )
    sup.service.director_ack(
        d["id"],
        response="plan",
        plan=plan["id"],
        reason="This short pilot will test the proposed affordable path.",
    )
    assert (
        sup.service.run("calc.py", outputs=["result.json"], stage="exploration", key="new")[
            "status"
        ]
        == "queued"
    )
    assert not sup.service.status()["completed"]


def test_director_rejects_unknown_stop_before_any_actions(tmp_path, monkeypatch):
    sup = supervisor(tmp_path)
    r = active(sup, monkeypatch)
    answer(sup, monkeypatch, [r["id"], "exp_unknown"])
    assert not sup.run_director(force=True)
    assert not sup.service._read("experiments", r["id"]).get("cancel_requested")
    assert sup.service.director_status() == []


def test_director_can_redirect_planning_without_experiments(tmp_path, monkeypatch):
    sup = supervisor(tmp_path)
    sup.state.update(round=2, last_director_at=time.time() - 400)
    answer(sup, monkeypatch, [])
    assert sup.run_director()
    assert sup.service.director_status()[0]["decision"] == "replan"
    assert not sup.service._all("experiments")


def test_strategy_review_runs_while_waiting_and_wakes_worker(tmp_path, monkeypatch):
    sup = supervisor(tmp_path)
    r = active(sup, monkeypatch)
    sup.state["waiting_for"] = [r["id"]]
    sup.state["last_director_at"] = time.time() - 400
    answer(sup, monkeypatch, [])
    original = sup.launch
    worker = []

    def launch(directory, prompt, **kwargs):
        if kwargs.get("judge"):
            return original(directory, prompt, **kwargs)
        worker.append(prompt)
        sup.cancelled = True
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    monkeypatch.setattr(sup, "maintain_journal", lambda: None)
    monkeypatch.setattr("conjecture_solver.research_supervisor.write_report", lambda *args: None)
    monkeypatch.setattr(sup.service, "cancel_active", lambda: None)
    assert sup.run() == 0
    assert worker and sup.service.director_status()[0]["decision"] == "replan"


def test_flash_live_timing_is_not_claim_evidence(tmp_path):
    (tmp_path / "execution.log").write_text("1 2.0000E-12 2.0000E-12 ( 0, 0, 0 ) | 1e-10\n")
    m = {"path": "execution.log", "format": "flash", "target": 20.0, "unit": "ns"}
    r = read_monitor(tmp_path, m, 100)
    assert r["value"] == pytest.approx(0.002)
    assert r["estimated_additional_seconds"] == pytest.approx(999900)
    assert "not scientific evidence" in r["authority"]
    (tmp_path / "execution.log").write_text("incomplete log")
    assert not read_monitor(tmp_path, m, 100)["available"]


@pytest.mark.parametrize("path", ["../outside", "/etc/passwd"])
def test_monitor_cannot_escape_workspace(path):
    with pytest.raises(ValueError):
        ExperimentMonitor(path=path, target=20.0)


def test_continue_cannot_stop_jobs():
    with pytest.raises(ValueError):
        DirectorVerdict(
            decision="continue",
            rationale="A valid science rationale.",
            scientific_feasibility="unknown",
            budget_feasibility="unknown",
            stop_experiments=["exp_a"],
            next_action="Keep this useful bounded experiment running.",
        )


def test_director_receives_operator_steering_and_claim_remains_fixed(tmp_path):
    from conjecture_solver.research_continuation import submit

    sup = supervisor(tmp_path)
    submit(sup.root, "Keep this bounded accuracy comparison; stop the costly refinement.")
    p = sup.director_packet()
    assert p["operator_steering"][0]["message"].startswith("Keep this bounded")
    assert p["original_hypothesis"] == "A full physical trajectory"


def test_director_launch_policy_is_explicit_and_boolean():
    from conjecture_solver.study_launch import NativeStudyRequest

    arguments = dict(
        hypothesis="A finite claim.", output_directory="new-study", campaign_id="new-study"
    )
    assert NativeStudyRequest(**arguments).director_enabled
    assert not NativeStudyRequest(**arguments, director_enabled=False).director_enabled
    with pytest.raises(ValueError):
        NativeStudyRequest(**arguments, director_enabled="false")


def test_pre_director_launch_resumes_with_its_old_policy(tmp_path):
    import sys

    from conjecture_solver.research_service import put
    from conjecture_solver.study_launch import NativeStudyRequest, materialize_native, resume_native

    request = NativeStudyRequest(
        hypothesis="A finite claim.",
        campaign_id="legacy",
        output_directory=str(tmp_path / "study"),
        model="fixture",
        agent_executable=sys.executable,
        director_enabled=False,
    )
    materialize_native(request)
    p = tmp_path / "study" / "study-launch.json"
    saved = json.loads(p.read_text())
    saved["request"].pop("director_enabled")
    saved["argv"].remove("--no-director")
    put(p, saved)
    resumed = resume_native(p.parent)
    assert resumed.request.director_enabled is False
    assert "--no-director" in resumed.argv
    with pytest.raises(ValueError, match="contract differs"):
        materialize_native(request.model_copy(update={"director_enabled": True}), resume=True)


def test_real_live_monitor_and_targeted_stop_preserve_partial_data(tmp_path):
    import os

    if os.geteuid() == 0:
        pytest.skip("Native cooperative execution requires an unprivileged account")
    s = ResearchService.create(
        tmp_path / "native",
        "A complete trajectory",
        wall_seconds=90,
        execution_backend="process-cooperative",
    )
    (s.work / "slow.py").write_text(
        "import time,json\nfrom pathlib import Path\n"
        "Path('progress.json').write_text(json.dumps({'value':2}))\n"
        "time.sleep(60)\nPath('final.json').write_text('{}')\n"
    )
    (s.work / "fast.py").write_text(
        "from pathlib import Path\nPath('result.json').write_text('{}')\n"
    )
    first = s.run(
        "slow.py",
        outputs=["progress.json", "final.json"],
        timeout=65,
        monitor={"path": "progress.json", "target": 40.0},
        stage="exploration",
    )
    second = s.run("fast.py", outputs=["result.json"], stage="exploration")
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            r = s._read("experiments", first["id"])
            if r.get("telemetry", {}).get("available"):
                break
            time.sleep(0.1)
        assert r["telemetry"]["value"] == 2
        assert r["telemetry"]["estimated_additional_seconds"] > 0
        s.cancel(first["id"], reason="Measured trajectory exceeds the remaining budget.")
        while time.monotonic() < deadline:
            r = s._read("experiments", first["id"])
            other = s._read("experiments", second["id"])
            if r["status"] == "cancelled" and other["status"] == "succeeded":
                break
            time.sleep(0.1)
        assert r["cancellation_confirmed"]
        assert r["execution"]["cancelled"]
        assert "progress.json" in r["artifacts"]
        assert "final.json" not in r["artifacts"]
        assert other["status"] == "succeeded"
        assert not s.status()["completed"]
    finally:
        s.cancel_active()


def test_legacy_worker_request_identity_omits_absent_monitor():
    from conjecture_solver.worker_protocol import Experiment, fingerprint

    body = dict(
        id="job_" + "a" * 40,
        binding={"source": "calc.py", "inputs": {"calc.py": "b" * 64}, "args": []},
        outputs=["result.json"],
        deadline=time.time() + 100,
        timeout=30,
        config_sha256="c" * 64,
    )
    old = Experiment.model_validate(body).model_dump(mode="json")
    assert "monitor" not in old
    assert fingerprint(Experiment.model_validate(old).model_dump(mode="json")) == fingerprint(old)
    monitored = Experiment.model_validate(
        body | {"monitor": {"path": "progress.json", "target": 40.0}}
    )
    assert fingerprint(monitored.model_dump(mode="json")) != fingerprint(old)


def test_native_uuid_usage_retains_its_director_role(tmp_path):
    import sys

    from conjecture_solver.study_status import study_status

    sup = supervisor(tmp_path)
    agent = tmp_path / "codex-fixture"
    agent.write_text(
        f"#!{sys.executable}\nimport json\n"
        "print(json.dumps({'type':'thread.started','thread_id':'native-uuid'}))\n"
        "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':123,'output_tokens':7}}))\n"
    )
    agent.chmod(0o755)
    sup.args.executable = str(agent)
    sup.args.turn_seconds = 10
    d = sup.directory / "director-00001"
    d.mkdir()
    assert sup.launch(d, "Return a fixture decision.", judge=True) == 0
    totals = study_status(sup.root)
    assert totals["usage"]["input_tokens"] == 123
    assert totals["usage_details"]["by_role"]["director"]["input_tokens"] == 123
    assert totals["usage_details"]["request_count_complete"] is False
    assert "other" not in totals["usage_details"]["by_role"]
