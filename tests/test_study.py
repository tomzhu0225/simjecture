import argparse
import json
import sys

import pytest

from conjecture_solver.study import configure_parser, run, selected_mode


def test_new_default_and_archived_modes_cannot_resume(tmp_path):
    assert selected_mode(tmp_path) == "minimal"
    for mode in ["structured", "frontier", "legacy"]:
        with pytest.raises(ValueError, match="have been removed"):
            selected_mode(tmp_path, mode)
    (tmp_path / "research.json").write_text("{}")
    assert selected_mode(tmp_path) == "minimal"
    (tmp_path / "research.json").unlink()
    state = tmp_path / "old-supervisor"
    state.mkdir()
    (state / "state.json").write_text(json.dumps(dict(workflow="frontier")))
    with pytest.raises(ValueError, match="have been removed"):
        selected_mode(tmp_path, state_dir=state)


@pytest.mark.parametrize("mode", ["minimal"])
def test_launch_modes_materialize_correct_records(tmp_path, monkeypatch, mode):
    from conjecture_solver.agent_supervisor import AgentSupervisor
    from conjecture_solver.research_supervisor import ResearchSupervisor

    hypothesis, instructions = tmp_path / "h.txt", tmp_path / "i.txt"
    hypothesis.write_text("A finite arithmetic claim.")
    instructions.write_text("Test the finite claim.")
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    root = tmp_path / "study"
    args = parser.parse_args(
        [
            "--campaign",
            str(root),
            "--hypothesis-file",
            str(hypothesis),
            "--instructions-file",
            str(instructions),
            "--mode",
            mode,
            "--executable",
            sys.executable,
        ]
    )
    calls = []

    def fake_run(self):
        calls.append(type(self))
        return 0

    monkeypatch.setattr(AgentSupervisor, "run", fake_run)
    monkeypatch.setattr(ResearchSupervisor, "run", fake_run)
    assert run(args) == 0
    assert calls == [ResearchSupervisor if mode == "minimal" else AgentSupervisor]
    assert (root / ("research.json" if mode == "minimal" else "mvp_manifest.json")).is_file()
    assert json.loads((root / "study-mode.json").read_text())["mode"] == mode


def test_cli_exposes_default_study_command():
    from conjecture_solver.cli import build_parser

    args = build_parser().parse_args(["study", "--campaign", "new", "--instructions-file", "i"])
    assert args.mode is None
    assert args.handler is run


def test_direct_cli_resume_preserves_exact_frozen_hypothesis(tmp_path, monkeypatch):
    from conjecture_solver.research_supervisor import ResearchSupervisor

    hypothesis, instructions = tmp_path / "h.txt", tmp_path / "i.txt"
    original = "A finite arithmetic claim.\n"
    hypothesis.write_text(original)
    instructions.write_text("Test the finite claim.\n")
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    root = tmp_path / "study"
    argv = [
        "--campaign", str(root), "--hypothesis-file", str(hypothesis),
        "--instructions-file", str(instructions), "--executable", sys.executable,
    ]
    monkeypatch.setattr(ResearchSupervisor, "run", lambda self: 0)
    assert run(parser.parse_args(argv)) == 0
    assert (root / "operator_input/hypothesis.txt").read_text() == original
    argv[argv.index("--hypothesis-file") + 1] = str(root / "operator_input/hypothesis.txt")
    assert run(parser.parse_args(argv)) == 0
    assert json.loads((root / "research.json").read_text())["hypothesis"] == original


def test_legacy_resume_inherits_wrapper_and_rejects_changed_review_route(tmp_path, monkeypatch):
    from conjecture_solver.research_supervisor import ResearchSupervisor

    hypothesis, instructions = tmp_path / "h.txt", tmp_path / "i.txt"
    hypothesis.write_text("A finite claim.")
    instructions.write_text("Check this finite claim.")
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    root = tmp_path / "study"
    argv = [
        "--campaign", str(root), "--hypothesis-file", str(hypothesis),
        "--instructions-file", str(instructions), "--executable", sys.executable,
    ]
    monkeypatch.setattr(ResearchSupervisor, "run", lambda self: 0)
    assert run(parser.parse_args(argv)) == 0
    path = root / "study-launch.json"
    record = json.loads(path.read_text())
    record.pop("reviewer_route")
    for key in ("judge_backend", "judge_executable", "judge_provider_config"):
        record["request"].pop(key)
    path.write_text(json.dumps(record))
    deadline = json.loads((root / "research.json").read_text())["deadline"]
    for field, value in [
        ("--judge-backend", "grok"),
        ("--judge-executable", "another-wrapper"),
        ("--judge-provider-config", "another-provider.json"),
    ]:
        with pytest.raises(ValueError, match="Reviewer backend is part"):
            run(parser.parse_args([*argv, field, value]))
    assert run(parser.parse_args([*argv, "--judge-backend", "codex-glm"])) == 0
    assert json.loads((root / "research.json").read_text())["deadline"] == deadline


def test_director_route_is_saved_and_immutable_on_resume(tmp_path, monkeypatch):
    from conjecture_solver.research_supervisor import ResearchSupervisor

    hypothesis, instructions = tmp_path / "h.txt", tmp_path / "i.txt"
    hypothesis.write_text("A finite claim.")
    instructions.write_text("Check the claim.")
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    root = tmp_path / "study"
    argv = ["--campaign", str(root), "--hypothesis-file", str(hypothesis),
            "--instructions-file", str(instructions), "--executable", sys.executable]
    monkeypatch.setattr(ResearchSupervisor, "run", lambda self: 0)
    selected = ["--judge-model", "reviewer", "--director-model", "director",
                "--director-reasoning-effort", "high"]
    assert run(parser.parse_args(argv + selected)) == 0
    saved = json.loads((root / "study-launch.json").read_text())["request"]
    assert saved["director_model"] == "director"
    assert saved["director_reasoning_effort"] == "high"
    assert run(parser.parse_args(argv)) == 0
    for option, value in [("--director-model", "other"),
                          ("--director-reasoning-effort", "low")]:
        with pytest.raises(ValueError, match="saved launch contract"):
            run(parser.parse_args(argv + [option, value]))
