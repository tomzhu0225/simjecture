import argparse
import json

import pytest
from simjecture_monitor.repair import RepairAuthority
from simjecture_monitor.repair_roles import adjudicate

from conjecture_solver.agent_supervisor import AgentSupervisor
from conjecture_solver.research_service import ResearchService


def setup(tmp_path, *, allowed="bridge.py"):
    service = ResearchService.create(tmp_path / "study", "Check adapter", wall_seconds=600)
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Read-only scoped repair review.")
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
    )
    component = tmp_path / "component"
    component.mkdir()
    (component / allowed).write_text('def classify(alive, code): return "running"\n')
    authority = RepairAuthority(
        component, tmp_path / "grants", allowed_files=[allowed], test_source="pass"
    )
    verdict = dict(
        decision="grant",
        rationale="A stopped process is incorrectly classified as running.",
        evidence=["The stopped process receipt and registered component source."],
        files=[allowed],
        seconds=180,
    )
    return args, authority, verdict


@pytest.mark.parametrize("bad_names", [["harness/bridge.py"], ["/work/harness/bridge.py"], []])
@pytest.mark.parametrize("corrected", [True, False])
def test_scope_error_gets_one_bounded_correction_without_normalizing_paths(
    tmp_path, monkeypatch, bad_names, corrected
):
    args, authority, verdict = setup(tmp_path)
    judge_calls = []

    def launch(self, directory, prompt, **kwargs):
        if not directory.name.startswith("authority-judge"):
            return 1  # Keep this test at the grant boundary, without a native repair call.
        judge_calls.append(prompt)
        assert '"enum": ["bridge.py"]' in prompt
        value = dict(verdict)
        if len(judge_calls) == 1 or not corrected:
            value["files"] = bad_names
        (directory / "response.json").write_text(json.dumps(value))
        return 0

    monkeypatch.setattr(AgentSupervisor, "launch", launch)
    monkeypatch.setattr(
        "simjecture_monitor.repair_roles.parse_judge_stream",
        lambda path, *args, **kwargs: json.loads(path.read_text()),
    )
    result = adjudicate(args, authority, {"observed": "Stopped process"}, tmp_path / "call")
    assert len(judge_calls) == 2
    assert "Grant file names do not match operator policy" in judge_calls[1]
    if corrected:
        assert set(result["grant"]["originals"]) == {"bridge.py"}
        assert result["verdict_trace"].endswith("authority-judge-retry/response.json")
    else:
        assert result["stage"] == "failed" and not result.get("grant")
        assert authority.grants == {}
    assert (authority.component / "bridge.py").read_text().endswith('return "running"\n')


def test_schema_uses_the_configured_file_names(tmp_path, monkeypatch):
    args, authority, verdict = setup(tmp_path, allowed="status.py")
    prompts = []

    def launch(self, directory, prompt, **kwargs):
        prompts.append(prompt)
        (directory / "response.json").write_text(json.dumps(verdict | dict(decision="deny")))
        return 0

    monkeypatch.setattr(AgentSupervisor, "launch", launch)
    monkeypatch.setattr(
        "simjecture_monitor.repair_roles.parse_judge_stream",
        lambda path, *args, **kwargs: json.loads(path.read_text()),
    )
    result = adjudicate(args, authority, {}, tmp_path / "call")
    assert '"enum": ["status.py"]' in prompts[0]
    assert "bridge.py" not in prompts[0]
    assert result["grant"]["status"] == "deny" and authority.grants == {}
