"""Finish an investigation without silently converting uncertainty into support."""

import argparse
import json

import pytest

from conjecture_solver.research_director import DirectorVerdict
from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.research_supervisor import ResearchSupervisor
from conjecture_solver.study_status import study_status


def prepared(tmp_path):
    service = ResearchService.create(
        tmp_path / "study", "The physical bound holds", wall_seconds=600
    )
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Conclude honestly when no useful affordable test remains.")
    supervisor = ResearchSupervisor(
        argparse.Namespace(
            campaign=service.root,
            state_dir=service.root / "supervisor",
            instructions_file=instructions,
            backend="codex",
            model="unused-worker",
            judge_model="independent-director",
            wall_seconds=600,
            director_enabled=True,
        )
    )
    service = supervisor.service
    (service.work / "RESULTS.md").write_text(
        "The bound remains unresolved. Missing topology conversion requires a new commissioned run."
    )
    report = service.assess_report()
    report.update(
        status="resolved",
        assessment=dict(
            decision="accepted",
            summary="Honest unresolved findings and useful next test.",
            issues=[],
        ),
    )
    put(service.root / "report_requests" / (report["id"] + ".json"), report)
    return supervisor, report


def finish_response(supervisor, report, monkeypatch):
    launches = []

    def launch(directory, prompt, *, judge=False, director=False):
        assert judge and director, "Closing must use the director review route"
        launches.append(directory.name)
        value = dict(
            decision="finish",
            closeout_report=report["id"],
            rationale=(
                "Useful tests exceed this budget; the report records the missing diagnostic."
            ),
            scientific_feasibility="limited",
            budget_feasibility="infeasible",
            next_action="Preserve the unresolved report and finish this investigation.",
        )
        (directory / "response.json").write_text(
            json.dumps(
                dict(type="item.completed", item=dict(type="agent_message", text=json.dumps(value)))
            )
            + "\n"
            + json.dumps(dict(type="turn.completed", usage={}))
            + "\n"
        )
        return 0

    monkeypatch.setattr(supervisor, "launch", launch)
    return launches


def test_director_finishes_unresolved_campaign_without_worker_or_claim_promotion(
    tmp_path, monkeypatch
):
    supervisor, report = prepared(tmp_path)
    service = supervisor.service
    deadline = service.manifest["deadline"]
    service.wait("No useful further work remains pending operator direction", for_operator=True)
    launches = finish_response(supervisor, report, monkeypatch)
    supervisor.state["last_director_at"] = 0
    assert not service.status()["completed"]  # Acceptance alone still cannot close a study.
    assert supervisor.run() == 0
    status = service.status()
    assert status["completed"] and not status["scientific_completed"]
    assert status["original_disposition"] == "unresolved" and not status["reviews"]
    assert status["audit"]["scientific_status"] == "unresolved"
    assert status["campaign_closeout"]["report_id"] == report["id"]
    assert len(launches) == 1 and service.manifest["deadline"] == deadline
    assert supervisor.state["status"] == "completed"
    assert "hypothesis unresolved" in study_status(service.root)["activity"]
    published = json.loads((service.root / "research_report.json").read_text())
    assert published["completed"] and published["original_disposition"] == "unresolved"
    assert not (service.root / "finalization.json").exists()  # Reuse the accepted report.
    with pytest.raises(ValueError, match="Investigation finished"):
        service.run("new.py", outputs=["result.json"])


@pytest.mark.parametrize(
    "obstacle", ["job", "changed_report", "new_record", "new_guidance", "worker"]
)
def test_director_cannot_close_over_unfinished_or_unassessed_work(tmp_path, monkeypatch, obstacle):
    supervisor, report = prepared(tmp_path)
    service = supervisor.service
    if obstacle in {"job", "new_record"}:
        (service.work / "later.py").write_text("print('new analysis')\n")
        monkeypatch.setattr(service, "_spawn_experiment", lambda record: None)
        experiment = service.run("later.py", outputs=["result.json"], stage="exploration")
        if obstacle == "new_record":
            experiment["status"] = "failed"
            put(service.root / "experiments" / (experiment["id"] + ".json"), experiment)
    elif obstacle == "changed_report":
        (service.work / "RESULTS.md").write_text("New unassessed interpretation")
    elif obstacle == "new_guidance":
        from conjecture_solver.research_continuation import submit

        submit(
            service.root, "New affordable discriminating test: inspect the preserved flux ledger."
        )
    else:
        supervisor._worker_turn_active = True
    finish_response(supervisor, report, monkeypatch)
    supervisor.run_director(force=True)
    assert not service.campaign_closeout()
    assert not service.status()["completed"] and not service.status()["reviews"]
    assert supervisor.state["last_director_error"]


def test_finish_decision_cannot_cancel_jobs_or_request_more_work():
    base = dict(
        decision="finish",
        rationale="No useful affordable work remains after the accepted report.",
        scientific_feasibility="limited",
        budget_feasibility="infeasible",
        next_action="Finish without claiming the hypothesis is established.",
    )
    with pytest.raises(ValueError, match="accepted report ID"):
        DirectorVerdict(**base)
    with pytest.raises(ValueError, match="no other control action"):
        DirectorVerdict(**base, closeout_report="report_example", wake_worker=True)


def test_new_guidance_and_extensions_cannot_cross_the_completion_barrier(tmp_path, monkeypatch):
    from conjecture_solver.research_budget import budget_status, extend_budget
    from conjecture_solver.research_continuation import submit

    supervisor, report = prepared(tmp_path)
    finish_response(supervisor, report, monkeypatch)
    supervisor.run_director(force=True)
    assert supervisor.service.campaign_closeout()
    # The report publication barrier has not yet published terminal supervisor state.
    assert supervisor.state["status"] != "completed"
    assert not budget_status(supervisor.root)["can_extend"]
    with pytest.raises(ValueError, match="ended"):
        submit(supervisor.root, "New direction arriving after the closeout was committed")
    with pytest.raises(ValueError, match="ended|finished|completed"):
        extend_budget(supervisor.root, hours=1, key="late-extension")
