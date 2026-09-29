"""ITER integration routes real execution and keeps unverified solvers distinct."""

import json
from pathlib import Path

import pytest

from conjecture_solver.agent_skills import research_skills
from conjecture_solver.cli import build_parser
from conjecture_solver.deployment import DeploymentManager, DeploymentProfile
from conjecture_solver.web.workspace import CATALOGUE, Workspace


def test_pack_installer_and_skill_are_discoverable():
    assert build_parser().parse_args(["install", "iter-pack"]).profile == "iter-pack"
    assert build_parser().parse_args(["doctor", "--profile", "iter-pack"]).profile == "iter-pack"
    skills = research_skills()
    for reference in (
        "SKILL.md",
        "references/diagnostics.md",
        "references/solps.md",
        "references/jorek.md",
        "references/dina.md",
        "examples/diagnostics_demo.py",
    ):
        assert skills.read("iter-pack", reference, max_chars=32000)["content"]
    cards = {row[0]: row[3] for row in CATALOGUE}
    assert cards["iter-pack"] == "install"
    assert all(cards[name] == "agent" for name in ("solps", "jorek", "dina"))


def test_guided_solver_is_not_a_fake_automatic_install(tmp_path):
    workspace = Workspace(tmp_path / ".workspace")
    for name in ("solps", "jorek", "dina"):
        with pytest.raises(ValueError, match="Install with agent"):
            workspace.start_install({"name": name})
    assert not (workspace.root / "tools").exists()


def test_demo_requires_runtime_and_creates_monitored_project(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path / "runs/.workspace")
    monkeypatch.setattr(
        Workspace,
        "default_agent",
        lambda self: {
            "backend": "builtin",
            "model": "deepseek-flash",
            "reasoning_effort": "",
        },
    )
    root = tmp_path / "deployment"
    for name in ("skills/iter-pack/examples", "capabilities", "environments"):
        (root / name).mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='test'\n")
    (root / "skills/iter-pack/examples/diagnostics_demo.py").write_text("print('demo')\n")
    monkeypatch.setattr("conjecture_solver.deployment.resolve_project_root", lambda *a: root)
    with pytest.raises(ValueError, match="Install the ITER pack"):
        workspace.run_tool_demo({"name": "iter-pack"})
    runtime = root / ".runtime/iter-pack-1.0"
    (runtime / "bin").mkdir(parents=True)
    (runtime / "share").mkdir()
    (runtime / "bin/python").write_text("placeholder")
    (runtime / "share/build-record.json").write_text("{}")
    observed = {}

    def capture(self, identifier, payload):
        observed.update(project=identifier, **payload)
        return {"id": "001-demo"}

    monkeypatch.setattr(Workspace, "start_simulation", capture)
    result = workspace.run_tool_demo({"name": "iter-pack"})
    assert result["simulation"]["id"] == "001-demo"
    assert observed["timeout_seconds"] == 120
    assert str(runtime / "bin/python") in observed["command"]
    assert (workspace.directory(result["project"]) / "files/diagnostics_demo.py").is_file()


def test_automatic_capability_has_real_numerical_checks():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "capabilities/iter-pack-1.0.json").read_text())
    assert set(config["manifest"]["preflight_checks"]) >= {
        "checks.chord_integral",
        "checks.density_scaling",
        "checks.imas_roundtrip",
        "checks.imas_bolometers",
        "checks.iter_geometry",
    }
    manager = DeploymentManager(root)
    assert manager._configured_runtime_root("iter-pack-1.0").name == "iter-pack-1.0"
    assert DeploymentProfile("iter-pack").value == "iter-pack"
