"""Persistent interactive runs and public activity regression checks."""

import json
import time

import pytest

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


def test_run_files_separate_copied_results_and_changed_inputs(tmp_path):
    files = tmp_path / "files"
    (files / "analysis").mkdir(parents=True)
    (files / "analysis/previous-result.svg").write_text("previous simulation figure")
    (files / "settings.txt").write_text("before")
    (files / "unchanged.txt").write_text("keep this input")
    run = jobs.launch(
        tmp_path,
        dict(
            name="New result",
            command=(
                "printf 'after!' > settings.txt; touch unchanged.txt; printf fresh > result.txt"
            ),
        ),
    )
    result = await_finished(tmp_path, run["id"])
    roles = {f["name"]: f["role"] for f in result["files"]}
    assert roles == {
        "analysis/previous-result.svg": "input",
        "settings.txt": "modified_input",
        "unchanged.txt": "input",
        "result.txt": "output",
    }
    assert result["file_provenance"] == "content"
    assert "input_manifest" not in result  # Keep full hashes out of repeated agent/GUI polls.
    request = jobs.read(tmp_path / "simulations" / run["id"] / "request.json")
    assert len(request["input_manifest"]["settings.txt"]["sha256"]) == 64
    assert (files / "settings.txt").read_text() == "before"


def test_old_run_file_provenance_uses_only_recorded_input_paths(tmp_path):
    (tmp_path / "files").mkdir()
    (tmp_path / "files/input.txt").write_text("original")
    run = jobs.launch(
        tmp_path, dict(name="Legacy", command="printf changed > input.txt; printf new > result.txt")
    )
    await_finished(tmp_path, run["id"])
    request_path = tmp_path / "simulations" / run["id"] / "request.json"
    request = jobs.read(request_path)
    del request["input_manifest"]
    jobs.put(request_path, request)
    result = jobs.snapshot(tmp_path, run["id"], include_files=True)
    assert result["file_provenance"] == "paths_only"
    assert {f["name"]: f["role"] for f in result["files"]} == {
        "input.txt": "input",
        "result.txt": "output",
    }
    assert "input_manifest" not in jobs.read(request_path)  # No retrospective record rewrite.


def test_run_file_limit_prioritizes_outputs_and_modified_inputs(tmp_path):
    files = tmp_path / "files"
    files.mkdir()
    for i in range(205):
        (files / f"input-{i:03d}.txt").write_text("unchanged")
    (files / "z-settings.txt").write_text("before")
    run = jobs.launch(
        tmp_path,
        dict(
            name="Many inputs",
            command="printf 'after!' > z-settings.txt; printf new > z-result.txt",
        ),
    )
    result = await_finished(tmp_path, run["id"])
    assert len(result["files"]) == 200
    assert {f["name"]: f["role"] for f in result["files"][:2]} == {
        "z-result.txt": "output",
        "z-settings.txt": "modified_input",
    }


def test_command_files_are_shared_project_files(tmp_path):
    (tmp_path / "files").mkdir()
    (tmp_path / "files/previous-result.txt").write_text("earlier result")
    run = jobs.launch(
        tmp_path,
        dict(name="Analysis", kind="command", command="printf comparison > comparison.txt"),
    )
    result = await_finished(tmp_path, run["id"])
    assert result["file_provenance"] == "shared"
    assert {f["name"]: f["role"] for f in result["files"]} == {
        "previous-result.txt": "shared",
        "comparison.txt": "shared",
    }


def test_selected_simulation_inputs_skip_large_unrelated_project_files(tmp_path):
    files = tmp_path / "files"
    (files / "case").mkdir(parents=True)
    (files / "case/input.txt").write_text("needed")
    # A sparse archive exceeds the former 512 MiB ceiling without a large test write.
    with (files / "old-result.bin").open("wb") as stream:
        stream.truncate(1024**3)
    assert {relative.as_posix() for _, relative in jobs.selected_inputs(tmp_path, None)} == {
        "case/input.txt",
        "old-result.bin",
    }
    assert len(jobs.selected_inputs(tmp_path, ["old-result.bin"])) == 1
    run = jobs.launch(
        tmp_path,
        dict(
            command="cat case/input.txt > result.txt",
            input_files=["case/input.txt", "case/input.txt"],
        ),
    )
    result = await_finished(tmp_path, run["id"])
    assert result["kind"] == "simulation" and result["status"] == "succeeded"
    assert result["inputs"] == ["case/input.txt"]
    assert {f["name"]: f["role"] for f in result["files"]} == {
        "case/input.txt": "input",
        "result.txt": "output",
    }
    empty = jobs.launch(tmp_path, dict(command="printf fresh > fresh.txt", input_files=[]))
    assert {f["name"] for f in await_finished(tmp_path, empty["id"])["files"]} == {"fresh.txt"}


@pytest.mark.parametrize(
    "selection",
    [["../outside.txt"], ["/etc/passwd"], ["linked/file.txt"], ["missing.txt"], "input.txt", [123]],
)
def test_selected_inputs_reject_non_project_or_linked_files(tmp_path, selection):
    (tmp_path / "files").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file.txt").write_text("not a project input")
    (tmp_path / "files/linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        jobs.launch(tmp_path, dict(command="true", input_files=selection))
    assert not (tmp_path / "simulations").exists()


@pytest.mark.parametrize("aliased", [False, True])
def test_reclassifying_legacy_command_preserves_request_and_shared_provenance(tmp_path, aliased):
    (tmp_path / "files").mkdir()
    run = jobs.launch(
        tmp_path, dict(name="Solver", command="echo result > field.txt", kind="command")
    )
    await_finished(tmp_path, run["id"])
    request = tmp_path / "simulations" / run["id"] / "request.json"
    work = tmp_path / "files"
    if aliased:
        # Migrated requests can retain an old host path through a compatibility link.
        alias = tmp_path / "old-host"
        alias.symlink_to(tmp_path, target_is_directory=True)
        work = alias / "files"
        saved = json.loads(request.read_text())
        saved["work_directory"] = str(work)
        request.write_text(json.dumps(saved))
    original = request.read_bytes()
    jobs.classify(tmp_path, run["id"], "simulation")
    result = jobs.snapshot(tmp_path, run["id"], include_files=True)
    assert result["kind"] == "simulation"
    assert result["file_provenance"] == "shared"
    assert result["files"] == [dict(name="field.txt", bytes=7, role="shared")]
    assert result["work_directory"] == str(work)
    assert request.read_bytes() == original
    assert jobs.classify(tmp_path, run["id"], "command")["kind"] == "command"
    with pytest.raises(ValueError, match="Choose simulation or command"):
        jobs.classify(tmp_path, run["id"], "evidence")


def test_simulation_history_survives_many_newer_commands(tmp_path):
    from conjecture_solver.web.workspace import Workspace

    workspace = Workspace(tmp_path / ".workspace")
    project = workspace.create({"name": "Simulation history"})
    root_project = workspace.directory(project["id"])
    directory = root_project / "simulations"
    for i in range(240):
        root = directory / f"{i:03d}-job"
        root.mkdir(parents=True)
        jobs.put(
            root / "request.json",
            dict(
                id=root.name,
                name=root.name,
                kind="simulation" if i < 120 else "command",
                created_at=i,
            ),
        )
        jobs.put(root / "state.json", dict(status="succeeded", finished_at=i))
    records = jobs.list_jobs(root_project)
    assert len(records) == 240
    assert records[0]["id"] == "000-job"
    assert records[1]["id"] == "001-job"
    assert len(workspace.project(project["id"])["simulations"]) == 240
    native = dict(id="native-active", kind="command", source_turn="1000000000000", live=True)
    combined = jobs.ordered_jobs(records + [native])
    assert len(combined) == 241 and combined[-1] == native
    assert combined[0]["kind"] == "simulation"


def test_history_summaries_do_not_read_console_logs(tmp_path, monkeypatch):
    run = tmp_path / "simulations/001-solver"
    run.mkdir(parents=True)
    jobs.put(
        run / "request.json",
        dict(
            id=run.name,
            name="Solver",
            kind="simulation",
            created_at=1,
            inputs=["input.par"],
            input_manifest={"input.par": {}},
        ),
    )
    jobs.put(run / "state.json", dict(status="succeeded", finished_at=2))
    (run / "output.log").write_text("Retained detailed output")
    calls = []
    original = jobs.tail
    monkeypatch.setattr(
        jobs, "tail", lambda path, *args: calls.append(path) or original(path, *args)
    )
    summaries = jobs.list_jobs(tmp_path, summary=True)
    assert summaries[0]["id"] == "001-solver"
    assert "output" not in summaries[0] and "inputs" not in summaries[0]
    assert calls == []
    assert jobs.snapshot(tmp_path, "001-solver")["output"] == "Retained detailed output"


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


def test_live_preview_uses_only_top_level_public_text(tmp_path):
    log = tmp_path / "response.json"
    events = [
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "Inspecting the run."},
        },
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "delta": {"type": "thinking_delta", "thinking": "hidden"},
            },
        },
        {
            "type": "stream_event",
            "parent_tool_use_id": "helper",
            "event": {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "nested"},
            },
        },
    ]
    log.write_text("\n".join(json.dumps(e) for e in events))
    assert native_activity(log, "123", True)[0]["preview"] == "Inspecting the run."
    assert "preview" not in native_activity(log, "123", False)[0]
