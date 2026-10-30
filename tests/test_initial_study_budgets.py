import argparse
import json
import sys
import time

import pytest
from pydantic import ValidationError

from conjecture_solver.research_service import ResearchService
from conjecture_solver.study import configure_parser
from conjecture_solver.study_launch import NativeStudyRequest, materialize_native, resume_native


def request(tmp_path, **values):
    return NativeStudyRequest(
        hypothesis="A bounded synthetic claim.",
        campaign_id="study-test",
        output_directory=str(tmp_path / "study"),
        backend="codex",
        model="test-model",
        agent_executable=sys.executable,
        capability_directory="none",
        max_wall_seconds=300,
        **values,
    )


def test_storage_and_reserve_materialize_and_resume_immutable(tmp_path, monkeypatch):
    import conjecture_solver.execution as execution

    monkeypatch.setattr(execution, "require_execution_backend", lambda _: {"available": True})
    chosen = dict(
        max_experiment_bytes=64 * 1024**3, max_total_bytes=256 * 1024**3, report_reserve_seconds=180
    )
    original = request(tmp_path, **chosen)
    plan = materialize_native(original)
    service = ResearchService(plan.output_directory)
    manifest = service.manifest
    assert service.storage_limits() == {
        k: chosen[k] for k in ("max_experiment_bytes", "max_total_bytes")
    }
    assert manifest["finalization_policy"]["reserve_seconds"] == 180
    assert manifest["deadline"] - manifest["finalization_policy"]["compute_deadline"] == 180
    saved = json.loads((service.root / "study-launch.json").read_text())["request"]
    assert all(saved[k] == v for k, v in chosen.items())
    for name, value in chosen.items():
        assert float(plan.argv[plan.argv.index("--" + name.replace("_", "-")) + 1]) == value
    resumed = resume_native(service.root)
    assert resumed.request.report_reserve_seconds == 180
    omitted = request(tmp_path)
    assert (
        materialize_native(omitted, resume=True).request.max_total_bytes
        == chosen["max_total_bytes"]
    )
    for field, altered in [
        ("max_experiment_bytes", 63 * 1024**3),
        ("max_total_bytes", 300 * 1024**3),
        ("report_reserve_seconds", 120),
    ]:
        with pytest.raises(ValueError, match="differs"):
            materialize_native(original.model_copy(update={field: altered}), resume=True)
    assert service.storage_limits()["max_total_bytes"] == chosen["max_total_bytes"]


def test_storage_admission_uses_initial_allowance_and_rejects_oversize(tmp_path):
    s = ResearchService.create(
        tmp_path / "study",
        "A synthetic claim.",
        wall_seconds=60,
        execution_backend="process-cooperative",
        max_experiment_bytes=2 * 1024 * 1024,
        max_total_bytes=4 * 1024 * 1024,
    )
    (s.work / "calc.py").write_text("from pathlib import Path\nPath('result').write_text('ok')\n")
    receipt = s.run("calc.py", outputs=["result"], stage="exploration")
    assert receipt["workspace_limit_bytes"] == 2 * 1024 * 1024
    end = time.monotonic() + 20
    while time.monotonic() < end and s._read("experiments", receipt["id"])["status"] in {
        "queued",
        "running",
    }:
        time.sleep(0.05)
    assert s._read("experiments", receipt["id"])["status"] == "succeeded"
    with (s.work / "large").open("wb") as f:
        f.truncate(2 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="storage limits"):
        s.run("calc.py", inputs=["large"], outputs=["result"], stage="exploration")


@pytest.mark.parametrize(
    "name,value",
    [
        ("max_experiment_bytes", True),
        ("max_experiment_bytes", 1.5),
        ("max_total_bytes", "12"),
        ("max_total_bytes", 0),
        ("report_reserve_seconds", True),
        ("report_reserve_seconds", float("inf")),
        ("report_reserve_seconds", 300),
    ],
)
def test_request_rejects_invalid_budgets(tmp_path, name, value):
    with pytest.raises(ValidationError):
        request(tmp_path, **{name: value})


def test_defaults_legacy_resume_and_direct_cli_options(tmp_path, monkeypatch):
    import conjecture_solver.execution as execution

    monkeypatch.setattr(execution, "require_execution_backend", lambda _: {"available": True})
    plan = materialize_native(request(tmp_path))
    s = ResearchService(plan.output_directory)
    assert s.storage_limits() == {
        "max_experiment_bytes": 4 * 1024**3,
        "max_total_bytes": 8 * 1024**3,
    }
    assert "finalization_policy" not in s.manifest
    launch_path = s.root / "study-launch.json"
    launch = json.loads(launch_path.read_text())
    for key in ("max_experiment_bytes", "max_total_bytes", "report_reserve_seconds"):
        launch["request"].pop(key)
    launch_path.write_text(json.dumps(launch))
    assert resume_native(s.root).request.max_experiment_bytes is None
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    parsed = parser.parse_args(
        [
            "--campaign",
            str(s.root),
            "--max-experiment-bytes",
            "64",
            "--max-total-bytes",
            "256",
            "--report-reserve-seconds",
            "18",
        ]
    )
    assert (parsed.max_experiment_bytes, parsed.max_total_bytes, parsed.report_reserve_seconds) == (
        64,
        256,
        18,
    )


def test_service_validates_pair_and_rejects_changed_values_on_resume(tmp_path):
    s = ResearchService.create(
        tmp_path / "study",
        "A bounded claim.",
        wall_seconds=100,
        max_experiment_bytes=100,
        max_total_bytes=200,
        report_reserve_seconds=30,
    )
    assert ResearchService.create(s.root, s.manifest["hypothesis"]).manifest == s.manifest
    for kwargs in (
        {"max_experiment_bytes": 101},
        {"max_total_bytes": 201},
        {"report_reserve_seconds": 31},
        {"report_reserve_seconds": True},
    ):
        with pytest.raises(ValueError):
            ResearchService.create(s.root, s.manifest["hypothesis"], **kwargs)
    with pytest.raises(ValueError, match="cover"):
        ResearchService.create(
            tmp_path / "bad", "claim", max_experiment_bytes=100, max_total_bytes=99
        )


def test_explicit_report_cutoff_blocks_experiment_admission(tmp_path, monkeypatch):
    import conjecture_solver.research_service as service_module

    s = ResearchService.create(
        tmp_path / "study",
        "A bounded claim.",
        wall_seconds=100,
        report_reserve_seconds=20,
        execution_backend="process-cooperative",
    )
    (s.work / "calc.py").write_text("print('fixture')\n")
    monkeypatch.setattr(service_module.time, "time", lambda: s.manifest["deadline"] - 19)
    with pytest.raises(ValueError, match="Protected report time"):
        s.run("calc.py", outputs=["result"], stage="exploration")


def test_web_api_passes_budgets_without_coercion(tmp_path, monkeypatch):
    import conjecture_solver.web.application as module
    from conjecture_solver.web.application import SimjectureWebApplication, WebApplicationError

    captured = []

    def record(request):
        captured.append(request)
        raise RuntimeError("stop before launching")

    monkeypatch.setattr(module, "materialize_operator_input", record)
    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    payload = dict(
        hypothesis="A synthetic claim.",
        max_wall_seconds=300,
        max_experiment_bytes=64 * 1024**3,
        max_total_bytes=256 * 1024**3,
        report_reserve_seconds=180,
    )
    with pytest.raises(WebApplicationError, match="stop before launching"):
        app.create_campaign(payload)
    assert captured[0].max_experiment_bytes == payload["max_experiment_bytes"]
    assert captured[0].report_reserve_seconds == 180
    with pytest.raises(WebApplicationError):
        app.create_campaign(payload | {"max_total_bytes": "123"})
    assert len(captured) == 1


def test_direct_cli_launch_and_reject_changed_resume(tmp_path):
    import os
    import subprocess
    from pathlib import Path

    agent = tmp_path / "fake-agent"
    agent.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(60)\n")
    agent.chmod(0o700)
    hypothesis = tmp_path / "hypothesis"
    instructions = tmp_path / "instructions"
    hypothesis.write_text("A synthetic bounded claim.")
    instructions.write_text("Use synthetic tests only.")
    root = tmp_path / "direct"
    base = [
        sys.executable,
        "-m",
        "conjecture_solver.study",
        "--campaign",
        str(root),
        "--instructions-file",
        str(instructions),
        "--backend",
        "codex",
        "--model",
        "fixture",
        "--executable",
        str(agent),
        "--capabilities",
        "none",
        "--execution-backend",
        "process-cooperative",
        "--wall-seconds",
        "90",
        "--turn-seconds",
        "10",
        "--quiet",
    ]
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    process = subprocess.Popen(
        base
        + [
            "--hypothesis-file",
            str(hypothesis),
            "--max-experiment-bytes",
            "2097152",
            "--max-total-bytes",
            "4194304",
            "--report-reserve-seconds",
            "25",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 15
        state_path = root / "supervisor/state.json"
        while time.monotonic() < deadline:
            if state_path.exists() and json.loads(state_path.read_text()).get("child_pid"):
                break
            if process.poll() is not None:
                pytest.fail(process.stderr.read().decode())
            time.sleep(0.05)
        else:
            pytest.fail("Fixture worker did not start")
        manifest = ResearchService(root).manifest
        assert manifest["max_experiment_bytes"] == 2097152
        assert manifest["max_total_bytes"] == 4194304
        assert manifest["finalization_policy"]["reserve_seconds"] == 25
        (root / "supervisor/control.json").write_text('{"command":"pause"}')
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
    resumed = subprocess.run(
        base + ["--max-total-bytes", "8388608"], env=env, capture_output=True, text=True, timeout=10
    )
    assert resumed.returncode != 0
    assert "immutable" in resumed.stderr
    assert ResearchService(root).manifest["max_total_bytes"] == 4194304
