"""Returned assistance takes precedence over unrelated simulation parking."""

import os

import pytest

from conjecture_solver.research_helpers import finish_helper
from tests.test_research_director import supervisor
from tests.test_research_helpers import assignment, request, result


def idle_loop(sup, monkeypatch):
    snapshot = sup.service.status()
    snapshot["experiments"] = [{"id": "long_experiment", "status": "running"}]
    monkeypatch.setattr(sup.service, "status", lambda **kw: snapshot)
    monkeypatch.setattr(sup.service, "dispatch_helpers", lambda *a, **kw: [])
    monkeypatch.setattr(sup.service, "cancel_active", lambda: None)
    for name in (
        "process_methods",
        "process_reviews",
        "process_report_requests",
        "maintain_journal",
        "run_oversight",
        "recovery_wait",
        "observe_turn",
        "report",
        "run_director",
    ):
        monkeypatch.setattr(sup, name, lambda *a, **kw: None)
    monkeypatch.setattr(sup, "prompt", lambda: str(sup.helper_feedback()))
    monkeypatch.setattr(
        "conjecture_solver.research_supervisor.durable_signature", lambda s: "fixture"
    )


@pytest.mark.parametrize("outcome", ["completed", "blocked", "failed", "cancelled"])
def test_help_resolved_during_turn_is_delivered_to_next_turn(tmp_path, monkeypatch, outcome):
    sup = supervisor(tmp_path)
    s = sup.service
    idle_loop(sup, monkeypatch)
    launches = []

    def launch(directory, prompt):
        launches.append(prompt)
        if len(launches) == 2:
            assert "resolved" in prompt
            assert sup.state["helper_feedback_pending"]
            sup.cancelled = True
            return 0
        item = request(s)
        task = s.assign_helpers([assignment(item["id"])], [], director="fixture")[0]
        s.wait("Await assistance before choosing the next action", help_requests=[item["id"]])
        if outcome == "completed":
            result(s, task)
        elif outcome == "blocked":
            result(s, task, status="blocked", unresolved=["Reference unavailable"])
        elif outcome == "failed":
            finish_helper(s, task, 1)
        else:
            s.cancel_helpers("Fixture cancellation")
        sup._next_helper_poll = 0
        sup.process_helpers()
        assert s.waiting_status()["status"] == "woken"
        return 0

    def unexpected_wait(seconds):
        pytest.fail("Returned help was lost behind an unrelated experiment")

    monkeypatch.setattr(sup, "launch", launch)
    monkeypatch.setattr("conjecture_solver.research_supervisor.time.sleep", unexpected_wait)
    assert sup.run() == 0
    assert len(launches) == 2
    assert not sup.state["helper_feedback_pending"]


def test_individual_helper_can_wake_parent_before_other_helpers_finish(tmp_path, monkeypatch):
    sup = supervisor(tmp_path)
    s = sup.service
    idle_loop(sup, monkeypatch)
    launches, tasks, sleeps = [], [], []

    def launch(directory, prompt):
        launches.append(prompt)
        if len(launches) == 2:
            assert s._read("helper_tasks", tasks[0])["status"] == "completed"
            assert s._read("helper_tasks", tasks[1])["status"] == "queued"
            sup.cancelled = True
            return 0
        item = request(s)
        tasks.extend(
            s.assign_helpers(
                [assignment(item["id"], name) for name in ["a.txt", "b.txt"]],
                [],
                director="fixture",
            )
        )
        s.wait("Await the first helper before choosing the next action", helpers=[tasks[0]])
        return 0

    def sleep(seconds):
        sleeps.append(seconds)
        assert len(sleeps) == 1
        result(s, tasks[0])
        sup._next_helper_poll = 0

    monkeypatch.setattr(sup, "launch", launch)
    monkeypatch.setattr("conjecture_solver.research_supervisor.time.sleep", sleep)
    assert sup.run() == 0
    assert len(launches) == 2


@pytest.mark.parametrize("same_artifact", [True, False])
def test_distinct_imports_keep_distinct_provenance_receipts(tmp_path, same_artifact):
    s = supervisor(tmp_path).service
    item = request(s)
    spec = assignment(item["id"])
    spec.outputs = ["first.txt", "second.txt"]
    task = s.assign_helpers([spec], [], director="fixture")[0]
    result(s, task)
    s.import_helper_artifact(task, "first.txt", "a.txt")
    s.import_helper_artifact(task, "first.txt" if same_artifact else "second.txt", "b.txt")
    receipts = s._all("helper_imports")
    assert len(receipts) == 2
    assert {r["destination"] for r in receipts} == {"a.txt", "b.txt"}
    assert len({r["sha256"] for r in receipts}) == 1


@pytest.mark.parametrize(
    "name", ["HELPER_RESULT.json", "CONTEXT.json", "inputs/calc.py", "answer.txt"]
)
def test_nonregular_handoff_or_input_fails_without_holding_service_lock(tmp_path, name):
    import subprocess
    import sys

    from conjecture_solver.research_service import put

    s = supervisor(tmp_path).service
    item = request(s)
    task = s.assign_helpers([assignment(item["id"])], [], director="fixture")[0]
    work = s.root / s._read("helper_tasks", task)["workspace"]
    put(
        work / "HELPER_RESULT.json",
        dict(status="completed", summary="Ready for validated transfer", artifacts=["answer.txt"]),
    )
    (work / "answer.txt").write_text("answer")
    (work / name).unlink()
    os.mkfifo(work / name)
    code = (
        "from conjecture_solver.research_service import ResearchService; "
        "from conjecture_solver.research_helpers import finish_helper; "
        f"s=ResearchService({str(s.root)!r}); "
        f"assert finish_helper(s,{task!r},0)['status'] == 'failed'; "
        "s.cancel_helpers('Final validation cleanup')"
    )
    subprocess.run([sys.executable, "-c", code], check=True, timeout=5)
