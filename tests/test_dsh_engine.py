from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from conjecture_solver.dsh_engine import DshEngineError, run_dsh_campaign
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
    assert (root / "operator_input" / "run_clock.json").is_file()


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
