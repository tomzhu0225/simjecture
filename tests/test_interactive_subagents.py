from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conjecture_solver.research_service import put
from conjecture_solver.web.activity import describe_tool
from conjecture_solver.web.subagents import (
    import_subagent_outputs,
    normalize_tasks,
    validate_subagent_handoff,
)
from conjecture_solver.web.workspace import Workspace


def test_normalize_tasks_validates_bounds_and_output_paths():
    specs = normalize_tasks(
        {
            "tasks": [
                {
                    "name": "Mesh convergence",
                    "task": "Run two grid resolutions and record L2 error.",
                    "completion_criteria": "Produce convergence.json with both L2 errors.",
                    "outputs": ["convergence.json", "plots/err.txt"],
                    "input_files": ["setup.py"],
                    "timeout_seconds": 120,
                }
            ]
        }
    )
    assert len(specs) == 1
    assert specs[0].outputs == ["convergence.json", "plots/err.txt"]

    with pytest.raises(ValueError, match="between one and four"):
        normalize_tasks({"tasks": []})

    with pytest.raises(ValueError, match="distinct"):
        normalize_tasks(
            {
                "name": "Duplicate output",
                "task": "Write the same file twice.",
                "completion_criteria": "Write result.json.",
                "outputs": ["result.json", "./result.json"],
            }
        )

    with pytest.raises(ValueError, match="relative file path"):
        normalize_tasks(
            {
                "name": "Traversal output",
                "task": "Attempt parent traversal.",
                "completion_criteria": "Must fail validation.",
                "outputs": ["../escape.txt"],
            }
        )


def test_describe_tool_recognizes_subagent_tools():
    info = describe_tool(
        "run_subagents",
        {"tasks": [{"name": "Proof check"}, {"name": "Parameter sweep"}]},
    )
    assert info["label"] == "Running subagents"
    assert "Proof check, Parameter sweep" in info["detail"]

    status_info = describe_tool("subagent_status", {"identifier": "001-subagent-proof"})
    assert status_info["label"] == "Checking subagent"
    assert status_info["detail"] == "001-subagent-proof"


def test_subagent_handoff_validation_and_import(tmp_path: Path, monkeypatch):
    real_popen = subprocess.Popen
    monkeypatch.setattr(
        subprocess, "Popen", lambda cmd, **kw: real_popen([sys.executable, "-c", "pass"], **kw)
    )
    workspace = Workspace(tmp_path / ".workspace")
    workspace.save_api({"base_url": "http://127.0.0.1:9999/v1"})
    project = workspace.create({"name": "Subagent test"})
    workspace.select_agent(project["id"], {"backend": "builtin", "model": "test-model"})
    project_dir = workspace.directory(project["id"])
    (project_dir / "files/input.txt").write_text("alpha=0.25\n")

    # Launch without waiting and stub the child runner to simulate completion
    launched = workspace.start_subagents(
        project["id"],
        {
            "wait": False,
            "tasks": [
                {
                    "name": "Compute summary",
                    "task": "Read input.txt and produce summary.json.",
                    "completion_criteria": "summary.json exists with alpha.",
                    "outputs": ["summary.json"],
                    "input_files": ["input.txt"],
                    "timeout_seconds": 30,
                }
            ],
        },
    )
    assert len(launched["tasks"]) == 1
    task_id = launched["tasks"][0]["id"]
    root = project_dir / "simulations" / task_id
    request = json.loads((root / "request.json").read_text())
    work = Path(request["work_directory"])
    assert (work / "input.txt").read_text() == "alpha=0.25\n"
    assert (work / "inputs/input.txt").read_text() == "alpha=0.25\n"

    # Write required deliverable and valid HELPER_RESULT.json
    (work / "summary.json").write_text('{"alpha": 0.25, "verified": true}\n')
    put(
        work / "HELPER_RESULT.json",
        {
            "status": "completed",
            "summary": "Computed alpha summary and verified input consistency.",
            "artifacts": ["summary.json"],
            "checks": ["verified alpha == 0.25"],
            "unresolved": [],
        },
    )
    handoff = validate_subagent_handoff(root, request)
    assert handoff["status"] == "completed"
    assert "summary.json" in handoff["artifacts"]
    put(root / "state.json", {"status": "succeeded", "finished_at": request["created_at"] + 1})

    assert workspace.subagent_status(project["id"], task_id, import_files=[])["imported"] == []
    assert not (project_dir / "files/summary.json").exists()

    # A conflict on a later deliverable must not leave an earlier file or receipt behind.
    (work / "other.json").write_text("new")
    (project_dir / "files/other.json").write_text("existing")
    result_path = work / "HELPER_RESULT.json"
    result = json.loads(result_path.read_text())
    result["artifacts"].append("other.json")
    put(result_path, result)
    validate_subagent_handoff(root, request)
    with pytest.raises(ValueError, match="already exists"):
        workspace.subagent_status(project["id"], task_id, import_files=result["artifacts"])
    assert not (project_dir / "files/summary.json").exists()
    assert not list((project_dir / "subagent_imports").glob("*.json"))
    (work / "other.json").write_text("changed after validation")
    with pytest.raises(ValueError, match="changed after handoff"):
        workspace.subagent_status(
            project["id"], task_id, import_files=result["artifacts"], overwrite=True
        )
    assert (project_dir / "files/other.json").read_text() == "existing"
    assert not (project_dir / "files/summary.json").exists()

    # Inspect status and import deliverable into conversation files/
    status = workspace.subagent_status(
        project["id"],
        task_id,
        import_files=["summary.json"],
    )
    assert status["subagent_result"]["status"] == "completed"
    assert len(status["imported"]) == 1
    assert (project_dir / "files/summary.json").is_file()
    assert json.loads((project_dir / "files/summary.json").read_text())["verified"] is True

    # Re-importing without overwrite=True must fail
    with pytest.raises(ValueError, match="already exists"):
        import_subagent_outputs(project_dir, task_id, ["summary.json"], overwrite=False)

    # Tampering with frozen inputs/ copy must be rejected
    (work / "inputs/input.txt").write_text("tampered\n")
    with pytest.raises(ValueError, match="frozen inputs"):
        validate_subagent_handoff(root, request)


def test_two_cli_subagents_run_concurrently_and_import_separately(tmp_path, monkeypatch):
    from conjecture_solver.research_helper_runtime import process_stat
    from tests.test_workspace import wait_for

    binary = tmp_path / "codex"
    binary.write_text(
        f"#!{sys.executable}\n"
        + """
import json, os, subprocess, sys, time
from pathlib import Path
context = json.loads(Path('CONTEXT.json').read_text())
worker = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(12)'])
Path('worker.pid').write_text(str(worker.pid))
Path('started').touch()
while not Path(os.environ['SIMJECTURE_TEST_GATE']).exists():
    time.sleep(.05)
name = context['outputs'][0]
Path(name).write_text(Path('inputs/input.txt').read_text() + context['name'])
Path('HELPER_RESULT.json').write_text(json.dumps(dict(
    status='completed', summary='Verified the selected input and saved its result.',
    artifacts=[name], checks=['input read'], unresolved=[],
)))
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'Done.'}}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}}))
"""
    )
    binary.chmod(0o755)
    gate = tmp_path / "release"
    monkeypatch.setenv("SIMJECTURE_TEST_GATE", str(gate))
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    ws = Workspace(tmp_path / ".workspace")
    project = ws.create({"name": "Parallel checks", "agent": {"backend": "codex", "model": "test"}})
    project_id = project["id"]
    project_dir = ws.directory(project_id)
    files = project_dir / "files"
    (files / "input.txt").write_text("read by ")
    (files / "inputs").mkdir()
    (files / "inputs/input.txt").write_text("a different project input")
    specs = [
        dict(
            name=name,
            task="Read the selected input.",
            completion_criteria="Record the name.",
            outputs=[name + ".txt"],
            input_files=["input.txt", "inputs/input.txt"],
            timeout_seconds=30,
        )
        for name in ("Analyst", "Verifier")
    ]
    with pytest.raises(ValueError):
        ws.start_subagents(
            project_id, {"tasks": [specs[0], specs[1] | {"input_files": ["absent"]}]}
        )
    assert not list(project_dir.glob("simulations/*/request.json"))
    assert not list(ws.root.glob("turn-connections/*"))
    jobs = ws.start_subagents(project_id, {"tasks": specs, "wait": False})["tasks"]
    try:
        wait_for(lambda: all((Path(j["work_directory"]) / "started").exists() for j in jobs))
        for task in ws.subagent_status(project_id)["tasks"]:
            assert task["live"]
            assert (Path(task["work_directory"]) / "inputs/inputs/input.txt").read_text() == (
                "a different project input"
            )
            assert (
                next(f for f in task["files"] if f["name"] == "inputs/input.txt")["role"] == "input"
            )
    finally:
        gate.touch()
    for j in jobs:
        name = j["name"] + ".txt"
        wait_for(lambda j=j: ws.subagent_status(project_id, j["id"])["status"] == "succeeded")
        pid = int((Path(j["work_directory"]) / "worker.pid").read_text())
        assert process_stat(pid) is None
        assert not (files / name).exists()
        ws.subagent_status(project_id, j["id"], import_files=[name])
        assert (files / name).read_text() == "read by " + j["name"]
    assert not list(ws.root.glob("turn-connections/*"))


def test_sibling_prompts_share_skill_and_handoff_prefix(tmp_path):
    import time

    from conjecture_solver.web.subagents import build_subagent_prompt

    def prompt(name):
        request = dict(
            task=f"Measure {name}.",
            completion_criteria=f"Save {name}.",
            expected_outputs=[name],
            created_at=time.time(),
            timeout_seconds=30,
        )
        return build_subagent_prompt(request, tmp_path / name)

    common = os.path.commonprefix([prompt("grid"), prompt("mass")])
    assert "AVAILABLE SIMJECTURE RESEARCH SKILLS" in common
    assert "HELPER_RESULT.json" in common
    assert '"properties"' in common


def test_chat_dispatches_worker_and_imports_handoff_via_api_tools(tmp_path):
    from contextlib import contextmanager

    from tests.test_workspace import wait_for
    from tests.test_workspace_protocol import api, response

    with contextmanager(api.__wrapped__)() as (url, requests, replies):
        ws = Workspace(tmp_path / ".workspace")
        ws.save_api({"base_url": url})
        project = ws.create(
            {
                "name": "Chat handoff",
                "agent": {
                    "backend": "builtin",
                    "model": "deepseek-fixture",
                },
            }
        )
        assignment = dict(
            name="Grid",
            task="Write the grid check.",
            outputs=["grid.txt"],
            completion_criteria="Record the grid count.",
            input_files=[],
        )
        handoff = dict(
            status="completed",
            summary="Recorded the grid count in the output.",
            artifacts=["grid.txt"],
            checks=["grid count recorded"],
            unresolved=[],
        )
        replies.extend(
            [
                response(("dispatch", "run_subagents", {"tasks": [assignment], "wait": True})),
                response(("file", "write_file", {"path": "grid.txt", "content": "32"})),
                response(
                    (
                        "handoff",
                        "write_file",
                        {"path": "HELPER_RESULT.json", "content": json.dumps(handoff)},
                    )
                ),
                response(("done", "final_answer", {"answer": "The grid count is saved."})),
                response(
                    (
                        "collect",
                        "subagent_status",
                        {"identifier": "001-subagent-grid", "import_files": ["grid.txt"]},
                    )
                ),
                response(("finish", "final_answer", {"answer": "The grid count is 32."})),
            ]
        )
        ws.send(
            project["id"], {"message": "Ask a helper for the grid count and import its result."}
        )
        try:
            wait_for(lambda: not ws.project(project["id"])["running"], seconds=40)
            finished = ws.project(project["id"])
            assert finished["messages"][-1]["content"] == "The grid count is 32."
            assert finished["messages"][-1]["links"][0]["subagent"]
            assert (ws.directory(project["id"]) / "files/grid.txt").read_text() == "32"
            assert len(requests) == 6
        finally:
            ws.stop(project["id"])
