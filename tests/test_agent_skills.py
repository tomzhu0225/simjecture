"""The browser and autonomous API workers share the existing research skills."""

import json
import time
from pathlib import Path

import pytest

from conjecture_solver.agent_skills import research_skills, skill_context


def test_documentation_does_not_depend_on_runtime_health(monkeypatch):
    from conjecture_solver.mvp_skills import MVPCapabilityRegistry

    def unavailable(*args, **kwargs):
        raise ValueError("capability executable is unavailable or not executable")

    monkeypatch.setattr(MVPCapabilityRegistry, "discover", unavailable)
    assert "flash-mhd" in research_skills()
    assert "local-cuda-deployment.md" in research_skills().read(
        "warpx", "SKILL.md", max_chars=32000
    )["content"]


def test_catalogue_advertises_existing_absolute_skill_entrypoints():
    skills = research_skills()
    context = skill_context()
    for name in ("flash-mhd", "warpx", "python-experiment"):
        assert name in skills
        path = skills.root / name / "SKILL.md"
        assert path.is_file() and str(path) in context
    assert "read_skill(name" in context


def test_api_worker_can_read_skill_references_without_project_path_escape(tmp_path):
    pytest.importorskip("smolagents")
    from conjecture_solver.workspace_agent import agent_tools

    tool = next(t for t in agent_tools(tmp_path, time.time() + 60) if t.name == "read_skill")
    document = json.loads(tool(name="flash-mhd"))
    assert "# FLASH MHD" in document["content"]
    reference = json.loads(tool(name="flash-mhd", path="references/execution-output.md"))
    assert "-par_file" in reference["content"]
    with pytest.raises(ValueError):
        tool(name="flash-mhd", path="../../pyproject.toml")
    assert list(Path(tmp_path).iterdir()) == []


def test_skill_read_exposes_resource_manifest_and_helpful_missing_resource_error():
    skills = research_skills()
    entry = skills.read("elmer", "SKILL.md", max_chars=32000)
    assert "references/installation.md" in entry["resources"]
    assert "examples/conductor_control.py" in entry["resources"]
    assert "examples/health_check.py" in entry["resources"]
    with pytest.raises(ValueError, match="references/installation.md"):
        skills.read("elmer", "references/nonexistent.md", max_chars=32000)


def test_all_catalogue_tools_have_setup_guides_referencing_real_skill_files(tmp_path):
    import re

    from conjecture_solver.research_service import put
    from conjecture_solver.web.workspace import CATALOGUE, Workspace

    js = (
        Path(__file__).resolve().parents[1]
        / "src/conjecture_solver/web/static/workspace.js"
    ).read_text()
    block = re.search(r"const toolSetupGuides = \{(.*?)\n\};", js, re.S)
    assert block is not None
    body = block.group(1)
    skills = research_skills()
    for tool_id, *_ in CATALOGUE:
        key = re.escape(tool_id)
        pattern = rf'(?:^|\n)\s*(?:{key}|"{key}")\s*:\s*\{{([^}}]*)\}}'
        match = re.search(pattern, body)
        assert match is not None, f"Missing toolSetupGuides entry for {tool_id}"
        entry = match.group(1)
        skill_match = re.search(r'skill:\s*"([^"]+)"', entry)
        assert skill_match is not None
        skill_name = skill_match.group(1)
        assert skill_name in skills
        read_match = re.search(r"read:\s*\[([^\]]*)\]", entry)
        assert read_match is not None
        for ref in re.findall(r'"([^"]+)"', read_match.group(1)):
            assert skills.read(skill_name, ref, max_chars=4000)["content"]
    assert "if (tool.skill)" in js

    workspace = Workspace(tmp_path / ".workspace")
    runtime = tmp_path / "custom-runtime"
    runtime.mkdir()
    exe = runtime / "run"
    exe.write_text("#!/bin/sh\nexit 0\n")
    exe.chmod(0o755)
    cap_dir = tmp_path / "custom-cap"
    cap_dir.mkdir()
    put(
        cap_dir / "elmer-custom.json",
        {
            "runtime_root": str(runtime),
            "executable": "run",
            "manifest": {
                "name": "elmer-custom-0.1",
                "version": "0.1",
                "description": "Custom Elmer",
                "skill": "elmer",
                "executable_kind": "python",
            },
        },
    )
    record = workspace.register_tool({"name": "Custom Elmer", "path": str(cap_dir)})
    custom_card = next(c for c in workspace.catalogue() if c["id"] == record["id"])
    assert custom_card["skill"] == "elmer"


def test_classic_researcher_and_helper_prompts_include_skill_context(tmp_path, monkeypatch):
    import argparse

    from conjecture_solver.agent_supervisor import AgentSupervisor
    from conjecture_solver.research_helpers import execute_helper
    from conjecture_solver.research_service import ResearchService, put

    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Test the claim.")
    (tmp_path / "classic").mkdir()
    sup = AgentSupervisor(
        argparse.Namespace(
            campaign=tmp_path / "classic",
            state_dir=tmp_path / "classic/supervisor",
            wall_seconds=60,
            turn_seconds=30,
            instructions_file=instructions,
            backend="codex",
            model="fixture",
            judge_model="fixture",
            workflow="frontier",
        )
    )
    prompt = sup.researcher_prompt(
        tmp_path / "classic/turn",
        {"claim_id": "claim_root", "assignment_id": "a1"},
        tmp_path / "classic/kernel_call.py",
    )
    assert "AVAILABLE SIMJECTURE RESEARCH SKILLS" in prompt

    service = ResearchService.create(tmp_path / "study", "Helper skill prompt test")
    helper_dir = service.root / "helpers/helper_1"
    (helper_dir / "research").mkdir(parents=True)
    (service.root / "helper_tasks").mkdir(exist_ok=True)
    put(
        helper_dir / "launch.json",
        {"backend": "codex", "model": "fixture", "judge_model": "fixture"},
    )
    put(
        service.root / "helper_tasks/helper_1.json",
        {
            "id": "helper_1",
            "status": "queued",
            "task": "Check the mesh script",
            "completion_criteria": "Return a validated script",
            "outputs": ["mesh_check.py"],
            "timeout_seconds": 30,
            "deadline": time.time() + 30,
            "workspace": "helpers/helper_1/research",
            "process_identity": {"pid": 12345},
        },
    )
    captured = []
    monkeypatch.setattr("os.getpid", lambda: 12345)
    monkeypatch.setattr("conjecture_solver.research_helpers.owned_alive", lambda _: True)
    monkeypatch.setattr("conjecture_solver.research_helpers.stop_native", lambda _: None)
    monkeypatch.setattr(
        "conjecture_solver.research_helpers.finish_helper", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        AgentSupervisor, "launch", lambda self, d, p, **kw: captured.append(p) or 0
    )
    execute_helper(service.root, "helper_1")
    assert captured and "AVAILABLE SIMJECTURE RESEARCH SKILLS" in captured[0]


def test_api_study_worker_read_file_allows_study_readonly_inputs_and_blocks_secrets(tmp_path):
    pytest.importorskip("smolagents")
    from conjecture_solver.workspace_agent import agent_tools

    study_root = tmp_path / "study"
    work = study_root / "research"
    work.mkdir(parents=True)
    (study_root / "research.json").write_text("{}")
    (study_root / "STUDY_LEDGER.md").write_text("# Ledger\n")
    (study_root / "continuation_input").mkdir()
    (study_root / "continuation_input/brief.json").write_text('{"parent": "ok"}')
    (study_root / "guided_commissioning_input").mkdir()
    (study_root / "guided_commissioning_input/anchor.txt").write_text("anchor")
    exp_work = study_root / "experiments/exp_1/workspace"
    exp_work.mkdir(parents=True)
    (exp_work / "result.json").write_text('{"value": 42}')
    (study_root / "supervisor").mkdir()
    (study_root / "supervisor/provider.json").write_text('{"api_key": "secret"}')

    tools = {t.name: t for t in agent_tools(work, time.time() + 60, project=None)}
    read_file = tools["read_file"]
    write_file = tools["write_file"]

    assert '"parent": "ok"' in read_file(path="../continuation_input/brief.json")
    assert read_file(path="../guided_commissioning_input/anchor.txt") == "anchor"
    assert '"value": 42' in read_file(path=str(exp_work / "result.json"))
    assert "# Ledger" in read_file(path="../STUDY_LEDGER.md")

    with pytest.raises(ValueError):
        read_file(path="../supervisor/provider.json")
    with pytest.raises(ValueError):
        write_file(path="../continuation_input/brief.json", content="overwrite")

    interactive_tools = {t.name: t for t in agent_tools(work, time.time() + 60, project="p1")}
    with pytest.raises(ValueError):
        interactive_tools["read_file"](path="../continuation_input/brief.json")


def test_stale_study_brief_json_is_not_reimported_on_subsequent_cli_turns(tmp_path, monkeypatch):
    from conjecture_solver import workspace_agent
    from conjecture_solver.research_service import put
    from conjecture_solver.web.workspace import Workspace, load

    workspace = Workspace(tmp_path / ".workspace")
    project = workspace.create({"name": "CLI brief persistence"})
    pid = project["id"]
    directory = workspace.directory(pid)
    files = directory / "files"
    brief_file = files / "STUDY_BRIEF.json"
    initial_brief = {
        "question": "Original CLI question",
        "success_criteria": "Original criteria",
        "constraints": "Original constraints",
        "hours": 2,
    }
    brief_file.write_text(json.dumps(initial_brief))
    workspace.save_brief(pid, initial_brief | {"question": "Edited in browser UI"})
    saved = load(directory / "project.json")
    saved["brief_launched"] = "camp-1"
    put(directory / "project.json", saved)

    turn = directory / "turns/1"
    turn.mkdir(parents=True)
    prompt_file = turn / "prompt.txt"
    prompt_file.write_text("Follow-up chat turn that does not touch STUDY_BRIEF.json")
    conn = tmp_path / "conn.json"
    put(conn, {"backend": "codex", "model": "fixture", "base_url": "http://localhost"})

    monkeypatch.setattr(workspace_agent, "run_external", lambda *a, **kw: "ok")
    rc = workspace_agent.main(
        [
            "--provider-config",
            str(conn),
            "--prompt-file",
            str(prompt_file),
            "--cwd",
            str(files),
            "--workspace",
            str(workspace.root),
            "--project",
            pid,
        ]
    )
    assert rc == 0
    after = workspace.project(pid)
    assert after["brief"]["question"] == "Edited in browser UI"
    assert after["brief_launched"] == "camp-1"

    workspace.new_study(pid)
    assert not brief_file.exists()


def test_report_review_prompt_includes_packet_view_and_handles_results_md_paths(tmp_path):
    import argparse

    from conjecture_solver.research_service import ResearchService
    from conjecture_solver.research_supervisor import ResearchSupervisor

    service = ResearchService.create(
        tmp_path / "study",
        "Report packet view test",
        wall_seconds=600,
        report_reserve_seconds=200,
    )
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Test")
    sup = ResearchSupervisor(
        argparse.Namespace(
            campaign=service.root,
            state_dir=service.root / "supervisor",
            wall_seconds=600,
            instructions_file=instructions,
            backend="builtin",
            model="fixture",
            judge_model="fixture",
            turn_seconds=300,
        )
    )
    (service.work / "RESULTS.md").write_text("# Findings\nBounded conclusion.\n")
    frozen, _ = service.freeze_report("research/RESULTS.md")
    review_prompt = sup._report_review_prompt(frozen, 60)
    assert "\nPACKET:\n" in review_prompt
    assert "Bounded conclusion." in review_prompt
    director_packet = sup.director_packet()
    assert "record_index" in director_packet
    director_prompt = sup.director_prompt(director_packet)
    assert '"record_index"' not in director_prompt

