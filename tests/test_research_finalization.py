"""Deadline/report lifecycle tests with synthetic agents, not research evidence."""

import argparse
import json
import time

import pytest

from conjecture_solver.research_finalization import (
    ReportAssessment,
    default_report_reserve,
    report_status,
)
from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.research_supervisor import ResearchSupervisor


def fixture(tmp_path):
    s = ResearchService.create(
        tmp_path / "study",
        "Original unchanged question",
        wall_seconds=600,
        report_reserve_seconds=200,
    )
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Inspect the results and report what they establish.")
    sup = ResearchSupervisor(
        argparse.Namespace(
            campaign=s.root,
            state_dir=s.root / "supervisor",
            wall_seconds=600,
            instructions_file=instructions,
            backend="codex",
            model="fixture",
            judge_model="fixture",
            turn_seconds=300,
        )
    )
    (s.work / "calc.py").write_text("print('synthetic')\n")
    return sup


def answer(directory, decision="accepted"):
    verdict = dict(
        decision=decision,
        summary="Useful bounded analysis; claim remains open.",
        issues=[] if decision == "accepted" else ["Explain the omitted control."],
    )
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


def test_default_reserve_is_bounded_and_legacy_resume_unchanged(tmp_path):
    assert default_report_reserve(1800) == 450
    assert default_report_reserve(30) == 15
    assert default_report_reserve(43200) == 600
    s = ResearchService.create(tmp_path / "legacy", "old")
    before = (s.root / "research.json").read_bytes()
    ResearchService.create(s.root, "old")
    assert not report_status(s.root, s.manifest)
    assert (s.root / "research.json").read_bytes() == before
    with pytest.raises(ValueError, match="immutable"):
        ResearchService.create(s.root, "old", report_reserve_seconds=100)


def test_admissions_protect_reserve_and_allow_bounded_analysis(tmp_path, monkeypatch):
    sup = fixture(tmp_path)
    s = sup.service
    monkeypatch.setattr(s, "_spawn_experiment", lambda record: None)
    r = s.run("calc.py", outputs=["out.json"], timeout=590, stage="exploration")
    cutoff = s.manifest["finalization_policy"]["compute_deadline"]
    assert r["execution_deadline"] == cutoff
    assert r["timeout"] <= 400
    monkeypatch.setattr("time.time", lambda: cutoff + 1)
    # Retry of an already admitted identity still returns its receipt.
    assert s.run("calc.py", outputs=["out.json"], timeout=590, stage="exploration")["id"] == r["id"]
    with pytest.raises(ValueError, match="Protected report"):
        s.run("calc.py", outputs=["out.json"], stage="exploration", key="late")
    post = s.analyze("calc.py", outputs=["out.json"], timeout=500)
    assert post["stage"] == "exploration"
    assert post["execution_deadline"] == cutoff + 80
    assert post["timeout"] <= 79
    monkeypatch.setattr("time.time", lambda: cutoff + 81)
    with pytest.raises(ValueError, match="Protected report"):
        s.analyze("calc.py", outputs=["out.json"], key="too-late")


def test_reviewed_unresolved_report_never_approves_claim(tmp_path, monkeypatch):
    sup = fixture(tmp_path)
    before = (sup.root / "research.json").read_bytes()
    sup.state["waiting_for"] = ["old-job"]
    calls = []

    def launch(directory, prompt, judge=False):
        calls.append((judge, sup.launch_deadline))
        if judge:
            assert "not a claim-approval" in prompt
            answer(directory)
        else:
            assert "PROTECTED FINALIZATION" in prompt
            (sup.service.work / "RESULTS.md").write_text("Results with bounded uncertainty.")
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.finalize_report()
    status = sup.service.status()
    assert status["finalization"]["report_status"] == "reviewed"
    assert not status["completed"] and not status["reviews"]
    assert "waiting_for" not in sup.state
    assert [j for j, _ in calls] == [False, True]
    assert all(d < sup.state["deadline"] for _, d in calls)
    assert (sup.root / "research.json").read_bytes() == before
    sup.finalize_report()
    assert len(calls) == 2  # No repeated provider calls once a report is assessed.
    from conjecture_solver.study_status import study_status
    from conjecture_solver.web.application import _engine_projection

    assert study_status(sup.root)["finalization"]["report_status"] == "reviewed"
    assert _engine_projection(sup.root)["finalization"]["report_status"] == "reviewed"
    (sup.service.work / "RESULTS.md").write_text("Changed after the review")
    assert sup.service.status()["finalization"]["report_status"] == "changed_since_review"


def test_report_revision_and_invalid_reviewer_are_bounded(tmp_path, monkeypatch):
    sup = fixture(tmp_path)
    calls = []

    def launch(directory, prompt, judge=False):
        calls.append(judge)
        if judge:
            answer(directory, "needs_revision" if len(calls) == 2 else "accepted")
        else:
            (sup.service.work / "RESULTS.md").write_text(f"Report draft {len(calls)}")
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.finalize_report()
    assert calls == [False, True, False, True]
    assert sup.service.status()["finalization"]["report_status"] == "reviewed"
    assert not sup.service.status()["completed"]


def test_review_failure_stays_unreviewed(tmp_path, monkeypatch):
    sup = fixture(tmp_path)

    def launch(directory, prompt, judge=False):
        (sup.service.work / "RESULTS.md").write_text("Partial scientific report")
        return 124 if judge else 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.finalize_report()
    assert sup.service.status()["finalization"]["report_status"] == "unreviewed"
    assert not sup.service.status()["completed"]


def test_finalization_wakes_parked_worker_at_cutoff(tmp_path, monkeypatch):
    sup = fixture(tmp_path)
    sup.service.manifest["finalization_policy"]["compute_deadline"] = time.time() - 1
    put(sup.root / "research.json", sup.service.manifest)
    sup.state["waiting_for"] = ["old-job"]
    calls = []

    def finish():
        calls.append("finish")
        sup.cancelled = True

    monkeypatch.setattr(sup, "finalize_report", finish)
    monkeypatch.setattr(sup, "process_methods", lambda: pytest.fail("Must finalize before methods"))
    assert sup.run() == 0
    assert calls == ["finish"]
    assert sup.worker_checkpoint_requested()


@pytest.mark.parametrize(
    "decision,issues", [("accepted", ["missing result"]), ("needs_revision", [])]
)
def test_report_verdict_cannot_hide_blockers(decision, issues):
    with pytest.raises(ValueError):
        ReportAssessment(decision=decision, summary="Summary", issues=issues)


def test_native_activity_cannot_extend_absolute_call_boundary(tmp_path):
    import sys

    from conjecture_solver.agent_supervisor import AgentSupervisor

    root = tmp_path / "native"
    root.mkdir()
    fake = tmp_path / "active-agent"
    fake.write_text(
        f"#!{sys.executable}\nimport time\n"
        "while True:\n print('{}', flush=True)\n time.sleep(.01)\n"
    )
    fake.chmod(0o700)
    sup = AgentSupervisor(
        argparse.Namespace(
            campaign=root,
            state_dir=root / "supervisor",
            wall_seconds=30,
            turn_seconds=20,
            executable=str(fake),
            model="fixture",
            judge_model="fixture",
            workflow="frontier",
        )
    )
    turn = sup.directory / "turn"
    turn.mkdir()
    sup.launch_deadline = time.time() + 0.2
    started = time.monotonic()
    assert sup.launch(turn, "Synthetic active agent") == 124
    assert time.monotonic() - started < 8
    assert sup.boundary() is None
    assert "child_pid" not in sup.state


def test_cutoff_preserves_diagnostic_admitted_into_drafting_time(tmp_path, monkeypatch):
    sup = fixture(tmp_path)
    s = sup.service
    monkeypatch.setattr(s, "_spawn_experiment", lambda record: None)
    analysis = s.analyze("calc.py", outputs=["out.json"])
    simulation = s.run("calc.py", outputs=["sim.json"], stage="exploration")
    s.cancel_active(preserve_diagnostics=True)
    assert s._read("experiments", analysis["id"])["status"] == "queued"
    assert s._read("experiments", simulation["id"])["status"] == "cancelled"
    s.cancel_active()
    assert s._read("experiments", analysis["id"])["status"] == "cancelled"


def test_draft_resumes_after_async_analysis_before_freezing_report(tmp_path, monkeypatch):
    sup = fixture(tmp_path)
    monkeypatch.setattr(sup.service, "_spawn_experiment", lambda record: None)
    calls = []
    job = []

    def launch(directory, prompt, judge=False):
        calls.append(judge)
        if judge:
            assert (sup.service.work / "RESULTS.md").read_text() == "Analysis incorporated."
            answer(directory)
        elif not job:
            job.append(sup.service.analyze("calc.py", outputs=["out.json"]))
            (sup.service.work / "RESULTS.md").write_text("Analysis pending.")
        else:
            assert "incorporate" in prompt
            (sup.service.work / "RESULTS.md").write_text("Analysis incorporated.")
        return 0

    def finish_job(seconds):
        put(
            sup.root / "experiments" / (job[0]["id"] + ".json"),
            job[0] | {"status": "succeeded", "finished_at": time.time()},
        )

    monkeypatch.setattr(sup, "launch", launch)
    monkeypatch.setattr("conjecture_solver.research_finalization.time.sleep", finish_job)
    sup.finalize_report()
    assert calls == [False, False, True]
    assert sup.service.status()["finalization"]["report_status"] == "reviewed"
    assert not sup.service.status()["completed"]


def test_report_timeout_uses_remaining_budget_for_one_retry(tmp_path, monkeypatch):
    sup = fixture(tmp_path)
    calls = []

    def launch(directory, prompt, judge=False):
        calls.append(judge)
        if not judge:
            (sup.service.work / "RESULTS.md").write_text("A useful unresolved report.")
        elif len(calls) == 2:
            return 124
        else:
            answer(directory)
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.finalize_report()
    assert calls == [False, True, True]
    assert sup.service.status()["finalization"]["report_status"] == "reviewed"
    assert not sup.service.status()["completed"]
