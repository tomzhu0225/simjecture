"""Synthetic supervisor lifecycle coverage; no provider or numerical execution."""

import argparse

from conjecture_solver.research_service import ResearchService
from conjecture_solver.research_supervisor import ResearchSupervisor


def test_waiting_for_running_job_does_not_spend_provider_turns(tmp_path, monkeypatch):
    service = ResearchService.create(
        tmp_path / "study", "A bounded waiting fixture", wall_seconds=60
    )
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Wait for durable numerical receipts.")
    supervisor = ResearchSupervisor(
        argparse.Namespace(
            campaign=service.root,
            state_dir=service.root / "supervisor",
            wall_seconds=60,
            instructions_file=instructions,
            backend="codex",
            model="unused-fixture",
            judge_model="unused-fixture",
        )
    )
    supervisor.state["waiting_for"] = ["fixture-job"]
    snapshot = service.status()
    snapshot["experiments"] = [{"id": "fixture-job", "status": "running"}]
    monkeypatch.setattr(supervisor.service, "status", lambda **kwargs: snapshot)
    for method in (
        "process_methods",
        "process_reviews",
        "maintain_journal",
        "run_oversight",
        "recovery_wait",
    ):
        monkeypatch.setattr(supervisor, method, lambda: None)
    monkeypatch.setattr(
        "conjecture_solver.research_supervisor.durable_signature", lambda service: "fixture"
    )
    monkeypatch.setattr("conjecture_solver.research_supervisor.write_report", lambda *args: None)
    monkeypatch.setattr(supervisor.service, "cancel_active", lambda: None)
    launches, waits = [], []

    def sleep(seconds):
        assert not launches
        waits.append(seconds)
        if len(waits) == 5:
            snapshot["experiments"][0]["status"] = "succeeded"

    def launch(*args, **kwargs):
        launches.append(len(waits))
        supervisor.cancelled = True
        return 0

    monkeypatch.setattr("conjecture_solver.research_supervisor.time.sleep", sleep)
    monkeypatch.setattr(supervisor, "launch", launch)
    monkeypatch.setattr(supervisor, "prompt", lambda: "fixture")
    assert supervisor.run() == 0
    assert launches == [5]
    assert waits == [1] * 5
    assert supervisor.state["status"] == "cancelled"
    assert "waiting_for" not in supervisor.state
