"""Actual helper process lifecycle, immutable handoffs and parent-worker recovery."""

import json
import os
import signal
import time

import pytest

from conjecture_solver.research_helpers import HelperAssignment, HelpReply, finish_helper
from conjecture_solver.research_service import ResearchService, put
from tests.test_research_director import supervisor


def request(service, **kwargs):
    return service.request_help(
        "Inspect the timestep calculation and supply a tested correction",
        success_criteria="Return a corrected function and its regression check",
        context="The parent found a discrepancy; inherited results are unreviewed.",
        files=["calc.py"],
        **kwargs,
    )


def assignment(identifier, name="answer.txt", **kwargs):
    return HelperAssignment(
        request=identifier,
        task="Independently inspect the supplied calculation and write " + name,
        completion_criteria="The output explains the defect and a checked repair",
        outputs=[name],
        **kwargs,
    )


def result(service, task, *, status="completed", outputs=None, unresolved=None):
    record = service._read("helper_tasks", task)
    work = service.root / record["workspace"]
    names = record["outputs"] if outputs is None else outputs
    for name in names:
        (work / name).write_text("A concrete checked result from the helper.\n")
    put(
        work / "HELPER_RESULT.json",
        dict(
            status=status,
            summary="Completed the requested bounded investigation.",
            artifacts=names,
            checks=["Compared against the supplied reference"],
            unresolved=unresolved or [],
        ),
    )
    return finish_helper(service, task, 0)


def wait_until(predicate, timeout=15):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    pytest.fail("Helper lifecycle did not reach the expected state")


def fake_backend(tmp_path, body):
    executable = tmp_path / "helper-backend"
    executable.write_text(
        "#!/usr/bin/env python3\nimport json,time,os\nfrom pathlib import Path\n"
        "print(json.dumps({'type':'thread.started','thread_id':Path.cwd().parent.name}),flush=True)\n"
        + body
        + "\nprint(json.dumps({'type':'turn.completed',"
        "'usage':{'input_tokens':31,'output_tokens':7}}),flush=True)\n"
    )
    executable.chmod(0o700)
    return dict(backend="codex", model="fixture", executable=str(executable))


def director_response(directory, value):
    body = dict(
        decision="continue",
        rationale="Delegate this bounded assistance request now.",
        scientific_feasibility="adequate",
        budget_feasibility="feasible",
        next_action="Inspect the returned helper artifacts and resume the investigation.",
        **value,
    )
    (directory / "response.json").write_text(
        json.dumps(
            dict(type="item.completed", item=dict(type="agent_message", text=json.dumps(body)))
        )
        + "\n"
        + json.dumps(dict(type="turn.completed", usage={}))
        + "\n"
    )
    return 0


def test_request_freezes_context_and_rejects_changed_replay(tmp_path):
    sup = supervisor(tmp_path)
    s = sup.service
    original = (s.root / "research.json").read_bytes()
    item = request(s, key="timestep-question")
    assert request(s, key="timestep-question")["id"] == item["id"]
    (s.work / "calc.py").write_text("print('parent continues independent work')")
    frozen = s.root / "help_context" / item["id"] / "inputs/calc.py"
    assert frozen.read_text() == "print(1)\n"
    with pytest.raises(ValueError, match="different context"):
        request(s, key="timestep-question")
    with pytest.raises(ValueError, match="traversal"):
        s.request_help(
            "Inspect this source file",
            success_criteria="Return a tested answer",
            files=["../outside.py"],
        )
    assert (s.root / "research.json").read_bytes() == original
    assert not s.status()["scientific_completed"]


def test_no_unroutable_help_request_without_director(tmp_path):
    s = ResearchService.create(tmp_path / "study", "Scientific question", wall_seconds=600)
    with pytest.raises(ValueError, match="enabled research director"):
        s.request_help("Need a specialist", success_criteria="Return a checked explanation")
    assert not s._all("help_requests")


def test_help_wakes_director_before_periodic_interval_and_assigns_two_jobs(tmp_path, monkeypatch):
    sup = supervisor(tmp_path)
    item = request(sup.service)
    tasks = [assignment(item["id"], name) for name in ["analysis.txt", "patch.py"]]
    calls = []

    def launch(directory, prompt, **kwargs):
        calls.append(prompt)
        return director_response(directory, {"helper_tasks": [t.model_dump() for t in tasks]})

    monkeypatch.setattr(sup, "launch", launch)
    sup.state["last_director_at"] = time.time()
    sup.run_director()  # No force flag: the queued request itself triggers attention.
    assert len(calls) == 1
    assert len(sup.service._all("helper_tasks")) == 2
    assert sup.service.help_status(item["id"])["status"] == "running"
    sup.run_director()
    assert len(calls) == 1


def test_director_can_answer_without_launching_and_cannot_ignore_help(tmp_path, monkeypatch):
    sup = supervisor(tmp_path)
    item = request(sup.service)
    monkeypatch.setattr(sup, "launch", lambda d, p, **kw: director_response(d, {}))
    sup.run_director()
    assert sup.service.pending_help()
    assert "Address each queued" in sup.state["last_director_error"]
    sup.state["director_retry_after"] = 0
    reply = HelpReply(
        request=item["id"], advice="Reuse the existing measured control and check its units."
    )
    monkeypatch.setattr(
        sup,
        "launch",
        lambda d, p, **kw: director_response(d, {"help_replies": [reply.model_dump()]}),
    )
    sup.run_director()
    assert not sup.service._all("helper_tasks")
    assert sup.service.help_status(item["id"])["status"] == "resolved"
    assert "Reuse" in sup.prompt()


def test_two_helpers_keep_separate_workspaces_and_wake_after_both_return(tmp_path):
    sup = supervisor(tmp_path)
    s = sup.service
    item = request(s)
    tasks = [assignment(item["id"], name) for name in ["first.txt", "second.txt"]]
    ids = s.assign_helpers(
        tasks,
        [],
        director="director_test",
        worker_activity={"recent_messages": ["Need the phase check"]},
    )
    assert s.assign_helpers(tasks, [], director="director_replay") == ids
    assert len(s._all("helper_tasks")) == 2
    assert len({s._read("helper_tasks", i)["workspace"] for i in ids}) == 2
    assert (
        s.wait("Wait for both requested analyses", help_requests=[item["id"]])["status"]
        == "waiting"
    )
    result(s, ids[0])
    assert s.waiting_status()["status"] == "waiting"
    result(s, ids[1])
    assert s.waiting_status()["status"] == "woken"
    assert (s.work / "calc.py").read_text() == "print(1)\n"
    s.import_helper_artifact(ids[0], "first.txt", "candidate.txt")
    with pytest.raises(FileExistsError):
        s.import_helper_artifact(ids[1], "second.txt", "candidate.txt")
    assert not s.status()["scientific_completed"]


@pytest.mark.parametrize(
    "failure", ["no_handoff", "missing_output", "changed_input", "changed_context", "symlink"]
)
def test_exit_zero_is_not_success_without_valid_handoff(tmp_path, failure):
    s = supervisor(tmp_path).service
    item = request(s)
    task = s.assign_helpers([assignment(item["id"])], [], director="director_test")[0]
    work = s.root / s._read("helper_tasks", task)["workspace"]
    if failure != "no_handoff":
        put(
            work / "HELPER_RESULT.json",
            dict(
                status="completed",
                summary="This is a claimed result, not proof.",
                artifacts=["answer.txt"],
                checks=[],
                unresolved=[],
            ),
        )
        if failure != "missing_output":
            (work / "answer.txt").write_text("answer")
        if failure == "changed_input":
            (work / "inputs/calc.py").chmod(0o600)
            (work / "inputs/calc.py").write_text("changed")
        if failure == "changed_context":
            (work / "CONTEXT.json").write_text("{}")
        if failure == "symlink":
            (work / "answer.txt").unlink()
            (work / "answer.txt").symlink_to(s.work / "calc.py")
    record = finish_helper(s, task, 0)
    assert record["status"] == "failed"
    assert s.help_status(item["id"])["status"] == "resolved"
    assert not s.status()["scientific_completed"]


def test_blocked_handoff_returns_partial_work_and_preserves_hashes(tmp_path):
    s = supervisor(tmp_path).service
    item = request(s)
    task = s.assign_helpers([assignment(item["id"])], [], director="director_test")[0]
    record = result(s, task, status="blocked", unresolved=["The required reference is unavailable"])
    assert record["status"] == "blocked"
    frozen = s.root / "helper_results" / task / "answer.txt"
    frozen.chmod(0o600)
    frozen.write_text("tampered")
    with pytest.raises(ValueError, match="changed after handoff"):
        s.import_helper_artifact(task, "answer.txt", "candidate.txt")


def test_tampered_context_rejects_assignment_before_launch(tmp_path):
    s = supervisor(tmp_path).service
    item = request(s)
    (s.root / item["context_file"]).write_text("{}")
    with pytest.raises(ValueError, match="Frozen help context changed"):
        s.assign_helpers([assignment(item["id"])], [], director="director_test")
    assert not s._all("helper_tasks")


def test_real_processes_run_concurrently_resume_without_duplication_and_account_usage(tmp_path):
    sup = supervisor(tmp_path)
    s = sup.service
    item = request(s)
    tasks = [
        assignment(item["id"], name, timeout_seconds=30)
        for name in ["one.txt", "two.txt", "three.txt"]
    ]
    ids = s.assign_helpers(tasks, [], director="director_test")
    release = tmp_path / "release"
    options = fake_backend(
        tmp_path,
        "Path('started').write_text('ready')\n"
        f"while not Path({str(release)!r}).exists(): time.sleep(.02)\n"
        "task=json.loads((Path.cwd().parents[2]/'helper_tasks'/(Path.cwd().parent.name+'.json')).read_text())\n"
        "name=task['outputs'][0]\nPath(name).write_text('tested result')\n"
        "Path('HELPER_RESULT.json').write_text(json.dumps({'status':'completed',"
        "'summary':'Implemented and checked the assigned correction.',"
        "'artifacts':[name],'checks':['Local fixture completed'],'unresolved':[]}))\n",
    )
    try:
        assert len(s.dispatch_helpers(options, maximum=2)) == 2
        wait_until(lambda: len(list((s.root / "helpers").glob("*/research/started"))) == 2)
        recovered = ResearchService(s.root)
        assert recovered.dispatch_helpers(options, maximum=2) == []
        assert sum(r["status"] == "running" for r in recovered._all("helper_tasks")) == 2
        assert recovered._read("helper_tasks", ids[2])["status"] == "queued"
        release.touch()
        wait_until(
            lambda: all(
                recovered._read("helper_tasks", i)["status"] == "completed" for i in ids[:2]
            )
        )
        assert recovered.dispatch_helpers(options, maximum=2) == [ids[2]]
        wait_until(lambda: recovered.help_status(item["id"])["status"] == "resolved")
        sup.process_helpers()
        assert len(sup.state["helper_usage_collected"]) == 3
        assert sum(v["input_tokens"] for v in sup.state["usage_by_thread"].values()) == 93
        assert set(sup.state["usage_roles_by_thread"].values()) == {"helper"}
        sup._next_helper_poll = 0
        sup.process_helpers()
        assert sum(v["input_tokens"] for v in sup.state["usage_by_thread"].values()) == 93
    finally:
        release.touch()
        s.cancel_helpers("Test cleanup")


def test_cancellation_stops_owned_helper_and_preserves_pending_context(tmp_path):
    s = supervisor(tmp_path).service
    item = request(s)
    task = s.assign_helpers(
        [assignment(item["id"], timeout_seconds=30)], [], director="director_test"
    )[0]
    options = fake_backend(tmp_path, "Path('started').write_text('ready')\ntime.sleep(60)\n")
    try:
        s.dispatch_helpers(options)
        wait_until(lambda: (s.root / "helpers" / task / "research/started").exists())
        s.cancel_helpers("Operator stopped the study")
        wait_until(lambda: s.help_status(item["id"])["status"] == "resolved")
        assert s._read("helper_tasks", task)["status"] == "cancelled"
    finally:
        s.cancel_helpers("Test cleanup")


def test_lost_helper_controller_reaps_its_owned_native_agent(tmp_path):
    from conjecture_solver.mvp_launch import ProcessIdentity, process_identity_matches

    s = supervisor(tmp_path).service
    item = request(s)
    task = s.assign_helpers(
        [assignment(item["id"], timeout_seconds=30)], [], director="director_test"
    )[0]
    options = fake_backend(tmp_path, "Path('started').write_text('ready')\ntime.sleep(60)\n")
    try:
        s.dispatch_helpers(options)
        wait_until(lambda: (s.root / "helpers" / task / "research/started").exists())
        record = s._read("helper_tasks", task)
        child = ProcessIdentity.model_validate_json(
            (s.root / "helpers" / task / "turn-00001/child_identity.json").read_text()
        )
        os.kill(record["process_identity"]["pid"], signal.SIGKILL)
        wait_until(lambda: s.help_status(item["id"])["status"] == "resolved")
        assert s._read("helper_tasks", task)["status"] == "failed"
        wait_until(lambda: not process_identity_matches(child))
    finally:
        s.cancel_helpers("Test cleanup")
