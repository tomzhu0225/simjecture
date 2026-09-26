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
        (build / "CMakeCache.txt").write_text("WarpX_COMPUTE:STRING=" + compute + "\n")
        binary = build / "bin/warpx.3d"
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)
    found = discover_system_warpx(home / "src/simjecture", home=home)
    assert {item["profile"] for item in found} == {"warpx-cpu", "warpx-cuda"}
    assert all(item["path"] is None and not item["registered"] for item in found)
