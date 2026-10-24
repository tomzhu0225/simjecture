"""Collectors keep case/treatment metadata out of the worker's directory name."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("script", ["collect_sampled", "evaluate_adapter"])
def test_worker_roots_are_opaque_and_recoverable_from_host_manifest(tmp_path, monkeypatch, script):
    path = Path(__file__).parents[1] / "scripts" / (script + ".py")
    spec = importlib.util.spec_from_file_location("blinded_" + script, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []

    class Process:
        def __init__(self, command, **kwargs):
            calls.append(command)

        def poll(self):
            return 0

        def wait(self, **kwargs):
            return 0

    monkeypatch.setattr(
        module,
        "subprocess",
        SimpleNamespace(
            Popen=Process,
            check_output=lambda *a, **k: "test-revision\n",
            TimeoutExpired=subprocess.TimeoutExpired,
        ),
    )
    root = tmp_path / "cohort"
    argv = [script, "--root", str(root)]
    if script == "evaluate_adapter":
        data = tmp_path / "probe.json"
        data.write_text(json.dumps({"episodes": [{"decisions": [{"packet": {}}]}]}))
        argv += [
            "--base-socket",
            "/tmp/test-base",
            "--adapter-socket",
            "/tmp/test-adapter",
            "--probe-data",
            str(data),
        ]
        monkeypatch.setattr(
            module,
            "request",
            lambda socket, packet, **kw: dict(
                model_identity=dict(
                    checkpoint_config_sha256="same-base",
                    adapter_files_sha256={"weights": "adapter"} if "adapter" in str(socket) else {},
                )
            ),
        )
    monkeypatch.setattr(sys, "argv", argv)
    module.main()
    manifest = json.loads(
        (
            root / ("COLLECTION.json" if script == "collect_sampled" else "EVALUATION.json")
        ).read_text()
    )
    assert len(calls) == len(manifest["jobs"]) == 4
    roots = {Path(call[call.index("--root") + 1]) for call in calls}
    assert len(roots) == 4
    assert {path.name for path in roots} == {job["trial_id"] for job in manifest["jobs"]}
    assert all(path.parent == root for path in roots)
    for path in roots:
        assert path.name.startswith("trial-")
        assert not any(
            label in path.name
            for label in ["harness", "analysis", "healthy", "discrepancy", "base", "adapter"]
        )
    assert {job["case"] for job in manifest["jobs"]}
