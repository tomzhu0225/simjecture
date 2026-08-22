from __future__ import annotations

import json
import signal
import sys
from pathlib import Path

import pytest

from conjecture_solver import dsh_engine
from conjecture_solver.dsh_engine import DshEngineError, run_dsh_campaign
from conjecture_solver.mvp_control import read_clock
from conjecture_solver.mvp_launch import MVPLaunchRequest, materialize_operator_input


def _fake_dsh(path: Path, *, status: str = "idle") -> Path:
    selected = (
        "SIMJECTURE_WORKSPACE",
        "SIMJECTURE_CAMPAIGN",
        "SIMJECTURE_HYPOTHESIS_FILE",
        "SIMJECTURE_CAPABILITIES",
        "SIMJECTURE_SKILLS",
        "SIMJECTURE_MCP_MAX_OUTPUT_CHARS",
        "SIMJECTURE_MCP_TIMEOUT_SECONDS",
        "SIMJECTURE_DSH_SESSION_ID",
        "SIMJECTURE_DSH_SESSION_ROOT",
        "SIMJECTURE_DSH_ACTIVITY_FILE",
        "SIMJECTURE_DSH_STATE_FILE",
        "SIMJECTURE_DSH_CONTROL_FILE",
        "SIMJECTURE_DSH_RESUME",
        "PATH",
    )
    path.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        f"keys = {selected!r}\n"
        "captured = {'argv': sys.argv[1:], 'env': {key: os.environ.get(key) for key in keys}}\n"
        "Path('captured_dsh.json').write_text(json.dumps(captured))\n"
        "state = Path(os.environ['SIMJECTURE_DSH_STATE_FILE'])\n"
        f"state.write_text(json.dumps({{'status': {status!r}, 'engine': 'dsh'}}))\n"
    )
    path.chmod(0o700)
    return path


def _launch(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "campaign"
    hypothesis = "A bounded private hypothesis remains outside DSH argv."
    plan = materialize_operator_input(
        MVPLaunchRequest(
            hypothesis=hypothesis,
            campaign_id="campaign-dsh-adapter",
            output_directory=str(root),
            engine="dsh",
            max_command_seconds=123,
            max_tool_output_chars=12_345,
        )
    )
    assert plan.dsh_session_id is not None
    return root, plan.dsh_session_id, hypothesis


def test_dsh_process_adapter_passes_only_paths_and_reuses_session(tmp_path: Path) -> None:
    root, session_id, hypothesis = _launch(tmp_path)
    executable = _fake_dsh(tmp_path / "dsh")
    result = run_dsh_campaign(
        root,
        session_id=session_id,
        resume=True,
        executable=str(executable),
    )
    assert result == 0
    captured = json.loads((root / "captured_dsh.json").read_text())
    assert captured["argv"][:2] == ["--profile", "simjecture"]
    assert hypothesis not in " ".join(captured["argv"])
    environment = captured["env"]
    assert environment["SIMJECTURE_DSH_SESSION_ID"] == session_id
    assert environment["SIMJECTURE_DSH_RESUME"] == "1"
    assert environment["SIMJECTURE_MCP_TIMEOUT_SECONDS"] == "123"
    assert environment["SIMJECTURE_MCP_MAX_OUTPUT_CHARS"] == "12345"
    assert Path(environment["SIMJECTURE_DSH_SESSION_ROOT"]).is_relative_to(root)
    assert Path(environment["SIMJECTURE_HYPOTHESIS_FILE"]) == (
        root / "operator_input" / "hypothesis.txt"
    )
    clock = read_clock(root)
    assert clock is not None
    assert clock.state == "finished"


def test_dsh_environment_preserves_virtualenv_scripts_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id, _hypothesis = _launch(tmp_path)
    executable = _fake_dsh(tmp_path / "dsh")
    virtualenv_bin = tmp_path / "venv" / "bin"
    virtualenv_bin.mkdir(parents=True)
    virtualenv_python = virtualenv_bin / "python"
    virtualenv_python.symlink_to(sys.executable)
    monkeypatch.setattr(dsh_engine.sys, "executable", str(virtualenv_python))

    result = run_dsh_campaign(root, session_id=session_id, executable=str(executable))

    assert result == 0
    captured = json.loads((root / "captured_dsh.json").read_text())
    assert captured["env"]["PATH"].split(":", 1)[0] == str(virtualenv_bin)


def test_dsh_process_adapter_rejects_session_or_artifact_substitution(tmp_path: Path) -> None:
    root, session_id, _hypothesis = _launch(tmp_path)
    executable = _fake_dsh(tmp_path / "dsh")
    with pytest.raises(DshEngineError, match="session identity"):
        run_dsh_campaign(root, session_id="simjecture-wrong", executable=str(executable))

    outside = tmp_path / "outside.log"
    outside.write_text("outside\n")
    activity = root / "operator_input" / "dsh_activity.jsonl"
    activity.symlink_to(outside)
    with pytest.raises(DshEngineError, match="must not be a symlink"):
        run_dsh_campaign(root, session_id=session_id, executable=str(executable))


def test_dsh_process_adapter_enforces_total_wall_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id, _hypothesis = _launch(tmp_path)
    executable = _fake_dsh(tmp_path / "dsh")

    def timeout(*_args: object, **kwargs: object) -> None:
        raise dsh_engine.subprocess.TimeoutExpired(
            cmd="dsh",
            timeout=float(kwargs["timeout"]),
        )

    monkeypatch.setattr(dsh_engine.subprocess, "run", timeout)

    result = run_dsh_campaign(root, session_id=session_id, executable=str(executable))

    assert result == 124
    state = json.loads((root / "operator_input" / "dsh_state.json").read_text())
    assert state["status"] == "budget_exhausted"
    clock = read_clock(root)
    assert clock is not None
    assert clock.state == "finished"


def test_dsh_process_adapter_finalizes_clock_on_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id, _hypothesis = _launch(tmp_path)
    executable = _fake_dsh(tmp_path / "dsh")

    def interrupt(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(dsh_engine.subprocess, "run", interrupt)

    result = run_dsh_campaign(root, session_id=session_id, executable=str(executable))

    assert result == 130
    state = json.loads((root / "operator_input" / "dsh_state.json").read_text())
    assert state["status"] == "cancelled"
    clock = read_clock(root)
    assert clock is not None
    assert clock.state == "finished"


def test_dsh_process_adapter_finalizes_clock_on_sigterm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, session_id, _hypothesis = _launch(tmp_path)
    executable = _fake_dsh(tmp_path / "dsh")
    prior_handler = signal.getsignal(signal.SIGTERM)

    def terminate(*_args: object, **_kwargs: object) -> None:
        handler = signal.getsignal(signal.SIGTERM)
        assert callable(handler)
        handler(signal.SIGTERM, None)

    monkeypatch.setattr(dsh_engine.subprocess, "run", terminate)

    result = run_dsh_campaign(root, session_id=session_id, executable=str(executable))

    assert result == 128 + signal.SIGTERM
    assert signal.getsignal(signal.SIGTERM) is prior_handler
    state = json.loads((root / "operator_input" / "dsh_state.json").read_text())
    assert state["status"] == "cancelled"
    assert "SIGTERM" in state["reason"]
    clock = read_clock(root)
    assert clock is not None
    assert clock.state == "finished"
