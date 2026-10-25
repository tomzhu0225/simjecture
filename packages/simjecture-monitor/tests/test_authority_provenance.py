"""A transport retry must bind the grant to the judge response that authorized it."""

import argparse
import json

import pytest
from simjecture_monitor.events import digest
from simjecture_monitor.repair import RepairAuthority
from simjecture_monitor.repair_roles import adjudicate

from conjecture_solver.agent_supervisor import AgentSupervisor
from conjecture_solver.research_service import ResearchService


@pytest.mark.parametrize("contract", [None, "Requested source identity must be preserved."])
def test_grant_receipt_uses_successful_retry(tmp_path, monkeypatch, contract):
    service = ResearchService.create(tmp_path / "study", "Check adapter", wall_seconds=600)
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Read-only judge and repair proposer.")
    args = argparse.Namespace(
        campaign=service.root,
        state_dir=service.root / "supervisor",
        wall_seconds=600,
        turn_seconds=120,
        instructions_file=instructions,
        backend="codex",
        model="worker",
        judge_model="judge",
        director_enabled=True,
        repair_contract=contract,
    )
    component = tmp_path / "component"
    component.mkdir()
    (component / "bridge.py").write_text('def classify(alive, code): return "running"\n')
    authority = RepairAuthority(
        component, tmp_path / "grants", allowed_files=["bridge.py"], test_source="pass"
    )
    verdict = dict(
        decision="grant",
        rationale="Completed processes remain incorrectly running.",
        evidence=["completed receipt"],
        files=["bridge.py"],
        seconds=180,
    )

    def launch(self, directory, prompt, **kwargs):
        if contract:
            assert contract in prompt
        if directory.name == "authority-judge":
            return 1
        if directory.name == "authority-judge-retry":
            (directory / "response.json").write_text(json.dumps(verdict))
            return 0
        # Preserve the issued grant while independently failing the proposer.
        return 1

    monkeypatch.setattr(AgentSupervisor, "launch", launch)
    monkeypatch.setattr(
        "simjecture_monitor.repair_roles.parse_judge_stream",
        lambda path, *args, **kwargs: json.loads(path.read_text()),
    )
    directory = tmp_path / "authority-call"
    result = adjudicate(args, authority, {"observed": "completed process"}, directory)
    trace = directory / "authority-judge-retry/response.json"
    assert result["verdict_trace"] == str(trace)
    assert result["grant"]["judge_receipt_sha256"] == digest(
        dict(verdict=verdict, trace=str(trace))
    )
    assert result["stage"] == "failed"
    assert not result.get("deployment")
