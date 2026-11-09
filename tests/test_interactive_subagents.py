from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conjecture_solver.research_service import put
from conjecture_solver.web.activity import describe_tool
from conjecture_solver.web.subagents import (
    import_subagent_outputs,
    normalize_tasks,
    run_subagent,
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


def test_subagent_handoff_validation_and_import(tmp_path: Path):
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


def test_run_subagent_handles_agent_execution(tmp_path: Path, monkeypatch):
    workspace = Workspace(tmp_path / ".workspace")
    workspace.save_api({"base_url": "http://127.0.0.1:9999/v1"})
    project = workspace.create({"name": "Subagent runner"})
    workspace.select_agent(project["id"], {"backend": "builtin", "model": "test-model"})
    project_dir = workspace.directory(project["id"])

    real_popen = subprocess.Popen

    def fake_popen(cmd, *args, **kwargs):
        cwd = Path(kwargs["cwd"])
        script = (
            "import json, pathlib; "
            "w = pathlib.Path('.'); "
            "(w / 'out.txt').write_text('ok\\n'); "
            "(w / 'HELPER_RESULT.json').write_text(json.dumps({"
            "'status': 'completed', "
            "'summary': 'Produced out.txt cleanly in isolated workspace.', "
            "'artifacts': ['out.txt'], "
            "'checks': ['out.txt non-empty'], "
            "'unresolved': []}))"
        )
        return real_popen([sys.executable, "-c", script], *args, **{**kwargs, "cwd": cwd})

    monkeypatch.setattr("conjecture_solver.web.subagents.subprocess.Popen", fake_popen)
    from conjecture_solver.web.subagents import SubagentTaskSpec, launch_subagent

    conn = tmp_path / "conn.json"
    conn.write_text('{"backend": "builtin", "model": "test"}')
    spec = SubagentTaskSpec(
        name="Quick check",
        task="Write out.txt in isolated workspace.",
        completion_criteria="out.txt is non-empty.",
        outputs=["out.txt"],
        timeout_seconds=30,
    )
    snap = launch_subagent(project_dir, spec, conn)
    rc = run_subagent(project_dir / "simulations" / snap["id"])
    assert rc == 0
    final = workspace.subagent_status(project["id"], snap["id"])
    assert final["status"] == "succeeded"
    assert final["subagent_result"]["status"] == "completed"
