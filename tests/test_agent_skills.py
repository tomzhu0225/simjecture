"""The browser and autonomous API workers share the existing research skills."""

import json
import time
from pathlib import Path

import pytest

from conjecture_solver.agent_skills import research_skills, skill_context


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
