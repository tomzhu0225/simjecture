import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from simjecture_monitor.control_commission import SOURCE_FILES, TOOL_FILES, plan


def setup_runner(tmp_path, monkeypatch):
    script = Path(__file__).parents[1] / "scripts/run_control_commission.py"
    spec = importlib.util.spec_from_file_location("control_runner_test", script)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    source = tmp_path / "source"
    hashes = {}
    for name in SOURCE_FILES:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("unit-test source placeholder\n")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    value = plan("a" * 40, hashes)
    value["source_archive_sha256"] = "c" * 64
    package = script.parents[1]
    value["commissioning_tools_sha256"] = {
        name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in TOOL_FILES
    }
    value["resource_bounds"]["minimum_gap_seconds"] = 0
    documents = {
        "plan": value,
        "backend": {},
        "predecessor-summary": dict(
            primary_all_attempts=dict(
                planned=64,
                started=64,
                complete_design=True,
                unstarted=[],
                audit_violations=[],
            )
        ),
        "predecessor-guard": {"stage": "released"},
        "predecessor-budget": {"starts": [{"ended_at": 1}]},
    }
    paths = {}
    for name, data in documents.items():
        paths[name] = tmp_path / (name + ".json")
        paths[name].write_text(json.dumps(data))
    qualification = dict(
        stage="completed",
        ended_at=time.time(),
        backend_sha256=hashlib.sha256(paths["backend"].read_bytes()).hexdigest(),
        cases=[
            dict(cells=cells, steps=steps, measured={"original_checks_passed": True})
            for cells, steps in [(64, 40), (128, 80)]
        ],
    )
    paths["physics-qualification"] = tmp_path / "physics.json"
    paths["physics-qualification"].write_text(json.dumps(qualification))
    interpreter = tmp_path / "venv-python"
    interpreter.symlink_to(sys.executable)
    root = tmp_path / "commission"
    paths.update(
        root=root,
        source=source,
        python=interpreter,
        codex=Path("/bin/false"),
        **{"plasma-assets": tmp_path / "plasma"},
    )
    arguments = [str(script)]
    for name, path in paths.items():
        arguments.extend(["--" + name, str(path)])
    monkeypatch.setattr(sys, "argv", arguments)
    return runner, root, interpreter, paths


def test_runner_rejects_partial_predecessor_before_creating_output_or_starting_process(
    tmp_path, monkeypatch
):
    runner, root, _, paths = setup_runner(tmp_path, monkeypatch)
    previous = json.loads(paths["predecessor-summary"].read_text())
    previous["primary_all_attempts"]["complete_design"] = False
    paths["predecessor-summary"].write_text(json.dumps(previous))
    monkeypatch.setattr(
        runner.subprocess, "Popen", lambda *a, **k: pytest.fail("No process allowed")
    )
    with pytest.raises(ValueError, match="incomplete"):
        runner.main()
    assert not root.exists()


@pytest.mark.parametrize("failure", ["nonzero_exit", "invalid_outcome"])
def test_first_scientific_attempt_is_retained_even_when_collection_fails(
    tmp_path, monkeypatch, failure
):
    runner, root, interpreter, _ = setup_runner(tmp_path, monkeypatch)
    calls = []

    class Child:
        pid = 424242

        def __init__(self, command, **kwargs):
            calls.append(command)
            if "--output-last-message" in command:
                Path(command[command.index("--output-last-message") + 1]).write_text("READY")
                self.returncode = 0
            else:
                if failure == "invalid_outcome":
                    output = Path(command[command.index("--root") + 1])
                    output.mkdir()
                    (output / "OUTCOME.json").write_text("{")
                self.returncode = 1 if failure == "nonzero_exit" else 0

        def communicate(self, *args, **kwargs):
            return None

        def poll(self):
            return self.returncode

    monkeypatch.setattr(runner.subprocess, "Popen", Child)
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1))
    monkeypatch.setattr(runner, "process_stat", lambda pid: {"pid": pid})
    with pytest.raises(SystemExit) as result:
        runner.main()
    assert result.value.code == 1 and len(calls) == 2
    assert (root / "native-codex").read_text().splitlines()[0] == "#!" + str(interpreter)
    final = json.loads((root / "FINALIZATION.json").read_text())
    assert final["attempted"] == 1 and len(final["unstarted"]) == 5
    selected = json.loads((root / "STARTED.json").read_text())
    identity = selected["blocks"][0]["trials"][0]["id"]
    receipt = json.loads((root / (identity + "-receipt.json")).read_text())
    assert receipt["ended_at"] >= receipt["started_at"]
    assert identity not in final["unstarted"]
    assert json.loads((root / "CAMPAIGN.json").read_text())["stage"] == "failed"
