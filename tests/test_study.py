import argparse
import json
import sys

import pytest

from conjecture_solver.study import configure_parser, run, selected_mode


def test_new_default_and_explicit_modes_preserve_resume(tmp_path):
    assert selected_mode(tmp_path) == "minimal"
    assert selected_mode(tmp_path, "frontier") == "frontier"
    (tmp_path / "research.json").write_text("{}")
    assert selected_mode(tmp_path) == "minimal"
    with pytest.raises(ValueError, match="immutable"):
        selected_mode(tmp_path, "structured")
    (tmp_path / "research.json").unlink()
    state = tmp_path / "old-supervisor"
    state.mkdir()
    (state / "state.json").write_text(json.dumps(dict(workflow="frontier")))
    assert selected_mode(tmp_path, state_dir=state) == "frontier"
    with pytest.raises(ValueError, match="immutable"):
        selected_mode(tmp_path, "minimal", state)


@pytest.mark.parametrize("mode", ["minimal", "structured", "frontier"])
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
