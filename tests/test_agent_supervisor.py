from __future__ import annotations

import argparse
import json

import pytest

from conjecture_solver.agent_supervisor import AgentSupervisor, next_assignment, parse_judge_stream


def claim(name="claim_root", status="open", **extra):
    return dict(id=name, kind="scientific", status=status, relation="root", **extra)


def test_falsification_requires_repair_then_tests_repair():
    root = claim(status="falsified")
    assert next_assignment([root]) == ("claim_root", "repair_scientist")
    child = claim("claim_repair", parent_id="claim_root")
    child["relation"] = "repairs"
    assert next_assignment([root, child]) == ("claim_repair", "falsifier")


@pytest.mark.parametrize("status", ["unresolved", "instrument_limited", "supported"])
def test_no_worker_status_can_self_certify_completion(status):
    with pytest.raises(RuntimeError):
        next_assignment([claim(status=status)])


def test_judge_rejects_any_tool_event(tmp_path):
    p = tmp_path / "stream"
    p.write_text(
        json.dumps({"event": "step_update", "step_update": {"step_type": "tool", "state": "ERROR"}})
        + "\n"
        + json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "{}"}})
    )
    with pytest.raises(ValueError, match="used a tool"):
        parse_judge_stream(p)
    p.write_text(
        json.dumps(
            {
                "event": "result",
                "result": {"status": "SUCCESS", "response": '{"decision":"insufficient"}'},
            }
        )
    )
    assert parse_judge_stream(p)["decision"] == "insufficient"
    p.write_text("")
    with pytest.raises(ValueError):
        parse_judge_stream(p)


def test_inconclusive_and_clean_exit_continue_until_host_deadline(tmp_path, monkeypatch):
    root = tmp_path / "campaign"
    root.mkdir()
    args = argparse.Namespace(
        campaign=root,
        state_dir=tmp_path / "supervisor",
        wall_seconds=100,
        instructions_file=tmp_path / "instructions",
    )
    supervisor = AgentSupervisor(args)
    turns = []
    monkeypatch.setattr(supervisor, "inspect", lambda: ("open claims", [claim()], {"jobs": []}))
    monkeypatch.setattr(supervisor, "assign", lambda claims: {"spec": {"assignment_id": "worker"}})
    monkeypatch.setattr(supervisor, "worker_files", lambda directory, record: "continue")
    monkeypatch.setattr(supervisor, "review", lambda *a: None)

    def launch(directory, prompt):
        turns.append(directory)
        supervisor.state["next_test"] = "inconclusive; refine the grid"
        if len(turns) == 3:
            supervisor.state["deadline"] = 0
        return 0

    monkeypatch.setattr(supervisor, "launch", launch)
    assert supervisor.run() == 124
    assert len(turns) == 3
    assert supervisor.state["status"] == "budget_exhausted"
    assert not (root / "mvp_report.json").exists()
    deadline = supervisor.state["deadline"]
    assert AgentSupervisor(args).state["deadline"] == deadline


def test_completion_requires_kernel_gate_not_exit(tmp_path, monkeypatch):
    root = tmp_path / "campaign"
    root.mkdir()
    args = argparse.Namespace(campaign=root, state_dir=tmp_path / "supervisor", wall_seconds=100)
    s = AgentSupervisor(args)
    monkeypatch.setattr(s, "inspect", lambda: (None, [claim(status="supported")], {"jobs": []}))
    calls = []
    monkeypatch.setattr(s, "call", lambda name, args: calls.append(name) or {"status": "completed"})
    assert s.run() == 0
    assert calls == ["finalize_campaign"]
    assert s.state["status"] == "completed"


def test_real_handoff_starts_successor_without_completion(tmp_path):
    import sys

    from conjecture_solver.campaign_kernel import CampaignKernel

    root = tmp_path / "campaign"
    from conjecture_solver.mvp_agent import MVPAgentConfig

    CampaignKernel.open(
        workspace=root,
        hypothesis="A finite scientific claim remains untested.",
        config=MVPAgentConfig(require_independent_contract_review=True),
    )
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Continue testing.")
    fake = tmp_path / "fake-agy"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json, subprocess, sys\nfrom pathlib import Path\n"
        "cwd=Path.cwd(); state=json.loads((cwd.parent/'state.json').read_text())\n"
        "subprocess.run([sys.executable,str(cwd/'kernel_call.py'),'snapshot'],check=True)\n"
        "payload=dict(assignment_id=state['assignment_id'],claim_id='claim_root',"
        "outcome='inconclusive',evidence_paths=[],next_test='Refine the experiment')\n"
        "(cwd/'handoff.json').write_text(json.dumps(payload))\n"
        "subprocess.run([sys.executable,str(cwd/'kernel_call.py'),'handoff',"
        "str(cwd/'handoff.json')],check=True)\n"
        "if state['round']==2: (cwd.parent/'control.json').write_text('{\"command\":\"pause\"}')\n"
    )
    fake.chmod(0o700)
    args = argparse.Namespace(
        campaign=root,
        state_dir=tmp_path / "supervisor",
        instructions_file=instructions,
        wall_seconds=30,
        turn_seconds=10,
        executable=str(fake),
        model="fake",
        judge_model="fake",
    )
    s = AgentSupervisor(args)
    assert s.run() == 0
    assert s.state["status"] == "paused"
    assignments = json.loads((root / "role_assignments.json").read_text())["assignments"]
    assert len(assignments) == 2
    assert all(a["handoff"]["outcome"] == "inconclusive" for a in assignments.values())
    assert not (root / "mvp_report.json").exists()


def test_host_turn_timeout_is_a_checkpoint_not_provider_failure(tmp_path):
    import sys

    root = tmp_path / "campaign"
    root.mkdir()
    fake = tmp_path / "slow-agy"
    fake.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
    fake.chmod(0o700)
    args = argparse.Namespace(
        campaign=root,
        state_dir=tmp_path / "supervisor",
        wall_seconds=20,
        turn_seconds=0.1,
        executable=str(fake),
        model="fake",
        judge_model="fake",
    )
    s = AgentSupervisor(args)
    turn = s.directory / "turn"
    turn.mkdir()
    assert s.launch(turn, "continue working") == 124
    assert s.boundary() is None
    assert "worker_turn_timeout" in (s.directory / "events.jsonl").read_text()
    assert "child_pid" not in s.state


def test_grok_judge_transport_and_fences(tmp_path):
    p = tmp_path / "response.json"
    p.write_text(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": (
                    '```json\n{"decision":"insufficient","scientific_disposition":"open"}\n```'
                ),
            }
        )
    )
    result = parse_judge_stream(p, "grok")
    assert result["scientific_disposition"] == "open"  # Parser must NOT fix scientific semantics.
    from conjecture_solver.mvp_agent import MVPJudgeVerdict

    with pytest.raises(ValueError):
        MVPJudgeVerdict.model_validate(result)
    p.write_text(
        json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use"}]}})
        + "\n"
        + p.read_text()
    )
    with pytest.raises(ValueError, match="used a tool"):
        parse_judge_stream(p, "grok")


def test_judge_schema_retry_preserves_case_and_rejects_invalid_disposition(tmp_path, monkeypatch):
    from conjecture_solver.mvp_agent import MVPJudgeVerdict

    root = tmp_path / "campaign"
    root.mkdir()
    args = argparse.Namespace(
        campaign=root, state_dir=tmp_path / "supervisor", wall_seconds=60, backend="grok"
    )
    supervisor = AgentSupervisor(args)
    responses = [
        {
            "claim_id": "claim_root",
            "contract_version": 1,
            "decision": "insufficient",
            "scientific_disposition": "open",
            "claim_tested": False,
            "contract_preserves_claim_semantics": False,
            "rationale": "The measurements do not resolve the original claim.",
            "evidence_gaps": ["No qualifying onset observed"],
            "next_test": "Extend the shared horizon",
        }
    ]
    responses.append({**responses[0], "scientific_disposition": None})
    prompts = []

    def launch(directory, prompt, judge=False):
        prompts.append(prompt)
        (directory / "response.json").write_text(
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "result": json.dumps(responses[len(prompts) - 1]),
                }
            )
        )
        return 0

    monkeypatch.setattr(supervisor, "launch", launch)
    parent = tmp_path / "review"
    parent.mkdir()
    result, _ = supervisor.judge_case(
        parent,
        {"original_claim": "all18 cases"},
        MVPJudgeVerdict.model_json_schema(),
        "adjudication",
    )
    assert len(prompts) == 2
    assert all("all18 cases" in p for p in prompts)
    assert result["scientific_disposition"] is None
    assert result["decision"] == "insufficient"


def test_large_codex_case_uses_stdin_without_changing_prompt(tmp_path):
    import sys

    root = tmp_path / "campaign"
    root.mkdir()
    fake = tmp_path / "codex-transport-probe"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import sys,json,hashlib\n"
        'assert sys.argv[-1] == "-"\n'
        "raw=sys.stdin.read()\n"
        'print(json.dumps({"sha256":hashlib.sha256(raw.encode()).hexdigest()}))\n'
    )
    fake.chmod(0o700)
    args = argparse.Namespace(
        campaign=root,
        state_dir=tmp_path / "supervisor",
        wall_seconds=20,
        turn_seconds=10,
        executable=str(fake),
        model="fake",
        judge_model="fake",
        backend="codex-glm",
        workflow="structured",
    )
    s = AgentSupervisor(args)
    directory = s.directory / "judge"
    directory.mkdir()
    prompt = "A complete scientific case.\n" * 10000
    assert s.launch(directory, prompt, judge=True) == 0
    import hashlib

    assert (
        json.loads((directory / "response.json").read_text())["sha256"]
        == hashlib.sha256(prompt.encode()).hexdigest()
    )


@pytest.mark.parametrize(
    "backend,output_format", [("grok", "streaming-messages-json"), ("agy", "stream-json")]
)
def test_native_backends_stream_activity_for_watchdog(tmp_path, backend, output_format):
    import sys

    root = tmp_path / "campaign"
    root.mkdir()
    executable = tmp_path / "transport-fixture"
    executable.write_text(f"#!{sys.executable}\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n")
    executable.chmod(0o755)
    args = argparse.Namespace(
        campaign=root,
        state_dir=root / "supervisor",
        wall_seconds=30,
        turn_seconds=5,
        backend=backend,
        model="fixture",
        judge_model="fixture",
        executable=str(executable),
        workflow="frontier",
    )
    supervisor = AgentSupervisor(args)
    directory = supervisor.directory / "turn-00001"
    directory.mkdir()
    assert supervisor.launch(directory, "Transport fixture; no model call.") == 0
    argv = json.loads((directory / "response.json").read_text())
    assert argv[argv.index("--output-format") + 1] == output_format


def test_codex_startup_diagnostic_is_not_judge_tool_use(tmp_path):
    path = tmp_path / "response.json"
    events = [
        {"type": "item.completed", "item": {"type": "error", "message": "Ignored setting"}},
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": '{"decision":"approved"}'},
        },
        {"type": "turn.completed"},
    ]
    path.write_text("\n".join(json.dumps(e) for e in events))
    assert parse_judge_stream(path, "codex") == {"decision": "approved"}
    events[-1] = {"type": "turn.failed", "error": {"message": "connection lost"}}
    path.write_text("\n".join(json.dumps(e) for e in events))
    with pytest.raises(ValueError, match="successful complete"):
        parse_judge_stream(path, "codex")
    events[-1] = {"type": "turn.completed"}
    events.insert(1, {"type": "item.completed", "item": {"type": "command_execution"}})
    path.write_text("\n".join(json.dumps(e) for e in events))
    with pytest.raises(ValueError, match="used a tool"):
        parse_judge_stream(path, "codex")
