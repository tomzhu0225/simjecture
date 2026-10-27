import hashlib
import json
from types import SimpleNamespace

import pytest
from simjecture_monitor.workflow_prompt import full_prompt, prompt
from test_scientific_workflow_collection import module


def supervisor(tmp_path):
    work = tmp_path / "research"
    work.mkdir()
    task = (
        "Use the recorded solver outputs. Preserve field tolerance 0.05. "
        "Protected edits need a judge."
    )
    service = SimpleNamespace(
        work=work,
        manifest={"operator_protocol": task},
        director_status=lambda: [{"id": "director_one", "decision": "replan"}],
        pending_director_replan=lambda: {"id": "director_one", "response_required": True},
    )
    return SimpleNamespace(
        root=tmp_path,
        service=service,
        state={
            "deadline": 200,
            "monitor_authority_results": [
                {"stage": "denied", "verdict": {"allowed": False}, "private_case_label": "hidden"}
            ],
            "recovery_instruction": (
                "The preceding provider request failed; continue from recorded artifacts."
            ),
        },
        helper_feedback=lambda: [
            {"id": "help_one", "status": "resolved", "summary": "Check units"}
        ],
        housekeeping=lambda name, fn: fn(),
    )


def test_default_keeps_both_inherited_initial_and_resume_instructions(monkeypatch):
    class Parent:
        def _full_prompt(self):
            return "original initial instructions"

        def prompt(self):
            return "original resumed instructions"

    mod = module(monkeypatch)
    sup = mod.supervisor_type(SimpleNamespace(RawSupervisor=Parent))()
    assert sup._full_prompt() == "original initial instructions"
    assert sup.prompt() == "original resumed instructions"


def test_task_control_preserves_contract_and_all_required_return_channels(tmp_path, monkeypatch):
    from conjecture_solver import research_continuation, research_journal

    sup = supervisor(tmp_path)
    housekeeping = []
    monkeypatch.setattr(
        research_continuation, "deliver", lambda service: [{"text": "Operator note"}]
    )
    monkeypatch.setattr(
        research_journal, "sync_journal", lambda service: housekeeping.append(service)
    )
    text = prompt(sup)
    assert sup.service.manifest["operator_protocol"] in text
    for required in [
        "director_one",
        "help_one",
        "Operator note",
        '"allowed": false',
        sup.state["recovery_instruction"],
        "lab.director_ack",
        "feedback_requirement",
    ]:
        assert required in text
    assert "private_case_label" not in text and "hidden" not in text
    assert "call lab.review with its experiment ID" not in text
    assert housekeeping == [sup.service]
    guide = (sup.service.work / "RESEARCH_GUIDE.md").read_text()
    assert guide in text
    receipt = json.loads((tmp_path / "WORKER_PROMPT_MODE.json").read_text())
    assert receipt["mode"] == "task_protocol"
    assert (
        receipt["task_sha256"]
        == hashlib.sha256(sup.service.manifest["operator_protocol"].encode()).hexdigest()
    )


def test_task_control_cannot_discard_inherited_phase_requirements(tmp_path):
    sup = supervisor(tmp_path)
    sup.service.manifest["continuation"] = {"parent": "previous-scientific-study"}
    with pytest.raises(ValueError, match="inherited research-phase"):
        full_prompt(sup)
    assert not (sup.service.work / "RESEARCH_GUIDE.md").exists()


def test_selected_control_is_used_by_the_scientific_supervisor(tmp_path, monkeypatch):
    class Parent:
        def _full_prompt(self):
            raise AssertionError("Inherited instructions must not enter the selected control")

    mod = module(monkeypatch)
    wrapped = mod.supervisor_type(
        SimpleNamespace(RawSupervisor=Parent), worker_prompt="task_protocol"
    )()
    wrapped.__dict__.update(vars(supervisor(tmp_path)))
    assert wrapped.service.manifest["operator_protocol"] in wrapped._full_prompt()
    assert (tmp_path / "WORKER_PROMPT_MODE.json").is_file()
