"""Persistent interactive runs and public activity regression checks."""

import json
import time

from conjecture_solver.web import jobs
from conjecture_solver.web.activity import native_activity
from conjecture_solver.web.inventory import discover_system_warpx


def await_finished(project, identifier):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        result = jobs.snapshot(project, identifier, include_files=True)
        if result["status"] in jobs.TERMINAL:
            return result
        time.sleep(0.1)
    raise AssertionError("Simulation did not finish")


def test_runs_keep_inputs_logs_and_outputs_and_stop(tmp_path):
    (tmp_path / "files").mkdir()
    (tmp_path / "files/input.txt").write_text("permanent input")
    run = jobs.launch(
        tmp_path, dict(name="Wave decay", command="cat input.txt; printf result > result.txt")
    )
    result = await_finished(tmp_path, run["id"])
    assert result["status"] == "succeeded"
    assert result["output"] == "permanent input"
    assert {f["name"] for f in result["files"]} == {"input.txt", "result.txt"}
    assert "wave-decay" in result["path"]
    assert not (tmp_path / "files/result.txt").exists()
    run = jobs.launch(tmp_path, dict(name="Deadline", command="sleep 30", timeout_seconds=1))
    assert await_finished(tmp_path, run["id"])["status"] == "timed_out"
    run = jobs.launch(tmp_path, dict(name="Stop", command="sleep 30"))
    jobs.cancel(tmp_path, run["id"])
    assert await_finished(tmp_path, run["id"])["status"] == "cancelled"


def test_native_activity_exposes_state_not_reasoning(tmp_path):
    log = tmp_path / "events.jsonl"
    log.write_text(
        json.dumps(
            {"type": "item.started", "item": {"type": "reasoning", "text": "private reasoning"}}
        )
        + "\n"
    )
    activity, commands = native_activity(log, "123", True)
    assert activity["label"] == "Thinking"
    assert "private reasoning" not in json.dumps(activity)
    assert commands == []


def test_warpx_discovery_uses_build_configuration(tmp_path):
    home = tmp_path / "home"
    for name, compute in [("build-one", "OMP"), ("build-two", "CUDA")]:
        build = home / "src/warpx" / name
        (build / "bin").mkdir(parents=True)
        (build / "CMakeCache.txt").write_text(
            "WarpX_COMPUTE:STRING=" + compute + "\nWarpX_PYTHON:BOOL=OFF\nWarpX_OPENPMD:BOOL=ON\n"
        )
        binary = build / "bin/warpx.3d"
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)
    found = discover_system_warpx(home / "src/simjecture", home=home)
    assert {item["profile"] for item in found} == {"warpx-cpu", "warpx-cuda"}
    assert all(item["path"] is None and not item["registered"] for item in found)


def test_interruption_report_distinguishes_agent_timeout_from_simulation_failure(tmp_path):
    from conjecture_solver.workspace_agent import interrupted_turn_summary

    (tmp_path / "files").mkdir()
    (tmp_path / "files/input.txt").write_text("saved")
    turn = tmp_path / "turns/123"
    turn.mkdir(parents=True)
    report = interrupted_turn_summary(tmp_path, turn, 900, timed_out=True)
    assert "15-minute" in report
    assert "not a verdict that the simulation failed" in report
    assert "No simulation was registered" in report
    assert "1 files" in report
    assert (
        "time" not in interrupted_turn_summary(tmp_path, turn, 900, timed_out=False).splitlines()[0]
    )


def test_controller_registers_identity_if_parent_cannot_read_it(tmp_path, monkeypatch):
    (tmp_path / "files").mkdir()
    monkeypatch.setattr(jobs, "read_process_identity", lambda *args, **kwargs: None)
    run = jobs.launch(tmp_path, dict(name="Identity recovery", command="sleep 20"))
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if jobs.snapshot(tmp_path, run["id"])["live"]:
            break
        time.sleep(0.05)
    assert jobs.snapshot(tmp_path, run["id"])["live"]
    jobs.cancel(tmp_path, run["id"])
    assert await_finished(tmp_path, run["id"])["status"] == "cancelled"


def test_public_native_activity_describes_work_without_reasoning(tmp_path):
    log = tmp_path / "events.jsonl"
    events = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "private hidden reasoning"},
                    {
                        "type": "tool_use",
                        "id": "read1",
                        "name": "read_file",
                        "input": {"target_file": "flash.par"},
                    },
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "read1", "content": "input contents"}
                ]
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "run1",
                        "name": "run_terminal_command",
                        "input": {
                            "command": "python pilot.py",
                            "description": "Run the pilot simulation",
                        },
                    }
                ]
            },
        },
    ]
    log.write_text("\n".join(json.dumps(e) for e in events))
    activity, commands = native_activity(log, "123", True)
    assert activity["label"] == "Running command"
    assert activity["detail"] == "Run the pilot simulation"
    assert activity["recent_actions"][0]["detail"] == "flash.par"
    assert activity["recent_actions"][0]["status"] == "completed"
    assert commands[0]["live"] and commands[0]["command"] == "python pilot.py"
    assert "private hidden reasoning" not in json.dumps([activity, commands])


def test_interactive_worker_does_not_arm_default_alarm(tmp_path, monkeypatch):
    from conjecture_solver import workspace_agent

    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(dict(backend="builtin", model="fixture", base_url="http://localhost"))
    )
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Investigate")
    limits = []
    alarms = []
    monkeypatch.setattr(workspace_agent.signal, "signal", lambda *args: None)
    monkeypatch.setattr(workspace_agent.signal, "alarm", alarms.append)

    def run(*args, **kwargs):
        limits.append(kwargs["wall_seconds"])
        return "done"

    monkeypatch.setattr(workspace_agent, "run_agent", run)
    assert (
        workspace_agent.main(
            ["--provider-config", str(config), "--prompt-file", str(prompt), "--cwd", str(tmp_path)]
        )
        == 0
    )
    assert limits == [None]
    assert alarms == [0]  # only clear a possible old alarm on exit
